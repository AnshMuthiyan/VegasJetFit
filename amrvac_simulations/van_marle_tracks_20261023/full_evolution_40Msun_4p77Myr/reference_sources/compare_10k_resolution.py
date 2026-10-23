#!/usr/bin/env python3
"""Compare matched 10k full runs on 512 and 1024 stretched cells."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_evolving import front_log
from validate_smoke import PRESSURE_UNIT, read_vtu


def native_profile(data: np.ndarray, field: int) -> tuple[np.ndarray, np.ndarray]:
    radius, inverse = np.unique(data[:, 0], return_inverse=True)
    mean = np.bincount(inverse, weights=data[:, field]) / np.bincount(inverse)
    return radius, mean


def shell_peak(data: np.ndarray) -> float:
    radius, rho = native_profile(data, 1)
    mask = (radius > 2.0) & (radius < 35.0)
    peak = float(np.max(rho[mask]))
    ambient = float(np.median(rho[radius > 35.0]))
    if peak < 1.2 * ambient:
        return float("nan")
    return float(radius[mask][np.argmax(rho[mask])])


def pressure_at_10pc(data: np.ndarray) -> float:
    radius, pressure = native_profile(data, 3)
    return float(np.interp(10.0, radius, pressure) * PRESSURE_UNIT / 1.380649e-16)


def compare(root: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "resolution_10k_matched_ages.csv"
    front_plot = out / "resolution_10k_front_difference.png"
    shell_plot = out / "resolution_10k_shell_difference.png"
    for path in (csv_path, front_plot, shell_plot):
        if path.exists():
            raise FileExistsError(path)
    rows = []
    for branch in ("gravity", "nogravity"):
        prefixes = {cells: f"ion_{branch}_n10000_r{cells}_4p77myr"
                    for cells in (512, 1024)}
        fronts = {cells: front_log(root / f"{prefix}.run.log")
                  for cells, prefix in prefixes.items()}
        for index in range(49):
            saves = {cells: read_vtu(root / f"{prefix}{index:04d}.vtu")
                     for cells, prefix in prefixes.items()}
            ages = {cells: age_yr * (365.25 / 365.0) / 1.0e6
                    for cells, (age_yr, _) in saves.items()}
            if not np.isclose(ages[512], ages[1024], atol=2e-5):
                raise ValueError(f"save {index}: unmatched ages {ages}")
            age = ages[512]
            row: dict[str, float | str | int] = {
                "branch": branch, "save": index, "age_myr": age,
            }
            # Front logs have different time grids; interpolate only away from
            # the two abrupt photon/wind switches.
            at_switch = min(abs(age - 4.3), abs(age - 4.5)) < 2e-5
            for cells in (512, 1024):
                time, front = fronts[cells]
                data = saves[cells][1]
                row[f"front_r{cells}_pc"] = (
                    float("nan") if at_switch else float(np.interp(age, time, front))
                )
                row[f"shell_peak_r{cells}_pc"] = shell_peak(data)
                row[f"pressure_10pc_r{cells}_K_cm3"] = pressure_at_10pc(data)
            row["front_abs_diff_pc"] = abs(
                row["front_r1024_pc"] - row["front_r512_pc"]
            )
            row["shell_abs_diff_pc"] = abs(
                row["shell_peak_r1024_pc"] - row["shell_peak_r512_pc"]
            )
            rows.append(row)
    with csv_path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    for name, y_key, ylabel, target in (
        ("Front", "front_abs_diff_pc", "Absolute front difference (pc)", front_plot),
        ("Shell peak", "shell_abs_diff_pc", "Absolute shell-peak difference (pc)", shell_plot),
    ):
        fig, ax = plt.subplots(figsize=(8.2, 4.7), constrained_layout=True)
        for branch, color in (("gravity", "#19778c"), ("nogravity", "#bb7124")):
            branch_rows = [row for row in rows if row["branch"] == branch]
            ax.plot([row["age_myr"] for row in branch_rows],
                    [row[y_key] for row in branch_rows], marker="o", ms=3,
                    color=color, lw=1.2, label=branch)
        for phase_age in (4.3, 4.5):
            ax.axvline(phase_age, color="#777777", lw=0.8, linestyle=":")
        ax.set(xlabel="Stellar age (Myr)", ylabel=ylabel,
               title=f"10,000 cm$^{{-3}}$: {name.lower()} grid difference")
        ax.set_xlim(0, 4.77)
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.18)
        ax.legend(frameon=False)
        fig.savefig(target, dpi=180)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    compare(args.root, args.output)


if __name__ == "__main__":
    main()
