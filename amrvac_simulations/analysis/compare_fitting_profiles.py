#!/usr/bin/env python3
"""Compare fitting-side bubble density laws to curated AMRVAC snapshots."""

from __future__ import annotations

import argparse
import csv
import re
import struct
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import trapezoid
from scipy.optimize import differential_evolution

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from jetfit.models.empiricalBubbleProfile import (
    empirical_number_density_cm3,
    simple_bubble_outer_radius_cm,
)


ROOT = Path(__file__).resolve().parents[1]
PC_CM = 3.0857e18
MP_G = 1.67262192e-24
MU = 1.3
MODEL_NAMES = ("Jonathan simple", "Jonathan empirical", "Ansh fixed cavity", "Ansh free cavity")
COLORS = {
    "Jonathan simple": "#17765b",
    "Jonathan empirical": "#168fa1",
    "Ansh fixed cavity": "#d16d22",
    "Ansh free cavity": "#d16d22",
}


def read_vtu(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read AMRVAC's appended Float32 rho/point arrays, averaging shared nodes."""
    raw = path.read_bytes()
    app_start = raw.find(b"<AppendedData")
    data_start = raw.find(b"_", app_start) + 1
    data_end = raw.find(b"</AppendedData>", data_start)
    if app_start < 0 or data_start <= app_start or data_end < 0:
        raise ValueError(f"Unsupported VTU appended-data layout: {path}")
    header = raw[:app_start].decode("ascii", "ignore")
    appended = raw[data_start:data_end]
    chunks = []
    for piece in re.finditer(r"<Piece NumberOfPoints=\"\s*(\d+)\".*?</Piece>", header, re.S):
        body = piece.group(0)
        rho_m = re.search(r'Name="rho"[^>]*offset="(\d+)"', body)
        pts_m = re.search(r'<Points>\s*<DataArray[^>]*offset="(\d+)"', body, re.S)
        if rho_m is None or pts_m is None:
            continue
        rho_off, pts_off = int(rho_m.group(1)), int(pts_m.group(1))
        rho_len = struct.unpack_from("<I", appended, rho_off)[0]
        pts_len = struct.unpack_from("<I", appended, pts_off)[0]
        rho = np.frombuffer(appended, dtype="<f4", count=rho_len // 4, offset=rho_off + 4)
        pts = np.frombuffer(appended, dtype="<f4", count=pts_len // 4, offset=pts_off + 4).reshape(-1, 3)
        if len(rho) != len(pts):
            raise ValueError(f"Point/density count mismatch: {path}")
        chunks.append(np.column_stack((pts[:, 0], rho)))
    if not chunks:
        raise ValueError(f"No rho/point arrays: {path}")
    samples = np.concatenate(chunks)
    samples = samples[np.isfinite(samples).all(axis=1) & (samples[:, 0] > 0) & (samples[:, 1] > 0)]
    radii, inverse = np.unique(samples[:, 0], return_inverse=True)
    rho_sum = np.bincount(inverse, weights=samples[:, 1])
    counts = np.bincount(inverse)
    return radii, rho_sum / counts


def simple_density(radius: np.ndarray, rt: float, nt: float, nism: float) -> tuple[np.ndarray, float]:
    r2 = simple_bubble_outer_radius_cm(rt, nt, nism)
    density = np.where(radius < rt, nt * (rt / radius) ** 2, np.where(radius < r2, 4 * nt, nism))
    return density, r2


def empirical_density(radius: np.ndarray, rt: float, nt: float, nism: float) -> tuple[np.ndarray, float]:
    r2 = simple_bubble_outer_radius_cm(rt, nt, nism)
    return empirical_number_density_cm3(radius, rt, nt, nism, r2), r2


def spheroid_density(radius: np.ndarray, r_outer: float, eps: float, nism: float, ncav: float) -> np.ndarray:
    """Ansh's q=1 radial formula, with mu standardized separately below."""
    r_inner = (1 - eps) * r_outer
    nwall = nism / (1 - (1 - eps) ** 3)
    return np.where(radius < r_inner, ncav, np.where(radius <= r_outer, nwall, nism))


def fitting_grid(raw_r: np.ndarray, raw_rho: np.ndarray, rt_external: float, outer_rise: float, points: int):
    lower = max(raw_r[0], 0.25 * rt_external)
    upper = min(raw_r[-1], 3.0 * outer_rise)
    if lower >= upper or lower <= 0:
        raise ValueError("No valid common radial range")
    radius = np.geomspace(lower, upper, points)
    rho = 10 ** np.interp(np.log10(radius), np.log10(raw_r), np.log10(raw_rho))
    return radius, rho / (MU * MP_G)


def fit_profile(name: str, radius: np.ndarray, target: np.ndarray, nism: float, rt: float, wall: float,
                maxiter: int, restarts: int):
    log_target = np.log10(target)
    if name.startswith("Jonathan"):
        bounds = [
            (np.log10(0.25 * rt), np.log10(2.5 * rt)),
            (np.log10(nism) - 6, np.log10(nism) + 2),
        ]

        def unpack(values):
            fit_rt, fit_nt = 10 ** values[0], 10 ** values[1]
            if name == "Jonathan simple":
                density, r2 = simple_density(radius, fit_rt, fit_nt, nism)
            else:
                density, r2 = empirical_density(radius, fit_rt, fit_nt, nism)
            return density, {"rt_pc": fit_rt / PC_CM, "nt_cm3": fit_nt, "r2_pc": r2 / PC_CM}
    else:
        bounds = [(np.log10(0.5 * wall), np.log10(3 * wall)), (0.001, 0.5)]
        if name == "Ansh free cavity":
            bounds.append((np.log10(nism) - 7, np.log10(nism) + 1))

        def unpack(values):
            r_outer, eps = 10 ** values[0], values[1]
            ncav = 10 ** values[2] if name == "Ansh free cavity" else 0.01
            density = spheroid_density(radius, r_outer, eps, nism, ncav)
            return density, {"R_pole_pc": r_outer / PC_CM, "eps": eps, "n_cav_cm3": ncav}

    def objective(values):
        predicted, _ = unpack(values)
        return float(np.mean((np.log10(np.maximum(predicted, 1e-300)) - log_target) ** 2))

    attempts = [differential_evolution(objective, bounds, seed=20260928 + i,
                                       maxiter=maxiter, popsize=12, tol=1e-6, polish=True)
                for i in range(restarts)]
    result = min(attempts, key=lambda attempt: attempt.fun)
    predicted, params = unpack(result.x)
    return predicted, params, float(np.sqrt(objective(result.x)))


def load_rows():
    with (ROOT / "tables" / "allP_run_quality_table.csv").open(newline="") as handle:
        quality = list(csv.DictReader(handle))
    with (ROOT / "tables" / "log_grid_plan.csv").open(newline="") as handle:
        plan = {row["run_id"]: row for row in csv.DictReader(handle)}
    return quality, plan


def make_overlay(cases: dict, output: Path):
    fig, axes = plt.subplots(3, 1, figsize=(8.0, 11.2))
    for ax, run_id in zip(axes, ("p4_n22", "p5_n21", "p6_n19")):
        item = cases[run_id]
        radius_pc = item["radius"] / PC_CM
        ax.plot(radius_pc, item["target"], color="black", lw=2.3, label="AMRVAC selected snapshot", zorder=6)
        for name in MODEL_NAMES:
            ax.plot(radius_pc, item["models"][name], color=COLORS[name], lw=1.5,
                    ls=":" if name == "Ansh free cavity" else "-", label=name)
        ax.axvline(item["ts_pc"], color="#707780", ls="--", lw=0.9)
        ax.axvline(item["wall_pc"], color="#707780", ls=":", lw=0.9)
        ax.set(xscale="log", yscale="log", ylabel=r"Equivalent $n=\rho/(1.3m_p)$ [cm$^{-3}$]",
               title=f"{run_id}: P/k=10^{run_id[1]} K cm^-3")
        ax.grid(alpha=0.16, which="both")
        ax.text(0.02, 0.04, "-- first shock     : outer rise", transform=ax.transAxes, fontsize=8)
    axes[-1].set_xlabel("Radius [pc]")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=2, fontsize=8)
    fig.subplots_adjust(left=0.14, right=0.98, bottom=0.07, top=0.90, hspace=0.39)
    fig.savefig(output.with_suffix(".png"), dpi=180)
    fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)


def make_summary(results: list[dict], output: Path):
    ids = [row["run_id"] for row in results if row["model"] == MODEL_NAMES[0]]
    x = np.arange(len(ids))
    fig, ax = plt.subplots(figsize=(10.5, 4.7), constrained_layout=True)
    for offset, name in zip((-0.27, -0.09, 0.09, 0.27), MODEL_NAMES):
        values = [next(row["rmse_dex"] for row in results if row["run_id"] == rid and row["model"] == name) for rid in ids]
        ax.bar(x + offset, values, 0.18, label=name, color=COLORS[name],
               alpha=0.5 if name == "Ansh free cavity" else 0.9,
               hatch="//" if name == "Ansh free cavity" else None)
    ax.set_xticks(x, ids, rotation=45, ha="right")
    ax.set_ylabel("RMS log-density residual [dex]")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(ncol=2, fontsize=8)
    fig.savefig(output.with_suffix(".png"), dpi=180)
    fig.savefig(output.with_suffix(".pdf"))
    plt.close(fig)


def make_pressure_groups(cases: dict, outdir: Path):
    for pressure in ("p4", "p5", "p6"):
        ids = sorted(run_id for run_id in cases if run_id.startswith(pressure + "_"))
        if len(ids) != 4:
            continue
        fig, axes = plt.subplots(2, 2, figsize=(10.2, 8.6))
        for ax, run_id in zip(axes.flat, ids):
            item = cases[run_id]
            radius_pc = item["radius"] / PC_CM
            ax.plot(radius_pc, item["target"], color="black", lw=2.1,
                    label="AMRVAC selected snapshot", zorder=6)
            for name in MODEL_NAMES:
                ax.plot(radius_pc, item["models"][name], color=COLORS[name], lw=1.4,
                        ls=":" if name == "Ansh free cavity" else "-", label=name)
            ax.axvline(item["ts_pc"], color="#707780", ls="--", lw=0.8)
            ax.axvline(item["wall_pc"], color="#707780", ls=":", lw=0.8)
            ax.set(xscale="log", yscale="log", title=run_id,
                   xlabel="Radius [pc]", ylabel=r"Equivalent $n=\rho/(1.3m_p)$ [cm$^{-3}$]")
            ax.grid(alpha=0.16, which="both")
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=3, fontsize=8)
        fig.subplots_adjust(left=0.11, right=0.98, bottom=0.09, top=0.86, hspace=0.34, wspace=0.29)
        output = outdir / f"{pressure}_profiles"
        fig.savefig(output.with_suffix(".png"), dpi=180)
        fig.savefig(output.with_suffix(".pdf"))
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="*", help="Optional run IDs; default is all 12")
    parser.add_argument("--maxiter", type=int, default=120)
    parser.add_argument("--restarts", type=int, default=3)
    parser.add_argument("--points", type=int, default=256)
    parser.add_argument("--outdir", type=Path, default=ROOT / "plots" / "bubble_profile_comparison_2026_09_28")
    args = parser.parse_args()
    if args.points < 32 or args.maxiter < 1 or args.restarts < 1:
        parser.error("Use at least 32 points, one optimizer iteration, and one restart")
    quality, plan = load_rows()
    known = {row["run_id"] for row in quality}
    selected = set(args.runs) if args.runs else known
    if not selected <= known:
        parser.error(f"Unknown run IDs: {sorted(selected - known)}")
    args.outdir.mkdir(parents=True, exist_ok=True)
    results, cases = [], {}
    for row in quality:
        run_id = row["run_id"]
        if run_id not in selected:
            continue
        chosen = ROOT / "selected_vtu" / f"{run_id}__{row['chosen_snapshot']}"
        raw_r, raw_rho = read_vtu(chosen)
        rt_external = float(plan[run_id]["rt_external_pc"]) * PC_CM
        ts = float(row["x_ts"]) * rt_external
        wall = float(row["x_final_rise"]) * rt_external
        nism = 10 ** float(row["n"]) / (MU * MP_G)
        radius, target = fitting_grid(raw_r, raw_rho, rt_external, wall, args.points)
        curves = {}
        for name in MODEL_NAMES:
            predicted, params, rmse = fit_profile(name, radius, target, nism, ts, wall,
                                                  args.maxiter, args.restarts)
            curves[name] = predicted
            mass_ratio = trapezoid(predicted * radius**2, radius) / trapezoid(target * radius**2, radius)
            results.append({"run_id": run_id, "model": name, "rmse_dex": rmse,
                            "window_mass_ratio": mass_ratio, "nism_cm3": nism,
                            "ts_AMRVAC_pc": ts / PC_CM, "outer_rise_AMRVAC_pc": wall / PC_CM,
                            "radius_min_pc": radius[0] / PC_CM, "radius_max_pc": radius[-1] / PC_CM,
                            **params})
        cases[run_id] = {"radius": radius, "target": target, "models": curves,
                         "ts_pc": ts / PC_CM, "wall_pc": wall / PC_CM}
        print(run_id, " ".join(f"{r['model']}={r['rmse_dex']:.3f}" for r in results[-4:]), flush=True)
    with (args.outdir / "fit_metrics.csv").open("w", newline="") as handle:
        columns = ["run_id", "model", "rmse_dex", "window_mass_ratio", "nism_cm3", "ts_AMRVAC_pc",
                   "outer_rise_AMRVAC_pc", "radius_min_pc", "radius_max_pc", "rt_pc", "nt_cm3",
                   "r2_pc", "R_pole_pc", "eps", "n_cav_cm3"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)
    if {"p4_n22", "p5_n21", "p6_n19"} <= cases.keys():
        make_overlay(cases, args.outdir / "representative_profiles")
    make_pressure_groups(cases, args.outdir)
    make_summary(results, args.outdir / "all_selected_profile_errors")
    print(f"Saved results under {args.outdir}")


if __name__ == "__main__":
    main()
