#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyze_all_pressure_features_and_surrogate import (
    RunRecord,
    build_records,
    log_residual_metrics,
    make_registered_table,
    registered_coordinate,
)
from evaluate_p4_full_profile_density_interpolator import pchip_eval, pchip_slopes
from evaluate_p4n22_7param_model import despike_log_profile

CAMPAIGN = Path(__file__).resolve().parent
ANALYSIS_ROOT = CAMPAIGN / "analysis_allP_20260501"
OUT_ROOT = ANALYSIS_ROOT / "diagnostics_surrogate_alignment"
PLOT_DIR = OUT_ROOT / "plots"
TABLE_DIR = OUT_ROOT / "tables"
REPORT_DIR = OUT_ROOT / "reports"
for p in (PLOT_DIR, TABLE_DIR, REPORT_DIR):
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class PredictionMeta:
    boundary_mode: str
    outside_n_per_pressure_slice: bool
    outside_pressure_grid: bool
    log_x_ts_pred: float
    log_x_outer_pred: float


def _pchip_eval_boundary(x: np.ndarray, y: np.ndarray, xq: float, boundary_mode: str) -> float:
    """
    Evaluate PCHIP interpolation with configurable out-of-range behavior.

    boundary_mode='clamp':
        Hold endpoint value outside the training interval.
    boundary_mode='linear':
        Use endpoint secant extrapolation outside interval.
    """
    if boundary_mode == "clamp":
        return float(pchip_eval(x, y, xq))

    if boundary_mode != "linear":
        raise ValueError(f"unsupported boundary mode: {boundary_mode}")

    xx = np.asarray(x, dtype=float)
    yy = np.asarray(y, dtype=float)
    if len(xx) < 2:
        return float(yy[0])

    if xq <= xx[0]:
        m0 = (yy[1] - yy[0]) / (xx[1] - xx[0])
        return float(yy[0] + m0 * (xq - xx[0]))
    if xq >= xx[-1]:
        m1 = (yy[-1] - yy[-2]) / (xx[-1] - xx[-2])
        return float(yy[-1] + m1 * (xq - xx[-1]))

    # Interior evaluation stays shape-preserving PCHIP.
    k = int(np.searchsorted(xx, xq) - 1)
    h = xx[k + 1] - xx[k]
    t = (xq - xx[k]) / h
    m = pchip_slopes(xx, yy)
    h00 = 2.0 * t**3 - 3.0 * t**2 + 1.0
    h10 = t**3 - 2.0 * t**2 + t
    h01 = -2.0 * t**3 + 3.0 * t**2
    h11 = t**3 - t**2
    return float(h00 * yy[k] + h10 * h * m[k] + h01 * yy[k + 1] + h11 * h * m[k + 1])


def predict_profile_with_meta(
    p_query: float,
    n_query: float,
    x_query: np.ndarray,
    records: list[RunRecord],
    z_grid: np.ndarray,
    logy_table: np.ndarray,
    boundary_mode: str,
) -> tuple[np.ndarray, PredictionMeta]:
    recs = sorted(records, key=lambda r: (r.p, r.n))
    unique_p = sorted({r.p for r in recs})
    if len(unique_p) < 2:
        raise RuntimeError("need at least two pressure slices")

    ly_per_p: dict[int, np.ndarray] = {}
    lxts_per_p: dict[int, float] = {}
    lxouter_per_p: dict[int, float] = {}

    outside_any_n_slice = False
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

        if n_query < n_train[0] or n_query > n_train[-1]:
            outside_any_n_slice = True

        ly_interp = np.array(
            [
                _pchip_eval_boundary(n_train, ly_rows[:, j], n_query, boundary_mode)
                for j in range(logy_table.shape[1])
            ],
            dtype=float,
        )
        ly_per_p[p0] = ly_interp
        lxts_per_p[p0] = float(_pchip_eval_boundary(n_train, lxts_train, n_query, boundary_mode))
        lxouter_per_p[p0] = float(_pchip_eval_boundary(n_train, lxouter_train, n_query, boundary_mode))

    p_train = np.asarray(unique_p, dtype=float)
    ly_stack = np.vstack([ly_per_p[p0] for p0 in unique_p])
    lxts_stack = np.asarray([lxts_per_p[p0] for p0 in unique_p], dtype=float)
    lxouter_stack = np.asarray([lxouter_per_p[p0] for p0 in unique_p], dtype=float)

    outside_p_grid = bool((p_query < p_train[0]) or (p_query > p_train[-1]))
    ly_q = np.array(
        [
            _pchip_eval_boundary(p_train, ly_stack[:, j], p_query, boundary_mode)
            for j in range(ly_stack.shape[1])
        ],
        dtype=float,
    )
    log_x_ts_q = float(_pchip_eval_boundary(p_train, lxts_stack, p_query, boundary_mode))
    log_x_outer_q = float(_pchip_eval_boundary(p_train, lxouter_stack, p_query, boundary_mode))
    if not np.isfinite(log_x_outer_q) or log_x_outer_q <= log_x_ts_q:
        log_x_outer_q = log_x_ts_q + 1e-4

    z_query = registered_coordinate(
        np.log10(np.maximum(x_query, 1e-300)),
        log_x_ts_q,
        log_x_outer_q,
    )
    ly = np.interp(z_query, z_grid, ly_q, left=ly_q[0], right=ly_q[-1])
    y = 10.0 ** ly
    y = despike_log_profile(y, threshold_dex=0.32, max_passes=1)

    meta = PredictionMeta(
        boundary_mode=boundary_mode,
        outside_n_per_pressure_slice=outside_any_n_slice,
        outside_pressure_grid=outside_p_grid,
        log_x_ts_pred=log_x_ts_q,
        log_x_outer_pred=log_x_outer_q,
    )
    return y, meta


def evaluate_mode(records: list[RunRecord], boundary_mode: str) -> tuple[Path, Path]:
    recs = sorted([r for r in records if r.decent_quality], key=lambda r: (r.p, r.n))
    rows: list[dict[str, float | int | str]] = []

    fig, axes = plt.subplots(3, 4, figsize=(15, 10), constrained_layout=True)
    for ax, r in zip(axes.flat, recs):
        others = [o for o in recs if o.run_id != r.run_id]
        z_loo, table_loo = make_registered_table(others)
        y_loo, meta = predict_profile_with_meta(
            p_query=float(r.p),
            n_query=float(r.n),
            x_query=r.x,
            records=others,
            z_grid=z_loo,
            logy_table=table_loo,
            boundary_mode=boundary_mode,
        )
        rms, mad = log_residual_metrics(r.y, y_loo)
        dx_ts = float(meta.log_x_ts_pred - np.log10(r.x_ts))
        dx_outer = float(meta.log_x_outer_pred - np.log10(r.x_final_rise))
        rows.append(
            {
                "run_id": r.run_id,
                "pressure_exponent": r.p,
                "density_exponent": r.n,
                "loo_rms_log10": rms,
                "loo_mad_log10": mad,
                "delta_log10_x_ts": dx_ts,
                "delta_log10_x_outer": dx_outer,
                "outside_n_slice": int(meta.outside_n_per_pressure_slice),
                "outside_p_grid": int(meta.outside_pressure_grid),
                "boundary_mode": boundary_mode,
            }
        )

        flag = "*" if meta.outside_n_per_pressure_slice else ""
        ax.plot(r.x, r.y, lw=1.8, label="AMRVAC")
        ax.plot(r.x, y_loo, lw=1.4, ls="--", label=f"LOO ({boundary_mode})")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(
            f"{r.run_id}{flag}  RMS={rms:.3g}, MAD={mad:.3g}\n"
            f"dlog x_ts={dx_ts:+.2f}, dlog x_out={dx_outer:+.2f}"
        )
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=7)
    for ax in axes.flat[len(recs) :]:
        ax.axis("off")

    fig.suptitle(
        "All-pressure LOO surrogate diagnostics "
        f"({boundary_mode} boundaries; '*' means query outside a pressure-slice n range)",
        fontsize=13,
    )
    out_plot = PLOT_DIR / f"allP_surrogate_leave_one_out_overlay_{boundary_mode}.png"
    fig.savefig(out_plot, dpi=220)
    plt.close(fig)

    out_csv = TABLE_DIR / f"allP_surrogate_loo_alignment_{boundary_mode}.csv"
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "run_id",
                "pressure_exponent",
                "density_exponent",
                "loo_rms_log10",
                "loo_mad_log10",
                "delta_log10_x_ts",
                "delta_log10_x_outer",
                "outside_n_slice",
                "outside_p_grid",
                "boundary_mode",
            ],
        )
        w.writeheader()
        for row in rows:
            w.writerow(row)

    return out_plot, out_csv


def compare_modes(csv_clamp: Path, csv_linear: Path) -> tuple[Path, Path]:
    def read_rows(path: Path) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        with path.open() as fh:
            rr = csv.DictReader(fh)
            for row in rr:
                rid = row["run_id"]
                out[rid] = {
                    "rms": float(row["loo_rms_log10"]),
                    "mad": float(row["loo_mad_log10"]),
                    "dts": float(row["delta_log10_x_ts"]),
                    "dou": float(row["delta_log10_x_outer"]),
                    "outside": float(row["outside_n_slice"]),
                }
        return out

    clamp = read_rows(csv_clamp)
    linear = read_rows(csv_linear)
    run_ids = sorted(clamp.keys(), key=lambda rid: (int(rid[1]), -int(rid.split("_n")[1])))

    rows: list[dict[str, float | str | int]] = []
    for rid in run_ids:
        c = clamp[rid]
        l = linear[rid]
        rows.append(
            {
                "run_id": rid,
                "outside_n_slice": int(c["outside"]),
                "rms_clamp": c["rms"],
                "rms_linear": l["rms"],
                "delta_rms_linear_minus_clamp": l["rms"] - c["rms"],
                "mad_clamp": c["mad"],
                "mad_linear": l["mad"],
                "delta_mad_linear_minus_clamp": l["mad"] - c["mad"],
            }
        )

    out_csv = TABLE_DIR / "allP_surrogate_mode_comparison.csv"
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "run_id",
                "outside_n_slice",
                "rms_clamp",
                "rms_linear",
                "delta_rms_linear_minus_clamp",
                "mad_clamp",
                "mad_linear",
                "delta_mad_linear_minus_clamp",
            ],
        )
        w.writeheader()
        for row in rows:
            w.writerow(row)

    x = np.arange(len(rows))
    fig, axes = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True, constrained_layout=True)
    axes[0].plot(x, [row["rms_clamp"] for row in rows], "o-", label="clamp")
    axes[0].plot(x, [row["rms_linear"] for row in rows], "s--", label="linear extrap")
    axes[0].set_ylabel("LOO RMS (dex)")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)

    axes[1].plot(x, [row["mad_clamp"] for row in rows], "o-", label="clamp")
    axes[1].plot(x, [row["mad_linear"] for row in rows], "s--", label="linear extrap")
    axes[1].set_ylabel("LOO MAD (dex)")
    axes[1].set_xlabel("Run")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([row["run_id"] for row in rows], rotation=40, ha="right")

    for i, row in enumerate(rows):
        if int(row["outside_n_slice"]) == 1:
            axes[0].axvspan(i - 0.4, i + 0.4, color="0.85", alpha=0.35, lw=0.0)
            axes[1].axvspan(i - 0.4, i + 0.4, color="0.85", alpha=0.35, lw=0.0)

    out_plot = PLOT_DIR / "allP_surrogate_clamp_vs_linear_metrics.png"
    fig.savefig(out_plot, dpi=220)
    plt.close(fig)
    return out_csv, out_plot


def write_report(csv_mode_compare: Path) -> Path:
    with csv_mode_compare.open() as fh:
        rr = list(csv.DictReader(fh))

    rms_clamp = np.array([float(r["rms_clamp"]) for r in rr], dtype=float)
    rms_linear = np.array([float(r["rms_linear"]) for r in rr], dtype=float)
    mad_clamp = np.array([float(r["mad_clamp"]) for r in rr], dtype=float)
    mad_linear = np.array([float(r["mad_linear"]) for r in rr], dtype=float)
    outside = np.array([int(r["outside_n_slice"]) for r in rr], dtype=int)

    lines = [
        "All-pressure surrogate alignment diagnostics",
        "",
        "Goal:",
        "- Diagnose why leave-one-out overlays show similar morphology but poor radial alignment.",
        "",
        "Main finding:",
        "- Most large LOO failures occur when the queried density lies outside the",
        "  remaining training densities in that pressure slice.",
        "- The old clamp mode then pins the profile to slice endpoints, which shifts",
        "  anchors and distorts the registered profile blend.",
        "",
        f"Mean RMS clamp:  {np.mean(rms_clamp):.4f} dex",
        f"Mean RMS linear: {np.mean(rms_linear):.4f} dex",
        f"Mean MAD clamp:  {np.mean(mad_clamp):.4f} dex",
        f"Mean MAD linear: {np.mean(mad_linear):.4f} dex",
        "",
        f"Outside-slice LOO cases: {int(np.sum(outside))} / {len(outside)}",
        "",
        "Interpretation:",
        "- These LOO edge failures are mostly extrapolation diagnostics, not pure",
        "  interpolation diagnostics.",
        "- Interior points are generally much more stable.",
    ]
    out = REPORT_DIR / "allP_surrogate_alignment_report.txt"
    out.write_text("\n".join(lines))
    return out


def main() -> None:
    records = build_records()
    out_clamp_plot, out_clamp_csv = evaluate_mode(records, boundary_mode="clamp")
    out_linear_plot, out_linear_csv = evaluate_mode(records, boundary_mode="linear")
    out_cmp_csv, out_cmp_plot = compare_modes(out_clamp_csv, out_linear_csv)
    out_report = write_report(out_cmp_csv)

    for path in [out_clamp_plot, out_clamp_csv, out_linear_plot, out_linear_csv, out_cmp_csv, out_cmp_plot, out_report]:
        print(path)


if __name__ == "__main__":
    main()

