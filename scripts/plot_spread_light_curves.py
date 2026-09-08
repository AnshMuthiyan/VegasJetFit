#!/usr/bin/env python3
"""Generate spread-out light-curve previews with posterior overlays.

This is the paper-style companion to the standard physical-unit light curve:
bands are multiplied by event-specific factors to separate them vertically while
keeping the time axis in physical units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np
from astropy import units as u

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.ampy import Ampy
from jetfit.core.utils import add_collision_aware_grb_label
from jetfit.mcmc.parameters import Parameters
from scripts.plot.base import OPTION_MAP
from scripts.plot.visualize import LABELS, LightCurvePlot, model_extinction

DEFAULT_SPACING = Path(__file__).resolve().parent / "events" / "spacing.json"
SEC_PER_DAY = 86400.0
# Version 5 repairs mixed-band Galactic extinction and records the exact fit
# inputs used to build a cache, preventing stale posterior curves after a
# model, chain, or minimized-solution change.
CACHE_VERSION = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="Finished run directory.")
    parser.add_argument("--event", default=None, help="GRB name. Defaults to run-directory prefix.")
    parser.add_argument("--spacing", default=DEFAULT_SPACING, type=Path, help="Band spacing JSON.")
    parser.add_argument("--ncurves", default=100, type=int, help="Number of posterior curves for shaded plot.")
    parser.add_argument("--seed", default=1729, type=int, help="RNG seed for posterior draw plot.")
    parser.add_argument("--ndata", default=80, type=int, help="Number of model times per band.")
    parser.add_argument("--walker-limit", default=0, type=int, help="Number of final walkers to draw in the walker plot. Use 0 for all walkers.")
    return parser.parse_args()


def infer_event(run_dir: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    if run_dir.name and run_dir.name[0].isdigit():
        return run_dir.name.split("_", 1)[0]
    raise ValueError(f"Could not infer event from {run_dir}")


def load_postfit_params(run_dir: Path) -> tuple[dict[str, Any], str, float | None]:
    minimized = run_dir / "minimized" / "minimized.json"
    if minimized.exists():
        payload = json.loads(minimized.read_text())
        return payload.get("params", payload), "minimized/minimized.json", _float_or_none(payload.get("nmap"))

    best = run_dir / "best_fit.json"
    if best.exists():
        payload = json.loads(best.read_text())
        return payload, "best_fit.json", _float_or_none(payload.get("nmap"))

    raise FileNotFoundError(f"No minimized/minimized.json or best_fit.json in {run_dir}")


def _float_or_none(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def load_spacing(path: Path, event: str) -> dict[str, float]:
    payload = json.loads(path.read_text())
    if event not in payload:
        raise KeyError(f"No spread/spacing entry for {event} in {path}")
    return {str(k): float(v) for k, v in payload[event].items()}


def load_chain_samples(run_dir: Path) -> tuple[np.ndarray, np.ndarray | None]:
    chain_path = run_dir / "chain.npz"
    if not chain_path.exists():
        raise FileNotFoundError(f"Missing chain.npz in {run_dir}")
    with np.load(chain_path) as data:
        chain = np.asarray(data["chain"], dtype=float)
        lnprob = np.asarray(data["lnprob"], dtype=float) if "lnprob" in data.files else None
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if lnprob is not None and lnprob.ndim == 3:
        lnprob = lnprob[:, 0, :]
    if chain.ndim != 3:
        raise ValueError(f"Expected cold chain shape [steps, walkers, ndim], got {chain.shape}")
    return chain, lnprob


def final_walker_samples(run_dir: Path, limit: int | None = None) -> tuple[np.ndarray, list[str]]:
    params = Parameters.from_toml(run_dir / "model.toml")
    chain, _ = load_chain_samples(run_dir)
    final = chain[-1, :, :]
    if limit is not None and limit > 0:
        final = final[: min(limit, final.shape[0]), :]
    return np.asarray(final, dtype=float), [p.name for p in params.fitting]


def samples_to_param_dicts(run_dir: Path, samples: np.ndarray) -> list[dict[str, Any]]:
    params = Parameters.from_toml(run_dir / "model.toml")
    return [params.samples_to_dict(sample) for sample in np.asarray(samples, dtype=float)]


def final_walker_count(run_dir: Path) -> int:
    chain, _ = load_chain_samples(run_dir)
    return int(chain.shape[1])


def cache_input_signature(run_dir: Path) -> str:
    """Identify the fit inputs that determine cached light-curve arrays."""
    candidates = [
        run_dir / "model.toml",
        run_dir / "chain.npz",
        run_dir / "minimized" / "minimized.json",
        run_dir / "best_fit.json",
    ]
    digest = hashlib.sha256()
    for path in candidates:
        if not path.is_file():
            continue
        stat = path.stat()
        digest.update(str(path.name).encode("utf-8"))
        digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode("ascii"))
        if path.suffix in {".toml", ".json"}:
            digest.update(path.read_bytes())
    return digest.hexdigest()


def random_posterior_samples(run_dir: Path, ncurves: int, seed: int) -> tuple[np.ndarray, list[str]]:
    params = Parameters.from_toml(run_dir / "model.toml")
    chain, lnprob = load_chain_samples(run_dir)
    flat = chain.reshape((-1, chain.shape[-1]))
    valid = np.ones(flat.shape[0], dtype=bool)
    if lnprob is not None:
        valid = np.isfinite(lnprob.reshape((-1,)))
    flat = flat[valid]
    if flat.size == 0:
        raise ValueError("No finite posterior samples available for light-curve preview")
    rng = np.random.default_rng(seed)
    idx = rng.choice(flat.shape[0], size=min(ncurves, flat.shape[0]), replace=False)
    return np.asarray(flat[idx], dtype=float), [p.name for p in params.fitting]


def fast_model_fluxes(lcg: LightCurvePlot, params: dict[str, Any], times: np.ndarray, ext_model) -> dict[str, np.ndarray]:
    """Evaluate all spectral bands for one parameter set in one VA call."""
    spectral_data = [d for d in lcg.get_spectral_data() if str(d.band) != "nan"]
    integrated_data = [d for d in lcg.get_integrated_data() if str(d.band) != "nan"]
    if not spectral_data and not integrated_data:
        return {}

    ag_model = lcg.model(**params.get("model"), **lcg.meta)
    fluxes: dict[str, np.ndarray] = {}

    # Spectral-flux bands are grouped into one paired time/frequency call.
    bands = [str(d.band) for d in spectral_data]
    nu = np.asarray([d.frequency.to_value("Hz") for d in spectral_data], dtype=float)
    nband = len(spectral_data)
    nt = len(times)

    if nband:
        # VegasAfterglow requires the time array to be ascending, so group all
        # bands at each time rather than all times for each band.
        t_flat = np.repeat(np.asarray(times, dtype=float), nband)
        nu_flat = np.tile(nu, nt)
        sdata_flat = [d for _ in range(nt) for d in spectral_data]

        flux_flat = np.asarray(ag_model.spectral_flux(t_flat, nu_flat), dtype=float)
        if ext_model is not None:
            flux_flat = np.asarray(model_extinction(flux_flat, ext_model, sdata_flat, params), dtype=float)

        flux_grid = flux_flat.reshape(nt, nband).T
        fluxes.update({band: flux_grid[i] for i, band in enumerate(bands)})

    # XRT is stored as an integrated-flux band in the standard observation
    # object. Convert integrated flux to flux density, matching LightCurvePlot.
    for datum in integrated_data:
        lower = np.full(nt, datum.int_range.lower.to_value("Hz"), dtype=float)
        upper = np.full(nt, datum.int_range.upper.to_value("Hz"), dtype=float)
        iflux = np.asarray(ag_model.integrated_flux(np.asarray(times, dtype=float), lower=lower, upper=upper), dtype=float)
        iflux_q = u.Quantity(iflux, unit=lcg.observation.as_arrays.if_units)
        fluxes[str(datum.band)] = (iflux_q / datum.int_range.width).to_value("mJy")

    return fluxes


def model_fluxes_for_params(lcg: LightCurvePlot, params_list: list[dict[str, Any]], times: np.ndarray, ext_model) -> dict[str, np.ndarray]:
    stacks: dict[str, list[np.ndarray]] = {}
    for params in params_list:
        fluxes = fast_model_fluxes(lcg, params, times, ext_model)
        for band, flux in fluxes.items():
            stacks.setdefault(str(band), []).append(np.asarray(flux, dtype=float))
    return {band: np.asarray(curves, dtype=float) for band, curves in stacks.items() if curves}


def _cache_key(band: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]+", "_", str(band)).strip("_") or "band"


def write_flux_stack_cache(
    path: Path,
    *,
    times: np.ndarray,
    best_fluxes: dict[str, np.ndarray],
    posterior_fluxes: dict[str, np.ndarray] | None = None,
    walker_fluxes: dict[str, np.ndarray] | None = None,
    parameter_names: list[str] | None = None,
    posterior_samples: np.ndarray | None = None,
    walker_samples: np.ndarray | None = None,
    spread: dict[str, float] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Save light-curve model arrays so restyling does not require VA calls."""
    arrays: dict[str, Any] = {
        "cache_version": np.asarray(CACHE_VERSION, dtype=np.int16),
        "times_days": np.asarray(times, dtype=np.float64),
        "metadata_json": np.asarray(json.dumps(metadata or {}, sort_keys=True)),
        "spread_json": np.asarray(json.dumps(spread or {}, sort_keys=True)),
        "best_bands": np.asarray(list(best_fluxes), dtype=str),
    }
    for band, flux in best_fluxes.items():
        arrays[f"best__{_cache_key(band)}"] = np.asarray(flux, dtype=np.float32)

    if parameter_names is not None:
        arrays["parameter_names"] = np.asarray(parameter_names, dtype=str)
    if posterior_samples is not None:
        arrays["posterior_samples"] = np.asarray(posterior_samples, dtype=np.float32)
    if walker_samples is not None:
        arrays["walker_samples"] = np.asarray(walker_samples, dtype=np.float32)

    if posterior_fluxes is not None:
        arrays["posterior_bands"] = np.asarray(list(posterior_fluxes), dtype=str)
        for band, curves in posterior_fluxes.items():
            arrays[f"posterior__{_cache_key(band)}"] = np.asarray(curves, dtype=np.float32)

    if walker_fluxes is not None:
        arrays["walker_bands"] = np.asarray(list(walker_fluxes), dtype=str)
        for band, curves in walker_fluxes.items():
            arrays[f"walker__{_cache_key(band)}"] = np.asarray(curves, dtype=np.float32)

    np.savez_compressed(path, **arrays)


def _read_band_stack(data: np.lib.npyio.NpzFile, prefix: str) -> dict[str, np.ndarray]:
    bands_key = f"{prefix}_bands"
    if bands_key not in data.files:
        return {}
    out: dict[str, np.ndarray] = {}
    for band in np.asarray(data[bands_key]).astype(str):
        key = f"{prefix}__{_cache_key(band)}"
        if key in data.files:
            out[str(band)] = np.asarray(data[key], dtype=float)
    return out


def read_spread_flux_cache(
    path: Path,
    *,
    ndata: int,
    ncurves: int,
    seed: int,
    walker_limit: int,
    available_walkers: int,
    input_signature: str,
) -> tuple[
    np.ndarray,
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    np.ndarray,
    np.ndarray,
    list[str],
] | None:
    """Read a matching spread-out light-curve cache when available."""
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = int(np.asarray(data["cache_version"]).item())
            metadata = json.loads(str(np.asarray(data["metadata_json"]).item()))
            if version != CACHE_VERSION:
                return None
            if metadata.get("input_signature") != input_signature:
                return None
            for key, expected in {
                "ndata": ndata,
                "ncurves": ncurves,
                "seed": seed,
                "walker_limit": walker_limit,
            }.items():
                if int(metadata.get(key, -999999)) != int(expected):
                    return None
            times = np.asarray(data["times_days"], dtype=float)
            best = _read_band_stack(data, "best")
            posterior = _read_band_stack(data, "posterior")
            walker = _read_band_stack(data, "walker")
            posterior_samples = np.asarray(data["posterior_samples"], dtype=float)
            walker_samples = np.asarray(data["walker_samples"], dtype=float)
            parameter_names = [str(name) for name in np.asarray(data["parameter_names"]).tolist()]
    except Exception:
        return None
    if times.size != ndata or not best or not posterior or not walker:
        return None
    if posterior_samples.shape[0] != ncurves:
        return None
    if walker_limit <= 0 and walker_samples.shape[0] != available_walkers:
        return None
    if walker_limit > 0 and walker_samples.shape[0] != min(walker_limit, available_walkers):
        return None
    return times, best, posterior, walker, posterior_samples, walker_samples, parameter_names


def setup_axis(ax, event: str, *, label_y: float = 0.94) -> None:
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Time Since Trigger [days]")
    ax.set_ylabel("Scaled Flux Density [mJy]")
    ax.grid(alpha=0.25)
    # LightCurvePlot already adds the top seconds axis; do not create a duplicate.
    if event:
        add_collision_aware_grb_label(
            ax,
            f"GRB {event}",
            corner="upper right",
            candidates=[
                (0.985, label_y),
                (0.985, max(label_y - 0.085, 0.70)),
                (0.985, max(label_y - 0.17, 0.62)),
                (0.925, label_y),
            ],
            fontsize=15,
            zorder=30,
        )


def restyle_legend(ax) -> None:
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return
    ax.legend(
        handles,
        labels,
        loc="center left",
        bbox_to_anchor=(1.015, 0.5),
        ncols=1,
        fontsize=8.5,
        frameon=True,
        framealpha=0.94,
        fancybox=False,
        borderpad=0.45,
        handlelength=1.4,
        handletextpad=0.45,
        borderaxespad=0.0,
    )


def add_seconds_axis(ax) -> None:
    secax = ax.secondary_xaxis("top", functions=(lambda d: d * SEC_PER_DAY, lambda s: s / SEC_PER_DAY))
    secax.set_xlabel("Time Since Trigger [seconds]", labelpad=8)
    secax.tick_params(axis="x", labelsize=9)


def add_panel_label(ax, text: str, *, x: float = 0.985, y: float = 0.94, size: float = 15) -> None:
    add_collision_aware_grb_label(
        ax,
        text,
        corner="upper right",
        candidates=[
            (x, y),
            (x, max(y - 0.085, 0.70)),
            (x, max(y - 0.17, 0.62)),
            (max(x - 0.06, 0.80), y),
        ],
        fontsize=size,
        zorder=30,
    )


def attach_axis(lcg: LightCurvePlot, ax) -> LightCurvePlot:
    """Use a LightCurvePlot helper on an externally managed Matplotlib axis."""
    old_fig = lcg.ax.figure
    lcg.ax = ax
    lcg.ax1 = None
    plt.close(old_fig)
    return lcg


def band_label(band: str, spread: dict[str, float]) -> str:
    label = LABELS.get(band) or band
    factor = spread.get(band, 1.0)
    if factor != 1.0:
        if float(factor).is_integer():
            factor_text = f"{int(factor)}"
        else:
            factor_text = f"{factor:g}"
        label = f"{label} x {factor_text}"
    return label


def plot_best_curves(
    ax,
    lcg: LightCurvePlot,
    best_params: dict[str, Any],
    times: np.ndarray,
    spread: dict[str, float],
    ext_model,
    *,
    lw: float = 1.25,
    best_fluxes: dict[str, np.ndarray] | None = None,
) -> None:
    if best_fluxes is None:
        best_fluxes = fast_model_fluxes(lcg, best_params, times, ext_model)
    for band, flux in best_fluxes.items():
        band = str(band)
        if band == "nan":
            continue
        scale = spread.get(band, 1.0)
        color = OPTION_MAP[band]["color"]
        line_width = max(lw, 1.6) if band == "xray" else lw
        zorder = 9 if band == "xray" else 6
        ax.loglog(times, np.asarray(flux, dtype=float) * scale, color=color, lw=line_width, ls="--", zorder=zorder)


def plot_regular_panel(
    ax,
    lcg: LightCurvePlot,
    event: str,
    best_params: dict[str, Any],
    times: np.ndarray,
    ext_model,
    *,
    best_fluxes: dict[str, np.ndarray] | None = None,
) -> None:
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Time Since Trigger [days]")
    ax.set_ylabel("Flux Density [mJy]")
    ax.grid(alpha=0.25)
    add_seconds_axis(ax)

    if best_fluxes is None:
        best_fluxes = fast_model_fluxes(lcg, best_params, times, ext_model)
    for band, flux in best_fluxes.items():
        band = str(band)
        if band == "nan" or band not in OPTION_MAP:
            continue
        ax.loglog(
            times,
            np.asarray(flux, dtype=float),
            color=OPTION_MAP[band]["color"],
            lw=1.45 if band != "xray" else 1.8,
            ls="--",
            zorder=8,
        )

    lcg.plot_observation(best_params, excluded=True)
    add_panel_label(ax, f"GRB {event}", y=0.955)
    ax.set_xlim(times.min(), times.max())


def plot_spread_walker_panel(
    ax,
    lcg: LightCurvePlot,
    best_params: dict[str, Any],
    times: np.ndarray,
    spread: dict[str, float],
    ext_model,
    final_params: list[dict[str, Any]],
    available_walkers: int,
    *,
    walker_fluxes: dict[str, np.ndarray] | None = None,
    best_fluxes: dict[str, np.ndarray] | None = None,
) -> None:
    walker_label = (
        f"All {len(final_params)} final walkers"
        if len(final_params) == available_walkers
        else f"{len(final_params)} of {available_walkers} final walkers"
    )
    stacks = walker_fluxes if walker_fluxes is not None else model_fluxes_for_params(lcg, final_params, times, ext_model)
    for band, curves in stacks.items():
        band = str(band)
        if band == "nan" or band not in OPTION_MAP:
            continue
        scale = spread.get(band, 1.0)
        color = OPTION_MAP[band]["color"]
        alpha = 0.08 if band == "xray" else 0.045
        lw = 0.85 if band == "xray" else 0.55
        zorder = 4 if band == "xray" else 2
        for curve in curves:
            ax.loglog(times, curve * scale, color=color, alpha=alpha, lw=lw, zorder=zorder)

    plot_best_curves(ax, lcg, best_params, times, spread, ext_model, lw=1.25, best_fluxes=best_fluxes)
    lcg.plot_observation(best_params, spreads=spread, offset=True, excluded=True)
    setup_axis(ax, "", label_y=0.965)
    ax.text(
        0.985,
        0.035,
        walker_label,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=10,
        color="0.25",
        zorder=30,
    )
    ax.set_xlim(times.min(), times.max())


def plot_shaded(
    run_dir: Path,
    event: str,
    lcg: LightCurvePlot,
    best_params: dict[str, Any],
    times: np.ndarray,
    spread: dict[str, float],
    ext_model,
    ncurves: int,
    seed: int,
    *,
    posterior_fluxes: dict[str, np.ndarray] | None = None,
    best_fluxes: dict[str, np.ndarray] | None = None,
) -> None:
    fig = lcg.ax.figure
    ax = lcg.ax
    if posterior_fluxes is None:
        posterior = random_posterior_param_dicts(run_dir, ncurves=ncurves, seed=seed)
        stacks = model_fluxes_for_params(lcg, posterior, times, ext_model)
    else:
        stacks = posterior_fluxes
    for band, curves in stacks.items():
        if curves.shape[0] < 2:
            continue
        p16, p84 = np.nanpercentile(curves, [16, 84], axis=0)
        scale = spread.get(band, 1.0)
        alpha = 0.16 if band == "xray" else 0.20
        ax.fill_between(times, p16 * scale, p84 * scale, color=OPTION_MAP[band]["color"], alpha=alpha, lw=0, zorder=2)
    plot_best_curves(ax, lcg, best_params, times, spread, ext_model, best_fluxes=best_fluxes)
    lcg.plot_observation(best_params, spreads=spread, offset=True, excluded=True)
    setup_axis(ax, event)
    ax.text(
        0.985,
        0.885,
        "16th-84th percentile posterior band",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        color="0.25",
        zorder=30,
    )
    restyle_legend(ax)
    ax.set_xlim(times.min(), times.max())
    fig.savefig(run_dir / "light_curve_spread_out_shaded_posterior.pdf", bbox_inches="tight", pad_inches=0.045)
    fig.savefig(run_dir / "light_curve_spread_out_shaded_posterior.png", dpi=220, bbox_inches="tight", pad_inches=0.045)
    plt.close(fig)


def plot_walkers(
    run_dir: Path,
    event: str,
    lcg: LightCurvePlot,
    best_params: dict[str, Any],
    times: np.ndarray,
    spread: dict[str, float],
    ext_model,
    final_params: list[dict[str, Any]],
    available_walkers: int,
    *,
    walker_fluxes: dict[str, np.ndarray] | None = None,
    best_fluxes: dict[str, np.ndarray] | None = None,
) -> None:
    fig = lcg.ax.figure
    ax = lcg.ax
    plot_spread_walker_panel(
        ax,
        lcg,
        best_params,
        times,
        spread,
        ext_model,
        final_params,
        available_walkers,
        walker_fluxes=walker_fluxes,
        best_fluxes=best_fluxes,
    )
    add_panel_label(ax, f"GRB {event}", y=0.965)
    restyle_legend(ax)
    fig.savefig(run_dir / "light_curve_spread_out_100_walkers.pdf", bbox_inches="tight", pad_inches=0.045)
    fig.savefig(run_dir / "light_curve_spread_out_100_walkers.png", dpi=220, bbox_inches="tight", pad_inches=0.045)
    plt.close(fig)


def plot_two_panel(
    run_dir: Path,
    event: str,
    best_params: dict[str, Any],
    ampy: Ampy,
    times: np.ndarray,
    spread: dict[str, float],
    ext_model,
    final_params: list[dict[str, Any]],
    available_walkers: int,
    *,
    walker_fluxes: dict[str, np.ndarray] | None = None,
    best_fluxes: dict[str, np.ndarray] | None = None,
) -> None:
    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(10.0, 12.0), sharex=True)
    regular_lcg = attach_axis(
        LightCurvePlot(
            ampy.mcmc.models.afg_model,
            best_params,
            ampy.obs,
            meta=ampy.mcmc.models.afg_kw,
            title=None,
            dual=False,
        ),
        ax_top,
    )
    spread_lcg = attach_axis(
        LightCurvePlot(
            ampy.mcmc.models.afg_model,
            best_params,
            ampy.obs,
            meta=ampy.mcmc.models.afg_kw,
            title=None,
            dual=False,
        ),
        ax_bottom,
    )

    plot_regular_panel(ax_top, regular_lcg, event, best_params, times, ext_model, best_fluxes=best_fluxes)
    plot_spread_walker_panel(
        ax_bottom,
        spread_lcg,
        best_params,
        times,
        spread,
        ext_model,
        final_params,
        available_walkers,
        walker_fluxes=walker_fluxes,
        best_fluxes=best_fluxes,
    )

    top_legend = ax_top.get_legend()
    if top_legend is not None:
        top_legend.remove()
    ax_top.set_xlabel("")
    ax_top.text(
        0.985,
        0.875,
        "unscaled flux density",
        transform=ax_top.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        color="0.25",
        zorder=30,
    )
    ax_bottom.text(
        0.985,
        0.875,
        "band-scaled flux density",
        transform=ax_bottom.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        color="0.25",
        zorder=30,
    )
    restyle_legend(ax_bottom)
    fig.subplots_adjust(hspace=0.05)
    fig.savefig(run_dir / "light_curve_two_panel.pdf", bbox_inches="tight", pad_inches=0.045)
    fig.savefig(run_dir / "light_curve_two_panel.png", dpi=220, bbox_inches="tight", pad_inches=0.045)
    plt.close(fig)


def _stack_count(stacks: dict[str, np.ndarray]) -> int:
    counts = [int(np.asarray(curves).shape[0]) for curves in stacks.values() if np.asarray(curves).ndim >= 2]
    return min(counts) if counts else 0


def write_audit(
    run_dir: Path,
    event: str,
    spread: dict[str, float],
    source: str,
    nmap: float | None,
    *,
    requested_posterior_curves: int,
    requested_walker_limit: int,
    available_walkers: int,
    posterior_fluxes: dict[str, np.ndarray],
    walker_fluxes: dict[str, np.ndarray],
    posterior_samples: np.ndarray,
    walker_samples: np.ndarray,
    parameter_names: list[str],
) -> None:
    rows = ["band,spread_factor"]
    for band in sorted(spread):
        rows.append(f"{band},{spread[band]:g}")
    (run_dir / "light_curve_spread_out_factors.csv").write_text("\n".join(rows) + "\n")
    meta = {
        "event": event,
        "postfit_source": source,
        "nmap": nmap,
        "spacing_source": str(DEFAULT_SPACING),
        "requested_posterior_curves": int(requested_posterior_curves),
        "requested_walker_limit": int(requested_walker_limit),
        "available_walkers": int(available_walkers),
        "posterior_curve_count": int(_stack_count(posterior_fluxes)),
        "walker_curve_count": int(_stack_count(walker_fluxes)),
        "posterior_solution_count": int(np.asarray(posterior_samples).shape[0]),
        "walker_solution_count": int(np.asarray(walker_samples).shape[0]),
        "parameter_count": int(len(parameter_names)),
        "parameter_names": list(parameter_names),
        "uses_all_final_walkers": bool(_stack_count(walker_fluxes) == int(available_walkers)),
        "posterior_sampling": "without_replacement",
        "outputs": [
            "light_curve_spread_out_shaded_posterior.pdf",
            "light_curve_spread_out_shaded_posterior.png",
            "light_curve_spread_out_100_walkers.pdf",
            "light_curve_spread_out_100_walkers.png",
            "light_curve_two_panel.pdf",
            "light_curve_two_panel.png",
        ],
    }
    (run_dir / "light_curve_spread_out_spread_metadata.json").write_text(json.dumps(meta, indent=2) + "\n")


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    event = infer_event(run_dir, args.event)
    best_params, source, nmap = load_postfit_params(run_dir)
    spread = load_spacing(args.spacing, event)

    ampy = Ampy(run_dir / "obs.csv", run_dir / "model.toml")
    ext_model = ampy.extinction_model(Rv=3.1) if ampy.extinction_model is not None else None
    ranges = ampy.obs.epoch(ampy.obs.flux_loc)
    times = np.geomspace(float(ranges[0]) / 2.0, float(ranges[1]) * 2.0, num=args.ndata)
    available_walkers = final_walker_count(run_dir)
    input_signature = cache_input_signature(run_dir)
    cache_path = run_dir / "light_curve_spread_out_model_data.npz"
    cached = read_spread_flux_cache(
        cache_path,
        ndata=args.ndata,
        ncurves=args.ncurves,
        seed=args.seed,
        walker_limit=args.walker_limit,
        available_walkers=available_walkers,
        input_signature=input_signature,
    )
    if cached is None:
        walker_samples, parameter_names = final_walker_samples(run_dir, limit=args.walker_limit)
        final_params = samples_to_param_dicts(run_dir, walker_samples)
        cache_lcg = LightCurvePlot(
            ampy.mcmc.models.afg_model,
            best_params,
            ampy.obs,
            meta=ampy.mcmc.models.afg_kw,
            title=None,
            dual=False,
        )
        best_fluxes = fast_model_fluxes(cache_lcg, best_params, times, ext_model)
        posterior_samples, posterior_parameter_names = random_posterior_samples(
            run_dir,
            ncurves=args.ncurves,
            seed=args.seed,
        )
        if posterior_parameter_names != parameter_names:
            raise ValueError("Posterior and walker parameter names do not match.")
        posterior_params = samples_to_param_dicts(run_dir, posterior_samples)
        posterior_fluxes = model_fluxes_for_params(cache_lcg, posterior_params, times, ext_model)
        walker_fluxes = model_fluxes_for_params(cache_lcg, final_params, times, ext_model)
        plt.close(cache_lcg.ax.figure)

        write_flux_stack_cache(
            cache_path,
            times=times,
            best_fluxes=best_fluxes,
            posterior_fluxes=posterior_fluxes,
            walker_fluxes=walker_fluxes,
            parameter_names=parameter_names,
            posterior_samples=posterior_samples,
            walker_samples=walker_samples,
            spread=spread,
            metadata={
                "event": event,
                "source": source,
                "nmap": nmap,
                "ncurves": args.ncurves,
                "seed": args.seed,
                "ndata": args.ndata,
                "walker_limit": args.walker_limit,
                "available_walkers": available_walkers,
                "input_signature": input_signature,
                "posterior_solution_count": int(posterior_samples.shape[0]),
                "walker_solution_count": int(walker_samples.shape[0]),
                "parameter_names": parameter_names,
                "saved_units": "mJy before spread factors",
                "time_units": "days",
            },
        )
        print(f"light_curve_cache_written path={cache_path}")
    else:
        times, best_fluxes, posterior_fluxes, walker_fluxes, posterior_samples, walker_samples, parameter_names = cached
        walker_count = next(iter(walker_fluxes.values())).shape[0]
        final_params = [{} for _ in range(int(walker_count))]
        print(f"light_curve_cache_reused path={cache_path}")

    for plotter in (plot_shaded, plot_walkers):
        lcg = LightCurvePlot(
            ampy.mcmc.models.afg_model,
            best_params,
            ampy.obs,
            meta=ampy.mcmc.models.afg_kw,
            title=None,
            dual=False,
        )
        if plotter is plot_shaded:
            plotter(
                run_dir,
                event,
                lcg,
                best_params,
                times,
                spread,
                ext_model,
                args.ncurves,
                args.seed,
                posterior_fluxes=posterior_fluxes,
                best_fluxes=best_fluxes,
            )
        else:
            plotter(
                run_dir,
                event,
                lcg,
                best_params,
                times,
                spread,
                ext_model,
                final_params,
                available_walkers,
                walker_fluxes=walker_fluxes,
                best_fluxes=best_fluxes,
            )

    plot_two_panel(
        run_dir,
        event,
        best_params,
        ampy,
        times,
        spread,
        ext_model,
        final_params,
        available_walkers,
        walker_fluxes=walker_fluxes,
        best_fluxes=best_fluxes,
    )

    write_audit(
        run_dir,
        event,
        spread,
        source,
        nmap,
        requested_posterior_curves=args.ncurves,
        requested_walker_limit=args.walker_limit,
        available_walkers=available_walkers,
        posterior_fluxes=posterior_fluxes,
        walker_fluxes=walker_fluxes,
        posterior_samples=posterior_samples,
        walker_samples=walker_samples,
        parameter_names=parameter_names,
    )
    print(f"spread_light_curves_ok event={event} run_dir={run_dir}")
    print(f"source={source} nmap={nmap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
