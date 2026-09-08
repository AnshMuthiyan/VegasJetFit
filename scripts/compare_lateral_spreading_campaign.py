#!/usr/bin/env python3
"""Compare fixed GRB solutions with Vegas lateral spreading off and on.

This is a diagnostic, not a refit.  Every fitted parameter, calibration
offset, datum, and Vegas resolution is held fixed; only the native jet
``spreading`` flag changes.  The comparison therefore measures model
sensitivity to lateral expansion without conflating it with posterior motion.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.ampy import Ampy
from scripts.plot.base import OPTION_MAP
from scripts.plot.visualize import LightCurvePlot
from scripts.plot_spread_light_curves import (
    DEFAULT_SPACING,
    SEC_PER_DAY,
    attach_axis,
    fast_model_fluxes,
    load_spacing,
)
from scripts.run_vegas_resolution_ladder import evaluate, load_fixed_solution


VERSION = "fixed-parameter-lateral-spreading-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--events", nargs="*", default=None)
    parser.add_argument("--spacing", type=Path, default=DEFAULT_SPACING)
    parser.add_argument("--ndata", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def finite(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return result if math.isfinite(result) else float("nan")


def event_directories(campaign: Path, requested: list[str] | None) -> list[Path]:
    excluded = {"trash", "comparison_plots", "histograms", "numerical_resolution_ladder", "lateral_spreading_comparison"}
    dirs = [
        path for path in campaign.iterdir()
        if path.is_dir() and path.name not in excluded and (path / "model.toml").is_file() and (path / "obs.csv").is_file()
    ]
    by_name = {path.name: path for path in dirs}
    if requested:
        missing = sorted(set(requested) - set(by_name))
        if missing:
            raise FileNotFoundError(f"Campaign lacks requested event(s): {', '.join(missing)}")
        return [by_name[event] for event in requested]
    return [by_name[name] for name in sorted(by_name)]


def time_grid(event_dir: Path, ampy: Ampy, ndata: int) -> np.ndarray:
    cache = event_dir / "light_curve_spread_out_model_data.npz"
    if cache.is_file():
        try:
            with np.load(cache, allow_pickle=False) as data:
                cached = np.asarray(data["times_days"], dtype=float)
            valid = cached[np.isfinite(cached) & (cached > 0)]
            if valid.size >= 2:
                return np.logspace(np.log10(valid.min()), np.log10(valid.max()), ndata)
        except Exception:
            pass
    obs_times = np.asarray(ampy.obs.as_arrays.times, dtype=float)
    valid = obs_times[np.isfinite(obs_times) & (obs_times > 0)]
    if valid.size < 2:
        raise ValueError(f"Insufficient positive observation times in {event_dir}")
    return np.logspace(np.log10(valid.min()), np.log10(valid.max()), ndata)


def make_light_curve_helper(ampy: Ampy, params: dict[str, Any], spreading: bool) -> LightCurvePlot:
    return LightCurvePlot(
        ampy.mcmc.models.afg_model,
        params,
        ampy.obs,
        meta={**ampy.mcmc.models.afg_kw, "lateral_spreading": spreading},
        title=None,
        dual=False,
    )


def positive_ratio(spreading: np.ndarray, baseline: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    spreading = np.asarray(spreading, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    valid = np.isfinite(spreading) & np.isfinite(baseline) & (spreading > 0) & (baseline > 0)
    ratio = np.full(np.broadcast_shapes(spreading.shape, baseline.shape), np.nan, dtype=float)
    ratio[valid] = spreading[valid] / baseline[valid]
    return ratio, valid


def interp_cell_at_time(details: Any, field: str, theta_index: int, target_seconds: float) -> float:
    values = np.asarray(getattr(details.fwd, field), dtype=float)
    times = np.asarray(details.fwd.t_obs, dtype=float)
    value_i = min(theta_index, values.shape[1] - 1)
    time_i = min(theta_index, times.shape[1] - 1)
    y = values[0, value_i, :]
    x = times[0, time_i, :]
    valid = np.isfinite(x) & np.isfinite(y) & (x > 0)
    if not np.any(valid):
        return float("nan")
    x = x[valid]
    y = y[valid]
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    x, unique = np.unique(x, return_index=True)
    y = y[unique]
    return float(np.interp(target_seconds, x, y, left=y[0], right=y[-1]))


def dynamic_metrics(model: Any, theta_c: float, theta_v: float, min_day: float, max_day: float) -> dict[str, float]:
    details = model.vegas_model.details(
        t_min=max(float(min_day) * SEC_PER_DAY, 1.0),
        t_max=max(float(max_day) * SEC_PER_DAY, float(min_day) * SEC_PER_DAY * 1.01),
    )
    theta = np.asarray(details.fwd.theta, dtype=float)
    initial = theta[0, :, 0]
    edge_index = int(np.nanargmin(np.abs(initial - theta_c)))
    target = float(max_day) * SEC_PER_DAY
    return {
        "gamma_axis_late": interp_cell_at_time(details, "Gamma", 0, target),
        "gamma_core_edge_late": interp_cell_at_time(details, "Gamma", edge_index, target),
        "theta_core_edge_initial_rad": float(initial[edge_index]),
        "theta_core_edge_late_rad": interp_cell_at_time(details, "theta", edge_index, target),
        "theta_c_rad": float(theta_c),
        "theta_v_rad": float(theta_v),
        "theta_v_over_theta_c": float(theta_v / theta_c) if theta_c > 0 else float("nan"),
        "outside_core_angle_rad": float(max(theta_v - theta_c, 0.0)),
    }


def percent_difference(new: float, old: float) -> float:
    if not (math.isfinite(new) and math.isfinite(old) and old != 0):
        return float("nan")
    return 100.0 * (new / old - 1.0)


def write_dict_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_light_curves(
    event: str,
    event_out: Path,
    params: dict[str, Any],
    ampy: Ampy,
    helper: LightCurvePlot,
    times: np.ndarray,
    spacing: dict[str, float],
    baseline_fluxes: dict[str, np.ndarray],
    spreading_fluxes: dict[str, np.ndarray],
) -> None:
    fig, ax = plt.subplots(figsize=(10.2, 7.6))
    helper = attach_axis(helper, ax)
    for band, baseline in baseline_fluxes.items():
        if band not in spreading_fluxes or band not in OPTION_MAP:
            continue
        scale = spacing.get(band, 1.0)
        color = OPTION_MAP[band]["color"]
        ax.loglog(times, np.asarray(baseline) * scale, color=color, lw=2.0, ls="--", zorder=5)
        ax.loglog(times, np.asarray(spreading_fluxes[band]) * scale, color=color, lw=1.35, ls="-", alpha=0.92, zorder=6)
    helper.plot_observation(params, spreads=spacing, offset=True, excluded=True)
    ax.set_xlabel("Time Since Trigger [days]")
    ax.set_ylabel("Scaled Flux Density [mJy]")
    ax.grid(alpha=0.25, which="both")
    ax.set_xlim(times.min(), times.max())
    ax.set_title(f"GRB {event}: fixed-parameter lateral-spreading test")
    seconds = ax.secondary_xaxis("top", functions=(lambda day: day * SEC_PER_DAY, lambda sec: sec / SEC_PER_DAY))
    seconds.set_xlabel("Time Since Trigger [seconds]")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        band_legend = ax.legend(handles, labels, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=True, fancybox=False)
        ax.add_artist(band_legend)
    styles = [
        Line2D([0], [0], color="0.15", lw=2.0, ls="--", label="current fit: no spreading"),
        Line2D([0], [0], color="0.15", lw=1.35, ls="-", label="same parameters: spreading"),
    ]
    ax.legend(handles=styles, loc="lower left", fontsize=9, frameon=True, fancybox=False)
    fig.tight_layout()
    fig.savefig(event_out / "lateral_spreading_light_curve.png", dpi=220, bbox_inches="tight")
    fig.savefig(event_out / "lateral_spreading_light_curve.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_event_diagnostics(
    event: str,
    event_out: Path,
    times: np.ndarray,
    baseline_fluxes: dict[str, np.ndarray],
    spreading_fluxes: dict[str, np.ndarray],
    obs_rows: list[dict[str, Any]],
    chi2_no: float,
    chi2_yes: float,
    dynamic_changes: dict[str, float],
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 9.3))
    for band, baseline in baseline_fluxes.items():
        if band not in spreading_fluxes or band not in OPTION_MAP:
            continue
        ratio, _ = positive_ratio(spreading_fluxes[band], baseline)
        axes[0, 0].plot(times, np.log10(ratio), color=OPTION_MAP[band]["color"], lw=1.25, label=band)
    axes[0, 0].axhline(0, color="0.25", lw=1)
    axes[0, 0].set(xscale="log", xlabel="Time Since Trigger [days]", ylabel="log10(Fspread/Fno-spread)")
    axes[0, 0].grid(alpha=0.25)
    axes[0, 0].legend(frameon=False, fontsize=7, ncols=3)

    by_band: dict[str, list[float]] = {}
    for row in obs_rows:
        value = finite(row["absolute_percent_flux_difference"])
        if math.isfinite(value):
            by_band.setdefault(str(row["band"]), []).append(value)
    labels = sorted(by_band)
    if labels:
        axes[0, 1].boxplot([by_band[label] for label in labels], tick_labels=labels, showfliers=False)
        axes[0, 1].tick_params(axis="x", rotation=55, labelsize=7)
    axes[0, 1].set_ylabel("|Fspread/Fno-spread - 1| [%]")
    axes[0, 1].set_title("differences at fitted observation points")
    axes[0, 1].grid(axis="y", alpha=0.25)

    statistic_change = chi2_yes - chi2_no
    axes[1, 0].bar(["no spreading", "spreading"], [0.0, statistic_change], color=["#326b96", "#b45f3c"])
    axes[1, 0].axhline(0, color="0.25", lw=1)
    axes[1, 0].set_ylabel("effective fit statistic - no-spreading reference")
    axes[1, 0].set_title(f"change = {statistic_change:+.2f}; lower is better")
    axes[1, 0].grid(axis="y", alpha=0.25)

    ordered = sorted(dynamic_changes.items(), key=lambda item: abs(item[1]) if math.isfinite(item[1]) else -1, reverse=True)
    names = [name for name, value in ordered if math.isfinite(value)]
    values = [value for name, value in ordered if math.isfinite(value)]
    colors = ["#a7345d" if value < 0 else "#0a6f6a" for value in values]
    axes[1, 1].barh(names[::-1], values[::-1], color=colors[::-1], alpha=0.85)
    axes[1, 1].axvline(0, color="0.25", lw=1)
    axes[1, 1].set_xlabel("spreading versus no-spreading difference [%]")
    axes[1, 1].set_title("late-time dynamical quantities; fitted inputs fixed")
    axes[1, 1].grid(axis="x", alpha=0.25)

    fig.suptitle(f"GRB {event}: lateral-spreading sensitivity", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(event_out / "lateral_spreading_diagnostics.png", dpi=200, bbox_inches="tight")
    fig.savefig(event_out / "lateral_spreading_diagnostics.pdf", bbox_inches="tight")
    plt.close(fig)


def compare_event(event_dir: Path, event_out: Path, spacing_path: Path, ndata: int) -> dict[str, Any]:
    event = event_dir.name
    params, source = load_fixed_solution(event_dir)
    model_params = params.get("model", {})
    theta_c = finite(model_params.get("theta_c"))
    theta_v = finite(model_params.get("theta_v"))
    if not (theta_c > 0 and theta_v >= 0):
        raise ValueError(f"Invalid theta_c/theta_v for {event}")

    ampy_no = Ampy(event_dir / "obs.csv", event_dir / "model.toml", model_kw={"lateral_spreading": False})
    ampy_yes = Ampy(event_dir / "obs.csv", event_dir / "model.toml", model_kw={"lateral_spreading": True})
    times = time_grid(event_dir, ampy_no, ndata)
    spacing = load_spacing(spacing_path, event)

    started = time.perf_counter()
    modeled_no, chi2_no = evaluate(ampy_no, params)
    no_seconds = time.perf_counter() - started
    started = time.perf_counter()
    modeled_yes, chi2_yes = evaluate(ampy_yes, params)
    yes_seconds = time.perf_counter() - started

    helper_no = make_light_curve_helper(ampy_no, params, False)
    helper_yes = make_light_curve_helper(ampy_yes, params, True)
    ext_no = ampy_no.extinction_model(Rv=3.1) if ampy_no.extinction_model is not None else None
    ext_yes = ampy_yes.extinction_model(Rv=3.1) if ampy_yes.extinction_model is not None else None
    flux_no = fast_model_fluxes(helper_no, params, times, ext_no)
    flux_yes = fast_model_fluxes(helper_yes, params, times, ext_yes)

    event_out.mkdir(parents=True, exist_ok=True)
    plot_light_curves(event, event_out, params, ampy_no, helper_no, times, spacing, flux_no, flux_yes)

    curve_rows: list[dict[str, Any]] = []
    for band in sorted(set(flux_no) & set(flux_yes)):
        ratio, _ = positive_ratio(flux_yes[band], flux_no[band])
        for day, baseline, spread_value, ratio_value in zip(times, flux_no[band], flux_yes[band], ratio):
            curve_rows.append({
                "event": event,
                "band": band,
                "time_days": float(day),
                "no_spreading_flux_mjy": float(baseline),
                "spreading_flux_mjy": float(spread_value),
                "spreading_to_no_spreading_ratio": float(ratio_value),
                "signed_percent_flux_difference": 100.0 * (float(ratio_value) - 1.0),
            })
    write_dict_rows(event_out / "lateral_spreading_light_curves.csv", curve_rows)

    obs_rows: list[dict[str, Any]] = []
    bands = np.asarray(ampy_no.obs.as_arrays.bands).astype(str)
    times_obs = np.asarray(ampy_no.obs.as_arrays.times, dtype=float)
    values_obs = np.asarray(ampy_no.obs.as_arrays.values, dtype=float)
    errors_obs = np.asarray(ampy_no.obs.as_arrays.errors, dtype=float)
    mask = np.asarray(ampy_no.obs.flux_loc, dtype=bool)
    for i in np.flatnonzero(mask):
        ratio = modeled_yes[i] / modeled_no[i] if modeled_no[i] > 0 and modeled_yes[i] > 0 else float("nan")
        obs_rows.append({
            "event": event,
            "band": bands[i],
            "time_days": times_obs[i],
            "observed_value": values_obs[i],
            "observed_error": errors_obs[i],
            "no_spreading_modeled_value": modeled_no[i],
            "spreading_modeled_value": modeled_yes[i],
            "spreading_to_no_spreading_ratio": ratio,
            "signed_log10_flux_ratio": math.log10(ratio) if ratio > 0 else float("nan"),
            "signed_percent_flux_difference": 100.0 * (ratio - 1.0),
            "absolute_percent_flux_difference": 100.0 * abs(ratio - 1.0),
        })
    write_dict_rows(event_out / "modeled_observation_flux_comparison.csv", obs_rows)

    model_no = ampy_no.afterglow_model(**model_params, lateral_spreading=False)
    model_yes = ampy_yes.afterglow_model(**model_params, lateral_spreading=True)
    dynamics_no = dynamic_metrics(model_no, theta_c, theta_v, times.min(), times.max())
    dynamics_yes = dynamic_metrics(model_yes, theta_c, theta_v, times.min(), times.max())
    changes = {
        "core-edge angle": percent_difference(dynamics_yes["theta_core_edge_late_rad"], dynamics_no["theta_core_edge_late_rad"]),
        "core-axis Gamma": percent_difference(dynamics_yes["gamma_axis_late"], dynamics_no["gamma_axis_late"]),
        "core-edge Gamma": percent_difference(dynamics_yes["gamma_core_edge_late"], dynamics_no["gamma_core_edge_late"]),
    }
    plot_event_diagnostics(event, event_out, times, flux_no, flux_yes, obs_rows, chi2_no, chi2_yes, changes)

    obs_abs = np.asarray([finite(row["absolute_percent_flux_difference"]) for row in obs_rows], dtype=float)
    obs_log = np.asarray([finite(row["signed_log10_flux_ratio"]) for row in obs_rows], dtype=float)
    obs_abs = obs_abs[np.isfinite(obs_abs)]
    obs_log = obs_log[np.isfinite(obs_log)]
    gamma_late = dynamics_no["gamma_axis_late"]
    delta_angle = dynamics_no["outside_core_angle_rad"]
    summary = {
        "event": event,
        "solution_source": source,
        "source_results": str(event_dir.resolve()),
        "n_observation_points": int(obs_abs.size),
        "effective_fit_statistic_no_spreading": chi2_no,
        "effective_fit_statistic_spreading": chi2_yes,
        "delta_effective_fit_statistic_spreading_minus_no": chi2_yes - chi2_no,
        "median_absolute_percent_flux_difference": float(np.median(obs_abs)) if obs_abs.size else float("nan"),
        "p95_absolute_percent_flux_difference": float(np.quantile(obs_abs, 0.95)) if obs_abs.size else float("nan"),
        "max_absolute_percent_flux_difference": float(np.max(obs_abs)) if obs_abs.size else float("nan"),
        "median_signed_log10_flux_ratio": float(np.median(obs_log)) if obs_log.size else float("nan"),
        "p16_signed_log10_flux_ratio": float(np.quantile(obs_log, 0.16)) if obs_log.size else float("nan"),
        "p84_signed_log10_flux_ratio": float(np.quantile(obs_log, 0.84)) if obs_log.size else float("nan"),
        "theta_c_rad": theta_c,
        "theta_v_rad": theta_v,
        "theta_v_over_theta_c": dynamics_no["theta_v_over_theta_c"],
        "outside_core_angle_rad": delta_angle,
        "late_time_days": float(times.max()),
        "gamma_axis_late_no_spreading": gamma_late,
        "gamma_axis_late_spreading": dynamics_yes["gamma_axis_late"],
        "gamma_theta_c_late_no_spreading": gamma_late * theta_c,
        "gamma_theta_v_late_no_spreading": gamma_late * theta_v,
        "gamma_outside_core_angle_late_no_spreading": gamma_late * delta_angle,
        "core_edge_theta_late_no_spreading_rad": dynamics_no["theta_core_edge_late_rad"],
        "core_edge_theta_late_spreading_rad": dynamics_yes["theta_core_edge_late_rad"],
        "core_edge_theta_percent_difference": changes["core-edge angle"],
        "core_axis_gamma_percent_difference": changes["core-axis Gamma"],
        "core_edge_gamma_percent_difference": changes["core-edge Gamma"],
        "fixed_model_runtime_no_spreading_seconds": no_seconds,
        "fixed_model_runtime_spreading_seconds": yes_seconds,
        "comparison_version": VERSION,
        "no_refit_or_parameter_change": True,
    }
    write_dict_rows(event_out / "lateral_spreading_summary.csv", [summary])
    (event_out / "lateral_spreading_metadata.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def plot_campaign(summary: list[dict[str, Any]], out: Path) -> None:
    for row in summary:
        if "gamma_theta_v_late_no_spreading" not in row:
            row["gamma_theta_v_late_no_spreading"] = (
                finite(row.get("gamma_axis_late_no_spreading")) * finite(row.get("theta_v_rad"))
            )
    ordered = sorted(summary, key=lambda row: finite(row["p95_absolute_percent_flux_difference"]), reverse=True)
    events = [str(row["event"]) for row in ordered]
    values = [finite(row["p95_absolute_percent_flux_difference"]) for row in ordered]
    fig, ax = plt.subplots(figsize=(9.2, 7.2))
    positions = np.arange(len(events))
    ax.barh(positions, values, color="#b45f3c", alpha=0.85)
    ax.set_yticks(positions, events)
    ax.invert_yaxis()
    ax.set_xlabel("95th percentile |Fspread/Fno-spread - 1| at observation times [%]")
    ax.set_title("Fixed-parameter sensitivity to lateral spreading")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out / "campaign_spreading_percent_differences_ranked.png", dpi=220, bbox_inches="tight")
    fig.savefig(out / "campaign_spreading_percent_differences_ranked.pdf", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 9.2))
    y = np.asarray(values, dtype=float)
    x_fields = [
        ("gamma_axis_late_no_spreading", "late core-axis Gamma"),
        ("theta_c_rad", "theta_c [rad]"),
        ("gamma_theta_c_late_no_spreading", "late Gamma x theta_c"),
        ("gamma_theta_v_late_no_spreading", "late Gamma x theta_v"),
    ]
    correlation_rows: list[dict[str, Any]] = []
    for ax, (field, label) in zip(axes.ravel(), x_fields):
        x = np.asarray([finite(row[field]) for row in ordered], dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        correlation = spearmanr(x[valid], y[valid]) if np.count_nonzero(valid) >= 3 else None
        rho = float(correlation.statistic) if correlation is not None else float("nan")
        pvalue = float(correlation.pvalue) if correlation is not None else float("nan")
        correlation_rows.append({
            "effect_metric": "p95_absolute_percent_flux_difference",
            "comparison_metric": field,
            "n_events": int(np.count_nonzero(valid)),
            "spearman_rho": rho,
            "two_sided_pvalue_exploratory": pvalue,
        })
        ax.scatter(x, y, color="#0a6f6a", s=42)
        for index, (event, xv, yv) in enumerate(zip(events, x, y)):
            if math.isfinite(xv) and math.isfinite(yv):
                offset_y = (index % 3 - 1) * 6 + 3
                ax.annotate(event, (xv, yv), xytext=(4, offset_y), textcoords="offset points", fontsize=7)
        ax.set_xlabel(label)
        ax.set_ylabel("p95 absolute flux difference [%]")
        ax.grid(alpha=0.25)
        ax.text(
            0.98,
            0.96,
            f"Spearman rho = {rho:+.2f}\np = {pvalue:.3g}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "0.75", "alpha": 0.85},
        )
    for ax in axes.ravel():
        ax.set_xscale("log")
    fig.suptitle("Does spreading sensitivity track low Gamma or off-axis geometry?", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out / "campaign_spreading_effect_vs_geometry.png", dpi=210, bbox_inches="tight")
    fig.savefig(out / "campaign_spreading_effect_vs_geometry.pdf", bbox_inches="tight")
    plt.close(fig)
    write_dict_rows(out / "campaign_spreading_rank_correlations.csv", correlation_rows)


def main() -> None:
    args = parse_args()
    campaign = args.campaign.expanduser().resolve()
    if not campaign.is_dir():
        raise NotADirectoryError(campaign)
    out = (args.out or (campaign / "lateral_spreading_comparison")).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    events = event_directories(campaign, args.events)
    summaries: list[dict[str, Any]] = []
    for event_dir in events:
        event_out = event_dir / "lateral_spreading_comparison"
        summary_path = event_out / "lateral_spreading_summary.csv"
        if summary_path.exists() and not args.force:
            with summary_path.open(newline="") as handle:
                summaries.extend(csv.DictReader(handle))
            print(f"REUSED {event_dir.name}")
            continue
        print(f"RUNNING {event_dir.name}", flush=True)
        summaries.append(compare_event(event_dir, event_out, args.spacing.expanduser().resolve(), args.ndata))
        write_dict_rows(out / "campaign_lateral_spreading_summary.csv", summaries)
    write_dict_rows(out / "campaign_lateral_spreading_summary.csv", summaries)
    plot_campaign(summaries, out)
    metadata = {
        "comparison_version": VERSION,
        "source_campaign": str(campaign),
        "event_count": len(summaries),
        "events": [row["event"] for row in summaries],
        "fixed_parameters": True,
        "lateral_spreading_is_only_changed_model_setting": True,
        "statistics_reference": "current fitted no-spreading model",
    }
    (out / "README.md").write_text(
        "# Lateral-spreading comparison\n\n"
        "This fixed-parameter diagnostic compares the current fitted model with "
        "VegasAfterglow lateral spreading disabled and enabled. All fitted "
        "parameters, data, calibration terms, extinction, and numerical resolution "
        "remain identical. Percent differences therefore describe predicted flux "
        "sensitivity, not refitted parameter shifts.\n"
    )
    (out / "lateral_spreading_campaign_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()
