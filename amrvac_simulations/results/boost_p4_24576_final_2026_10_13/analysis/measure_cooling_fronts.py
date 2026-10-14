#!/usr/bin/env python3
"""Measure the native inner density front in complete 4x-domain controls."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
GRBS = ROOT.parents[1]
sys.path.insert(0, str(GRBS / "VegasJetFit_wind_bubble_handoff/amrvac_simulations/analysis"))
from plot_dense_cooling_run import read_vtu  # noqa: E402


PC_CM = 3.0856775814913673e18
MSUN_G = 1.98847e33
CASES = ("p4_n22", "p4_n23", "p4_n24")


def crossing(radius: np.ndarray, log_rho: np.ndarray, front: float, level: float) -> float:
    midpoint = (radius[:-1] + radius[1:]) / 2
    candidates = np.flatnonzero(
        (radius[:-1] > front - 0.5)
        & (radius[1:] < front + 0.5)
        & (log_rho[:-1] <= level)
        & (log_rho[1:] > level)
    )
    if not len(candidates):
        return math.nan
    i = candidates[np.argmin(np.abs(midpoint[candidates] - front))]
    fraction = (level - log_rho[i]) / (log_rho[i + 1] - log_rho[i])
    return float(radius[i] + fraction * (radius[i + 1] - radius[i]))


def measure(run: Path) -> dict[str, float]:
    if (run / "run.exit").read_text().strip() != "0":
        raise ValueError(f"{run}: failed run")
    if "Finished AMRVAC in" not in (run / "run.stdout").read_text():
        raise ValueError(f"{run}: normal completion marker missing")
    files = sorted((run / "output").glob("test*.vtu"))
    if len(files) != 54:
        raise ValueError(f"{run}: expected 54 VTUs, found {len(files)}")
    age, profile = read_vtu(files[-1])
    if not np.isclose(age, 5.24, atol=0.001):
        raise ValueError(f"{run}: final age {age} Myr")

    radius, rho = profile[:, 0], profile[:, 1]
    mid = (radius[:-1] + radius[1:]) / 2
    dr = np.diff(radius)
    log_rho = np.log10(rho)
    slope = np.diff(log_rho) / dr
    inner = np.flatnonzero((mid > 2.0) & (mid < 30.0) & (slope > 0))
    if not len(inner):
        raise ValueError(f"{run}: no rising inner front in 2-30 pc")
    i = inner[np.argmax(slope[inner])]
    front = float(mid[i])
    below = log_rho[(radius > front - 0.5) & (radius < front - 0.2)]
    above = log_rho[(radius > front + 0.2) & (radius < front + 0.5)]
    if not len(below) or not len(above):
        raise ValueError(f"{run}: insufficient native samples around front")
    low, high = float(np.median(below)), float(np.median(above))
    r10 = crossing(radius, log_rho, front, low + 0.1 * (high - low))
    r90 = crossing(radius, log_rho, front, low + 0.9 * (high - low))

    metadata = (run / "RUN.txt").read_text()
    match = re.search(r"rho_ISM=([\d.+-]+[dDeE][+-]?\d+)\s+g/cm\^3", metadata)
    if match is None:
        raise ValueError(f"{run}: ambient density missing")
    rho_ism = float(match.group(1).replace("d", "e").replace("D", "E"))
    ambient_mass = 4 * math.pi / 3 * rho_ism * (front * PC_CM) ** 3 / MSUN_G
    return {
        "age_Myr": float(age),
        "front_radius_pc": front,
        "native_spacing_pc": float(dr[i]),
        "front_log10rho_slope_dex_per_pc": float(slope[i]),
        "rho_outside_over_inside": 10 ** (high - low),
        "front_width_10to90_pc": r90 - r10,
        "front_width_native_cells": (r90 - r10) / dr[i],
        "rho_ISM_g_cm3": rho_ism,
        "initial_ambient_mass_inside_front_Msun": ambient_mass,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=int, nargs="+", choices=(1536, 3072, 6144, 12288, 24576), required=True)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=CASES)
    parser.add_argument("--platform", choices=("vm", "mac"), default="vm")
    parser.add_argument("--variant", choices=("cooling", "hydro"), default="cooling")
    parser.add_argument("--output", type=Path, help="write a distinct native-front CSV")
    args = parser.parse_args()
    cells = sorted(set(args.cells))
    rows: list[dict[str, float | int | str]] = []
    for case in args.cases:
        for n in cells:
            prefix = "results_mac_full" if args.platform == "mac" else "results_full"
            run = ROOT / f"{prefix}_domain4x_{n}" / f"{case}_{args.variant}"
            if not (run / "run.exit").exists():
                print(f"{case}/{n}: waiting for complete run")
                continue
            row = {"case": case, "base_cells": n, **measure(run)}
            rows.append(row)
            print(f"{case}/{n}: front={row['front_radius_pc']:.4f} pc")
    if not rows:
        return
    label = "vs".join(str(n) for n in cells)
    platform_tag = "mac_" if args.platform == "mac" else ""
    out = ROOT / f"{args.variant}_inner_front_{platform_tag}{label}_domain4x.csv"
    out = args.output or out
    with out.open("x" if args.output else "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} native-front measurements to {out}")


if __name__ == "__main__":
    main()
