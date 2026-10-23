#!/usr/bin/env python3
"""Summarize the matched 512-cell density sweep and short grid checks."""

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
from validate_smoke import PRESSURE_UNIT, read_vtu


DENSITIES = (4000, 6000, 8000, 10000)
COLORS = ("#19778c", "#8c9a34", "#bb7124", "#ad384f")


def crossing_age(age: np.ndarray, front: np.ndarray, radius: float) -> float:
    indices = np.flatnonzero(front >= radius)
    if not len(indices):
        return float("nan")
    index = int(indices[0])
    if index == 0:
        return float(age[0])
    return float(np.interp(radius, front[index - 1:index + 1], age[index - 1:index + 1]))


def plot(root: Path, out: Path) -> None:
    for n0 in DENSITIES:
        for branch in ("gravity", "nogravity"):
            prefix = f"ion_{branch}_n{n0:05d}_r512_4p77myr"
            if not (root / f"{prefix}0048.vtu").exists():
                raise FileNotFoundError(f"missing full endpoint: {prefix}")
            if not (root / f"{prefix}.run.log").exists():
                raise FileNotFoundError(f"missing full log: {prefix}")
    out.mkdir(parents=True, exist_ok=True)
    names = ("front_history_r512.png", "wr_density_r512.png",
             "resolution_check_0p1myr.png", "front_summary_phase_aware_r512.csv",
             "late_front_r512.png", "wr_pressure_r512.png")
    for name in names:
        if (out / name).exists():
            raise FileExistsError(out / name)

    fig, ax = plt.subplots(figsize=(9.0, 5.1), constrained_layout=True)
    rows = []
    for n0, color in zip(DENSITIES, COLORS):
        for branch, linestyle in (("gravity", "-"), ("nogravity", "--")):
            prefix = f"ion_{branch}_n{n0:05d}_r512_4p77myr"
            age, front = front_log(root / f"{prefix}.run.log")
            ax.plot(age, front, color=color, linestyle=linestyle, lw=1.5,
                    label=f"{n0:,} cm$^{{-3}}$, {branch}")
            rows.append({
                "n0_cm3": n0,
                "grid_cells": 512,
                "gravity": branch,
                "initial_front_analytic_pc": expected_front(n0),
                "front_0p1myr_pc": float(np.interp(0.1, age, front)),
                "front_4p3myr_pc": float(np.interp(4.3, age, front)),
                "rsg_min_front_pc": float(np.min(front[(age >= 4.3) & (age < 4.5)])),
                "front_4p6myr_pc": float(np.interp(4.6, age, front)),
                "front_4p77myr_pc": float(np.interp(4.77, age, front)),
                "first_cross_2pc_myr": crossing_age(age, front, 2.0),
            })
    ax.axhline(2.0, color="#555555", lw=0.9, linestyle=":")
    for phase_age in (4.3, 4.5):
        ax.axvline(phase_age, color="#777777", lw=0.8, linestyle=":")
    ax.set(xlabel="Stellar age (Myr)", ylabel="Ionization-front radius (pc)",
           title="40 solar-mass wind: density sweep on matched 512-cell grid")
    ax.set_xlim(0, 4.77)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, ncol=2, fontsize=8, loc="upper left")
    fig.savefig(out / names[0], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.7), constrained_layout=True)
    for n0, color in zip(DENSITIES, COLORS):
        prefix = f"ion_gravity_n{n0:05d}_r512_4p77myr"
        age, front = front_log(root / f"{prefix}.run.log")
        ax.plot(age, front, color=color, lw=1.5, label=f"{n0:,} cm$^{{-3}}$")
    for phase_age in (4.3, 4.5):
        ax.axvline(phase_age, color="#555555", lw=0.9, linestyle=":")
    ax.set(xlabel="Stellar age (Myr)", ylabel="Ionization-front radius (pc)",
           title="RSG recombination and WR reionization")
    ax.set_xlim(4.25, 4.65)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.18)
    ax.legend(frameon=False)
    fig.savefig(out / names[4], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.0, 5.1), constrained_layout=True)
    for n0, color in zip(DENSITIES, COLORS):
        prefix = f"ion_gravity_n{n0:05d}_r512_4p77myr"
        radius, nh = density_profile(root / f"{prefix}0048.vtu")
        ax.plot(radius, nh, color=color, lw=1.5, label=f"{n0:,} cm$^{{-3}}$")
    ax.axvline(2.0, color="#555555", lw=0.9, linestyle=":")
    ax.set(xlabel="Radius (pc)", ylabel=r"Hydrogen nuclei density (cm$^{-3}$)",
           title="End of Wolf-Rayet phase, static-gravity branch")
    ax.set_xlim(0, 35)
    ax.set_yscale("log")
    ax.grid(alpha=0.18, which="both")
    ax.legend(frameon=False)
    fig.savefig(out / names[1], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.0, 5.1), constrained_layout=True)
    for n0, color in zip(DENSITIES, COLORS):
        prefix = f"ion_gravity_n{n0:05d}_r512_4p77myr"
        _, data = read_vtu(root / f"{prefix}0048.vtu")
        order = np.argsort(data[:, 0])
        ax.plot(data[order, 0], data[order, 3] * PRESSURE_UNIT / 1.380649e-16,
                color=color, lw=1.4, label=f"{n0:,} cm$^{{-3}}$")
    ax.axvline(2.0, color="#555555", lw=0.9, linestyle=":")
    ax.set(xlabel="Radius (pc)", ylabel=r"Thermal pressure $P/k_B$ (K cm$^{-3}$)",
           title="End of Wolf-Rayet phase, static-gravity branch")
    ax.set_xlim(0, 35)
    ax.set_yscale("log")
    ax.grid(alpha=0.18, which="both")
    ax.legend(frameon=False)
    fig.savefig(out / names[5], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.7), constrained_layout=True)
    for grid, marker, linestyle in ((256, "o", "--"), (512, "s", "-"),
                                    (1024, "^", ":")):
        fronts = []
        densities = DENSITIES if grid != 1024 else (4000, 10000)
        for n0 in densities:
            tag = "" if grid == 256 else f"_r{grid}"
            prefix = f"ion_gravity_n{n0:05d}{tag}_0p1myr"
            age, front = front_log(root / f"{prefix}.run.log")
            fronts.append(float(np.interp(0.1, age, front)))
        ax.plot(densities, fronts, marker=marker, linestyle=linestyle, lw=1.4,
                label=f"{grid} cells")
    for grid, marker in ((1024, "^"), (2048, "D")):
        pilot = root / f"ion_gravity_n20000_r{grid}_0p1myr.run.log"
        if pilot.exists():
            age, front = front_log(pilot)
            ax.scatter([20000], [np.interp(0.1, age, front)], marker=marker,
                       s=65, facecolors="none", edgecolors="#a23d4a",
                       linewidths=1.5, label=f"20,000; {grid} cells")
    ax.set(xlabel=r"Central initial density (cm$^{-3}$)",
           ylabel="Ionization-front radius at 0.1 Myr (pc)",
           title="Short-run grid sensitivity")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False)
    fig.savefig(out / names[2], dpi=180)
    plt.close(fig)

    with (out / names[3]).open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plot(args.root, args.output)


if __name__ == "__main__":
    main()
