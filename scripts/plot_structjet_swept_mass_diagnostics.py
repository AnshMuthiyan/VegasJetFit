#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np

from jetfit.models.powerlawJetVegasDylanSpectrum import PowerlawJetVegasDylanSpectrumModel


SEC_PER_DAY = 86400.0
MP_G = 1.67262192369e-24
C_CGS = 2.99792458e10
PC_CM = 3.0856775814913673e18
MSUN_G = 1.98847e33


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


def main() -> None:
    p = argparse.ArgumentParser(description="Plot structured-jet swept-mass diagnostics for one run.")
    p.add_argument("--run-dir", type=Path, required=True)
    args = p.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    campaign_dir = run_dir.parent
    event = run_dir.name

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
    e_iso = float(model_params["E52"]) * 1.0e52
    gamma0_core = float(model_params["lf0"])
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

    # Color mapping: red -> theta=0, blue -> theta=theta_c
    c0 = "tab:red"
    cc = "tab:blue"

    h_red_sw, = ax_ot.plot(t_obs_days[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")
    h_blue_sw, = ax_ot.plot(t_obs_days[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")

    h_red_th1, = ax_ot.plot(t_obs_days[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_blue_th1, = ax_ot.plot(t_obs_days[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")

    h_red_th10, = ax_ot.plot(t_obs_days[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_blue_th10, = ax_ot.plot(t_obs_days[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_ot.set_xlabel("Observer time [days]")
    ax_ot.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    ax_ot.set_title(f"{event} | Single-plot overlay (time): local diagnostics only")
    # Matplotlib fills legends down columns first. Force left column to be all-red + data.
    handles_t = [h_red_sw, h_red_th1, h_red_th10, h_data_t, h_blue_sw, h_blue_th1, h_blue_th10]
    labels_t = [h.get_label() for h in handles_t]
    ax_ot.legend(handles_t, labels_t, fontsize=8, ncol=2, loc="best")
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

    # Approximate radial data range from observed time window mapped through local radius tracks.
    r_candidates = [
        interp_radius_at_time(t_obs_days[idx_axis], r_cm[idx_axis], obs_tmin_days),
        interp_radius_at_time(t_obs_days[idx_axis], r_cm[idx_axis], obs_tmax_days),
        interp_radius_at_time(t_obs_days[idx_core], r_cm[idx_core], obs_tmin_days),
        interp_radius_at_time(t_obs_days[idx_core], r_cm[idx_core], obs_tmax_days),
    ]
    r_candidates = [x for x in r_candidates if np.isfinite(x) and x > 0]
    if len(r_candidates) >= 2:
        r_lo = float(np.min(r_candidates))
        r_hi = float(np.max(r_candidates))
        if r_hi > r_lo:
            h_data_r = ax_or.axvspan(r_lo, r_hi, color="0.6", alpha=0.17, lw=0, label="Approx. data radial range")
    else:
        h_data_r = None

    h_red_sw_r, = ax_or.plot(r_cm[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")
    h_blue_sw_r, = ax_or.plot(r_cm[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")

    h_red_th1_r, = ax_or.plot(r_cm[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_blue_th1_r, = ax_or.plot(r_cm[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")

    h_red_th10_r, = ax_or.plot(r_cm[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_blue_th10_r, = ax_or.plot(r_cm[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_or.set_xlabel("Radius [cm]")
    ax_or.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    ax_or.set_title(f"{event} | Single-plot overlay (radius): local diagnostics only")
    handles_r = [h_red_sw_r, h_red_th1_r, h_red_th10_r]
    if h_data_r is not None:
        handles_r.append(h_data_r)
    else:
        # preserve 4-left / 3-right layout if radial data span is unavailable
        h_dummy, = ax_or.plot([], [], alpha=0.0, label="")
        handles_r.append(h_dummy)
    handles_r.extend([h_blue_sw_r, h_blue_th1_r, h_blue_th10_r])
    labels_r = [h.get_label() for h in handles_r]
    ax_or.legend(handles_r, labels_r, fontsize=8, ncol=2, loc="best")
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

    h_ct_red_sw, = ax_ctop.plot(t_obs_days[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")
    h_ct_blue_sw, = ax_ctop.plot(t_obs_days[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")
    h_ct_red_th1, = ax_ctop.plot(t_obs_days[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_ct_blue_th1, = ax_ctop.plot(t_obs_days[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    h_ct_red_th10, = ax_ctop.plot(t_obs_days[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_ct_blue_th10, = ax_ctop.plot(t_obs_days[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_ctop.set_xlabel("Observer time [days]")
    ax_ctop.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")
    handles_ct = [h_ct_red_sw, h_ct_red_th1, h_ct_red_th10, h_ct_data, h_ct_blue_sw, h_ct_blue_th1, h_ct_blue_th10]
    labels_ct = [h.get_label() for h in handles_ct]
    ax_ctop.legend(handles_ct, labels_ct, fontsize=8, ncol=2, loc="best")

    # Bottom panel (radius)
    secax_cr = ax_cbot.secondary_xaxis("top", functions=(lambda cm: cm / PC_CM, lambda pc: pc * PC_CM))
    secax_cr.set_xlabel("Radius [pc]", labelpad=4)
    secax_cr.tick_params(axis="x", labelsize=8)
    right_cr = ax_cbot.secondary_yaxis("right", functions=(lambda g: g / MSUN_G, lambda ms: ms * MSUN_G))
    right_cr.set_ylabel(r"Mass per solid angle [$M_\odot$ sr$^{-1}$]")

    h_cr_data = None
    if len(r_candidates) >= 2:
        r_lo = float(np.min(r_candidates))
        r_hi = float(np.max(r_candidates))
        if r_hi > r_lo:
            h_cr_data = ax_cbot.axvspan(r_lo, r_hi, color="0.6", alpha=0.17, lw=0, label="Approx. data radial range")

    h_cr_red_sw, = ax_cbot.plot(r_cm[idx_axis], m_sw_per_sr[idx_axis], lw=2.0, ls="-", color=c0, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=0$")
    h_cr_blue_sw, = ax_cbot.plot(r_cm[idx_core], m_sw_per_sr[idx_core], lw=2.0, ls="-", color=cc, label=r"$dM_{\rm sw}/d\Omega$ @ $\theta=\theta_c$")
    h_cr_red_th1, = ax_cbot.plot(r_cm[idx_axis], thresh1_local[idx_axis], lw=1.7, ls=":", color=c0, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_cr_blue_th1, = ax_cbot.plot(r_cm[idx_core], thresh1_local[idx_core], lw=1.7, ls=":", color=cc, label=r"$(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    h_cr_red_th10, = ax_cbot.plot(r_cm[idx_axis], thresh10_local[idx_axis], lw=1.7, ls="--", color=c0, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=0$")
    h_cr_blue_th10, = ax_cbot.plot(r_cm[idx_core], thresh10_local[idx_core], lw=1.7, ls="--", color=cc, label=r"$10(dM_{\rm ej}/d\Omega)/\Gamma$ @ $\theta=\theta_c$")
    ax_cbot.set_xlabel("Radius [cm]")
    ax_cbot.set_ylabel(r"Mass per solid angle [g sr$^{-1}$]")

    handles_cr = [h_cr_red_sw, h_cr_red_th1, h_cr_red_th10]
    if h_cr_data is not None:
        handles_cr.append(h_cr_data)
    else:
        h_dummy_cr, = ax_cbot.plot([], [], alpha=0.0, label="")
        handles_cr.append(h_dummy_cr)
    handles_cr.extend([h_cr_blue_sw, h_cr_blue_th1, h_cr_blue_th10])
    labels_cr = [h.get_label() for h in handles_cr]
    ax_cbot.legend(handles_cr, labels_cr, fontsize=8, ncol=2, loc="best")

    fig_combo.suptitle(f"GRB {event}", fontsize=14, y=0.995)
    fig_combo.tight_layout(rect=(0, 0, 1, 0.975))

    out_time_pdf = campaign_dir / f"{event}_structjet_swept_mass_diagnostics_vs_time.pdf"
    out_time_png = campaign_dir / f"{event}_structjet_swept_mass_diagnostics_vs_time.png"
    out_radius_pdf = campaign_dir / f"{event}_structjet_swept_mass_diagnostics_vs_radius.pdf"
    out_radius_png = campaign_dir / f"{event}_structjet_swept_mass_diagnostics_vs_radius.png"
    out_ct_pdf = campaign_dir / f"{event}_structjet_swept_mass_local_vs_coreavg_per_sr_vs_time.pdf"
    out_ct_png = campaign_dir / f"{event}_structjet_swept_mass_local_vs_coreavg_per_sr_vs_time.png"
    out_cr_pdf = campaign_dir / f"{event}_structjet_swept_mass_local_vs_coreavg_per_sr_vs_radius.pdf"
    out_cr_png = campaign_dir / f"{event}_structjet_swept_mass_local_vs_coreavg_per_sr_vs_radius.png"
    out_ot_pdf = campaign_dir / f"{event}_structjet_swept_mass_single_overlay_per_sr_vs_time.pdf"
    out_ot_png = campaign_dir / f"{event}_structjet_swept_mass_single_overlay_per_sr_vs_time.png"
    out_or_pdf = campaign_dir / f"{event}_structjet_swept_mass_single_overlay_per_sr_vs_radius.pdf"
    out_or_png = campaign_dir / f"{event}_structjet_swept_mass_single_overlay_per_sr_vs_radius.png"
    out_combo_pdf = campaign_dir / f"{event}_structjet_swept_mass_single_overlay_two_panel.pdf"
    out_combo_png = campaign_dir / f"{event}_structjet_swept_mass_single_overlay_two_panel.png"
    fig_t.savefig(out_time_pdf)
    fig_t.savefig(out_time_png, dpi=220)
    fig_r.savefig(out_radius_pdf)
    fig_r.savefig(out_radius_png, dpi=220)
    fig_ct.savefig(out_ct_pdf)
    fig_ct.savefig(out_ct_png, dpi=220)
    fig_cr.savefig(out_cr_pdf)
    fig_cr.savefig(out_cr_png, dpi=220)
    fig_ot.savefig(out_ot_pdf)
    fig_ot.savefig(out_ot_png, dpi=220)
    fig_or.savefig(out_or_pdf)
    fig_or.savefig(out_or_png, dpi=220)
    fig_combo.savefig(out_combo_pdf)
    fig_combo.savefig(out_combo_png, dpi=220)
    plt.close(fig_t)
    plt.close(fig_r)
    plt.close(fig_ct)
    plt.close(fig_cr)
    plt.close(fig_ot)
    plt.close(fig_or)
    plt.close(fig_combo)

    print(f"Wrote: {out_time_pdf}")
    print(f"Wrote: {out_radius_pdf}")
    print(f"Wrote: {out_ct_pdf}")
    print(f"Wrote: {out_cr_pdf}")
    print(f"Wrote: {out_ot_pdf}")
    print(f"Wrote: {out_or_pdf}")
    print(f"Wrote: {out_combo_pdf}")


if __name__ == "__main__":
    main()
