#!/usr/bin/env python3
"""Plot native density-shell peaks against initial central cloud density."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np

from plot_evolving import density_profile
from validate_smoke import read_vtu


def measure(root: Path, prefix: str, n0: int, cells: int, inner_pc: float,
            branch: str, age_myr: float, search_min_pc: float,
            search_max_pc: float, series: str) -> dict:
    log = (root / f"{prefix}.run.log").read_text(encoding="utf-8")
    if "Finished AMRVAC" not in log or (root / f"{prefix}.run.err").stat().st_size:
        raise ValueError(f"incomplete run or nonempty stderr: {prefix}")
    exit_path = root / f"{prefix}.run.exit"
    if exit_path.exists() and exit_path.read_text(encoding="ascii").strip() != "0":
        raise ValueError(f"nonzero run exit: {prefix}")
    index = 48 if age_myr == 4.77 else 5
    vtu = root / f"{prefix}{index:04d}.vtu"
    saved_age_yr, _ = read_vtu(vtu)
    saved_age_myr = saved_age_yr * (365.25 / 365.0) / 1.0e6
    if not np.isclose(saved_age_myr, age_myr, atol=2e-5):
        raise ValueError(f"unexpected saved age in {vtu}: {saved_age_myr}")
    radius, nh = density_profile(vtu)
    mask = (radius >= search_min_pc) & (radius < search_max_pc)
    if not np.any(mask) or not np.all(np.isfinite(nh[mask])) or np.any(nh[mask] <= 0):
        raise ValueError(f"invalid shell search region: {vtu}")
    shell_index = int(np.argmax(nh[mask]))
    return {
        "series": series,
        "case": prefix,
        "age_myr": age_myr,
        "central_nh_cm3": n0,
        "inner_radius_pc": inner_pc,
        "grid_cells": cells,
        "field_branch": "prescribed_g" if branch == "gravity" else "none",
        "search_min_pc": search_min_pc,
        "search_max_pc": search_max_pc,
        "shell_peak_pc": float(radius[mask][shell_index]),
        "shell_peak_nh_cm3": float(nh[mask][shell_index]),
    }


def plot(old_root: Path, new_root: Path, output: Path) -> None:
    rows = []
    for n0 in (4000, 6000, 8000, 10000):
        for branch in ("gravity", "nogravity"):
            prefix = f"ion_{branch}_n{n0:05d}_r512_4p77myr"
            rows.append(measure(old_root, prefix, n0, 512, 0.1, branch,
                                4.77, 2.0, 35.0, "old_full"))
    for branch in ("gravity", "nogravity"):
        prefix = f"ion_{branch}_n10000_r1024_4p77myr"
        rows.append(measure(old_root, prefix, 10000, 1024, 0.1, branch,
                            4.77, 2.0, 35.0, "old_grid_check"))
    for n0 in (20000, 40000):
        for branch in ("gravity", "nogravity"):
            prefix = f"ion_{branch}_n{n0:05d}_inner0p01_r1024_4p77myr"
            rows.append(measure(new_root, prefix, n0, 1024, 0.01, branch,
                                4.77, 2.0, 35.0, "new_full"))
    for n0 in (20000, 40000, 80000):
        for branch in ("gravity", "nogravity"):
            prefix = f"ion_{branch}_n{n0:05d}_inner0p01_r2048_0p1myr"
            rows.append(measure(new_root, prefix, n0, 2048, 0.01, branch,
                                0.1, 0.2, 2.0, "new_short"))

    output.mkdir(parents=True, exist_ok=False)
    csv_path = output / "shell_peak_vs_density.csv"
    with csv_path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.1), constrained_layout=True)
    groups = (
        ("old_full", "0.1 pc inner, 512 cells", "#19778c", "o"),
        ("new_full", "0.01 pc inner, 1024 cells", "#ad384f", "s"),
    )
    for series, label, color, marker in groups:
        for branch, linestyle, suffix in (
            ("prescribed_g", "-", "fixed g(r)"),
            ("none", "--", "no g"),
        ):
            subset = [r for r in rows if r["series"] == series
                      and r["field_branch"] == branch]
            axes[0].plot([r["central_nh_cm3"] for r in subset],
                         [r["shell_peak_pc"] for r in subset],
                         color=color, marker=marker, linestyle=linestyle,
                         linewidth=1.6, markersize=5,
                         label=f"{label}, {suffix}")
    check = next(r for r in rows if r["series"] == "old_grid_check"
                 and r["field_branch"] == "prescribed_g")
    axes[0].scatter([check["central_nh_cm3"]], [check["shell_peak_pc"]],
                    facecolors="none", edgecolors="#19778c", marker="D",
                    s=52, linewidths=1.4, label="10k grid check, 1024 cells")
    axes[0].set(title="WR endpoint (4.77 Myr)", ylabel="Density-shell peak radius (pc)",
                xlabel=r"Initial central $n_H$ (cm$^{-3}$)")
    axes[0].set_xscale("log")
    axes[0].set_xticks([4000, 6000, 8000, 10000, 20000, 40000],
                      labels=["4k", "6k", "8k", "10k", "20k", "40k"])
    axes[0].xaxis.set_minor_formatter(NullFormatter())
    axes[0].set_xlim(3500, 48000)
    axes[0].set_ylim(12, 24)
    axes[0].grid(alpha=0.2)
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper right")

    for branch, linestyle, suffix in (
        ("prescribed_g", "-", "fixed g(r)"),
        ("none", "--", "no g"),
    ):
        subset = [r for r in rows if r["series"] == "new_short"
                  and r["field_branch"] == branch]
        axes[1].plot([r["central_nh_cm3"] for r in subset],
                     [r["shell_peak_pc"] for r in subset],
                     color="#ad384f", marker="s", linestyle=linestyle,
                     linewidth=1.6, markersize=5,
                     label=f"0.01 pc inner, 2048 cells, {suffix}")
    axes[1].set(title="Early phase (0.1 Myr)",
                xlabel=r"Initial central $n_H$ (cm$^{-3}$)")
    axes[1].set_xscale("log")
    axes[1].set_xticks([20000, 40000, 80000], labels=["20k", "40k", "80k"])
    axes[1].xaxis.set_minor_formatter(NullFormatter())
    axes[1].set_xlim(17000, 95000)
    axes[1].set_ylim(0.45, 1.1)
    axes[1].grid(alpha=0.2)
    axes[1].legend(frameon=False, fontsize=8)
    fig.savefig(output / "shell_peak_vs_density.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {len(rows)} native-shell measurements to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_root", type=Path)
    parser.add_argument("new_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plot(args.old_root, args.new_root, args.output)


if __name__ == "__main__":
    main()
