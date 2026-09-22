#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from plot_tight_density_profiles import PLOT_DIR, final_file, read_plan, read_vtu


@dataclass
class P4Features:
    run_id: str
    n_rho_exp: int
    x_ts: float
    x_pre: float
    y_pre: float
    x_4outer: float
    x_inflect: float
    x_final_rise: float
    x_flat_min: float
    y_flat_min: float
    x_peak_wall: float
    y_peak_wall: float
    x_peak_half_left: float
    x_peak_half_right: float
    width_peak_wall: float
    width_peak_wall_dex: float
    rt_external_pc: float
    rt_real_pc: float


def smooth(y: np.ndarray, width: int = 7) -> np.ndarray:
    width = max(3, int(width) | 1)
    kernel = np.ones(width, dtype=float) / float(width)
    ypad = np.pad(y, (width // 2, width // 2), mode="edge")
    return np.convolve(ypad, kernel, mode="valid")


def crossing_upward(x: np.ndarray, y: np.ndarray, target: float, start: int = 0) -> float:
    for i in range(max(0, start), len(x) - 1):
        y0 = y[i]
        y1 = y[i + 1]
        if (y0 <= target <= y1) or (y1 <= target <= y0):
            t = 0.0 if y1 == y0 else (target - y0) / (y1 - y0)
            return float(x[i] + t * (x[i + 1] - x[i]))
    return float("nan")


def crossing_downward(x: np.ndarray, y: np.ndarray, target: float, start: int = 0, stop_x: float | None = None) -> float:
    for i in range(max(0, start), len(x) - 1):
        if stop_x is not None and x[i] > stop_x:
            break
        y0 = y[i]
        y1 = y[i + 1]
        if (y0 >= target >= y1) or (y1 >= target >= y0):
            t = 0.0 if y1 == y0 else (target - y0) / (y1 - y0)
            return float(x[i] + t * (x[i + 1] - x[i]))
    return float("nan")


def crossing_upward_until(x: np.ndarray, y: np.ndarray, target: float, start: int = 0, stop: int | None = None) -> float:
    last = (len(x) - 1) if stop is None else min(stop, len(x) - 1)
    for i in range(max(0, start), last):
        y0 = y[i]
        y1 = y[i + 1]
        if (y0 <= target <= y1) or (y1 <= target <= y0):
            t = 0.0 if y1 == y0 else (target - y0) / (y1 - y0)
            return float(x[i] + t * (x[i + 1] - x[i]))
    return float("nan")


def extract_features(x: np.ndarray, y: np.ndarray, run_id: str, rt_external_pc: float) -> P4Features:
    m = np.isfinite(x) & np.isfinite(y) & (x > 0.0) & (y > 0.0)
    x = x[m]
    y = y[m]
    if x.size < 100:
        raise ValueError(f"{run_id}: too few valid points")

    lx = np.log(x)
    ly = np.log(y)
    ly_s = smooth(ly, width=7)
    d1 = np.gradient(ly_s, lx)

    # Inner wind normalization: y_wind = A / x^2 on the pre-shock branch.
    fit_window = (x > 0.20) & (x < 0.50)
    if np.count_nonzero(fit_window) < 6:
        fit_window = x < 0.55
    if np.count_nonzero(fit_window) < 4:
        raise ValueError(f"{run_id}: cannot fit wind branch")
    A = float(np.median(y[fit_window] * (x[fit_window] ** 2)))
    y_wind = A / np.maximum(x, 1e-30) ** 2

    # Initial shock location from the physical factor-4 jump midpoint: q = y/y_wind = 2.
    q = y / np.maximum(y_wind, 1e-30)
    lq = smooth(np.log(np.maximum(q, 1e-30)), width=5)
    shock_window = (x > 0.20) & (x < 1.60)
    if np.count_nonzero(shock_window) < 6:
        raise ValueError(f"{run_id}: no shock search window")
    xs = x[shock_window]
    qs = lq[shock_window]
    target_q = np.log(2.0)
    cross_idx = np.where((qs[:-1] <= target_q) & (qs[1:] >= target_q))[0]
    if cross_idx.size > 0:
        i = int(cross_idx[0])
        y0 = qs[i]
        y1 = qs[i + 1]
        t = 0.0 if y1 == y0 else (target_q - y0) / (y1 - y0)
        x_ts = float(xs[i] + t * (xs[i + 1] - xs[i]))
    else:
        x_ts = float(xs[int(np.argmin(np.abs(qs - target_q)))])

    # Density just before the shock.
    pre_window = (x >= 0.85 * x_ts) & (x <= 0.97 * x_ts)
    if np.count_nonzero(pre_window) == 0:
        i_pre = int(np.argmin(np.abs(x - 0.92 * x_ts)))
        x_pre = float(x[i_pre])
        y_pre = float(y[i_pre])
    else:
        x_pre = float(np.median(x[pre_window]))
        y_pre = float(np.median(y[pre_window]))

    # Outer radius of the ~4*n_t shelf: first descending crossing of y = 4*A.
    y_4 = 4.0 * A
    start = int(np.searchsorted(x, x_ts))
    x_4outer = crossing_downward(x, y, y_4, start=start, stop_x=2.5)
    if not np.isfinite(x_4outer):
        x_4outer = crossing_downward(x, y, y_4, start=start, stop_x=None)
    if not np.isfinite(x_4outer):
        x_4outer = float("nan")

    # Small-bump inflection zone around r/R_t ~ 1.5-2: use least-negative slope.
    bump_window = (x > 1.40) & (x < 2.30)
    if np.count_nonzero(bump_window) < 4:
        x_inflect = float("nan")
    else:
        idx = np.where(bump_window)[0]
        i_inflect = int(idx[np.argmax(d1[idx])])
        x_inflect = float(x[i_inflect])

    # Final rise transition feature (onset-style):
    # define as first upward crossing where density reaches 2x the cavity-floor
    # minimum, i.e. the beginning of the outer-wall rise.
    min_window = (x > 2.0) & (x < 12.0)
    if np.count_nonzero(min_window) < 4:
        x_final_rise = float("nan")
        y_out = float("nan")
        i_min = int(np.argmin(y))
    else:
        idx_min = np.where(min_window)[0]
        i_min = int(idx_min[np.argmin(y[idx_min])])
        if np.any(x > 12.0):
            y_out = float(np.median(y[x > 12.0]))
        else:
            high = np.argsort(x)[-max(8, x.size // 10) :]
            y_out = float(np.median(y[high]))
        y_floor = float(y[i_min])
        y_onset = max(2.0 * y_floor, 1e-30)
        x_final_onset = crossing_upward(x, y, y_onset, start=i_min)
        if np.isfinite(x_final_onset):
            x_final_rise = float(x_final_onset)
        else:
            # Fallback: geometric midpoint crossing if onset crossing fails.
            y_mid = float(np.sqrt(max(y_floor, 1e-30) * max(y_out, 1e-30)))
            x_final_mid = crossing_upward(x, y, y_mid, start=i_min)
            x_final_rise = float(x_final_mid) if np.isfinite(x_final_mid) else float(x[i_min])

    # Flat minimum density just inside the outer bubble rise.
    left_floor = max(2.0, (x_4outer + 0.15) if np.isfinite(x_4outer) else 2.0)
    right_floor = 0.92 * x_final_rise if np.isfinite(x_final_rise) else 12.0
    floor_window = (x > left_floor) & (x < right_floor)
    if np.count_nonzero(floor_window) < 5:
        floor_window = (x > 2.0) & (x < 0.95 * x_final_rise) if np.isfinite(x_final_rise) else (x > 2.0) & (x < 12.0)
    if np.count_nonzero(floor_window) < 5:
        floor_window = min_window if np.count_nonzero(min_window) >= 4 else (x > 2.0) & (x < 12.0)

    if np.count_nonzero(floor_window) == 0:
        x_flat_min = float(x[i_min])
        y_flat_min = float(y[i_min])
    else:
        idx_floor = np.where(floor_window)[0]
        i_floor = int(idx_floor[np.argmin(y[idx_floor])])
        y_floor_min = float(y[i_floor])
        # Capture the flat trough level with a narrow band above the minimum.
        flat_mask = floor_window & (y <= 1.20 * y_floor_min)
        if np.count_nonzero(flat_mask) >= 4:
            x_flat_min = float(np.median(x[flat_mask]))
            y_flat_min = float(np.median(y[flat_mask]))
        else:
            x_flat_min = float(x[i_floor])
            y_flat_min = y_floor_min

    # Peak density just before the outer wall / ISM plateau.
    if np.isfinite(x_final_rise):
        peak_window = (x > 1.02 * x_final_rise) & (x < min(np.max(x), 3.0 * x_final_rise))
    else:
        peak_window = x > 3.0
    if np.count_nonzero(peak_window) < 5:
        peak_window = x > max(3.0, 1.01 * x_final_rise) if np.isfinite(x_final_rise) else (x > 3.0)
    if np.count_nonzero(peak_window) == 0:
        i_peak = int(np.argmax(y))
    else:
        idx_peak = np.where(peak_window)[0]
        i_peak = int(idx_peak[np.argmax(y[idx_peak])])

    x_peak_wall = float(x[i_peak])
    y_peak_wall = float(y[i_peak])

    # Width of that peak around half-height above the outer plateau.
    y_base = y_out if np.isfinite(y_out) else float(np.median(y[-max(10, y.size // 10) :]))
    if y_peak_wall <= 1.01 * y_base:
        x_peak_half_left = x_peak_wall
        x_peak_half_right = x_peak_wall
        width_peak_wall = 0.0
        width_peak_wall_dex = 0.0
    else:
        y_half = float(y_base + 0.5 * (y_peak_wall - y_base))
        # left side: crossing before the peak
        left_start = int(np.searchsorted(x, x_final_rise)) if np.isfinite(x_final_rise) else max(i_peak - 50, 0)
        x_peak_half_left = crossing_upward_until(x, y, y_half, start=left_start, stop=i_peak)
        if not np.isfinite(x_peak_half_left):
            x_peak_half_left = float(x[max(i_peak - 1, 0)])
        # right side: crossing down from the peak toward plateau
        x_peak_half_right = crossing_downward(x, y, y_half, start=i_peak, stop_x=min(np.max(x), 4.0 * x_peak_wall))
        if not np.isfinite(x_peak_half_right):
            x_peak_half_right = float(x[min(i_peak + 1, len(x) - 1)])
        width_peak_wall = float(max(x_peak_half_right - x_peak_half_left, 0.0))
        if x_peak_half_right > x_peak_half_left > 0.0:
            width_peak_wall_dex = float(np.log10(x_peak_half_right / x_peak_half_left))
        else:
            width_peak_wall_dex = 0.0

    n_rho_exp = -int(run_id.split("_n")[1])
    return P4Features(
        run_id=run_id,
        n_rho_exp=n_rho_exp,
        x_ts=x_ts,
        x_pre=x_pre,
        y_pre=y_pre,
        x_4outer=x_4outer,
        x_inflect=x_inflect,
        x_final_rise=x_final_rise,
        x_flat_min=x_flat_min,
        y_flat_min=y_flat_min,
        x_peak_wall=x_peak_wall,
        y_peak_wall=y_peak_wall,
        x_peak_half_left=x_peak_half_left,
        x_peak_half_right=x_peak_half_right,
        width_peak_wall=width_peak_wall,
        width_peak_wall_dex=width_peak_wall_dex,
        rt_external_pc=rt_external_pc,
        rt_real_pc=float(x_ts * rt_external_pc),
    )


def fit_cubic(n: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    coeff = np.polyfit(n, y, deg=3)
    pred = np.polyval(coeff, n)
    return coeff, pred


def fit_cubic_log10(n: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if np.any(y <= 0.0):
        raise ValueError("fit_cubic_log10 requires strictly positive y")
    coeff_log = np.polyfit(n, np.log10(y), deg=3)
    pred = 10.0 ** np.polyval(coeff_log, n)
    return coeff_log, pred


def main() -> None:
    plan = read_plan()
    runs = sorted([r for r in plan.keys() if r.startswith("p4_")], key=lambda r: int(r.split("_n")[1]))
    if len(runs) < 4:
        raise RuntimeError(f"Expected 4 p4 runs, found {len(runs)}")

    features: list[P4Features] = []
    curves: list[tuple[str, np.ndarray, np.ndarray]] = []
    for run in runs:
        radius_pc, rho_g_cm3, _ = read_vtu(final_file(run))
        row = plan[run]
        x = radius_pc / row["rt_external_pc"]
        y = rho_g_cm3 / row["rho_g_cm3"]
        feat = extract_features(x, y, run, row["rt_external_pc"])
        features.append(feat)
        m = np.isfinite(x) & np.isfinite(y) & (x > 0.0) & (y > 0.0)
        curves.append((run, x[m], y[m]))

    features = sorted(features, key=lambda f: f.n_rho_exp)
    n = np.asarray([f.n_rho_exp for f in features], dtype=float)

    y_pre = np.asarray([f.y_pre for f in features], dtype=float)
    y_flat = np.asarray([f.y_flat_min for f in features], dtype=float)
    y_peak = np.asarray([f.y_peak_wall for f in features], dtype=float)
    w_peak = np.asarray([f.width_peak_wall_dex for f in features], dtype=float)
    x_4outer = np.asarray([f.x_4outer for f in features], dtype=float)
    x_inflect = np.asarray([f.x_inflect for f in features], dtype=float)
    x_final = np.asarray([f.x_final_rise for f in features], dtype=float)

    # Fit this feature in log space to avoid unphysical oscillations between
    # monotonic points spanning multiple dex.
    c_y_pre_log10, p_y_pre = fit_cubic_log10(n, y_pre)
    c_y_flat_log10, p_y_flat = fit_cubic_log10(n, y_flat)
    c_y_peak_log10, p_y_peak = fit_cubic_log10(n, y_peak)
    c_w_peak, p_w_peak = fit_cubic(n, w_peak)
    c_x4, p_x4 = fit_cubic(n, x_4outer)
    c_xinf, p_xinf = fit_cubic(n, x_inflect)
    c_xfin, p_xfin = fit_cubic(n, x_final)

    rms_y_pre = float(np.sqrt(np.mean((p_y_pre - y_pre) ** 2)))
    rms_y_flat = float(np.sqrt(np.mean((p_y_flat - y_flat) ** 2)))
    rms_y_peak = float(np.sqrt(np.mean((p_y_peak - y_peak) ** 2)))
    rms_w_peak = float(np.sqrt(np.mean((p_w_peak - w_peak) ** 2)))
    rms_x4 = float(np.sqrt(np.mean((p_x4 - x_4outer) ** 2)))
    rms_xinf = float(np.sqrt(np.mean((p_xinf - x_inflect) ** 2)))
    rms_xfin = float(np.sqrt(np.mean((p_xfin - x_final) ** 2)))

    # Plot 1: profile overlay with all feature locations.
    fig, ax = plt.subplots(figsize=(11, 7), constrained_layout=True)
    color_map: dict[str, str] = {}
    for run, x, y in curves:
        line = ax.plot(x, y, lw=2.1, label=run)[0]
        color = line.get_color()
        color_map[run] = color
        f = next(v for v in features if v.run_id == run)
        ax.axvline(f.x_ts, color=color, ls=":", lw=1.2, alpha=0.95)
        ax.axvline(f.x_4outer, color=color, ls="--", lw=1.15, alpha=0.95)
        ax.axvline(f.x_inflect, color=color, ls="-.", lw=1.15, alpha=0.95)
        ax.axvline(f.x_final_rise, color=color, ls="-", lw=1.10, alpha=0.55)
        ax.plot(f.x_pre, f.y_pre, marker="o", ms=5.2, color=color, mec="k", mew=0.3, linestyle="None")
        ax.plot(f.x_flat_min, f.y_flat_min, marker="s", ms=5.0, color=color, mec="k", mew=0.3, linestyle="None")
        ax.plot(f.x_peak_wall, f.y_peak_wall, marker="^", ms=5.4, color=color, mec="k", mew=0.3, linestyle="None")
        if f.x_peak_half_right > f.x_peak_half_left > 0.0:
            y_half_plot = 0.5 * (f.y_peak_wall + (np.median(y[x > 12.0]) if np.any(x > 12.0) else np.median(y[-10:])))
            ax.hlines(
                y_half_plot,
                f.x_peak_half_left,
                f.x_peak_half_right,
                color=color,
                lw=1.2,
                alpha=0.7,
            )

    ax.axvline(1.0, color="k", ls=":", lw=1.2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$r/R_t$")
    ax.set_ylabel(r"$\rho/\rho_{\rm ISM}$")
    ax.set_title("p4 structured runs with extracted feature locations")
    ax.grid(True, which="both", alpha=0.25)

    run_legend = ax.legend(loc="lower right", fontsize=10, ncol=2, title="Runs")
    ax.add_artist(run_legend)
    feature_handles = [
        Line2D([0], [0], color="k", ls=":", lw=1.3, label=r"$x_{ts}$ (initial shock midpoint)"),
        Line2D([0], [0], color="k", ls="--", lw=1.2, label=r"$x_{4,outer}$"),
        Line2D([0], [0], color="k", ls="-.", lw=1.2, label=r"$x_{infl}$ (small-bump feature)"),
        Line2D([0], [0], color="k", ls="-", lw=1.2, alpha=0.6, label=r"$x_{final}$ (final rise midpoint)"),
        Line2D([0], [0], marker="o", color="k", lw=0, label=r"$y_{pre}$ at $x<x_{ts}$"),
        Line2D([0], [0], marker="s", color="k", lw=0, label=r"$y_{flat,min}$ just inside outer rise"),
        Line2D([0], [0], marker="^", color="k", lw=0, label=r"$y_{peak,wall}$ just before outer wall"),
        Line2D([0], [0], color="k", ls=":", lw=1.2, label=r"$R_t$ (external)"),
    ]
    ax.legend(handles=feature_handles, loc="upper left", fontsize=9)

    profiles_out = PLOT_DIR / "p4_feature_locations_overlay.png"
    fig.savefig(profiles_out, dpi=220)
    plt.close(fig)

    # Plot 2: feature-vs-density cubic fits.
    fig2, axes = plt.subplots(4, 2, figsize=(11.3, 13.0), constrained_layout=True)
    n_grid = np.linspace(float(n.min()), float(n.max()), 200)

    axes[0, 0].plot(n, y_pre, "o", ms=6, label="measured")
    axes[0, 0].plot(n_grid, 10.0 ** np.polyval(c_y_pre_log10, n_grid), "-", lw=1.8, label="cubic fit (log-space)")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_title(r"Density just before $x_{ts}$")
    axes[0, 0].set_xlabel(r"ambient-density exponent $n$ in $\rho_{\rm ISM}=10^{n}$ g cm$^{-3}$")
    axes[0, 0].set_ylabel(r"$\rho_{pre}/\rho_{ISM}$")
    axes[0, 0].grid(True, which="both", alpha=0.25)
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].plot(n, y_flat, "o", ms=6, label="measured")
    axes[0, 1].plot(n_grid, 10.0 ** np.polyval(c_y_flat_log10, n_grid), "-", lw=1.8, label="cubic fit (log-space)")
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_title(r"Flat minimum density (inside outer rise)")
    axes[0, 1].set_xlabel(r"ambient-density exponent $n$ in $\rho_{\rm ISM}=10^{n}$ g cm$^{-3}$")
    axes[0, 1].set_ylabel(r"$\rho_{flat,min}/\rho_{ISM}$")
    axes[0, 1].grid(True, which="both", alpha=0.25)
    axes[0, 1].legend(fontsize=8)

    axes[1, 0].plot(n, x_4outer, "o", ms=6, label="measured")
    axes[1, 0].plot(n_grid, np.polyval(c_x4, n_grid), "-", lw=1.8, label="cubic fit")
    axes[1, 0].set_title(r"Outer radius of 4x-density shelf")
    axes[1, 0].set_xlabel(r"ambient-density exponent $n$ in $\rho_{\rm ISM}=10^{n}$ g cm$^{-3}$")
    axes[1, 0].set_ylabel(r"$x_{4,outer}=r_{4,outer}/R_t$")
    axes[1, 0].grid(True, which="both", alpha=0.25)
    axes[1, 0].legend(fontsize=8)

    axes[1, 1].plot(n, x_inflect, "o", ms=6, label="measured")
    axes[1, 1].plot(n_grid, np.polyval(c_xinf, n_grid), "-", lw=1.8, label="cubic fit")
    axes[1, 1].set_title(r"Inflection / small-bump location")
    axes[1, 1].set_xlabel(r"ambient-density exponent $n$ in $\rho_{\rm ISM}=10^{n}$ g cm$^{-3}$")
    axes[1, 1].set_ylabel(r"$x_{infl}=r_{infl}/R_t$")
    axes[1, 1].grid(True, which="both", alpha=0.25)
    axes[1, 1].legend(fontsize=8)

    axes[2, 0].plot(n, x_final, "o", ms=6, label="measured")
    axes[2, 0].plot(n_grid, np.polyval(c_xfin, n_grid), "-", lw=1.8, label="cubic fit")
    axes[2, 0].set_title(r"Final-rise midpoint")
    axes[2, 0].set_xlabel(r"ambient-density exponent $n$ in $\rho_{\rm ISM}=10^{n}$ g cm$^{-3}$")
    axes[2, 0].set_ylabel(r"$x_{final}=r_{final}/R_t$")
    axes[2, 0].grid(True, which="both", alpha=0.25)
    axes[2, 0].legend(fontsize=8)

    axes[2, 1].plot(n, y_peak, "o", ms=6, label="measured")
    axes[2, 1].plot(n_grid, 10.0 ** np.polyval(c_y_peak_log10, n_grid), "-", lw=1.8, label="cubic fit (log-space)")
    axes[2, 1].set_yscale("log")
    axes[2, 1].set_title(r"Peak density just before bubble wall")
    axes[2, 1].set_xlabel(r"ambient-density exponent $n$ in $\rho_{\rm ISM}=10^{n}$ g cm$^{-3}$")
    axes[2, 1].set_ylabel(r"$\rho_{peak,wall}/\rho_{ISM}$")
    axes[2, 1].grid(True, which="both", alpha=0.25)
    axes[2, 1].legend(fontsize=8)

    axes[3, 0].plot(n, w_peak, "o", ms=6, label="measured")
    axes[3, 0].plot(n_grid, np.polyval(c_w_peak, n_grid), "-", lw=1.8, label="cubic fit")
    axes[3, 0].set_title(r"Pre-wall peak width")
    axes[3, 0].set_xlabel(r"ambient-density exponent $n$ in $\rho_{\rm ISM}=10^{n}$ g cm$^{-3}$")
    axes[3, 0].set_ylabel(r"$\Delta\log_{10}(r/R_t)$ at half-peak")
    axes[3, 0].grid(True, which="both", alpha=0.25)
    axes[3, 0].legend(fontsize=8)

    axes[3, 1].axis("off")

    fits_out = PLOT_DIR / "p4_feature_vs_density_cubic_fits.png"
    fig2.savefig(fits_out, dpi=220)
    plt.close(fig2)

    # CSV + coefficients report.
    csv_out = PLOT_DIR / "p4_feature_table_and_cubic_fits.csv"
    with csv_out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "run_id",
                "n_rho_exp",
                "x_ts",
                "x_pre",
                "y_pre",
                "x_flat_min",
                "y_flat_min",
                "x_peak_wall",
                "y_peak_wall",
                "x_peak_half_left",
                "x_peak_half_right",
                "width_peak_wall",
                "width_peak_wall_dex",
                "x_4outer",
                "x_inflect",
                "x_final_rise",
                "rt_external_pc",
                "rt_real_pc",
                "y_pre_fit",
                "y_flat_min_fit",
                "y_peak_wall_fit",
                "width_peak_wall_dex_fit",
                "x_4outer_fit",
                "x_inflect_fit",
                "x_final_rise_fit",
            ]
        )
        for i, f in enumerate(features):
            w.writerow(
                [
                    f.run_id,
                    f.n_rho_exp,
                    f.x_ts,
                    f.x_pre,
                    f.y_pre,
                    f.x_flat_min,
                    f.y_flat_min,
                    f.x_peak_wall,
                    f.y_peak_wall,
                    f.x_peak_half_left,
                    f.x_peak_half_right,
                    f.width_peak_wall,
                    f.width_peak_wall_dex,
                    f.x_4outer,
                    f.x_inflect,
                    f.x_final_rise,
                    f.rt_external_pc,
                    f.rt_real_pc,
                    p_y_pre[i],
                    p_y_flat[i],
                    p_y_peak[i],
                    p_w_peak[i],
                    p_x4[i],
                    p_xinf[i],
                    p_xfin[i],
                ]
            )

    txt_out = PLOT_DIR / "p4_feature_cubic_models.txt"
    txt_out.write_text(
        "\n".join(
            [
                "p4 additional feature fits (4-parameter cubic in ambient-density exponent n, rho_ism = 10^n)",
                "Model form: f(n) = a3*n^3 + a2*n^2 + a1*n + a0",
                "",
                "y_pre model: log10(y_pre) = a3*n^3 + a2*n^2 + a1*n + a0",
                f"y_pre log10 coefficients: {c_y_pre_log10.tolist()}",
                f"y_pre RMS: {rms_y_pre:.6e}",
                "",
                "y_flat_min model: log10(y_flat_min) = a3*n^3 + a2*n^2 + a1*n + a0",
                f"y_flat_min log10 coefficients: {c_y_flat_log10.tolist()}",
                f"y_flat_min RMS: {rms_y_flat:.6e}",
                "",
                "y_peak_wall model: log10(y_peak_wall) = a3*n^3 + a2*n^2 + a1*n + a0",
                f"y_peak_wall log10 coefficients: {c_y_peak_log10.tolist()}",
                f"y_peak_wall RMS: {rms_y_peak:.6e}",
                "",
                "width_peak_wall_dex model: w(n) = a3*n^3 + a2*n^2 + a1*n + a0",
                f"width_peak_wall_dex coefficients: {c_w_peak.tolist()}",
                f"width_peak_wall_dex RMS: {rms_w_peak:.6e}",
                "",
                f"x_4outer coefficients: {c_x4.tolist()}",
                f"x_4outer RMS: {rms_x4:.6e}",
                "",
                f"x_inflect coefficients: {c_xinf.tolist()}",
                f"x_inflect RMS: {rms_xinf:.6e}",
                "",
                f"x_final_rise coefficients: {c_xfin.tolist()}",
                f"x_final_rise RMS: {rms_xfin:.6e}",
                "",
                "Feature definitions:",
                "- y_pre: median density in [0.85, 0.97] x_ts on the pre-shock side.",
                "- y_flat_min: flat minimum density just inside the outer rise (median of trough points within 20% of the local minimum).",
                "- y_peak_wall: maximum density in the pre-wall region (x > 1.02 x_final and x < 3 x_final).",
                "- width_peak_wall_dex: log10-width between left/right half-height crossings of the pre-wall peak above the outer ISM plateau.",
                "- x_4outer: first descending crossing of y = 4*A, where A is pre-shock wind normalization y=A/x^2.",
                "- x_inflect: least-negative local log-slope location in 1.4 < x < 2.3.",
                "- x_final_rise: midpoint of final rise between cavity minimum and outer ISM plateau (log-space).",
            ]
        )
    )

    print(profiles_out)
    print(fits_out)
    print(csv_out)
    print(txt_out)


if __name__ == "__main__":
    main()
