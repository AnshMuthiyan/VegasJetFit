#!/usr/bin/env python3
"""Run independent fixed-parameter VegasAfterglow physics sensitivity tests.

Each feature family starts from the unchanged current fitted model. Features
are never stacked across families. These products diagnose model sensitivity;
they are not refits and must not be interpreted as posterior comparisons.
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.ampy import Ampy
from scripts.compare_lateral_spreading_campaign import (
    event_directories,
    finite,
    make_light_curve_helper,
    positive_ratio,
    time_grid,
    write_dict_rows,
)
from scripts.plot.base import OPTION_MAP
from scripts.plot_spread_light_curves import DEFAULT_SPACING, SEC_PER_DAY, attach_axis, fast_model_fluxes, load_spacing
from scripts.run_vegas_resolution_ladder import evaluate, load_fixed_solution


VERSION = "independent-fixed-parameter-physics-v1"
FEATURE_ORDER = ("ssc_kn", "xi_e", "cmb_cooling", "reverse_shock", "energy_injection", "jet_profile")
FEATURE_TITLES = {
    "ssc_kn": "SSC and Klein-Nishina sensitivity",
    "xi_e": "accelerated-electron fraction sensitivity",
    "cmb_cooling": "CMB inverse-Compton cooling sensitivity",
    "reverse_shock": "reverse-shock sensitivity",
    "energy_injection": "energy-injection sensitivity",
    "jet_profile": "jet-profile family sensitivity",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--events", nargs="*", default=None)
    parser.add_argument("--features", nargs="*", choices=FEATURE_ORDER, default=None)
    parser.add_argument("--spacing", type=Path, default=DEFAULT_SPACING)
    parser.add_argument("--ndata", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def scenarios_for(feature: str, baseline_model: Any) -> list[dict[str, Any]]:
    if feature == "ssc_kn":
        return [
            {"name": "ssc_thomson", "label": "SSC: Thomson", "kwargs": {"ssc": True}},
            {"name": "ssc_kn", "label": "SSC + KN", "kwargs": {"ssc": True, "kn": True}},
        ]
    if feature == "xi_e":
        return [
            {"name": "xi_e_0p3", "label": "xi_e = 0.3", "kwargs": {"xi_e": 0.3}},
            {"name": "xi_e_0p1", "label": "xi_e = 0.1", "kwargs": {"xi_e": 0.1}},
        ]
    if feature == "cmb_cooling":
        return [{"name": "cmb_on", "label": "CMB cooling", "kwargs": {"cmb_cooling": True}}]
    if feature == "reverse_shock":
        return [
            {
                "name": f"reverse_{duration:g}s",
                "label": f"reverse shock: {duration:g} s",
                "kwargs": {"reverse_shock": True, "jet_duration": duration},
            }
            for duration in (1.0, 10.0, 100.0)
        ]
    if feature == "energy_injection":
        t0 = 1.0e4
        e_iso = float(baseline_model.E_iso52)
        return [
            {
                "name": f"injection_{fraction:g}Eiso",
                "label": f"injected energy = {fraction:g} E_iso,on-axis",
                "kwargs": {
                    "magnetar_L0": fraction * e_iso / t0,
                    "magnetar_t0": t0,
                    "magnetar_q": 2.0,
                },
                "derived": {
                    "injected_to_initial_on_axis_eiso": fraction,
                    "injection_t0_seconds": t0,
                    "injection_q": 2.0,
                },
            }
            for fraction in (0.1, 1.0)
        ]
    if feature == "jet_profile":
        return [
            {"name": "gaussian", "label": "Gaussian", "kwargs": {"diagnostic_jet_type": "gaussian"}},
            {"name": "tophat", "label": "top-hat", "kwargs": {"diagnostic_jet_type": "tophat"}},
        ]
    raise ValueError(feature)


def scenario_styles(count: int) -> list[dict[str, Any]]:
    styles = [
        {"ls": "-", "alpha": 0.95, "lw": 1.35},
        {"ls": "-.", "alpha": 0.82, "lw": 1.25},
        {"ls": ":", "alpha": 0.74, "lw": 1.35},
    ]
    return styles[:count]


def plot_feature(
    event: str,
    feature: str,
    out: Path,
    params: dict[str, Any],
    baseline_ampy: Ampy,
    baseline_helper: Any,
    times: np.ndarray,
    spacing: dict[str, float],
    baseline_flux: dict[str, np.ndarray],
    scenario_results: list[dict[str, Any]],
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 10.0), height_ratios=(2.0, 1.0))
    ax = axes[0]
    baseline_helper = attach_axis(baseline_helper, ax)
    styles = scenario_styles(len(scenario_results))
    for band, values in baseline_flux.items():
        if band not in OPTION_MAP:
            continue
        color = OPTION_MAP[band]["color"]
        scale = spacing.get(band, 1.0)
        ax.loglog(times, np.asarray(values) * scale, color=color, lw=2.0, ls="--", zorder=3)
        for result, style in zip(scenario_results, styles):
            if band in result["flux"]:
                ax.loglog(
                    times,
                    np.asarray(result["flux"][band]) * scale,
                    color=color,
                    zorder=4,
                    **style,
                )
    baseline_helper.plot_observation(params, spreads=spacing, offset=True, excluded=True)
    ax.set(xlabel="Time Since Trigger [days]", ylabel="Scaled Flux Density [mJy]", xlim=(times.min(), times.max()))
    ax.grid(alpha=0.25, which="both")
    ax.set_title(f"GRB {event}: {FEATURE_TITLES[feature]}")
    seconds = ax.secondary_xaxis("top", functions=(lambda day: day * SEC_PER_DAY, lambda sec: sec / SEC_PER_DAY))
    seconds.set_xlabel("Time Since Trigger [seconds]")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        band_legend = ax.legend(handles, labels, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=True, fancybox=False)
        ax.add_artist(band_legend)
    scenario_handles = [Line2D([0], [0], color="0.2", lw=2, ls="--", label="current fit")]
    scenario_handles.extend(
        Line2D([0], [0], color="0.2", label=result["label"], **style)
        for result, style in zip(scenario_results, styles)
    )
    ax.legend(handles=scenario_handles, loc="lower left", fontsize=8, frameon=True, fancybox=False)

    ratio_ax = axes[1]
    for band, baseline in baseline_flux.items():
        if band not in OPTION_MAP:
            continue
        for result, style in zip(scenario_results, styles):
            if band not in result["flux"]:
                continue
            ratio, _ = positive_ratio(result["flux"][band], baseline)
            ratio_ax.plot(times, np.log10(ratio), color=OPTION_MAP[band]["color"], **style)
    ratio_ax.axhline(0, color="0.25", lw=1)
    ratio_ax.set(xscale="log", xlabel="Time Since Trigger [days]", ylabel="log10(Ffeature/Fcurrent)")
    ratio_ax.grid(alpha=0.25, which="both")
    fig.tight_layout()
    fig.savefig(out / "light_curve_comparison.png", dpi=220, bbox_inches="tight")
    fig.savefig(out / "light_curve_comparison.pdf", bbox_inches="tight")
    plt.close(fig)

    labels = [result["label"] for result in scenario_results]
    p95 = [result["summary"]["p95_absolute_percent_flux_difference"] for result in scenario_results]
    med = [result["summary"]["median_signed_percent_flux_difference"] for result in scenario_results]
    delta = [result["summary"]["delta_effective_fit_statistic"] for result in scenario_results]
    runtime = [result["summary"]["runtime_ratio_to_current"] for result in scenario_results]
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.2))
    for ax_i, values, ylabel, title in (
        (axes[0, 0], p95, "p95 absolute flux difference [%]", "largest typical flux response"),
        (axes[0, 1], med, "median signed flux difference [%]", "direction of flux response"),
        (axes[1, 0], delta, "feature statistic - current statistic", "fixed-parameter fit change; lower is better"),
        (axes[1, 1], runtime, "runtime / current runtime", "evaluation cost"),
    ):
        positions = np.arange(len(labels))
        ax_i.bar(positions, values, color="#0a6f6a", alpha=0.85)
        ax_i.set_xticks(positions, labels, rotation=25, ha="right")
        ax_i.set_ylabel(ylabel)
        ax_i.set_title(title)
        ax_i.axhline(0 if "runtime" not in ylabel else 1, color="0.25", lw=1)
        ax_i.grid(axis="y", alpha=0.25)
    fig.suptitle(f"GRB {event}: {FEATURE_TITLES[feature]}", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out / "diagnostics.png", dpi=210, bbox_inches="tight")
    fig.savefig(out / "diagnostics.pdf", bbox_inches="tight")
    plt.close(fig)


def compare_feature(
    event_dir: Path,
    feature: str,
    params: dict[str, Any],
    source: str,
    baseline: dict[str, Any],
    times: np.ndarray,
    spacing: dict[str, float],
) -> list[dict[str, Any]]:
    out = event_dir / "physics_feature_comparisons" / feature
    out.mkdir(parents=True, exist_ok=True)
    model_params = params["model"]
    scenarios = scenarios_for(feature, baseline["model"])
    results: list[dict[str, Any]] = []
    flux_rows: list[dict[str, Any]] = []
    obs_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        ampy = Ampy(event_dir / "obs.csv", event_dir / "model.toml", model_kw=scenario["kwargs"])
        started = time.perf_counter()
        modeled, statistic = evaluate(ampy, params)
        runtime = time.perf_counter() - started
        helper = make_light_curve_helper(ampy, params, False)
        extinction = ampy.extinction_model(Rv=3.1) if ampy.extinction_model is not None else None
        flux = fast_model_fluxes(helper, params, times, extinction)
        plt.close(helper.ax.figure)
        ratio = np.divide(
            modeled,
            baseline["modeled"],
            out=np.full_like(modeled, np.nan, dtype=float),
            where=(np.asarray(modeled) > 0) & (np.asarray(baseline["modeled"]) > 0),
        )
        valid = ratio[np.isfinite(ratio)]
        absolute = 100.0 * np.abs(valid - 1.0)
        signed = 100.0 * (valid - 1.0)
        summary = {
            "event": event_dir.name,
            "feature": feature,
            "scenario": scenario["name"],
            "scenario_label": scenario["label"],
            "solution_source": source,
            "n_observation_points": int(valid.size),
            "effective_fit_statistic_current": baseline["statistic"],
            "effective_fit_statistic_feature": statistic,
            "delta_effective_fit_statistic": statistic - baseline["statistic"],
            "median_signed_percent_flux_difference": float(np.median(signed)) if signed.size else float("nan"),
            "median_absolute_percent_flux_difference": float(np.median(absolute)) if absolute.size else float("nan"),
            "p95_absolute_percent_flux_difference": float(np.quantile(absolute, 0.95)) if absolute.size else float("nan"),
            "max_absolute_percent_flux_difference": float(np.max(absolute)) if absolute.size else float("nan"),
            "current_runtime_seconds": baseline["runtime"],
            "feature_runtime_seconds": runtime,
            "runtime_ratio_to_current": runtime / baseline["runtime"] if baseline["runtime"] > 0 else float("nan"),
            "fixed_parameters": True,
            "comparison_version": VERSION,
            **scenario.get("derived", {}),
        }
        results.append({**scenario, "flux": flux, "modeled": modeled, "summary": summary})
        bands = np.asarray(ampy.obs.as_arrays.bands).astype(str)
        obs_times = np.asarray(ampy.obs.as_arrays.times, dtype=float)
        for index, ratio_value in enumerate(ratio):
            if not math.isfinite(float(ratio_value)):
                continue
            obs_rows.append({
                "event": event_dir.name,
                "feature": feature,
                "scenario": scenario["name"],
                "band": bands[index],
                "time_days": obs_times[index],
                "current_modeled_value": baseline["modeled"][index],
                "feature_modeled_value": modeled[index],
                "feature_to_current_ratio": ratio_value,
                "signed_percent_difference": 100.0 * (ratio_value - 1.0),
            })
        for band in sorted(set(baseline["flux"]) & set(flux)):
            curve_ratio, _ = positive_ratio(flux[band], baseline["flux"][band])
            for day, current_value, feature_value, ratio_value in zip(
                times, baseline["flux"][band], flux[band], curve_ratio
            ):
                flux_rows.append({
                    "event": event_dir.name,
                    "feature": feature,
                    "scenario": scenario["name"],
                    "band": band,
                    "time_days": day,
                    "current_flux_mjy": current_value,
                    "feature_flux_mjy": feature_value,
                    "feature_to_current_ratio": ratio_value,
                })
    plot_feature(
        event_dir.name,
        feature,
        out,
        params,
        baseline["ampy"],
        baseline["helper"],
        times,
        spacing,
        baseline["flux"],
        results,
    )
    summaries = [result["summary"] for result in results]
    write_dict_rows(out / "summary.csv", summaries)
    write_dict_rows(out / "modeled_observation_fluxes.csv", obs_rows)
    write_dict_rows(out / "light_curve_fluxes.csv", flux_rows)
    metadata = {
        "event": event_dir.name,
        "feature": feature,
        "feature_title": FEATURE_TITLES[feature],
        "fixed_parameters": True,
        "features_are_not_stacked": True,
        "current_fit_is_reference": True,
        "scenarios": [{"name": item["name"], "label": item["label"], "kwargs": item["kwargs"], **item.get("derived", {})} for item in scenarios],
        "comparison_version": VERSION,
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return summaries


def plot_campaign(rows: list[dict[str, Any]], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 2, figsize=(12.0, 15.0))
    for ax, feature in zip(axes.ravel(), FEATURE_ORDER):
        feature_rows = [row for row in rows if row["feature"] == feature]
        if feature == "reverse_shock":
            feature_rows = [row for row in feature_rows if row.get("feasibility_status") == "completed_clean"]
        by_event: dict[str, float] = {}
        for row in feature_rows:
            by_event[str(row["event"])] = max(
                by_event.get(str(row["event"]), -math.inf),
                finite(row["p95_absolute_percent_flux_difference"]),
            )
        ordered = sorted(by_event.items(), key=lambda item: item[1], reverse=True)
        positions = np.arange(len(ordered))
        ax.barh(positions, [value for _, value in ordered], color="#b45f3c", alpha=0.85)
        ax.set_yticks(positions, [event for event, _ in ordered], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("maximum scenario p95 flux difference [%]")
        title = FEATURE_TITLES[feature]
        if feature == "reverse_shock":
            title += " (clean solver completions only)"
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.25)
    fig.suptitle("Independent fixed-parameter VegasAfterglow feature sensitivities", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    fig.savefig(out / "campaign_feature_sensitivity_rankings.png", dpi=210, bbox_inches="tight")
    fig.savefig(out / "campaign_feature_sensitivity_rankings.pdf", bbox_inches="tight")
    plt.close(fig)
    write_dict_rows(out / "campaign_feature_summary.csv", rows)


def collect_existing_summaries(campaign: Path, event_dirs: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reverse_status_path = campaign / "physics_feature_comparisons" / "reverse_shock_feasibility.csv"
    reverse_status: dict[str, str] = {}
    if reverse_status_path.is_file():
        with reverse_status_path.open(newline="") as handle:
            reverse_status = {row["event"]: row["status"] for row in csv.DictReader(handle)}
    for event_dir in event_dirs:
        root = event_dir / "physics_feature_comparisons"
        for feature in FEATURE_ORDER:
            summary = root / feature / "summary.csv"
            if not summary.is_file():
                continue
            with summary.open(newline="") as handle:
                for row in csv.DictReader(handle):
                    row["feasibility_status"] = (
                        reverse_status.get(event_dir.name, "unknown")
                        if feature == "reverse_shock"
                        else "completed"
                    )
                    rows.append(row)
    return rows


def publish_feature_statuses(campaign: Path) -> None:
    status_path = campaign / "physics_feature_comparisons" / "reverse_shock_feasibility.csv"
    if not status_path.is_file():
        return
    with status_path.open(newline="") as handle:
        statuses = list(csv.DictReader(handle))
    for status in statuses:
        out = campaign / status["event"] / "physics_feature_comparisons" / "reverse_shock"
        out.mkdir(parents=True, exist_ok=True)
        (out / "feasibility_status.json").write_text(json.dumps(status, indent=2) + "\n")


def main() -> None:
    args = parse_args()
    campaign = args.campaign.expanduser().resolve()
    features = tuple(args.features or FEATURE_ORDER)
    event_dirs = event_directories(campaign, args.events)
    campaign_rows: list[dict[str, Any]] = []
    for event_dir in event_dirs:
        params, source = load_fixed_solution(event_dir)
        baseline_ampy = Ampy(event_dir / "obs.csv", event_dir / "model.toml")
        times = time_grid(event_dir, baseline_ampy, args.ndata)
        spacing = load_spacing(args.spacing.expanduser().resolve(), event_dir.name)
        started = time.perf_counter()
        baseline_modeled, baseline_statistic = evaluate(baseline_ampy, params)
        baseline_runtime = time.perf_counter() - started
        baseline_helper = make_light_curve_helper(baseline_ampy, params, False)
        extinction = baseline_ampy.extinction_model(Rv=3.1) if baseline_ampy.extinction_model is not None else None
        baseline_flux = fast_model_fluxes(baseline_helper, params, times, extinction)
        baseline_model = baseline_ampy.afterglow_model(**params["model"])
        baseline = {
            "ampy": baseline_ampy,
            "helper": baseline_helper,
            "modeled": baseline_modeled,
            "statistic": baseline_statistic,
            "runtime": baseline_runtime,
            "flux": baseline_flux,
            "model": baseline_model,
        }
        for feature in features:
            summary_path = event_dir / "physics_feature_comparisons" / feature / "summary.csv"
            if summary_path.exists() and not args.force:
                with summary_path.open(newline="") as handle:
                    campaign_rows.extend(csv.DictReader(handle))
                print(f"REUSED {event_dir.name} {feature}", flush=True)
                continue
            print(f"RUNNING {event_dir.name} {feature}", flush=True)
            campaign_rows.extend(compare_feature(event_dir, feature, params, source, baseline, times, spacing))
    campaign_out = campaign / "physics_feature_comparisons"
    all_event_dirs = event_directories(campaign, None)
    publish_feature_statuses(campaign)
    plot_campaign(collect_existing_summaries(campaign, all_event_dirs), campaign_out)
    (campaign_out / "README.md").write_text(
        "# Independent VegasAfterglow physics comparisons\n\n"
        "Every feature family starts independently from the unchanged current fitted power-law-jet model. "
        "Features are never stacked, fitted parameters are not changed, and the broken-density-profile "
        "model is intentionally excluded. These products measure fixed-parameter sensitivity, not posterior "
        "preference; a large fit-statistic change does not replace a refit.\n\n"
        "Tested families: SSC with and without Klein-Nishina corrections; accelerated-electron fractions "
        "xi_e = 0.3 and 0.1; CMB inverse-Compton cooling; injected energies of 0.1 and 1 times the initial "
        "on-axis isotropic-equivalent energy with t0 = 10^4 s and q = 2; and Gaussian/top-hat jet profiles. "
        "Reverse-shock tests use 1, 10, and 100 s ejecta durations with reverse microphysics matched to the "
        "forward shock. Consult reverse_shock_feasibility.csv before interpreting that feature: the native "
        "reverse-shock ODE hit its 100000-step safeguard for multiple structured-jet solutions, so only rows "
        "marked completed_clean are included in the campaign ranking.\n"
    )
    print(f"WROTE {campaign_out}")


if __name__ == "__main__":
    main()
