#!/usr/bin/env python3
"""Plot fixed-parameter VegasAfterglow resolution-ladder diagnostics."""

from __future__ import annotations

import argparse
import csv
from fractions import Fraction
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.plot.base import OPTION_MAP
from scripts.plot_spread_light_curves import (
    add_seconds_axis,
    attach_axis,
    cache_input_signature,
    fast_model_fluxes,
    load_postfit_params,
    read_spread_flux_cache,
    restyle_legend,
    setup_axis,
)
from scripts.plot.visualize import LightCurvePlot
from jetfit.ampy import Ampy


COUPLED_LEVELS = (
    "very_coarse",
    "coarse",
    "sub_default",
    "native_default",
    "production",
    "fine",
    "very_fine",
    "ultra_fine",
    "extreme_fine",
)
AXIS_LEVELS = (
    "phi_coarsened",
    "phi_refined",
    "theta_coarsened",
    "theta_refined",
    "time_coarsened",
    "time_refined",
)
PLOT_VERSION = "signed-primary-convergence-and-16core-runtime-v16"

# Standard unattended MCMC allocations. Alternate-host wall-clock estimates
# deliberately use this worker-count normalization only; it is more honest
# than extrapolating an unstable microbenchmark across full MCMC workloads.
STANDARD_WORKERS = {
    "pcrc": 16,
    "pauley": 8,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--results-root", type=Path)
    group.add_argument("--event-dir", type=Path, help="Plot one event-level resolution_ladder directory.")
    group.add_argument("--campaign", type=Path, help="Build only campaign-wide comparisons from event resolution ladders.")
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument(
        "--publication-labels",
        action="store_true",
        help="Use machine-neutral runtime labels for externally facing figures.",
    )
    parser.add_argument(
        "--convergence-only",
        action="store_true",
        help="Skip the light-curve overlay when plotting one event directory.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def finite_delta(values: np.ndarray, reference: np.ndarray) -> tuple[float, float, float]:
    valid = np.isfinite(values) & np.isfinite(reference) & (values > 0) & (reference > 0)
    if not np.any(valid):
        return (float("nan"), float("nan"), float("nan"))
    delta = np.abs(np.log10(values[valid] / reference[valid]))
    return (float(np.median(delta)), float(np.quantile(delta, 0.95)), float(np.max(delta)))


def signed_log_ratio_quantiles(values: np.ndarray, reference: np.ndarray) -> tuple[float, float, float]:
    """Return the signed 16th/50th/84th percentiles of log10(values/reference)."""
    valid = np.isfinite(values) & np.isfinite(reference) & (values > 0) & (reference > 0)
    if not np.any(valid):
        return (float("nan"), float("nan"), float("nan"))
    delta = np.log10(values[valid] / reference[valid])
    return tuple(float(value) for value in np.quantile(delta, (0.16, 0.50, 0.84)))


def resolution_label(row: dict[str, str]) -> str:
    ident = "published production" if row["resolution_id"] in {"production", "campaign_moderate"} else row["resolution_id"]
    return f"{ident} ({float(row['phi_ppd']):g}, {float(row['theta_ppd']):g}, {float(row['time_per_log10_decade']):g})"


def production_id(rows: dict[str, dict[str, str]]) -> str:
    if "production" in rows:
        return "production"
    if "campaign_moderate" in rows:
        return "campaign_moderate"
    raise ValueError("Resolution ladder lacks the published production resolution")


def coupled_rows(rows: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    order = tuple(level for level in COUPLED_LEVELS if level != "production")
    production = production_id(rows)
    return [rows[level] for level in (*order[:4], production, *order[4:]) if level in rows]


def load_spread_factors(event: str) -> dict[str, float]:
    path = PROJECT_ROOT / "scripts" / "events" / "spacing.json"
    payload = json.loads(path.read_text())
    return {str(band): float(value) for band, value in payload.get(event, {}).items()}


def resolution_shade(color: str, index: int, production_index: int, total: int) -> tuple[float, float, float]:
    """Use lighter shades below production and darker shades above it."""
    base = np.asarray(to_rgb(color))
    if index < production_index:
        fraction = (production_index - index) / max(production_index, 1)
        return tuple(base + (1.0 - base) * (0.65 * fraction))
    if index > production_index:
        fraction = (index - production_index) / max(total - 1 - production_index, 1)
        return tuple(np.clip(base * (1.0 - 0.48 * fraction), 0.0, 1.0))
    return tuple(base)


def ratio_label(value: float) -> str:
    """Format a coupled-resolution multiplier for log-axis ticks."""
    fraction = Fraction(float(value)).limit_denominator(96)
    if fraction.denominator == 1:
        return str(fraction.numerator)
    return f"{fraction.numerator}/{fraction.denominator}"


def coupled_ratio(row: dict[str, str], production: dict[str, str]) -> float:
    """The common phi/theta/time multiplier relative to the published grid."""
    ratios = np.asarray([
        float(row["phi_ppd"]) / float(production["phi_ppd"]),
        float(row["theta_ppd"]) / float(production["theta_ppd"]),
        float(row["time_per_log10_decade"]) / float(production["time_per_log10_decade"]),
    ])
    if not np.allclose(ratios, ratios[0], rtol=1e-10, atol=1e-12):
        raise ValueError(f"Coupled ladder level {row['resolution_id']} does not use one common grid multiplier")
    return float(ratios[0])


def configure_coupled_axis(ax, ratios: np.ndarray, production_ratio: float, reference_ratio: float) -> None:
    """Make the shared coupled-grid axis explicit instead of implying phi alone varies."""
    ax.set_xscale("log")
    ax.set_xticks(ratios, [ratio_label(value) for value in ratios])
    for ratio in ratios:
        ax.axvline(ratio, color="0.84", lw=0.8, zorder=0)
    ax.axvline(production_ratio, color="#9a3e00", lw=1.35, ls="--", label="production grid")
    ax.axvline(reference_ratio, color="#4d4d4d", lw=1.35, ls="--", label="reference grid")
    ax.set_xlabel("coupled grid resolution / production")


def production_neighborhood_indices(x: np.ndarray, production_index: int) -> np.ndarray:
    """Keep two nearby coarse levels and every finer level readable."""
    coarser = np.where(x < 1.0)[0]
    # The nearest coarse levels are most informative for the production-grid
    # decision. Keep at least two when the ladder contains them.
    near_coarse = coarser[np.argsort(x[coarser])[-2:]] if coarser.size else np.empty(0, dtype=int)
    finer = np.where(x > 1.0)[0]
    return np.unique(np.concatenate((near_coarse, np.asarray([production_index]), finer)))


def positive_zoom_upper(values: np.ndarray, keep: np.ndarray) -> float:
    selected = np.asarray(values, dtype=float)[keep]
    selected = selected[np.isfinite(selected) & (selected >= 0.0)]
    if not selected.size:
        return 1.0
    return max(float(np.max(selected)) * 1.10, 1.0e-12)


def signed_production_zoom_limits(values: np.ndarray, keep: np.ndarray) -> tuple[float, float]:
    """Asymmetric limits with zero 30% above the lower edge."""
    selected = np.asarray(values, dtype=float)[keep]
    selected = selected[np.isfinite(selected)]
    if not selected.size:
        return -1.0e-6, 2.0e-6
    negative = max(float(np.max(np.maximum(-selected, 0.0))), 0.0)
    positive = max(float(np.max(np.maximum(selected, 0.0))), 0.0)
    span = max(negative / 0.30, positive / 0.70, 1.0e-12) * 1.05
    return -0.30 * span, 0.70 * span


def metadata_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def recorded_mcmc_wall_hours(event: Path) -> float | None:
    run_log = event / "run.log"
    if not run_log.is_file():
        return None
    match = re.search(r"^real\s+([0-9.]+)\s*$", run_log.read_text(errors="replace"), re.MULTILINE)
    return float(match.group(1)) / 3600.0 if match else None


def recorded_worker_count(event: Path) -> int:
    run_log = event / "run.log"
    if run_log.is_file():
        match = re.search(r"^\s*workers:\s*(\d+)\s*$", run_log.read_text(errors="replace"), re.MULTILINE)
        if match:
            return int(match.group(1))
    settings = event / "mcmc_settings.toml"
    if settings.is_file():
        match = re.search(r"^workers\s*=\s*(\d+)\s*$", settings.read_text(errors="replace"), re.MULTILINE)
        if match:
            return int(match.group(1))
    return 8


def host_class(host: str) -> str:
    lowered = host.lower()
    if "pcrc" in lowered:
        return "pcrc"
    if "pauley" in lowered:
        return "pauley"
    if "lyra" in lowered:
        return "lyra"
    return "unknown"


def alternate_host_estimate(event: Path) -> tuple[str, float, str, int, int]:
    """Return alternate standard host label and benchmark-normalized time factor."""
    source_host = metadata_value(event / "sync_manifest.txt", "source_host") or "recorded source host"
    source_class = host_class(source_host)
    if source_class == "pcrc":
        alternate_class, alternate_label = "pauley", "standard Pauley"
    else:
        # Pauley and Lyra source runs are usefully compared with the PCRC M4
        # standard; unknown legacy hosts retain a clearly neutral estimate.
        alternate_class, alternate_label = "pcrc", "standard PCRC"
    source_workers = recorded_worker_count(event)
    alternate_workers = STANDARD_WORKERS[alternate_class]
    factor = source_workers / alternate_workers
    return source_host, factor, alternate_label, source_workers, alternate_workers


def resolution_curve_cache_path(out: Path) -> Path:
    return out / "resolution_light_curve_model_data.npz"


def load_or_calculate_resolution_curves(
    event: str,
    summaries: list[dict[str, str]],
    out: Path,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Return posterior-envelope inputs plus smooth ladder curves on its exact grid."""
    metadata = json.loads((out / "resolution_run_metadata.json").read_text())
    source = Path(metadata["source_results"])
    cache = source / "light_curve_spread_out_model_data.npz"
    if not cache.is_file():
        raise FileNotFoundError(f"Missing posterior light-curve cache: {cache}")

    available_walkers = 0
    with np.load(cache, allow_pickle=False) as data:
        if "walker_samples" in data.files:
            available_walkers = int(np.asarray(data["walker_samples"]).shape[0])
        cache_metadata = json.loads(str(np.asarray(data["metadata_json"]).item()))
    input_signature = cache_input_signature(source)
    cached = read_spread_flux_cache(
        cache,
        ndata=int(cache_metadata["ndata"]),
        ncurves=int(cache_metadata["ncurves"]),
        seed=int(cache_metadata["seed"]),
        walker_limit=int(cache_metadata["walker_limit"]),
        available_walkers=available_walkers,
        input_signature=input_signature,
    )
    if cached is None:
        raise ValueError(f"Unreadable posterior light-curve cache: {cache}")
    times, best_fluxes, posterior_fluxes, _, _, _, _ = cached

    rows = {row["resolution_id"]: row for row in summaries}
    levels = [row["resolution_id"] for row in coupled_rows(rows)]
    output = resolution_curve_cache_path(out)
    expected = {level: tuple(float(rows[level][key]) for key in ("phi_ppd", "theta_ppd", "time_per_log10_decade")) for level in levels}
    if output.is_file():
        try:
            with np.load(output, allow_pickle=False) as data:
                saved = json.loads(str(np.asarray(data["resolution_json"]).item()))
                saved_times = np.asarray(data["times_days"], dtype=float)
                if saved == {key: list(value) for key, value in expected.items()} and np.array_equal(saved_times, times):
                    curves = {
                        str(band): np.asarray(data[f"curve__{band}"], dtype=float)
                        for band in np.asarray(data["bands"]).astype(str)
                    }
                    return times, best_fluxes, posterior_fluxes, curves
        except Exception:
            pass

    params, _, _ = load_postfit_params(source)
    ampy = Ampy(source / "obs.csv", source / "model.toml")
    ext_model = ampy.extinction_model(Rv=3.1) if ampy.extinction_model is not None else None
    lcg = LightCurvePlot(
        ampy.mcmc.models.afg_model,
        params,
        ampy.obs,
        meta=ampy.mcmc.models.afg_kw,
        title=None,
        dual=False,
    )
    curves: dict[str, np.ndarray] = {}
    for level in levels:
        trial = json.loads(json.dumps(params))
        phi, theta, time_resolution = expected[level]
        trial["model"].update(
            vegas_resolution_phi=phi,
            vegas_resolution_theta=theta,
            vegas_resolution_t=time_resolution,
        )
        for band, values in fast_model_fluxes(lcg, trial, times, ext_model).items():
            curves.setdefault(str(band), np.full((len(levels), times.size), np.nan, dtype=float))[levels.index(level)] = values
    plt.close(lcg.ax.figure)
    np.savez_compressed(
        output,
        times_days=times,
        bands=np.asarray(sorted(curves), dtype=str),
        resolution_ids=np.asarray(levels, dtype=str),
        resolution_json=np.asarray(json.dumps({key: list(value) for key, value in expected.items()}, sort_keys=True)),
        **{f"curve__{band}": values for band, values in curves.items()},
    )
    return times, best_fluxes, posterior_fluxes, curves


def plot_light_curves(event: str, summaries: list[dict[str, str]], fluxes: list[dict[str, str]], out: Path) -> None:
    ordered = {row["resolution_id"]: row for row in summaries}
    production = production_id(ordered)
    level_ids = [row["resolution_id"] for row in coupled_rows(ordered)]
    production_index = level_ids.index(production)
    times, best_fluxes, posterior_fluxes, resolution_curves = load_or_calculate_resolution_curves(event, summaries, out)
    metadata = json.loads((out / "resolution_run_metadata.json").read_text())
    source = Path(metadata["source_results"])
    params, _, _ = load_postfit_params(source)
    ampy = Ampy(source / "obs.csv", source / "model.toml")
    lcg = LightCurvePlot(ampy.mcmc.models.afg_model, params, ampy.obs, meta=ampy.mcmc.models.afg_kw, title=None, dual=False)
    ax = lcg.ax
    bands = sorted(set(posterior_fluxes) & set(resolution_curves) & set(OPTION_MAP))
    spread = load_spread_factors(event)
    # Use the posterior-envelope page's native plot construction, but omit its
    # shaded posterior band. The solid lines are the resolution alternatives;
    # the dashed production curve is the actual fit used by the campaign.
    for band in bands:
        base_color = OPTION_MAP[band]["color"]
        scale = spread.get(band, 1.0)
        for index, level in enumerate(level_ids):
            y = resolution_curves[band][index] * scale
            good = np.isfinite(times) & np.isfinite(y) & (times > 0) & (y > 0)
            is_production = level == production
            ax.plot(
                times[good], y[good],
                color=resolution_shade(base_color, index, production_index, len(level_ids)),
                alpha=1.0 if is_production else 0.54,
                lw=3.0 if is_production else 1.05,
                ls="--" if is_production else "-",
                # Keep the actual production curve thick but underneath the
                # alternatives, so close resolution curves remain visible.
                zorder=2 if is_production else 5,
            )
    lcg.plot_observation(params, spreads=spread, offset=True, excluded=True)
    production_row = ordered[production]
    setup_axis(ax, event)
    production_key = (
        "lighter = coarser; darker = finer\n"
        "thick dashed = production\n"
        f"phi: {float(production_row['phi_ppd']):g} angular samples per deg\n"
        f"theta: {float(production_row['theta_ppd']):g} angular samples per deg\n"
        f"time: {float(production_row['time_per_log10_decade']):g} samples per log10 decade"
    )
    ax.text(0.015, 0.035, production_key,
            transform=ax.transAxes, ha="left", va="bottom", fontsize=8.5,
            bbox={"facecolor": "white", "edgecolor": "0.75", "alpha": 0.9, "pad": 3.5}, zorder=20)
    restyle_legend(ax)
    ax.set_xlim(times.min(), times.max())
    fig = ax.figure
    fig.savefig(out / "resolution_light_curve_overlay.png", dpi=220, bbox_inches="tight", pad_inches=0.045)
    fig.savefig(out / "resolution_light_curve_overlay.pdf", bbox_inches="tight", pad_inches=0.045)
    plt.close(fig)


def plot_convergence(
    event: str,
    summaries: list[dict[str, str]],
    fluxes: list[dict[str, str]],
    out: Path,
    *,
    runtime_event_dir: Path | None = None,
    publication_labels: bool = False,
) -> dict[str, float]:
    rows = {row["resolution_id"]: row for row in summaries}
    flux_by_level: dict[str, np.ndarray] = {}
    for level in rows:
        values = [float(row["modeled_value"]) for row in fluxes if row["resolution_id"] == level]
        flux_by_level[level] = np.asarray(values)
    coupled = coupled_rows(rows)
    production = production_id(rows)
    production_row = rows[production]
    x = np.asarray([coupled_ratio(row, production_row) for row in coupled])
    moderate = flux_by_level[production]
    max_delta = np.asarray([finite_delta(flux_by_level[row["resolution_id"]], moderate)[2] for row in coupled])
    p95_delta = np.asarray([finite_delta(flux_by_level[row["resolution_id"]], moderate)[1] for row in coupled])
    production_chi2 = float(rows[production]["chi2"])
    chi2_delta = np.asarray([abs(float(row["chi2"]) - production_chi2) for row in coupled])
    reference = "extreme_fine"
    reference_index = [row["resolution_id"] for row in coupled].index(reference)
    production_index = [row["resolution_id"] for row in coupled].index(production)
    reference_ratio = float(x[reference_index])
    keep = production_neighborhood_indices(x, production_index)

    axis_values: list[tuple[str, float]] = []
    for level in AXIS_LEVELS:
        if level not in flux_by_level:
            continue
        _, p95, _ = finite_delta(flux_by_level[level], moderate)
        axis_values.append((level, p95))

    # Production is the actual MCMC grid, so all numerical differences are
    # referenced to it and have an interpretable zero at the production point.
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 10.0))
    axes = axes.ravel()
    axes[0].plot(x, p95_delta, "o-", color="#0a6f6a", lw=1.8, label="95th percentile")
    axes[0].plot(x, max_delta, "o:", color="#54706f", lw=1.2, ms=3.8, label="maximum")
    axes[0].scatter([x[production_index]], [0.0], marker="*", s=105, color="#9a3e00", edgecolor="black", linewidth=0.35, zorder=4)
    configure_coupled_axis(axes[0], x, 1.0, reference_ratio)
    axes[0].set_ylabel("|log10(F/F_production)| [dex]")
    axes[0].set_ylim(0.0, positive_zoom_upper(np.maximum(p95_delta, max_delta), keep))
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(x, chi2_delta, "o-", color="#a7345d", lw=1.8)
    axes[1].scatter([x[production_index]], [0.0], marker="*", s=105, color="#9a3e00", edgecolor="black", linewidth=0.35, zorder=4)
    configure_coupled_axis(axes[1], x, 1.0, reference_ratio)
    axes[1].set_ylabel("|fit statistic - production|")
    axes[1].set_ylim(0.0, positive_zoom_upper(chi2_delta, keep))
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)
    event_dir = runtime_event_dir or out.parent
    mcmc_wall_hours = recorded_mcmc_wall_hours(event_dir)
    source_host, alternate_factor, alternate_label, source_workers, alternate_workers = alternate_host_estimate(event_dir)
    model_runtime = np.asarray([float(row["runtime_seconds"]) for row in coupled])
    production_model_runtime = model_runtime[production_index]
    estimated_hours = np.full_like(model_runtime, np.nan)
    if mcmc_wall_hours is not None and production_model_runtime > 0:
        estimated_hours = mcmc_wall_hours * model_runtime / production_model_runtime
    axes[2].plot(x, estimated_hours, "o-", color="#5b4a9f", lw=1.8)
    axes[2].scatter([x[production_index]], [estimated_hours[production_index]], marker="*", s=105, color="#9a3e00", edgecolor="black", linewidth=0.35, zorder=4)
    configure_coupled_axis(axes[2], x, 1.0, reference_ratio)
    if publication_labels:
        axes[2].set_ylabel("estimated repeat-MCMC wall time [h]")
    else:
        axes[2].set_ylabel(f"estimated full MCMC on {source_host} ({source_workers} workers) [h]")
    axes[2].set_ylim(bottom=0.0)
    axes[2].grid(alpha=0.25)
    if not publication_labels and np.any(np.isfinite(estimated_hours)):
        secondary = axes[2].secondary_yaxis(
            "right",
            functions=(lambda hours: hours * alternate_factor, lambda hours: hours / alternate_factor),
        )
        secondary.set_ylabel(f"estimated on {alternate_label} ({alternate_workers} workers) [h]")
    runtime_title = (
        "production wall time x fixed-model cost ratio"
        if publication_labels
        else "recorded production MCMC wall clock x fixed-model cost ratio"
    )
    axes[2].set_title(runtime_title, fontsize=9)
    labels = [label.replace("_", "\n") for label, _ in axis_values]
    colors = ["#8ab6d6" if "coarsened" in label else "#326b96" for label, _ in axis_values]
    axes[3].bar(np.arange(len(axis_values)), [value for _, value in axis_values], color=colors, alpha=0.86)
    axes[3].set_ylabel("95th percentile |log10(F/F_production)| [dex]")
    axes[3].set_title("one-control sensitivity around production")
    axes[3].set_ylim(bottom=0.0)
    axes[3].set_xticks(np.arange(len(axis_values)), labels, fontsize=7)
    axes[3].grid(alpha=0.25, which="both")
    fig.suptitle(f"GRB {event}: production-grid-referenced VegasAfterglow resolution tests", y=0.995, fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(out / "resolution_convergence.png", dpi=180, bbox_inches="tight")
    fig.savefig(out / "resolution_convergence.pdf", bbox_inches="tight")
    plt.close(fig)
    moderate_row = rows[production]
    return {
        "event": event,
        "moderate_max_abs_log10_flux_delta": float(moderate_row["max_abs_log10_flux_delta"]),
        "moderate_p95_abs_log10_flux_delta": float(moderate_row["p95_abs_log10_flux_delta"]),
        "very_coarse_max_abs_log10_flux_delta": float(rows["very_coarse"]["max_abs_log10_flux_delta"]),
        "physics_runtime_seconds": sum(float(row["runtime_seconds"]) for row in summaries),
    }


def plot_signed_convergence(
    event: str,
    summaries: list[dict[str, str]],
    fluxes: list[dict[str, str]],
    out: Path,
    *,
    runtime_event_dir: Path | None = None,
    publication_labels: bool = False,
) -> None:
    """Show directional numerical shifts relative to production, without absolutes."""
    rows = {row["resolution_id"]: row for row in summaries}
    flux_by_level: dict[str, np.ndarray] = {}
    for level in rows:
        flux_by_level[level] = np.asarray(
            [float(row["modeled_value"]) for row in fluxes if row["resolution_id"] == level],
            dtype=float,
        )
    coupled = coupled_rows(rows)
    production = production_id(rows)
    production_row = rows[production]
    x = np.asarray([coupled_ratio(row, production_row) for row in coupled])
    production_index = [row["resolution_id"] for row in coupled].index(production)
    reference_index = [row["resolution_id"] for row in coupled].index("extreme_fine")
    reference_ratio = float(x[reference_index])
    production_flux = flux_by_level[production]
    quantiles = np.asarray([
        signed_log_ratio_quantiles(flux_by_level[row["resolution_id"]], production_flux)
        for row in coupled
    ])
    signed_statistic = np.asarray([float(row["chi2"]) - float(rows[production]["chi2"]) for row in coupled])

    keep = production_neighborhood_indices(x, production_index)

    axis_values: list[tuple[str, float]] = []
    for level in AXIS_LEVELS:
        if level not in flux_by_level:
            continue
        _, p95, _ = finite_delta(flux_by_level[level], production_flux)
        axis_values.append((level, p95))

    fig, axes = plt.subplots(2, 2, figsize=(12.2, 10.0))
    axes = axes.ravel()
    axes[0].fill_between(x, quantiles[:, 0], quantiles[:, 2], color="#0a6f6a", alpha=0.18, label="16th--84th percentile")
    axes[0].plot(x, quantiles[:, 1], "o-", color="#0a6f6a", lw=1.8, label="median")
    axes[0].scatter([x[production_index]], [0.0], marker="*", s=105, color="#9a3e00", edgecolor="black", linewidth=0.35, zorder=4)
    axes[0].axhline(0.0, color="0.35", lw=1.0, zorder=0)
    configure_coupled_axis(axes[0], x, 1.0, reference_ratio)
    axes[0].set_ylabel("signed log10(F/F_production) [dex]")
    axes[0].set_ylim(*signed_production_zoom_limits(quantiles, keep))
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)

    axes[1].plot(x, signed_statistic, "o-", color="#a7345d", lw=1.8)
    axes[1].scatter([x[production_index]], [0.0], marker="*", s=105, color="#9a3e00", edgecolor="black", linewidth=0.35, zorder=4)
    axes[1].axhline(0.0, color="0.35", lw=1.0, zorder=0)
    configure_coupled_axis(axes[1], x, 1.0, reference_ratio)
    axes[1].set_ylabel("fit statistic - production")
    axes[1].set_ylim(*signed_production_zoom_limits(signed_statistic, keep))
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)

    event_dir = runtime_event_dir or out.parent
    mcmc_wall_hours = recorded_mcmc_wall_hours(event_dir)
    source_host, alternate_factor, alternate_label, source_workers, alternate_workers = alternate_host_estimate(event_dir)
    model_runtime = np.asarray([float(row["runtime_seconds"]) for row in coupled])
    production_model_runtime = model_runtime[production_index]
    estimated_hours = np.full_like(model_runtime, np.nan)
    if mcmc_wall_hours is not None and production_model_runtime > 0:
        estimated_hours = mcmc_wall_hours * model_runtime / production_model_runtime
    axes[2].plot(x, estimated_hours, "o-", color="#5b4a9f", lw=1.8)
    axes[2].scatter([x[production_index]], [estimated_hours[production_index]], marker="*", s=105, color="#9a3e00", edgecolor="black", linewidth=0.35, zorder=4)
    configure_coupled_axis(axes[2], x, 1.0, reference_ratio)
    if publication_labels:
        axes[2].set_ylabel("estimated repeat-MCMC wall time [h]")
    else:
        axes[2].set_ylabel(f"estimated full MCMC on {source_host} ({source_workers} workers) [h]")
    axes[2].set_ylim(bottom=0.0)
    axes[2].grid(alpha=0.25)
    if not publication_labels and np.any(np.isfinite(estimated_hours)):
        secondary = axes[2].secondary_yaxis(
            "right",
            functions=(lambda hours: hours * alternate_factor, lambda hours: hours / alternate_factor),
        )
        secondary.set_ylabel(f"estimated on {alternate_label} ({alternate_workers} workers) [h]")
    runtime_title = (
        "production wall time x fixed-model cost ratio"
        if publication_labels
        else "recorded production MCMC wall clock x fixed-model cost ratio"
    )
    axes[2].set_title(runtime_title, fontsize=9)

    labels = [label.replace("_", "\n") for label, _ in axis_values]
    colors = ["#8ab6d6" if "coarsened" in label else "#326b96" for label, _ in axis_values]
    axes[3].bar(np.arange(len(axis_values)), [value for _, value in axis_values], color=colors, alpha=0.86)
    axes[3].set_ylabel("95th percentile |log10(F/F_production)| [dex]")
    axes[3].set_title("one-control magnitude sensitivity around production")
    axes[3].set_ylim(bottom=0.0)
    axes[3].set_xticks(np.arange(len(axis_values)), labels, fontsize=7)
    axes[3].grid(alpha=0.25)
    fig.suptitle(f"GRB {event}: signed numerical shifts and resolution cost", y=0.995, fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(out / "resolution_convergence_signed.png", dpi=180, bbox_inches="tight")
    fig.savefig(out / "resolution_convergence_signed.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_campaign(rows_by_event: dict[str, list[dict[str, str]]], table: list[dict[str, float]], out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    colors = plt.get_cmap("tab10", len(rows_by_event))
    for color, (event, summaries) in zip(colors.colors, sorted(rows_by_event.items())):
        by_level = {row["resolution_id"]: row for row in summaries}
        coupled = coupled_rows(by_level)
        x = [float(row["phi_ppd"]) for row in coupled]
        y = [max(float(row["max_abs_log10_flux_delta"]), 1e-6) for row in coupled]
        axes[0].plot(x, y, "o-", color=color, alpha=0.75, ms=3, label=event)
    axes[0].set(xscale="log", yscale="log", xlabel="coupled phi resolution [per degree]", ylabel="max |log10(F/F_extreme)|")
    axes[0].grid(alpha=0.25, which="both")
    axes[0].legend(fontsize=7, ncol=2)
    ordered = sorted(table, key=lambda row: row["moderate_max_abs_log10_flux_delta"])
    events = [row["event"] for row in ordered]
    values = [max(row["moderate_max_abs_log10_flux_delta"], 1e-6) for row in ordered]
    axes[1].barh(events, values, color="#b45f3c", alpha=0.78)
    axes[1].axvline(0.01, color="#4d4d4d", lw=1, ls="--", label="0.01 dex")
    axes[1].set(xscale="log", xlabel="moderate max |log10(F/F_extreme)|", title="current campaign resolution")
    axes[1].grid(axis="x", alpha=0.25, which="both")
    axes[1].legend(fontsize=8)
    fig.suptitle("Final-final VegasAfterglow resolution convergence", y=1.02, fontsize=14)
    fig.tight_layout()
    fig.savefig(out / "campaign_resolution_convergence.png", dpi=180, bbox_inches="tight")
    fig.savefig(out / "campaign_resolution_convergence.pdf", bbox_inches="tight")
    plt.close(fig)


def load_viewing_geometry(event_dir: Path) -> dict[str, float]:
    metadata = json.loads((event_dir / "resolution_run_metadata.json").read_text())
    source = Path(metadata["source_results"])
    payload = json.loads((source / "minimized" / "minimized.json").read_text())
    model = payload["params"]["model"]
    theta_v = float(model["theta_v"])
    theta_c = float(model["theta_c"])
    return {
        "theta_v_rad": theta_v,
        "theta_v_deg": float(np.degrees(theta_v)),
        "theta_c_rad": theta_c,
        "theta_c_deg": float(np.degrees(theta_c)),
        "theta_v_over_theta_c": theta_v / theta_c,
    }


def plot_viewing_angle(table: list[dict[str, float]], out: Path) -> None:
    ordered = sorted(table, key=lambda row: row["theta_v_deg"])
    x = np.asarray([row["theta_v_deg"] for row in ordered])
    y = np.asarray([max(row["moderate_max_abs_log10_flux_delta"], 1e-6) for row in ordered])
    color = np.asarray([row["theta_v_over_theta_c"] for row in ordered])
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    points = ax.scatter(x, y, c=color, cmap="viridis", s=58, edgecolor="black", linewidth=0.45, zorder=3)
    for row, x_value, y_value in zip(ordered, x, y):
        ax.annotate(row["event"], (x_value, y_value), xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.axhline(0.01, color="#4d4d4d", lw=1, ls="--", label="0.01 dex guide")
    ax.set(xlabel="viewing angle theta_v [deg]", ylabel="moderate max |log10(F/F_extreme)|", yscale="log")
    ax.grid(alpha=0.25, which="both")
    ax.legend(frameon=False)
    colorbar = fig.colorbar(points, ax=ax)
    colorbar.set_label("theta_v / theta_c")
    fig.suptitle("VegasAfterglow convergence versus viewing angle", y=0.98, fontsize=13)
    fig.tight_layout()
    fig.savefig(out / "convergence_vs_viewing_angle.png", dpi=180)
    fig.savefig(out / "convergence_vs_viewing_angle.pdf")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    if args.event_dir:
        event_dir = args.event_dir.expanduser().resolve()
        out_root = (args.out_root or event_dir).expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)
        summaries = read_csv(event_dir / "resolution_summary.csv")
        fluxes = read_csv(event_dir / "modeled_observation_fluxes.csv")
        if not summaries or not fluxes:
            raise ValueError(f"Incomplete event resolution products in {event_dir}")
        event = summaries[0]["event"]
        if not args.convergence_only:
            plot_light_curves(event, summaries, fluxes, out_root)
        plot_convergence(
            event,
            summaries,
            fluxes,
            out_root,
            runtime_event_dir=event_dir.parent,
            publication_labels=args.publication_labels,
        )
        plot_signed_convergence(
            event,
            summaries,
            fluxes,
            out_root,
            runtime_event_dir=event_dir.parent,
            publication_labels=args.publication_labels,
        )
        (out_root / ".resolution_plot_version").write_text(PLOT_VERSION + "\n")
        print(f"PLOTTED {event}")
        return
    if args.campaign:
        campaign = args.campaign.expanduser().resolve()
        out_root = (args.out_root or campaign / "comparison_plots").expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)
        campaign_table: list[dict[str, float]] = []
        rows_by_event: dict[str, list[dict[str, str]]] = {}
        for event_dir in sorted(path for path in campaign.iterdir() if path.is_dir()):
            source = event_dir / "resolution_ladder"
            summaries = read_csv(source / "resolution_summary.csv") if (source / "resolution_summary.csv").is_file() else []
            fluxes = read_csv(source / "modeled_observation_fluxes.csv") if (source / "modeled_observation_fluxes.csv").is_file() else []
            if not summaries or not fluxes:
                continue
            row = plot_convergence(event_dir.name, summaries, fluxes, source)
            row.update(load_viewing_geometry(source))
            campaign_table.append(row)
            rows_by_event[event_dir.name] = summaries
        if not campaign_table:
            raise ValueError(f"No complete event resolution ladders in {campaign}")
        fields = list(campaign_table[0])
        with (out_root / "campaign_resolution_summary.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(sorted(campaign_table, key=lambda row: row["event"]))
        plot_campaign(rows_by_event, campaign_table, out_root)
        plot_viewing_angle(campaign_table, out_root)
        print(f"PLOTTED campaign {campaign.name}")
        return
    results_root = args.results_root.expanduser().resolve()
    out_root = (args.out_root or results_root).expanduser().resolve()
    events = sorted(path.name for path in results_root.iterdir() if path.is_dir() and (path / "resolution_summary.csv").is_file())
    if not events:
        raise ValueError(f"No resolution results found in {results_root}")
    campaign_table: list[dict[str, float]] = []
    rows_by_event: dict[str, list[dict[str, str]]] = {}
    for event in events:
        source = results_root / event
        target = out_root / event
        target.mkdir(parents=True, exist_ok=True)
        summaries = read_csv(source / "resolution_summary.csv")
        fluxes = read_csv(source / "modeled_observation_fluxes.csv")
        plot_light_curves(event, summaries, fluxes, target)
        row = plot_convergence(event, summaries, fluxes, target)
        plot_signed_convergence(event, summaries, fluxes, target)
        (target / ".resolution_plot_version").write_text(PLOT_VERSION + "\n")
        row.update(load_viewing_geometry(source))
        campaign_table.append(row)
        rows_by_event[event] = summaries
        print(f"PLOTTED {event}")
    fields = list(campaign_table[0])
    with (out_root / "campaign_resolution_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(campaign_table, key=lambda row: row["event"]))
    plot_campaign(rows_by_event, campaign_table, out_root)
    plot_viewing_angle(campaign_table, out_root)
    print(f"WROTE {out_root}")


if __name__ == "__main__":
    main()
