#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np

from evaluate_p4_full_profile_density_interpolator import pchip_eval
from evaluate_p4n22_7param_model import despike_log_profile
from fit_p4_additional_features import extract_features
from plot_tight_density_profiles import all_run_ids, final_file, read_plan, read_vtu

CAMPAIGN = Path(__file__).resolve().parent
OUT_ROOT = CAMPAIGN / "analysis_allP_20260501"
PLOT_DIR = OUT_ROOT / "plots"
TABLE_DIR = OUT_ROOT / "tables"
REPORT_DIR = OUT_ROOT / "reports"
for p in (PLOT_DIR, TABLE_DIR, REPORT_DIR):
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class RunRecord:
    run_id: str
    p: int
    n: int
    chosen_snapshot: str
    final_snapshot: str
    final_valid_fraction: float
    chosen_valid_fraction: float
    x: np.ndarray
    y: np.ndarray
    x_max: float
    x_ts: float
    y_pre: float
    x_4outer: float
    x_inflect: float
    x_final_rise: float
    x_flat_min: float
    y_flat_min: float
    x_peak_wall: float
    y_peak_wall: float
    width_peak_wall_dex: float
    headroom_ratio: float
    tail_ratio: float
    tail_slope: float
    shock_cells_12_38: float
    shock_width_dex_12_38: float
    outer_rise_cells: float
    outer_rise_width_dex: float
    domain_issue: bool
    resolution_issue: bool
    decent_quality: bool


FEATURE_KEYS = [
    "x_ts",
    "y_pre",
    "x_4outer",
    "x_inflect",
    "x_final_rise",
    "y_flat_min",
    "x_peak_wall",
    "y_peak_wall",
    "width_peak_wall_dex",
]


def run_to_pn(run_id: str) -> tuple[int, int]:
    return int(run_id[1]), -int(run_id.split("_n")[1])


def finite_positive_mask(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.isfinite(x) & np.isfinite(y) & (x > 0.0) & (y > 0.0)


def crossing_up(x: np.ndarray, y: np.ndarray, target: float, start: int = 0) -> float:
    for i in range(max(0, start), len(x) - 1):
        y0 = y[i]
        y1 = y[i + 1]
        if (y0 <= target <= y1) or (y1 <= target <= y0):
            t = 0.0 if y1 == y0 else (target - y0) / (y1 - y0)
            return float(x[i] + t * (x[i + 1] - x[i]))
    return float("nan")


def choose_snapshot(run_id: str, rt_external_pc: float, rho_ism_g_cm3: float) -> tuple[Path, float, float]:
    files = sorted((CAMPAIGN / f"pressure_{run_id}" / "output" / "Ostar_1D").glob("test*.vtu"))
    if not files:
        raise FileNotFoundError(f"{run_id}: no VTU files")

    final = files[-1]
    xf, rhof, _ = read_vtu(final)
    yf = rhof / rho_ism_g_cm3
    xnf = xf / rt_external_pc
    mf = finite_positive_mask(xnf, yf)
    final_valid_fraction = float(np.count_nonzero(mf) / max(1, len(yf)))

    chosen: Path | None = None
    chosen_fraction = float("nan")
    for f in reversed(files):
        x, rho, _ = read_vtu(f)
        y = rho / rho_ism_g_cm3
        xn = x / rt_external_pc
        m = finite_positive_mask(xn, y)
        frac = float(np.count_nonzero(m) / max(1, len(y)))
        if np.count_nonzero(m) < 120:
            continue
        if frac < 0.90:
            continue
        if float(np.min(xn[m])) > 0.25:
            continue
        chosen = f
        chosen_fraction = frac
        break

    if chosen is None:
        # Fallback to best finite-rich snapshot by count then fraction.
        best_score = (-1, -1.0)
        best_file = final
        best_frac = final_valid_fraction
        for f in files:
            x, rho, _ = read_vtu(f)
            y = rho / rho_ism_g_cm3
            xn = x / rt_external_pc
            m = finite_positive_mask(xn, y)
            score = (int(np.count_nonzero(m)), float(np.count_nonzero(m) / max(1, len(y))))
            if score > best_score:
                best_score = score
                best_file = f
                best_frac = score[1]
        chosen = best_file
        chosen_fraction = best_frac

    return chosen, final_valid_fraction, chosen_fraction


def compute_resolution_metrics(x: np.ndarray, y: np.ndarray, x_ts: float, x_final_rise: float, y_flat_min: float) -> tuple[float, float, float, float]:
    # Inner shock width: q = y / y_wind, measured from q=1.2 to q=3.8.
    fit_window = (x > 0.20) & (x < 0.50)
    if np.count_nonzero(fit_window) < 6:
        fit_window = x < 0.55
    A = float(np.median(y[fit_window] * (x[fit_window] ** 2)))
    y_wind = A / np.maximum(x, 1e-30) ** 2
    q = y / np.maximum(y_wind, 1e-30)
    i_start = int(np.searchsorted(x, 0.75 * x_ts))
    x12 = crossing_up(x, q, 1.2, start=i_start)
    x38 = crossing_up(x, q, 3.8, start=i_start)
    if np.isfinite(x12) and np.isfinite(x38) and x38 > x12 > 0.0:
        shock_cells = float(np.count_nonzero((x >= x12) & (x <= x38)))
        shock_width_dex = float(np.log10(x38 / x12))
    else:
        shock_cells = float("nan")
        shock_width_dex = float("nan")

    # Outer rise width from 2*y_floor to 0.9*y_outer.
    outer_mask = x > max(1.15 * x_final_rise, 12.0)
    y_outer = float(np.median(y[outer_mask])) if np.count_nonzero(outer_mask) >= 5 else float(np.median(y[-20:]))
    y_lo = max(2.0 * y_flat_min, 1e-30)
    y_hi = 0.90 * max(y_outer, 1e-30)
    i_floor = int(np.argmin(np.abs(x - max(x_final_rise * 0.75, 2.0))))
    xlo = crossing_up(x, y, y_lo, start=i_floor)
    xhi = crossing_up(x, y, y_hi, start=i_floor)
    if np.isfinite(xlo) and np.isfinite(xhi) and xhi > xlo > 0.0:
        outer_cells = float(np.count_nonzero((x >= xlo) & (x <= xhi)))
        outer_width_dex = float(np.log10(xhi / xlo))
    else:
        outer_cells = float("nan")
        outer_width_dex = float("nan")

    return shock_cells, shock_width_dex, outer_cells, outer_width_dex


def build_records() -> list[RunRecord]:
    plan = read_plan()
    records: list[RunRecord] = []
    for run_id in all_run_ids(plan):
        row = plan[run_id]
        p, n = run_to_pn(run_id)
        rt = float(row["rt_external_pc"])
        rho_ism = float(row["rho_g_cm3"])
        chosen_file, final_valid_fraction, chosen_valid_fraction = choose_snapshot(run_id, rt, rho_ism)
        final_name = final_file(run_id).name

        radius_pc, rho_g_cm3, _ = read_vtu(chosen_file)
        x_all = radius_pc / rt
        y_all = rho_g_cm3 / rho_ism
        m = finite_positive_mask(x_all, y_all)
        x = x_all[m]
        y = despike_log_profile(y_all[m], threshold_dex=0.32, max_passes=1)
        order = np.argsort(x)
        x = x[order]
        y = y[order]

        feat = extract_features(x, y, run_id, rt)
        x_max = float(np.max(x))
        headroom = float(x_max / max(feat.x_final_rise, 1e-30))
        tail = y[-max(20, len(y) // 20) :]
        tail_ratio = float(np.median(tail))
        if len(y) >= 20:
            lx_tail = np.log10(x[-20:])
            ly_tail = np.log10(y[-20:])
            tail_slope = float(np.polyfit(lx_tail, ly_tail, 1)[0])
        else:
            tail_slope = float("nan")

        shock_cells, shock_wdex, outer_cells, outer_wdex = compute_resolution_metrics(
            x=x,
            y=y,
            x_ts=feat.x_ts,
            x_final_rise=feat.x_final_rise,
            y_flat_min=feat.y_flat_min,
        )

        domain_issue = bool(
            (headroom < 1.35)
            or (abs(np.log10(max(tail_ratio, 1e-30))) > 0.10)
            or (np.isfinite(tail_slope) and abs(tail_slope) > 0.18)
        )
        resolution_issue = bool(
            (np.isfinite(shock_cells) and shock_cells < 3.0)
            or (np.isfinite(outer_cells) and outer_cells < 3.0)
            or (not np.isfinite(shock_cells))
            or (not np.isfinite(outer_cells))
        )
        decent_quality = bool((not domain_issue) and (not resolution_issue) and (chosen_valid_fraction >= 0.90))

        records.append(
            RunRecord(
                run_id=run_id,
                p=p,
                n=n,
                chosen_snapshot=chosen_file.name,
                final_snapshot=final_name,
                final_valid_fraction=final_valid_fraction,
                chosen_valid_fraction=chosen_valid_fraction,
                x=x,
                y=y,
                x_max=x_max,
                x_ts=float(feat.x_ts),
                y_pre=float(feat.y_pre),
                x_4outer=float(feat.x_4outer),
                x_inflect=float(feat.x_inflect),
                x_final_rise=float(feat.x_final_rise),
                x_flat_min=float(feat.x_flat_min),
                y_flat_min=float(feat.y_flat_min),
                x_peak_wall=float(feat.x_peak_wall),
                y_peak_wall=float(feat.y_peak_wall),
                width_peak_wall_dex=float(feat.width_peak_wall_dex),
                headroom_ratio=headroom,
                tail_ratio=tail_ratio,
                tail_slope=tail_slope,
                shock_cells_12_38=shock_cells,
                shock_width_dex_12_38=shock_wdex,
                outer_rise_cells=outer_cells,
                outer_rise_width_dex=outer_wdex,
                domain_issue=domain_issue,
                resolution_issue=resolution_issue,
                decent_quality=decent_quality,
            )
        )
    return records


def write_quality_table(records: list[RunRecord]) -> Path:
    out = TABLE_DIR / "allP_run_quality_table.csv"
    fields = [
        "run_id",
        "p",
        "n",
        "chosen_snapshot",
        "final_snapshot",
        "final_valid_fraction",
        "chosen_valid_fraction",
        "x_ts",
        "x_final_rise",
        "x_max",
        "headroom_ratio",
        "tail_ratio",
        "tail_slope",
        "shock_cells_12_38",
        "shock_width_dex_12_38",
        "outer_rise_cells",
        "outer_rise_width_dex",
        "domain_issue",
        "resolution_issue",
        "decent_quality",
    ]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow(
                {
                    "run_id": r.run_id,
                    "p": r.p,
                    "n": r.n,
                    "chosen_snapshot": r.chosen_snapshot,
                    "final_snapshot": r.final_snapshot,
                    "final_valid_fraction": r.final_valid_fraction,
                    "chosen_valid_fraction": r.chosen_valid_fraction,
                    "x_ts": r.x_ts,
                    "x_final_rise": r.x_final_rise,
                    "x_max": r.x_max,
                    "headroom_ratio": r.headroom_ratio,
                    "tail_ratio": r.tail_ratio,
                    "tail_slope": r.tail_slope,
                    "shock_cells_12_38": r.shock_cells_12_38,
                    "shock_width_dex_12_38": r.shock_width_dex_12_38,
                    "outer_rise_cells": r.outer_rise_cells,
                    "outer_rise_width_dex": r.outer_rise_width_dex,
                    "domain_issue": int(r.domain_issue),
                    "resolution_issue": int(r.resolution_issue),
                    "decent_quality": int(r.decent_quality),
                }
            )
    return out


def plot_domain_and_resolution(records: list[RunRecord]) -> Path:
    recs = sorted(records, key=lambda r: (r.p, r.n))
    labels = [r.run_id for r in recs]
    x = np.arange(len(recs))
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)

    axes[0, 0].plot(x, [r.headroom_ratio for r in recs], "o-")
    axes[0, 0].axhline(1.35, color="r", ls=":", lw=1.0, label="flag threshold")
    axes[0, 0].set_title("Domain Headroom: x_max / x_final_rise")
    axes[0, 0].set_ylabel("ratio")
    axes[0, 0].grid(True, alpha=0.25)
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].plot(x, [np.log10(max(r.tail_ratio, 1e-30)) for r in recs], "o-")
    axes[0, 1].axhline(+0.10, color="r", ls=":", lw=1.0)
    axes[0, 1].axhline(-0.10, color="r", ls=":", lw=1.0, label="flag threshold")
    axes[0, 1].set_title("Boundary Plateau Check: log10(y_tail)")
    axes[0, 1].set_ylabel("dex")
    axes[0, 1].grid(True, alpha=0.25)
    axes[0, 1].legend(fontsize=8)

    axes[1, 0].plot(x, [r.shock_cells_12_38 for r in recs], "o-", label="first-shock cells")
    axes[1, 0].plot(x, [r.outer_rise_cells for r in recs], "s--", label="outer-rise cells")
    axes[1, 0].axhline(3.0, color="r", ls=":", lw=1.0, label="flag threshold")
    axes[1, 0].set_title("Resolution in Transition Regions")
    axes[1, 0].set_ylabel("cells")
    axes[1, 0].grid(True, alpha=0.25)
    axes[1, 0].legend(fontsize=8)

    final_drop = [1.0 - r.final_valid_fraction for r in recs]
    chosen_drop = [1.0 - r.chosen_valid_fraction for r in recs]
    axes[1, 1].bar(x - 0.16, final_drop, width=0.30, label="final snapshot invalid fraction")
    axes[1, 1].bar(x + 0.16, chosen_drop, width=0.30, label="chosen snapshot invalid fraction")
    axes[1, 1].set_title("Snapshot Data Integrity (NaN/invalid fractions)")
    axes[1, 1].set_ylabel("fraction invalid")
    axes[1, 1].grid(True, alpha=0.25)
    axes[1, 1].legend(fontsize=8)

    for ax in axes.flat:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

    out = PLOT_DIR / "allP_domain_and_resolution_diagnostics.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_profiles(records: list[RunRecord]) -> Path:
    recs = sorted(records, key=lambda r: (r.p, r.n))
    fig, ax = plt.subplots(figsize=(11, 6.8), constrained_layout=True)
    colors = plt.cm.plasma(np.linspace(0.08, 0.92, len(recs)))
    for color, r in zip(colors, recs):
        ax.plot(r.x, r.y, lw=1.35, color=color, label=f"{r.run_id} ({r.chosen_snapshot})")
        ax.axvline(r.x_ts, color=color, ls=":", lw=0.85, alpha=0.65)
        ax.axvline(r.x_final_rise, color=color, ls="--", lw=0.85, alpha=0.65)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$r/R_t$")
    ax.set_ylabel(r"$\rho/\rho_{\mathrm{ISM}}$")
    ax.set_title("All 12 pressure-grid profiles (chosen valid snapshots)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=7, ncol=3)
    out = PLOT_DIR / "allP_profiles_with_feature_anchors.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def feature_value(rec: RunRecord, key: str) -> float:
    return float(getattr(rec, key))


def pava(y: np.ndarray, increasing: bool = True) -> np.ndarray:
    """Pool-adjacent-violators isotonic regression with unit weights."""
    yy = np.asarray(y, dtype=float)
    if yy.size == 0:
        return yy.copy()
    if not increasing:
        return -pava(-yy, increasing=True)

    v: list[float] = []
    w: list[float] = []
    c: list[int] = []
    for val in yy:
        v.append(float(val))
        w.append(1.0)
        c.append(1)
        while len(v) >= 2 and v[-2] > v[-1]:
            v2 = (v[-2] * w[-2] + v[-1] * w[-1]) / (w[-2] + w[-1])
            w2 = w[-2] + w[-1]
            c2 = c[-2] + c[-1]
            v[-2] = v2
            w[-2] = w2
            c[-2] = c2
            v.pop()
            w.pop()
            c.pop()

    out = np.empty_like(yy, dtype=float)
    idx = 0
    for vv, cc in zip(v, c):
        out[idx : idx + cc] = vv
        idx += cc
    return out


def fit_pressure_slices_monotone(records: list[RunRecord]) -> tuple[Path, Path]:
    rows: list[dict[str, float | int | str]] = []
    for p in [4, 5, 6]:
        subset = sorted([r for r in records if r.p == p and r.decent_quality], key=lambda r: r.n)
        if len(subset) < 3:
            continue
        fig, axes = plt.subplots(3, 3, figsize=(14, 11), constrained_layout=True)
        axes_flat = axes.flat
        nvals = np.asarray([r.n for r in subset], dtype=float)
        for i, key in enumerate(FEATURE_KEYS):
            yvals = np.asarray([feature_value(r, key) for r in subset], dtype=float)
            finite = np.isfinite(yvals)
            n_use = nvals[finite]
            y_use = yvals[finite]
            if len(y_use) < 3:
                continue

            # Choose monotonic direction from endpoint trend in this pressure slice.
            increasing = bool(y_use[-1] >= y_use[0])
            y_iso = pava(y_use, increasing=increasing)
            n_grid = np.linspace(float(np.min(n_use)), float(np.max(n_use)), 240)
            y_grid = np.array([pchip_eval(n_use, y_iso, nq) for nq in n_grid], dtype=float)

            # Residual metrics against isotonic fit at training points.
            y_hat_train = np.array([pchip_eval(n_use, y_iso, nq) for nq in n_use], dtype=float)
            resid = y_hat_train - y_use
            rms = float(np.sqrt(np.mean(resid**2)))
            mad = float(np.median(np.abs(resid)))

            ax = axes_flat[i]
            ax.plot(n_use, y_use, "o", label="AMRVAC")
            ax.plot(n_grid, y_grid, "-", label="monotone isotonic+PCHIP")
            ax.plot(n_use, y_iso, "s", ms=4.0, label="isotonic points")
            ax.set_title(f"p={p}: {key}  RMS={rms:.3g}, MAD={mad:.3g}")
            ax.set_xlabel("n in rho_ISM=10^n")
            ax.grid(True, alpha=0.25)
            ax.legend(fontsize=7)

            rows.append(
                {
                    "pressure_exponent": p,
                    "feature": key,
                    "increasing": int(increasing),
                    "rms_abs": rms,
                    "mad_abs": mad,
                    "n0": n_use[0],
                    "n1": n_use[1] if len(n_use) > 1 else float("nan"),
                    "n2": n_use[2] if len(n_use) > 2 else float("nan"),
                    "n3": n_use[3] if len(n_use) > 3 else float("nan"),
                    "y0_iso": y_iso[0],
                    "y1_iso": y_iso[1] if len(y_iso) > 1 else float("nan"),
                    "y2_iso": y_iso[2] if len(y_iso) > 2 else float("nan"),
                    "y3_iso": y_iso[3] if len(y_iso) > 3 else float("nan"),
                }
            )

        for j in range(len(FEATURE_KEYS), 9):
            axes_flat[j].axis("off")
        out_plot = PLOT_DIR / f"allP_feature_fits_pressure_p{p}_monotone.png"
        fig.savefig(out_plot, dpi=220)
        plt.close(fig)

    out_csv = TABLE_DIR / "allP_feature_slice_monotone_fits.csv"
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "pressure_exponent",
                "feature",
                "increasing",
                "rms_abs",
                "mad_abs",
                "n0",
                "n1",
                "n2",
                "n3",
                "y0_iso",
                "y1_iso",
                "y2_iso",
                "y3_iso",
            ],
        )
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return out_csv, PLOT_DIR


def fit_pressure_slices(records: list[RunRecord]) -> tuple[Path, Path]:
    coeff_rows: list[dict[str, float | int | str]] = []
    for p in [4, 5, 6]:
        subset = sorted([r for r in records if r.p == p and r.decent_quality], key=lambda r: r.n)
        if len(subset) < 3:
            continue
        fig, axes = plt.subplots(3, 3, figsize=(14, 11), constrained_layout=True)
        axes_flat = axes.flat
        nvals = np.asarray([r.n for r in subset], dtype=float)
        for i, key in enumerate(FEATURE_KEYS):
            yvals = np.asarray([feature_value(r, key) for r in subset], dtype=float)
            finite = np.isfinite(yvals)
            n_use = nvals[finite]
            y_use = yvals[finite]
            if len(y_use) < 3:
                continue
            degree = min(3, len(y_use) - 1)
            coeff = np.polyfit(n_use, y_use, degree)
            n_grid = np.linspace(np.min(n_use), np.max(n_use), 240)
            y_grid = np.polyval(coeff, n_grid)
            ax = axes_flat[i]
            ax.plot(n_use, y_use, "o", label="AMRVAC")
            ax.plot(n_grid, y_grid, "-", label=f"poly deg {degree}")
            ax.set_title(f"p={p}: {key}")
            ax.set_xlabel("n in rho_ISM=10^n")
            ax.grid(True, alpha=0.25)
            ax.legend(fontsize=8)
            coeff_rows.append(
                {
                    "pressure_exponent": p,
                    "feature": key,
                    "degree": degree,
                    "c0": coeff[-1] if len(coeff) >= 1 else float("nan"),
                    "c1": coeff[-2] if len(coeff) >= 2 else float("nan"),
                    "c2": coeff[-3] if len(coeff) >= 3 else float("nan"),
                    "c3": coeff[-4] if len(coeff) >= 4 else float("nan"),
                }
            )
        for j in range(len(FEATURE_KEYS), 9):
            axes_flat[j].axis("off")
        out_plot = PLOT_DIR / f"allP_feature_fits_pressure_p{p}.png"
        fig.savefig(out_plot, dpi=220)
        plt.close(fig)

    coeff_csv = TABLE_DIR / "allP_feature_slice_polyfits.csv"
    with coeff_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["pressure_exponent", "feature", "degree", "c0", "c1", "c2", "c3"])
        w.writeheader()
        for row in coeff_rows:
            w.writerow(row)
    return coeff_csv, PLOT_DIR


def design_matrix(dp: np.ndarray, dn: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones_like(dp), dp, dn, dp * dn, dp**2, dn**2, dp**2 * dn, dp * dn**2])


def fit_global_feature_surfaces(records: list[RunRecord]) -> tuple[Path, Path]:
    subset = [r for r in records if r.decent_quality]
    p = np.asarray([r.p for r in subset], dtype=float)
    n = np.asarray([r.n for r in subset], dtype=float)
    p0 = float(np.mean(p))
    n0 = float(np.mean(n))
    dp = p - p0
    dn = n - n0
    X = design_matrix(dp, dn)

    coeff_rows: list[dict[str, float | str]] = []
    fig, axes = plt.subplots(3, 3, figsize=(14, 11), constrained_layout=True)
    for ax, key in zip(axes.flat, FEATURE_KEYS):
        y = np.asarray([feature_value(r, key) for r in subset], dtype=float)
        finite = np.isfinite(y) & (y > 0.0)
        if np.count_nonzero(finite) < 8:
            ax.set_title(f"{key}: insufficient points")
            ax.axis("off")
            continue
        use_log = True
        if key == "width_peak_wall_dex":
            # Width can be exactly zero in some runs.
            yfit = np.log10(y[finite] + 1e-6)
        else:
            yfit = np.log10(y[finite]) if use_log else y[finite]
        Xf = X[finite]
        cf, *_ = np.linalg.lstsq(Xf, yfit, rcond=None)
        yhat = Xf @ cf
        rms = float(np.sqrt(np.mean((yfit - yhat) ** 2)))
        ax.plot(yfit, yhat, "o")
        lo = float(min(np.min(yfit), np.min(yhat)))
        hi = float(max(np.max(yfit), np.max(yhat)))
        ax.plot([lo, hi], [lo, hi], "k--", lw=1.0)
        ax.set_title(f"{key} (RMS={rms:.3g} dex)")
        ax.set_xlabel("measured log10")
        ax.set_ylabel("fitted log10")
        ax.grid(True, alpha=0.25)

        coeff_rows.append(
            {
                "feature": key,
                "p0": p0,
                "n0": n0,
                "a0": cf[0],
                "a1": cf[1],
                "a2": cf[2],
                "a3": cf[3],
                "a4": cf[4],
                "a5": cf[5],
                "a6": cf[6],
                "a7": cf[7],
                "rms_dex": rms,
            }
        )
    out_plot = PLOT_DIR / "allP_global_feature_surface_pred_vs_measured.png"
    fig.savefig(out_plot, dpi=220)
    plt.close(fig)

    out_csv = TABLE_DIR / "allP_global_feature_surface_coefficients.csv"
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["feature", "p0", "n0", "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "rms_dex"],
        )
        w.writeheader()
        for row in coeff_rows:
            w.writerow(row)
    return out_csv, out_plot


def registered_coordinate(logx: np.ndarray, log_x_ts: float, log_x_outer: float) -> np.ndarray:
    span = log_x_outer - log_x_ts
    if span <= 0.0:
        raise ValueError("registration span must be > 0")
    return (logx - log_x_ts) / span


def make_registered_table(records: list[RunRecord], z_points: int = 1200) -> tuple[np.ndarray, np.ndarray]:
    z_min = +1e30
    z_max = -1e30
    for r in records:
        z = registered_coordinate(np.log10(r.x), np.log10(r.x_ts), np.log10(r.x_final_rise))
        z_min = min(z_min, float(np.min(z)))
        z_max = max(z_max, float(np.max(z)))
    z_grid = np.linspace(z_min, z_max, z_points)
    table = []
    for r in records:
        z = registered_coordinate(np.log10(r.x), np.log10(r.x_ts), np.log10(r.x_final_rise))
        ly = np.log10(np.maximum(r.y, 1e-300))
        table.append(np.interp(z_grid, z, ly, left=ly[0], right=ly[-1]))
    return z_grid, np.asarray(table, dtype=float)


def predict_profile(
    p_query: float,
    n_query: float,
    x_query: np.ndarray,
    records: list[RunRecord],
    z_grid: np.ndarray,
    logy_table: np.ndarray,
) -> np.ndarray:
    recs = sorted(records, key=lambda r: (r.p, r.n))
    unique_p = sorted({r.p for r in recs})
    if len(unique_p) < 2:
        raise RuntimeError("need at least two pressure slices")

    ly_per_p: dict[int, np.ndarray] = {}
    lxts_per_p: dict[int, float] = {}
    lxouter_per_p: dict[int, float] = {}

    for p0 in unique_p:
        sub_idx = [i for i, r in enumerate(recs) if r.p == p0]
        sub = [recs[i] for i in sub_idx]
        n_train = np.asarray([r.n for r in sub], dtype=float)
        order = np.argsort(n_train)
        n_train = n_train[order]
        row_idx = [sub_idx[i] for i in order]
        ly_rows = logy_table[row_idx, :]
        lxts_train = np.log10(np.asarray([sub[i].x_ts for i in order], dtype=float))
        lxouter_train = np.log10(np.asarray([sub[i].x_final_rise for i in order], dtype=float))

        ly_interp = np.array([pchip_eval(n_train, ly_rows[:, j], n_query) for j in range(logy_table.shape[1])], dtype=float)
        ly_per_p[p0] = ly_interp
        lxts_per_p[p0] = float(pchip_eval(n_train, lxts_train, n_query))
        lxouter_per_p[p0] = float(pchip_eval(n_train, lxouter_train, n_query))

    p_train = np.asarray(unique_p, dtype=float)
    ly_stack = np.vstack([ly_per_p[p0] for p0 in unique_p])
    lxts_stack = np.asarray([lxts_per_p[p0] for p0 in unique_p], dtype=float)
    lxouter_stack = np.asarray([lxouter_per_p[p0] for p0 in unique_p], dtype=float)

    ly_q = np.array([pchip_eval(p_train, ly_stack[:, j], p_query) for j in range(ly_stack.shape[1])], dtype=float)
    log_x_ts_q = float(pchip_eval(p_train, lxts_stack, p_query))
    log_x_outer_q = float(pchip_eval(p_train, lxouter_stack, p_query))

    z_query = registered_coordinate(np.log10(np.maximum(x_query, 1e-300)), log_x_ts_q, log_x_outer_q)
    ly = np.interp(z_query, z_grid, ly_q, left=ly_q[0], right=ly_q[-1])
    y = 10.0 ** ly
    return despike_log_profile(y, threshold_dex=0.32, max_passes=1)


def predict_profile_single_pressure(
    n_query: float,
    x_query: np.ndarray,
    records: list[RunRecord],
    z_grid: np.ndarray,
    logy_table: np.ndarray,
) -> np.ndarray:
    recs = sorted(records, key=lambda r: r.n)
    n_train = np.asarray([r.n for r in recs], dtype=float)
    ly_q = np.array([pchip_eval(n_train, logy_table[:, j], n_query) for j in range(logy_table.shape[1])], dtype=float)
    log_x_ts_q = float(
        pchip_eval(
            n_train,
            np.log10(np.asarray([r.x_ts for r in recs], dtype=float)),
            n_query,
        )
    )
    log_x_outer_q = float(
        pchip_eval(
            n_train,
            np.log10(np.asarray([r.x_final_rise for r in recs], dtype=float)),
            n_query,
        )
    )
    z_query = registered_coordinate(np.log10(np.maximum(x_query, 1e-300)), log_x_ts_q, log_x_outer_q)
    ly = np.interp(z_query, z_grid, ly_q, left=ly_q[0], right=ly_q[-1])
    y = 10.0 ** ly
    return despike_log_profile(y, threshold_dex=0.32, max_passes=1)


def log_residual_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    m = np.isfinite(y_true) & np.isfinite(y_pred) & (y_true > 0.0) & (y_pred > 0.0)
    if np.count_nonzero(m) < 8:
        return float("nan"), float("nan")
    resid = np.log10(y_pred[m]) - np.log10(y_true[m])
    return float(np.sqrt(np.mean(resid**2))), float(np.median(np.abs(resid)))


def evaluate_surrogate(records: list[RunRecord]) -> tuple[Path, Path, Path]:
    recs = sorted([r for r in records if r.decent_quality], key=lambda r: (r.p, r.n))
    z_grid, table = make_registered_table(recs)

    # Training reconstruction (all profiles in table).
    train_rows: list[dict[str, float | str]] = []
    fig, axes = plt.subplots(3, 4, figsize=(15, 10), constrained_layout=True)
    for ax, r in zip(axes.flat, recs):
        y_model = predict_profile(float(r.p), float(r.n), r.x, recs, z_grid, table)
        rms, mad = log_residual_metrics(r.y, y_model)
        train_rows.append({"run_id": r.run_id, "rms_log10": rms, "mad_log10": mad})
        ax.plot(r.x, r.y, lw=1.8, label="AMRVAC")
        ax.plot(r.x, y_model, lw=1.4, ls="--", label="ad-hoc surrogate")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"{r.run_id}  RMS={rms:.3g}, MAD={mad:.3g}")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=7)
    for ax in axes.flat[len(recs) :]:
        ax.axis("off")
    out_train_plot = PLOT_DIR / "allP_surrogate_training_overlay.png"
    fig.savefig(out_train_plot, dpi=220)
    plt.close(fig)

    # Leave-one-out by run.
    loo_rows: list[dict[str, float | str]] = []
    fig2, axes2 = plt.subplots(3, 4, figsize=(15, 10), constrained_layout=True)
    for ax, r in zip(axes2.flat, recs):
        others = [o for o in recs if o.run_id != r.run_id]
        z_loo, table_loo = make_registered_table(others)
        y_loo = predict_profile(float(r.p), float(r.n), r.x, others, z_loo, table_loo)
        rms, mad = log_residual_metrics(r.y, y_loo)
        loo_rows.append({"run_id": r.run_id, "rms_log10": rms, "mad_log10": mad})
        ax.plot(r.x, r.y, lw=1.8, label="AMRVAC")
        ax.plot(r.x, y_loo, lw=1.4, ls="--", label="LOO surrogate")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"{r.run_id}  LOO RMS={rms:.3g}, MAD={mad:.3g}")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=7)
    for ax in axes2.flat[len(recs) :]:
        ax.axis("off")
    out_loo_plot = PLOT_DIR / "allP_surrogate_leave_one_out_overlay.png"
    fig2.savefig(out_loo_plot, dpi=220)
    plt.close(fig2)

    train_csv = TABLE_DIR / "allP_surrogate_training_metrics.csv"
    with train_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["run_id", "rms_log10", "mad_log10"])
        w.writeheader()
        for row in train_rows:
            w.writerow(row)

    loo_csv = TABLE_DIR / "allP_surrogate_loo_metrics.csv"
    with loo_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["run_id", "rms_log10", "mad_log10"])
        w.writeheader()
        for row in loo_rows:
            w.writerow(row)

    return out_train_plot, out_loo_plot, loo_csv


def evaluate_pressure_slice_surrogates(records: list[RunRecord]) -> tuple[Path, Path]:
    rows: list[dict[str, float | str | int]] = []
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    for ax, p in zip(axes, [4, 5, 6]):
        recs = sorted([r for r in records if r.decent_quality and r.p == p], key=lambda r: r.n)
        z_grid, table = make_registered_table(recs)
        loo_rms = []
        loo_mad = []
        for r in recs:
            others = [o for o in recs if o.run_id != r.run_id]
            z_loo, table_loo = make_registered_table(others)
            y_loo = predict_profile_single_pressure(float(r.n), r.x, others, z_loo, table_loo)
            rms, mad = log_residual_metrics(r.y, y_loo)
            loo_rms.append(rms)
            loo_mad.append(mad)
            rows.append(
                {
                    "pressure_exponent": p,
                    "run_id": r.run_id,
                    "loo_rms_log10": rms,
                    "loo_mad_log10": mad,
                }
            )
        x = np.arange(len(recs))
        ax.plot(x, loo_rms, "o-", label="LOO RMS")
        ax.plot(x, loo_mad, "s--", label="LOO MAD")
        ax.set_xticks(x)
        ax.set_xticklabels([r.run_id for r in recs], rotation=40, ha="right", fontsize=8)
        ax.set_title(f"Pressure slice p={p}")
        ax.set_ylabel("Dex")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)

    out_plot = PLOT_DIR / "allP_pressure_slice_surrogate_loo_metrics.png"
    fig.savefig(out_plot, dpi=220)
    plt.close(fig)

    out_csv = TABLE_DIR / "allP_pressure_slice_surrogate_loo_metrics.csv"
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["pressure_exponent", "run_id", "loo_rms_log10", "loo_mad_log10"])
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return out_csv, out_plot


def write_report(records: list[RunRecord]) -> Path:
    n_total = len(records)
    n_domain = sum(int(r.domain_issue) for r in records)
    n_res = sum(int(r.resolution_issue) for r in records)
    n_good = sum(int(r.decent_quality) for r in records)

    chosen_not_final = [r for r in records if r.chosen_snapshot != r.final_snapshot]
    lines = [
        "All-pressure AMRVAC quality + feature-fit + surrogate summary",
        "",
        f"Total runs analyzed: {n_total}",
        f"Decent quality runs: {n_good}",
        f"Domain issues flagged: {n_domain}",
        f"Resolution issues flagged: {n_res}",
        "",
        "Snapshot integrity findings:",
        "- Some runs have corrupted final snapshots (inner-domain NaNs).",
        "- For those runs, the analysis uses the latest fully valid snapshot.",
        "",
        "Runs where chosen snapshot != final snapshot:",
    ]
    if chosen_not_final:
        for r in sorted(chosen_not_final, key=lambda z: (z.p, z.n)):
            lines.append(
                f"- {r.run_id}: chosen={r.chosen_snapshot}, final={r.final_snapshot}, "
                f"final_valid_fraction={r.final_valid_fraction:.3f}"
            )
    else:
        lines.append("- none")

    lines += [
        "",
        "Flagged domain issues:",
    ]
    flagged_domain = [r for r in records if r.domain_issue]
    if flagged_domain:
        for r in sorted(flagged_domain, key=lambda z: (z.p, z.n)):
            lines.append(
                f"- {r.run_id}: headroom={r.headroom_ratio:.3f}, "
                f"log10(tail_ratio)={np.log10(max(r.tail_ratio,1e-30)):.3f}, "
                f"tail_slope={r.tail_slope:.3f}"
            )
    else:
        lines.append("- none")

    lines += ["", "Flagged resolution issues:"]
    flagged_res = [r for r in records if r.resolution_issue]
    if flagged_res:
        for r in sorted(flagged_res, key=lambda z: (z.p, z.n)):
            lines.append(
                f"- {r.run_id}: shock_cells={r.shock_cells_12_38:.2f}, "
                f"outer_rise_cells={r.outer_rise_cells:.2f}"
            )
    else:
        lines.append("- none")

    out = REPORT_DIR / "allP_quality_and_model_report.txt"
    out.write_text("\n".join(lines))
    return out


def main() -> None:
    records = build_records()
    outs: list[Path] = []
    outs.append(write_quality_table(records))
    outs.append(plot_profiles(records))
    outs.append(plot_domain_and_resolution(records))
    coeff_csv, _ = fit_pressure_slices(records)
    outs.append(coeff_csv)
    mono_csv, _ = fit_pressure_slices_monotone(records)
    outs.append(mono_csv)
    coeff2d_csv, coeff2d_plot = fit_global_feature_surfaces(records)
    outs.append(coeff2d_csv)
    outs.append(coeff2d_plot)
    out_train, out_loo, out_loo_csv = evaluate_surrogate(records)
    outs.extend([out_train, out_loo, out_loo_csv])
    out_slice_csv, out_slice_plot = evaluate_pressure_slice_surrogates(records)
    outs.extend([out_slice_csv, out_slice_plot])
    outs.append(write_report(records))
    for p in outs:
        print(p)


if __name__ == "__main__":
    main()
