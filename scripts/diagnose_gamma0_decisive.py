#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq

from jetfit.ampy import Ampy
from jetfit.mcmc.mcmc import calibration_offsets, chi_squared, slop
from jetfit.models.base import deceleration_time


SOL_CGS = 2.99792458e10


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


def decel_time_obs_days(model: dict[str, float]) -> float:
    e52 = float(model["E52"])
    n017 = float(model["n017"])
    k = float(model["k"])
    gamma0 = float(model["lf0"])
    z = float(model["z"])
    n0 = n017 * (1.0e17 ** k)
    tdec_src_s = float(deceleration_time(e52 * 1.0e52, n0, k, gamma0))
    return tdec_src_s * (1.0 + z) / 86400.0


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


def solve_e52_for_tdec_match(
    *,
    n017: float,
    k: float,
    z: float,
    gamma0: float,
    target_tdec_obs_days: float,
    e52_hint: float,
) -> float:
    n0 = n017 * (1.0e17 ** k)
    t_target_src = target_tdec_obs_days * 86400.0 / (1.0 + z)

    def f(log10_e52: float) -> float:
        e52 = 10.0 ** log10_e52
        t_src = float(deceleration_time(e52 * 1.0e52, n0, k, gamma0))
        return t_src - t_target_src

    lo = math.log10(max(e52_hint, 1e-12)) - 6.0
    hi = math.log10(max(e52_hint, 1e-12)) + 6.0

    flo = f(lo)
    fhi = f(hi)
    tries = 0
    while flo * fhi > 0 and tries < 10:
        lo -= 2.0
        hi += 2.0
        flo = f(lo)
        fhi = f(hi)
        tries += 1

    if flo * fhi > 0:
        raise RuntimeError(
            f"Could not bracket E52 root for gamma0={gamma0} target_tdec={target_tdec_obs_days:g}"
        )

    root = brentq(f, lo, hi, maxiter=300)
    return float(10.0 ** root)


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


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Decisive Gamma0 diagnostic for one GRB: "
            "(1) freeze-all sweep and (2) tdec-matched reverse sweep."
        )
    )
    p.add_argument("--event", default="221009A")
    p.add_argument("--base-results-dir", required=True)
    p.add_argument("--base-model-toml", default=None)
    p.add_argument("--obs-clean", required=True)
    p.add_argument("--obs-full", required=True)
    p.add_argument(
        "--gammas",
        nargs="+",
        type=float,
        default=[50, 100, 200, 400, 600, 800, 1000],
    )
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    base_results_dir = Path(args.base_results_dir).expanduser().resolve()
    base_model_toml = (
        Path(args.base_model_toml).expanduser().resolve()
        if args.base_model_toml
        else (base_results_dir / "model.toml")
    )
    obs_clean = Path(args.obs_clean).expanduser().resolve()
    obs_full = Path(args.obs_full).expanduser().resolve()
    out_dir = ensure_dir(Path(args.out_dir).expanduser().resolve())

    base_params, src = load_best_params(base_results_dir)
    base_model = copy.deepcopy(base_params.get("model", {}))
    if not isinstance(base_model, dict):
        raise ValueError("Base params missing model section.")

    # Two datasets for robustness.
    ampy_clean = Ampy(obs_clean, base_model_toml)
    ampy_full = Ampy(obs_full, base_model_toml)

    t1_clean = first_time_days(obs_clean)
    t1_full = first_time_days(obs_full)
    tdec_base = decel_time_obs_days(base_model)

    gamma_ref = float(base_model["lf0"])
    e52_ref = float(base_model["E52"])
    n017_ref = float(base_model["n017"])
    k_ref = float(base_model["k"])
    z_ref = float(base_model["z"])

    # Baseline modeled flux vectors (used for ratio plots).
    chi2_b_clean, ll_b_clean, t_flux_clean, f_flux_clean = eval_one(ampy_clean, base_params)
    chi2_b_full, ll_b_full, t_flux_full, f_flux_full = eval_one(ampy_full, base_params)

    rows: list[dict[str, Any]] = []
    variants = ("freeze_all_except_gamma0", "tdec_matched_reverse")

    for variant in variants:
        for gamma in args.gammas:
            params = copy.deepcopy(base_params)
            if variant == "freeze_all_except_gamma0":
                params["model"]["lf0"] = float(gamma)
            else:
                e52_new = solve_e52_for_tdec_match(
                    n017=n017_ref,
                    k=k_ref,
                    z=z_ref,
                    gamma0=float(gamma),
                    target_tdec_obs_days=tdec_base,
                    e52_hint=e52_ref,
                )
                params["model"]["lf0"] = float(gamma)
                params["model"]["E52"] = float(e52_new)

            chi2_clean, ll_clean, _, f_model_clean = eval_one(ampy_clean, params)
            chi2_full, ll_full, _, f_model_full = eval_one(ampy_full, params)

            tdec_here = decel_time_obs_days(params["model"])
            row = {
                "event": args.event,
                "variant": variant,
                "gamma0_fixed": float(gamma),
                "gamma0_ref": gamma_ref,
                "solution_source": src,
                "base_results_dir": str(base_results_dir),
                "e52_used": float(params["model"]["E52"]),
                "n017_used": float(params["model"]["n017"]),
                "k_used": float(params["model"]["k"]),
                "eps_e_used": float(params["model"]["eps_e"]),
                "eps_b_used": float(params["model"]["eps_b"]),
                "p_used": float(params["model"]["p"]),
                "theta_c_used": float(params["model"]["theta_c"]),
                "chi2_clean": chi2_clean,
                "nmap_clean": chi2_clean,
                "loglike_clean": ll_clean,
                "chi2_full": chi2_full,
                "nmap_full": chi2_full,
                "loglike_full": ll_full,
                "tdec_obs_days": tdec_here,
                "t1_clean_days": t1_clean,
                "t1_full_days": t1_full,
                "t1_over_tdec_clean": t1_clean / tdec_here,
                "t1_over_tdec_full": t1_full / tdec_here,
                "median_log10_flux_ratio_clean_vs_base": float(
                    np.nanmedian(np.log10(np.clip(f_model_clean / f_flux_clean, 1e-300, 1e300)))
                ),
                "mad_log10_flux_ratio_clean_vs_base": float(
                    np.nanmedian(
                        np.abs(
                            np.log10(np.clip(f_model_clean / f_flux_clean, 1e-300, 1e300))
                            - np.nanmedian(np.log10(np.clip(f_model_clean / f_flux_clean, 1e-300, 1e300)))
                        )
                    )
                ),
                "median_log10_flux_ratio_full_vs_base": float(
                    np.nanmedian(np.log10(np.clip(f_model_full / f_flux_full, 1e-300, 1e300)))
                ),
                "mad_log10_flux_ratio_full_vs_base": float(
                    np.nanmedian(
                        np.abs(
                            np.log10(np.clip(f_model_full / f_flux_full, 1e-300, 1e300))
                            - np.nanmedian(np.log10(np.clip(f_model_full / f_flux_full, 1e-300, 1e300)))
                        )
                    )
                ),
            }
            rows.append(row)

    # Delta columns by variant/dataset.
    for variant in variants:
        sub = [r for r in rows if r["variant"] == variant]
        best_clean = min(r["nmap_clean"] for r in sub)
        best_full = min(r["nmap_full"] for r in sub)
        for r in sub:
            r["delta_nmap_clean"] = r["nmap_clean"] - best_clean
            r["delta_nmap_full"] = r["nmap_full"] - best_full

    # Include baseline row for reference.
    rows.append(
        {
            "event": args.event,
            "variant": "baseline_reference",
            "gamma0_fixed": gamma_ref,
            "gamma0_ref": gamma_ref,
            "solution_source": src,
            "base_results_dir": str(base_results_dir),
            "e52_used": e52_ref,
            "n017_used": n017_ref,
            "k_used": k_ref,
            "eps_e_used": float(base_model["eps_e"]),
            "eps_b_used": float(base_model["eps_b"]),
            "p_used": float(base_model["p"]),
            "theta_c_used": float(base_model["theta_c"]),
            "chi2_clean": chi2_b_clean,
            "nmap_clean": chi2_b_clean,
            "loglike_clean": ll_b_clean,
            "chi2_full": chi2_b_full,
            "nmap_full": chi2_b_full,
            "loglike_full": ll_b_full,
            "tdec_obs_days": tdec_base,
            "t1_clean_days": t1_clean,
            "t1_full_days": t1_full,
            "t1_over_tdec_clean": t1_clean / tdec_base,
            "t1_over_tdec_full": t1_full / tdec_base,
            "median_log10_flux_ratio_clean_vs_base": 0.0,
            "mad_log10_flux_ratio_clean_vs_base": 0.0,
            "median_log10_flux_ratio_full_vs_base": 0.0,
            "mad_log10_flux_ratio_full_vs_base": 0.0,
            "delta_nmap_clean": 0.0,
            "delta_nmap_full": 0.0,
        }
    )

    out_csv = out_dir / f"{args.event}_gamma0_decisive_sweeps.csv"
    # Stable column order.
    cols = [
        "event",
        "variant",
        "gamma0_fixed",
        "gamma0_ref",
        "solution_source",
        "base_results_dir",
        "e52_used",
        "n017_used",
        "k_used",
        "eps_e_used",
        "eps_b_used",
        "p_used",
        "theta_c_used",
        "chi2_clean",
        "nmap_clean",
        "delta_nmap_clean",
        "loglike_clean",
        "chi2_full",
        "nmap_full",
        "delta_nmap_full",
        "loglike_full",
        "tdec_obs_days",
        "t1_clean_days",
        "t1_full_days",
        "t1_over_tdec_clean",
        "t1_over_tdec_full",
        "median_log10_flux_ratio_clean_vs_base",
        "mad_log10_flux_ratio_clean_vs_base",
        "median_log10_flux_ratio_full_vs_base",
        "mad_log10_flux_ratio_full_vs_base",
    ]
    out = []
    for r in rows:
        item = {c: r.get(c) for c in cols}
        out.append(item)

    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    # Plot: delta nmap vs gamma (clean + full)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True)
    for ax, dataset in zip(axes, ("clean", "full")):
        for variant in variants:
            sub = [r for r in rows if r["variant"] == variant]
            sub = sorted(sub, key=lambda x: x["gamma0_fixed"])
            g = np.asarray([r["gamma0_fixed"] for r in sub], dtype=float)
            d = np.asarray([r[f"delta_nmap_{dataset}"] for r in sub], dtype=float)
            ax.plot(g, d, marker="o", label=variant)
        ax.set_xscale("log")
        ax.set_xlabel("Fixed Gamma0")
        ax.set_ylabel(f"Delta nmap ({dataset})")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle(f"{args.event}: decisive Gamma0 sweeps")
    fig.tight_layout()
    fig.savefig(out_dir / f"{args.event}_gamma0_decisive_delta_nmap.png", dpi=220)
    plt.close(fig)

    # Plot: modeled flux ratio relative to baseline for both variants (clean).
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)
    for ax, variant in zip(axes, variants):
        for gamma in args.gammas:
            params = copy.deepcopy(base_params)
            if variant == "freeze_all_except_gamma0":
                params["model"]["lf0"] = float(gamma)
            else:
                e52_new = solve_e52_for_tdec_match(
                    n017=n017_ref,
                    k=k_ref,
                    z=z_ref,
                    gamma0=float(gamma),
                    target_tdec_obs_days=tdec_base,
                    e52_hint=e52_ref,
                )
                params["model"]["lf0"] = float(gamma)
                params["model"]["E52"] = float(e52_new)

            _, _, times, flux = eval_one(ampy_clean, params)
            ratio = np.clip(flux / f_flux_clean, 1e-300, 1e300)
            ax.plot(times, np.log10(ratio), ".", markersize=2.5, alpha=0.55, label=f"g={int(gamma)}")

        ax.set_xscale("log")
        ax.set_xlabel("Observer time [days] (flux points)")
        ax.set_title(variant)
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel(r"log10(model flux / baseline flux)")
    axes[1].legend(fontsize=7, ncol=2)
    fig.suptitle(f"{args.event}: light-curve ratio vs baseline (clean data)")
    fig.tight_layout()
    fig.savefig(out_dir / f"{args.event}_gamma0_decisive_flux_ratio_clean.png", dpi=220)
    plt.close(fig)

    print(out_csv)
    print(out_dir / f"{args.event}_gamma0_decisive_delta_nmap.png")
    print(out_dir / f"{args.event}_gamma0_decisive_flux_ratio_clean.png")


if __name__ == "__main__":
    main()
