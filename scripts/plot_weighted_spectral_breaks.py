#!/usr/bin/env python3
"""Retired helper for Dylan-style weighted spectral-break plots.

The standard pipeline should use ``frequencies.pdf`` and should not regenerate
``spectral_plot.pdf``, ``spectral_plot.png``, or
``spectral_breaks_eats_weighted.csv``. This script now requires an explicit
opt-in flag before writing those retired products.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.ampy import model_factory
from jetfit.core.utils import apply_plot_run_label, apply_plot_title
from scripts.plot.base import OPTION_MAP

DAY_S = 86400.0


def read_model_name(run_dir: Path) -> str:
    with (run_dir / "model.toml").open("rb") as handle:
        payload = tomllib.load(handle)
    name = payload.get("name")
    if not name:
        raise ValueError(f"Missing top-level model name in {run_dir / 'model.toml'}")
    return str(name)


def read_postfit_params(run_dir: Path) -> tuple[dict[str, Any], str]:
    minimized = run_dir / "minimized" / "minimized.json"
    if minimized.exists():
        payload = json.loads(minimized.read_text())
        return payload.get("params", payload), "minimized/minimized.json"

    best = run_dir / "best_fit.json"
    if best.exists():
        return json.loads(best.read_text()), "best_fit.json"

    raise FileNotFoundError(f"No minimized/minimized.json or best_fit.json in {run_dir}")


def read_obs_points(obs_csv: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with obs_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("ValueType") != "Spectral Flux":
                continue
            try:
                time = float(row["Time"])
                freq = float(row["Wave"])
            except Exception:
                continue
            if not (math.isfinite(time) and math.isfinite(freq) and time > 0.0 and freq > 0.0):
                continue

            time_units = (row.get("TimeUnits") or "d").lower()
            if time_units in {"s", "sec", "second", "seconds"}:
                time_days = time / DAY_S
            else:
                time_days = time

            rows.append(
                {
                    "time_days": time_days,
                    "frequency_hz": freq,
                    "filter": row.get("Filter") or "data",
                }
            )
    if not rows:
        raise ValueError(f"No spectral-flux rows found in {obs_csv}")
    return rows


def label_for_filter(name: str) -> str:
    return {
        "Ic": "I",
        "Rc": "R",
        "C": "3 GHz",
        "Ka": "229 GHz",
        "Kb": "272 GHz",
        "Kc": "290 GHz",
        "Kd": "341 GHz",
        "uvot-u": "UVOT-u",
        "uvot-b": "UVOT-b",
        "uvot-v": "UVOT-v",
        "uvw1": "UVOT-uvw1",
        "uvm2": "UVOT-uvm2",
        "uvw2": "UVOT-uvw2",
        "xray": "XRT",
        "S": "345 GHz",
    }.get(name, name)


def plot_data(ax, rows: list[dict[str, Any]]) -> None:
    filters = sorted({str(r["filter"]) for r in rows})
    for filt in filters:
        subset = [r for r in rows if r["filter"] == filt]
        times = np.asarray([r["time_days"] for r in subset], dtype=float)
        freqs = np.asarray([r["frequency_hz"] for r in subset], dtype=float)
        style = dict(OPTION_MAP.get(filt, {"color": "0.35", "marker": "."}))
        style["marker"] = style.get("marker", ".")
        ax.scatter(times, freqs, s=18, alpha=0.82, linewidths=0.0, label=label_for_filter(filt), **style)


def write_break_csv(path: Path, times: np.ndarray, nu_a: np.ndarray, nu_m: np.ndarray, nu_c: np.ndarray) -> None:
    table = np.column_stack([times, nu_a, nu_m, nu_c])
    np.savetxt(
        path,
        table,
        delimiter=",",
        header="time_days,nu_a_eats_weighted_hz,nu_m_eats_weighted_hz,nu_c_eats_weighted_hz",
        comments="",
    )


def _weighted_observed_freq(details: Any, field: str, t_sec: np.ndarray, z: float) -> np.ndarray:
    """Approximate Dylan-style EATS luminosity-weighted observer-frame breaks."""
    t_obs = np.asarray(details.fwd.t_obs, dtype=float)
    doppler = np.asarray(details.fwd.Doppler, dtype=float)
    values = np.asarray(getattr(details.fwd, field), dtype=float)
    i_nu_max = np.asarray(details.fwd.I_nu_max, dtype=float)

    values_obs = values * doppler / (1.0 + float(z))
    weights = np.clip(i_nu_max * np.power(np.clip(doppler, 0.0, None), 3.0), 0.0, None)

    t_grid = t_obs.reshape(-1, t_obs.shape[-1])
    v_grid = values_obs.reshape(-1, values_obs.shape[-1])
    w_grid = weights.reshape(-1, weights.shape[-1])

    out = np.full_like(t_sec, np.nan, dtype=float)
    for i, tgt in enumerate(t_sec):
        num = 0.0
        den = 0.0
        for tz, vz, wz in zip(t_grid, v_grid, w_grid):
            if tz.size < 2:
                continue
            if not (np.all(np.isfinite(tz)) and np.all(np.isfinite(vz)) and np.all(np.isfinite(wz))):
                continue
            if tgt < tz[0] or tgt > tz[-1]:
                continue
            v = float(np.interp(tgt, tz, vz))
            w = float(np.interp(tgt, tz, wz))
            if np.isfinite(v) and np.isfinite(w) and w > 0.0:
                num += w * v
                den += w
        if den > 0.0:
            out[i] = num / den
    return out


def _vegas_weighted_breaks(model: Any, times_days: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute EATS-weighted nu_a/nu_m/nu_c directly from Vegas detail grids."""
    if not hasattr(model, "vegas_model"):
        raise AttributeError("model has no vegas_model")
    if not hasattr(model, "z"):
        raise AttributeError("model has no z")

    t_sec = np.asarray(times_days, dtype=float) * DAY_S
    details = model.vegas_model.details(float(np.nanmin(t_sec)), float(np.nanmax(t_sec)))

    nu_a = _weighted_observed_freq(details, "nu_a", t_sec, model.z)
    nu_m = _weighted_observed_freq(details, "nu_m", t_sec, model.z)
    nu_c = _weighted_observed_freq(details, "nu_c", t_sec, model.z)

    if not np.all(np.isfinite(nu_a) | np.isnan(nu_a)):
        raise ValueError("non-finite nu_a in weighted break calculation")
    if not np.all(np.isfinite(nu_m) | np.isnan(nu_m)):
        raise ValueError("non-finite nu_m in weighted break calculation")
    if not np.all(np.isfinite(nu_c) | np.isnan(nu_c)):
        raise ValueError("non-finite nu_c in weighted break calculation")

    return nu_a, nu_m, nu_c


def make_plot(
    run_dir: Path,
    event: str | None = None,
    ngrid: int = 220,
    allow_local_fallback: bool = False,
) -> tuple[Path, Path, Path]:
    obs_rows = read_obs_points(run_dir / "obs.csv")
    model_name = read_model_name(run_dir)
    params, source = read_postfit_params(run_dir)
    if "model" not in params:
        raise ValueError(f"{source} does not contain a model section")

    model_kwargs = dict(params["model"])
    if "DylanSpectrum" in model_name:
        model_kwargs["break_frequency_mode"] = "eats_weighted"
    model = model_factory(model_name)(**model_kwargs)

    obs_times = np.asarray([r["time_days"] for r in obs_rows], dtype=float)
    t_min = float(np.nanmin(obs_times))
    t_max = float(np.nanmax(obs_times))
    times = np.geomspace(max(t_min / 2.0, 1.0e-8), t_max * 2.0, ngrid)

    try:
        nu_a, nu_m, nu_c = _vegas_weighted_breaks(model, times)
    except Exception as exc:
        if not allow_local_fallback:
            raise RuntimeError(
                "EATS-weighted spectral-break calculation failed. "
                "Not falling back to legacy/local nu_* curves because "
                "spectral_plot.pdf and spectral_breaks_eats_weighted.csv "
                "are reserved for Dylan-style EATS-weighted products. "
                "Pass --allow-local-fallback only for an explicitly labeled "
                "legacy diagnostic."
            ) from exc
        nu_a = np.asarray(model.nu_a(times), dtype=float)
        nu_m = np.asarray(model.nu_m(times), dtype=float)
        nu_c = np.asarray(model.nu_c(times), dtype=float)

    fig, ax = plt.subplots(figsize=(8.4, 5.8))
    plot_data(ax, obs_rows)
    ax.loglog(times, nu_a, color="tab:green", lw=2.4, label=r"$\nu_a$ weighted")
    ax.loglog(times, nu_m, color="tab:blue", lw=2.4, label=r"$\nu_m$ weighted")
    ax.loglog(times, nu_c, color="tab:orange", lw=2.4, label=r"$\nu_c$ weighted")

    ax.set_xlabel("Time Since Trigger [days]")
    ax.set_ylabel("Frequency [Hz]")
    ax.grid(alpha=0.22, axis="x", which="both")

    event_label = event or run_dir.name.split("_", 1)[0]
    apply_plot_title(fig, f"GRB {event_label} Spectral Breaks", y=0.985, top=0.82)
    apply_plot_run_label(fig, label=f"GRB {event_label} | {run_dir.parent.name}/{run_dir.name} | {source}")

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.885),
        ncol=5,
        fontsize=7.5,
        frameon=True,
        fancybox=False,
        edgecolor="black",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.80])

    pdf = run_dir / "spectral_plot.pdf"
    png = run_dir / "spectral_plot.png"
    csv_path = run_dir / "spectral_breaks_eats_weighted.csv"

    if pdf.exists():
        backup = run_dir / "spectral_plot_legacy_before_eats_weighted.pdf"
        if not backup.exists():
            shutil.copy2(pdf, backup)

    fig.savefig(pdf)
    fig.savefig(png, dpi=220)
    plt.close(fig)
    write_break_csv(csv_path, times, nu_a, nu_m, nu_c)
    return pdf, png, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--event", default=None)
    parser.add_argument("--ngrid", type=int, default=220)
    parser.add_argument(
        "--write-retired-products",
        action="store_true",
        help=(
            "Actually write retired spectral_plot.pdf/.png and "
            "spectral_breaks_eats_weighted.csv products. Standard pipelines "
            "should not pass this flag; use frequencies.pdf instead."
        ),
    )
    parser.add_argument(
        "--allow-local-fallback",
        action="store_true",
        help=(
            "If direct EATS-weighted details fail, fall back to model.nu_* "
            "legacy/local curves. Do not use for production spectral_plot.pdf."
        ),
    )
    args = parser.parse_args()

    if not args.write_retired_products:
        print(
            "SKIP: spectral_plot.pdf, spectral_plot.png, and "
            "spectral_breaks_eats_weighted.csv are retired standard products. "
            "Use frequencies.pdf instead. Pass --write-retired-products only "
            "for an explicit one-off diagnostic."
        )
        return 0

    pdf, png, csv_path = make_plot(
        args.run_dir.expanduser().resolve(),
        args.event,
        args.ngrid,
        allow_local_fallback=args.allow_local_fallback,
    )
    print(f"Wrote: {pdf}")
    print(f"Wrote: {png}")
    print(f"Wrote: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
