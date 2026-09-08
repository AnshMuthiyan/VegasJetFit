#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from jetfit.ampy import Ampy
from jetfit.mcmc.mcmc import calibration_offsets, chi_squared, slop
from jetfit.models.base import deceleration_time


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_best_params(results_dir: Path) -> tuple[dict[str, Any], str]:
    min_path = results_dir / "minimized" / "minimized.json"
    if min_path.exists():
        payload = _load_json(min_path)
        params = payload.get("params")
        if isinstance(params, dict):
            return params, "minimized/minimized.json"

    best_path = results_dir / "best_fit.json"
    if best_path.exists():
        payload = _load_json(best_path)
        if isinstance(payload, dict):
            return payload, "best_fit.json"

    raise FileNotFoundError(f"No minimized/minimized.json or best_fit.json in {results_dir}")


def first_time_days(obs_csv: Path) -> float:
    with obs_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"No columns in {obs_csv}")

        lowered = {c.lower(): c for c in reader.fieldnames}
        time_col = None
        for cand in ("time_days", "time", "t_days", "t", "days"):
            if cand in lowered:
                time_col = lowered[cand]
                break
        if time_col is None:
            time_col = reader.fieldnames[0]

        vals = []
        for row in reader:
            try:
                v = float(row.get(time_col, "nan"))
            except Exception:
                continue
            if math.isfinite(v) and v > 0:
                vals.append(v)
    if not vals:
        raise ValueError(f"No positive times in {obs_csv}")
    return float(min(vals))


def decel_time_obs_days(model: dict[str, float]) -> float:
    e52 = float(model["E52"])
    n017 = float(model["n017"])
    k = float(model["k"])
    gamma0 = float(model["lf0"])
    z = float(model["z"])
    n0 = n017 * (1.0e17 ** k)
    tdec_src_s = float(deceleration_time(e52 * 1.0e52, n0, k, gamma0))
    return tdec_src_s * (1.0 + z) / 86400.0


def eval_one(ampy: Ampy, params: dict[str, Any]) -> tuple[float, float, np.ndarray, np.ndarray]:
    obs = ampy.obs
    modeled = ampy.mcmc.models.model(params)
    modeled = calibration_offsets(modeled, params.get("offsets"), obs.offsets)
    s = slop(params.get("slop"), obs)
    chi2 = float(chi_squared(modeled, obs, s))
    ll = -0.5 * chi2

    flux_mask = obs.flux_loc
    times_flux = obs.as_arrays.times[flux_mask]
    modeled_flux = modeled[flux_mask]
    return chi2, ll, times_flux, modeled_flux


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Evaluate fixed-Gamma0 sweep by holding all other parameters at one best solution. "
            "This is a fast sensitivity diagnostic (no MCMC/no minimization)."
        )
    )
    p.add_argument("--event", default="221009A")
    p.add_argument("--base-results-dir", required=True)
    p.add_argument("--base-model-toml", default=None)
    p.add_argument("--obs", required=True)
    p.add_argument("--gammas", nargs="+", type=float, required=True)
    p.add_argument("--out-csv", required=True)
    args = p.parse_args()

    base_results_dir = Path(args.base_results_dir).expanduser().resolve()
    base_model_toml = (
        Path(args.base_model_toml).expanduser().resolve()
        if args.base_model_toml
        else (base_results_dir / "model.toml")
    )
    obs_csv = Path(args.obs).expanduser().resolve()
    out_csv = Path(args.out_csv).expanduser().resolve()
    ensure_parent(out_csv)

    base_params, source = load_best_params(base_results_dir)
    base_model = copy.deepcopy(base_params.get("model", {}))
    if not isinstance(base_model, dict):
        raise ValueError("Base params missing model section.")

    ampy = Ampy(obs_csv, base_model_toml)
    t1_days = first_time_days(obs_csv)

    chi2_base, _, _, flux_base = eval_one(ampy, base_params)

    rows: list[dict[str, Any]] = []
    for gamma in args.gammas:
        params = copy.deepcopy(base_params)
        params["model"]["lf0"] = float(gamma)
        chi2, ll, _, flux = eval_one(ampy, params)
        tdec_days = decel_time_obs_days(params["model"])
        ratio = np.clip(flux / flux_base, 1e-300, 1e300)
        rows.append(
            {
                "event": args.event,
                "gamma0_fixed": float(gamma),
                "nmap": chi2,
                "chi2": chi2,
                "loglike": ll,
                "delta_nmap": np.nan,  # populated after sort
                "lf0_reference": float(base_model["lf0"]),
                "E52": float(params["model"]["E52"]),
                "n017": float(params["model"]["n017"]),
                "k": float(params["model"]["k"]),
                "eps_e": float(params["model"]["eps_e"]),
                "eps_b": float(params["model"]["eps_b"]),
                "p": float(params["model"]["p"]),
                "theta_c": float(params["model"]["theta_c"]),
                "theta_v": float(params["model"]["theta_v"]),
                "k_e": float(params["model"]["k_e"]),
                "k_g": float(params["model"]["k_g"]),
                "s": float(params["model"]["s"]),
                "ebv_source_frame": float(params["extinction"]["ebv_source_frame"]),
                "slop": float(params["slop"]["slop"]),
                "tdec_obs_days": tdec_days,
                "t1_days": t1_days,
                "t1_over_tdec": t1_days / tdec_days,
                "median_log10_flux_ratio_vs_reference": float(np.nanmedian(np.log10(ratio))),
                "mad_log10_flux_ratio_vs_reference": float(
                    np.nanmedian(np.abs(np.log10(ratio) - np.nanmedian(np.log10(ratio))))
                ),
                "base_results_dir": str(base_results_dir),
                "solution_source": source,
                "obs_csv": str(obs_csv),
            }
        )

    rows = sorted(rows, key=lambda r: r["gamma0_fixed"])
    best_nmap = min(r["nmap"] for r in rows)
    for row in rows:
        row["delta_nmap"] = row["nmap"] - best_nmap

    fieldnames = [
        "event",
        "gamma0_fixed",
        "nmap",
        "chi2",
        "delta_nmap",
        "loglike",
        "lf0_reference",
        "E52",
        "n017",
        "k",
        "eps_e",
        "eps_b",
        "p",
        "theta_c",
        "theta_v",
        "k_e",
        "k_g",
        "s",
        "ebv_source_frame",
        "slop",
        "tdec_obs_days",
        "t1_days",
        "t1_over_tdec",
        "median_log10_flux_ratio_vs_reference",
        "mad_log10_flux_ratio_vs_reference",
        "base_results_dir",
        "solution_source",
        "obs_csv",
    ]
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(out_csv)


if __name__ == "__main__":
    main()
