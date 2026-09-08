#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from jetfit.ampy import Ampy
from jetfit.mcmc.mcmc import calibration_offsets, slop as format_slop
from jetfit.models.base import deceleration_time


def load_params(results_dir: Path) -> dict:
    min_path = results_dir / "minimized" / "minimized.json"
    best_path = results_dir / "best_fit.json"
    if min_path.exists():
        payload = json.loads(min_path.read_text())
        return payload["params"]
    if best_path.exists():
        return json.loads(best_path.read_text())
    raise FileNotFoundError(f"No minimized/minimized.json or best_fit.json in {results_dir}")


def resolve_obs_csv(results_dir: Path) -> Path:
    obs = results_dir / "obs.csv"
    if obs.exists():
        return obs
    # fallback for old runs where obs.csv may not have been copied
    return Path("/Users/jkeohane/GRBs/VegasJetFit/jetfit/resources/grbs/221009A/221009A.csv")


def point_contributions(ampy: Ampy, params_dict: dict) -> pd.DataFrame:
    obs = ampy.obs
    modeled = ampy.mcmc.models.model(params_dict)
    modeled = calibration_offsets(modeled, params_dict.get("offsets"), obs.offsets)

    y = obs.as_arrays.values
    e = obs.as_arrays.errors
    t_days = obs.as_arrays.times

    s = format_slop(params_dict.get("slop"), obs)
    flux_mask = obs.flux_loc
    sindex_mask = obs.sindex_loc

    contrib = np.zeros_like(y, dtype=float)
    sig_eff = np.array(e, dtype=float)

    if s is not None and flux_mask.any():
        if np.isscalar(s):
            s_flux = np.full(np.count_nonzero(flux_mask), float(s))
        else:
            s_flux = np.asarray(s, dtype=float)[flux_mask]
        f_flux = modeled[flux_mask]
        y_flux = y[flux_mask]
        e_flux = e[flux_mask]
        s_lin_avg = f_flux * (10**s_flux - 10**-s_flux) / 2.0
        sig_flux = np.sqrt(s_lin_avg**2 + e_flux**2)
        contrib[flux_mask] = 2.0 * np.log(sig_flux) + ((y_flux - f_flux) / sig_flux) ** 2
        sig_eff[flux_mask] = sig_flux
    else:
        contrib[flux_mask] = ((y[flux_mask] - modeled[flux_mask]) / e[flux_mask]) ** 2

    if sindex_mask.any():
        contrib[sindex_mask] = ((y[sindex_mask] - modeled[sindex_mask]) / e[sindex_mask]) ** 2

    bands = [getattr(d, "band", "unknown") or "unknown" for d in obs.data]
    value_types = [d.__class__.__name__ for d in obs.data]
    resid_sigma = (y - modeled) / sig_eff

    return pd.DataFrame(
        {
            "time_days": t_days,
            "band": bands,
            "value_type": value_types,
            "y": y,
            "model": modeled,
            "err": e,
            "sigma_eff": sig_eff,
            "resid_sigma": resid_sigma,
            "chi_term": contrib,
            "pull2": resid_sigma**2,
        }
    )


def attach_t_over_tdec(df: pd.DataFrame, params_dict: dict) -> tuple[pd.DataFrame, float]:
    model = params_dict.get("model", {})
    E52 = float(model["E52"])
    gamma0 = float(model["lf0"])
    n017 = float(model["n017"])
    k = float(model["k"])
    z = float(model["z"])

    # Dylan PL convention: n(r) = n017 * (r/1e17 cm)^(-k)  => n(r)=n0*r^-k
    # with n0 = n017*(1e17)^k in cm^(k-3)
    n0 = n017 * (1.0e17 ** k)
    tdec_src_s = float(deceleration_time(E52 * 1.0e52, n0, k, gamma0))
    tdec_obs_days = tdec_src_s * (1.0 + z) / 86400.0
    out = df.copy()
    out["t_over_tdec_obs"] = out["time_days"] / tdec_obs_days
    return out, tdec_obs_days


def run_one(results_dir: Path, out_dir: Path) -> tuple[str, Path]:
    params = load_params(results_dir)
    obs_csv = resolve_obs_csv(results_dir)
    model_toml = results_dir / "model.toml"
    if not model_toml.exists():
        raise FileNotFoundError(f"Missing model.toml in {results_dir}")

    ampy = Ampy(obs_csv, model_toml)
    df = point_contributions(ampy, params)
    df, tdec_obs_days = attach_t_over_tdec(df, params)
    label = results_dir.name

    run_out = out_dir / label
    run_out.mkdir(parents=True, exist_ok=True)
    df.to_csv(run_out / "likelihood_point_contributions.csv", index=False)

    # Plot 1: per-point contribution vs time
    fig, ax = plt.subplots(figsize=(10, 5))
    for band, sub in df.groupby("band"):
        ax.scatter(sub["time_days"], sub["chi_term"], s=14, alpha=0.7, label=band)
    ax.set_xscale("log")
    ax.set_xlabel("Time [days]")
    ax.set_ylabel("Per-point chi contribution")
    ax.set_title(f"{label}: likelihood contribution by point")
    ax.legend(fontsize=7, ncol=3)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_out / "chi_contrib_vs_time_by_band.png", dpi=200)
    plt.close(fig)

    # Plot 2: total contribution by band
    by_band = (
        df.groupby("band", as_index=False)
        .agg(chi_term=("chi_term", "sum"), pull2=("pull2", "sum"))
        .sort_values("pull2", ascending=False)
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(by_band["band"], by_band["pull2"])
    ax.set_ylabel("Total residual$^2$ contribution")
    ax.set_title(f"{label}: mismatch contribution by band (positive-definite)")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_out / "chi_contrib_by_band.png", dpi=200)
    plt.close(fig)

    # Plot 3: stacked by time decade and band
    bins = np.logspace(np.log10(df["time_days"].min()), np.log10(df["time_days"].max()), 10)
    tmp = df.copy()
    tmp["time_bin"] = pd.cut(tmp["time_days"], bins=bins, include_lowest=True)
    pivot = tmp.pivot_table(index="time_bin", columns="band", values="chi_term", aggfunc="sum", fill_value=0.0)
    fig, ax = plt.subplots(figsize=(11, 5))
    bottom = np.zeros(len(pivot.index))
    x = np.arange(len(pivot.index))
    for col in pivot.columns:
        vals = pivot[col].values
        ax.bar(x, vals, bottom=bottom, label=col, width=0.9)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in pivot.index], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Total chi contribution")
    ax.set_title(f"{label}: contribution by time bin and band")
    ax.legend(fontsize=7, ncol=4)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_out / "chi_contrib_stacked_timeband.png", dpi=200)
    plt.close(fig)

    summary = by_band.copy()
    denom = float(summary["pull2"].sum()) if len(summary) else 1.0
    summary["fraction_pull2"] = summary["pull2"] / denom
    summary.to_csv(run_out / "chi_contrib_by_band_summary.csv", index=False)

    top20 = df.sort_values("pull2", ascending=False).head(20).copy()
    top20.to_csv(run_out / "top20_points_with_t_over_tdec.csv", index=False)
    (run_out / "tdec_obs_days.txt").write_text(f"{tdec_obs_days:.12g}\n")
    return label, run_out


def main() -> None:
    p = argparse.ArgumentParser(description="Diagnose per-point likelihood contributions for GRB fits.")
    p.add_argument("--results", nargs="+", required=True, help="Result directories to analyze.")
    p.add_argument(
        "--out-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/plots/likelihood_diagnostics",
        help="Output directory.",
    )
    args = p.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in args.results:
        label, run_out = run_one(Path(r).expanduser().resolve(), out_dir)
        rows.append({"run": label, "output_dir": str(run_out)})

    pd.DataFrame(rows).to_csv(out_dir / "index.csv", index=False)

    # If two or more runs are provided, add cross-run top20 overlay with t/t_dec.
    if len(rows) >= 2:
        fig, ax = plt.subplots(figsize=(10, 6))
        for row in rows[:2]:
            run = row["run"]
            top = pd.read_csv(Path(row["output_dir"]) / "top20_points_with_t_over_tdec.csv")
            ax.scatter(
                top["t_over_tdec_obs"],
                top["pull2"],
                s=28,
                alpha=0.8,
                label=run,
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$t/t_{\rm dec,obs}$ for top-20 leverage points")
        ax.set_ylabel(r"Per-point residual$^2$")
        ax.set_title("Top-20 leverage points across runs")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_dir / "top20_overlay_t_over_tdec.png", dpi=220)
        plt.close(fig)

    print(out_dir)


if __name__ == "__main__":
    main()
