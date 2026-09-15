#!/usr/bin/env python3
"""Compare the matched 090424 CCM and Trotter bandpass diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jetfit.ampy import Ampy
from jetfit.core import utils
from jetfit.mcmc.mcmc import (
    calibration_offsets,
    chi_squared,
    log_likelihood_fn,
    log_posterior_fn,
    slop,
)
from scripts.minimize import initial_from_best_fit
from scripts.plot.base import OPTION_MAP
from scripts.plot.visualize import LightCurvePlot
from scripts.plot_spread_light_curves import (
    DEFAULT_SPACING,
    SEC_PER_DAY,
    attach_axis,
    fast_model_fluxes,
    load_spacing,
)


VARIANTS = {
    "CCM": "ccm",
    "Trotter": "trotter",
}


def wall_clock_seconds(result: Path, explicit_log: Path | None = None) -> float | None:
    candidates = [explicit_log, result / "run.log", ROOT / "logs" / f"{result.name}.log"]
    for path in candidates:
        if path is None or not path.is_file():
            continue
        matches = re.findall(r"^real\s+([0-9]+(?:\.[0-9]+)?)\s*$", path.read_text(), re.MULTILINE)
        if matches:
            return float(matches[-1])
    return None


def evaluate(
    result: Path, config: Path, label: str, runtime_log: Path | None = None
):
    best = json.loads((result / "best_fit.json").read_text())
    ampy = Ampy(
        config / "obs.csv",
        config / "model.toml",
        bandpass_integration="verified",
        bandpass_nodes=16,
    )
    theta = initial_from_best_fit(ampy, best)
    params = ampy.mcmc.params.samples_to_dict(theta)
    obs = ampy.mcmc.models.obs
    modeled = ampy.mcmc.models.model(params)
    modeled = calibration_offsets(modeled, params.get("offsets"), obs.offsets)
    fitted_slop = slop(params.get("slop"), obs)

    values = np.asarray(obs.as_arrays.values, dtype=float)
    errors = np.asarray(obs.as_arrays.errors, dtype=float)
    bands = np.asarray(obs.as_arrays.bands, dtype=str)
    flux = np.asarray(obs.flux_loc, dtype=bool)
    spectral_index = np.asarray(obs.sindex_loc, dtype=bool)
    fractional = (modeled - values) / values

    loglike = log_likelihood_fn(theta, ampy.mcmc.params, ampy.mcmc.models)
    logpost = log_posterior_fn(theta, ampy.mcmc.params, ampy.mcmc.models)
    ndata = int(obs.length)
    nparams = int(theta.size)
    with np.load(result / "chain.npz", allow_pickle=False) as archive:
        chain = np.asarray(archive["chain"], dtype=float)
    if chain.ndim != 3 or chain.shape[-1] != nparams:
        raise ValueError(f"Unexpected {label} chain shape: {chain.shape}")
    flat_chain = chain.reshape(-1, nparams)
    posterior = {}
    for index, parameter in enumerate(ampy.mcmc.params.fitting):
        q16, q50, q84 = np.percentile(flat_chain[:, index], [16.0, 50.0, 84.0])
        posterior[parameter.name] = {
            "q16": float(q16),
            "median": float(q50),
            "q84": float(q84),
            "scale": str(getattr(parameter.scale, "value", parameter.scale)),
        }
    summary = {
        "model": label,
        "observations": ndata,
        "fitted_parameters": nparams,
        "minus2_log_likelihood": float(-2.0 * loglike),
        "minus2_log_posterior": float(-2.0 * logpost),
        "minus2_log_prior": float((-2.0 * logpost) - (-2.0 * loglike)),
        "aic": float(-2.0 * loglike + 2.0 * nparams),
        "bic": float(-2.0 * loglike + nparams * math.log(ndata)),
        "best_extinction": best.get("extinction", {}),
    }
    runtime = wall_clock_seconds(result, runtime_log)
    summary["wall_clock_seconds"] = runtime
    summary["wall_clock_hours"] = runtime / 3600.0 if runtime is not None else None

    rows = []
    for band in sorted(set(bands[flux]), key=str.lower):
        mask = flux & (bands == band)
        band_slop = (
            fitted_slop
            if np.isscalar(fitted_slop)
            else np.asarray(fitted_slop)[mask]
        )
        statistic = utils.chi_squared(
            modeled[mask], values[mask], errors[mask], band_slop
        )
        rows.append(_residual_row(label, band, mask, statistic, fractional))

    if spectral_index.any():
        statistic = utils.chi_squared(
            modeled[spectral_index], values[spectral_index], errors[spectral_index]
        )
        rows.append(
            _residual_row(
                label, "spectral_index", spectral_index, statistic, fractional
            )
        )

    total = chi_squared(modeled, obs, fitted_slop)
    rows.append(
        _residual_row(
            label, "ALL", np.ones(ndata, dtype=bool), total, fractional
        )
    )
    if not np.isclose(total, -2.0 * loglike, rtol=0.0, atol=1.0e-8):
        raise RuntimeError("Per-result likelihood decomposition is inconsistent.")
    return summary, rows, posterior, {"ampy": ampy, "params": params}


def _residual_row(label, band, mask, statistic, fractional):
    selected = fractional[mask]
    return {
        "model": label,
        "band": band,
        "n": int(mask.sum()),
        "minus2_log_likelihood": float(statistic),
        "median_fractional_residual": float(np.median(selected)),
        "median_abs_fractional_residual": float(np.median(np.abs(selected))),
        "rms_fractional_residual": float(np.sqrt(np.mean(selected**2))),
    }


def write_posterior_comparison(path: Path, posteriors: dict) -> list[dict]:
    common = sorted(set(posteriors["CCM"]) & set(posteriors["Trotter"]))
    rows = []
    for name in common:
        ccm = posteriors["CCM"][name]
        trotter = posteriors["Trotter"][name]
        ccm_sigma = 0.5 * (ccm["q84"] - ccm["q16"])
        trotter_sigma = 0.5 * (trotter["q84"] - trotter["q16"])
        pooled = math.sqrt(ccm_sigma**2 + trotter_sigma**2)
        delta = trotter["median"] - ccm["median"]
        rows.append(
            {
                "parameter": name,
                "scale": ccm["scale"],
                "ccm_q16": ccm["q16"],
                "ccm_median": ccm["median"],
                "ccm_q84": ccm["q84"],
                "trotter_q16": trotter["q16"],
                "trotter_median": trotter["median"],
                "trotter_q84": trotter["q84"],
                "trotter_minus_ccm": delta,
                "standardized_shift": delta / pooled if pooled > 0.0 else float("nan"),
            }
        )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def save_figure(fig, output_dir: Path, stem: str) -> None:
    for suffix in ("png", "pdf"):
        fig.savefig(output_dir / f"{stem}.{suffix}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def calibration_factors_by_band(ampy: Ampy, params: dict) -> dict[str, float]:
    """Return the multiplicative per-band corrections used by the likelihood."""
    bands = np.asarray(ampy.obs.as_arrays.bands, dtype=str)
    offsets = params.get("offsets") or {}
    factors: dict[str, float] = {}
    for name, mask in ampy.obs.offsets.items():
        value = offsets.get(name)
        if value is None:
            continue
        for band in set(bands[np.asarray(mask, dtype=bool)]):
            factor = 10.0 ** (-0.4 * float(value))
            if band in factors and not np.isclose(factors[band], factor):
                raise ValueError(f"Band {band!r} has multiple calibration offsets.")
            factors[band] = factor
    return factors


def plot_light_curve_comparison(states: dict[str, dict], output_dir: Path) -> None:
    """Plot the fitted CCM and Trotter light curves on the shared data set."""
    baseline = states["CCM"]
    ampy = baseline["ampy"]
    obs_times = np.asarray(ampy.obs.as_arrays.times, dtype=float)
    flux_rows = np.asarray(ampy.obs.flux_loc, dtype=bool)
    valid_times = obs_times[flux_rows & np.isfinite(obs_times) & (obs_times > 0.0)]
    times = np.geomspace(valid_times.min() / 2.0, valid_times.max() * 2.0, 120)
    spacing = load_spacing(DEFAULT_SPACING, "090424")
    styles = {
        "CCM": {"ls": "--", "lw": 2.1, "alpha": 1.0},
        "Trotter": {"ls": "-", "lw": 1.55, "alpha": 0.9},
    }
    helpers: dict[str, LightCurvePlot] = {}
    curves: dict[str, dict[str, np.ndarray]] = {}
    csv_rows: list[dict] = []
    for label, state in states.items():
        variant_ampy = state["ampy"]
        params = state["params"]
        helper = LightCurvePlot(
            variant_ampy.mcmc.models.afg_model,
            params,
            variant_ampy.obs,
            meta=variant_ampy.mcmc.models.afg_kw,
        )
        helpers[label] = helper
        factors = calibration_factors_by_band(variant_ampy, params)
        raw_curves = fast_model_fluxes(
            helper, params, times, variant_ampy.extinction_model
        )
        curves[label] = {
            band: np.asarray(values, dtype=float) * factors.get(band, 1.0)
            for band, values in raw_curves.items()
        }
        for band, values in curves[label].items():
            spread = spacing.get(band, 1.0)
            csv_rows.extend(
                {
                    "event": "090424",
                    "model": label,
                    "band": band,
                    "time_days": float(time),
                    "model_flux_density_mjy": float(flux),
                    "plot_spacing_factor": float(spread),
                    "plotted_flux_density_mjy": float(flux * spread),
                }
                for time, flux in zip(times, values)
            )

    csv_path = output_dir / "090424_ccm_vs_trotter_light_curves.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(csv_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    fig, (ax, ratio_ax) = plt.subplots(
        2, 1, figsize=(8.2, 10.0), height_ratios=(2.1, 1.0), sharex=True
    )
    helper = attach_axis(helpers["CCM"], ax)
    for label in ("CCM", "Trotter"):
        for band, values in curves[label].items():
            if band not in OPTION_MAP:
                continue
            ax.loglog(
                times,
                values * spacing.get(band, 1.0),
                color=OPTION_MAP[band]["color"],
                zorder=3 if label == "CCM" else 4,
                **styles[label],
            )
    helper.plot_observation(
        baseline["params"], spreads=spacing, offset=False, excluded=True
    )
    ax.set_ylabel("Scaled Flux Density [mJy]")
    ax.set_title("GRB 090424: fitted source-frame extinction comparison")
    ax.grid(alpha=0.25, which="both")
    band_handles, band_labels = ax.get_legend_handles_labels()
    if band_handles:
        band_legend = ax.legend(
            band_handles,
            band_labels,
            loc="upper right",
            ncols=2,
            fontsize=6.5,
            frameon=True,
            fancybox=False,
            framealpha=0.92,
        )
        ax.add_artist(band_legend)
    ax.legend(
        handles=[
            Line2D([0], [0], color="0.2", label=label, **styles[label])
            for label in ("CCM", "Trotter")
        ],
        loc="lower left",
        fontsize=8,
        frameon=True,
        fancybox=False,
    )

    for band, ccm_values in curves["CCM"].items():
        if band not in curves["Trotter"] or band not in OPTION_MAP:
            continue
        ratio = np.divide(
            curves["Trotter"][band],
            ccm_values,
            out=np.full_like(ccm_values, np.nan),
            where=(curves["Trotter"][band] > 0.0) & (ccm_values > 0.0),
        )
        ratio_ax.plot(
            times,
            np.log10(ratio),
            color=OPTION_MAP[band]["color"],
            linewidth=1.5,
            alpha=0.9,
        )
    ratio_ax.axhline(0.0, color="0.25", linewidth=0.9)
    ratio_ax.set_xscale("log")
    ratio_ax.set_xlabel("Time Since Trigger [days]")
    ratio_ax.set_ylabel(r"$\log_{10}(F_{\rm Trotter}/F_{\rm CCM})$")
    ratio_ax.grid(alpha=0.25, which="both")
    seconds = ax.secondary_xaxis(
        "top",
        functions=(lambda day: day * SEC_PER_DAY, lambda sec: sec / SEC_PER_DAY),
    )
    seconds.set_xlabel("Time Since Trigger [seconds]")
    plt.close(helpers["Trotter"].ax.figure)
    fig.tight_layout()
    save_figure(fig, output_dir, "090424_ccm_vs_trotter_light_curve_comparison")


def plot_band_differences(rows: list[dict], output_dir: Path) -> None:
    by_model = {
        model: {row["band"]: row for row in rows if row["model"] == model}
        for model in VARIANTS
    }
    bands = sorted(
        set(by_model["CCM"]) & set(by_model["Trotter"]) - {"ALL"},
        key=lambda band: abs(
            by_model["Trotter"][band]["minus2_log_likelihood"]
            - by_model["CCM"][band]["minus2_log_likelihood"]
        ),
    )
    delta = np.asarray(
        [
            by_model["Trotter"][band]["minus2_log_likelihood"]
            - by_model["CCM"][band]["minus2_log_likelihood"]
            for band in bands
        ]
    )
    height = max(4.5, 0.28 * len(bands))
    fig, ax = plt.subplots(figsize=(8.0, height))
    colors = np.where(delta < 0.0, "#2a7f62", "#b24a4a")
    ax.barh(bands, delta, color=colors)
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel(r"Trotter minus CCM $(-2\ln\mathcal{L})$")
    ax.set_ylabel("Observed band")
    ax.set_title("GRB 090424: extinction-model fit difference by band")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, output_dir, "090424_ccm_vs_trotter_band_fit_difference")


def plot_parameter_shifts(rows: list[dict], output_dir: Path) -> None:
    finite = [row for row in rows if math.isfinite(row["standardized_shift"])]
    finite.sort(key=lambda row: abs(row["standardized_shift"]))
    labels = [row["parameter"] for row in finite]
    shifts = np.asarray([row["standardized_shift"] for row in finite])
    height = max(5.0, 0.30 * len(labels))
    fig, ax = plt.subplots(figsize=(8.0, height))
    colors = np.where(shifts < 0.0, "#3f78a8", "#b96b2c")
    ax.barh(labels, shifts, color=colors)
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.axvline(-1.0, color="0.5", linewidth=0.8, linestyle="--")
    ax.axvline(1.0, color="0.5", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Posterior median shift (pooled 68% half-widths)")
    ax.set_ylabel("Common fitted parameter")
    ax.set_title("GRB 090424: Trotter minus CCM posterior shifts")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, output_dir, "090424_ccm_vs_trotter_common_parameter_shifts")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/2026_09_10_trotter_extinction_review"),
    )
    parser.add_argument("--ccm-log", type=Path, default=None)
    parser.add_argument("--trotter-log", type=Path, default=None)
    parser.add_argument(
        "--ccm-results",
        type=Path,
        default=None,
        help="CCM result directory; defaults to the completed short diagnostic.",
    )
    parser.add_argument(
        "--trotter-results",
        type=Path,
        default=None,
        help="Trotter result directory; defaults to the completed short diagnostic.",
    )
    args = parser.parse_args()
    root = ROOT
    results = {
        "CCM": args.ccm_results
        or root / "jetfit/results/090424_ccm_bandpass_verified_5temp_25x100_v1",
        "Trotter": args.trotter_results
        or root / "jetfit/results/090424_trotter_bandpass_verified_5temp_25x100_v1",
    }
    summaries = {}
    posteriors = {}
    states = {}
    rows = []
    runtime_logs = {"CCM": args.ccm_log, "Trotter": args.trotter_log}
    for label, variant in VARIANTS.items():
        config = root / "run_configs" / "bandpass_integration" / f"090424_{variant}"
        summary, model_rows, posterior, state = evaluate(
            results[label], config, label, runtime_logs[label]
        )
        summaries[label] = summary
        posteriors[label] = posterior
        states[label] = state
        rows.extend(model_rows)

    differences = {
        key: summaries["Trotter"][key] - summaries["CCM"][key]
        for key in (
            "minus2_log_likelihood",
            "minus2_log_posterior",
            "aic",
            "bic",
        )
    }
    payload = {
        "models": summaries,
        "trotter_minus_ccm": differences,
        "interpretation": (
            "Negative deltas favor Trotter. AIC and BIC are approximate "
            "diagnostics, not a substitute for Bayesian evidence."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "090424_verified_bandpass_model_comparison.json"
    csv_path = args.output_dir / "090424_ccm_vs_trotter_verified_bandpass_residuals.csv"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    posterior_path = args.output_dir / "090424_ccm_vs_trotter_posterior_comparison.csv"
    posterior_rows = write_posterior_comparison(posterior_path, posteriors)
    plot_band_differences(rows, args.output_dir)
    plot_parameter_shifts(posterior_rows, args.output_dir)
    plot_light_curve_comparison(states, args.output_dir)
    print(json.dumps(payload, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {posterior_path}")


if __name__ == "__main__":
    main()
