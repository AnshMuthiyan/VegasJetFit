#!/usr/bin/env python3
"""
Analyze pressure-regulated AMRVAC bubble runs.

The campaign directories are named pressure_p{Pexp}_n{Nexp}; each contains
output/Ostar_1D/test*.vtu.  This script uses the last VTU snapshot, plots the
final radial density profiles, and estimates whether the disturbed bubble
structure is comfortably inside the computational box.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze_amrvac_bubble_profiles import M_MOL, PC_TO_CM, TINY, read_vtu_snapshot


RUN_RE = re.compile(r"pressure_p(?P<pexp>\d+)_n(?P<nexp>\d+)")


@dataclass(frozen=True)
class PlanRow:
    run_id: str
    pressure_exponent: int
    density_exponent: int
    pressure_k_cm3: float
    rho_g_cm3: float
    nism_cm3: float
    tism_k: float
    predicted_outer_radius_pc: float
    xprobmax1_pc: float
    domain_nx1: int


def read_plan(path: Path) -> dict[str, PlanRow]:
    rows: dict[str, PlanRow] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            rows[row["run_id"]] = PlanRow(
                run_id=row["run_id"],
                pressure_exponent=int(row["pressure_exponent"]),
                density_exponent=int(row["density_exponent"]),
                pressure_k_cm3=float(row["pressure_k_cm3"]),
                rho_g_cm3=float(row["rho_g_cm3"]),
                nism_cm3=float(row["nism_cm3"]),
                tism_k=float(row["tism_k"]),
                predicted_outer_radius_pc=float(row["outer_radius_pc"]),
                xprobmax1_pc=float(row["xprobmax1_pc"]),
                domain_nx1=int(row["domain_nx1"]),
            )
    return rows


def run_id_from_dir(run_dir: Path) -> str:
    match = RUN_RE.fullmatch(run_dir.name)
    if not match:
        raise ValueError(f"Unexpected pressure-grid run directory: {run_dir.name}")
    return f"p{match.group('pexp')}_n{match.group('nexp')}"


def collect_snapshots(campaign_dir: Path, plan: dict[str, PlanRow]):
    snapshots = []
    skipped = []
    for run_dir in sorted(campaign_dir.glob("pressure_p*_n*")):
        if not run_dir.is_dir():
            continue
        run_id = run_id_from_dir(run_dir)
        vtus = sorted((run_dir / "output" / "Ostar_1D").glob("test*.vtu"))
        if not vtus:
            skipped.append(f"{run_id}: no VTU snapshots")
            continue
        if run_id not in plan:
            skipped.append(f"{run_id}: not in pressure_box_plan.csv")
            continue
        snapshots.append((run_id, plan[run_id], read_vtu_snapshot(vtus[-1])))
    snapshots.sort(key=lambda item: (item[1].pressure_exponent, item[1].density_exponent))
    return snapshots, skipped


def smooth_log_profile(log_y: np.ndarray, window: int = 7) -> np.ndarray:
    if len(log_y) < window:
        return log_y
    kernel = np.ones(window, dtype=float) / float(window)
    pad = window // 2
    padded = np.pad(log_y, pad_width=pad, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def estimate_disturbed_outer_radius(radius_pc: np.ndarray, n_cm3: np.ndarray, nism_cm3: float) -> dict[str, float]:
    """Find the last radius that is measurably away from the ambient plateau."""
    log_ratio = np.log10(np.maximum(n_cm3, TINY) / max(nism_cm3, TINY))
    smoothed = smooth_log_profile(log_ratio)
    threshold_dex = 0.05
    disturbed = np.where(np.abs(smoothed) > threshold_dex)[0]
    if disturbed.size:
        idx = int(disturbed[-1])
        r_outer_pc = float(radius_pc[idx])
    else:
        idx = 0
        r_outer_pc = float(radius_pc[0])

    n_tail = max(5, int(0.05 * len(radius_pc)))
    edge_deviation_dex = float(np.nanmedian(np.abs(log_ratio[-n_tail:])))
    edge_slope_dex_per_dex = float(
        np.nanmedian(np.abs(np.gradient(smoothed[-n_tail:], np.log10(radius_pc[-n_tail:]))))
    )
    return {
        "measured_outer_pc": r_outer_pc,
        "measured_outer_index": idx,
        "edge_deviation_dex": edge_deviation_dex,
        "edge_slope_dex_per_dex": edge_slope_dex_per_dex,
    }


def analyze_snapshot(run_id: str, plan: PlanRow, snapshot, rwind_pc: float) -> dict[str, float | int | str]:
    radius_pc = snapshot.radius_cm / PC_TO_CM
    n_cm3 = snapshot.number_density_cm3
    outer = estimate_disturbed_outer_radius(radius_pc, n_cm3, plan.nism_cm3)
    measured_outer_pc = outer["measured_outer_pc"]
    first_cell_center_pc = float(0.5 * (radius_pc[0] + radius_pc[1])) if len(radius_pc) > 1 else float(radius_pc[0])
    first_cell_width_pc = float(radius_pc[1] - radius_pc[0]) if len(radius_pc) > 1 else float("nan")
    return {
        "run_id": run_id,
        "pressure_exponent": plan.pressure_exponent,
        "density_exponent": plan.density_exponent,
        "pressure_k_cm3": plan.pressure_k_cm3,
        "rho_g_cm3": plan.rho_g_cm3,
        "nism_cm3": plan.nism_cm3,
        "tism_k": plan.tism_k,
        "snapshot": snapshot.path.name,
        "time_code": snapshot.time_code,
        "r_min_pc": float(radius_pc.min()),
        "r_max_pc": float(radius_pc.max()),
        "first_cell_center_pc": first_cell_center_pc,
        "first_cell_width_pc": first_cell_width_pc,
        "rwind_pc": rwind_pc,
        "first_cell_center_minus_rwind_pc": first_cell_center_pc - rwind_pc,
        "wind_injection_cell_present": "yes" if first_cell_center_pc < rwind_pc else "no",
        "n_first_over_nism": float(n_cm3[0] / max(plan.nism_cm3, TINY)),
        "n_min_over_nism": float(np.nanmin(n_cm3) / max(plan.nism_cm3, TINY)),
        "n_max_over_nism": float(np.nanmax(n_cm3) / max(plan.nism_cm3, TINY)),
        "predicted_outer_radius_pc": plan.predicted_outer_radius_pc,
        "measured_outer_pc": measured_outer_pc,
        "measured_outer_box_fraction": measured_outer_pc / max(float(radius_pc.max()), TINY),
        "predicted_outer_box_fraction": plan.predicted_outer_radius_pc / max(float(radius_pc.max()), TINY),
        "headroom_pc": float(radius_pc.max()) - measured_outer_pc,
        "headroom_factor": float(radius_pc.max()) / max(measured_outer_pc, TINY),
        "measured_over_predicted": measured_outer_pc / max(plan.predicted_outer_radius_pc, TINY),
        "edge_deviation_dex": outer["edge_deviation_dex"],
        "edge_slope_dex_per_dex": outer["edge_slope_dex_per_dex"],
    }


def write_csv(rows: list[dict[str, float | int | str]], path: Path) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_profiles_by_pressure(items, summary_by_run: dict[str, dict[str, float | int | str]], output_path: Path) -> None:
    pressures = sorted({plan.pressure_exponent for _, plan, _ in items})
    fig, axes = plt.subplots(len(pressures), 1, figsize=(10, 4.0 * len(pressures)), sharex=False)
    if len(pressures) == 1:
        axes = [axes]

    cmap = plt.get_cmap("viridis")
    for ax, pexp in zip(axes, pressures):
        group = [(run_id, plan, snap) for run_id, plan, snap in items if plan.pressure_exponent == pexp]
        for j, (run_id, plan, snap) in enumerate(group):
            color = cmap(j / max(len(group) - 1, 1))
            radius_pc = snap.radius_cm / PC_TO_CM
            n_cm3 = snap.number_density_cm3
            summary = summary_by_run[run_id]
            ax.loglog(radius_pc, n_cm3, color=color, lw=1.8, label=f"{run_id}: nISM={plan.nism_cm3:.2g}")
            ax.axhline(plan.nism_cm3, color=color, ls=":", lw=0.9, alpha=0.55)
            ax.axvline(summary["measured_outer_pc"], color=color, ls="--", lw=0.9, alpha=0.65)
        ax.set_title(f"Final profiles, P/k = 1e{pexp} K cm$^{{-3}}$")
        ax.set_xlabel("Radius (pc)")
        ax.set_ylabel(r"$n(r)$ [cm$^{-3}$]")
        ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_scaled_profiles(items, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=False)
    pressures = sorted({plan.pressure_exponent for _, plan, _ in items})
    cmap = plt.get_cmap("plasma")
    for ax, pexp in zip(axes, pressures):
        group = [(run_id, plan, snap) for run_id, plan, snap in items if plan.pressure_exponent == pexp]
        for j, (run_id, plan, snap) in enumerate(group):
            color = cmap(j / max(len(group) - 1, 1))
            radius_pc = snap.radius_cm / PC_TO_CM
            x = radius_pc / plan.predicted_outer_radius_pc
            y = snap.number_density_cm3 / plan.nism_cm3
            ax.loglog(x, y, color=color, lw=1.6, label=run_id)
        ax.axvline(1.0, color="0.25", lw=1.0, ls="--", label="predicted R")
        ax.axvline(2.5, color="0.35", lw=1.0, ls=":", label="box edge target")
        ax.axhline(1.0, color="0.25", lw=1.0, ls="-.", label="ambient")
        ax.set_title(f"P/k = 1e{pexp}")
        ax.set_xlabel(r"$r / R_{\rm predicted}$")
        ax.set_ylabel(r"$n / n_{\rm ISM}$")
        ax.legend(fontsize=8)
    fig.suptitle("Pressure-grid profiles scaled by predicted outer bubble radius", y=1.02)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_headroom(rows: list[dict[str, float | int | str]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    pressures = sorted({int(row["pressure_exponent"]) for row in rows})
    markers = {4: "o", 5: "s", 6: "^", 7: "D", 8: "P"}
    for pexp in pressures:
        subset = [row for row in rows if int(row["pressure_exponent"]) == pexp]
        subset.sort(key=lambda row: int(row["density_exponent"]))
        x = [int(row["density_exponent"]) for row in subset]
        y = [float(row["measured_outer_box_fraction"]) for row in subset]
        ax.plot(x, y, marker=markers.get(pexp, "o"), lw=1.8, label=f"P/k=1e{pexp}")
    ax.axhline(0.25, color="tab:green", ls="--", lw=1.2, label="ideal 1/4 box")
    ax.axhline(0.40, color="0.35", ls=":", lw=1.2, label="planned 0.4 box")
    ax.set_xlabel(r"Density exponent $N$ in $\rho_{\rm ISM}=10^{-N}$ g cm$^{-3}$")
    ax.set_ylabel("Measured disturbed radius / box radius")
    ax.set_title("Pressure-grid bubble headroom")
    ax.invert_xaxis()
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_wind_injection_resolution(rows: list[dict[str, float | int | str]], output_path: Path) -> None:
    ordered = sorted(rows, key=lambda row: (int(row["pressure_exponent"]), int(row["density_exponent"])))
    labels = [str(row["run_id"]) for row in ordered]
    center_minus_rwind = [float(row["first_cell_center_minus_rwind_pc"]) for row in ordered]
    colors = ["tab:red" if value >= 0.0 else "tab:blue" for value in center_minus_rwind]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(labels, center_minus_rwind, color=colors, alpha=0.8)
    ax.axhline(0.0, color="0.2", lw=1.2)
    ax.set_ylabel("First cell center - Rwind (pc)")
    ax.set_title("Wind injection resolution diagnostic")
    ax.tick_params(axis="x", rotation=45)
    ax.text(
        0.01,
        0.96,
        "Red: no cell center inside Rwind; wind source can be missed.",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox=dict(facecolor="white", edgecolor="0.8", alpha=0.9),
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def write_notes(rows: list[dict[str, float | int | str]], skipped: list[str], output_path: Path) -> None:
    edge_good = [
        str(row["run_id"])
        for row in rows
        if float(row["edge_deviation_dex"]) < 0.02 and float(row["edge_slope_dex_per_dex"]) < 0.1
    ]
    inactive_wind_source = [
        str(row["run_id"]) for row in rows if str(row["wind_injection_cell_present"]) == "no"
    ]
    with output_path.open("w") as handle:
        handle.write(f"Included runs: {len(rows)}\n")
        if skipped:
            handle.write("Skipped runs:\n")
            for item in skipped:
                handle.write(f"- {item}\n")
        handle.write("\nRuns whose first cell center is outside Rwind:\n")
        if inactive_wind_source:
            for run_id in inactive_wind_source:
                handle.write(f"- {run_id}\n")
        else:
            handle.write("- none\n")
        handle.write("\nRuns with clean ambient tail by the simple edge metric:\n")
        if edge_good:
            for run_id in edge_good:
                handle.write(f"- {run_id}\n")
        else:
            handle.write("- none\n")
        handle.write("\nMeasured disturbed-radius summary:\n")
        for row in rows:
            handle.write(
                f"- {row['run_id']}: Rdist/Rbox={float(row['measured_outer_box_fraction']):.3f}, "
                f"Rdist/Rpred={float(row['measured_over_predicted']):.3f}, "
                f"edge deviation={float(row['edge_deviation_dex']):.3g} dex, "
                f"first-cell-center-Rwind={float(row['first_cell_center_minus_rwind_pc']):+.3e} pc\n"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign-dir",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_24_pressure_grid_p4p5p6_boxfactor30_cells6_test",
        help="Directory containing pressure_p*_n* runs.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_pressure_grid_prelim_20260424",
        help="Directory for pressure-grid plots and CSV outputs.",
    )
    parser.add_argument(
        "--rwind-pc",
        type=float,
        default=0.2,
        help="Wind injection radius in pc from mod_usr.t.",
    )
    args = parser.parse_args()

    campaign_dir = Path(args.campaign_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plan = read_plan(campaign_dir / "pressure_box_plan.csv")
    items, skipped = collect_snapshots(campaign_dir, plan)
    if not items:
        raise SystemExit("No pressure-grid snapshots found.")

    rows = [analyze_snapshot(run_id, plan_row, snapshot, args.rwind_pc) for run_id, plan_row, snapshot in items]
    summary_by_run = {str(row["run_id"]): row for row in rows}
    write_csv(rows, output_dir / "pressure_grid_profile_summary.csv")
    plot_profiles_by_pressure(items, summary_by_run, output_dir / "pressure_grid_final_profiles_by_pressure.png")
    plot_scaled_profiles(items, output_dir / "pressure_grid_scaled_by_predicted_radius.png")
    plot_headroom(rows, output_dir / "pressure_grid_headroom.png")
    plot_wind_injection_resolution(rows, output_dir / "pressure_grid_wind_injection_resolution.png")
    write_notes(rows, skipped, output_dir / "analysis_notes.txt")

    print(f"Wrote pressure-grid profile analysis to {output_dir}")


if __name__ == "__main__":
    main()
