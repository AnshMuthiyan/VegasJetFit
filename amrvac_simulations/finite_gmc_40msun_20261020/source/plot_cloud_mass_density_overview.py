#!/usr/bin/env python3
"""Plot the validated 80-pc shell peaks without mixing simulation ages."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_rows(path: Path, mesh: int, stage: str) -> list[dict]:
    with path.open(newline="", encoding="ascii") as stream:
        source = list(csv.DictReader(stream))
    if not source:
        raise ValueError(f"empty product table: {path}")
    rows = []
    for item in source:
        if item["stage"] != stage or float(item["domain_max_pc"]) != 80.0:
            raise ValueError(f"unexpected stage or domain in {path}")
        if (float(item["cloud_pc"]) != 2.0 or float(item["edge_width_pc"]) != 0.5
                or float(item["slope_p"]) != 1.8 or float(item["star_mass_msun"]) != 40.0):
            raise ValueError(f"different cloud physics in {path}")
        age = float(item["age_myr"])
        if abs(age - (0.1 if stage == "wind" else 4.77)) > 3e-5:
            raise ValueError(f"unexpected age in {path}: {age}")
        width_elements = float(item["shell_width_elements"])
        row = {
            "case": item["case"],
            "stage": stage,
            "mesh_cells": mesh,
            "age_myr": age,
            "n_ref_cm3": float(item["n_ref_cm3"]),
            "shell_peak_pc": float(item["shell_peak_pc"]),
            "shell_width_elements": width_elements,
            "initial_front_elements": int(item["initial_front_elements"]),
            "meets_sampling_gate": width_elements >= 5.0 and int(item["initial_front_elements"]) >= 10,
            "source_csv": str(path),
        }
        rows.append(row)
    return sorted(rows, key=lambda row: row["n_ref_cm3"])


def plot(rows: list[dict], output: Path) -> None:
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, (early, late) = plt.subplots(1, 2, figsize=(11.5, 5.4),
                                     gridspec_kw={"width_ratios": [1.35, 1]},
                                     constrained_layout=True)
    colors = {2048: "#9f3547", 4096: "#207a81"}
    markers = {2048: "o", 4096: "D"}
    for ax, stage in ((early, "wind"), (late, "full")):
        for mesh in (2048, 4096):
            group = [row for row in rows if row["stage"] == stage and row["mesh_cells"] == mesh]
            if not group:
                continue
            for row in group:
                ax.scatter(row["n_ref_cm3"], row["shell_peak_pc"], s=105,
                           marker=markers[mesh], color=colors[mesh],
                           facecolors=colors[mesh] if row["meets_sampling_gate"] else "white",
                           linewidths=2.0, zorder=3)
        ax.set_xlim(220, 1600)
        ax.set_xticks((300, 600, 1000, 1500))
        ax.set_xlabel(r"Untapered $n_{ref}$ at 1 pc (cm$^{-3}$)")
        ax.grid(alpha=0.22)
    early.set_ylim(0, 3.8)
    late.set_ylim(0, 65)
    early.set_ylabel("Native density-excess shell peak (pc)")
    late.set_ylabel("Native density-excess shell peak (pc)")
    early.set_title("0.10 Myr | early wind", loc="left")
    late.set_title("4.77 Myr | after WR phase", loc="left")
    late_row = next(row for row in rows if row["stage"] == "full")
    late.annotate(f"{late_row['shell_peak_pc']:.1f} pc",
                  xy=(late_row["n_ref_cm3"], late_row["shell_peak_pc"]),
                  xytext=(450, late_row["shell_peak_pc"]),
                  va="center", color=colors[2048], fontsize=11)
    late.text(0.98, 0.05, "Higher-density full runs held", transform=late.transAxes,
              ha="right", va="bottom", fontsize=9, color="#555555")
    early.scatter([], [], s=85, marker="o", color=colors[2048], label="2048 radial cells")
    early.scatter([], [], s=85, marker="D", color=colors[4096], label="4096 radial cells")
    early.scatter([], [], s=85, marker="o", facecolors="white", edgecolors="#555555",
                  linewidths=2, label="Below sampling gate")
    early.legend(loc="upper right", frameon=False, fontsize=9)
    fig.suptitle("40-solar-mass finite-cloud shell radius vs initial density", fontsize=14)
    fig.text(0.5, -0.015,
             "2-pc cloud, 80-pc domain. Hollow markers: shell FWHM <5 cells or H II zone <10 cells. "
             "No fit or late-time density trend is implied.",
             ha="center", fontsize=9, color="#555555")
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("early_2048_csv", type=Path)
    parser.add_argument("early_4096_csv", type=Path)
    parser.add_argument("late_2048_csv", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    rows = (load_rows(args.early_2048_csv, 2048, "wind")
            + load_rows(args.early_4096_csv, 4096, "wind")
            + load_rows(args.late_2048_csv, 2048, "full"))
    expected = {(2048, "wind"): {300.0, 600.0, 1000.0, 1500.0},
                (4096, "wind"): {600.0, 1000.0, 1500.0},
                (2048, "full"): {300.0}}
    for (mesh, stage), densities in expected.items():
        actual = [row["n_ref_cm3"] for row in rows
                  if row["mesh_cells"] == mesh and row["stage"] == stage]
        if len(actual) != len(densities) or set(actual) != densities:
            raise ValueError(f"unexpected {mesh}-cell {stage} density set: {actual}")
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "plotted_shell_peaks.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plot(rows, args.output_dir / "shell_radius_vs_density_80pc.png")
    print(f"Plotted {len(rows)} validated points in {args.output_dir}")


if __name__ == "__main__":
    main()
