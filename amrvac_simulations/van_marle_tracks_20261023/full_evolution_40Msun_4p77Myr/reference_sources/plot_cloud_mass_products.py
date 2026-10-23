#!/usr/bin/env python3
"""Validate one completed cloud-mass stage and create its standard products."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np

from validate_cloud_mass import (
    MASS_PER_H, PRESSURE_UNIT, RHO_UNIT,
    atmosphere_table, profile_nh, validate,
)
from validate_smoke import read_vtu


def shell_measure(data: np.ndarray, n_ref: float, edge_width: float,
                  stage: str, domain_max_pc: float, cloud_pc: float = 2.0,
                  slope: float = 1.8) -> dict:
    order = np.argsort(data[:, 0])
    radius = data[order, 0]
    nh = data[order, 1] * RHO_UNIT / MASS_PER_H
    pressure = data[order, 3] * PRESSURE_UNIT
    initial = profile_nh(radius, n_ref, edge_width, cloud_pc, slope)
    inner = 0.2 if stage == "wind" else 2.0
    upper = min(35.0, domain_max_pc - 5.0) if stage == "wind" else domain_max_pc - 5.0
    mask = (radius >= inner) & (radius <= upper)
    if not np.any(mask):
        raise ValueError("no saved points in shell search interval")
    search_r = radius[mask]
    search_nh = nh[mask]
    search_initial = initial[mask]
    search_pressure = pressure[mask]
    excess = search_nh - search_initial
    if np.max(excess) <= 0:
        raise ValueError("no positive density excess to identify a shell")
    index = int(np.argmax(excess))
    half_peak = 0.5 * excess[index]
    left = index
    while left > 0 and excess[left] > half_peak:
        left -= 1
    right = index
    while right < len(excess) - 1 and excess[right] > half_peak:
        right += 1
    if left == 0 or right == len(excess) - 1:
        width = float("nan")
    else:
        left_radius = float(np.interp(half_peak, excess[left:left + 2],
                                      search_r[left:left + 2]))
        right_radius = float(np.interp(half_peak, excess[right - 1:right + 1][::-1],
                                       search_r[right - 1:right + 1][::-1]))
        width = right_radius - left_radius
    unique_r = np.unique(search_r)
    near = int(np.clip(np.searchsorted(unique_r, search_r[index]), 1, len(unique_r) - 2))
    local_dx = 0.5 * (unique_r[near + 1] - unique_r[near - 1])
    return dict(shell_peak_pc=float(search_r[index]),
                shell_peak_nh_cm3=float(search_nh[index]),
                shell_excess_nh_cm3=float(excess[index]),
                shell_width_fwhm_pc=width,
                shell_width_elements=float(width / local_dx),
                shell_contrast_to_initial=float(search_nh[index] / search_initial[index]),
                shell_peak_pressure_dyn_cm2=float(search_pressure[index]))


def products(manifest: Path, results: Path, stage: str, output: Path,
             selected_case: str | None = None) -> None:
    with manifest.open(newline="", encoding="ascii") as stream:
        cases = [row for row in csv.DictReader(stream)
                 if row["stage"] == stage
                 and (selected_case is None or row["case"] == selected_case)]
    if not 1 <= len(cases) <= 4 or (len(cases) == 1 and selected_case is None):
        raise ValueError(f"expected two to four independent {stage} cases, or one selected case")
    rows = []
    density_data = []
    for case in cases:
        prefix = case["case"]
        n_ref = float(case["n_ref_cm3"])
        edge_width = float(case["edge_width_pc"])
        domain_max_pc = float(case.get("domain_max_pc", 40.0))
        root = results / f"nref{int(n_ref):04d}" / stage
        check = validate(root, prefix, n_ref, float(case["endpoint_myr"]),
                         int(case["expected_vtus"]), False, edge_width,
                         domain_max_pc=domain_max_pc)
        last = read_vtu(root / f"{prefix}{int(case['expected_vtus']) - 1:04d}.vtu")[1]
        shell = shell_measure(last, n_ref, edge_width, stage, domain_max_pc)
        rows.append({**check, "stage": stage,
                     "initial_central_nh_cm3": float(profile_nh(
                         np.array([0.0]), n_ref, edge_width)[0]),
                     "initial_1pc_nh_cm3": float(profile_nh(
                         np.array([1.0]), n_ref, edge_width)[0]),
                     **shell,
                     "shell_search_min_pc": 0.2 if stage == "wind" else 2.0,
                     "shell_search_max_pc": min(35.0, domain_max_pc - 5.0)
                     if stage == "wind" else domain_max_pc - 5.0})
        unresolved = (check["initial_front_elements"] < 10 or
                      shell["shell_width_elements"] < 5)
        density_data.append((n_ref, last, shell["shell_peak_pc"], unresolved))
    rows.sort(key=lambda item: item["n_ref_cm3"])
    output.mkdir(parents=True, exist_ok=False)
    with (output / "shell_radius_vs_density.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(7.0, 4.8), constrained_layout=True)
    if len(rows) > 1:
        ax.plot([r["n_ref_cm3"] for r in rows], [r["shell_peak_pc"] for r in rows],
                color="#a33445", linewidth=1.7)
    for row in rows:
        unresolved = (row["initial_front_elements"] < 10 or
                      row["shell_width_elements"] < 5)
        ax.scatter(row["n_ref_cm3"], row["shell_peak_pc"], s=48,
                   facecolors="white" if unresolved else "#a33445",
                   edgecolors="#a33445", linewidths=1.6, zorder=3)
    if any(r["initial_front_elements"] < 10 or r["shell_width_elements"] < 5
           for r in rows):
        ax.scatter([], [], s=48, facecolors="white", edgecolors="#a33445",
                   linewidths=1.6, label="Under-resolved H II or shell")
        ax.legend(frameon=False, fontsize=8)
    ax.set(xscale="log", xlabel=r"Untapered $n_{ref}$ at 1 pc (cm$^{-3}$)",
           ylabel="Native density-excess shell peak (pc)",
           title=f"40 solar-mass wind, {float(cases[0]['endpoint_myr']):.2f} Myr"
                 + (" (single case)" if len(rows) == 1 else ""))
    ax.set_xticks([r["n_ref_cm3"] for r in rows],
                  labels=[f"{r['n_ref_cm3']:g}" for r in rows])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.grid(alpha=0.25)
    fig.savefig(output / "shell_radius_vs_density.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 5.2), constrained_layout=True)
    colors = ("#2b6f7b", "#cd7c28", "#a33445", "#483c87")
    for (n_ref, data, shell, unresolved), color in zip(
            density_data, colors[:len(cases)], strict=True):
        order = np.argsort(data[:, 0])
        radius = data[order, 0]
        nh = data[order, 1] * RHO_UNIT / MASS_PER_H
        note = " (under-resolved)" if unresolved else ""
        ax.plot(radius, nh, color=color, label=f"{n_ref:g} cm$^{{-3}}${note}")
        ax.plot(radius, profile_nh(radius, n_ref, 0.5), color=color,
                linestyle=":", linewidth=1.0, alpha=0.6)
        ax.axvline(shell, color=color, linestyle="--", linewidth=0.8, alpha=0.75)
    ax.set(yscale="log", xlim=(0, 8 if stage == "wind" else
                              float(cases[0].get("domain_max_pc", 40.0)) - 5.0),
           xlabel="Radius (pc)", ylabel=r"$n_H$ (cm$^{-3}$)",
           title="Saved density; dotted: initial, dashed: measured shell")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(output / "density_profiles_and_shells.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.4), constrained_layout=True)
    for case, color in zip(cases, colors[:len(cases)], strict=True):
        n_ref = float(case["n_ref_cm3"])
        radial, mass, g, pressure = atmosphere_table(
            n_ref, float(case["edge_width_pc"]),
            domain_max_pc=float(case.get("domain_max_pc", 40.0)))
        stride = slice(None, None, 50)
        axes[0, 0].plot(radial[stride], profile_nh(radial[stride], n_ref, 0.5),
                        color=color, label=f"{n_ref:g}")
        axes[0, 1].plot(radial[stride], (mass[stride] - 40.0 * 1.98847e33) / 1.98847e33,
                        color=color)
        axes[1, 0].plot(radial[stride], -g[stride], color=color)
        axes[1, 1].plot(radial[stride], pressure[stride], color=color)
    for ax in axes.flat:
        ax.set_xscale("log")
        ax.grid(alpha=0.2)
        ax.set_xlabel("Radius (pc)")
    axes[0, 0].set(yscale="log", ylabel=r"Initial $n_H$ (cm$^{-3}$)")
    axes[0, 0].legend(title=r"Untapered $n_{ref}$", frameon=False, fontsize=8)
    axes[0, 1].set(yscale="log", ylabel=r"Enclosed cloud excess mass ($M_\odot$)")
    axes[1, 0].set(yscale="log", ylabel=r"Inward $|g|$ (cm s$^{-2}$)")
    axes[1, 1].set(yscale="log", ylabel=r"Initial support $P$ (dyn cm$^{-2}$)")
    fig.suptitle("Fixed initial potential: 40 solar-mass star plus tapered cloud excess")
    fig.savefig(output / "cloud_structure.png", dpi=180)
    plt.close(fig)
    print(f"Validated {len(rows)} cases; wrote standard products to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("stage", choices=("wind", "full"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--case", help="Select one validated case without implying a density trend")
    args = parser.parse_args()
    products(args.manifest, args.results, args.stage, args.output, args.case)
