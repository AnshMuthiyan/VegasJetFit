#!/usr/bin/env python3
"""Validate BoOST p4 smoke outputs and compare the hydro initial state."""

from __future__ import annotations

import csv
import argparse
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
GRBS = ROOT.parents[1]
sys.path.insert(0, str(GRBS / "VegasJetFit_wind_bubble_handoff/amrvac_simulations/analysis"))
from plot_dense_cooling_run import read_vtu  # noqa: E402


CASES = {"p4_n22": 1e-22, "p4_n23": 1e-23, "p4_n24": 1e-24}
VARIANTS = ("hydro", "cooling", "conduction", "both")


def validate(
    case: str,
    variant: str,
    base_cells: int,
    domain_scale: int,
    results_root: Path | None = None,
    numerical_tag: str | None = None,
) -> dict[str, str | float]:
    suffix = (
        f"_domain{domain_scale}x_{base_cells}"
        if domain_scale != 1
        else ("" if base_cells == 192 else f"_{base_cells}")
    )
    if numerical_tag is not None:
        suffix += f"_{numerical_tag}"
    run = (results_root or ROOT / f"results_smoke{suffix}") / f"{case}_{variant}"
    if (run / "run.exit").read_text().strip() != "0":
        raise ValueError(f"{run}: nonzero guarded exit")
    log = (run / "run.stdout").read_text()
    if "Finished AMRVAC in" not in log:
        raise ValueError(f"{run}: missing completion marker")
    if "Loaded stellar history:" not in log or "Unique ages:" not in log:
        raise ValueError(f"{run}: BoOST table not loaded")
    if variant in ("cooling", "both") and "Use SPEX cooling curve" not in log:
        raise ValueError(f"{run}: cooling did not initialize")
    if variant in ("conduction", "both") and "Spitzer HD par:" not in log:
        raise ValueError(f"{run}: conduction did not initialize")

    snapshots = sorted((run / "output").glob("test*.vtu"))
    if len(snapshots) != 3:
        raise ValueError(f"{run}: expected three VTUs, got {len(snapshots)}")
    times = []
    for snapshot in snapshots:
        age_myr, profile = read_vtu(snapshot)
        times.append(age_myr)
        if not np.all(np.diff(profile[:, 0]) > 0):
            raise ValueError(f"{snapshot}: unordered radii")
        if not np.isclose(profile[0, 0], 0.19676954697354643, rtol=1e-5):
            raise ValueError(f"{snapshot}: unexpected inner edge")
        expected_outer = 0.19676954697354643 + domain_scale * (32.36185189733113 - 0.19676954697354643)
        if not np.isclose(profile[-1, 0], expected_outer, rtol=1e-5):
            raise ValueError(f"{snapshot}: unexpected outer edge")
        if not np.isclose(profile[-1, 1], CASES[case], rtol=1e-4):
            raise ValueError(f"{snapshot}: outer density changed")
    if not np.all(np.diff(times) > 0) or not np.isclose(times[-1], 0.00097847, rtol=1e-3):
        raise ValueError(f"{run}: unexpected saved ages {times}")

    _, initial = read_vtu(snapshots[0])
    _, final = read_vtu(snapshots[-1])
    return {
        "case": case,
        "variant": variant,
        "age_myr": times[-1],
        "initial_outer_rho_g_cm3": initial[-1, 1],
        "initial_outer_p_dyn_cm2": initial[-1, 3],
        "initial_inner_rho_g_cm3": initial[0, 1],
        "final_min_rho_g_cm3": float(final[:, 1].min()),
        "final_min_p_dyn_cm2": float(final[:, 3].min()),
        "final_points": len(final),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-cells", type=int, choices=(192, 384, 768, 1536, 3072, 6144, 12288, 24576), default=192)
    parser.add_argument("--domain-scale", type=int, choices=(1, 2, 4, 8), default=1)
    parser.add_argument("--numerical-tag", choices=("sts0p4", "cfl0p15"))
    parser.add_argument("--results-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.results_root and not args.output:
        parser.error("--results-root requires --output to preserve the default validation CSV")
    if args.domain_scale == 2 and args.base_cells not in (384, 768):
        parser.error("domain-scale 2 supports 384 or 768 base cells")
    if args.domain_scale == 4 and args.base_cells not in (1536, 3072, 6144, 12288, 24576):
        parser.error("domain-scale 4 supports 1536, 3072, 6144, 12288, or 24576 base cells")
    if args.domain_scale == 8 and args.base_cells != 3072:
        parser.error("domain-scale 8 requires 3072 base cells")
    suffix = (
        f"_domain{args.domain_scale}x_{args.base_cells}"
        if args.domain_scale != 1
        else ("" if args.base_cells == 192 else f"_{args.base_cells}")
    )
    if args.numerical_tag is not None:
        suffix += f"_{args.numerical_tag}"
    results_root = args.results_root or ROOT / f"results_smoke{suffix}"
    rows = [
        validate(case, variant, args.base_cells, args.domain_scale, results_root, args.numerical_tag)
        for case in CASES
        for variant in VARIANTS
        if (results_root / f"{case}_{variant}" / "run.exit").exists()
    ]
    if not rows:
        raise ValueError(f"No {args.base_cells}-cell smoke results found")
    out = args.output or ROOT / f"smoke_validation{suffix}.csv"
    with out.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['case']} {row['variant']}: "
            f"t={row['age_myr']:.6f} Myr, "
            f"min rho={row['final_min_rho_g_cm3']:.3g}, "
            f"min p={row['final_min_p_dyn_cm2']:.3g}"
        )
    print(f"Validated {len(rows)} smoke cases: {out}")


if __name__ == "__main__":
    main()
