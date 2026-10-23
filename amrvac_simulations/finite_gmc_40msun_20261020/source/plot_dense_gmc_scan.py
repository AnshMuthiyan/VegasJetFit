#!/usr/bin/env python3
"""Plot validated finite-GMC shell checks without conflating run stages."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from validate_cloud_mass import MASS_PER_H, RHO_UNIT, profile_nh, validate
from validate_smoke import read_vtu


def unique_radial_samples(data: np.ndarray) -> np.ndarray:
    _, first, inverse = np.unique(data[:, 0], return_index=True,
                                  return_inverse=True)
    unique = data[first]
    if not np.allclose(data[:, 1:], unique[inverse, 1:], rtol=1e-6,
                       atol=1e-12):
        raise ValueError("inconsistent fields at duplicated block vertices")
    return unique


def shell_peak(data: np.ndarray, initial: np.ndarray, minimum: float,
               maximum: float) -> dict[str, float]:
    radius = data[:, 0]
    density = data[:, 1] * RHO_UNIT / MASS_PER_H
    allowed = (radius >= minimum) & (radius <= maximum)
    if np.count_nonzero(allowed) < 5:
        raise ValueError("shell search interval has too few native samples")
    position = np.where(allowed)[0]
    excess = density - initial
    peak = int(position[np.argmax(excess[allowed])])
    if excess[peak] <= 0:
        raise ValueError("no positive density excess")
    half = excess[peak] / 2.0
    left = peak
    right = peak
    while left > position[0] and excess[left] > half:
        left -= 1
    while right < position[-1] and excess[right] > half:
        right += 1
    if left == position[0] or right == position[-1]:
        raise ValueError("shell FWHM extends outside search interval")
    rleft = radius[left] + (half - excess[left]) * (
        radius[left + 1] - radius[left]) / (excess[left + 1] - excess[left])
    rright = radius[right - 1] + (half - excess[right - 1]) * (
        radius[right] - radius[right - 1]) / (excess[right] - excess[right - 1])
    width = float(rright - rleft)
    local_dx = float((radius[peak + 1] - radius[peak - 1]) / 2.0)
    return dict(shell_peak_pc=float(radius[peak]),
                shell_fwhm_pc=width, shell_fwhm_cells=width / local_dx,
                shell_contrast=float(density[peak] / initial[peak]))


def inner_rise(radius: np.ndarray, density: np.ndarray,
               peak_pc: float, minimum_radius_pc: float = 0.05) -> dict[str, float]:
    """Measure the local inner swept-shell rise, before any broad outer crest.

    Local pre-jump and shell levels bracket the contiguous positive-gradient
    run around the steepest inner-side jump. Crossing fractions are linear in
    n_H; this does not measure any shallower precursor farther inward.
    """
    if len(radius) < 8 or not np.all(np.diff(radius) > 0):
        raise ValueError("radius must contain ordered native samples")
    if not np.all(np.isfinite(density)) or np.any(density <= 0):
        raise ValueError("density must be finite and positive")
    peak = int(np.argmin(np.abs(radius - peak_pc)))
    gradient = np.diff(density) / np.diff(radius)
    candidates = np.where((radius[:-1] >= max(minimum_radius_pc, 0.5 * peak_pc))
                          & (np.arange(len(gradient)) < peak)
                          & (density[1:] >= 0.1 * density[peak])
                          & (density[:-1] < 0.9 * density[peak]))[0]
    if not len(candidates):
        raise ValueError("no inner-side shell jump candidate")
    steepest = int(candidates[np.argmax(gradient[candidates])])
    if gradient[steepest] <= 0:
        raise ValueError("no positive inner-side shell jump")
    cutoff = 0.05 * gradient[steepest]
    left = steepest
    while left > 0 and gradient[left - 1] > cutoff:
        left -= 1
    right = steepest
    while right + 1 < peak and gradient[right + 1] > cutoff:
        right += 1
    low, high = float(density[left]), float(density[right + 1])
    if high <= 3.0 * low or high < 0.5 * density[peak]:
        raise ValueError("inner jump does not reach the selected shell")
    segment = np.maximum.accumulate(density[left:right + 2])
    radii = radius[left:right + 2]

    def crossing(fraction: float) -> float:
        target = low + fraction * (high - low)
        upper = int(np.searchsorted(segment, target, side="left"))
        if not 0 < upper < len(segment):
            raise ValueError("inner-rise crossing is not bracketed")
        lower = upper - 1
        return float(radii[lower] + (target - segment[lower]) *
                     (radii[upper] - radii[lower]) /
                     (segment[upper] - segment[lower]))

    r10, r50, r90 = (crossing(level) for level in (0.1, 0.5, 0.9))
    local_dx = float(radius[steepest + 1] - radius[steepest])
    return {"inner_radius_pc": r10, "inner_midrise_pc": r50,
            "inner_rise_90_pc": r90, "inner_ramp_pc": r90 - r10,
            "inner_ramp_cells": (r90 - r10) / local_dx,
            "inner_local_dx_pc": local_dx,
            "prejump_nh_cm3": low, "shell_inner_nh_cm3": high,
            "shell_peak_nh_cm3": float(density[peak]),
            "inner_jump_contrast": high / low}


def products(manifest: Path, results: Path, stage: str, output: Path,
             selected: str | None) -> None:
    with manifest.open(newline="", encoding="ascii") as stream:
        cases = [row for row in csv.DictReader(stream)
                 if row["stage"] == stage
                 and (selected is None or row["case"] == selected)]
    if not cases:
        raise ValueError("no matching cases")
    rows = []
    profiles = []
    for case in cases:
        prefix = case["case"]
        n_ref = float(case["n_ref_cm3"])
        n_gmc = float(case["n_gmc_cm3"])
        inner = float(case["inner_pc"])
        domain = float(case["domain_max_pc"])
        reference_outer = float(case.get("atmosphere_outer_pc") or domain)
        search_min = 0.05 if domain >= 10.0 else inner + 4 * float(case["first_width_pc"])
        search_max = (10.0 if stage == "wind" else 18.0) if domain >= 10.0 else 0.8 * domain
        endpoint = float(case["endpoint_myr"])
        root = results / f"n{int(n_ref):05d}b{int(n_gmc):04d}" / stage
        check = validate(root, prefix, n_ref, endpoint,
                         int(case["expected_vtus"]), False, 0.5, 2.0, 1.8,
                         40.0, domain, inner, n_gmc, True, 10.0, 15.0, 1.0,
                         expected_mdot_msun_yr=1e-5 if stage == "wind" else None,
                         atmosphere_outer_pc=reference_outer)
        last = unique_radial_samples(
            read_vtu(root / f"{prefix}{int(case['expected_vtus']) - 1:04d}.vtu")[1])
        initial = profile_nh(last[:, 0], n_ref, 0.5, 2.0, 1.8,
                             n_bg=n_gmc, finite_gmc=True,
                             n_ext=10.0, gmc_pc=15.0, gmc_edge_width=1.0)
        shell = shell_peak(last, initial, search_min, search_max)
        try:
            rise = inner_rise(last[:, 0], last[:, 1] * RHO_UNIT / MASS_PER_H,
                              shell["shell_peak_pc"], search_min)
            rise_status = "measured"
        except ValueError as error:
            rise = {}
            rise_status = f"ambiguous: {error}"
        rows.append({**check, **shell, **rise, "inner_edge_status": rise_status,
                     "inner_ramp_resolved": (rise.get("inner_ramp_cells", 0) >= 5),
                     "stage": stage,
                     "n_gmc_cm3": n_gmc,
                     "adequately_sampled": (check["initial_front_elements"] >= 10
                                            and shell["shell_fwhm_cells"] >= 5)})
        profiles.append((case, last, initial, shell, rise))
    rows.sort(key=lambda row: row["n_ref_cm3"])
    output.mkdir(parents=True, exist_ok=False)
    with (output / "shell_metrics.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(
            key for row in rows for key in row)))
        writer.writeheader()
        writer.writerows(rows)

    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    for row in rows:
        radius = row.get("inner_radius_pc", row["shell_peak_pc"])
        ax.scatter(row["n_ref_cm3"], radius,
                   marker="o" if row["adequately_sampled"] and row["inner_edge_status"] == "measured" else "x", s=55,
                   color="#a33445")
    if len(rows) > 1:
        ax.plot([row["n_ref_cm3"] for row in rows],
                [row.get("inner_radius_pc", row["shell_peak_pc"]) for row in rows],
                color="#a33445", alpha=0.55)
    ax.set(xscale="log", yscale="log",
           xlabel=r"Core $n_{\rm ref}$ at 1 pc (cm$^{-3}$)",
           ylabel="Inner 10% rise (pc); x marks ambiguous cases",
           title=rf"40 $M_\odot$ wind, {stage}, {rows[0]['age_myr']:.2f} Myr")
    ax.grid(alpha=0.25)
    fig.savefig(output / "shell_radius_vs_core_density.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    colors = plt.cm.viridis(np.linspace(0.1, 0.85, len(profiles)))
    for (case, data, initial, shell, rise), color in zip(profiles, colors, strict=True):
        density = data[:, 1] * RHO_UNIT / MASS_PER_H
        label = f"core {case['n_ref_cm3']}, GMC {case['n_gmc_cm3']}"
        ax.plot(data[:, 0], density, color=color, label=label)
        ax.plot(data[:, 0], initial, color=color, linestyle=":", alpha=0.7)
        ax.axvline(shell["shell_peak_pc"], color=color, linestyle="--", alpha=0.7)
        if rise:
            ax.axvline(rise["inner_radius_pc"], color=color, linestyle="-", alpha=0.7)
    ax.set(xlim=(0, 10.0 if stage == "wind" else 18.0), yscale="log",
           xlabel="Radius (pc)", ylabel=r"$n_{\rm H}$ (cm$^{-3}$)",
           title="Saved density; dotted initial, dashed peak, solid inner edge")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(output / "density_profiles.png", dpi=180)
    plt.close(fig)
    print(f"Validated {len(rows)} {stage} cases and wrote {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("stage", choices=("wind", "full"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--case", help="Plot only one completed case")
    args = parser.parse_args()
    products(args.manifest, args.results, args.stage, args.output, args.case)
