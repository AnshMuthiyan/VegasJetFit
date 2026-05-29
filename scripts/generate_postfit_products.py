#!/usr/bin/env python3
"""Generate standard post-fit products from a finished VegasJetFit run.

The products in this script are intentionally post-minimization products when
``minimized/minimized.json`` is present.  MCMC diagnostics such as corner plots
remain posterior diagnostics and are not regenerated from the minimizer.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import os
import subprocess
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

from jetfit.ampy import Ampy
from jetfit.core.utils import apply_plot_run_label, apply_plot_title
from scripts.plot import visualize
from scripts.thesis_reproduction_data import THESIS, normalize_event_name


PC_CM = 3.0856775814913673e18
MSUN_G = 1.98847e33
MP_G = 1.67262192369e-24
C_CGS = 2.99792458e10
REF_RADIUS_CM = 1.0e17

MODEL_CLASS_MAP: dict[str, str] = {
    "powerlawVegasModel": "jetfit.models.powerlawVegas:powerlawVegasModel",
    "powerlawVegasDylanSpectrumModel": "jetfit.models.powerlawVegasDylanSpectrum:powerlawVegasDylanSpectrumModel",
    "VegasAfterglowModel": "jetfit.models.vegasafterglow:VegasAfterglowModel",
    "PowerlawJetVegasAfterglowModel": "jetfit.models.powerlawJetVegasAfterglow:PowerlawJetVegasAfterglowModel",
    "PowerlawJetVegasDylanSpectrumModel": "jetfit.models.powerlawJetVegasDylanSpectrum:PowerlawJetVegasDylanSpectrumModel",
    "BubbleVegasDylanSpectrumModel": "jetfit.models.bubbleVegasDylanSpectrum:BubbleVegasDylanSpectrumModel",
    "EmpiricalBubbleVegasModel": "jetfit.models.empiricalBubbleVegas:EmpiricalBubbleVegasModel",
    "EmpiricalBubbleVegasDylanSpectrumModel": (
        "jetfit.models.empiricalBubbleVegasDylanSpectrum:EmpiricalBubbleVegasDylanSpectrumModel"
    ),
}

THESIS_LOG10_PARAMS = {"E52", "lf0", "n017", "nt", "rt", "eps_e", "eps_b"}
TIME_COLUMN_CANDIDATES = ("time_days", "time", "t_days", "t", "days")
AMPY_MISSING_NOTE = "ampy_comparison_missing_reference.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path, help="Finished run directory.")
    parser.add_argument("--event", default=None, help="GRB name. Defaults to the run folder prefix.")
    parser.add_argument(
        "--skip-density-replot",
        action="store_true",
        help="Skip regenerating n/k/n0 profile plots from the MCMC chain.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def infer_event(results: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    parent = results.name
    if parent and parent[0].isdigit():
        return parent.split("_", 1)[0]
    if results.parent.name and results.parent.name[0].isdigit():
        return results.parent.name.split("_", 1)[0]
    raise ValueError(f"Could not infer event name from {results}")


def load_model_toml(results: Path) -> dict[str, Any]:
    path = results / "model.toml"
    if not path.exists():
        raise FileNotFoundError(f"Missing model.toml in {results}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_postfit_params(results: Path) -> tuple[dict[str, Any], str, float | None]:
    minimized = results / "minimized" / "minimized.json"
    if minimized.exists():
        payload = read_json(minimized)
        return payload.get("params", payload), "minimized/minimized.json", _float_or_none(payload.get("nmap"))

    best = results / "best_fit.json"
    if best.exists():
        payload = read_json(best)
        return payload, "best_fit.json", _float_or_none(payload.get("nmap"))

    raise FileNotFoundError(f"No minimized/minimized.json or best_fit.json in {results}")


def _float_or_none(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def load_model_class(model_name: str):
    if model_name not in MODEL_CLASS_MAP:
        raise ValueError(f"No postfit model-class mapping for {model_name!r}")
    module_name, class_name = MODEL_CLASS_MAP[model_name].split(":")
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def display_run_label(results: Path, event: str) -> str:
    """Return the human-readable run label for local and share-tree layouts."""
    if results.name == "fit" and results.parent.name == event:
        return results.parent.parent.name
    return results.parent.name if results.name == event else results.name


def read_obs_time_range(obs_csv: Path) -> tuple[float, float]:
    if not obs_csv.exists():
        return 1.0, 100.0
    with obs_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return 1.0, 100.0
        fields = list(reader.fieldnames)
        lower = {name.lower(): name for name in fields}
        time_col = next((lower[name] for name in TIME_COLUMN_CANDIDATES if name in lower), fields[0])
        units_col = lower.get("timeunits")
        include_col = lower.get("include")
        times: list[float] = []
        for row in reader:
            if include_col is not None:
                try:
                    if float(row.get(include_col, "1")) <= 0:
                        continue
                except Exception:
                    pass
            try:
                raw = float(row.get(time_col, "nan"))
            except Exception:
                continue
            unit = (row.get(units_col) if units_col else "") or ""
            unit = unit.strip().lower()
            if unit in {"s", "sec", "secs", "second", "seconds"}:
                value = raw / 86400.0
            elif unit in {"ks", "kilosecond", "kiloseconds"}:
                value = raw * 1000.0 / 86400.0
            elif unit in {"hr", "hrs", "hour", "hours", "h"}:
                value = raw / 24.0
            else:
                value = raw
            if math.isfinite(value) and value > 0:
                times.append(value)
    if not times:
        return 1.0, 100.0
    return min(times), max(times)


def cm_to_pc(value):
    return np.asarray(value) / PC_CM


def pc_to_cm(value):
    return np.asarray(value) * PC_CM


def g_to_msun(value):
    return np.asarray(value) / MSUN_G


def msun_to_g(value):
    return np.asarray(value) * MSUN_G


def density_number_cm3(r_cm: np.ndarray, model_params: dict[str, Any]) -> np.ndarray:
    """Return number density using JetFit's fitted CSM convention."""
    r = np.asarray(r_cm, dtype=float)

    if "n017" in model_params and "k" in model_params:
        n017 = float(model_params["n017"])
        k = float(model_params["k"])
        return n017 * (r / REF_RADIUS_CM) ** (-k)

    if {"n0t", "rt", "k1", "k2", "sn"}.issubset(model_params):
        n0t = float(model_params["n0t"])
        rt = float(model_params["rt"])
        k1 = float(model_params["k1"])
        k2 = float(model_params["k2"])
        sn = float(model_params["sn"])
        x = np.maximum(r / rt, 1.0e-300)
        return n0t * (2.0 ** (1.0 / sn)) * (x ** (k1 * sn) + x ** (k2 * sn)) ** (-1.0 / sn)

    if {"nt", "rt", "kpre", "kpost", "sn"}.issubset(model_params):
        translated = {
            "n0t": model_params["nt"],
            "rt": model_params["rt"],
            "k1": model_params["kpre"],
            "k2": model_params["kpost"],
            "sn": model_params["sn"],
        }
        return density_number_cm3(r, translated)

    raise ValueError("Cannot infer CSM density profile from model parameters.")


def swept_mass_profile_g(r_cm: np.ndarray, model_params: dict[str, Any]) -> np.ndarray:
    """Integrate isotropic-equivalent swept-up mass in the fit density convention."""
    hmf = float(model_params.get("hmf", 0.7))
    rho_factor = hmf * MP_G

    if "n017" in model_params and "k" in model_params:
        n017 = float(model_params["n017"])
        k = float(model_params["k"])
        coefficient = 4.0 * math.pi * rho_factor * n017 * REF_RADIUS_CM**k
        if abs(3.0 - k) > 1.0e-8 and k < 3.0:
            return coefficient * np.asarray(r_cm, dtype=float) ** (3.0 - k) / (3.0 - k)

    r = np.asarray(r_cm, dtype=float)
    n = density_number_cm3(r, model_params)
    integrand = 4.0 * math.pi * rho_factor * n * r * r
    mass = np.zeros_like(r)
    if r.size > 1:
        dr = np.diff(r)
        mass[1:] = np.cumsum(0.5 * (integrand[1:] + integrand[:-1]) * dr)
    return mass


def crossing_radius_cm(r_cm: np.ndarray, mass_g: np.ndarray, target_g: float) -> float:
    """Return the log-interpolated radius where swept-up mass reaches target."""
    if not math.isfinite(target_g) or target_g <= 0.0:
        return float("nan")
    r = np.asarray(r_cm, dtype=float)
    m = np.asarray(mass_g, dtype=float)
    mask = np.isfinite(r) & np.isfinite(m) & (r > 0.0) & (m > 0.0)
    r = r[mask]
    m = m[mask]
    if r.size < 2:
        return float("nan")
    order = np.argsort(r)
    r = r[order]
    m = m[order]
    hits = np.where(m >= target_g)[0]
    if hits.size == 0:
        return float("nan")
    idx = int(hits[0])
    if idx == 0:
        return float(r[0])
    r0, r1 = float(r[idx - 1]), float(r[idx])
    m0, m1 = float(m[idx - 1]), float(m[idx])
    if m0 <= 0.0 or m1 <= 0.0 or m0 == m1:
        return r1
    frac = (math.log(target_g) - math.log(m0)) / (math.log(m1) - math.log(m0))
    frac = float(np.clip(frac, 0.0, 1.0))
    return float(math.exp(math.log(r0) + frac * (math.log(r1) - math.log(r0))))


def crossing_radius_cm_against_curve(
    r_cm: np.ndarray,
    mass_g: np.ndarray,
    target_curve_g: np.ndarray,
) -> float:
    """Return first log-interpolated radius where swept-up mass exceeds a target curve."""
    r = np.asarray(r_cm, dtype=float)
    m = np.asarray(mass_g, dtype=float)
    q = np.asarray(target_curve_g, dtype=float)
    if not (r.size == m.size == q.size) or r.size < 2:
        return float("nan")

    mask = np.isfinite(r) & np.isfinite(m) & np.isfinite(q) & (r > 0.0) & (m > 0.0) & (q > 0.0)
    r = r[mask]
    m = m[mask]
    q = q[mask]
    if r.size < 2:
        return float("nan")

    order = np.argsort(r)
    r = r[order]
    m = m[order]
    q = q[order]
    delta = m - q
    hits = np.where(delta >= 0.0)[0]
    if hits.size == 0:
        return float("nan")
    idx = int(hits[0])
    if idx == 0:
        return float(r[0])

    r0, r1 = float(r[idx - 1]), float(r[idx])
    d0, d1 = float(delta[idx - 1]), float(delta[idx])
    if d1 == d0 or not (np.isfinite(d0) and np.isfinite(d1)):
        return r1
    frac = -d0 / (d1 - d0)
    frac = float(np.clip(frac, 0.0, 1.0))
    return float(math.exp(math.log(r0) + frac * (math.log(r1) - math.log(r0))))


def expand_radius_grid_for_mass_targets(
    r_cm: np.ndarray,
    model_params: dict[str, Any],
    targets_g: list[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Expand the profile grid until requested mass crossings are visible."""
    r = np.asarray(r_cm, dtype=float)
    positive_targets = [target for target in targets_g if math.isfinite(target) and target > 0.0]
    if not positive_targets:
        return r, swept_mass_profile_g(r, model_params)

    target_min = min(positive_targets)
    target_max = max(positive_targets)

    for _ in range(14):
        mass = swept_mass_profile_g(r, model_params)
        finite_mask = np.isfinite(mass) & np.isfinite(r)
        finite_mass = mass[finite_mask]
        finite_r = r[finite_mask]
        if not finite_mass.size or not finite_r.size:
            return r, mass

        lo_ok = float(np.nanmin(finite_mass)) <= target_min
        hi_ok = float(np.nanmax(finite_mass)) >= target_max
        if lo_ok and hi_ok:
            return r, mass

        r_lo = float(np.nanmin(finite_r))
        r_hi = float(np.nanmax(finite_r))
        if not (math.isfinite(r_lo) and math.isfinite(r_hi) and r_lo > 0.0 and r_hi > r_lo):
            return r, mass

        # Expand inward when the smallest sampled mass is still above the smallest target.
        if not lo_ok:
            r_lo = max(r_lo / 10.0, 1.0e9)
        # Expand outward when the largest sampled mass is still below the largest target.
        if not hi_ok:
            r_hi = min(r_hi * 10.0, 1.0e26)

        if r_hi <= r_lo:
            return r, mass
        r = np.geomspace(r_lo, r_hi, max(r.size, 900))
    return r, swept_mass_profile_g(r, model_params)


def radius_grid_for_model(params: dict[str, Any], model_name: str, obs_csv: Path) -> np.ndarray:
    model_params = dict(params["model"])
    t_min, t_max = read_obs_time_range(obs_csv)
    t_lo = max(t_min / 30.0, 1.0e-8)
    t_hi = max(t_max * 30.0, t_lo * 100.0)

    try:
        model_cls = load_model_class(model_name)
        model = model_cls(**model_params)
        times = np.geomspace(t_lo, t_hi, 350)
        radii = np.asarray(model.radii(times), dtype=float)
        radii = radii[np.isfinite(radii) & (radii > 0)]
        if radii.size >= 2:
            lo = max(float(radii.min()) / 3.0, 1.0e12)
            hi = max(float(radii.max()) * 3.0, lo * 100.0)
            return np.geomspace(lo, hi, 900)
    except Exception as exc:
        print(f"WARNING: radius-grid model evaluation failed: {type(exc).__name__}: {exc}")

    ref = float(model_params.get("rt", REF_RADIUS_CM))
    return np.geomspace(ref / 1.0e3, ref * 1.0e3, 900)


def observed_radius_window_cm(
    params: dict[str, Any],
    model_name: str,
    obs_csv: Path,
) -> tuple[float, float, float, float]:
    """Return the included data time range and its best-fit radial equivalent."""
    t_min, t_max = read_obs_time_range(obs_csv)
    try:
        model_cls = load_model_class(model_name)
        model = model_cls(**dict(params["model"]))
        radii = np.asarray(model.radii(np.asarray([t_min, t_max], dtype=float)), dtype=float)
        radii = radii[np.isfinite(radii) & (radii > 0.0)]
        if radii.size >= 2:
            return t_min, t_max, float(np.min(radii[:2])), float(np.max(radii[:2]))
    except Exception as exc:
        print(f"WARNING: data-radius window evaluation failed: {type(exc).__name__}: {exc}")
    return t_min, t_max, float("nan"), float("nan")


def plot_mass_profile(results: Path, event: str, params: dict[str, Any], model_name: str, source: str, nmap: float | None) -> None:
    model_params = params["model"]
    obs_csv = results / "obs.csv"
    r_cm = radius_grid_for_model(params, model_name, obs_csv)
    mass_g = swept_mass_profile_g(r_cm, model_params)
    obs_tmin_days, obs_tmax_days, obs_rmin_cm, obs_rmax_cm = observed_radius_window_cm(params, model_name, obs_csv)

    e52 = float(model_params["E52"])
    gamma0 = float(model_params.get("lf0", 300.0))
    ejecta_mass_g = e52 * 1.0e52 / (gamma0 * C_CGS * C_CGS)

    # Dynamic relativistic thresholds from model Gamma(t), projected to radius.
    model_cls = load_model_class(model_name)
    model = model_cls(**dict(model_params))
    t_eval_days = np.geomspace(max(obs_tmin_days / 30.0, 1.0e-8), max(obs_tmax_days * 30.0, 1.0), 400)
    details = model.vegas_model.details(float(t_eval_days.min() * 86400.0), float(t_eval_days.max() * 86400.0))
    r_dyn = np.asarray(details.fwd.r[0, 0, :], dtype=float)
    gamma_dyn = np.asarray(details.fwd.Gamma[0, 0, :], dtype=float)
    valid = np.isfinite(r_dyn) & np.isfinite(gamma_dyn) & (r_dyn > 0.0) & (gamma_dyn > 0.0)
    r_dyn = r_dyn[valid]
    gamma_dyn = gamma_dyn[valid]
    if r_dyn.size >= 2:
        order_dyn = np.argsort(r_dyn)
        r_dyn = r_dyn[order_dyn]
        gamma_dyn = gamma_dyn[order_dyn]
        gamma_on_grid = np.interp(r_cm, r_dyn, gamma_dyn, left=gamma_dyn[0], right=gamma_dyn[-1])
    else:
        gamma_on_grid = np.full_like(r_cm, gamma0)
    gamma_on_grid = np.clip(gamma_on_grid, 1.0e-12, np.inf)
    decel_mass_curve_g = ejecta_mass_g / gamma_on_grid
    decel_mass_10x_curve_g = 10.0 * ejecta_mass_g / gamma_on_grid
    decel_mass_g = ejecta_mass_g / gamma0

    r_cm, mass_g = expand_radius_grid_for_mass_targets(
        r_cm, model_params, [float(np.nanmin(decel_mass_curve_g)), float(np.nanmin(decel_mass_10x_curve_g)), ejecta_mass_g]
    )
    if r_cm.size != decel_mass_curve_g.size:
        gamma_on_grid = np.interp(
            r_cm,
            r_dyn if r_dyn.size >= 2 else np.asarray([r_cm[0], r_cm[-1]]),
            gamma_dyn if r_dyn.size >= 2 else np.asarray([gamma0, gamma0]),
            left=(gamma_dyn[0] if r_dyn.size >= 2 else gamma0),
            right=(gamma_dyn[-1] if r_dyn.size >= 2 else gamma0),
        )
        gamma_on_grid = np.clip(gamma_on_grid, 1.0e-12, np.inf)
        decel_mass_curve_g = ejecta_mass_g / gamma_on_grid
        decel_mass_10x_curve_g = 10.0 * ejecta_mass_g / gamma_on_grid

    r_decel_cm = crossing_radius_cm_against_curve(r_cm, mass_g, decel_mass_curve_g)
    r_decel_10x_cm = crossing_radius_cm_against_curve(r_cm, mass_g, decel_mass_10x_curve_g)
    r_ejecta_cm = crossing_radius_cm(r_cm, mass_g, ejecta_mass_g)

    csv_path = results / "mass_profile.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "radius_cm",
                "radius_pc",
                "m_swept_iso_g",
                "m_swept_iso_msun",
                "m_decel_iso_g",
                "m_decel_iso_msun",
                "m_decel_dynamic_iso_g",
                "m_10xdecel_dynamic_iso_g",
                "r_decel_cm",
                "r_decel_pc",
                "r_decel_10x_cm",
                "r_decel_10x_pc",
                "m_ejecta_iso_g",
                "m_ejecta_iso_msun",
                "r_ejecta_equal_cm",
                "r_ejecta_equal_pc",
                "obs_tmin_days",
                "obs_tmax_days",
                "obs_rmin_cm",
                "obs_rmax_cm",
                "obs_rmin_pc",
                "obs_rmax_pc",
            ]
        )
        for radius, mass, mdec_dyn, mdec10_dyn in zip(r_cm, mass_g, decel_mass_curve_g, decel_mass_10x_curve_g):
            writer.writerow(
                [
                    radius,
                    radius / PC_CM,
                    mass,
                    mass / MSUN_G,
                    decel_mass_g,
                    decel_mass_g / MSUN_G,
                    mdec_dyn,
                    mdec10_dyn,
                    r_decel_cm,
                    r_decel_cm / PC_CM if math.isfinite(r_decel_cm) else float("nan"),
                    r_decel_10x_cm,
                    r_decel_10x_cm / PC_CM if math.isfinite(r_decel_10x_cm) else float("nan"),
                    ejecta_mass_g,
                    ejecta_mass_g / MSUN_G,
                    r_ejecta_cm,
                    r_ejecta_cm / PC_CM if math.isfinite(r_ejecta_cm) else float("nan"),
                    obs_tmin_days,
                    obs_tmax_days,
                    obs_rmin_cm,
                    obs_rmax_cm,
                    obs_rmin_cm / PC_CM if math.isfinite(obs_rmin_cm) else float("nan"),
                    obs_rmax_cm / PC_CM if math.isfinite(obs_rmax_cm) else float("nan"),
                ]
            )

    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    ax.plot(r_cm, mass_g, lw=2.1, color="tab:blue", label=r"$M_{\rm sw,iso}(<r)$")
    if math.isfinite(obs_rmin_cm) and math.isfinite(obs_rmax_cm) and obs_rmax_cm > obs_rmin_cm:
        ax.axvspan(obs_rmin_cm, obs_rmax_cm, color="0.55", alpha=0.18, lw=0, label="Data radial range")
    ax.plot(r_cm, decel_mass_curve_g, lw=1.6, ls=":", color="tab:red", label=r"$M_{\rm ej,iso}/\Gamma(r)$")
    ax.plot(r_cm, decel_mass_10x_curve_g, lw=1.6, ls=":", color="tab:purple", label=r"$10\,M_{\rm ej,iso}/\Gamma(r)$")
    if math.isfinite(r_decel_cm):
        ax.axvline(r_decel_cm, lw=1.3, ls=":", color="tab:red")
        ax.scatter(
            [r_decel_cm],
            [np.interp(r_decel_cm, r_cm, decel_mass_curve_g)],
            s=42,
            color="tab:red",
            edgecolor="black",
            linewidth=0.5,
            zorder=5,
        )
    if math.isfinite(r_decel_10x_cm):
        ax.axvline(r_decel_10x_cm, lw=1.3, ls=":", color="tab:purple")
        ax.scatter(
            [r_decel_10x_cm],
            [np.interp(r_decel_10x_cm, r_cm, decel_mass_10x_curve_g)],
            s=42,
            color="tab:purple",
            edgecolor="black",
            linewidth=0.5,
            zorder=5,
        )
    ax.axhline(
        ejecta_mass_g,
        lw=1.6,
        ls="--",
        color="tab:orange",
        label=r"$M_{\rm sw,iso}=M_{\rm ej,iso}$",
    )
    if math.isfinite(r_ejecta_cm):
        ax.axvline(r_ejecta_cm, lw=1.3, ls="--", color="tab:orange")
        ax.scatter([r_ejecta_cm], [ejecta_mass_g], s=42, color="tab:orange", edgecolor="black", linewidth=0.5, zorder=5)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Radius [cm]")
    ax.set_ylabel("Isotropic-equivalent mass [g]")
    ax.grid(False, which="both")
    ax.legend(fontsize=8, loc="best")

    top = ax.secondary_xaxis("top", functions=(cm_to_pc, pc_to_cm))
    top.set_xlabel("Radius [pc]", labelpad=4)
    top.tick_params(axis="x", labelsize=8)
    right = ax.secondary_yaxis("right", functions=(g_to_msun, msun_to_g))
    right.set_ylabel(r"Isotropic-equivalent mass [$M_\odot$]")
    right.tick_params(axis="y", labelsize=8)

    label = f"GRB {event} | {display_run_label(results, event)} | {source}"
    if nmap is not None:
        label += f" | nmap={nmap:.3g}"
    apply_plot_title(fig, "Isotropic-equivalent Swept-up Mass Profile", y=0.955, top=0.86)
    apply_plot_run_label(fig, label=label)
    fig.subplots_adjust(left=0.12, right=0.86, bottom=0.16, top=0.82)
    fig.savefig(results / "mass_profile.pdf")
    fig.savefig(results / "mass_profile.png", dpi=220)
    plt.close(fig)


def thesis_physical_value(name: str, median: float) -> float:
    if name in THESIS_LOG10_PARAMS:
        return 10.0 ** median
    return median


def flatten_sections(params: dict[str, Any]) -> dict[str, float]:
    flat: dict[str, float] = {}
    for section in ("model", "extinction", "host", "offsets", "slop"):
        values = params.get(section, {})
        if not isinstance(values, dict):
            continue
        for name, value in values.items():
            try:
                flat[name] = float(value)
            except Exception:
                pass
    return flat


def fit_context_summary(model_name: str, model_params: dict[str, Any]) -> str:
    parts: list[str] = [f"model={model_name}"]
    theta_c = model_params.get("theta_c")
    theta_v = model_params.get("theta_v")
    if theta_c is not None:
        try:
            parts.append(f"theta_c={float(theta_c):.3g} rad")
        except Exception:
            pass
    if theta_v is not None:
        try:
            parts.append(f"theta_v={float(theta_v):.3g} rad")
        except Exception:
            pass
    if model_name in {"powerlawVegasModel", "powerlawVegasDylanSpectrumModel"}:
        parts.append("jet=top-hat")
    elif "PowerlawJet" in model_name:
        parts.append("jet=structured_powerlaw")
    return ", ".join(parts)


def write_ampy_missing_note(results: Path, event: str, source: str, reason: str, detail: str) -> None:
    note_path = results / AMPY_MISSING_NOTE
    note = (
        f"# AMPy Comparison Not Produced\n\n"
        f"- Event: `{event}`\n"
        f"- Run label: `{display_run_label(results, event)}`\n"
        f"- Post-fit source: `{source}`\n"
        f"- Reason code: `{reason}`\n\n"
        f"{detail}\n"
    )
    note_path.write_text(note)


def plot_ampy_comparison(
    results: Path,
    event: str,
    params: dict[str, Any],
    model_name: str,
    source: str,
    nmap: float | None,
) -> None:
    thesis = THESIS.get(normalize_event_name(event))
    if thesis is None:
        print(f"WARNING: no Dylan thesis values for {event}; skipping ampy_comparison.pdf")
        write_ampy_missing_note(
            results,
            event,
            source,
            "missing_thesis_reference",
            "No entry was found in `scripts/thesis_reproduction_data.py::THESIS` for this GRB.",
        )
        return

    current = flatten_sections(params)
    context = fit_context_summary(model_name, params.get("model", {}))
    nmap_text = f"{nmap:.3g}" if (nmap is not None and math.isfinite(nmap)) else "n/a"
    rows: list[dict[str, Any]] = []
    for name, triple in thesis.items():
        if name == "model" or name not in current:
            continue
        median = float(triple[0])
        dylan = thesis_physical_value(name, median)
        new = float(current[name])
        if not (math.isfinite(new) and math.isfinite(dylan)) or dylan == 0.0:
            continue
        denom = abs(new) + abs(dylan)
        symmetric_delta = (new - dylan) / denom if denom > 0.0 else float("nan")
        rows.append(
            {
                "parameter": name,
                "this_fit": new,
                "dylan_thesis": dylan,
                "ratio_to_dylan": new / dylan,
                "log10_ratio_to_dylan": math.log10(new / dylan) if new / dylan > 0.0 else float("nan"),
                "symmetric_delta_over_sum": symmetric_delta,
            }
        )

    if not rows:
        print(f"WARNING: no common Dylan/current parameters for {event}; skipping ampy_comparison.pdf")
        write_ampy_missing_note(
            results,
            event,
            source,
            "no_common_parameters",
            "A Dylan thesis entry exists, but there were no overlapping parameters between the run output and thesis table.",
        )
        return

    csv_path = results / "ampy_comparison.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "parameter",
                "this_fit",
                "dylan_thesis",
                "ratio_to_dylan",
                "log10_ratio_to_dylan",
                "symmetric_delta_over_sum",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    plot_rows = [row for row in rows if math.isfinite(float(row["log10_ratio_to_dylan"]))]
    if not plot_rows:
        print(f"WARNING: no positive Dylan/current ratios for {event}; skipping ampy_comparison.pdf")
        write_ampy_missing_note(
            results,
            event,
            source,
            "no_finite_log_ratios",
            "Overlapping parameters were found, but no finite `log10(this_fit / dylan_fit)` values could be produced.",
        )
        return

    labels = [row["parameter"] for row in plot_rows]
    log_ratios = np.asarray([row["log10_ratio_to_dylan"] for row in plot_rows], dtype=float)
    colors = ["tab:blue" if value >= 0.0 else "tab:orange" for value in log_ratios]
    this_vals = np.asarray([row["this_fit"] for row in plot_rows], dtype=float)
    dylan_vals = np.asarray([row["dylan_thesis"] for row in plot_rows], dtype=float)

    fig_width = max(7.5, 0.58 * len(labels) + 2.0)
    fig, ax = plt.subplots(figsize=(fig_width, 5.0))
    ax.bar(np.arange(len(labels)), log_ratios, color=colors, alpha=0.86)
    ax.axhline(0.0, lw=1.5, color="black", ls="--", label="Dylan/AMPy")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel(r"$\log_{10}$(VegasAfterglow fit / AMPy fit)")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    y_span = float(max(np.max(np.abs(log_ratios)), 1.0))
    for i, y in enumerate(log_ratios):
        label = f"VA={this_vals[i]:.3g}\nAMPy={dylan_vals[i]:.3g}"
        # Place labels on the opposite side of the zero line to keep bars visible.
        dy = -7 if y >= 0.0 else 7
        va = "top" if y >= 0.0 else "bottom"
        ax.annotate(
            label,
            (i, 0.0),
            xytext=(0, dy),
            textcoords="offset points",
            ha="center",
            va=va,
            fontsize=7,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.75, edgecolor="none"),
            clip_on=False,
        )
    ax.set_ylim(min(-y_span - 0.25, ax.get_ylim()[0]), max(y_span + 0.45, ax.get_ylim()[1]))
    apply_plot_title(fig, "VegasAfterglow / AMPy Fit Log Parameter Ratios", y=0.99, top=0.90)
    apply_plot_run_label(
        fig,
        label=(
            f"GRB {event} | {display_run_label(results, event)} | {source} | "
            f"nmap={nmap_text} | This fit: {context} vs Dylan AMPy thesis"
        ),
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.savefig(results / "ampy_comparison.pdf")
    fig.savefig(results / "ampy_comparison.png", dpi=220)
    plt.close(fig)

    # Robust, bounded comparison that remains defined even when signs differ.
    sym_rows = [row for row in rows if math.isfinite(float(row["symmetric_delta_over_sum"]))]
    if sym_rows:
        sym_labels = [row["parameter"] for row in sym_rows]
        sym_values = np.asarray([row["symmetric_delta_over_sum"] for row in sym_rows], dtype=float)
        sym_colors = ["tab:blue" if value >= 0.0 else "tab:orange" for value in sym_values]
        sym_this = np.asarray([row["this_fit"] for row in sym_rows], dtype=float)
        sym_dylan = np.asarray([row["dylan_thesis"] for row in sym_rows], dtype=float)

        fig_width = max(7.5, 0.58 * len(sym_labels) + 2.0)
        fig, ax = plt.subplots(figsize=(fig_width, 5.0))
        ax.bar(np.arange(len(sym_labels)), sym_values, color=sym_colors, alpha=0.86)
        ax.axhline(0.0, lw=1.5, color="black", ls="--", label="No difference")
        ax.set_ylim(-1.02, 1.02)
        ax.set_xticks(np.arange(len(sym_labels)))
        ax.set_xticklabels(sym_labels, rotation=45, ha="right")
        ax.set_ylabel(r"$(x_{\rm VA} - x_{\rm AMPy}) / (|x_{\rm VA}| + |x_{\rm AMPy}|)$")
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(fontsize=8)
        for i, y in enumerate(sym_values):
            label = f"VA={sym_this[i]:.3g}\nAMPy={sym_dylan[i]:.3g}"
            # Place labels on the opposite side of the zero line to keep bars visible.
            dy = -7 if y >= 0.0 else 7
            va = "top" if y >= 0.0 else "bottom"
            ax.annotate(
                label,
                (i, 0.0),
                xytext=(0, dy),
                textcoords="offset points",
                ha="center",
                va=va,
                fontsize=7,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.75, edgecolor="none"),
                clip_on=False,
            )
        apply_plot_title(fig, "VegasAfterglow vs AMPy Symmetric Parameter Difference", y=0.99, top=0.90)
        apply_plot_run_label(
            fig,
            label=(
                f"GRB {event} | {display_run_label(results, event)} | {source} | "
                f"nmap={nmap_text} | This fit: {context} vs Dylan AMPy thesis"
            ),
        )
        fig.tight_layout(rect=(0, 0.04, 1, 0.92))
        fig.savefig(results / "ampy_comparison_symmetric.pdf")
        fig.savefig(results / "ampy_comparison_symmetric.png", dpi=220)
        plt.close(fig)
    note_path = results / AMPY_MISSING_NOTE
    if note_path.exists():
        note_path.unlink()


def remove_old_profile_outputs(results: Path) -> None:
    for stem in ("n_profile", "n0_profile", "k_profile"):
        for ext in ("pdf", "png"):
            path = results / f"{stem}.{ext}"
            if path.exists():
                path.unlink()


def regenerate_density_profiles(results: Path, event: str, params: dict[str, Any]) -> None:
    chain_path = results / "chain.npz"
    obs_path = results / "obs.csv"
    model_path = results / "model.toml"
    if not (chain_path.exists() and obs_path.exists() and model_path.exists()):
        print("WARNING: missing chain/model/obs; skipping density profile regeneration")
        return

    os.environ["JETFIT_PLOT_RUN_LABEL"] = f"GRB {event} | {display_run_label(results, event)} | minimized overlay"
    np.random.seed(1729)

    ampy = Ampy(obs_path, model_path)
    with np.load(chain_path) as data:
        chain = np.asarray(data["chain"])
        lnprob = np.asarray(data["lnprob"])
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if lnprob.ndim == 3:
        lnprob = lnprob[:, 0, :]
    flat_chain = chain.reshape((-1, chain.shape[-1]))
    flat_lnprob = lnprob.reshape((-1,))

    remove_old_profile_outputs(results)
    visualize.plot_density_profile(
        flat_chain,
        flat_lnprob,
        ampy.mcmc.params,
        ampy.obs,
        ampy.afterglow_model,
        model_kw=ampy.mcmc.models.afg_kw,
        best=params.get("model"),
        out_dir=results,
    )


def maybe_generate_structjet_swept_mass_overlay(results: Path, model_name: str) -> None:
    """Generate structured-jet swept-mass overlay products for PowerLawJet models."""
    if "PowerlawJet" not in model_name:
        return

    script = Path(__file__).resolve().parent / "plot_structjet_swept_mass_diagnostics.py"
    if not script.exists():
        print(f"WARNING: missing structured-jet overlay script: {script}")
        return

    env = dict(os.environ)
    root = Path(__file__).resolve().parents[1]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{root}:{existing}" if existing else str(root)

    cmd = [sys.executable, str(script), "--run-dir", str(results)]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print("WARNING: structured-jet swept-mass overlay generation failed.")
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip())
    else:
        if proc.stdout.strip():
            print(proc.stdout.strip())


def main() -> int:
    args = parse_args()
    results = args.results.expanduser().resolve()
    event = infer_event(results, args.event)
    model_cfg = load_model_toml(results)
    model_name = str(model_cfg.get("name", ""))
    params, source, nmap = load_postfit_params(results)
    os.environ["JETFIT_PLOT_EVENT_TITLE"] = f"GRB {event}"
    os.environ["JETFIT_PLOT_RUN_LABEL"] = f"GRB {event} | {display_run_label(results, event)} | {source}"

    if "model" not in params:
        raise ValueError(f"{source} does not contain a model parameter section.")

    plot_mass_profile(results, event, params, model_name, source, nmap)
    plot_ampy_comparison(results, event, params, model_name, source, nmap)
    maybe_generate_structjet_swept_mass_overlay(results, model_name)
    if not args.skip_density_replot:
        regenerate_density_profiles(results, event, params)

    print(f"postfit_products_ok results={results} source={source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
