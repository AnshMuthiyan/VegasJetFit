#!/usr/bin/env python3
"""Audit completed BoOST p4 checkpoint fields and physics deltas."""

from __future__ import annotations

import csv
import argparse
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "VegasJetFit_wind_bubble_handoff/amrvac_simulations/analysis"))
from plot_dense_cooling_run import read_vtu  # noqa: E402


CASES = {"p4_n22": 1e-22, "p4_n23": 1e-23, "p4_n24": 1e-24}
VARIANTS = ("hydro", "cooling", "conduction", "both")


def validate(
    case: str,
    variant: str,
    base_cells: int,
    domain_scale: int,
    results_root: Path | None = None,
) -> tuple[dict[str, object], np.ndarray]:
    suffix = (
        f"_domain{domain_scale}x_{base_cells}"
        if domain_scale != 1
        else ("" if base_cells == 192 else f"_{base_cells}")
    )
    run = (results_root or ROOT / f"results_checkpoint{suffix}") / f"{case}_{variant}"
    if (run / "run.exit").read_text().strip() != "0":
        raise ValueError(f"{run}: failed guarded run")
    log = (run / "run.stdout").read_text()
    if "Finished AMRVAC in" not in log or "Loaded stellar history:" not in log:
        raise ValueError(f"{run}: no completion or BoOST load marker")
    if variant in ("cooling", "both") and "Use SPEX cooling curve" not in log:
        raise ValueError(f"{run}: cooling not active")
    if variant in ("conduction", "both") and "Spitzer HD par:" not in log:
        raise ValueError(f"{run}: conduction not active")
    files = sorted((run / "output").glob("test*.vtu"))
    if len(files) != 5:
        raise ValueError(f"{run}: expected five saved profiles, got {len(files)}")
    ages = []
    profiles = []
    for path in files:
        age, profile = read_vtu(path)
        ages.append(age)
        profiles.append(profile)
        if not np.all(np.diff(profile[:, 0]) > 0):
            raise ValueError(f"{path}: radius order")
        expected_outer = 0.19676954697354643 + domain_scale * (32.36185189733113 - 0.19676954697354643)
        if not np.isclose(profile[-1, 0], expected_outer, rtol=1e-5):
            raise ValueError(f"{path}: unexpected outer radius")
        if not np.isclose(profile[-1, 1], CASES[case], rtol=1e-4):
            raise ValueError(f"{path}: unexpected outer density")
    if not np.all(np.diff(ages) > 0) or not np.isclose(ages[-1], 0.1, rtol=1e-3):
        raise ValueError(f"{run}: unexpected ages {ages}")
    final = profiles[-1]
    interior = final[1:-1]
    row = {
        "case": case,
        "variant": variant,
        "end_age_Myr": ages[-1],
        "n_saved": len(files),
        "n_final_points": len(final),
        "min_rho_g_cm3": float(interior[:, 1].min()),
        "min_p_dyn_cm2": float(interior[:, 3].min()),
        "peak_rho_over_ISM": float(interior[:, 1].max() / CASES[case]),
        "peak_radius_pc": float(interior[interior[:, 1].argmax(), 0]),
        "median_abs_log10rho_diff_from_hydro": float("nan"),
        "max_abs_log10rho_diff_from_hydro": float("nan"),
    }
    return row, final


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
    results_root = args.results_root or ROOT / f"results_checkpoint{suffix}"
    rows = []
    for case in CASES:
        results = {}
        for variant in VARIANTS:
            path = results_root / f"{case}_{variant}" / "run.exit"
            if path.exists():
                results[variant] = validate(case, variant, args.base_cells, args.domain_scale, results_root)
        hydro = results["hydro"][1] if "hydro" in results else None
        if hydro is not None:
            radius = np.geomspace(hydro[1, 0], hydro[-2, 0], 1000)
            hydro_logrho = np.interp(radius, hydro[:, 0], np.log10(hydro[:, 1]))
        for variant in VARIANTS:
            if variant not in results:
                continue
            row, profile = results[variant]
            if hydro is not None:
                logrho = np.interp(radius, profile[:, 0], np.log10(profile[:, 1]))
                delta = np.abs(logrho - hydro_logrho)
                row["median_abs_log10rho_diff_from_hydro"] = float(np.median(delta))
                row["max_abs_log10rho_diff_from_hydro"] = float(np.max(delta))
            rows.append(row)
    if not rows:
        raise ValueError("No completed checkpoint profiles were found")
    out = args.output or ROOT / f"checkpoint_validation{suffix}.csv"
    with out.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['case']} {row['variant']}: {row['end_age_Myr']:.6f} Myr, "
            f"peak rho/ISM={row['peak_rho_over_ISM']:.3g}, "
            f"median |delta log10 rho|={row['median_abs_log10rho_diff_from_hydro']:.3g}"
        )
    print(f"Validated {len(rows)} checkpoints: {out}")


if __name__ == "__main__":
    main()
