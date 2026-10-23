#!/usr/bin/env python3
"""Summarize validated 0.01 pc inner-boundary short density tests."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_evolving import density_profile, front_log
from validate_evolving import expected_front


def summarize(root: Path, output: Path) -> None:
    rows = []
    for grid in (1024, 2048):
        for n0 in (20000, 40000, 80000):
            for branch in ("gravity", "nogravity"):
                prefix = f"ion_{branch}_n{n0:05d}_inner0p01_r{grid}_0p1myr"
                log = root / f"{prefix}.run.log"
                if not log.exists():
                    continue
                if not (root / f"{prefix}0005.vtu").exists():
                    raise ValueError(f"missing validated endpoint: {prefix}")
                age, front = front_log(log)
                rows.append({
                    "n0_cm3": n0,
                    "grid_cells": grid,
                    "gravity": branch,
                    "inner_radius_pc": 0.01,
                    "initial_front_analytic_pc": expected_front(n0, 0.01),
                    "front_0p1myr_pc": float(np.interp(0.1, age, front)),
                })
    if not rows:
        raise ValueError("no completed short cases")
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "front_summary_0p1myr.csv"
    png_path = output / "front_0p1myr_by_density.png"
    profile_path = output / "density_profiles_0p1myr.png"
    for path in (csv_path, png_path, profile_path):
        if path.exists():
            raise FileExistsError(path)
    with csv_path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    for grid, marker in ((1024, "o"), (2048, "s")):
        for branch, style in (("gravity", "-"), ("nogravity", "--")):
            subset = [r for r in rows if r["grid_cells"] == grid and r["gravity"] == branch]
            if subset:
                ax.plot([r["n0_cm3"] for r in subset],
                        [r["front_0p1myr_pc"] for r in subset],
                        marker=marker, linestyle=style, lw=1.5,
                        label=f"{grid} cells, {branch}")
    ax.set(xlabel=r"Initial central $n_H$ (cm$^{-3}$)",
           ylabel="Ionization-front radius at 0.1 Myr (pc)",
           title="0.01 pc inner-boundary density tests")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    fig.savefig(png_path, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    for n0, color in ((20000, "#19778c"), (40000, "#bb7124"),
                      (80000, "#ad384f")):
        prefix = f"ion_gravity_n{n0:05d}_inner0p01_r2048_0p1myr"
        path = root / f"{prefix}0005.vtu"
        if not path.exists():
            continue
        radius, nh = density_profile(path)
        ax.plot(radius, nh, color=color, lw=1.4, label=f"{n0:,} cm$^{{-3}}$")
    ax.axvline(2, color="#666666", linestyle=":", lw=0.9)
    ax.set(xlabel="Radius (pc)", ylabel=r"Hydrogen nuclei density (cm$^{-3}$)",
           title="0.1 Myr; 2048-cell prescribed-field branch")
    ax.set_xlim(0, 4)
    ax.set_yscale("log")
    ax.grid(alpha=0.2, which="both")
    ax.legend(frameon=False)
    fig.savefig(profile_path, dpi=180)
    plt.close(fig)
    print(f"{len(rows)} cases: {csv_path}, {png_path}, {profile_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    summarize(args.root, args.output)


if __name__ == "__main__":
    main()
