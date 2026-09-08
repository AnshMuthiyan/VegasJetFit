#!/usr/bin/env python3
"""
Fit the shelf-plus-smooth-contact surrogate across the AMRVAC density family
and compare it against the simple bubble and mass-scaled cavity models.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyze_amrvac_bubble_profiles import (
    PC_TO_CM,
    TINY,
    bubble_number_density,
    bubble_shell_radius,
    read_vtu_snapshot,
)
from compare_empirical_cavity_model import (
    fit_empirical_cavity_slope,
    fit_mass_scaled_cavity,
    find_profile_rises,
    infer_nism_from_run_name,
    infer_nt_from_inner_wind,
    intershock_mass_ratio,
)
from compare_contact_cavity_model import (
    fit_shelf_contact_model,
    shelf_cavity_mass_ratio,
)


@dataclass
class SnapshotComparison:
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
    simple_rms: float
    simple_outer_ratio: float
    simple_mass_ratio: float
    massfit_s: float
    massfit_f_mass: float
    massfit_outer_ratio: float
    massfit_rms: float
    contact_s: float
    contact_f_mass: float
    contact_shelf_ratio: float
    contact_width_dex: float
    contact_outer_ratio: float
    contact_mass_ratio: float
    contact_rms: float


def list_family_runs(family_dir: Path, min_snapshots: int) -> list[Path]:
    runs = []
    for run_dir in sorted(p for p in family_dir.glob("density_*") if p.is_dir()):
        vtus = sorted(run_dir.glob("output/Ostar_1D/test*.vtu"))
        if len(vtus) >= min_snapshots:
            runs.append(run_dir)
    return runs


def fit_snapshot(vtu_path: Path) -> SnapshotComparison:
    snapshot = read_vtu_snapshot(vtu_path)
    run = vtu_path.parents[2].name
    radius_cm = snapshot.radius_cm
    number_density_cm3 = np.maximum(snapshot.number_density_cm3, TINY)
    radius_pc = radius_cm / PC_TO_CM

    first_rise_pc, second_rise_pc = find_profile_rises(radius_pc, number_density_cm3)
    nt_cm3 = infer_nt_from_inner_wind(radius_cm, radius_pc, number_density_cm3, first_rise_pc)
    nism_cm3 = infer_nism_from_run_name(run)
    q_value = nism_cm3 / nt_cm3

    simple = bubble_number_density(radius_cm, first_rise_pc * PC_TO_CM, nt_cm3, nism_cm3)
    simple_rms = float(np.sqrt(np.mean((np.log10(np.maximum(simple, TINY)) - np.log10(number_density_cm3)) ** 2)))
    _, simple_r2_cm = bubble_shell_radius(first_rise_pc * PC_TO_CM, nt_cm3, nism_cm3)
    simple_outer_ratio = simple_r2_cm / (first_rise_pc * PC_TO_CM)
    simple_mass_ratio = intershock_mass_ratio(simple_outer_ratio, 0.0)

    empirical_s, _ = fit_empirical_cavity_slope(
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

    contact_s, contact_f_mass, contact_shelf_ratio, contact_width_dex, contact_outer_ratio, contact_rms = fit_shelf_contact_model(
        radius_cm=radius_cm,
        number_density_cm3=number_density_cm3,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        simple_mass_ratio=simple_mass_ratio,
        initial_s=massfit_s,
        initial_f_mass=massfit_f_mass,
    )
    contact_mass_ratio = shelf_cavity_mass_ratio(contact_outer_ratio, contact_shelf_ratio, contact_s)

    return SnapshotComparison(
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
        simple_rms=float(simple_rms),
        simple_outer_ratio=float(simple_outer_ratio),
        simple_mass_ratio=float(simple_mass_ratio),
        massfit_s=float(massfit_s),
        massfit_f_mass=float(massfit_f_mass),
        massfit_outer_ratio=float(massfit_outer_ratio),
        massfit_rms=float(massfit_rms),
        contact_s=float(contact_s),
        contact_f_mass=float(contact_f_mass),
        contact_shelf_ratio=float(contact_shelf_ratio),
        contact_width_dex=float(contact_width_dex),
        contact_outer_ratio=float(contact_outer_ratio),
        contact_mass_ratio=float(contact_mass_ratio),
        contact_rms=float(contact_rms),
    )


def write_csv(rows: list[dict[str, float | str]], path: Path) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_final_rms(rows: list[dict[str, float | str]], output_path: Path) -> None:
    x = np.arange(len(rows))
    simple = np.array([float(r["simple_rms"]) for r in rows], dtype=float)
    massfit = np.array([float(r["massfit_rms"]) for r in rows], dtype=float)
    contact = np.array([float(r["contact_rms"]) for r in rows], dtype=float)
    labels = [str(r["run"]) for r in rows]

    fig, ax = plt.subplots(figsize=(8.6, 4.8), dpi=220)
    ax.plot(x, simple, "o-", label="simple bubble")
    ax.plot(x, massfit, "o-", label="mass-scaled cavity")
    ax.plot(x, contact, "o-", label="shelf + smooth-contact")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("RMS (dex)")
    ax.set_title("Final-state RMS comparison")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")


def plot_time_medians(rows: list[dict[str, float | str]], output_path: Path) -> None:
    grouped: dict[float, list[dict[str, float | str]]] = {}
    for row in rows:
        grouped.setdefault(float(row["time_yr"]), []).append(row)

    times = np.array(sorted(grouped.keys()), dtype=float)
    simple = []
    massfit = []
    contact = []
    for t in times:
        subset = grouped[t]
        simple.append(np.median([float(r["simple_rms"]) for r in subset]))
        massfit.append(np.median([float(r["massfit_rms"]) for r in subset]))
        contact.append(np.median([float(r["contact_rms"]) for r in subset]))

    fig, ax = plt.subplots(figsize=(8.4, 4.8), dpi=220)
    ax.plot(times, simple, "o-", label="simple bubble median RMS")
    ax.plot(times, massfit, "o-", label="mass-scaled cavity median RMS")
    ax.plot(times, contact, "o-", label="shelf + smooth-contact median RMS")
    ax.set_xlabel("Simulation time (Myr)")
    ax.set_ylabel("Median RMS (dex)")
    ax.set_title("Intermediate-time model comparison")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")


def plot_final_contact_params(rows: list[dict[str, float | str]], output_path: Path) -> None:
    logq = np.log10(np.array([float(r["q_nism_over_nt"]) for r in rows], dtype=float))
    shelf = np.array([float(r["contact_shelf_ratio"]) for r in rows], dtype=float)
    slope = np.array([float(r["contact_s"]) for r in rows], dtype=float)
    logf = np.log10(np.array([float(r["contact_f_mass"]) for r in rows], dtype=float))
    labels = [str(r["run"]) for r in rows]

    fig, axes = plt.subplots(3, 1, figsize=(8.0, 9.0), dpi=220, sharex=True)
    for ax, y, ylabel in zip(
        axes,
        [shelf, slope, logf],
        [r"$x_p = r_p / r_t$", r"$s$", r"log$_{10}$(f$_M$)"],
    ):
        ax.scatter(logq, y, s=42)
        for x, yy, label in zip(logq, y, labels):
            ax.annotate(label, (x, yy), xytext=(4, 4), textcoords="offset points", fontsize=7)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
    axes[0].set_title("Final-state shelf + smooth-contact parameters")
    axes[-1].set_xlabel(r"log$_{10}$(q), q = n$_{ism}$/n$_t$")
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
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate_contact",
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

    all_rows: list[SnapshotComparison] = []
    final_rows: list[SnapshotComparison] = []
    for run_dir in run_dirs:
        vtus = sorted(run_dir.glob("output/Ostar_1D/test*.vtu"))
        for idx, path in enumerate(vtus):
            row = fit_snapshot(path)
            all_rows.append(row)
            if idx == len(vtus) - 1:
                final_rows.append(row)

    all_rows.sort(key=lambda row: (row.snapshot_index, row.run))
    final_rows.sort(key=lambda row: row.run)

    final_csv_rows = [row.__dict__ for row in final_rows]
    all_csv_rows = [row.__dict__ for row in all_rows]
    write_csv(final_csv_rows, output_dir / "final_contact_family_summary.csv")
    write_csv(all_csv_rows, output_dir / "time_contact_family_summary.csv")

    plot_final_rms(final_csv_rows, output_dir / "final_contact_rms_comparison.png")
    plot_time_medians(all_csv_rows, output_dir / "time_contact_median_rms_comparison.png")
    plot_final_contact_params(final_csv_rows, output_dir / "final_contact_params.png")

    notes = output_dir / "contact_notes.txt"
    with notes.open("w") as handle:
        handle.write(f"Included runs: {len(run_dirs)}\n")
        handle.write(
            f"Median final RMS: simple={np.median([r.simple_rms for r in final_rows]):.6f}, "
            f"massfit={np.median([r.massfit_rms for r in final_rows]):.6f}, "
            f"contact={np.median([r.contact_rms for r in final_rows]):.6f}\n"
        )
        handle.write(
            f"Median all-time RMS: simple={np.median([r.simple_rms for r in all_rows]):.6f}, "
            f"massfit={np.median([r.massfit_rms for r in all_rows]):.6f}, "
            f"contact={np.median([r.contact_rms for r in all_rows]):.6f}\n"
        )

    print(f"Wrote final summary to {output_dir / 'final_contact_family_summary.csv'}")
    print(f"Wrote time summary to {output_dir / 'time_contact_family_summary.csv'}")
    print(f"Wrote plots to {output_dir}")
    print(
        f"Median final RMS: simple={np.median([r.simple_rms for r in final_rows]):.6f}, "
        f"massfit={np.median([r.massfit_rms for r in final_rows]):.6f}, "
        f"contact={np.median([r.contact_rms for r in final_rows]):.6f}"
    )
    print(
        f"Median all-time RMS: simple={np.median([r.simple_rms for r in all_rows]):.6f}, "
        f"massfit={np.median([r.massfit_rms for r in all_rows]):.6f}, "
        f"contact={np.median([r.contact_rms for r in all_rows]):.6f}"
    )


if __name__ == "__main__":
    main()
