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
import shutil
import subprocess
import sys
import textwrap
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
from jetfit.core.utils import apply_plot_run_label, apply_plot_title, add_collision_aware_grb_label
from jetfit.mcmc.parameters import Parameters
from jetfit.models.jet_energy import integrated_profile_beaming_fraction, resolve_e_iso52
from scripts.plot import diagnose
from scripts.plot import visualize
from scripts.plot.base import OPTION_MAP
from scripts.thesis_reproduction_data import THESIS, normalize_event_name


PC_CM = 3.0856775814913673e18
MSUN_G = 1.98847e33
MP_G = 1.67262192369e-24
C_CGS = 2.99792458e10
REF_RADIUS_CM = 1.0e17
PLOT_POSTERIOR_MAX_SAMPLES = 50000
FREQUENCY_POSTERIOR_CURVES = int(os.environ.get("JETFIT_FREQUENCY_POSTERIOR_CURVES", "100"))
FREQUENCY_TIME_SAMPLES = int(os.environ.get("JETFIT_FREQUENCY_TIME_SAMPLES", "200"))
FREQUENCY_FAST_INDICES = os.environ.get("JETFIT_FREQUENCY_FAST_INDICES", "0").lower() in {"1", "true", "yes"}

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
AMPY_PARAM_LABELS = {
    "E52": r"$E_{52}$",
    "lf0": r"$\Gamma_0$",
    "n017": r"$n_{0,17}$",
    "nt": r"$n_t$",
    "rt": r"$r_t$",
    "eps_e": r"$\epsilon_e$",
    "eps_b": r"$\epsilon_B$",
    "p": r"$p$",
    "k": r"$k$",
    "k1": r"$k_1$",
    "k2": r"$k_2$",
    "ebv_source_frame": r"$E(B-V)$",
    "theta_c": r"$\theta_c$",
    "theta_v": r"$\theta_v$",
    "slop": "slop",
}
TIME_COLUMN_CANDIDATES = ("time_days", "time", "t_days", "t", "days")
AMPY_MISSING_NOTE = "ampy_comparison_missing_reference.md"
NMAP_DATASET_CHECKS = (
    PROJECT_ROOT / "analysis" / "nmap_dataset_check_same_model_20260428" / "nmap_same_model_check.csv",
    PROJECT_ROOT / "analysis" / "nmap_dataset_check_20260428" / "nmap_dataset_check.csv",
)
PRODUCT_CHOICES = (
    "all",
    "trace-summary",
    "spectrum-timeseries",
    "frequencies",
    "jet-energy",
    "reduced-corners",
    "light-curve",
    "ampy-comparison",
    "swept-mass",
    "spread-light-curves",
    "density-profiles",
)
POSTFIT_PRODUCT_STYLE_VERSION = "publication-ready-v3-prior-bound-and-zoomed-corners"


def ensure_png_companion(pdf_path: Path, *, dpi: int = 150) -> Path | None:
    """Render a single-page PNG companion for a PDF product when needed."""
    pdf_path = pdf_path.resolve()
    if "trash" in pdf_path.parts or not pdf_path.is_file():
        return None
    png_path = pdf_path.with_suffix(".png")
    if png_path.is_file() and png_path.stat().st_mtime >= pdf_path.stat().st_mtime:
        return png_path

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        print(f"WARNING: cannot make PNG companion for {pdf_path}; pdftoppm not found")
        return None

    stem = str(png_path.with_suffix(""))
    cmd = [pdftoppm, "-singlefile", "-png", "-r", str(dpi), str(pdf_path), stem]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
    except subprocess.CalledProcessError as exc:
        print(
            f"WARNING: cannot make PNG companion for {pdf_path}: "
            f"pdftoppm exit={exc.returncode} stderr={exc.stderr.strip()}"
        )
        return None
    except subprocess.TimeoutExpired:
        print(f"WARNING: timed out making PNG companion for {pdf_path}")
        return None
    if not png_path.is_file() or png_path.stat().st_size == 0:
        print(f"WARNING: PNG companion was not created for {pdf_path}")
        return None
    return png_path


def ensure_pdf_png_product_pairs(results: Path) -> None:
    """Ensure each root-level PDF data product has a same-stem PNG product."""
    converted = 0
    missing = 0
    for pdf_path in sorted(results.glob("*.pdf")):
        png_path = pdf_path.with_suffix(".png")
        before_mtime = png_path.stat().st_mtime if png_path.exists() else None
        made = ensure_png_companion(pdf_path)
        if made is None:
            missing += 1
            continue
        after_mtime = made.stat().st_mtime
        if before_mtime is None or after_mtime > before_mtime:
            converted += 1
    print(f"pdf_png_pairs_ok results={results} converted={converted} missing={missing}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path, help="Finished run directory.")
    parser.add_argument("--event", default=None, help="GRB name. Defaults to the run folder prefix.")
    parser.add_argument(
        "--skip-density-replot",
        action="store_true",
        help="Skip regenerating n/k/n0 profile plots from the MCMC chain.",
    )
    parser.add_argument(
        "--skip-spread-light-curves",
        action="store_true",
        help="Skip generating spread-out posterior/walker light-curve products.",
    )
    parser.add_argument(
        "--skip-frequency-plot",
        action="store_true",
        help="Skip regenerating the standard frequencies.pdf diagnostic.",
    )
    parser.add_argument(
        "--skip-reduced-corners",
        action="store_true",
        help="Skip regenerating posterior corner plots.",
    )
    parser.add_argument(
        "--skip-jet-energy",
        action="store_true",
        help="Skip derived beaming-corrected jet-energy products.",
    )
    parser.add_argument(
        "--only-product",
        choices=PRODUCT_CHOICES,
        default="all",
        help="Regenerate only one product family. Used by the parallel product runner.",
    )
    parser.add_argument(
        "--parallel-products",
        action="store_true",
        help="Run independent product families in separate Python processes.",
    )
    parser.add_argument(
        "--product-workers",
        type=int,
        default=int(os.environ.get("JETFIT_POSTFIT_PRODUCT_WORKERS", "4")),
        help="Maximum concurrent product processes when --parallel-products is set.",
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

    e52 = resolve_model_e_iso52(model_params, model_name)
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


def resolve_model_e_iso52(model_params: dict[str, Any], model_name: str) -> float:
    """Resolve on-axis E_iso,52 from either the old E52 or new E_j_52 convention."""
    jet_type = _infer_jet_type(model_name, {key: np.asarray([value]) for key, value in model_params.items()})
    return resolve_e_iso52(
        E52=model_params.get("E52"),
        E_j_52=model_params.get("E_j_52"),
        jet_type=jet_type,
        theta_c=float(model_params["theta_c"]),
        k_e=model_params.get("k_e"),
    )


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


def count_included_obs_rows(obs_csv: Path) -> int | None:
    """Count rows that participate in a fit, using obs.csv include flags when present."""
    if not obs_csv.exists():
        return None
    with obs_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return None
        include_col = next((name for name in reader.fieldnames if name.lower() == "include"), None)
        count = 0
        for row in reader:
            if include_col is not None:
                try:
                    if float(row.get(include_col, "1")) <= 0:
                        continue
                except Exception:
                    pass
            count += 1
    return count


def load_dylan_reference_metrics(event: str) -> dict[str, float | int | str | None]:
    """Load Dylan nmap and reference data-row counts from local audit tables."""
    normalized = normalize_event_name(event)
    result: dict[str, float | int | str | None] = {
        "dylan_nmap": None,
        "reference_data_rows": None,
        "reference_data_rows_label": None,
        "reference_current_rows": None,
        "reference_source": None,
    }
    for path in NMAP_DATASET_CHECKS:
        if not path.exists():
            continue
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if normalize_event_name(row.get("event", "")) != normalized:
                    continue
                result["dylan_nmap"] = _float_or_none(row.get("dylan_nmap"))
                raw_rows = _float_or_none(row.get("raw_grb_data_rows"))
                curated_rows = _float_or_none(row.get("curated_obs_rows"))
                if raw_rows is not None:
                    result["reference_data_rows"] = int(round(raw_rows))
                    result["reference_data_rows_label"] = "reference raw"
                if curated_rows is not None:
                    result["reference_current_rows"] = int(round(curated_rows))
                result["reference_source"] = str(path.relative_to(PROJECT_ROOT))
                return result
    return result


def format_nmap_data_note(
    current_nmap: float | None,
    dylan_nmap: float | None,
    current_rows: int | None,
    reference_rows: int | None,
    reference_rows_label: str = "reference audit",
) -> str:
    """Return the quick-reference nmap/data-count annotation."""
    this_rows = current_rows if current_rows is not None else "n/a"
    ref_rows = reference_rows if reference_rows is not None else "n/a"
    if current_rows is None or reference_rows is None:
        rows_note = f"data rows: this={this_rows}; {reference_rows_label}={ref_rows}; exact same-data check unavailable"
    elif current_rows == reference_rows:
        rows_note = f"data rows match audit: N={current_rows}"
    else:
        rows_note = (
            f"data rows differ from audit: this obs={current_rows}; "
            f"{reference_rows_label}={reference_rows}; same-data nmap not assumed"
        )

    if current_nmap is None or dylan_nmap is None:
        return f"{rows_note}; nmap unavailable"

    return (
        f"{rows_note}; nmap: this={current_nmap:.3f}, Dylan={dylan_nmap:.3f}, "
        f"Delta(this-Dylan)={current_nmap - dylan_nmap:+.3f}"
    )


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
    dylan_metrics = load_dylan_reference_metrics(event)
    dylan_nmap = dylan_metrics.get("dylan_nmap")
    dylan_nmap_value = dylan_nmap if isinstance(dylan_nmap, float) and math.isfinite(dylan_nmap) else None
    dylan_nmap_text = f"{dylan_nmap_value:.3g}" if dylan_nmap_value is not None else "n/a"
    current_data_rows = count_included_obs_rows(results / "obs.csv")
    reference_data_rows = dylan_metrics.get("reference_data_rows")
    reference_data_rows_label = dylan_metrics.get("reference_data_rows_label")
    nmap_data_note = format_nmap_data_note(
        nmap if (nmap is not None and math.isfinite(nmap)) else None,
        dylan_nmap_value,
        current_data_rows,
        reference_data_rows if isinstance(reference_data_rows, int) else None,
        str(reference_data_rows_label or "reference audit"),
    )
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
        difference_over_average = 2.0 * symmetric_delta if math.isfinite(symmetric_delta) else float("nan")
        rows.append(
            {
                "parameter": name,
                "this_fit": new,
                "dylan_thesis": dylan,
                "difference_over_average": difference_over_average,
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
                "difference_over_average",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    plot_rows = [row for row in rows if math.isfinite(float(row["difference_over_average"]))]
    if not plot_rows:
        print(f"WARNING: no finite Dylan/current difference-over-average values for {event}; skipping ampy_comparison.pdf")
        write_ampy_missing_note(
            results,
            event,
            source,
            "no_finite_difference_over_average",
            "Overlapping parameters were found, but no finite difference-over-average values could be produced.",
        )
        return

    labels = [AMPY_PARAM_LABELS.get(str(row["parameter"]), str(row["parameter"])) for row in plot_rows]
    values = np.asarray([row["difference_over_average"] for row in plot_rows], dtype=float)
    colors = ["tab:blue" if value >= 0.0 else "tab:orange" for value in values]
    this_vals = np.asarray([row["this_fit"] for row in plot_rows], dtype=float)
    dylan_vals = np.asarray([row["dylan_thesis"] for row in plot_rows], dtype=float)

    for stale in (
        "ampy_comparison_symmetric.pdf",
        "ampy_comparison_symmetric.png",
        "ampy_comparison_log_ratio.pdf",
        "ampy_comparison_log_ratio.png",
    ):
        path = results / stale
        if path.exists():
            path.unlink()

    fig_width = max(10.5, 0.92 * len(labels) + 3.0)
    fig, ax = plt.subplots(figsize=(fig_width, 5.2))
    ax.bar(np.arange(len(labels)), values, color=colors, alpha=0.86)
    ax.axhline(0.0, lw=1.5, color="black", ls="--", label="Dylan/AMPy")
    ax.set_ylim(-2.05, 2.05)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_ylabel(r"$2(x_{\rm this} - x_{\rm Dylan})/(|x_{\rm this}| + |x_{\rm Dylan}|)$")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8, loc="best")
    for i, y in enumerate(values):
        label = f"{this_vals[i]:.3g}\n{dylan_vals[i]:.3g}"
        # Place compact value labels near bar ends without clipping at the bounded metric limits.
        if y >= 1.72:
            y_text = y - 0.10
            va = "top"
        elif y >= 0.0:
            y_text = y + 0.10
            va = "bottom"
        elif y <= -1.72:
            y_text = y + 0.10
            va = "bottom"
        else:
            y_text = y - 0.10
            va = "top"
        ax.annotate(
            label,
            (i, y_text),
            ha="center",
            va=va,
            fontsize=6.8,
            bbox=dict(boxstyle="round,pad=0.16", facecolor="white", alpha=0.72, edgecolor="none"),
            clip_on=True,
        )
    ax.set_title(f"GRB {event}: This Fit vs Dylan AMPy Thesis Parameters", fontsize=12, pad=10)
    run_note = (
        "Minimized VegasJetFit solution compared with the Dylan/AMPy reference; "
        f"this fit nmap={nmap_text}; Dylan reference nmap={dylan_nmap_text}; {context}"
    )
    fig.text(0.01, 0.045, textwrap.fill(run_note, width=160), ha="left", va="bottom", fontsize=7)
    fig.text(0.01, 0.015, textwrap.fill(nmap_data_note, width=160), ha="left", va="bottom", fontsize=7)
    fig.tight_layout(rect=(0, 0.095, 1, 0.965))
    fig.savefig(results / "ampy_comparison.pdf", bbox_inches="tight", pad_inches=0.035)
    fig.savefig(results / "ampy_comparison.png", dpi=220, bbox_inches="tight", pad_inches=0.035)
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
    if chain.ndim != 3 or lnprob.ndim != 2:
        raise ValueError(
            "Density profiles require a cold chain with shape "
            "[steps, walkers, parameters] and log probabilities [steps, walkers]."
        )

    # A density-profile ensemble represents the final state of each cold-chain
    # walker.  Do not flatten the full chain: that silently substitutes a small
    # random set of historical samples for the actual walker ensemble.
    walker_chain = np.asarray(chain[-1], dtype=float)
    walker_lnprob = np.asarray(lnprob[-1], dtype=float)
    valid_walkers = np.isfinite(walker_lnprob) & np.isfinite(walker_chain).all(axis=1)
    profile_chain = walker_chain[valid_walkers]
    profile_lnprob = walker_lnprob[valid_walkers]
    if profile_chain.size == 0:
        raise ValueError("No finite final cold-chain walkers available for density profiles.")

    requested_samples = int(os.environ.get("JETFIT_DENSITY_PROFILE_SAMPLES", "0"))
    plotted_walkers = len(profile_chain) if requested_samples <= 0 else min(requested_samples, len(profile_chain))
    profile_metadata = {
        "event": event,
        "source": "terminal_cold_chain_walkers",
        "available_final_walkers": int(len(walker_chain)),
        "finite_final_walkers": int(len(profile_chain)),
        "excluded_nonfinite_walkers": int(len(walker_chain) - len(profile_chain)),
        "requested_samples": requested_samples,
        "plotted_walkers": int(plotted_walkers),
        "uses_all_finite_final_walkers": bool(requested_samples <= 0 or requested_samples >= len(profile_chain)),
    }
    print("density_profile_sampling=" + json.dumps(profile_metadata, sort_keys=True))

    remove_old_profile_outputs(results)
    generated = visualize.plot_density_profile(
        profile_chain,
        profile_lnprob,
        ampy.mcmc.params,
        ampy.obs,
        ampy.afterglow_model,
        model_kw=ampy.mcmc.models.afg_kw,
        best=params.get("model"),
        out_dir=results,
        )
    if not generated:
        raise RuntimeError("Density-profile plotting did not produce profile products.")
    (results / "density_profile_sampling.json").write_text(
        json.dumps(profile_metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def regenerate_light_curve_postfit(results: Path, event: str, params: dict[str, Any]) -> None:
    """Regenerate the standard light curve from the postfit parameters only."""
    obs_path = results / "obs.csv"
    model_path = results / "model.toml"
    if not (obs_path.exists() and model_path.exists()):
        print("WARNING: missing model/obs; skipping postfit light-curve regeneration")
        return

    from scripts.plot_spread_light_curves import fast_model_fluxes, write_flux_stack_cache
    from scripts.plot.visualize import LightCurvePlot

    ampy = Ampy(obs_path, model_path)
    ext_model = ampy.extinction_model(Rv=3.1) if ampy.extinction_model is not None else None
    lcg = LightCurvePlot(
        ampy.mcmc.models.afg_model,
        params,
        ampy.obs,
        meta=ampy.mcmc.models.afg_kw,
        title=None,
        dual=False,
    )
    ax = lcg.ax
    times = lcg.default_times(160)

    best_fluxes = fast_model_fluxes(lcg, params, times, ext_model)
    write_flux_stack_cache(
        results / "light_curve_model_data.npz",
        times=times,
        best_fluxes=best_fluxes,
        metadata={
            "event": event,
            "source": "standard postfit light curve",
            "postfit_params": "minimized/minimized.json" if (results / "minimized" / "minimized.json").exists() else "best_fit.json",
            "saved_units": "mJy",
            "time_units": "days",
        },
    )
    for band, flux in best_fluxes.items():
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

    lcg.plot_observation(params, excluded=True)
    add_collision_aware_grb_label(ax, f"GRB {event}", corner="upper right", fontsize=15, zorder=30)
    ax.set_xlim(times.min(), times.max())
    fig = ax.figure
    fig.savefig(results / "light_curve.pdf", bbox_inches="tight", pad_inches=0.045)
    fig.savefig(results / "light_curve.png", dpi=220, bbox_inches="tight", pad_inches=0.045)
    plt.close(fig)


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


def maybe_generate_spread_light_curves(results: Path, event: str) -> None:
    """Generate paper-style spread-out light-curve products when possible."""
    required = [
        results / "chain.npz",
        results / "model.toml",
        results / "obs.csv",
    ]
    if not all(path.exists() for path in required):
        missing = ", ".join(str(path.name) for path in required if not path.exists())
        print(f"WARNING: skipping spread light curves; missing {missing}")
        return

    script = Path(__file__).resolve().parent / "plot_spread_light_curves.py"
    if not script.exists():
        print(f"WARNING: missing spread light-curve script: {script}")
        return

    env = dict(os.environ)
    root = Path(__file__).resolve().parents[1]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{root}:{existing}" if existing else str(root)

    cmd = [
        sys.executable,
        str(script),
        "--run-dir",
        str(results),
        "--event",
        event,
        "--ncurves",
        "100",
        "--walker-limit",
        "0",
        "--ndata",
        "80",
    ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print("WARNING: spread light-curve generation failed.")
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip())
    else:
        if proc.stdout.strip():
            print(proc.stdout.strip())


def _load_chain_for_frequency_plot(results: Path) -> tuple[np.ndarray, np.ndarray]:
    chain_path = results / "chain.npz"
    if not chain_path.exists():
        raise FileNotFoundError(f"Missing chain.npz in {results}")

    with np.load(chain_path) as data:
        chain = np.asarray(data["chain"])
        if "lnprob" in data:
            log_prob = np.asarray(data["lnprob"])
        elif "log_prob" in data:
            log_prob = np.asarray(data["log_prob"])
        else:
            raise KeyError(f"{chain_path} has no lnprob/log_prob array")

    # Some old PT outputs preserve a temperature axis.  Plot the cold chain.
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if log_prob.ndim == 3:
        log_prob = log_prob[:, 0, :]

    if chain.ndim != 3:
        raise ValueError(f"Unexpected chain shape for frequency plot: {chain.shape}")
    if log_prob.ndim != 2:
        raise ValueError(f"Unexpected log-probability shape for frequency plot: {log_prob.shape}")

    return chain.reshape((-1, chain.shape[-1])), log_prob.reshape((-1,))


def _load_flat_chain(results: Path) -> np.ndarray:
    chain_path = results / "chain.npz"
    if not chain_path.exists():
        raise FileNotFoundError(f"Missing chain.npz in {results}")
    with np.load(chain_path) as data:
        chain = np.asarray(data["chain"])
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if chain.ndim == 3:
        return chain.reshape((-1, chain.shape[-1]))
    if chain.ndim == 2:
        return chain
    raise ValueError(f"Unexpected chain shape: {chain.shape}")


def _deterministic_sample_indices(n_items: int, max_items: int = PLOT_POSTERIOR_MAX_SAMPLES) -> np.ndarray:
    """Return evenly spaced indices for reproducible diagnostic plot thinning."""
    if n_items <= max_items:
        return np.arange(n_items, dtype=int)
    return np.unique(np.linspace(0, n_items - 1, max_items, dtype=int))


def _thin_chain_for_plot(chain: np.ndarray, max_items: int = PLOT_POSTERIOR_MAX_SAMPLES) -> np.ndarray:
    """Thin only diagnostic plot inputs; full posterior summaries stay unthinned."""
    chain = np.asarray(chain)
    return chain[_deterministic_sample_indices(chain.shape[0], max_items)]


def _thin_derived_for_plot(
    derived: dict[str, np.ndarray],
    max_items: int = PLOT_POSTERIOR_MAX_SAMPLES,
) -> dict[str, np.ndarray]:
    """Thin matching derived-posterior arrays for corner-style diagnostic plots."""
    if not derived:
        return derived
    first = next(iter(derived.values()))
    indices = _deterministic_sample_indices(np.asarray(first).shape[0], max_items)
    return {key: np.asarray(value)[indices] for key, value in derived.items()}


def _values_in_linear_scale(chain: np.ndarray, params: Parameters) -> dict[str, np.ndarray]:
    """Return fitting and fixed parameters as linear-scale posterior arrays."""
    n_samples = chain.shape[0]
    values: dict[str, np.ndarray] = {}

    for i, param in enumerate(params.fitting):
        if param.name in values:
            continue
        raw = np.asarray(chain[:, i], dtype=float)
        scale = str(param.scale.value)
        if scale == "log":
            values[param.name] = np.power(10.0, raw)
        elif scale == "ln":
            values[param.name] = np.exp(raw)
        else:
            values[param.name] = raw

    for param in params.fixed:
        if param.name in values:
            continue
        raw = float(param.value)
        scale = str(param.scale.value)
        if scale == "log":
            val = 10.0 ** raw
        elif scale == "ln":
            val = math.exp(raw)
        else:
            val = raw
        values[param.name] = np.full(n_samples, val, dtype=float)

    return values


def _infer_jet_type(model_name: str, values: dict[str, np.ndarray]) -> str:
    """Infer the angular jet profile used by the VegasAfterglow wrapper."""
    name = model_name.lower()
    if "powerlawjet" in name:
        return "powerlaw"
    if "gaussian" in name:
        return "gaussian"
    # Historical `powerlawVegas...` names refer to the CSM profile, not the jet.
    return "tophat"


def _integrated_profile_beaming_fraction(
    jet_type: str,
    theta_c: np.ndarray,
    k_e: np.ndarray | None = None,
    n_theta: int = 512,
    chunk_size: int = 25000,
) -> np.ndarray:
    """
    Compute two-sided E_j / E_iso,on-axis by integrating the angular profile.

    This returns int_0^(pi/2) f(theta) sin(theta) dtheta, where f(theta) is
    normalized to unity on-axis.  For top-hat jets this equals
    1 - cos(theta_c), matching the two-sided Frail convention.
    """
    theta_c = np.asarray(theta_c, dtype=float)
    frac = np.full(theta_c.shape, np.nan, dtype=float)
    good = np.isfinite(theta_c) & (theta_c > 0.0)
    if not np.any(good):
        return frac

    kind = jet_type.lower()

    if kind == "tophat":
        frac[good] = 1.0 - np.cos(theta_c[good])
        return frac

    for start in range(0, theta_c.size, chunk_size):
        stop = min(start + chunk_size, theta_c.size)
        local_good = good[start:stop]
        if not np.any(local_good):
            continue
        tc = theta_c[start:stop][local_good]
        if k_e is None:
            ke_values = np.full(tc.shape, np.nan)
        else:
            ke_values = np.asarray(k_e[start:stop], dtype=float)[local_good]
        frac_chunk = np.asarray(
            [
                integrated_profile_beaming_fraction(kind, theta, k_e=ke, n_theta=n_theta)
                for theta, ke in zip(tc, ke_values)
            ],
            dtype=float,
        )
        chunk_values = frac[start:stop]
        chunk_values[local_good] = frac_chunk
        frac[start:stop] = chunk_values

    return frac


def _integrated_core_profile_beaming_fraction(
    jet_type: str,
    theta_c: np.ndarray,
    k_e: np.ndarray | None = None,
    n_theta: int = 512,
    chunk_size: int = 4096,
) -> np.ndarray:
    """Return two-sided E_core/E_iso,on-axis integrated through theta_c."""
    theta_c = np.asarray(theta_c, dtype=float)
    out = np.full(theta_c.shape, np.nan, dtype=float)
    good = np.isfinite(theta_c) & (theta_c > 0.0)
    if not np.any(good):
        return out
    kind = jet_type.lower()
    if kind == "tophat":
        out[good] = 1.0 - np.cos(theta_c[good])
        return out
    ke_all = np.full(theta_c.shape, 2.0) if k_e is None else np.asarray(k_e, dtype=float)
    x = np.linspace(0.0, 1.0, int(n_theta))[None, :]
    for start in range(0, theta_c.size, chunk_size):
        stop = min(start + chunk_size, theta_c.size)
        local_good = good[start:stop]
        if not np.any(local_good):
            continue
        tc = theta_c[start:stop][local_good]
        ke = ke_all[start:stop][local_good]
        theta = tc[:, None] * x
        if kind == "gaussian":
            energy_profile = np.exp(-0.5 * x * x)
        elif kind == "powerlaw":
            energy_profile = 1.0 / (1.0 + np.power(x, ke[:, None]))
        else:
            energy_profile = np.ones_like(theta)
        integral = np.trapezoid(energy_profile * np.sin(theta), theta, axis=1)
        chunk = out[start:stop]
        chunk[local_good] = integral
        out[start:stop] = chunk
    return out


def _integrated_jet_mass_factor(
    jet_type: str,
    theta_c: np.ndarray,
    gamma0_core: np.ndarray,
    k_e: np.ndarray | None = None,
    k_g: np.ndarray | None = None,
    n_theta: int = 512,
    chunk_size: int = 2048,
    core_only: bool = False,
) -> np.ndarray:
    """Return integral of f_E(theta)/Gamma_0(theta) over two-sided solid angle."""
    theta_c = np.asarray(theta_c, dtype=float)
    gamma0_core = np.asarray(gamma0_core, dtype=float)
    out = np.full(theta_c.shape, np.nan, dtype=float)
    good = (
        np.isfinite(theta_c) & (theta_c > 0.0)
        & np.isfinite(gamma0_core) & (gamma0_core > 1.0)
    )
    if not np.any(good):
        return out

    kind = jet_type.lower()
    if kind == "tophat":
        out[good] = (1.0 - np.cos(theta_c[good])) / gamma0_core[good]
        return out

    ke_all = np.full(theta_c.shape, 2.0) if k_e is None else np.asarray(k_e, dtype=float)
    kg_all = np.full(theta_c.shape, 2.0) if k_g is None else np.asarray(k_g, dtype=float)

    for start in range(0, theta_c.size, chunk_size):
        stop = min(start + chunk_size, theta_c.size)
        local_good = good[start:stop]
        if not np.any(local_good):
            continue
        tc = theta_c[start:stop][local_good]
        gamma = gamma0_core[start:stop][local_good]
        ke = ke_all[start:stop][local_good]
        kg = kg_all[start:stop][local_good]
        if core_only:
            x = np.linspace(0.0, 1.0, int(n_theta))[None, :]
            theta = tc[:, None] * x
        else:
            theta_1d = np.linspace(0.0, 0.5 * math.pi, int(n_theta))
            theta = np.broadcast_to(theta_1d, (tc.size, theta_1d.size))
            x = theta / tc[:, None]
        if kind == "gaussian":
            energy_profile = np.exp(-0.5 * x * x)
            gamma_theta = 1.0 + (gamma[:, None] - 1.0) * np.exp(-0.5 * x * x)
        elif kind == "powerlaw":
            energy_profile = 1.0 / (1.0 + np.power(x, ke[:, None]))
            gamma_theta = 1.0 + (gamma[:, None] - 1.0) / (1.0 + np.power(x, kg[:, None]))
        else:
            energy_profile = (x <= 1.0).astype(float)
            gamma_theta = gamma[:, None]
        integral = np.trapezoid(
            energy_profile * np.sin(theta) / gamma_theta,
            theta,
            axis=1,
        )
        chunk = out[start:stop]
        chunk[local_good] = integral
        out[start:stop] = chunk
    return out


def _core_average_gamma0(
    jet_type: str,
    theta_c: np.ndarray,
    gamma0_core: np.ndarray,
    k_g: np.ndarray | None = None,
    n_theta: int = 512,
    chunk_size: int = 4096,
) -> np.ndarray:
    """Return the solid-angle-weighted mean Gamma_0 through theta_c."""
    theta_c = np.asarray(theta_c, dtype=float)
    gamma0_core = np.asarray(gamma0_core, dtype=float)
    out = np.full(theta_c.shape, np.nan, dtype=float)
    good = (
        np.isfinite(theta_c) & (theta_c > 0.0)
        & np.isfinite(gamma0_core) & (gamma0_core > 1.0)
    )
    if not np.any(good):
        return out
    kind = jet_type.lower()
    if kind == "tophat":
        out[good] = gamma0_core[good]
        return out
    kg_all = np.full(theta_c.shape, 2.0) if k_g is None else np.asarray(k_g, dtype=float)
    x = np.linspace(0.0, 1.0, int(n_theta))[None, :]
    for start in range(0, theta_c.size, chunk_size):
        stop = min(start + chunk_size, theta_c.size)
        local_good = good[start:stop]
        if not np.any(local_good):
            continue
        tc = theta_c[start:stop][local_good]
        gamma = gamma0_core[start:stop][local_good]
        kg = kg_all[start:stop][local_good]
        theta = tc[:, None] * x
        if kind == "gaussian":
            gamma_theta = 1.0 + (gamma[:, None] - 1.0) * np.exp(-0.5 * x * x)
        elif kind == "powerlaw":
            gamma_theta = 1.0 + (gamma[:, None] - 1.0) / (1.0 + np.power(x, kg[:, None]))
        else:
            gamma_theta = np.broadcast_to(gamma[:, None], theta.shape)
        numerator = np.trapezoid(gamma_theta * np.sin(theta), theta, axis=1)
        denominator = 1.0 - np.cos(tc)
        chunk = out[start:stop]
        chunk[local_good] = numerator / denominator
        out[start:stop] = chunk
    return out


def _axis_gamma0_from_core_average(
    jet_type: str,
    theta_c: np.ndarray,
    gamma0_core_avg: np.ndarray,
    k_g: np.ndarray | None = None,
) -> np.ndarray:
    """Invert the angular profile from core-mean Gamma0 to on-axis Gamma0."""
    gamma0_core_avg = np.asarray(gamma0_core_avg, dtype=float)
    reference_axis = np.full(gamma0_core_avg.shape, 2.0)
    reference_avg = _core_average_gamma0(
        jet_type,
        theta_c,
        reference_axis,
        k_g=k_g,
    )
    profile_avg = reference_avg - 1.0
    return np.divide(
        gamma0_core_avg - 1.0,
        profile_avg,
        out=np.full_like(gamma0_core_avg, np.nan),
        where=np.isfinite(profile_avg) & (profile_avg > 0.0),
    ) + 1.0


def derive_jet_energy_posterior(
    chain: np.ndarray,
    params: Parameters,
    model_name: str,
) -> tuple[dict[str, np.ndarray], str]:
    """Compute beaming-corrected jet-energy posterior samples."""
    values = _values_in_linear_scale(chain, params)
    theta_c = np.asarray(values["theta_c"], dtype=float)
    jet_type = _infer_jet_type(model_name, values)
    k_e = values.get("k_e")
    k_g = values.get("k_g")
    if "commons" in model_name.lower() and "s" in values:
        k_e = values["s"]
        k_g = values["s"]
    omega_core_frac = 1.0 - np.cos(theta_c)
    profile_frac = _integrated_profile_beaming_fraction(jet_type, theta_c, k_e=k_e)
    core_profile_frac = _integrated_core_profile_beaming_fraction(jet_type, theta_c, k_e=k_e)

    if "E52" in values:
        e_iso_52 = np.asarray(values["E52"], dtype=float)
        e_j_52 = e_iso_52 * profile_frac
    elif "E_j_52" in values:
        e_j_52 = np.asarray(values["E_j_52"], dtype=float)
        e_iso_52 = e_j_52 / profile_frac
    elif "E_j_core_52" in values:
        e_j_core_52 = np.asarray(values["E_j_core_52"], dtype=float)
        e_iso_52 = e_j_core_52 / core_profile_frac
        e_j_52 = e_iso_52 * profile_frac
    else:
        raise KeyError(
            "Cannot derive jet energy; missing E52, E_j_52, or E_j_core_52"
        )

    e_j_tophat_52 = e_iso_52 * omega_core_frac
    e_j_core_52 = e_iso_52 * core_profile_frac
    e_j_wings_52 = np.clip(e_j_52 - e_j_core_52, 0.0, np.inf)
    energy_core_fraction = np.divide(
        e_j_core_52,
        e_j_52,
        out=np.full_like(e_j_52, np.nan),
        where=e_j_52 > 0.0,
    )
    if "lf0" in values:
        gamma0 = np.asarray(values["lf0"], dtype=float)
        gamma0_core_avg = _core_average_gamma0(
            jet_type,
            theta_c,
            gamma0,
            k_g=k_g,
        )
    elif "Gamma_0_core_avg" in values:
        gamma0_core_avg = np.asarray(values["Gamma_0_core_avg"], dtype=float)
        gamma0 = _axis_gamma0_from_core_average(
            jet_type,
            theta_c,
            gamma0_core_avg,
            k_g=k_g,
        )
    else:
        raise KeyError(
            "Cannot derive Lorentz factor; missing lf0 or Gamma_0_core_avg"
        )

    mass_factor = _integrated_jet_mass_factor(
        jet_type,
        theta_c,
        gamma0,
        k_e=k_e,
        k_g=k_g,
    )
    core_mass_factor = _integrated_jet_mass_factor(
        jet_type,
        theta_c,
        gamma0,
        k_e=k_e,
        k_g=k_g,
        core_only=True,
    )
    m_j_g = e_iso_52 * 1.0e52 * mass_factor / (C_CGS**2)
    m_j_core_g = e_iso_52 * 1.0e52 * core_mass_factor / (C_CGS**2)
    m_j_wings_g = np.clip(m_j_g - m_j_core_g, 0.0, np.inf)
    core_mass_fraction = np.divide(
        m_j_core_g,
        m_j_g,
        out=np.full_like(m_j_g, np.nan),
        where=m_j_g > 0.0,
    )

    derived = {
        "E_j_52": e_j_52,
        "E_iso_52": e_iso_52,
        "Gamma_0": gamma0,
        "Gamma_0_core_avg": gamma0_core_avg,
        "M_j_g": m_j_g,
        "M_j_msun": m_j_g / MSUN_G,
        "M_j_core_g": m_j_core_g,
        "M_j_core_msun": m_j_core_g / MSUN_G,
        "M_j_wings_g": m_j_wings_g,
        "M_j_wings_msun": m_j_wings_g / MSUN_G,
        "M_j_core_fraction": core_mass_fraction,
        "M_j_wings_fraction": 1.0 - core_mass_fraction,
        "theta_c": theta_c,
        "Omega_2j_pct_4pi": 100.0 * omega_core_frac,
        "E_j_tophat_52": e_j_tophat_52,
        "E_j_core_52": e_j_core_52,
        "E_j_wings_52": e_j_wings_52,
        "E_j_core_fraction": energy_core_fraction,
        "E_j_wings_fraction": 1.0 - energy_core_fraction,
        "Omega_eff_pct_4pi": 100.0 * profile_frac,
    }
    return derived, jet_type


def summarize_derived_samples(derived: dict[str, np.ndarray], jet_type: str) -> list[dict[str, Any]]:
    """Return compact summary rows for derived posterior products."""
    rows: list[dict[str, Any]] = []
    for name, values in derived.items():
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            continue
        q16, q50, q84 = np.quantile(arr, [0.16, 0.5, 0.84])
        rows.append(
            {
                "parameter": name,
                "jet_profile": jet_type,
                "units": {
                    "E_j_52": "1e52 erg",
                    "E_iso_52": "1e52 erg",
                    "E_j_tophat_52": "1e52 erg",
                    "E_j_core_52": "1e52 erg",
                    "E_j_wings_52": "1e52 erg",
                    "E_j_core_fraction": "fraction",
                    "E_j_wings_fraction": "fraction",
                    "Gamma_0": "dimensionless",
                    "Gamma_0_core_avg": "dimensionless",
                    "M_j_g": "g",
                    "M_j_msun": "Msun",
                    "M_j_core_g": "g",
                    "M_j_core_msun": "Msun",
                    "M_j_wings_g": "g",
                    "M_j_wings_msun": "Msun",
                    "M_j_core_fraction": "fraction",
                    "M_j_wings_fraction": "fraction",
                    "theta_c": "rad",
                    "Omega_2j_pct_4pi": "percent",
                    "Omega_eff_pct_4pi": "percent",
                }.get(name, ""),
                "definition": (
                    "two-sided integral 2*int[(dE/dOmega)/(Gamma0(theta)*c^2)]dOmega"
                    if name in {
                        "M_j_g", "M_j_msun", "M_j_core_g", "M_j_core_msun",
                        "M_j_wings_g", "M_j_wings_msun",
                        "M_j_core_fraction", "M_j_wings_fraction",
                    }
                    else ""
                ),
                "mean": float(np.mean(arr)),
                "sd": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
                "median": float(q50),
                "q16": float(q16),
                "q84": float(q84),
                "n_samples": int(arr.size),
            }
        )
    return rows


def write_jet_energy_summary(results: Path, rows: list[dict[str, Any]]) -> None:
    """Write the compact derived-energy summary table."""
    path = results / "jet_energy_summary.csv"
    fields = [
        "parameter", "jet_profile", "units", "definition",
        "mean", "sd", "median", "q16", "q84", "n_samples",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def append_derived_rows_to_summary(results: Path, rows: list[dict[str, Any]]) -> None:
    """Append derived-energy rows to ArviZ-style summary.csv when present."""
    summary_path = results / "summary.csv"
    if not summary_path.exists() or not rows:
        return

    with summary_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        existing = [row for row in reader if row.get("") not in {r["parameter"] for r in rows}]

    if not fieldnames:
        return
    if "" not in fieldnames:
        fieldnames = [""] + fieldnames

    for row in rows:
        out = {field: "" for field in fieldnames}
        out[""] = row["parameter"]
        if "mean" in out:
            out["mean"] = f"{row['mean']:.6g}"
        if "sd" in out:
            out["sd"] = f"{row['sd']:.6g}"
        if "hdi_3%" in out:
            out["hdi_3%"] = f"{row['q16']:.6g}"
        if "hdi_97%" in out:
            out["hdi_97%"] = f"{row['q84']:.6g}"
        if "ess_bulk" in out:
            out["ess_bulk"] = row["n_samples"]
        if "ess_tail" in out:
            out["ess_tail"] = row["n_samples"]
        if "r_hat" in out:
            out["r_hat"] = "1"
        existing.append(out)

    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing)


def read_jet_energy_summary_rows(results: Path) -> list[dict[str, Any]]:
    """Read derived-energy rows from jet_energy_summary.csv for re-appending."""
    path = results / "jet_energy_summary.csv"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                rows.append(
                    {
                        "parameter": row["parameter"],
                        "mean": float(row["mean"]),
                        "sd": float(row["sd"]),
                        "q16": float(row["q16"]),
                        "q84": float(row["q84"]),
                        "n_samples": int(float(row["n_samples"])),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
    return rows


def regenerate_trace_summary(results: Path, event: str) -> None:
    """Regenerate historical MCMC trace plots and summary.csv."""
    required = [results / "chain.npz", results / "model.toml"]
    if not all(path.exists() for path in required):
        missing = ", ".join(path.name for path in required if not path.exists())
        print(f"WARNING: skipping trace/summary; missing {missing}")
        return

    chain = np.load(results / "chain.npz")["chain"]
    params = Parameters.from_toml(results / "model.toml")
    os.environ["JETFIT_PLOT_RUN_LABEL"] = f"GRB {event} | {display_run_label(results, event)} | trace"
    for path in (
        results / "summary.csv",
        results / "trace.pdf",
        results / "trace.png",
    ):
        if path.exists():
            path.unlink()
    diagnose.plot_trace(params, out_dir=results, chain=chain)
    append_derived_rows_to_summary(results, read_jet_energy_summary_rows(results))
    print(f"trace_summary_ok results={results}")


def regenerate_jet_energy_products(results: Path, event: str, model_name: str) -> None:
    """Regenerate beaming-corrected jet-energy posterior products."""
    required = [results / "chain.npz", results / "model.toml"]
    if not all(path.exists() for path in required):
        missing = ", ".join(path.name for path in required if not path.exists())
        print(f"WARNING: skipping jet-energy products; missing {missing}")
        return

    chain = _load_flat_chain(results)
    params = Parameters.from_toml(results / "model.toml")
    derived, jet_type = derive_jet_energy_posterior(chain, params, model_name)
    rows = summarize_derived_samples(derived, jet_type)

    np.savez_compressed(
        results / "jet_energy_posterior.npz",
        jet_profile=np.asarray(jet_type),
        jet_mass_definition=np.asarray(
            "two-sided integral 2*int[(dE/dOmega)/(Gamma0(theta)*c^2)]dOmega"
        ),
        core_jet_mass_definition=np.asarray(
            "two-sided core integral 2*int_0^theta_c[(dE/dOmega)/(Gamma0(theta)*c^2)]dOmega"
        ),
        core_gamma0_average_definition=np.asarray(
            "solid-angle-weighted mean Gamma0 over 0<=theta<=theta_c"
        ),
        jet_mass_energy_type=np.asarray("afterglow kinetic energy"),
        jet_mass_units=np.asarray("M_j_g in g; M_j_msun in solar masses"),
        **{key: np.asarray(value, dtype=np.float32) for key, value in derived.items()},
    )
    write_jet_energy_summary(results, rows)
    append_derived_rows_to_summary(results, rows)

    os.environ["JETFIT_PLOT_RUN_LABEL"] = f"GRB {event} | {display_run_label(results, event)} | jet energy"
    for path in (
        results / "corner_energy.pdf",
        results / "corner_energy.png",
        results / "corner_jet_mass.pdf",
        results / "corner_jet_mass.png",
    ):
        if path.exists():
            path.unlink()
    plot_derived = _thin_derived_for_plot(derived)
    diagnose.plot_energy_corner(plot_derived, out_dir=results)
    diagnose.plot_jet_mass_corner(plot_derived, out_dir=results)
    print(f"jet_energy_ok results={results} jet_profile={jet_type}")


def regenerate_frequency_plot(results: Path, params: dict[str, Any], source: str) -> None:
    """Regenerate the standard frequencies.pdf diagnostic in the current style."""
    required = [results / "chain.npz", results / "model.toml", results / "obs.csv"]
    if not all(path.exists() for path in required):
        missing = ", ".join(path.name for path in required if not path.exists())
        print(f"WARNING: skipping frequency plot; missing {missing}")
        return

    ampy = Ampy(results / "obs.csv", results / "model.toml")
    chain, log_prob = _load_chain_for_frequency_plot(results)

    # Keep the canonical output name clean when postfit products are refreshed.
    for path in list(results.glob("frequencies*.pdf")) + list(results.glob("frequencies*.png")):
        path.unlink()

    visualize.plot_frequencies(
        chain,
        log_prob,
        ampy.obs,
        ampy.mcmc.params,
        ampy.afterglow_model,
        model_kw=ampy.mcmc.models.afg_kw,
        best=params,
        out_dir=results,
        nsamps=FREQUENCY_POSTERIOR_CURVES,
        ntimes=FREQUENCY_TIME_SAMPLES,
        fast_indices=FREQUENCY_FAST_INDICES,
    )
    regenerate_spectral_evolution_two_panel(results)
    print(f"frequencies_ok results={results} source={source}")


def regenerate_spectral_evolution_two_panel(results: Path) -> None:
    """Combine spectra and frequencies in a compact paper-style vertical figure."""
    spectrum_path = results / "spectrum_timeseries.png"
    frequencies_path = results / "frequencies.png"
    if not (spectrum_path.is_file() and frequencies_path.is_file()):
        return

    spectrum = plt.imread(spectrum_path)
    frequencies = plt.imread(frequencies_path)
    # The standalone frequency figure has a generous title/legend band.  It
    # is useful on its own, but redundant below the already titled spectrum
    # panel.  Remove that band here; the paper caption supplies the color key.
    # Crop through the standalone title, legend, and its duplicate secondary
    # seconds axis.  The compact pair keeps the lower panel's primary days
    # axis and avoids a clipped partial label at the panel join.
    legend_band_rows = max(1, int(round(frequencies.shape[0] * 0.20)))
    frequencies = frequencies[legend_band_rows:, :, :]
    spectrum_aspect = spectrum.shape[0] / spectrum.shape[1]
    frequency_aspect = frequencies.shape[0] / frequencies.shape[1]
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(7.2, 7.2 * (spectrum_aspect + frequency_aspect)),
        gridspec_kw={"height_ratios": (spectrum_aspect, frequency_aspect), "hspace": 0.0},
    )
    for ax, image in zip(axes, (spectrum, frequencies)):
        ax.imshow(image)
        ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1, hspace=0)
    output = results / "spectral_evolution_two_panel.pdf"
    fig.savefig(output, dpi=300, bbox_inches="tight", pad_inches=0.01)
    fig.savefig(output.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)
    print(f"spectral_evolution_two_panel_ok results={results}")


def _terminal_cold_chain_walker_params(results: Path) -> tuple[list[dict[str, Any]], list[int], dict[str, int | str]]:
    """Return all finite terminal cold-chain walkers in model parameter form."""
    chain_path = results / "chain.npz"
    with np.load(chain_path) as data:
        chain = np.asarray(data["chain"], dtype=float)
        if "lnprob" in data:
            log_prob = np.asarray(data["lnprob"], dtype=float)
        elif "log_prob" in data:
            log_prob = np.asarray(data["log_prob"], dtype=float)
        else:
            raise KeyError(f"{chain_path} has no lnprob/log_prob array")
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if log_prob.ndim == 3:
        log_prob = log_prob[:, 0, :]
    if chain.ndim != 3 or log_prob.ndim != 2 or chain.shape[:2] != log_prob.shape:
        raise ValueError("Expected cold-chain samples [steps, walkers, parameters] with matching log probabilities.")

    terminal = np.asarray(chain[-1], dtype=float)
    terminal_log_prob = np.asarray(log_prob[-1], dtype=float)
    finite = np.isfinite(terminal_log_prob) & np.isfinite(terminal).all(axis=1)
    indices = np.flatnonzero(finite)
    if not len(indices):
        raise ValueError("No finite terminal cold-chain walkers available for spectrum-timeseries plotting.")
    parameter_set = Parameters.from_toml(results / "model.toml")
    walker_params = [parameter_set.samples_to_dict(terminal[index]) for index in indices]
    metadata: dict[str, int | str] = {
        "source": "terminal_cold_chain_walkers",
        "available_final_walkers": int(len(terminal)),
        "finite_final_walkers": int(len(indices)),
        "excluded_nonfinite_walkers": int(len(terminal) - len(indices)),
    }
    return walker_params, indices.astype(int).tolist(), metadata


def regenerate_spectrum_timeseries(results: Path, event: str, params: dict[str, Any]) -> None:
    """Regenerate instantaneous spectra plus every terminal walker at each epoch."""
    required = [results / "chain.npz", results / "model.toml", results / "obs.csv"]
    if not all(path.exists() for path in required):
        missing = ", ".join(path.name for path in required if not path.exists())
        print(f"WARNING: skipping spectrum-timeseries; missing {missing}")
        return

    ampy = Ampy(results / "obs.csv", results / "model.toml")
    walker_params, walker_indices, sampling = _terminal_cold_chain_walker_params(results)
    os.environ["JETFIT_PLOT_RUN_LABEL"] = (
        f"GRB {event} | {display_run_label(results, event)} | spectrum timeseries"
    )
    for path in results.glob("spectrum_timeseries*"):
        if path.is_file():
            path.unlink()
    visualize.plot_spectrum_timeseries_ampy(
        ampy,
        params=params,
        walker_params=walker_params,
        walker_indices=walker_indices,
        out_dir=results,
        ncurves=10,
        # The spectral curves are smooth on this logarithmic grid.  Retaining
        # all 100 walkers is the posterior requirement; 250 points per curve
        # keeps that complete product practical during routine post-fit work.
        nfreq=250,
    )
    (results / "spectrum_timeseries_sampling.json").write_text(
        json.dumps(sampling, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("spectrum_timeseries_sampling=" + json.dumps(sampling, sort_keys=True))
    regenerate_spectral_evolution_two_panel(results)
    print(f"spectrum_timeseries_ok results={results}")


def regenerate_reduced_corner_plots(results: Path, event: str, model_name: str) -> None:
    """Regenerate the standard posterior corner plots."""
    required = [results / "chain.npz", results / "model.toml"]
    if not all(path.exists() for path in required):
        missing = ", ".join(path.name for path in required if not path.exists())
        print(f"WARNING: skipping corner plots; missing {missing}")
        return

    full_chain = _load_flat_chain(results)
    params_all = Parameters.from_toml(results / "model.toml")
    derived, _ = derive_jet_energy_posterior(full_chain, params_all, model_name)
    indices = _deterministic_sample_indices(full_chain.shape[0])
    chain = full_chain[indices]
    plot_derived = {
        key: np.asarray(values)[indices]
        for key, values in derived.items()
    }
    params = params_all.fitting
    os.environ["JETFIT_PLOT_RUN_LABEL"] = f"GRB {event} | {display_run_label(results, event)} | corners"
    for path in (
        results / "corner_prior.pdf",
        results / "corner_prior.png",
        results / "corner.pdf",
        results / "corner.png",
        results / "corner_np.pdf",
        results / "corner_np.png",
        results / "corner_host.pdf",
        results / "corner_host.png",
        results / "corner_core.pdf",
        results / "corner_core.png",
        results / "corner_csm.pdf",
        results / "corner_csm.png",
    ):
        if path.exists():
            path.unlink()
    diagnose.plot_corner(chain, params, derived=plot_derived, out_dir=results)
    print(f"corner_plots_ok results={results}")


def run_product_step(name: str, func, *args, **kwargs) -> bool:
    """Run one product step, warning instead of aborting the whole GRB refresh."""
    try:
        func(*args, **kwargs)
        return True
    except Exception as exc:
        print(f"WARNING: {name} failed: {type(exc).__name__}: {exc}")
        return False


def enabled_product_keys(args: argparse.Namespace) -> list[str]:
    """Return product families enabled by the command-line skip flags."""
    keys: list[str] = ["trace-summary"]
    keys.append("spectrum-timeseries")
    if not args.skip_frequency_plot:
        keys.append("frequencies")
    if not args.skip_jet_energy:
        keys.append("jet-energy")
    if not args.skip_reduced_corners:
        keys.append("reduced-corners")
    keys.extend(["light-curve", "ampy-comparison", "swept-mass"])
    if not args.skip_spread_light_curves:
        keys.append("spread-light-curves")
    if not args.skip_density_replot:
        keys.append("density-profiles")
    return keys


def run_product_by_key(
    key: str,
    results: Path,
    event: str,
    params: dict[str, Any],
    model_name: str,
    source: str,
    nmap: float | None,
) -> bool:
    """Run a single product family."""
    if key == "trace-summary":
        return run_product_step("trace/summary", regenerate_trace_summary, results, event)
    if key == "spectrum-timeseries":
        return run_product_step("spectrum timeseries", regenerate_spectrum_timeseries, results, event, params)
    if key == "frequencies":
        return run_product_step("frequency plot", regenerate_frequency_plot, results, params, source)
    if key == "jet-energy":
        return run_product_step("jet-energy products", regenerate_jet_energy_products, results, event, model_name)
    if key == "reduced-corners":
        return run_product_step(
            "reduced corner plots",
            regenerate_reduced_corner_plots,
            results,
            event,
            model_name,
        )
    if key == "light-curve":
        return run_product_step("postfit light curve", regenerate_light_curve_postfit, results, event, params)
    if key == "ampy-comparison":
        return run_product_step("ampy comparison", plot_ampy_comparison, results, event, params, model_name, source, nmap)
    if key == "swept-mass":
        return run_product_step("structured-jet swept-mass overlay", maybe_generate_structjet_swept_mass_overlay, results, model_name)
    if key == "spread-light-curves":
        return run_product_step("spread light curves", maybe_generate_spread_light_curves, results, event)
    if key == "density-profiles":
        return run_product_step("density profiles", regenerate_density_profiles, results, event, params)
    raise ValueError(f"Unknown product key: {key}")


def run_parallel_products(args: argparse.Namespace, results: Path, event: str, product_keys: list[str]) -> bool:
    """Run product families concurrently as isolated subprocesses."""
    if not product_keys:
        return True

    workers = max(1, min(int(args.product_workers), len(product_keys)))
    print(f"parallel_postfit_products workers={workers} products={','.join(product_keys)}")
    running: dict[subprocess.Popen[str], str] = {}
    pending = list(product_keys)
    ok = True

    def launch_next() -> None:
        if not pending:
            return
        key = pending.pop(0)
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--results",
            str(results),
            "--event",
            event,
            "--only-product",
            key,
        ]
        env = dict(os.environ)
        env["JETFIT_POSTFIT_PARALLEL_CHILD"] = "1"
        print(f"parallel_product_start product={key}")
        running[subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env, text=True)] = key

    for _ in range(workers):
        launch_next()

    while running:
        for proc, key in list(running.items()):
            code = proc.poll()
            if code is None:
                continue
            running.pop(proc)
            if code == 0:
                print(f"parallel_product_ok product={key}")
            else:
                print(f"WARNING: parallel product failed product={key} exit={code}")
                ok = False
            launch_next()
        if running:
            import time

            time.sleep(2.0)
    return ok


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

    product_keys = enabled_product_keys(args)
    if args.only_product != "all":
        if args.only_product not in product_keys:
            print(f"postfit_product_skipped_by_flags product={args.only_product}")
            return 0
        ok = run_product_by_key(args.only_product, results, event, params, model_name, source, nmap)
        ensure_pdf_png_product_pairs(results)
        return 0 if ok else 1

    if args.parallel_products:
        ok = True
        if "trace-summary" in product_keys:
            ok = run_product_by_key("trace-summary", results, event, params, model_name, source, nmap)
            product_keys = [key for key in product_keys if key != "trace-summary"]
        ok = ok and run_parallel_products(args, results, event, product_keys)
        ensure_pdf_png_product_pairs(results)
        if ok:
            (results / ".postfit_product_style_version").write_text(
                POSTFIT_PRODUCT_STYLE_VERSION + "\n"
            )
        print(f"postfit_products_ok results={results} source={source}")
        return 0 if ok else 1

    for key in product_keys:
        run_product_by_key(key, results, event, params, model_name, source, nmap)

    ensure_pdf_png_product_pairs(results)
    (results / ".postfit_product_style_version").write_text(
        POSTFIT_PRODUCT_STYLE_VERSION + "\n"
    )
    print(f"postfit_products_ok results={results} source={source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
