#!/usr/bin/env python3
"""Validate complete BoOST VTUs and flag possible outer-boundary influence."""

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
    case: str, variant: str, suffix: str, domain_scale: int, results_root: Path | None = None
) -> dict[str, object]:
    run = (results_root or ROOT / f"results_full{suffix}") / f"{case}_{variant}"
    if (run / "run.exit").read_text().strip() != "0":
        raise ValueError(f"{run}: guarded run failed")
    log = (run / "run.stdout").read_text()
    if "Finished AMRVAC in" not in log or "Loaded stellar history:" not in log:
        raise ValueError(f"{run}: missing completion or BoOST marker")
    if variant in ("cooling", "both") and "Use SPEX cooling curve" not in log:
        raise ValueError(f"{run}: cooling not initialized")
    if variant in ("conduction", "both") and "Spitzer HD par:" not in log:
        raise ValueError(f"{run}: conduction not initialized")
    files = sorted((run / "output").glob("test*.vtu"))
    if len(files) != 54:
        raise ValueError(f"{run}: expected 54 saved profiles, found {len(files)}")
    ages = []
    for path in files:
        age, profile = read_vtu(path)
        ages.append(age)
        if not np.all(np.diff(profile[:, 0]) > 0):
            raise ValueError(f"{path}: unordered radii")
        expected_outer = 0.19676954697354643 + domain_scale * (32.36185189733113 - 0.19676954697354643)
        if not np.isclose(profile[-1, 0], expected_outer, rtol=1e-5):
            raise ValueError(f"{path}: unexpected outer radius")
    if not np.all(np.diff(ages) > 0) or not np.isclose(ages[-1], 5.24, rtol=1e-4):
        raise ValueError(f"{run}: unexpected ages {ages[:2]}...{ages[-2:]}")
    _, final = read_vtu(files[-1])
    outer = final[(final[:, 0] >= final[-1, 0] - 2.0) & (final[:, 0] < final[-1, 0])]
    if len(outer) < 2:
        raise ValueError(f"{run}: too few interior outer-domain points")
    max_outer_speed = float(np.max(np.abs(outer[:, 2])) / 1e5)
    return {
        "case": case,
        "variant": variant,
        "status": "complete",
        "run_exit": 0,
        "n_saved": len(files),
        "final_age_Myr": ages[-1],
        "min_final_rho_g_cm3": float(final[1:-1, 1].min()),
        "min_final_p_dyn_cm2": float(final[1:-1, 3].min()),
        "max_outer_2pc_speed_km_s": max_outer_speed,
        "outer_2pc_density_ratio_range": f"{outer[:, 1].min()/CASES[case]:.6g}:{outer[:, 1].max()/CASES[case]:.6g}",
        "boundary_influence_flag": max_outer_speed > 0.5,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-cells", type=int, choices=(192, 384, 768, 1536, 3072, 6144, 12288, 24576), default=192)
    parser.add_argument("--domain-scale", type=int, choices=(1, 2, 4, 8), default=1)
    parser.add_argument("--numerical-tag", choices=("cfl0p15",))
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
    results_root = args.results_root or ROOT / f"results_full{suffix}"
    rows = []
    failures = 0
    for case in CASES:
        for variant in VARIANTS:
            run = results_root / f"{case}_{variant}"
            if (run / "run.exit").exists():
                run_exit = int((run / "run.exit").read_text().strip())
                if run_exit:
                    failures += 1
                    rows.append({
                        "case": case,
                        "variant": variant,
                        "status": "failed",
                        "run_exit": run_exit,
                        "n_saved": len(list((run / "output").glob("test*.vtu"))),
                        "final_age_Myr": "",
                        "min_final_rho_g_cm3": "",
                        "min_final_p_dyn_cm2": "",
                        "max_outer_2pc_speed_km_s": "",
                        "outer_2pc_density_ratio_range": "",
                        "boundary_influence_flag": "",
                    })
                else:
                    rows.append(validate(case, variant, suffix, args.domain_scale, results_root))
    if not rows:
        raise ValueError("No completed full runs found")
    out = args.output or ROOT / f"full_validation{suffix}.csv"
    with out.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        if row["status"] == "failed":
            print(f"{row['case']} {row['variant']}: FAILED exit={row['run_exit']}; saved={row['n_saved']}")
        else:
            print(
                f"{row['case']} {row['variant']}: {row['final_age_Myr']:.5f} Myr, "
                f"outer speed {row['max_outer_2pc_speed_km_s']:.3g} km/s, "
                f"boundary flag={row['boundary_influence_flag']}"
            )
    print(f"Validated saved fields in {len(rows) - failures} full runs; {failures} failed: {out}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
