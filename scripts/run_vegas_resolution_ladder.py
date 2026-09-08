#!/usr/bin/env python3
"""Evaluate one fixed GRB solution across a VegasAfterglow resolution ladder.

This is deliberately not a fit: it never creates a sampler or changes model
parameters other than the three VegasAfterglow adaptive-resolution controls.
It is intended to establish convergence and diagnose resolution sensitivity
before choosing defaults for future campaigns.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.ampy import Ampy
from jetfit.mcmc.mcmc import calibration_offsets, chi_squared, slop


# The coupled ladder is relative to the resolution actually used by the
# published fit. It therefore always includes the production setting and four
# progressively finer levels (1.33x, 2x, 2.67x, and 4x), plus a separate
# perturbation of each adaptive coordinate.
COUPLED_FACTORS = (
    ("very_coarse", 1.0 / 6.0, "one-sixth production resolution on every control"),
    ("coarse", 1.0 / 3.0, "one-third production resolution on every control"),
    ("sub_default", 0.5, "half production resolution on every control"),
    ("native_default", 2.0 / 3.0, "two-thirds production resolution on every control"),
    ("production", 1.0, "published production resolution"),
    ("fine", 4.0 / 3.0, "first coupled refinement above production"),
    ("very_fine", 2.0, "second coupled refinement above production"),
    ("ultra_fine", 8.0 / 3.0, "third coupled refinement above production"),
    ("extreme_fine", 4.0, "fourth coupled refinement; numerical reference"),
)
# Increment this whenever the actual fixed-model evaluations or their grid
# definition change.  The meeting-book refresher uses it to avoid presenting a
# historical, differently scaled ladder as if it were the current protocol.
RESOLUTION_LADDER_VERSION = "coupled-grid-relative-to-production-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--results", required=True, type=Path, help="Finished final-final product directory.")
    parser.add_argument("--model", type=Path, default=None, help="Defaults to <results>/model.toml.")
    parser.add_argument("--obs", type=Path, default=None, help="Defaults to <results>/obs.csv.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--levels",
        nargs="*",
        default=None,
        help="Optional resolution IDs to run; default is the complete ladder.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and write the planned ladder only.")
    return parser.parse_args()


def load_fixed_solution(results: Path) -> tuple[dict[str, Any], str]:
    minimized = results / "minimized" / "minimized.json"
    if minimized.exists():
        payload = json.loads(minimized.read_text())
        params = payload.get("params")
        if isinstance(params, dict):
            return params, "minimized/minimized.json"
    best_fit = results / "best_fit.json"
    if best_fit.exists():
        payload = json.loads(best_fit.read_text())
        if isinstance(payload, dict):
            return payload, "best_fit.json"
    raise FileNotFoundError(f"No minimized/minimized.json or best_fit.json in {results}")


def production_resolution(params: dict[str, Any]) -> tuple[float, float, float]:
    model = params.get("model")
    if not isinstance(model, dict):
        raise ValueError("Fixed solution has no model section")
    keys = ("vegas_resolution_phi", "vegas_resolution_theta", "vegas_resolution_t")
    try:
        resolution = tuple(float(model[key]) for key in keys)
    except KeyError:
        # Earlier campaigns relied on the documented VegasAfterglow native
        # default, rather than serializing controls into minimized.json.
        resolution = (0.10, 0.25, 10.0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Published VegasAfterglow resolution controls are invalid") from exc
    if any(value <= 0 for value in resolution):
        raise ValueError("Published VegasAfterglow resolution controls must be positive")
    return resolution


def resolution_ladder(production: tuple[float, float, float]) -> list[tuple[str, float, float, float, str]]:
    phi, theta, time_resolution = production
    coupled = [
        (ident, phi * factor, theta * factor, time_resolution * factor, purpose)
        for ident, factor, purpose in COUPLED_FACTORS
    ]
    return coupled + [
        ("phi_coarsened", phi * 0.5, theta, time_resolution, "only azimuth coarsened from production"),
        ("phi_refined", phi * 2.0, theta, time_resolution, "only azimuth refined from production"),
        ("theta_coarsened", phi, theta * 0.5, time_resolution, "only polar angle coarsened from production"),
        ("theta_refined", phi, theta * 2.0, time_resolution, "only polar angle refined from production"),
        ("time_coarsened", phi, theta, time_resolution * 0.5, "only log-time sampling coarsened from production"),
        ("time_refined", phi, theta, time_resolution * 2.0, "only log-time sampling refined from production"),
    ]


def selected_levels(names: list[str] | None, production: tuple[float, float, float]) -> list[tuple[str, float, float, float, str]]:
    by_name = {row[0]: row for row in resolution_ladder(production)}
    if not names:
        return list(by_name.values())
    unknown = sorted(set(names) - set(by_name))
    if unknown:
        raise ValueError(f"Unknown resolution level(s): {', '.join(unknown)}")
    return [by_name[name] for name in names]


def evaluate(ampy: Ampy, params: dict[str, Any]) -> tuple[np.ndarray, float]:
    modeled = ampy.mcmc.models.model(params)
    if modeled.shape != ampy.obs.as_arrays.values.shape or not np.all(np.isfinite(modeled)):
        return np.full_like(ampy.obs.as_arrays.values, np.nan, dtype=float), float("nan")
    corrected = calibration_offsets(modeled, params.get("offsets"), ampy.obs.offsets)
    return corrected, float(chi_squared(corrected, ampy.obs, slop(params.get("slop"), ampy.obs)))


def write_plan(out: Path, levels: list[tuple[str, float, float, float, str]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    production = next((row for row in levels if row[0] == "production"), None)
    coupled_ids = {row[0] for row in COUPLED_FACTORS}
    with (out / "resolution_ladder.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["resolution_id", "production_multiplier", "phi_ppd", "theta_ppd", "time_per_log10_decade", "purpose"])
        writer.writeheader()
        for ident, phi, theta, t, purpose in levels:
            multiplier = phi / production[1] if production is not None and ident in coupled_ids else ""
            writer.writerow({"resolution_id": ident, "production_multiplier": multiplier, "phi_ppd": phi, "theta_ppd": theta, "time_per_log10_decade": t, "purpose": purpose})


def main() -> None:
    args = parse_args()
    results = args.results.expanduser().resolve()
    model = (args.model or (results / "model.toml")).expanduser().resolve()
    obs = (args.obs or (results / "obs.csv")).expanduser().resolve()
    out = args.out.expanduser().resolve()
    for path in (results, model, obs):
        if not path.exists():
            raise FileNotFoundError(path)
    params, source = load_fixed_solution(results)
    production = production_resolution(params)
    levels = selected_levels(args.levels, production)
    write_plan(out, levels)
    if args.dry_run:
        print(f"VALIDATED {args.event}: {len(levels)} fixed-parameter resolution evaluations planned")
        return

    ampy = Ampy(obs, model)
    records: list[dict[str, Any]] = []
    flux_by_level: dict[str, np.ndarray] = {}
    for ident, phi, theta, t, purpose in levels:
        trial = copy.deepcopy(params)
        trial["model"].update(
            vegas_resolution_phi=float(phi), vegas_resolution_theta=float(theta), vegas_resolution_t=float(t)
        )
        started = time.perf_counter()
        modeled, chi2 = evaluate(ampy, trial)
        elapsed = time.perf_counter() - started
        flux_by_level[ident] = modeled
        records.append({
            "event": args.event,
            "resolution_id": ident,
            "production_multiplier": phi / production[0] if ident in {row[0] for row in COUPLED_FACTORS} else float("nan"),
            "phi_ppd": phi,
            "theta_ppd": theta,
            "time_per_log10_decade": t,
            "purpose": purpose,
            "finite_model": bool(np.all(np.isfinite(modeled))),
            "chi2": chi2,
            "runtime_seconds": elapsed,
            "solution_source": source,
            "source_results": str(results),
        })

    reference_id = "extreme_fine" if "extreme_fine" in flux_by_level else levels[-1][0]
    reference = flux_by_level[reference_id]
    flux_mask = ampy.obs.flux_loc
    for record in records:
        model_flux = flux_by_level[record["resolution_id"]]
        valid = flux_mask & np.isfinite(model_flux) & np.isfinite(reference) & (model_flux > 0) & (reference > 0)
        delta = np.log10(model_flux[valid] / reference[valid]) if np.any(valid) else np.array([], dtype=float)
        record["reference_resolution_id"] = reference_id
        record["n_flux_points_compared"] = int(delta.size)
        record["median_abs_log10_flux_delta"] = float(np.median(np.abs(delta))) if delta.size else float("nan")
        record["p95_abs_log10_flux_delta"] = float(np.quantile(np.abs(delta), 0.95)) if delta.size else float("nan")
        record["max_abs_log10_flux_delta"] = float(np.max(np.abs(delta))) if delta.size else float("nan")

    with (out / "resolution_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with (out / "modeled_observation_fluxes.csv").open("w", newline="") as handle:
        fields = ["event", "resolution_id", "time_days", "band", "observed_value", "observed_error", "modeled_value", "reference_modeled_value", "log10_ratio_to_reference"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for ident, *_ in levels:
            modeled = flux_by_level[ident]
            for i in np.flatnonzero(flux_mask):
                ref = reference[i]
                value = modeled[i]
                ratio = float("nan") if not (np.isfinite(value) and np.isfinite(ref) and value > 0 and ref > 0) else float(np.log10(value / ref))
                writer.writerow({
                    "event": args.event,
                    "resolution_id": ident,
                    "time_days": float(ampy.obs.as_arrays.times[i]),
                    "band": str(ampy.obs.as_arrays.bands[i]),
                    "observed_value": float(ampy.obs.as_arrays.values[i]),
                    "observed_error": float(ampy.obs.as_arrays.errors[i]),
                    "modeled_value": float(value),
                    "reference_modeled_value": float(ref),
                    "log10_ratio_to_reference": ratio,
                })
    metadata = {
        "resolution_ladder_version": RESOLUTION_LADDER_VERSION,
        "event": args.event,
        "fixed_solution_source": source,
        "source_results": str(results),
        "model_toml": str(model),
        "obs_csv": str(obs),
        "reference_resolution_id": reference_id,
        "published_production_resolution": {
            "phi_ppd": production[0],
            "theta_ppd": production[1],
            "time_per_log10_decade": production[2],
        },
        "coupled_grid_multipliers": {
            ident: phi / production[0]
            for ident, phi, _, _, _ in levels
            if ident in {row[0] for row in COUPLED_FACTORS}
        },
        "no_fit_or_minimization": True,
    }
    (out / "resolution_run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()
