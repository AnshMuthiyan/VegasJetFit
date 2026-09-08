#!/usr/bin/env python3
"""
Calibrate a Weaver-style outer-radius scaling on trusted wide-box runs and
compare the prediction against the measured outer-rise radii.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_rows(csv_path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    with csv_path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "run": row["run"],
                    "density_exponent": float(row["density_exponent"]),
                    "rho_g_cm3": float(row["rho_g_cm3"]),
                    "measured_outer_rise_pc": float(row["measured_outer_rise_pc"]),
                    "domain_rmax_pc": float(row["domain_rmax_pc"]),
                    "edge_margin_pc": float(row["edge_margin_pc"]),
                }
            )
    rows.sort(key=lambda item: item["rho_g_cm3"])
    return rows


def calibrate_weaver(rows: list[dict[str, float | str]], trusted_runs: list[str]) -> float:
    trusted = [row for row in rows if row["run"] in trusted_runs]
    if not trusted:
        raise ValueError("No trusted runs selected for Weaver calibration.")
    log_k = [
        math.log10(float(row["measured_outer_rise_pc"])) + 0.2 * math.log10(float(row["rho_g_cm3"]))
        for row in trusted
    ]
    return 10.0 ** (sum(log_k) / len(log_k))


def write_table(rows: list[dict[str, float | str]], output_path: Path) -> None:
    fieldnames = list(rows[0].keys())
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot(rows: list[dict[str, float | str]], trusted_runs: list[str], output_path: Path) -> None:
    rho = np.asarray([float(row["rho_g_cm3"]) for row in rows], dtype=float)
    measured = np.asarray([float(row["measured_outer_rise_pc"]) for row in rows], dtype=float)
    predicted = np.asarray([float(row["weaver_predicted_pc"]) for row in rows], dtype=float)
    domain = np.asarray([float(row["domain_rmax_pc"]) for row in rows], dtype=float)

    plt.figure(figsize=(8.4, 5.8))
    plt.loglog(rho, measured, "s-", lw=1.8, ms=6, label="Measured outer rise")
    plt.loglog(rho, predicted, "o-", lw=1.8, ms=6, label="Weaver prediction")
    plt.loglog(rho, domain, "--", color="0.35", lw=1.3, label="Current box edge")

    for row in rows:
        run = str(row["run"])
        x = float(row["rho_g_cm3"])
        y = float(row["measured_outer_rise_pc"])
        label = run.split("_")[-1]
        suffix = "*" if run in trusted_runs else ""
        plt.annotate(f"{label}{suffix}", (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)

    plt.xlabel(r"Ambient mass density $\rho_{\rm ISM}$ (g cm$^{-3}$)")
    plt.ylabel("Outer radius (pc)")
    plt.title("Wide-Box Weaver Prediction vs Measured Outer Radius")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate_widebox_20260421/outer_radius_vs_density.csv",
        help="Wide-box outer-radius table.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate_widebox_20260421",
        help="Directory for the Weaver-comparison outputs.",
    )
    parser.add_argument(
        "--trusted",
        nargs="+",
        default=["density_20", "density_21"],
        help="Trusted runs used to set the Weaver normalization.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(Path(args.input_csv))
    k_norm = calibrate_weaver(rows, args.trusted)

    out_rows: list[dict[str, float | str]] = []
    for row in rows:
        rho = float(row["rho_g_cm3"])
        pred = k_norm * rho ** (-0.2)
        ratio = float(row["measured_outer_rise_pc"]) / pred
        out_rows.append(
            {
                **row,
                "weaver_k_pc_g0p2_cm0p6": k_norm,
                "weaver_predicted_pc": pred,
                "measured_over_predicted": ratio,
            }
        )

    write_table(out_rows, output_dir / "weaver_prediction_from_dense_subset.csv")
    plot(out_rows, args.trusted, output_dir / "weaver_prediction_from_dense_subset.png")

    notes = output_dir / "weaver_prediction_notes.txt"
    with notes.open("w") as handle:
        handle.write("Trusted calibration runs:\n")
        for run in args.trusted:
            handle.write(f"- {run}\n")
        handle.write(f"\nWeaver normalization K (pc * (g cm^-3)^1/5): {k_norm:.8e}\n")

    print(f"Wrote Weaver comparison to {output_dir}")


if __name__ == "__main__":
    main()
