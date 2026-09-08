#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib import pyplot as plt
import numpy as np

from jetfit.core.utils import add_collision_aware_grb_label, choose_axes_label_position
from jetfit.mcmc.parameters import Parameters
from jetfit.models.jet_energy import resolve_e_iso52, resolve_gamma0_axis
from jetfit.models.powerlawJetVegasDylanSpectrum import PowerlawJetVegasDylanSpectrumModel


SEC_PER_DAY = 86400.0
MP_G = 1.67262192369e-24
C_CGS = 2.99792458e10
PC_CM = 3.0856775814913673e18
MSUN_G = 1.98847e33


def resolve_structjet_e_iso52(model_params: dict) -> float:
    """Resolve on-axis E_iso,52 from legacy or core-energy fit parameters."""
    return resolve_e_iso52(
        E52=model_params.get("E52"),
        E_j_52=model_params.get("E_j_52"),
        E_j_core_52=model_params.get("E_j_core_52"),
        jet_type="powerlaw",
        theta_c=float(model_params["theta_c"]),
        k_e=model_params.get("k_e"),
    )


def resolve_structjet_gamma0_axis(model_params: dict) -> float:
    """Resolve the on-axis Gamma0 corresponding to this sample's fit coordinates."""
    return resolve_gamma0_axis(
        lf0=model_params.get("lf0"),
        Gamma_0_core_avg=model_params.get("Gamma_0_core_avg"),
        jet_type="powerlaw",
        theta_c=float(model_params["theta_c"]),
        k_g=model_params.get("k_g"),
    )


def retire_legacy_outputs(output_dir: Path, event: str) -> None:
    """Move old long-name swept-mass products out of the product namespace."""
    trash_dir = output_dir / "trash" / "20260604_retired_swept_mass_products"
    patterns = [
        f"{event}_structjet_swept_mass_diagnostics_vs_time.*",
        f"{event}_structjet_swept_mass_diagnostics_vs_radius.*",
        f"{event}_structjet_swept_mass_local_vs_coreavg_per_sr_vs_time.*",
        f"{event}_structjet_swept_mass_local_vs_coreavg_per_sr_vs_radius.*",
        f"{event}_structjet_swept_mass_single_overlay_per_sr_vs_time.*",
        f"{event}_structjet_swept_mass_single_overlay_per_sr_vs_radius.*",
        f"{event}_structjet_swept_mass_single_overlay_two_panel.*",
        f"{event}_structjet_swept_mass_crossings.csv",
    ]

    moved: list[Path] = []
    for pattern in patterns:
        for path in output_dir.glob(pattern):
            if not path.is_file():
                continue
            trash_dir.mkdir(parents=True, exist_ok=True)
            target = trash_dir / path.name
            if target.exists():
                target = trash_dir / f"{path.stem}.retired{path.suffix}"
            shutil.move(str(path), str(target))
            moved.append(target)

    if moved:
        readme = trash_dir / "README.md"
        readme.write_text(
            "# Retired swept-mass product names\n\n"
            "Moved here by `plot_structjet_swept_mass_diagnostics.py` because "
            "the standard product names are now `mass_swept_ejecta_time.*`, "
            "`mass_swept_ejecta_radius.*`, `mass_swept_ejecta_two_panel.*`, "
            "and `mass_swept_ejecta_crossings.csv`.\n"
        )


def compact_event_name(run_dir: Path) -> str:
    """Return the short GRB name for panel labels."""
    label = os.environ.get("JETFIT_PLOT_EVENT_TITLE", "").strip()
    if label:
        if label.upper().startswith("GRB "):
            label = label[4:].strip()
        return label
    name = run_dir.name
    for marker in ("_structjet", "_top_hat", "_powerlaw", "_bubble"):
        if marker in name:
            return name.split(marker, 1)[0]
    return name.split("_", 1)[0]


def read_obs_time_range_days(obs_csv: Path) -> tuple[float, float]:
    with obs_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"No header in {obs_csv}")
        fields = {name.lower(): name for name in reader.fieldnames}
        time_col = next((fields[k] for k in ("time_days", "time", "t_days", "t", "days") if k in fields), reader.fieldnames[0])
        units_col = fields.get("timeunits")
        include_col = fields.get("include")
        vals: list[float] = []
        for row in reader:
            if include_col is not None:
                try:
                    if float(row.get(include_col, "1")) <= 0:
                        continue
                except Exception:
                    pass
            try:
                t = float(row.get(time_col, "nan"))
            except Exception:
                continue
            u = (row.get(units_col, "") if units_col else "").strip().lower()
            if u in {"s", "sec", "secs", "second", "seconds"}:
                t /= SEC_PER_DAY
            elif u in {"ks"}:
                t = t * 1000.0 / SEC_PER_DAY
            elif u in {"h", "hr", "hrs", "hour", "hours"}:
                t /= 24.0
            if np.isfinite(t) and t > 0:
                vals.append(t)
    if not vals:
        raise ValueError(f"No positive times in {obs_csv}")
    return float(min(vals)), float(max(vals))


def theta_cell_solid_angles(theta_centers: np.ndarray) -> np.ndarray:
    theta = np.asarray(theta_centers, dtype=float)
    if theta.ndim != 1 or theta.size < 2:
        raise ValueError("theta_centers must be 1D with >=2 points")
    if not np.all(np.diff(theta) > 0):
        raise ValueError("theta centers are not strictly increasing")
    edges = np.empty(theta.size + 1, dtype=float)
    edges[1:-1] = 0.5 * (theta[:-1] + theta[1:])
    edges[0] = max(0.0, theta[0] - 0.5 * (theta[1] - theta[0]))
    edges[-1] = min(math.pi, theta[-1] + 0.5 * (theta[-1] - theta[-2]))
    edges = np.clip(edges, 0.0, math.pi)
    return 2.0 * math.pi * (np.cos(edges[:-1]) - np.cos(edges[1:]))


def interp_loglog(x_src: np.ndarray, y_src: np.ndarray, x_dst: np.ndarray) -> np.ndarray:
    xs = np.asarray(x_src, dtype=float)
    ys = np.asarray(y_src, dtype=float)
    xd = np.asarray(x_dst, dtype=float)
    m = np.isfinite(xs) & np.isfinite(ys) & (xs > 0) & (ys > 0)
    xs = xs[m]
    ys = ys[m]
    if xs.size < 2:
        return np.full_like(xd, np.nan, dtype=float)
    order = np.argsort(xs)
    xs = xs[order]
    ys = ys[order]
    return np.exp(np.interp(np.log(xd), np.log(xs), np.log(ys), left=np.nan, right=np.nan))


def interp_radius_at_time(t_days: np.ndarray, r_cm: np.ndarray, t_target_days: float) -> float:
    t = np.asarray(t_days, dtype=float)
    r = np.asarray(r_cm, dtype=float)
    m = np.isfinite(t) & np.isfinite(r) & (t > 0) & (r > 0)
    t = t[m]
    r = r[m]
    if t.size < 2:
        return float("nan")
    order = np.argsort(t)
    t = t[order]
    r = r[order]
    if not (t[0] <= t_target_days <= t[-1]):
        return float("nan")
    return float(np.exp(np.interp(np.log(t_target_days), np.log(t), np.log(r))))


def crossing_point_against_curve(
    x: np.ndarray,
    y: np.ndarray,
    target: np.ndarray,
) -> tuple[float, float]:
    """Return first log-interpolated crossing of ``y`` above ``target``."""
    xx = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float)
    tt = np.asarray(target, dtype=float)
    m = np.isfinite(xx) & np.isfinite(yy) & np.isfinite(tt) & (xx > 0) & (yy > 0) & (tt > 0)
    xx = xx[m]
    yy = yy[m]
    tt = tt[m]
    if xx.size < 2:
        return float("nan"), float("nan")

    order = np.argsort(xx)
    xx = xx[order]
    yy = yy[order]
    tt = tt[order]
    delta = np.log(yy) - np.log(tt)
    hit = np.where(delta >= 0.0)[0]
    if hit.size == 0:
        return float("nan"), float("nan")
    idx = int(hit[0])
    if idx == 0:
        # The curve was already above the threshold at the first sampled point.
        # That means the true crossing is before this model/details domain, so
        # plotting the first sampled point would create a fake crossing marker.
        return float("nan"), float("nan")

    x0 = float(xx[idx - 1])
    x1 = float(xx[idx])
    d0 = float(delta[idx - 1])
    d1 = float(delta[idx])
    if not (np.isfinite(d0) and np.isfinite(d1)) or d1 == d0:
        return float(xx[idx]), float(tt[idx])
    frac = float(np.clip(-d0 / (d1 - d0), 0.0, 1.0))
    x_cross = float(np.exp(np.log(x0) + frac * (np.log(x1) - np.log(x0))))
    y_cross = float(np.exp(np.interp(np.log(x_cross), np.log(xx), np.log(tt))))
    return x_cross, y_cross


def crossing_point_against_constant(
    x: np.ndarray,
    y: np.ndarray,
    target: float,
) -> tuple[float, float]:
    """Return first log-interpolated crossing of ``y`` through a constant."""
    if not (np.isfinite(target) and target > 0):
        return float("nan"), float("nan")
    xx = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float)
    m = np.isfinite(xx) & np.isfinite(yy) & (xx > 0) & (yy > 0)
    xx = xx[m]
    yy = yy[m]
    if xx.size < 2:
        return float("nan"), float("nan")

    order = np.argsort(xx)
    xx = xx[order]
    yy = yy[order]
    delta = np.log(yy) - math.log(target)
    crossings = np.where(delta[:-1] * delta[1:] <= 0.0)[0]
    if crossings.size == 0:
        return float("nan"), float("nan")

    idx = int(crossings[0])
    d0 = float(delta[idx])
    d1 = float(delta[idx + 1])
    x0 = float(xx[idx])
    x1 = float(xx[idx + 1])
    if d1 == d0:
        return x0, target
    frac = float(np.clip(-d0 / (d1 - d0), 0.0, 1.0))
    x_cross = float(np.exp(np.log(x0) + frac * (np.log(x1) - np.log(x0))))
    return x_cross, target


def radial_data_range_from_core_tracks(
    t_obs_days: np.ndarray,
    r_cm: np.ndarray,
    core_idx: np.ndarray,
    obs_tmin_days: float,
    obs_tmax_days: float,
) -> tuple[float, float]:
    """Map the observed time span through all core-angle radius tracks."""
    vals: list[float] = []
    for j in core_idx:
        vals.extend(
            [
                interp_radius_at_time(t_obs_days[j], r_cm[j], obs_tmin_days),
                interp_radius_at_time(t_obs_days[j], r_cm[j], obs_tmax_days),
            ]
        )
    vals = [v for v in vals if np.isfinite(v) and v > 0]
    if len(vals) < 2:
        return float("nan"), float("nan")
    return float(np.min(vals)), float(np.max(vals))


def radial_data_range_for_track(
    t_obs_days: np.ndarray,
    r_cm: np.ndarray,
    obs_tmin_days: float,
    obs_tmax_days: float,
) -> tuple[float, float]:
    """Map the observed time span through one angular radius track."""
    vals = [
        interp_radius_at_time(t_obs_days, r_cm, obs_tmin_days),
        interp_radius_at_time(t_obs_days, r_cm, obs_tmax_days),
    ]
    vals = [v for v in vals if np.isfinite(v) and v > 0]
    if len(vals) < 2:
        return float("nan"), float("nan")
    return float(np.min(vals)), float(np.max(vals))


def compute_local_crossings(
    *,
    t_days: np.ndarray,
    r_cm: np.ndarray,
    swept: np.ndarray,
    threshold_1x: np.ndarray,
    threshold_10x: np.ndarray,
    theta_label: str,
    source: str,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for threshold_label, threshold in (
        ("deceleration_m_ej_over_gamma", threshold_1x),
        ("bm_onset_10m_ej_over_gamma", threshold_10x),
    ):
        t_cross, m_t = crossing_point_against_curve(t_days, swept, threshold)
        r_cross, m_r = crossing_point_against_curve(r_cm, swept, threshold)
        rows.append(
            {
                "source": source,
                "theta": theta_label,
                "threshold": threshold_label,
                "t_obs_days": t_cross,
                "radius_cm": r_cross,
                "mass_time_g_per_sr": m_t,
                "mass_radius_g_per_sr": m_r,
            }
        )
    return rows


def load_final_walker_model_params(run_dir: Path) -> list[dict[str, float]]:
    """Return final cold-chain model params for each walker, if a chain exists."""
    chain_path = run_dir / "chain.npz"
    model_path = run_dir / "model.toml"
    if not chain_path.exists() or not model_path.exists():
        return []

    params = Parameters.from_toml(model_path)
    with np.load(chain_path) as data:
        chain = np.asarray(data["chain"], dtype=float)
    if chain.ndim == 4:
        # Parallel-tempered shape: step, temp, walker, dim. Use cold temp.
        final = chain[-1, 0, :, :]
    elif chain.ndim == 3:
        # Cold-chain shape: step, walker, dim.
        final = chain[-1, :, :]
    else:
        return []

    out: list[dict[str, float]] = []
    for theta in final:
        if not np.all(np.isfinite(theta)):
            continue
        try:
            payload = params.samples_to_dict(theta, cat="model", scale="linear")
            model_params = payload.get("model", {})
        except Exception:
            continue
        if model_params:
            out.append({k: float(v) for k, v in model_params.items()})
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Plot structured-jet swept-mass diagnostics for one run.")
    p.add_argument("--run-dir", type=Path, required=True)
    args = p.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    output_dir = run_dir
    event = compact_event_name(run_dir)

    min_json = run_dir / "minimized" / "minimized.json"
    best_json = run_dir / "best_fit.json"
    if min_json.exists():
        payload = json.loads(min_json.read_text())
        params = payload.get("params", payload)
    elif best_json.exists():
        params = json.loads(best_json.read_text())
    else:
        raise FileNotFoundError(f"No minimized/best_fit json in {run_dir}")
    model_params = params["model"]

    model = PowerlawJetVegasDylanSpectrumModel(**model_params)
    obs_tmin_days, obs_tmax_days = read_obs_time_range_days(run_dir / "obs.csv")
    details = model.vegas_model.details(float(max(obs_tmin_days / 30.0, 1e-8) * SEC_PER_DAY), float(max(obs_tmax_days * 30.0, obs_tmin_days) * SEC_PER_DAY))

    # Native arrays for forward shock.
    theta_grid = np.asarray(details.fwd.theta, dtype=float)[0, :, 0]
    t_obs_days = np.asarray(details.fwd.t_obs, dtype=float)[0, :, :] / SEC_PER_DAY
    r_cm = np.asarray(details.fwd.r, dtype=float)[0, :, :]
    gamma = np.asarray(details.fwd.Gamma, dtype=float)[0, :, :]
    n_p = np.asarray(details.fwd.N_p, dtype=float)[0, :, :]

    m_sw_per_sr = MP_G * n_p
    e_iso = resolve_structjet_e_iso52(model_params) * 1.0e52
    gamma0_core = resolve_structjet_gamma0_axis(model_params)
    theta_c = float(model_params["theta_c"])
    k_e = float(model_params["k_e"])
    k_g = float(model_params["k_g"])

    # dE/dOmega(theta) for VegasAfterglow PowerLawJet:
    # eps_k(theta) = (E_iso/4pi) / (1 + (theta/theta_c)^k_e)
    dE_dOmega = (e_iso / (4.0 * math.pi)) / (1.0 + np.power(theta_grid / max(theta_c, 1e-12), k_e))
    # Structured-jet local ejecta mass per solid angle must use Gamma0(theta),
    # not a single core Gamma0 value.
    gamma0_theta = (gamma0_core - 1.0) / (1.0 + np.power(theta_grid / max(theta_c, 1e-12), k_g)) + 1.0
    dMej_dOmega = dE_dOmega / (gamma0_theta * (C_CGS**2))

    thresh1_local = dMej_dOmega[:, None] / np.clip(gamma, 1e-12, np.inf)
    thresh10_local = 10.0 * thresh1_local

    idx_axis = int(np.argmin(np.abs(theta_grid - 0.0)))
    idx_core = int(np.argmin(np.abs(theta_grid - theta_c)))

    dOmega = theta_cell_solid_angles(theta_grid)
    core_mask = theta_grid <= theta_c + 1e-15
    core_idx = np.where(core_mask)[0]
    omega_core = float(np.sum(dOmega[core_idx]))

    # Time-domain core-integrated diagnostics with 1/Gamma inside the integral.
    tmin_common = float(np.max(t_obs_days[core_idx, 0]))
    tmax_common = float(np.min(t_obs_days[core_idx, -1]))
    t_common = np.geomspace(max(tmin_common, 1e-10), max(tmax_common, tmin_common * 1.01), 220)
    msw_core_t = np.zeros_like(t_common)
    thr1_core_t = np.zeros_like(t_common)
    for j in core_idx:
        msw_j = interp_loglog(t_obs_days[j], m_sw_per_sr[j], t_common)
        thr1_j = interp_loglog(t_obs_days[j], thresh1_local[j], t_common)
        msw_core_t += np.nan_to_num(msw_j, nan=0.0) * dOmega[j]
        thr1_core_t += np.nan_to_num(thr1_j, nan=0.0) * dOmega[j]
    thr10_core_t = 10.0 * thr1_core_t
    msw_core_t_avg = msw_core_t / omega_core
    thr1_core_t_avg = thr1_core_t / omega_core
    thr10_core_t_avg = thr10_core_t / omega_core

    # Radius-domain core-integrated diagnostics.
    rmin_common = float(np.max(r_cm[core_idx, 0]))
    rmax_common = float(np.min(r_cm[core_idx, -1]))
    r_common = np.geomspace(max(rmin_common, 1.0), max(rmax_common, rmin_common * 1.01), 220)
    msw_core_r = np.zeros_like(r_common)
    thr1_core_r = np.zeros_like(r_common)
    for j in core_idx:
        msw_j = interp_loglog(r_cm[j], m_sw_per_sr[j], r_common)
        thr1_j = interp_loglog(r_cm[j], thresh1_local[j], r_common)
        msw_core_r += np.nan_to_num(msw_j, nan=0.0) * dOmega[j]
        thr1_core_r += np.nan_to_num(thr1_j, nan=0.0) * dOmega[j]
    thr10_core_r = 10.0 * thr1_core_r
    msw_core_r_avg = msw_core_r / omega_core
    thr1_core_r_avg = thr1_core_r / omega_core
    thr10_core_r_avg = thr10_core_r / omega_core

    # ---- Plot vs observer time ----
    fig_t, axes_t = plt.subplots(3, 1, figsize=(9.5, 11.0), sharex=False)
    for ax in axes_t:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(False)
        ax.axvspan(obs_tmin_days, obs_tmax_days, color="0.6", alpha=0.17, lw=0, label="Data time range")
        secax = ax.secondary_xaxis("top", functions=(lambda d: d * SEC_PER_DAY, lambda s: s / SEC_PER_DAY))
        secax.set_xlabel("Observer time [s]", labelpad=4)
        secax.tick_params(axis="x", labelsize=8)

    axes_t[0].plot(t_obs_days[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, label=r"$dM_{\rm swept}/d\Omega$ @ $\theta=0$")
    axes_t[0].plot(t_obs_days[idx_axis], thresh1_local[idx_axis], lw=1.6, ls=":", label=r"$(dM_{\rm ej}/d\Omega)/\Gamma(\theta,t)$")
    axes_t[0].plot(t_obs_days[idx_axis], thresh10_local[idx_axis], lw=1.6, ls="--", label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma(\theta,t)$")
    axes_t[0].set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    axes_t[0].set_title(r"On-axis local diagnostic ($\theta=0$)")
    axes_t[0].legend(fontsize=8, loc="best")

    axes_t[1].plot(t_obs_days[idx_core], m_sw_per_sr[idx_core], lw=2.0, label=rf"$dM_{{\rm swept}}/d\Omega$ @ $\theta=\theta_c\approx{theta_grid[idx_core]:.3g}$")
    axes_t[1].plot(t_obs_days[idx_core], thresh1_local[idx_core], lw=1.6, ls=":", label=r"$(dM_{\rm ej}/d\Omega)/\Gamma(\theta,t)$")
    axes_t[1].plot(t_obs_days[idx_core], thresh10_local[idx_core], lw=1.6, ls="--", label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma(\theta,t)$")
    axes_t[1].set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    axes_t[1].set_title(r"Core-edge local diagnostic ($\theta=\theta_c$)")
    axes_t[1].legend(fontsize=8, loc="best")

    axes_t[2].plot(t_common, msw_core_t, lw=2.0, label=r"$M_{{\rm swept,core}}=\int_0^{\theta_c}(dM_{\rm swept}/d\Omega)d\Omega$")
    axes_t[2].plot(t_common, thr1_core_t, lw=1.6, ls=":", label=r"$\int_0^{\theta_c}[(dM_{\rm ej}/d\Omega)/\Gamma(\theta,t)]d\Omega$")
    axes_t[2].plot(t_common, thr10_core_t, lw=1.6, ls="--", label=r"$10\times$ core threshold")
    axes_t[2].set_ylabel("Core-integrated mass [g]")
    axes_t[2].set_title(r"Core-integrated diagnostic ($0\leq\theta\leq\theta_c$)")
    axes_t[2].set_xlabel("Observer time [days]")
    axes_t[2].legend(fontsize=8, loc="best")

    fig_t.suptitle(
        f"{event} | Structured-jet swept-mass diagnostics vs observer time\n"
        "Two local per-solid-angle diagnostics plus one core-integrated diagnostic",
        y=0.995,
        fontsize=11,
    )
    fig_t.tight_layout(rect=(0, 0, 1, 0.97))

    # ---- Plot vs radius ----
    fig_r, axes_r = plt.subplots(3, 1, figsize=(9.5, 11.0), sharex=False)
    for ax in axes_r:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(False)
        secax = ax.secondary_xaxis("top", functions=(lambda cm: cm / PC_CM, lambda pc: pc * PC_CM))
        secax.set_xlabel("Radius [pc]", labelpad=4)
        secax.tick_params(axis="x", labelsize=8)

    axes_r[0].plot(r_cm[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, label=r"$dM_{\rm swept}/d\Omega$ @ $\theta=0$")
    axes_r[0].plot(r_cm[idx_axis], thresh1_local[idx_axis], lw=1.6, ls=":", label=r"$(dM_{\rm ej}/d\Omega)/\Gamma(\theta,r)$")
    axes_r[0].plot(r_cm[idx_axis], thresh10_local[idx_axis], lw=1.6, ls="--", label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma(\theta,r)$")
    axes_r[0].set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    axes_r[0].set_title(r"On-axis local diagnostic ($\theta=0$)")
    axes_r[0].legend(fontsize=8, loc="best")

    axes_r[1].plot(r_cm[idx_core], m_sw_per_sr[idx_core], lw=2.0, label=rf"$dM_{{\rm swept}}/d\Omega$ @ $\theta=\theta_c\approx{theta_grid[idx_core]:.3g}$")
    axes_r[1].plot(r_cm[idx_core], thresh1_local[idx_core], lw=1.6, ls=":", label=r"$(dM_{\rm ej}/d\Omega)/\Gamma(\theta,r)$")
    axes_r[1].plot(r_cm[idx_core], thresh10_local[idx_core], lw=1.6, ls="--", label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma(\theta,r)$")
    axes_r[1].set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    axes_r[1].set_title(r"Core-edge local diagnostic ($\theta=\theta_c$)")
    axes_r[1].legend(fontsize=8, loc="best")

    axes_r[2].plot(r_common, msw_core_r, lw=2.0, label=r"$M_{{\rm swept,core}}(r)$")
    axes_r[2].plot(r_common, thr1_core_r, lw=1.6, ls=":", label=r"$\int_0^{\theta_c}[(dM_{\rm ej}/d\Omega)/\Gamma(\theta,r)]d\Omega$")
    axes_r[2].plot(r_common, thr10_core_r, lw=1.6, ls="--", label=r"$10\times$ core threshold")
    axes_r[2].set_ylabel("Core-integrated mass [g]")
    axes_r[2].set_title(r"Core-integrated diagnostic ($0\leq\theta\leq\theta_c$)")
    axes_r[2].set_xlabel("Radius [cm]")
    axes_r[2].legend(fontsize=8, loc="best")

    fig_r.suptitle(
        f"{event} | Structured-jet swept-mass diagnostics vs radius\n"
        "Two local per-solid-angle diagnostics plus one core-integrated diagnostic",
        y=0.995,
        fontsize=11,
    )
    fig_r.tight_layout(rect=(0, 0, 1, 0.97))

    # ---- Combined apples-to-apples (per-solid-angle) comparison ----
    fig_ct, axes_ct = plt.subplots(3, 1, figsize=(9.5, 11.0), sharex=True)
    for ax in axes_ct:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(False)
        ax.axvspan(obs_tmin_days, obs_tmax_days, color="0.6", alpha=0.17, lw=0, label="Data time range")
        secax = ax.secondary_xaxis("top", functions=(lambda d: d * SEC_PER_DAY, lambda s: s / SEC_PER_DAY))
        secax.set_xlabel("Observer time [s]", labelpad=4)
        secax.tick_params(axis="x", labelsize=8)

    axes_ct[0].plot(t_obs_days[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, label=r"$\theta=0$")
    axes_ct[0].plot(t_obs_days[idx_core], m_sw_per_sr[idx_core], lw=2.0, label=r"$\theta=\theta_c$")
    axes_ct[0].plot(t_common, msw_core_t_avg, lw=2.0, label=r"core-avg $(\int dM_{\rm sw}/d\Omega\,d\Omega)/\Omega_c$")
    axes_ct[0].set_ylabel(r"$dM_{\rm sw}/d\Omega$ [g sr$^{-1}$]")
    axes_ct[0].legend(fontsize=8, loc="best")

    axes_ct[1].plot(t_obs_days[idx_axis], thresh1_local[idx_axis], lw=2.0, label=r"$\theta=0$")
    axes_ct[1].plot(t_obs_days[idx_core], thresh1_local[idx_core], lw=2.0, label=r"$\theta=\theta_c$")
    axes_ct[1].plot(t_common, thr1_core_t_avg, lw=2.0, label=r"core-avg $(\int (dM_{\rm ej}/d\Omega)/\Gamma\,d\Omega)/\Omega_c$")
    axes_ct[1].set_ylabel(r"$(dM_{\rm ej}/d\Omega)/\Gamma$ [g sr$^{-1}$]")
    axes_ct[1].legend(fontsize=8, loc="best")

    axes_ct[2].plot(t_obs_days[idx_axis], thresh10_local[idx_axis], lw=2.0, label=r"$\theta=0$")
    axes_ct[2].plot(t_obs_days[idx_core], thresh10_local[idx_core], lw=2.0, label=r"$\theta=\theta_c$")
    axes_ct[2].plot(t_common, thr10_core_t_avg, lw=2.0, label=r"core-avg $10\times[(\int (dM_{\rm ej}/d\Omega)/\Gamma\,d\Omega)/\Omega_c]$")
    axes_ct[2].set_ylabel(r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ [g sr$^{-1}$]")
    axes_ct[2].set_xlabel("Observer time [days]")
    axes_ct[2].legend(fontsize=8, loc="best")

    fig_ct.suptitle(
        f"{event} | Per-solid-angle comparison: local vs core-averaged (time)\n"
        r"Core-avg uses $\Omega_c=\int_0^{\theta_c} d\Omega$",
        y=0.995,
        fontsize=11,
    )
    fig_ct.tight_layout(rect=(0, 0, 1, 0.97))

    fig_cr, axes_cr = plt.subplots(3, 1, figsize=(9.5, 11.0), sharex=True)
    for ax in axes_cr:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(False)
        secax = ax.secondary_xaxis("top", functions=(lambda cm: cm / PC_CM, lambda pc: pc * PC_CM))
        secax.set_xlabel("Radius [pc]", labelpad=4)
        secax.tick_params(axis="x", labelsize=8)

    axes_cr[0].plot(r_cm[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, label=r"$\theta=0$")
    axes_cr[0].plot(r_cm[idx_core], m_sw_per_sr[idx_core], lw=2.0, label=r"$\theta=\theta_c$")
    axes_cr[0].plot(r_common, msw_core_r_avg, lw=2.0, label=r"core-avg $(\int dM_{\rm sw}/d\Omega\,d\Omega)/\Omega_c$")
    axes_cr[0].set_ylabel(r"$dM_{\rm sw}/d\Omega$ [g sr$^{-1}$]")
    axes_cr[0].legend(fontsize=8, loc="best")

    axes_cr[1].plot(r_cm[idx_axis], thresh1_local[idx_axis], lw=2.0, label=r"$\theta=0$")
    axes_cr[1].plot(r_cm[idx_core], thresh1_local[idx_core], lw=2.0, label=r"$\theta=\theta_c$")
    axes_cr[1].plot(r_common, thr1_core_r_avg, lw=2.0, label=r"core-avg $(\int (dM_{\rm ej}/d\Omega)/\Gamma\,d\Omega)/\Omega_c$")
    axes_cr[1].set_ylabel(r"$(dM_{\rm ej}/d\Omega)/\Gamma$ [g sr$^{-1}$]")
    axes_cr[1].legend(fontsize=8, loc="best")

    axes_cr[2].plot(r_cm[idx_axis], thresh10_local[idx_axis], lw=2.0, label=r"$\theta=0$")
    axes_cr[2].plot(r_cm[idx_core], thresh10_local[idx_core], lw=2.0, label=r"$\theta=\theta_c$")
    axes_cr[2].plot(r_common, thr10_core_r_avg, lw=2.0, label=r"core-avg $10\times[(\int (dM_{\rm ej}/d\Omega)/\Gamma\,d\Omega)/\Omega_c]$")
    axes_cr[2].set_ylabel(r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ [g sr$^{-1}$]")
    axes_cr[2].set_xlabel("Radius [cm]")
    axes_cr[2].legend(fontsize=8, loc="best")

    fig_cr.suptitle(
        f"{event} | Per-solid-angle comparison: local vs core-averaged (radius)\n"
        r"Core-avg uses $\Omega_c=\int_0^{\theta_c} d\Omega$",
        y=0.995,
        fontsize=11,
    )
    fig_cr.tight_layout(rect=(0, 0, 1, 0.97))

    best_crossings: list[dict[str, float | str]] = []
    best_crossings.extend(
        compute_local_crossings(
            t_days=t_obs_days[idx_axis],
            r_cm=r_cm[idx_axis],
            swept=m_sw_per_sr[idx_axis],
            threshold_1x=thresh1_local[idx_axis],
            threshold_10x=thresh10_local[idx_axis],
            theta_label="theta=0",
            source="best",
        )
    )
    best_crossings.extend(
        compute_local_crossings(
            t_days=t_obs_days[idx_core],
            r_cm=r_cm[idx_core],
            swept=m_sw_per_sr[idx_core],
            threshold_1x=thresh1_local[idx_core],
            threshold_10x=thresh10_local[idx_core],
            theta_label="theta=theta_c",
            source="best",
        )
    )

    def gamma_reference_values(sample_params: dict[str, float]) -> tuple[float, float, float]:
        sample_theta_c = float(sample_params.get("theta_c", float("nan")))
        sample_theta_v = float(sample_params.get("theta_v", 0.0))
        gamma_ref = 1.0 / sample_theta_c if sample_theta_c > 0 else float("nan")
        gamma_low = 1.0 / (sample_theta_c + sample_theta_v) if sample_theta_c + sample_theta_v > 0 else float("nan")
        gamma_high = 1.0 / (sample_theta_c - sample_theta_v) if sample_theta_c - sample_theta_v > 0 else float("nan")
        return gamma_ref, gamma_low, gamma_high

    def gamma_crossing_rows_for_track(
        *,
        source: str,
        theta_label: str,
        t_days: np.ndarray,
        r_cm: np.ndarray,
        gamma_track: np.ndarray,
        gamma_ref: float,
        theta_c_value: float,
        theta_v_value: float,
        gamma_low: float,
        gamma_high: float,
    ) -> list[dict[str, float | str]]:
        t_cross, gamma_t = crossing_point_against_constant(t_days, gamma_track, gamma_ref)
        r_cross, gamma_r = crossing_point_against_constant(r_cm, gamma_track, gamma_ref)
        return [
            {
                "source": source,
                "theta": theta_label,
                "threshold": "gamma_equals_one_over_theta_c",
                "t_obs_days": t_cross,
                "radius_cm": r_cross,
                "gamma_time": gamma_t,
                "gamma_radius": gamma_r,
                "theta_c": theta_c_value,
                "theta_v": theta_v_value,
                "gamma_ref_one_over_theta_c": gamma_ref,
                "gamma_lower_one_over_theta_c_plus_theta_v": gamma_low,
                "gamma_upper_one_over_theta_c_minus_theta_v": gamma_high,
            }
        ]

    gamma_ref_best, gamma_low_best, gamma_high_best = gamma_reference_values(model_params)
    theta_v = float(model_params.get("theta_v", 0.0))
    best_gamma_crossings: list[dict[str, float | str]] = []
    best_gamma_crossings.extend(
        gamma_crossing_rows_for_track(
            source="best",
            theta_label="theta=0",
            t_days=t_obs_days[idx_axis],
            r_cm=r_cm[idx_axis],
            gamma_track=gamma[idx_axis],
            gamma_ref=gamma_ref_best,
            theta_c_value=theta_c,
            theta_v_value=theta_v,
            gamma_low=gamma_low_best,
            gamma_high=gamma_high_best,
        )
    )
    best_gamma_crossings.extend(
        gamma_crossing_rows_for_track(
            source="best",
            theta_label="theta=theta_c",
            t_days=t_obs_days[idx_core],
            r_cm=r_cm[idx_core],
            gamma_track=gamma[idx_core],
            gamma_ref=gamma_ref_best,
            theta_c_value=theta_c,
            theta_v_value=theta_v,
            gamma_low=gamma_low_best,
            gamma_high=gamma_high_best,
        )
    )

    walker_gamma_tracks: list[dict[str, object]] = []
    walker_gamma_crossings: list[dict[str, float | str]] = []

    def walker_crossings_for_params(sample_params: dict[str, float], source: str) -> list[dict[str, float | str]]:
        try:
            sample_model = PowerlawJetVegasDylanSpectrumModel(**sample_params)
            sample_details = sample_model.vegas_model.details(
                float(max(obs_tmin_days / 30.0, 1e-8) * SEC_PER_DAY),
                float(max(obs_tmax_days * 30.0, obs_tmin_days) * SEC_PER_DAY),
            )
            sample_theta = np.asarray(sample_details.fwd.theta, dtype=float)[0, :, 0]
            sample_t = np.asarray(sample_details.fwd.t_obs, dtype=float)[0, :, :] / SEC_PER_DAY
            sample_r = np.asarray(sample_details.fwd.r, dtype=float)[0, :, :]
            sample_gamma = np.asarray(sample_details.fwd.Gamma, dtype=float)[0, :, :]
            sample_np = np.asarray(sample_details.fwd.N_p, dtype=float)[0, :, :]
            sample_msw = MP_G * sample_np
            sample_e_iso = resolve_structjet_e_iso52(sample_params) * 1.0e52
            sample_gamma0_core = resolve_structjet_gamma0_axis(sample_params)
            sample_theta_c = float(sample_params["theta_c"])
            sample_k_e = float(sample_params["k_e"])
            sample_k_g = float(sample_params["k_g"])
            sample_dE_dOmega = (sample_e_iso / (4.0 * math.pi)) / (
                1.0 + np.power(sample_theta / max(sample_theta_c, 1e-12), sample_k_e)
            )
            sample_gamma0_theta = (sample_gamma0_core - 1.0) / (
                1.0 + np.power(sample_theta / max(sample_theta_c, 1e-12), sample_k_g)
            ) + 1.0
            sample_dMej_dOmega = sample_dE_dOmega / (sample_gamma0_theta * (C_CGS**2))
            sample_thr1 = sample_dMej_dOmega[:, None] / np.clip(sample_gamma, 1e-12, np.inf)
            sample_thr10 = 10.0 * sample_thr1
            sample_idx_axis = int(np.argmin(np.abs(sample_theta - 0.0)))
            # Use this posterior sample's own core angle for red/core-edge
            # walker curves and crossing clouds, not the minimized/best theta_c.
            sample_idx_core = int(np.argmin(np.abs(sample_theta - sample_theta_c)))
            sample_theta_v = float(sample_params.get("theta_v", 0.0))
            sample_gamma_ref, sample_gamma_low, sample_gamma_high = gamma_reference_values(sample_params)

            walker_gamma_tracks.append(
                {
                    "source": source,
                    "theta_c": sample_theta_c,
                    "theta_v": sample_theta_v,
                    "gamma_ref": sample_gamma_ref,
                    "gamma_low": sample_gamma_low,
                    "gamma_high": sample_gamma_high,
                    "t_axis": sample_t[sample_idx_axis],
                    "r_axis": sample_r[sample_idx_axis],
                    "gamma_axis": sample_gamma[sample_idx_axis],
                    "t_core": sample_t[sample_idx_core],
                    "r_core": sample_r[sample_idx_core],
                    "gamma_core": sample_gamma[sample_idx_core],
                }
            )
            walker_gamma_crossings.extend(
                gamma_crossing_rows_for_track(
                    source=source,
                    theta_label="theta=0",
                    t_days=sample_t[sample_idx_axis],
                    r_cm=sample_r[sample_idx_axis],
                    gamma_track=sample_gamma[sample_idx_axis],
                    gamma_ref=sample_gamma_ref,
                    theta_c_value=sample_theta_c,
                    theta_v_value=sample_theta_v,
                    gamma_low=sample_gamma_low,
                    gamma_high=sample_gamma_high,
                )
            )
            walker_gamma_crossings.extend(
                gamma_crossing_rows_for_track(
                    source=source,
                    theta_label="theta=theta_c",
                    t_days=sample_t[sample_idx_core],
                    r_cm=sample_r[sample_idx_core],
                    gamma_track=sample_gamma[sample_idx_core],
                    gamma_ref=sample_gamma_ref,
                    theta_c_value=sample_theta_c,
                    theta_v_value=sample_theta_v,
                    gamma_low=sample_gamma_low,
                    gamma_high=sample_gamma_high,
                )
            )

            rows: list[dict[str, float | str]] = []
            rows.extend(
                compute_local_crossings(
                    t_days=sample_t[sample_idx_axis],
                    r_cm=sample_r[sample_idx_axis],
                    swept=sample_msw[sample_idx_axis],
                    threshold_1x=sample_thr1[sample_idx_axis],
                    threshold_10x=sample_thr10[sample_idx_axis],
                    theta_label="theta=0",
                    source=source,
                )
            )
            rows.extend(
                compute_local_crossings(
                    t_days=sample_t[sample_idx_core],
                    r_cm=sample_r[sample_idx_core],
                    swept=sample_msw[sample_idx_core],
                    threshold_1x=sample_thr1[sample_idx_core],
                    threshold_10x=sample_thr10[sample_idx_core],
                    theta_label="theta=theta_c",
                    source=source,
                )
            )
            return rows
        except Exception:
            return []

    walker_crossings: list[dict[str, float | str]] = []
    for i, sample_params in enumerate(load_final_walker_model_params(run_dir)):
        walker_crossings.extend(walker_crossings_for_params(sample_params, f"walker_{i:03d}"))

    r_axis_lo, r_axis_hi = radial_data_range_for_track(
        t_obs_days[idx_axis],
        r_cm[idx_axis],
        obs_tmin_days,
        obs_tmax_days,
    )
    r_core_lo, r_core_hi = radial_data_range_for_track(
        t_obs_days[idx_core],
        r_cm[idx_core],
        obs_tmin_days,
        obs_tmax_days,
    )

    def _finite_positive_domain(*values: np.ndarray) -> tuple[float, float]:
        vals: list[np.ndarray] = []
        for value in values:
            arr = np.asarray(value, dtype=float)
            vals.append(arr[np.isfinite(arr) & (arr > 0)])
        if not vals:
            return float("nan"), float("nan")
        merged = np.concatenate([arr.ravel() for arr in vals if arr.size])
        if merged.size == 0:
            return float("nan"), float("nan")
        return float(np.min(merged)), float(np.max(merged))

    def _domain_has_value(domain: tuple[float, float], value: float) -> bool:
        lo, hi = domain
        return np.isfinite(value) and value > 0 and np.isfinite(lo) and np.isfinite(hi) and lo <= value <= hi

    def _mask_near_zero_display_artifacts(values: np.ndarray) -> np.ndarray:
        """Break log-plot lines at numerical zero/underflow artifacts only.

        The raw arrays and crossing calculations above remain unchanged.  This
        display-only mask removes abrupt zero-like tails that otherwise force a
        logarithmic panel to span many irrelevant decades.
        """
        result = np.asarray(values, dtype=float).copy()
        positive = np.where(np.isfinite(result) & (result > 0.0), result, np.nan)
        if result.ndim <= 1:
            reference = np.nanmax(positive) if np.any(np.isfinite(positive)) else np.nan
            floor = reference * 1.0e-12 if np.isfinite(reference) else np.nan
        else:
            reference = np.nanmax(positive, axis=-1, keepdims=True)
            floor = reference * 1.0e-12
        invalid = ~np.isfinite(result) | (result <= 0.0)
        if np.any(np.isfinite(floor)):
            invalid |= result <= floor
        result[invalid] = np.nan
        return result

    def _set_data_window_ylim(ax, x_window: tuple[float, float]) -> None:
        """Favor the scientifically observed domain while retaining real drops."""
        xmin, xmax = x_window
        if not (np.isfinite(xmin) and np.isfinite(xmax) and xmax > xmin > 0.0):
            return
        samples: list[np.ndarray] = []
        for line in ax.get_lines():
            xdata = np.asarray(line.get_xdata(), dtype=float)
            ydata = np.asarray(line.get_ydata(), dtype=float)
            valid = np.isfinite(xdata) & np.isfinite(ydata) & (xdata > 0.0) & (ydata > 0.0)
            valid &= (xdata >= xmin) & (xdata <= xmax)
            if np.any(valid):
                samples.append(ydata[valid])
        if not samples:
            return
        values = np.concatenate(samples)
        lo, hi = np.quantile(values, (0.01, 0.99))
        if not (np.isfinite(lo) and np.isfinite(hi) and hi > 0.0):
            return
        lo = max(lo, hi * 1.0e-12)
        if hi <= lo:
            return
        ax.set_ylim(lo / 2.0, hi * 2.0)

    # Apply only after scientific crossings have been computed.  The plotted
    # arrays may omit numerical underflow tails; the saved diagnostics retain
    # the unmodified model values used above.
    m_sw_per_sr = _mask_near_zero_display_artifacts(m_sw_per_sr)
    thresh1_local = _mask_near_zero_display_artifacts(thresh1_local)
    thresh10_local = _mask_near_zero_display_artifacts(thresh10_local)
    gamma = _mask_near_zero_display_artifacts(gamma)
    for track in walker_gamma_tracks:
        track["gamma_axis"] = _mask_near_zero_display_artifacts(np.asarray(track["gamma_axis"], dtype=float))
        track["gamma_core"] = _mask_near_zero_display_artifacts(np.asarray(track["gamma_core"], dtype=float))

    # Marker domains are based on the best-fit curves shown in each panel.
    # Best-fit crossings outside these domains are unbracketed by the visible
    # curves and should not be plotted; walker crossings are also filtered so
    # outliers do not pull the axes away from the scientifically relevant range.
    time_marker_domain = _finite_positive_domain(t_obs_days[idx_axis], t_obs_days[idx_core])
    radius_marker_domain = _finite_positive_domain(r_cm[idx_axis], r_cm[idx_core])

    def _valid_crossing_rows(
        rows: list[dict[str, float | str]],
        theta_label: str,
        threshold_label: str,
        *,
        x_key: str | None = None,
        x_domain: tuple[float, float] | None = None,
    ) -> list[dict[str, float | str]]:
        filtered: list[dict[str, float | str]] = []
        for row in rows:
            if row["theta"] != theta_label or row["threshold"] != threshold_label:
                continue
            if not (
                np.isfinite(float(row["t_obs_days"]))
                and float(row["t_obs_days"]) > 0
                and np.isfinite(float(row["radius_cm"]))
                and float(row["radius_cm"]) > 0
            ):
                continue
            if x_key is not None and x_domain is not None and not _domain_has_value(x_domain, float(row[x_key])):
                continue
            filtered.append(row)
        return filtered

    def scatter_crossings(
        ax,
        rows: list[dict[str, float | str]],
        *,
        x_key: str,
        y_key: str,
        theta_label: str,
        threshold_label: str,
        color: str,
        marker: str,
        alpha: float,
        size: float,
        edgecolor: str | None = None,
        zorder: float = 2.0,
        label: str | None = None,
        x_domain: tuple[float, float] | None = None,
    ):
        sub = _valid_crossing_rows(rows, theta_label, threshold_label, x_key=x_key, x_domain=x_domain)
        if not sub:
            return None
        return ax.scatter(
            [float(row[x_key]) for row in sub],
            [float(row[y_key]) for row in sub],
            s=size,
            marker=marker,
            color=color,
            alpha=alpha,
            edgecolors=edgecolor if edgecolor is not None else "none",
            linewidths=0.6 if edgecolor is not None else 0.0,
            zorder=zorder,
            label=label,
        )

    def add_walker_crossing_cloud(
        ax,
        *,
        x_key: str,
        y_key: str,
        axis_light: str,
        core_light: str,
        x_domain: tuple[float, float],
    ) -> None:
        # Marker semantics: circle = M_ej/Gamma crossing; square = 10 M_ej/Gamma crossing.
        scatter_crossings(
            ax,
            walker_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=theta_c",
            threshold_label="deceleration_m_ej_over_gamma",
            color=core_light,
            marker="o",
            alpha=0.50,
            size=24,
            zorder=1.1,
            x_domain=x_domain,
        )
        scatter_crossings(
            ax,
            walker_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=theta_c",
            threshold_label="bm_onset_10m_ej_over_gamma",
            color=core_light,
            marker="s",
            alpha=0.50,
            size=24,
            zorder=1.1,
            x_domain=x_domain,
        )
        scatter_crossings(
            ax,
            walker_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=0",
            threshold_label="deceleration_m_ej_over_gamma",
            color=axis_light,
            marker="o",
            alpha=0.50,
            size=24,
            zorder=1.4,
            x_domain=x_domain,
        )
        scatter_crossings(
            ax,
            walker_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=0",
            threshold_label="bm_onset_10m_ej_over_gamma",
            color=axis_light,
            marker="s",
            alpha=0.50,
            size=24,
            zorder=1.4,
            x_domain=x_domain,
        )

    def add_best_crossings(
        ax,
        *,
        x_key: str,
        y_key: str,
        axis_color: str,
        core_color: str,
        x_domain: tuple[float, float],
    ):
        h_core_dec = scatter_crossings(
            ax,
            best_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=theta_c",
            threshold_label="deceleration_m_ej_over_gamma",
            color=core_color,
            marker="o",
            alpha=1.0,
            size=72,
            edgecolor="black",
            zorder=6,
            x_domain=x_domain,
        )
        h_core_bm = scatter_crossings(
            ax,
            best_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=theta_c",
            threshold_label="bm_onset_10m_ej_over_gamma",
            color=core_color,
            marker="s",
            alpha=1.0,
            size=72,
            edgecolor="black",
            zorder=6,
            x_domain=x_domain,
        )
        h_axis_dec = scatter_crossings(
            ax,
            best_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=0",
            threshold_label="deceleration_m_ej_over_gamma",
            color=axis_color,
            marker="o",
            alpha=1.0,
            size=72,
            edgecolor="black",
            zorder=7,
            x_domain=x_domain,
        )
        h_axis_bm = scatter_crossings(
            ax,
            best_crossings,
            x_key=x_key,
            y_key=y_key,
            theta_label="theta=0",
            threshold_label="bm_onset_10m_ej_over_gamma",
            color=axis_color,
            marker="s",
            alpha=1.0,
            size=72,
            edgecolor="black",
            zorder=7,
            x_domain=x_domain,
        )
        return [h for h in (h_axis_dec, h_axis_bm, h_core_dec, h_core_bm) if h is not None]

    def add_radial_data_spans(ax):
        """Draw separate angular radial ranges with a neutral overlap span."""
        intervals: dict[str, tuple[float, float]] = {}
        if np.isfinite(r_core_lo) and np.isfinite(r_core_hi) and r_core_hi > r_core_lo:
            intervals["core"] = (r_core_lo, r_core_hi)
        if np.isfinite(r_axis_lo) and np.isfinite(r_axis_hi) and r_axis_hi > r_axis_lo:
            intervals["axis"] = (r_axis_lo, r_axis_hi)

        def span(lo: float, hi: float, color: str, alpha: float, zorder: float) -> None:
            if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                ax.axvspan(lo, hi, color=color, alpha=alpha, lw=0, zorder=zorder)

        if "core" in intervals and "axis" in intervals:
            core_lo, core_hi = intervals["core"]
            axis_lo, axis_hi = intervals["axis"]
            overlap_lo = max(core_lo, axis_lo)
            overlap_hi = min(core_hi, axis_hi)

            # Non-overlap portions retain their angular tint.
            span(core_lo, min(core_hi, overlap_lo), cc, 0.12, 0.10)
            span(max(core_lo, overlap_hi), core_hi, cc, 0.12, 0.10)
            span(axis_lo, min(axis_hi, overlap_lo), c0, 0.12, 0.20)
            span(max(axis_lo, overlap_hi), axis_hi, c0, 0.12, 0.20)

            # The shared portion represents where both angular mappings agree.
            span(overlap_lo, overlap_hi, "0.6", 0.17, 0.30)
            return

        if "core" in intervals:
            span(*intervals["core"], cc, 0.12, 0.10)
        if "axis" in intervals:
            span(*intervals["axis"], c0, 0.12, 0.20)

    def add_clean_overlay_legend(ax, *, radial_range: bool) -> None:
        handles = [
            Line2D([0], [0], color=c0, lw=2.2, ls="-", label=r"$\theta=0$: $dM_{\rm sw}/d\Omega$"),
            Line2D([0], [0], color=c0, lw=1.9, ls=":", label=r"$\theta=0$: $(dM_{\rm ej}/d\Omega)/\Gamma$"),
            Line2D([0], [0], color=c0, lw=1.9, ls="--", label=r"$\theta=0$: $10(dM_{\rm ej}/d\Omega)/\Gamma$"),
            Line2D([0], [0], color=cc, lw=2.2, ls="-", label=r"$\theta=\theta_c$: $dM_{\rm sw}/d\Omega$"),
            Line2D([0], [0], color=cc, lw=1.9, ls=":", label=r"$\theta=\theta_c$: $(dM_{\rm ej}/d\Omega)/\Gamma$"),
            Line2D([0], [0], color=cc, lw=1.9, ls="--", label=r"$\theta=\theta_c$: $10(dM_{\rm ej}/d\Omega)/\Gamma$"),
            Line2D([0], [0], marker="o", color="black", markerfacecolor="white", lw=0, ms=7, label="decel crossing"),
            Line2D([0], [0], marker="s", color="black", markerfacecolor="white", lw=0, ms=7, label="BM-onset crossing"),
        ]
        handles.append(
            Patch(
                facecolor="0.6",
                edgecolor="none",
                alpha=0.17,
                label="Data time range" if not radial_range else "Mapped data-range overlap",
            )
        )
        ax.legend(
            handles=handles,
            fontsize=7.4,
            ncol=3,
            loc="lower right",
            frameon=True,
            framealpha=0.93,
            fancybox=False,
            borderpad=0.45,
            handlelength=2.2,
            handletextpad=0.55,
            columnspacing=0.95,
        )

    def save_tight(fig, path: Path, *, dpi: int | None = None) -> None:
        fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.045)

    def add_grb_label(ax) -> None:
        add_collision_aware_grb_label(
            ax,
            f"GRB {event}",
            corner="upper left",
            candidates=[(0.035, 0.875), (0.035, 0.79), (0.035, 0.705), (0.095, 0.875)],
            fontsize=15,
            zorder=20,
        )

    def add_grb_label_upper_right(ax) -> None:
        add_collision_aware_grb_label(
            ax,
            f"GRB {event}",
            corner="upper right",
            candidates=[(0.965, 0.875), (0.965, 0.79), (0.965, 0.705), (0.905, 0.875)],
            fontsize=15,
            zorder=20,
        )

    def add_grb_label_gamma(ax) -> tuple[float, float]:
        label = f"GRB {event}"
        try:
            xmin, xmax = ax.get_xlim()
            if xmin > 0 and xmax > xmin:
                x_mid = math.sqrt(xmin * xmax)
            else:
                x_mid = 0.5 * (xmin + xmax)
            y_pref = ax.transAxes.inverted().transform(ax.transData.transform((x_mid, 1.0e2)))[1]
            y_pref = float(np.clip(y_pref, 0.30, 0.82))
        except Exception:
            y_pref = 0.62

        candidates = [
            (0.045, y_pref),
            (0.045, min(y_pref + 0.085, 0.86)),
            (0.045, max(y_pref - 0.085, 0.30)),
            (0.045, min(y_pref + 0.17, 0.86)),
            (0.105, y_pref),
        ]
        x, y = choose_axes_label_position(ax, label, candidates, ha="left", va="center", fontsize=15)
        ax.text(
            x,
            y,
            label,
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=15,
            fontweight="semibold",
            zorder=20,
        )
        return x, y

    # ---- True single-axis overlays (all comparable curves on one plot) ----
    fig_ot, ax_ot = plt.subplots(figsize=(10.0, 6.8))
    ax_ot.set_xscale("log")
    ax_ot.set_yscale("log")
    ax_ot.grid(False)
    h_data_t = ax_ot.axvspan(obs_tmin_days, obs_tmax_days, color="0.6", alpha=0.17, lw=0, label="Data time range")
    secax_t = ax_ot.secondary_xaxis("top", functions=(lambda d: d * SEC_PER_DAY, lambda s: s / SEC_PER_DAY))
    secax_t.set_xlabel("Observer time [s]", labelpad=4)
    secax_t.tick_params(axis="x", labelsize=8)
    right_t = ax_ot.secondary_yaxis("right", functions=(lambda g: g / MSUN_G, lambda ms: ms * MSUN_G))
    right_t.set_ylabel(r"Mass per solid angle [$M_\odot$ sr$^{-1}$]")

    # Color mapping requested 2026-06-01: swap the previous red/blue assignment.
    c0 = "tab:blue"
    cc = "tab:red"
    c0_light = "lightskyblue"
    cc_light = "lightpink"

    add_walker_crossing_cloud(
        ax_ot,
        x_key="t_obs_days",
        y_key="mass_time_g_per_sr",
        axis_light=c0_light,
        core_light=cc_light,
        x_domain=time_marker_domain,
    )

    ax_ot.plot(t_obs_days[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, zorder=3, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")
    ax_ot.plot(t_obs_days[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, zorder=4, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")

    ax_ot.plot(t_obs_days[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, zorder=3, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_ot.plot(t_obs_days[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, zorder=4, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")

    ax_ot.plot(t_obs_days[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, zorder=3, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_ot.plot(t_obs_days[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, zorder=4, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    ax_ot.set_xlabel("Observer time [days]")
    ax_ot.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    add_grb_label(ax_ot)
    add_best_crossings(
        ax_ot,
        x_key="t_obs_days",
        y_key="mass_time_g_per_sr",
        axis_color=c0,
        core_color=cc,
        x_domain=time_marker_domain,
    )
    add_clean_overlay_legend(ax_ot, radial_range=False)
    fig_ot.tight_layout()

    fig_or, ax_or = plt.subplots(figsize=(10.0, 6.8))
    ax_or.set_xscale("log")
    ax_or.set_yscale("log")
    ax_or.grid(False)
    secax_r = ax_or.secondary_xaxis("top", functions=(lambda cm: cm / PC_CM, lambda pc: pc * PC_CM))
    secax_r.set_xlabel("Radius [pc]", labelpad=4)
    secax_r.tick_params(axis="x", labelsize=8)
    right_r = ax_or.secondary_yaxis("right", functions=(lambda g: g / MSUN_G, lambda ms: ms * MSUN_G))
    right_r.set_ylabel(r"Mass per solid angle [$M_\odot$ sr$^{-1}$]")

    # Map the observed time window through each angular track shown. Non-overlap
    # spans keep their angular tint; the shared portion is neutral grey.
    add_radial_data_spans(ax_or)

    add_walker_crossing_cloud(
        ax_or,
        x_key="radius_cm",
        y_key="mass_radius_g_per_sr",
        axis_light=c0_light,
        core_light=cc_light,
        x_domain=radius_marker_domain,
    )

    ax_or.plot(r_cm[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, zorder=3, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")
    ax_or.plot(r_cm[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, zorder=4, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")

    ax_or.plot(r_cm[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, zorder=3, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_or.plot(r_cm[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, zorder=4, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")

    ax_or.plot(r_cm[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, zorder=3, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_or.plot(r_cm[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, zorder=4, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    ax_or.set_xlabel("Radius [cm]")
    ax_or.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    add_grb_label(ax_or)
    add_best_crossings(
        ax_or,
        x_key="radius_cm",
        y_key="mass_radius_g_per_sr",
        axis_color=c0,
        core_color=cc,
        x_domain=radius_marker_domain,
    )
    add_clean_overlay_legend(ax_or, radial_range=True)
    fig_or.tight_layout()

    # ---- Two-panel combined figure: time (top), radius (bottom) ----
    fig_combo, (ax_ctop, ax_cbot) = plt.subplots(2, 1, figsize=(10.0, 11.5), sharex=False)
    for ax in (ax_ctop, ax_cbot):
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(False)

    # Top panel (time)
    h_ct_data = ax_ctop.axvspan(obs_tmin_days, obs_tmax_days, color="0.6", alpha=0.17, lw=0, label="Data time range")
    secax_ct = ax_ctop.secondary_xaxis("top", functions=(lambda d: d * SEC_PER_DAY, lambda s: s / SEC_PER_DAY))
    secax_ct.set_xlabel("Observer time [s]", labelpad=4)
    secax_ct.tick_params(axis="x", labelsize=8)
    right_ct = ax_ctop.secondary_yaxis("right", functions=(lambda g: g / MSUN_G, lambda ms: ms * MSUN_G))
    right_ct.set_ylabel(r"Mass per solid angle [$M_\odot$ sr$^{-1}$]")

    add_walker_crossing_cloud(
        ax_ctop,
        x_key="t_obs_days",
        y_key="mass_time_g_per_sr",
        axis_light=c0_light,
        core_light=cc_light,
        x_domain=time_marker_domain,
    )

    ax_ctop.plot(t_obs_days[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, zorder=3, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")
    ax_ctop.plot(t_obs_days[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, zorder=4, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")
    ax_ctop.plot(t_obs_days[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, zorder=3, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_ctop.plot(t_obs_days[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, zorder=4, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    ax_ctop.plot(t_obs_days[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, zorder=3, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_ctop.plot(t_obs_days[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, zorder=4, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    ax_ctop.set_xlabel("Observer time [days]")
    ax_ctop.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    add_grb_label(ax_ctop)
    add_best_crossings(
        ax_ctop,
        x_key="t_obs_days",
        y_key="mass_time_g_per_sr",
        axis_color=c0,
        core_color=cc,
        x_domain=time_marker_domain,
    )
    _set_data_window_ylim(ax_ctop, (obs_tmin_days, obs_tmax_days))
    add_clean_overlay_legend(ax_ctop, radial_range=False)

    # Bottom panel (radius)
    secax_cr = ax_cbot.secondary_xaxis("top", functions=(lambda cm: cm / PC_CM, lambda pc: pc * PC_CM))
    secax_cr.set_xlabel("Radius [pc]", labelpad=4)
    secax_cr.tick_params(axis="x", labelsize=8)
    right_cr = ax_cbot.secondary_yaxis("right", functions=(lambda g: g / MSUN_G, lambda ms: ms * MSUN_G))
    right_cr.set_ylabel(r"Mass per solid angle [$M_\odot$ sr$^{-1}$]")

    add_radial_data_spans(ax_cbot)

    add_walker_crossing_cloud(
        ax_cbot,
        x_key="radius_cm",
        y_key="mass_radius_g_per_sr",
        axis_light=c0_light,
        core_light=cc_light,
        x_domain=radius_marker_domain,
    )

    ax_cbot.plot(r_cm[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, zorder=3, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")
    ax_cbot.plot(r_cm[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, zorder=4, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")
    ax_cbot.plot(r_cm[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, zorder=3, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_cbot.plot(r_cm[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, zorder=4, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    ax_cbot.plot(r_cm[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, zorder=3, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_cbot.plot(r_cm[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, zorder=4, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    ax_cbot.set_xlabel("Radius [cm]")
    ax_cbot.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    add_grb_label(ax_cbot)
    add_best_crossings(
        ax_cbot,
        x_key="radius_cm",
        y_key="mass_radius_g_per_sr",
        axis_color=c0,
        core_color=cc,
        x_domain=radius_marker_domain,
    )
    radial_window = (
        min(value for value in (r_axis_lo, r_core_lo) if np.isfinite(value) and value > 0.0),
        max(value for value in (r_axis_hi, r_core_hi) if np.isfinite(value) and value > 0.0),
    ) if any(np.isfinite(value) and value > 0.0 for value in (r_axis_lo, r_core_lo)) and any(np.isfinite(value) and value > 0.0 for value in (r_axis_hi, r_core_hi)) else (float("nan"), float("nan"))
    _set_data_window_ylim(ax_cbot, radial_window)
    add_clean_overlay_legend(ax_cbot, radial_range=True)

    fig_combo.tight_layout()

    def _valid_gamma_crossing_rows(
        rows: list[dict[str, float | str]],
        theta_label: str,
        *,
        x_key: str,
        x_domain: tuple[float, float],
    ) -> list[dict[str, float | str]]:
        filtered: list[dict[str, float | str]] = []
        y_key = "gamma_time" if x_key == "t_obs_days" else "gamma_radius"
        for row in rows:
            if row["theta"] != theta_label:
                continue
            x_val = float(row[x_key])
            y_val = float(row[y_key])
            if not (np.isfinite(x_val) and x_val > 0 and np.isfinite(y_val) and y_val > 0):
                continue
            if not _domain_has_value(x_domain, x_val):
                continue
            filtered.append(row)
        return filtered

    def add_gamma_crossings(
        ax,
        rows: list[dict[str, float | str]],
        *,
        x_key: str,
        x_domain: tuple[float, float],
        alpha: float,
        size: float,
        edgecolor: str | None,
        zorder: float,
    ) -> None:
        y_key = "gamma_time" if x_key == "t_obs_days" else "gamma_radius"
        for theta_label, color, marker in (
            ("theta=theta_c", cc, "s"),
            ("theta=0", c0, "o"),
        ):
            sub = _valid_gamma_crossing_rows(rows, theta_label, x_key=x_key, x_domain=x_domain)
            if not sub:
                continue
            ax.scatter(
                [float(row[x_key]) for row in sub],
                [float(row[y_key]) for row in sub],
                s=size,
                marker=marker,
                color=color,
                alpha=alpha,
                edgecolors=edgecolor if edgecolor is not None else "none",
                linewidths=0.6 if edgecolor is not None else 0.0,
                zorder=zorder + (0.2 if theta_label == "theta=0" else 0.0),
            )

    def add_gamma_reference(ax) -> None:
        for track in walker_gamma_tracks:
            gamma_ref = float(track.get("gamma_ref", float("nan")))
            if np.isfinite(gamma_ref) and gamma_ref > 0:
                ax.axhline(gamma_ref, color="0.30", lw=0.55, ls="-", alpha=0.12, zorder=0.65)
        if np.isfinite(gamma_ref_best) and gamma_ref_best > 0:
            ax.axhline(gamma_ref_best, color="black", lw=1.25, ls="-", alpha=0.62, zorder=0.9)

    def add_gamma_legend(ax, *, radial_range: bool, anchor: tuple[float, float] = (0.045, 0.59)) -> None:
        handles = [
            Line2D([0], [0], color=c0, lw=2.0, label=r"$\theta=0$: $\Gamma$"),
            Line2D([0], [0], color=cc, lw=2.0, label=r"$\theta=\theta_c$: $\Gamma$"),
            Line2D([0], [0], color="black", lw=1.25, ls="-", alpha=0.75, label=r"$\Gamma=1/\theta_c$"),
            Line2D([0], [0], marker="o", color="black", markerfacecolor="white", lw=0, ms=7, label=r"$\theta=0$ crossing"),
            Line2D([0], [0], marker="s", color="black", markerfacecolor="white", lw=0, ms=7, label=r"$\theta=\theta_c$ crossing"),
            Patch(
                facecolor="0.6",
                edgecolor="none",
                alpha=0.17,
                label="Data time range" if not radial_range else "Mapped data-range overlap",
            ),
        ]
        ax.legend(
            handles=handles,
            fontsize=7.4,
            ncol=2,
            loc="upper left",
            bbox_to_anchor=anchor,
            frameon=True,
            framealpha=0.93,
            fancybox=False,
            borderpad=0.45,
            handlelength=2.2,
            handletextpad=0.55,
            columnspacing=0.95,
        )

    gamma_time_domain = _finite_positive_domain(
        t_obs_days[idx_axis],
        t_obs_days[idx_core],
        *[np.asarray(track["t_axis"], dtype=float) for track in walker_gamma_tracks],
        *[np.asarray(track["t_core"], dtype=float) for track in walker_gamma_tracks],
    )
    gamma_radius_domain = _finite_positive_domain(
        r_cm[idx_axis],
        r_cm[idx_core],
        *[np.asarray(track["r_axis"], dtype=float) for track in walker_gamma_tracks],
        *[np.asarray(track["r_core"], dtype=float) for track in walker_gamma_tracks],
    )

    # ---- Lorentz-factor jet-break diagnostic: time (top), radius (bottom) ----
    fig_gamma, (ax_gtop, ax_gbot) = plt.subplots(2, 1, figsize=(10.0, 11.5), sharex=False)
    for ax in (ax_gtop, ax_gbot):
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(False)
        ax.tick_params(axis="y", which="both", right=True, labelright=False)
        add_gamma_reference(ax)

    ax_gtop.axvspan(obs_tmin_days, obs_tmax_days, color="0.6", alpha=0.17, lw=0, zorder=0.1)
    secax_gt = ax_gtop.secondary_xaxis("top", functions=(lambda d: d * SEC_PER_DAY, lambda s: s / SEC_PER_DAY))
    secax_gt.set_xlabel("Observer time [s]", labelpad=4)
    secax_gt.tick_params(axis="x", labelsize=8)

    add_radial_data_spans(ax_gbot)
    secax_gr = ax_gbot.secondary_xaxis("top", functions=(lambda cm: cm / PC_CM, lambda pc: pc * PC_CM))
    secax_gr.set_xlabel("Radius [pc]", labelpad=4)
    secax_gr.tick_params(axis="x", labelsize=8)

    for track in walker_gamma_tracks:
        ax_gtop.plot(track["t_core"], track["gamma_core"], lw=0.85, color=cc, alpha=0.10, zorder=1.2)
        ax_gbot.plot(track["r_core"], track["gamma_core"], lw=0.85, color=cc, alpha=0.10, zorder=1.2)
        ax_gtop.plot(track["t_axis"], track["gamma_axis"], lw=0.85, color=c0, alpha=0.13, zorder=1.4)
        ax_gbot.plot(track["r_axis"], track["gamma_axis"], lw=0.85, color=c0, alpha=0.13, zorder=1.4)

    add_gamma_crossings(
        ax_gtop,
        walker_gamma_crossings,
        x_key="t_obs_days",
        x_domain=gamma_time_domain,
        alpha=0.22,
        size=22,
        edgecolor=None,
        zorder=1.6,
    )
    add_gamma_crossings(
        ax_gbot,
        walker_gamma_crossings,
        x_key="radius_cm",
        x_domain=gamma_radius_domain,
        alpha=0.22,
        size=22,
        edgecolor=None,
        zorder=1.6,
    )

    ax_gtop.plot(t_obs_days[idx_core], gamma[idx_core], lw=2.0, color=cc, zorder=3.0)
    ax_gbot.plot(r_cm[idx_core], gamma[idx_core], lw=2.0, color=cc, zorder=3.0)
    ax_gtop.plot(t_obs_days[idx_axis], gamma[idx_axis], lw=2.0, color=c0, zorder=3.4)
    ax_gbot.plot(r_cm[idx_axis], gamma[idx_axis], lw=2.0, color=c0, zorder=3.4)

    add_gamma_crossings(
        ax_gtop,
        best_gamma_crossings,
        x_key="t_obs_days",
        x_domain=gamma_time_domain,
        alpha=1.0,
        size=72,
        edgecolor="black",
        zorder=5.0,
    )
    add_gamma_crossings(
        ax_gbot,
        best_gamma_crossings,
        x_key="radius_cm",
        x_domain=gamma_radius_domain,
        alpha=1.0,
        size=72,
        edgecolor="black",
        zorder=5.0,
    )

    ax_gtop.set_xlabel("Observer time [days]")
    ax_gtop.set_ylabel(r"Lorentz factor $\Gamma$")
    ax_gbot.set_xlabel("Radius [cm]")
    ax_gbot.set_ylabel(r"Lorentz factor $\Gamma$")
    if np.isfinite(gamma_time_domain[0]) and np.isfinite(gamma_time_domain[1]) and gamma_time_domain[1] > gamma_time_domain[0]:
        ax_gtop.set_xlim(gamma_time_domain)
    if np.isfinite(gamma_radius_domain[0]) and np.isfinite(gamma_radius_domain[1]) and gamma_radius_domain[1] > gamma_radius_domain[0]:
        ax_gbot.set_xlim(gamma_radius_domain)
    _set_data_window_ylim(ax_gtop, (obs_tmin_days, obs_tmax_days))
    _set_data_window_ylim(ax_gbot, radial_window)
    gamma_label_anchor = add_grb_label_gamma(ax_gtop)
    gamma_legend_anchor = (gamma_label_anchor[0], max(gamma_label_anchor[1] - 0.075, 0.12))
    add_gamma_legend(ax_gtop, radial_range=False, anchor=gamma_legend_anchor)
    fig_gamma.tight_layout()

    out_ot_pdf = output_dir / "mass_swept_ejecta_time.pdf"
    out_ot_png = output_dir / "mass_swept_ejecta_time.png"
    out_or_pdf = output_dir / "mass_swept_ejecta_radius.pdf"
    out_or_png = output_dir / "mass_swept_ejecta_radius.png"
    out_combo_pdf = output_dir / "mass_swept_ejecta_two_panel.pdf"
    out_combo_png = output_dir / "mass_swept_ejecta_two_panel.png"
    out_crossings_csv = output_dir / "mass_swept_ejecta_crossings.csv"
    out_gamma_pdf = output_dir / "gamma_jetbreak_two_panel.pdf"
    out_gamma_png = output_dir / "gamma_jetbreak_two_panel.png"
    out_gamma_crossings_csv = output_dir / "gamma_jetbreak_crossings.csv"

    retire_legacy_outputs(output_dir, event)

    crossing_rows = best_crossings + walker_crossings
    with out_crossings_csv.open("w", newline="") as handle:
        fieldnames = [
            "source",
            "theta",
            "threshold",
            "t_obs_days",
            "radius_cm",
            "mass_time_g_per_sr",
            "mass_radius_g_per_sr",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in crossing_rows:
            writer.writerow(row)

    gamma_crossing_rows = best_gamma_crossings + walker_gamma_crossings
    with out_gamma_crossings_csv.open("w", newline="") as handle:
        fieldnames = [
            "source",
            "theta",
            "threshold",
            "t_obs_days",
            "radius_cm",
            "gamma_time",
            "gamma_radius",
            "theta_c",
            "theta_v",
            "gamma_ref_one_over_theta_c",
            "gamma_lower_one_over_theta_c_plus_theta_v",
            "gamma_upper_one_over_theta_c_minus_theta_v",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in gamma_crossing_rows:
            writer.writerow(row)

    save_tight(fig_ot, out_ot_pdf)
    save_tight(fig_ot, out_ot_png, dpi=220)
    save_tight(fig_or, out_or_pdf)
    save_tight(fig_or, out_or_png, dpi=220)
    save_tight(fig_combo, out_combo_pdf)
    save_tight(fig_combo, out_combo_png, dpi=220)
    save_tight(fig_gamma, out_gamma_pdf)
    save_tight(fig_gamma, out_gamma_png, dpi=220)
    plt.close(fig_t)
    plt.close(fig_r)
    plt.close(fig_ct)
    plt.close(fig_cr)
    plt.close(fig_ot)
    plt.close(fig_or)
    plt.close(fig_combo)
    plt.close(fig_gamma)

    print(f"Wrote: {out_ot_pdf}")
    print(f"Wrote: {out_or_pdf}")
    print(f"Wrote: {out_combo_pdf}")
    print(f"Wrote: {out_crossings_csv}")
    print(f"Wrote: {out_gamma_pdf}")
    print(f"Wrote: {out_gamma_crossings_csv}")


if __name__ == "__main__":
    main()
