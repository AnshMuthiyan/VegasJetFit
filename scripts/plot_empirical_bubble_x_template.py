#!/usr/bin/env python3
"""
Plot the bubble-like AMRVAC x-coordinate map together with the adopted
``density_21`` empirical-bubble template and export the template as CSV.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_raw_profiles(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    by_run: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in csv.DictReader(path.open()):
        if row["psi"] == "":
            continue
        by_run[row["run"]].append((float(row["x"]), float(row["psi"])))

    profiles: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for run, points in by_run.items():
        points.sort()
        x = np.asarray([pair[0] for pair in points], dtype=float)
        psi = np.asarray([pair[1] for pair in points], dtype=float)
        profiles[run] = (x, psi)
    return profiles


def build_density21_template(
    x: np.ndarray,
    psi: np.ndarray,
    *,
    shelf_end: float = 0.02,
    blend_start: float = 0.82,
) -> tuple[np.ndarray, np.ndarray]:
    x_out = x[x <= blend_start].copy()
    psi_out = np.interp(x_out, x, psi)
    psi_out[x_out <= shelf_end] = 0.0
    return x_out, psi_out


def write_template_csv(path: Path, x: np.ndarray, psi: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["x", "psi_density21"])
        writer.writeheader()
        for x_val, psi_val in zip(x, psi):
            writer.writerow({"x": f"{x_val:.15g}", "psi_density21": f"{psi_val:.15g}"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-csv",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/empirical_bubble_note/x_profile_collapse_bubble_like.csv",
        help="Raw x-profile collapse CSV with per-run psi(x) samples.",
    )
    parser.add_argument(
        "--output",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/empirical_bubble_note/x_profile_collapse_bubble_like.png",
        help="Output plot path.",
    )
    parser.add_argument(
        "--template-csv",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/empirical_bubble_note/x_profile_density21_template.csv",
        help="Output CSV for the adopted density_21 template.",
    )
    parser.add_argument(
        "--blend-start",
        type=float,
        default=0.82,
        help="Blend start shown on the plot for the adopted empirical template.",
    )
    args = parser.parse_args()

    profiles = load_raw_profiles(Path(args.raw_csv))
    if "density_21" not in profiles:
        raise KeyError(f"density_21 not found in {args.raw_csv}")

    density21_x, density21_psi = profiles["density_21"]
    template_x, template_psi = build_density21_template(
        density21_x,
        density21_psi,
        blend_start=args.blend_start,
    )
    write_template_csv(Path(args.template_csv), template_x, template_psi)

    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=220)
    colors = {
        "density_21": "tab:blue",
        "density_22": "tab:orange",
        "density_23": "tab:green",
    }
    for run in ("density_21", "density_22", "density_23"):
        x, psi = profiles[run]
        ax.plot(x, psi, lw=1.6, color=colors[run], label=run)

    ax.plot(
        template_x,
        template_psi,
        color="black",
        lw=2.8,
        label="adopted density_21 template",
        zorder=5,
    )
    ax.axvline(args.blend_start, color="0.55", ls="--", lw=1.0, label=fr"blend start $x={args.blend_start:.2f}$")
    ax.axhline(0.0, color="0.35", ls="--", lw=0.9)
    ax.axhline(1.0, color="0.55", ls=":", lw=0.9)
    ax.set_xlabel(r"$x = (r-R_t)/(R_2-R_t)$ using simple-model $R_2$")
    ax.set_ylabel(r"$\psi(x) = [\log n - \log(4n_t)]/[\log n_{\rm ism}-\log(4n_t)]$")
    ax.set_title("Bubble-like AMRVAC profiles with adopted density_21 template")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)

    text = "\n".join(
        [
            "Median curve dropped for implementation",
            r"because the simple-model $x$ map pulls the",
            r"$\mathrm{density\_23}$ outer wall inward, creating",
            r"a nonphysical bump near $x \approx 0.8$.",
            r"The current empirical bubble uses the",
            r"$\mathrm{density\_21}$ profile directly.",
        ]
    )
    ax.text(
        0.03,
        0.03,
        text,
        transform=ax.transAxes,
        fontsize=8.0,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="0.7"),
    )

    fig.tight_layout()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")

    print(output_path)
    print(Path(args.template_csv))


if __name__ == "__main__":
    main()
