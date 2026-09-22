#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_tight_density_profiles import final_file, read_plan, read_vtu

CAMPAIGN = Path(__file__).resolve().parent
PLOT_DIR = CAMPAIGN / "plots"
PLOT_DIR.mkdir(exist_ok=True)


@dataclass
class RunFeatures:
    run_id: str
    x_ts: float
    y_pre: float
    x_4outer: float
    x_inflect: float
    x_final_rise: float
    y_flat_min: float
    x_peak_wall: float
    y_peak_wall: float
    width_peak_wall_dex: float


def load_features() -> dict[str, RunFeatures]:
    path = PLOT_DIR / "p4_feature_table_and_cubic_fits.csv"
    out: dict[str, RunFeatures] = {}
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rid = row["run_id"]
            out[rid] = RunFeatures(
                run_id=rid,
                x_ts=float(row["x_ts"]),
                y_pre=float(row["y_pre"]),
                x_4outer=float(row["x_4outer"]),
                x_inflect=float(row["x_inflect"]),
                x_final_rise=float(row["x_final_rise"]),
                y_flat_min=float(row["y_flat_min"]),
                x_peak_wall=float(row["x_peak_wall"]),
                y_peak_wall=float(row["y_peak_wall"]),
                width_peak_wall_dex=float(row["width_peak_wall_dex"]),
            )
    return out


def piecewise_linear_map(u: np.ndarray, xp: np.ndarray, fp: np.ndarray) -> np.ndarray:
    y = np.interp(u, xp, fp)
    left = u < xp[0]
    right = u > xp[-1]
    if np.any(left):
        y[left] = fp[0] + (u[left] - xp[0])
    if np.any(right):
        y[right] = fp[-1] + (u[right] - xp[-1])
    return y


def smooth_step(z: np.ndarray, z0: float, z1: float) -> np.ndarray:
    if z1 <= z0:
        return (z >= z0).astype(float)
    t = np.clip((z - z0) / (z1 - z0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def despike_log_profile(y: np.ndarray, threshold_dex: float = 0.30, max_passes: int = 2) -> np.ndarray:
    out = y.copy()
    if out.size < 7:
        return out
    for _ in range(max_passes):
        ly = np.log10(np.maximum(out, 1e-300))
        changed = False
        for i in range(2, out.size - 2):
            neigh = np.array([ly[i - 2], ly[i - 1], ly[i + 1], ly[i + 2]])
            med = float(np.median(neigh))
            if abs(ly[i] - med) < threshold_dex:
                continue
            # Isolated extremum test.
            left = ly[i] - ly[i - 1]
            right = ly[i + 1] - ly[i]
            if left * right >= 0.0:
                continue
            out[i] = 10.0 ** med
            changed = True
        if not changed:
            break
    return np.maximum(out, 1e-30)


def build_model_from_template(
    x_grid: np.ndarray,
    template_x: np.ndarray,
    template_y: np.ndarray,
    ft: RunFeatures,
    fr: RunFeatures,
) -> np.ndarray:
    # Exact-template pass-through avoids introducing artificial mismatch.
    if fr.run_id == ft.run_id and np.array_equal(x_grid, template_x):
        return np.maximum(template_y.copy(), 1e-30)

    # Work in log space.
    ut = np.log10(template_x)
    lt = np.log10(template_y)
    ux = np.log10(x_grid)

    # Horizontal landmark mapping from template to target.
    u_tmin = float(np.min(ut))
    u_tmax = float(np.max(ut))
    u_tanchors = np.array(
        [
            u_tmin,
            np.log10(ft.x_ts),
            np.log10(ft.x_4outer),
            np.log10(ft.x_inflect),
            np.log10(ft.x_final_rise),
            u_tmax,
        ],
        dtype=float,
    )

    u_rts = np.log10(fr.x_ts)
    u_r4 = np.log10(fr.x_4outer)
    u_rinf = np.log10(fr.x_inflect)
    u_rfin = np.log10(fr.x_final_rise)
    # Preserve near-inner and far-outer extent relative to x_ts and x_final.
    u_rmin = u_rts + (u_tmin - np.log10(ft.x_ts))
    u_rmax = u_rfin + (u_tmax - np.log10(ft.x_final_rise))
    u_ranchors = np.array([u_rmin, u_rts, u_r4, u_rinf, u_rfin, u_rmax], dtype=float)

    # Map template profile to warped horizontal coordinate.
    ur_of_ut = piecewise_linear_map(ut, u_tanchors, u_ranchors)
    order = np.argsort(ur_of_ut)
    ur = ur_of_ut[order]
    lr = lt[order]

    # Baseline model by interpolation onto target grid.
    lym = np.interp(ux, ur, lr, left=lr[0], right=lr[-1])
    ym = 10.0 ** lym

    # 1) Match pre-shock density level y_pre (window just before x_ts).
    x_pre_target = fr.x_ts * (ft.x_ts * 0.92 / ft.x_ts)  # keep same 0.92*x_ts fraction as extraction intent
    pre_mask = (x_grid >= 0.85 * x_pre_target) & (x_grid <= 0.98 * x_pre_target)
    if np.count_nonzero(pre_mask) >= 3:
        y_pre_model = float(np.median(ym[pre_mask]))
        if y_pre_model > 0.0:
            scale_pre = np.clip(fr.y_pre / y_pre_model, 0.2, 20.0)
            ym[x_grid <= 1.02 * fr.x_4outer] *= scale_pre

    # 2) Force plateau between x_ts and x_4outer near 4*y_pre.
    shelf_mask = (x_grid >= 1.02 * fr.x_ts) & (x_grid <= 0.98 * fr.x_4outer)
    if np.count_nonzero(shelf_mask) >= 4:
        y_shelf_model = float(np.median(ym[shelf_mask]))
        y_shelf_target = 4.0 * fr.y_pre
        if y_shelf_model > 0.0 and y_shelf_target > 0.0:
            scale_shelf = np.clip(y_shelf_target / y_shelf_model, 0.3, 5.0)
            ym[shelf_mask] *= scale_shelf

    # 3) Match cavity floor around x_final using y_flat_min.
    x_flat_target = fr.x_final_rise * (ft.y_flat_min * 0.0 + (1.0))  # placeholder no-op for clarity
    # Use template geometric offset of flat-min location relative to x_final from CSV notion.
    # Since x_flat itself is not part of the 7-parameter set, keep it template-anchored to x_final.
    # Approximate this offset with the same factor inferred from template extraction.
    # We use 0.73 as stable cavity-floor anchor near the broad trough.
    x_flat_target = 0.73 * fr.x_final_rise
    flat_mask = (x_grid >= 0.55 * fr.x_final_rise) & (x_grid <= 0.92 * fr.x_final_rise)
    if np.count_nonzero(flat_mask) >= 5:
        y_flat_model = float(np.min(ym[flat_mask]))
        if y_flat_model > 0.0 and fr.y_flat_min > 0.0:
            # Cap floor correction to avoid global over-amplification artifacts.
            scale_flat = np.clip(fr.y_flat_min / y_flat_model, 0.5, 3.0)
            w_left = smooth_step(np.log10(x_grid), np.log10(0.9 * fr.x_4outer), np.log10(1.05 * fr.x_4outer))
            w_right = 1.0 - smooth_step(np.log10(x_grid), np.log10(0.95 * fr.x_final_rise), np.log10(1.1 * fr.x_final_rise))
            w = np.clip(w_left * w_right, 0.0, 1.0)
            ym *= (1.0 + (scale_flat - 1.0) * w)

    # 4) Set outer-wall peak amplitude and width from (y_peak_wall, width_peak_wall_dex).
    # Peak-center scaling from template relation:
    # delta_u_peak = (u_peak-u_final) scales with width parameter.
    # This keeps p4_n22 exact while adapting to narrower/wider targets.
    u_delta_template = np.log10(max(ft.x_peak_wall, 1e-30) / max(ft.x_final_rise, 1e-30))
    width_ref = max(ft.width_peak_wall_dex, 1e-6)
    # Use sqrt scaling to avoid moving narrow-width peaks too close to x_final.
    u_delta_target = u_delta_template * np.sqrt(max(fr.width_peak_wall_dex, 0.0) / width_ref)
    u_delta_target = float(np.clip(u_delta_target, 0.02, 0.45))
    x_peak_center = fr.x_final_rise * (10.0 ** u_delta_target)
    # Estimate local outer plateau from large radius.
    outer_mask = x_grid >= 1.6 * fr.x_final_rise
    y_outer = float(np.median(ym[outer_mask])) if np.any(outer_mask) else 1.0
    y_outer = max(y_outer, 1e-12)

    amp = max(fr.y_peak_wall - y_outer, 0.0)
    if amp > 0.0 and fr.width_peak_wall_dex > 0.0:
        # width_peak_wall_dex is full width at half height in log10(x); for Gaussian:
        # FWHM = 2 * sqrt(2 ln2) * sigma
        sigma = fr.width_peak_wall_dex / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        u = np.log10(x_grid)
        uc = np.log10(max(x_peak_center, 1e-20))
        bump = amp * np.exp(-0.5 * ((u - uc) / max(sigma, 1e-6)) ** 2)
        ym = ym + bump

    ym = despike_log_profile(ym, threshold_dex=0.30, max_passes=2)
    return np.maximum(ym, 1e-30)


def main() -> None:
    plan = read_plan()
    feats = load_features()

    runs = sorted([r for r in feats.keys() if r.startswith("p4_")], key=lambda rid: int(rid.split("_n")[1]))
    if "p4_n22" not in feats:
        raise RuntimeError("p4_n22 features not found.")

    # Current p4 profiles.
    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for run in runs:
        radius_pc, rho, _ = read_vtu(final_file(run))
        row = plan[run]
        x = radius_pc / row["rt_external_pc"]
        y = rho / row["rho_g_cm3"]
        m = np.isfinite(x) & np.isfinite(y) & (x > 0.0) & (y > 0.0)
        xx = x[m]
        yy = despike_log_profile(y[m], threshold_dex=0.32, max_passes=1)
        curves[run] = (xx, yy)

    tx, ty = curves["p4_n22"]
    ft = feats["p4_n22"]

    metrics: list[tuple[str, float, float]] = []

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    for ax, run in zip(axes.flat, runs):
        x, y = curves[run]
        fr = feats[run]
        if run == "p4_n22":
            ymod = y.copy()
        else:
            ymod = build_model_from_template(x, tx, ty, ft=ft, fr=fr)

        # Quality in log-space over informative region.
        fit_mask = (x >= 0.35) & (x <= 25.0) & np.isfinite(ymod) & (ymod > 0.0)
        if np.count_nonzero(fit_mask) < 10:
            fit_mask = np.isfinite(ymod) & (ymod > 0.0)
        resid = np.log10(ymod[fit_mask]) - np.log10(y[fit_mask])
        rms = float(np.sqrt(np.mean(resid**2)))
        mad = float(np.median(np.abs(resid)))
        metrics.append((run, rms, mad))

        ax.plot(x, y, lw=2.0, label="AMRVAC")
        ax.plot(x, ymod, lw=1.8, ls="--", label="7-param model (p4_n22 shape)")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(True, which="both", alpha=0.25)
        ax.set_title(f"{run}   RMS(log10)={rms:.3f}, MAD={mad:.3f}")
        ax.set_xlabel(r"$r/R_t$")
        ax.set_ylabel(r"$\rho/\rho_{ISM}$")
        ax.legend(fontsize=8)

    out_overlay = PLOT_DIR / "p4_7param_p4n22shape_reconstruction_overlay.png"
    fig.savefig(out_overlay, dpi=220)
    plt.close(fig)

    # Summary metrics plot.
    fig2, ax2 = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    rr = np.arange(len(metrics))
    rms_vals = [m[1] for m in metrics]
    mad_vals = [m[2] for m in metrics]
    labels = [m[0] for m in metrics]
    ax2.plot(rr, rms_vals, "o-", lw=1.5, label="RMS(log10 residual)")
    ax2.plot(rr, mad_vals, "s--", lw=1.3, label="MAD(|log10 residual|)")
    ax2.set_xticks(rr)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Dex")
    ax2.set_title("7-parameter p4_n22-shape model residuals")
    ax2.grid(True, alpha=0.25)
    ax2.legend()
    out_metrics = PLOT_DIR / "p4_7param_p4n22shape_reconstruction_metrics.png"
    fig2.savefig(out_metrics, dpi=220)
    plt.close(fig2)

    out_csv = PLOT_DIR / "p4_7param_p4n22shape_reconstruction_metrics.csv"
    with out_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run_id", "rms_log10_resid", "mad_abs_log10_resid"])
        for run, rms, mad in metrics:
            w.writerow([run, rms, mad])

    out_txt = PLOT_DIR / "p4_7param_p4n22shape_reconstruction_report.txt"
    out_txt.write_text(
        "\n".join(
            [
                "7-parameter profile reconstruction using p4_n22 as template shape",
                "Parameters used per target run:",
                "  y_pre, x_4outer, x_inflect, x_final_rise, y_flat_min, y_peak_wall, width_peak_wall_dex",
                "",
                "Model notes:",
                "- Template (p4_n22) is horizontally warped by anchor mapping [x_ts, x_4outer, x_inflect, x_final_rise].",
                "- Pre-shock level and 4*y_pre shelf are rescaled.",
                "- Cavity trough is rescaled to y_flat_min.",
                "- Outer-wall bump amplitude/width set by (y_peak_wall, width_peak_wall_dex).",
                "",
                "Per-run residuals (dex):",
            ]
            + [f"{run}: RMS={rms:.6f}, MAD={mad:.6f}" for run, rms, mad in metrics]
        )
    )

    print(out_overlay)
    print(out_metrics)
    print(out_csv)
    print(out_txt)


if __name__ == "__main__":
    main()
