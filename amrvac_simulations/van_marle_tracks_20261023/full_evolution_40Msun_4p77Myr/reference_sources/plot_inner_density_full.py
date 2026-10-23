#!/usr/bin/env python3
"""Plot complete 20k/40k runs on the separate 0.01 pc inner-boundary grid."""

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


def plot(root: Path, output: Path) -> None:
    cases = []
    for n0 in (20000, 40000):
        for branch in ("gravity", "nogravity"):
            prefix = f"ion_{branch}_n{n0:05d}_inner0p01_r1024_4p77myr"
            if not (root / f"{prefix}0048.vtu").exists():
                raise FileNotFoundError(f"missing full endpoint: {prefix}")
            cases.append((n0, branch, prefix))
    output.mkdir(parents=True, exist_ok=True)
    names = ("front_history.png", "wr_density.png", "wr_pressure.png",
             "full_summary.csv")
    for name in names:
        if (output / name).exists():
            raise FileExistsError(output / name)

    colors = {20000: "#19778c", 40000: "#ad384f"}
    field_labels = {"gravity": "fixed g(r)", "nogravity": "no g"}
    rows = []
    fig, ax = plt.subplots(figsize=(8.5, 5), constrained_layout=True)
    for n0, branch, prefix in cases:
        age, front = front_log(root / f"{prefix}.run.log")
        ax.plot(age, front, color=colors[n0],
                linestyle="-" if branch == "gravity" else "--", lw=1.5,
                label=f"{n0:,} cm$^{{-3}}$, {field_labels[branch]}")
        radius, nh = density_profile(root / f"{prefix}0048.vtu")
        shell_mask = (radius >= 2) & (radius < 35)
        rows.append({
            "n0_cm3": n0,
            "grid_cells": 1024,
            "inner_radius_pc": 0.01,
            "field_branch": "prescribed_g" if branch == "gravity" else "none",
            "initial_front_analytic_pc": expected_front(n0, 0.01),
            "front_0p1myr_pc": float(np.interp(0.1, age, front)),
            "pre_rsg_front_pc": float(front[age < 4.3][-1]),
            "rsg_min_ionization_front_pc": float(np.min(front[(age >= 4.3) & (age < 4.5)])),
            "last_logged_age_myr": float(age[-1]),
            "last_logged_front_pc": float(front[-1]),
            "wr_shell_peak_pc": float(radius[shell_mask][np.argmax(nh[shell_mask])]),
        })
    ax.axhline(2, color="#666666", linestyle=":", lw=0.9)
    ax.axvspan(4.3, 4.5, color="#d9d9d9", alpha=0.5, zorder=0)
    for phase_age in (4.3, 4.5):
        ax.axvline(phase_age, color="#666666", linestyle=":", lw=0.9)
    ax.text(4.4, 0.96, "RSG: photons off", rotation=90, ha="center", va="top",
            transform=ax.get_xaxis_transform(), fontsize=8)
    ax.set(xlabel="Stellar age (Myr)", ylabel="Sharp H II front (pc; not bubble wall)",
           title="40 solar-mass wind; 0.01 pc inner boundary")
    ax.set_xlim(0, 4.77)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, ncol=2, fontsize=8)
    fig.savefig(output / names[0], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5), constrained_layout=True)
    for n0, branch, prefix in cases:
        radius, nh = density_profile(root / f"{prefix}0048.vtu")
        ax.plot(radius, nh, color=colors[n0], lw=1.5,
                linestyle="-" if branch == "gravity" else "--",
                label=f"{n0:,} cm$^{{-3}}$, {field_labels[branch]}")
    ax.axvline(2, color="#666666", linestyle=":", lw=0.9)
    ax.set(xlabel="Radius (pc)", ylabel=r"Hydrogen nuclei density (cm$^{-3}$)",
           title="WR endpoint density: field vs no field")
    ax.set_xlim(0, 35)
    ax.set_yscale("log")
    ax.grid(alpha=0.2, which="both")
    ax.legend(frameon=False)
    fig.savefig(output / names[1], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5), constrained_layout=True)
    for n0, branch, prefix in cases:
        _, data = read_vtu(root / f"{prefix}0048.vtu")
        order = np.argsort(data[:, 0])
        ax.plot(data[order, 0], data[order, 3] * PRESSURE_UNIT / 1.380649e-16,
                color=colors[n0], lw=1.5,
                linestyle="-" if branch == "gravity" else "--",
                label=f"{n0:,} cm$^{{-3}}$, {field_labels[branch]}")
    ax.axvline(2, color="#666666", linestyle=":", lw=0.9)
    ax.set(xlabel="Radius (pc)", ylabel=r"Thermal pressure $P/k_B$ (K cm$^{-3}$)",
           title="WR endpoint thermal pressure: field vs no field")
    ax.set_xlim(0, 35)
    ax.set_yscale("log")
    ax.grid(alpha=0.2, which="both")
    ax.legend(frameon=False)
    fig.savefig(output / names[2], dpi=180)
    plt.close(fig)

    with (output / names[3]).open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows and three PNGs to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plot(args.root, args.output)


if __name__ == "__main__":
    main()
