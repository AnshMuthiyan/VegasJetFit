#!/usr/bin/env python3
"""
Fit the mass-scaled empirical cavity model across the AMRVAC density family.

Workflow:
  1. Fit each snapshot individually with the simple bubble and the improved
     mass-scaled cavity model.
  2. Calibrate low-dimensional relations for the cavity model using the final
     snapshots only:
       s(log q), log10(f_M)(log q), with q = n_ism / n_t
  3. Apply that calibrated model back to every snapshot, including
     intermediate times, to see how well the low-dimensional closure holds.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

from analyze_amrvac_bubble_profiles import (
    PC_TO_CM,
    TINY,
    bubble_number_density,
    bubble_shell_radius,
    read_vtu_snapshot,
)
from compare_empirical_cavity_model import (
    empirical_cavity_profile,
    find_profile_rises,
    fit_empirical_cavity_slope,
    fit_mass_scaled_cavity,
    infer_nism_from_run_name,
    infer_nt_from_inner_wind,
    intershock_mass_ratio,
    outer_ratio_from_mass_ratio,
)


@dataclass
class SnapshotFit:
    run: str
    snapshot: str
    snapshot_index: int
    time_s: float
    time_yr: float
    rt_pc: float
    nt_cm3: float
    nism_cm3: float
    q_nism_over_nt: float
    second_rise_pc: float
    simple_outer_ratio: float
    simple_mass_ratio: float
    simple_rms: float
    empirical_s: float
    empirical_outer_ratio: float
    empirical_mass_ratio: float
    empirical_f_mass: float
    empirical_rms: float
    massfit_s: float
    massfit_f_mass: float
    massfit_outer_ratio: float
    massfit_rms: float


def list_family_runs(family_dir: Path, min_snapshots: int) -> list[Path]:
    runs = []
    for run_dir in sorted(p for p in family_dir.glob("density_*") if p.is_dir()):
        vtus = sorted(run_dir.glob("output/Ostar_1D/test*.vtu"))
        if len(vtus) >= min_snapshots:
            runs.append(run_dir)
    return runs


def rms_dex(model_n: np.ndarray, data_n: np.ndarray) -> float:
    resid = np.log10(np.maximum(model_n, TINY)) - np.log10(np.maximum(data_n, TINY))
    return float(np.sqrt(np.mean(resid**2)))


def fit_snapshot(vtu_path: Path) -> SnapshotFit:
    snapshot = read_vtu_snapshot(vtu_path)
    run = vtu_path.parents[2].name
    radius_cm = snapshot.radius_cm
    number_density_cm3 = np.maximum(snapshot.number_density_cm3, TINY)
    radius_pc = radius_cm / PC_TO_CM

    first_rise_pc, second_rise_pc = find_profile_rises(radius_pc, number_density_cm3)
    nt_cm3 = infer_nt_from_inner_wind(radius_cm, radius_pc, number_density_cm3, first_rise_pc)
    nism_cm3 = infer_nism_from_run_name(run)
    q_value = nism_cm3 / nt_cm3

    simple_n = bubble_number_density(radius_cm, first_rise_pc * PC_TO_CM, nt_cm3, nism_cm3)
    simple_rms = rms_dex(simple_n, number_density_cm3)
    _, simple_r2_cm = bubble_shell_radius(first_rise_pc * PC_TO_CM, nt_cm3, nism_cm3)
    simple_outer_ratio = simple_r2_cm / (first_rise_pc * PC_TO_CM)
    simple_mass_ratio = intershock_mass_ratio(simple_outer_ratio, 0.0)

    empirical_s, empirical_rms = fit_empirical_cavity_slope(
        radius_cm=radius_cm,
        number_density_cm3=number_density_cm3,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        outer_rise_pc=second_rise_pc,
    )
    empirical_outer_ratio = second_rise_pc / first_rise_pc
    empirical_mass_ratio = intershock_mass_ratio(empirical_outer_ratio, empirical_s)
    empirical_f_mass = empirical_mass_ratio / simple_mass_ratio

    massfit_s, massfit_f_mass, massfit_outer_ratio, massfit_rms = fit_mass_scaled_cavity(
        radius_cm=radius_cm,
        number_density_cm3=number_density_cm3,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        simple_mass_ratio=simple_mass_ratio,
        initial_s=empirical_s,
        initial_f_mass=empirical_f_mass,
    )

    return SnapshotFit(
        run=run,
        snapshot=vtu_path.name,
        snapshot_index=int(vtu_path.stem.replace("test", "")),
        time_s=float(snapshot.time_s),
        time_yr=float(snapshot.time_s / (365.25 * 86400.0)),
        rt_pc=float(first_rise_pc),
        nt_cm3=float(nt_cm3),
        nism_cm3=float(nism_cm3),
        q_nism_over_nt=float(q_value),
        second_rise_pc=float(second_rise_pc),
        simple_outer_ratio=float(simple_outer_ratio),
        simple_mass_ratio=float(simple_mass_ratio),
        simple_rms=float(simple_rms),
        empirical_s=float(empirical_s),
        empirical_outer_ratio=float(empirical_outer_ratio),
        empirical_mass_ratio=float(empirical_mass_ratio),
        empirical_f_mass=float(empirical_f_mass),
        empirical_rms=float(empirical_rms),
        massfit_s=float(massfit_s),
        massfit_f_mass=float(massfit_f_mass),
        massfit_outer_ratio=float(massfit_outer_ratio),
        massfit_rms=float(massfit_rms),
    )


def robust_line_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    def residual(params: np.ndarray) -> np.ndarray:
        a, b = params
        return a + b * x - y

    guess = np.polyfit(x, y, deg=1)
    result = least_squares(residual, x0=[guess[1], guess[0]], loss="soft_l1", f_scale=0.1, max_nfev=4000)
    a, b = map(float, result.x)
    fit_rms = float(np.sqrt(np.mean(residual(result.x) ** 2)))
    return a, b, fit_rms


def calibrated_values(logq: np.ndarray, a_s: float, b_s: float, a_f: float, b_f: float) -> tuple[np.ndarray, np.ndarray]:
    s = np.clip(a_s + b_s * logq, 0.1, 2.99)
    f_mass = np.clip(10.0 ** (a_f + b_f * logq), 1e-4, 10.0)
    return s, f_mass


def calibrated_model_rms(row: SnapshotFit, s_value: float, f_mass: float, vtu_path: Path) -> tuple[float, float]:
    snapshot = read_vtu_snapshot(vtu_path)
    radius_cm = snapshot.radius_cm
    number_density_cm3 = np.maximum(snapshot.number_density_cm3, TINY)
    outer_ratio = outer_ratio_from_mass_ratio(f_mass * row.simple_mass_ratio, s_value)
    model_n = empirical_cavity_profile(
        radius_cm=radius_cm,
        rt_pc=row.rt_pc,
        nt_cm3=row.nt_cm3,
        nism_cm3=row.nism_cm3,
        outer_rise_pc=row.rt_pc * outer_ratio,
        slope_s=s_value,
    )
    return rms_dex(model_n, number_density_cm3), float(outer_ratio)


def write_csv(rows: list[dict[str, float | str]], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_final_calibration(final_rows: list[dict[str, float | str]], output_path: Path, a_s: float, b_s: float, a_f: float, b_f: float) -> None:
    logq = np.array([float(r["log10_q"]) for r in final_rows], dtype=float)
    s_fit = np.array([float(r["massfit_s"]) for r in final_rows], dtype=float)
    logf_fit = np.log10(np.array([float(r["massfit_f_mass"]) for r in final_rows], dtype=float))
    labels = [str(r["run"]) for r in final_rows]

    xgrid = np.linspace(logq.min() - 0.2, logq.max() + 0.2, 300)
    s_pred, f_pred = calibrated_values(xgrid, a_s, b_s, a_f, b_f)

    fig, axes = plt.subplots(2, 1, figsize=(8.0, 7.2), dpi=220, sharex=True)

    axes[0].scatter(logq, s_fit, s=42)
    axes[0].plot(xgrid, s_pred, lw=1.8)
    for x, y, label in zip(logq, s_fit, labels):
        axes[0].annotate(label, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7)
    axes[0].set_ylabel("best-fit s")
    axes[0].grid(True, alpha=0.25)
    axes[0].set_title("Final-state cavity calibration")

    axes[1].scatter(logq, logf_fit, s=42)
    axes[1].plot(xgrid, np.log10(f_pred), lw=1.8)
    for x, y, label in zip(logq, logf_fit, labels):
        axes[1].annotate(label, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7)
    axes[1].set_xlabel(r"log$_{10}$(q), q = n$_{ism}$/n$_t$")
    axes[1].set_ylabel(r"log$_{10}$(f$_M$)")
    axes[1].grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")


def plot_rms_comparison(rows: list[dict[str, float | str]], output_path: Path, title: str, x_key: str) -> None:
    x = np.arange(len(rows))
    simple = np.array([float(r["simple_rms"]) for r in rows], dtype=float)
    massfit = np.array([float(r["massfit_rms"]) for r in rows], dtype=float)
    calibrated = np.array([float(r["calibrated_rms"]) for r in rows], dtype=float)
    labels = [str(r[x_key]) for r in rows]

    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=220)
    ax.plot(x, simple, "o-", label="simple bubble")
    ax.plot(x, massfit, "o-", label="mass-scaled cavity fit")
    ax.plot(x, calibrated, "o-", label="calibrated q-model")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("RMS (dex)")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")


def plot_time_summary(time_rows: list[dict[str, float | str]], output_path: Path) -> None:
    grouped: dict[float, list[dict[str, float | str]]] = {}
    for row in time_rows:
        grouped.setdefault(float(row["time_yr"]), []).append(row)

    times = np.array(sorted(grouped.keys()), dtype=float)
    simple_med = []
    massfit_med = []
    calibrated_med = []
    for t in times:
        rows = grouped[t]
        simple_med.append(np.median([float(r["simple_rms"]) for r in rows]))
        massfit_med.append(np.median([float(r["massfit_rms"]) for r in rows]))
        calibrated_med.append(np.median([float(r["calibrated_rms"]) for r in rows]))

    fig, ax = plt.subplots(figsize=(8.2, 4.8), dpi=220)
    ax.plot(times, simple_med, "o-", label="simple bubble median RMS")
    ax.plot(times, massfit_med, "o-", label="mass-scaled cavity median RMS")
    ax.plot(times, calibrated_med, "o-", label="calibrated q-model median RMS")
    ax.set_xlabel("Simulation time (Myr)")
    ax.set_ylabel("Median RMS (dex)")
    ax.set_title("Intermediate-time model comparison")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family-dir",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2025_08_07",
        help="Directory containing density_* runs.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate_cavity",
        help="Directory for outputs.",
    )
    parser.add_argument(
        "--min-snapshots",
        type=int,
        default=5,
        help="Skip density_* runs with fewer than this many snapshots.",
    )
    args = parser.parse_args()

    family_dir = Path(args.family_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = list_family_runs(family_dir, args.min_snapshots)
    if not run_dirs:
        raise SystemExit("No usable density_* runs found.")

    snapshot_paths_by_run = {
        run_dir.name: sorted(run_dir.glob("output/Ostar_1D/test*.vtu"))
        for run_dir in run_dirs
    }

    final_fit_rows: list[SnapshotFit] = []
    time_fit_rows: list[SnapshotFit] = []
    for run, paths in snapshot_paths_by_run.items():
        for idx, path in enumerate(paths):
            fit = fit_snapshot(path)
            time_fit_rows.append(fit)
            if idx == len(paths) - 1:
                final_fit_rows.append(fit)

    final_fit_rows.sort(key=lambda row: row.run)
    time_fit_rows.sort(key=lambda row: (row.snapshot_index, row.run))

    final_logq = np.log10(np.array([row.q_nism_over_nt for row in final_fit_rows], dtype=float))
    final_s = np.array([row.massfit_s for row in final_fit_rows], dtype=float)
    final_logf = np.log10(np.array([row.massfit_f_mass for row in final_fit_rows], dtype=float))

    a_s, b_s, s_reg_rms = robust_line_fit(final_logq, final_s)
    a_f, b_f, f_reg_rms = robust_line_fit(final_logq, final_logf)

    final_csv_rows: list[dict[str, float | str]] = []
    for row in final_fit_rows:
        logq = float(np.log10(row.q_nism_over_nt))
        s_cal, f_cal = calibrated_values(np.array([logq]), a_s, b_s, a_f, b_f)
        calibrated_rms, calibrated_outer_ratio = calibrated_model_rms(
            row=row,
            s_value=float(s_cal[0]),
            f_mass=float(f_cal[0]),
            vtu_path=snapshot_paths_by_run[row.run][-1],
        )
        final_csv_rows.append(
            {
                **row.__dict__,
                "log10_q": logq,
                "calibrated_s": float(s_cal[0]),
                "calibrated_f_mass": float(f_cal[0]),
                "calibrated_outer_ratio": calibrated_outer_ratio,
                "calibrated_rms": calibrated_rms,
            }
        )

    time_csv_rows: list[dict[str, float | str]] = []
    for row in time_fit_rows:
        logq = float(np.log10(row.q_nism_over_nt))
        s_cal, f_cal = calibrated_values(np.array([logq]), a_s, b_s, a_f, b_f)
        calibrated_rms, calibrated_outer_ratio = calibrated_model_rms(
            row=row,
            s_value=float(s_cal[0]),
            f_mass=float(f_cal[0]),
            vtu_path=snapshot_paths_by_run[row.run][row.snapshot_index],
        )
        time_csv_rows.append(
            {
                **row.__dict__,
                "log10_q": logq,
                "calibrated_s": float(s_cal[0]),
                "calibrated_f_mass": float(f_cal[0]),
                "calibrated_outer_ratio": calibrated_outer_ratio,
                "calibrated_rms": calibrated_rms,
            }
        )

    write_csv(final_csv_rows, output_dir / "final_cavity_family_summary.csv")
    write_csv(time_csv_rows, output_dir / "time_cavity_family_summary.csv")

    plot_final_calibration(
        final_rows=final_csv_rows,
        output_path=output_dir / "final_cavity_calibration.png",
        a_s=a_s,
        b_s=b_s,
        a_f=a_f,
        b_f=b_f,
    )
    plot_rms_comparison(
        rows=final_csv_rows,
        output_path=output_dir / "final_rms_comparison.png",
        title="Final-state RMS comparison",
        x_key="run",
    )
    plot_time_summary(
        time_rows=time_csv_rows,
        output_path=output_dir / "time_median_rms_comparison.png",
    )

    notes = output_dir / "calibration_notes.txt"
    with notes.open("w") as handle:
        handle.write(f"Included runs: {len(run_dirs)}\n")
        handle.write(f"Final-state slope calibration: s = {a_s:.6f} + {b_s:.6f} * log10(q)\n")
        handle.write(f"Final-state mass calibration: log10(f_M) = {a_f:.6f} + {b_f:.6f} * log10(q)\n")
        handle.write(f"s regression RMS: {s_reg_rms:.6f}\n")
        handle.write(f"log10(f_M) regression RMS: {f_reg_rms:.6f}\n")
        handle.write(
            f"Median final RMS: simple={np.median([r['simple_rms'] for r in final_csv_rows]):.6f}, "
            f"massfit={np.median([r['massfit_rms'] for r in final_csv_rows]):.6f}, "
            f"calibrated={np.median([r['calibrated_rms'] for r in final_csv_rows]):.6f}\n"
        )
        handle.write(
            f"Median all-time RMS: simple={np.median([r['simple_rms'] for r in time_csv_rows]):.6f}, "
            f"massfit={np.median([r['massfit_rms'] for r in time_csv_rows]):.6f}, "
            f"calibrated={np.median([r['calibrated_rms'] for r in time_csv_rows]):.6f}\n"
        )

    print(f"Wrote final summary to {output_dir / 'final_cavity_family_summary.csv'}")
    print(f"Wrote time summary to {output_dir / 'time_cavity_family_summary.csv'}")
    print(f"Wrote plots to {output_dir}")
    print(f"s(log10 q) = {a_s:.6f} + {b_s:.6f} * log10(q)")
    print(f"log10(f_M)(log10 q) = {a_f:.6f} + {b_f:.6f} * log10(q)")
    print(f"Median final RMS: simple={np.median([r['simple_rms'] for r in final_csv_rows]):.6f}, massfit={np.median([r['massfit_rms'] for r in final_csv_rows]):.6f}, calibrated={np.median([r['calibrated_rms'] for r in final_csv_rows]):.6f}")
    print(f"Median all-time RMS: simple={np.median([r['simple_rms'] for r in time_csv_rows]):.6f}, massfit={np.median([r['massfit_rms'] for r in time_csv_rows]):.6f}, calibrated={np.median([r['calibrated_rms'] for r in time_csv_rows]):.6f}")


if __name__ == "__main__":
    main()
