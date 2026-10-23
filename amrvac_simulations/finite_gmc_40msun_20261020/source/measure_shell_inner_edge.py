#!/usr/bin/env python3
"""Measure the inner swept-shell rise in validated direct-WR VTUs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_dense_gmc_scan import inner_rise, shell_peak, unique_radial_samples
from validate_cloud_mass import MASS_PER_H, RHO_UNIT, profile_nh, validate
from validate_smoke import read_vtu


def case_age_myr(vtu_age_yr: float) -> float:
    # AMRVAC case endpoints use 365-day years; read_vtu returns Julian years.
    return vtu_age_yr * 365.25 / 365.0 / 1e6


def analyze(manifest: Path, case_name: str, results: Path,
            output: Path) -> None:
    with manifest.open(newline="", encoding="ascii") as stream:
        cases = [row for row in csv.DictReader(stream)
                 if row["case"] == case_name and row["stage"] == "wind"]
    if len(cases) != 1:
        raise ValueError("select exactly one wind case from the manifest")
    case = cases[0]
    n_ref, n_gmc = float(case["n_ref_cm3"]), float(case["n_gmc_cm3"])
    inner = float(case["inner_pc"])
    domain = float(case["domain_max_pc"])
    reference_outer = float(case.get("atmosphere_outer_pc") or domain)
    search_min = 0.05 if domain >= 10.0 else inner + 4 * float(case["first_width_pc"])
    search_max = 10.0 if domain >= 10.0 else 0.8 * domain
    count = int(case["expected_vtus"])
    check = validate(results, case_name, n_ref, float(case["endpoint_myr"]),
                     count, False, 0.5, 2.0, 1.8, 40.0, domain,
                     inner, n_gmc, True, 10.0, 15.0, 1.0,
                     expected_mdot_msun_yr=1e-5,
                     atmosphere_outer_pc=reference_outer)
    rows = []
    final = None
    for index in range(1, count):
        age, raw = read_vtu(results / f"{case_name}{index:04d}.vtu")
        data = unique_radial_samples(raw)
        radius = data[:, 0]
        density = data[:, 1] * RHO_UNIT / MASS_PER_H
        initial = profile_nh(radius, n_ref, 0.5, 2.0, 1.8,
                             n_bg=n_gmc, finite_gmc=True, n_ext=10.0,
                             gmc_pc=15.0, gmc_edge_width=1.0)
        peak = shell_peak(data, initial, search_min, search_max)
        try:
            rise = inner_rise(radius, density, peak["shell_peak_pc"], search_min)
            status = "measured"
        except ValueError as error:
            rise = {}
            status = f"ambiguous: {error}"
        quality = (check["initial_front_elements"] >= 10
                   and peak["shell_fwhm_cells"] >= 5
                   and peak["shell_contrast"] >= 3
                   and peak["shell_fwhm_pc"] / peak["shell_peak_pc"] <= 0.25)
        rows.append({"case": case_name, "age_myr": case_age_myr(age),
                     "inner_edge_status": status, "shell_quality_pass": quality,
                     "inner_ramp_resolved": (rise.get("inner_ramp_cells", 0) >= 5),
                     **peak, **rise})
        final = (radius, density, initial, rows[-1])

    output.mkdir(parents=True, exist_ok=False)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (output / "inner_shell_metrics.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    radius, density, initial, last = final
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for ax in axes:
        ax.plot(radius, density, label="Saved density")
        ax.plot(radius, initial, linestyle=":", label="Initial atmosphere")
        ax.axvline(last["shell_peak_pc"], linestyle="--", color="0.45",
                   label="Density-excess peak")
        if last["inner_edge_status"] == "measured":
            for key, label, color in (("inner_radius_pc", "Inner 10%", "#b5323e"),
                                      ("inner_midrise_pc", "Inner 50%", "#d18b16"),
                                      ("inner_rise_90_pc", "Inner 90%", "#268071")):
                ax.axvline(last[key], color=color, label=label)
        ax.set(yscale="log", xlabel="Radius (pc)")
        ax.grid(alpha=0.2)
    axes[0].set(xlim=(0, min(10.0, 1.3 * last["shell_peak_pc"])),
                ylabel=r"$n_{\rm H}$ (cm$^{-3}$)", title="Bubble and shell")
    axes[1].set_title("Inner rise")
    if last["inner_edge_status"] == "measured":
        center = last["inner_midrise_pc"]
        span = max(8 * last["inner_ramp_pc"], 0.03 * center)
        axes[1].set_xlim(center - span, center + span)
    axes[1].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle(f"Inner shell rise at {last['age_myr']:.4f} Myr")
    fig.savefig(output / "inner_shell_profile.png", dpi=180)
    plt.close(fig)
    print(f"Validated {case_name}; wrote {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("case")
    parser.add_argument("results", type=Path, help="Validated wind VTUs and run logs")
    parser.add_argument("output", type=Path, help="New diagnostic directory")
    args = parser.parse_args()
    analyze(args.manifest, args.case, args.results, args.output)
