#!/usr/bin/env python3
"""Meeting figures comparing AMRVAC with the two completed analytic laws."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import differential_evolution

import compare_fitting_profiles as base


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "plots" / "bubble_profile_comparison_2026_09_28" / "fit_metrics.csv"
DEFAULT_OUTPUT = ROOT / "plots" / "tuesday_bubble_comparison_2026_09_29"
GREEN = "#14795e"
PALE_GREEN = "#82aa9a"
ORANGE = "#d56b1d"


def anchored_simple(radius: np.ndarray, target: np.ndarray, rt: float, nism: float):
    log_target = np.log10(target)

    def objective(values):
        density, _ = base.simple_density(radius, rt, 10 ** values[0], nism)
        return float(np.mean((np.log10(density) - log_target) ** 2))

    attempts = [differential_evolution(objective, [(np.log10(nism) - 6, np.log10(nism) + 2)],
                                       seed=20260929 + i, maxiter=120, popsize=12,
                                       tol=1e-6, polish=True)
                for i in range(3)]
    best = min(attempts, key=lambda result: result.fun)
    nt = 10 ** best.x[0]
    density, r2 = base.simple_density(radius, rt, nt, nism)
    return density, nt, r2, np.sqrt(best.fun)


def load_comparisons(points: int):
    with SOURCE.open(newline="") as handle:
        saved = {(row["run_id"], row["model"]): row for row in csv.DictReader(handle)}
    quality, plan = base.load_rows()
    cases, result_rows = {}, []
    for row in quality:
        run_id = row["run_id"]
        raw_r, raw_rho = base.read_vtu(ROOT / "selected_vtu" / f"{run_id}__{row['chosen_snapshot']}")
        rt_external = float(plan[run_id]["rt_external_pc"]) * base.PC_CM
        ts = float(row["x_ts"]) * rt_external
        wall = float(row["x_final_rise"]) * rt_external
        nism = 10 ** float(row["n"]) / (base.MU * base.MP_G)
        radius, target = base.fitting_grid(raw_r, raw_rho, rt_external, wall, points)
        jonathan = saved[(run_id, "Jonathan simple")]
        ansh = saved[(run_id, "Ansh fixed cavity")]
        j_rt = float(jonathan["rt_pc"]) * base.PC_CM
        j_nt = float(jonathan["nt_cm3"])
        j_curve, j_r2 = base.simple_density(radius, j_rt, j_nt, nism)
        a_outer = float(ansh["R_pole_pc"]) * base.PC_CM
        a_eps = float(ansh["eps"])
        a_curve = base.spheroid_density(radius, a_outer, a_eps, nism, 0.01)
        anchored_curve, anchored_nt, anchored_r2, anchored_rms = anchored_simple(radius, target, ts, nism)
        cases[run_id] = {
            "radius": radius, "target": target, "jonathan": j_curve, "ansh": a_curve,
            "anchored": anchored_curve, "ts": ts, "wall": wall,
            "j_rt": j_rt, "j_r2": j_r2, "a_inner": a_outer * (1 - a_eps), "a_outer": a_outer,
        }
        result_rows.append({
            "run_id": run_id, "amrvac_first_shock_pc": ts / base.PC_CM,
            "amrvac_outer_rise_pc": wall / base.PC_CM,
            "jonathan_fit_rt_pc": j_rt / base.PC_CM,
            "jonathan_fit_r2_pc": j_r2 / base.PC_CM,
            "jonathan_fit_nt_cm3": j_nt,
            "jonathan_fit_rms_dex": float(jonathan["rmse_dex"]),
            "jonathan_anchored_nt_cm3": anchored_nt,
            "jonathan_anchored_r2_pc": anchored_r2 / base.PC_CM,
            "jonathan_anchored_rms_dex": anchored_rms,
            "ansh_fit_inner_wall_pc": a_outer * (1 - a_eps) / base.PC_CM,
            "ansh_fit_outer_wall_pc": a_outer / base.PC_CM,
            "ansh_fit_eps": a_eps,
            "ansh_fixed_ncav_cm3": 0.01,
            "ansh_fit_rms_dex": float(ansh["rmse_dex"]),
        })
    return cases, result_rows


def draw_profile(ax, run_id: str, case: dict, *, annotate: bool = False):
    r_pc = case["radius"] / base.PC_CM
    ax.plot(r_pc, case["target"], color="black", lw=2.2, label="AMRVAC snapshot", zorder=5)
    ax.plot(r_pc, case["jonathan"], color=GREEN, lw=1.7, label="Jonathan: best profile match")
    ax.plot(r_pc, case["anchored"], color=PALE_GREEN, lw=1.5, ls="--",
            label=r"Jonathan: $R_t$ fixed to first shock")
    ax.plot(r_pc, case["ansh"], color=ORANGE, lw=1.7,
            label=r"Ansh: $n_{\rm cav}=0.01$ cm$^{-3}$")
    ax.axvline(case["ts"] / base.PC_CM, color="#717881", ls="--", lw=0.8)
    ax.axvline(case["wall"] / base.PC_CM, color="#717881", ls=":", lw=0.8)
    ax.set(xscale="log", yscale="log", title=run_id, xlabel="Radius [pc]",
           ylabel=r"Equivalent $n=\rho/(1.3m_p)$ [cm$^{-3}$]")
    ax.grid(alpha=0.16, which="both")
    if annotate:
        ax.text(0.02, 0.04, "-- AMRVAC first shock    : AMRVAC outer rise",
                transform=ax.transAxes, fontsize=8)


def save(fig, output: Path):
    fig.savefig(output.with_suffix(".png"), dpi=180)
    fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)


def profile_pages(cases: dict, outdir: Path):
    fig, axes = plt.subplots(3, 1, figsize=(8.0, 11.0))
    for ax, run_id in zip(axes, ("p4_n22", "p5_n21", "p6_n19")):
        draw_profile(ax, run_id, cases[run_id], annotate=True)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=2, fontsize=8)
    fig.subplots_adjust(left=0.14, right=0.98, bottom=0.07, top=0.90, hspace=0.38)
    save(fig, outdir / "representative_profiles")

    for pressure in ("p4", "p5", "p6"):
        ids = sorted(rid for rid in cases if rid.startswith(pressure + "_"))
        fig, axes = plt.subplots(2, 2, figsize=(10.2, 10.3))
        for ax, run_id in zip(axes.flat, ids):
            draw_profile(ax, run_id, cases[run_id])
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=2, fontsize=8)
        fig.subplots_adjust(left=0.11, right=0.98, bottom=0.09, top=0.86, hspace=0.34, wspace=0.29)
        save(fig, outdir / f"{pressure}_profiles")


def summary_page(rows: list[dict], outdir: Path):
    ids = [row["run_id"] for row in rows]
    x = np.arange(len(ids))
    fig, ax = plt.subplots(figsize=(10.5, 4.1), constrained_layout=True)
    ax.bar(x - 0.22, [row["jonathan_fit_rms_dex"] for row in rows], 0.29,
           color=GREEN, label="Jonathan: best profile match")
    ax.bar(x + 0.1, [row["ansh_fit_rms_dex"] for row in rows], 0.29,
           color=ORANGE, label="Ansh: fixed cavity")
    ax.set_xticks(x, ids, rotation=45, ha="right")
    ax.set_ylabel("RMS log-density residual [dex]")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.18)
    ax.legend(fontsize=8)
    save(fig, outdir / "all_12_residuals")


def radius_map(rows: list[dict], outdir: Path):
    ids = [row["run_id"] for row in rows]
    y = np.arange(len(ids))[::-1]
    fig, ax = plt.subplots(figsize=(10.2, 6.2), constrained_layout=True)
    for ordinate, row in zip(y, rows):
        ax.plot([row["amrvac_first_shock_pc"], row["amrvac_outer_rise_pc"]],
                [ordinate, ordinate], color="#c6cbd0", lw=2, zorder=1)
        ax.plot([row["ansh_fit_inner_wall_pc"], row["ansh_fit_outer_wall_pc"]],
                [ordinate + 0.13, ordinate + 0.13], color="#edc09d", lw=3, zorder=1)
    ax.scatter([row["amrvac_first_shock_pc"] for row in rows], y, color="black", marker="o",
               s=31, label="AMRVAC first shock", zorder=4)
    ax.scatter([row["amrvac_outer_rise_pc"] for row in rows], y, color="black", marker="^",
               s=37, label="AMRVAC outer rise", zorder=4)
    ax.scatter([row["jonathan_fit_rt_pc"] for row in rows], y - 0.13, color=GREEN,
               marker="D", s=31, label=r"Jonathan fitted $R_t$", zorder=4)
    ax.scatter([row["ansh_fit_inner_wall_pc"] for row in rows], y + 0.13, color=ORANGE,
               marker="s", s=30, label="Ansh inner wall", zorder=4)
    ax.scatter([row["ansh_fit_outer_wall_pc"] for row in rows], y + 0.13, color=ORANGE,
               marker="^", s=35, label=r"Ansh fitted $R_{\rm pole}$", zorder=4)
    ax.set(xscale="log", xlabel="Radius [pc]", yticks=y, yticklabels=ids,
           title="Different fit radii identify different bubble boundaries")
    ax.set_ylim(-0.7, max(y) + 0.7)
    ax.grid(axis="x", alpha=0.2, which="both")
    ax.legend(loc="lower right", fontsize=8, ncol=2)
    save(fig, outdir / "radius_correspondence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not SOURCE.is_file():
        parser.error(f"Run compare_fitting_profiles.py first; missing {SOURCE}")
    args.outdir.mkdir(parents=True, exist_ok=True)
    cases, rows = load_comparisons(points=256)
    profile_pages(cases, args.outdir)
    summary_page(rows, args.outdir)
    radius_map(rows, args.outdir)
    with (args.outdir / "meeting_fit_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved Tuesday figures and metrics under {args.outdir}")


if __name__ == "__main__":
    main()
