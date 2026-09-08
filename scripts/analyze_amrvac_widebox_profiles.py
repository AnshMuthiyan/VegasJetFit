#!/usr/bin/env python3
"""
Analyze the 2026 wide-box AMRVAC runs using the same simple-bubble surrogate
plots as before, plus a fixed-ambient comparison and an outer-wall clearance
summary.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares

from analyze_amrvac_bubble_profiles import (
    M_MOL,
    PC_TO_CM,
    TINY,
    bubble_number_density,
    code_unit_years_from_modusr,
    fit_simple_bubble,
    read_vtu_snapshot,
)


RUN_RE = re.compile(r"density_(\d+)")


def run_density_number(run_name: str) -> int:
    match = RUN_RE.fullmatch(run_name)
    if not match:
        raise ValueError(f"Could not parse density exponent from {run_name!r}")
    return int(match.group(1))


def ambient_number_density_from_run(run_name: str) -> float:
    rho_g_cm3 = 10.0 ** (-run_density_number(run_name))
    return rho_g_cm3 / M_MOL


def collect_final_snapshots(family_dir: Path) -> list:
    snapshots = []
    for run_dir in sorted(p for p in family_dir.glob("density_*") if p.is_dir()):
        vtus = sorted((run_dir / "output" / "Ostar_1D").glob("test*.vtu"))
        if not vtus:
            continue
        snapshots.append(read_vtu_snapshot(vtus[-1]))
    return snapshots


def fit_simple_bubble_fixed_nism(snapshot, nism_cm3: float, code_unit_years: float) -> dict[str, float]:
    radius_cm = snapshot.radius_cm
    number_density_cm3 = np.maximum(snapshot.number_density_cm3, TINY)

    simple = fit_simple_bubble(snapshot, code_unit_years)
    guess = np.log10([simple["rt_cm"], simple["nt_cm3"]])
    lower = np.log10(
        [
            radius_cm.min() * 1.001,
            max(number_density_cm3.min() / 1e3, 1e-12),
        ]
    )
    upper = np.log10(
        [
            radius_cm.max() / 1.001,
            max(number_density_cm3.max() * 1e3, 1e-6),
        ]
    )

    def residual(log_params: np.ndarray) -> np.ndarray:
        rt_cm, nt_cm3 = 10.0 ** log_params
        model_n = bubble_number_density(radius_cm, rt_cm, nt_cm3, nism_cm3)
        return np.log10(np.maximum(model_n, TINY)) - np.log10(number_density_cm3)

    result = least_squares(
        residual,
        x0=np.clip(guess, lower, upper),
        bounds=(lower, upper),
        loss="soft_l1",
        f_scale=0.1,
        max_nfev=2000,
    )
    rt_cm, nt_cm3 = 10.0 ** result.x
    resid = residual(result.x)
    return {
        "rt_cm": rt_cm,
        "rt_pc": rt_cm / PC_TO_CM,
        "nt_cm3": nt_cm3,
        "nism_cm3": nism_cm3,
        "rms_dex": float(np.sqrt(np.mean(resid**2))),
    }


def detect_outer_wall(snapshot) -> dict[str, float]:
    r_pc = snapshot.radius_cm / PC_TO_CM
    log_r = np.log10(r_pc)
    log_n = np.log10(np.maximum(snapshot.number_density_cm3, TINY))
    smooth = gaussian_filter1d(log_n, sigma=4)
    slope = np.gradient(smooth, log_r)

    lo = int(0.15 * len(r_pc))
    hi = int(0.97 * len(r_pc))
    trough_idx = lo + int(np.argmin(smooth[lo:hi]))
    rise_idx = trough_idx + int(np.argmax(slope[trough_idx:hi])) if trough_idx < hi - 1 else hi - 1

    r_max_pc = float(r_pc.max())
    trough_pc = float(r_pc[trough_idx])
    rise_pc = float(r_pc[rise_idx])
    margin_pc = r_max_pc - rise_pc
    return {
        "domain_rmax_pc": r_max_pc,
        "outer_trough_pc": trough_pc,
        "outer_rise_pc": rise_pc,
        "edge_margin_pc": margin_pc,
        "edge_ratio_rmax_over_rise": r_max_pc / max(rise_pc, 1e-30),
    }


def plot_family_raw(snapshots: list, output_path: Path) -> None:
    plt.figure(figsize=(8, 6))
    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        plt.loglog(snapshot.radius_cm / PC_TO_CM, snapshot.number_density_cm3, lw=1.6, label=label)
    plt.xlabel("Radius (pc)")
    plt.ylabel(r"n(r) [cm$^{-3}$]")
    plt.title("Wide-Box AMRVAC Final Density Profiles")
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def plot_family_simple(snapshots: list, simple_fits: dict[str, dict[str, float]], output_path: Path) -> None:
    plt.figure(figsize=(8, 6))
    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        fit = simple_fits[label]
        model_n = bubble_number_density(snapshot.radius_cm, fit["rt_cm"], fit["nt_cm3"], fit["nism_cm3"])
        plt.loglog(snapshot.radius_cm / PC_TO_CM, snapshot.number_density_cm3, lw=1.2, alpha=0.65, label=f"{label} AMRVAC")
        plt.loglog(snapshot.radius_cm / PC_TO_CM, model_n, "--", lw=1.2, alpha=0.95, label=f"{label} simple bubble")
    plt.xlabel("Radius (pc)")
    plt.ylabel(r"n(r) [cm$^{-3}$]")
    plt.title("Wide-Box AMRVAC vs Simple Bubble Fits")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def plot_fixed_nism(snapshot, fit: dict[str, float], wall: dict[str, float], output_path: Path) -> None:
    r_pc = snapshot.radius_cm / PC_TO_CM
    model_n = bubble_number_density(snapshot.radius_cm, fit["rt_cm"], fit["nt_cm3"], fit["nism_cm3"])

    plt.figure(figsize=(8, 6))
    plt.loglog(r_pc, snapshot.number_density_cm3, lw=2.0, label="AMRVAC")
    plt.loglog(r_pc, model_n, "--", lw=1.8, label="Simple bubble (fixed n_ism)")
    plt.axvline(wall["outer_rise_pc"], color="tab:red", ls=":", lw=1.4, label="Outer rise")
    plt.axvline(wall["domain_rmax_pc"], color="0.35", ls="--", lw=1.2, label="Box edge")
    plt.xlim(max(r_pc.min(), 0.08), wall["domain_rmax_pc"] * 1.02)
    plt.xlabel("Radius (pc)")
    plt.ylabel(r"n(r) [cm$^{-3}$]")
    plt.title(f"{snapshot.path.parents[2].name} Wide-Box Fixed Ambient Fit")
    text = (
        f"n_ism = {fit['nism_cm3']:.3g} cm^-3\n"
        f"r_t = {fit['rt_pc']:.3f} pc\n"
        f"outer rise = {wall['outer_rise_pc']:.3f} pc\n"
        f"edge margin = {wall['edge_margin_pc']:.3f} pc\n"
        f"RMS = {fit['rms_dex']:.3f} dex"
    )
    plt.text(0.03, 0.03, text, transform=plt.gca().transAxes, fontsize=9, va="bottom",
             bbox=dict(facecolor="white", alpha=0.85, edgecolor="0.8"))
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()


def plot_fixed_nism_overview(
    snapshots: list,
    fixed_fits: dict[str, dict[str, float]],
    walls: dict[str, dict[str, float]],
    output_path: Path,
) -> None:
    n = len(snapshots)
    cols = 2
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(12, 4.4 * rows), squeeze=False)
    for ax, snapshot in zip(axes.ravel(), snapshots):
        label = snapshot.path.parents[2].name
        fit = fixed_fits[label]
        wall = walls[label]
        r_pc = snapshot.radius_cm / PC_TO_CM
        model_n = bubble_number_density(snapshot.radius_cm, fit["rt_cm"], fit["nt_cm3"], fit["nism_cm3"])
        ax.loglog(r_pc, snapshot.number_density_cm3, lw=1.4, label="AMRVAC")
        ax.loglog(r_pc, model_n, "--", lw=1.4, label="fixed n_ism")
        ax.axvline(wall["outer_rise_pc"], color="tab:red", ls=":", lw=1.0)
        ax.axvline(wall["domain_rmax_pc"], color="0.4", ls="--", lw=0.9)
        ax.set_xlim(max(r_pc.min(), 0.08), wall["domain_rmax_pc"] * 1.02)
        ax.set_title(f"{label}: margin {wall['edge_margin_pc']:.2f} pc")
        ax.set_xlabel("Radius (pc)")
        ax.set_ylabel(r"n(r) [cm$^{-3}$]")
    for ax in axes.ravel()[len(snapshots):]:
        ax.axis("off")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2)
    fig.suptitle("Wide-Box AMRVAC Fixed-Ambient Fits", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    if not rows:
        return
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family-dir",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_19_widebox",
        help="Directory containing density_* wide-box AMRVAC runs.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate_widebox_20260421",
        help="Directory for CSV and plot outputs.",
    )
    args = parser.parse_args()

    family_dir = Path(args.family_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    code_unit_years = code_unit_years_from_modusr(family_dir / "Template" / "mod_usr.t")

    snapshots = collect_final_snapshots(family_dir)
    if not snapshots:
        raise SystemExit("No final wide-box snapshots found.")

    simple_fits: dict[str, dict[str, float]] = {}
    fixed_fits: dict[str, dict[str, float]] = {}
    walls: dict[str, dict[str, float]] = {}
    summary_rows: list[dict[str, object]] = []

    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        simple = fit_simple_bubble(snapshot, code_unit_years)
        fixed = fit_simple_bubble_fixed_nism(snapshot, ambient_number_density_from_run(label), code_unit_years)
        wall = detect_outer_wall(snapshot)
        simple_fits[label] = simple
        fixed_fits[label] = fixed
        walls[label] = wall
        summary_rows.append(
            {
                "run": label,
                "snapshot": snapshot.path.name,
                "domain_rmax_pc": wall["domain_rmax_pc"],
                "outer_trough_pc": wall["outer_trough_pc"],
                "outer_rise_pc": wall["outer_rise_pc"],
                "edge_margin_pc": wall["edge_margin_pc"],
                "edge_ratio_rmax_over_rise": wall["edge_ratio_rmax_over_rise"],
                "simple_rt_pc": simple["rt_pc"],
                "simple_r2_rt": simple["r2_rt"],
                "simple_nism_cm3": simple["nism_cm3"],
                "simple_rms_dex": simple["rms_dex"],
                "fixed_nism_cm3": fixed["nism_cm3"],
                "fixed_rt_pc": fixed["rt_pc"],
                "fixed_rms_dex": fixed["rms_dex"],
            }
        )

    summary_rows.sort(key=lambda row: row["run"])
    write_csv(summary_rows, output_dir / "widebox_wall_clearance_summary.csv")
    write_csv(
        [
            {
                "run": row["run"],
                "snapshot": row["snapshot"],
                "simple_rt_pc": row["simple_rt_pc"],
                "simple_r2_rt": row["simple_r2_rt"],
                "simple_nism_cm3": row["simple_nism_cm3"],
                "simple_rms_dex": row["simple_rms_dex"],
                "fixed_nism_cm3": row["fixed_nism_cm3"],
                "fixed_rt_pc": row["fixed_rt_pc"],
                "fixed_rms_dex": row["fixed_rms_dex"],
            }
            for row in summary_rows
        ],
        output_dir / "widebox_simple_bubble_fit_summary.csv",
    )

    plot_family_raw(snapshots, output_dir / "raw_profiles.png")
    plot_family_simple(snapshots, simple_fits, output_dir / "simple_bubble_fits.png")
    plot_fixed_nism_overview(snapshots, fixed_fits, walls, output_dir / "fixed_nism_overview.png")

    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        plot_fixed_nism(
            snapshot,
            fixed_fits[label],
            walls[label],
            output_dir / f"{label}_fixed_nism_fit_wide.png",
        )

    clear_runs = [row["run"] for row in summary_rows if row["edge_margin_pc"] >= 1.0]
    notes = output_dir / "analysis_notes.txt"
    with notes.open("w") as handle:
        handle.write(f"Included final runs: {len(summary_rows)}\n")
        handle.write("Runs with >= 1 pc margin after outer rise:\n")
        for run in clear_runs:
            handle.write(f"- {run}\n")
        if not clear_runs:
            handle.write("- none\n")

    print(f"Wrote wide-box analysis to {output_dir}")


if __name__ == "__main__":
    main()
