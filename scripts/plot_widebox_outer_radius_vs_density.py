#!/usr/bin/env python3
"""
Plot simple-bubble and measured outer radii against ambient density for the
wide-box AMRVAC runs.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyze_amrvac_bubble_profiles import M_MOL


RUN_RE = re.compile(r"density_(\d+)")


def run_density_number(run_name: str) -> int:
    match = RUN_RE.fullmatch(run_name)
    if not match:
        raise ValueError(f"Could not parse density exponent from {run_name!r}")
    return int(match.group(1))


def load_rows(summary_csv: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    with summary_csv.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            run = row["run"]
            exp = run_density_number(run)
            rho_g_cm3 = 10.0 ** (-exp)
            nism_cm3 = rho_g_cm3 / M_MOL
            simple_rt_pc = float(row["simple_rt_pc"])
            simple_r2_rt = float(row["simple_r2_rt"])
            rows.append(
                {
                    "run": run,
                    "density_exponent": exp,
                    "rho_g_cm3": rho_g_cm3,
                    "nism_cm3": nism_cm3,
                    "simple_r2_pc": simple_rt_pc * simple_r2_rt,
                    "measured_outer_rise_pc": float(row["outer_rise_pc"]),
                    "domain_rmax_pc": float(row["domain_rmax_pc"]),
                    "edge_margin_pc": float(row["edge_margin_pc"]),
                }
            )
    rows.sort(key=lambda item: item["density_exponent"], reverse=True)
    return rows


def write_table(rows: list[dict[str, float | str]], output_csv: Path) -> None:
    fieldnames = [
        "run",
        "density_exponent",
        "rho_g_cm3",
        "nism_cm3",
        "simple_r2_pc",
        "measured_outer_rise_pc",
        "domain_rmax_pc",
        "edge_margin_pc",
    ]
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot(rows: list[dict[str, float | str]], output_path: Path) -> None:
    rho = np.asarray([row["rho_g_cm3"] for row in rows], dtype=float)
    simple_r2 = np.asarray([row["simple_r2_pc"] for row in rows], dtype=float)
    measured = np.asarray([row["measured_outer_rise_pc"] for row in rows], dtype=float)
    domain_rmax = np.asarray([row["domain_rmax_pc"] for row in rows], dtype=float)

    plt.figure(figsize=(8.2, 5.8))
    plt.loglog(rho, simple_r2, "o-", lw=1.8, ms=6, label="Simple bubble $R_2$")
    plt.loglog(rho, measured, "s-", lw=1.8, ms=6, label="Measured outer rise")
    plt.loglog(rho, domain_rmax, "--", lw=1.4, color="0.35", label="Current box edge")

    for row in rows:
        x = float(row["rho_g_cm3"])
        plt.annotate(
            str(row["density_exponent"]),
            (x, float(row["measured_outer_rise_pc"])),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
        )

    plt.xlabel(r"Ambient mass density $\rho_{\rm ISM}$ (g cm$^{-3}$)")
    plt.ylabel("Outer radius (pc)")
    plt.title("Wide-Box AMRVAC Outer Radius vs Ambient Density")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary-csv",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate_widebox_20260421/widebox_wall_clearance_summary.csv",
        help="Wide-box wall-clearance summary CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate_widebox_20260421",
        help="Directory for the derived plot and table.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(Path(args.summary_csv))
    write_table(rows, output_dir / "outer_radius_vs_density.csv")
    plot(rows, output_dir / "outer_radius_vs_density.png")
    print(f"Wrote outer-radius plot and table to {output_dir}")


if __name__ == "__main__":
    main()
