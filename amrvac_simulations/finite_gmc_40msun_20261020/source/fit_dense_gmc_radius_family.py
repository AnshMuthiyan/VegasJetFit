#!/usr/bin/env python3
"""Fit an explicitly provisional, fixed-wind shell-radius/density family."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows = []
    for path in paths:
        with path.open(newline="", encoding="ascii") as stream:
            rows.extend(csv.DictReader(stream))
    if not rows:
        raise ValueError("no shell metrics")
    return rows


def fit(rows: list[dict[str, str]], label: str, output: Path,
        mesh_tag: str) -> dict:
    if len({row["case"] for row in rows}) != len(rows):
        raise ValueError("duplicate cases")
    fixed = ("age_myr", "star_mass_msun", "edge_width_pc", "cloud_pc",
             "slope_p", "gmc_pc", "domain_max_pc")
    reference = rows[0]
    for row in rows:
        if mesh_tag not in row["case"]:
            raise ValueError(f"case lacks required mesh tag {mesh_tag}: {row['case']}")
        if row["stage"] != reference["stage"] or row["finite_gmc"] != "True":
            raise ValueError("mixed stages or non-finite GMC cases")
        for field in fixed:
            if not np.isclose(float(row[field]), float(reference[field]), rtol=1e-5):
                raise ValueError(f"mixed physical setup: {field}")
    ratios = np.array([float(row["n_gmc_cm3"]) / float(row["n_ref_cm3"])
                       for row in rows])
    if not np.allclose(ratios, ratios[0], rtol=1e-6):
        raise ValueError("this one-parameter fit requires a fixed GMC/core density ratio")

    points = []
    for row in rows:
        radius = float(row["shell_peak_pc"])
        width_cells = float(row["shell_fwhm_cells"])
        width_fraction = float(row["shell_fwhm_pc"]) / radius
        contrast = float(row["shell_contrast"])
        accepted = (int(row["initial_front_elements"]) >= 10
                    and width_cells >= 5 and contrast >= 3
                    and width_fraction <= 0.25)
        points.append(dict(case=row["case"], n_ref_cm3=float(row["n_ref_cm3"]),
                           n_gmc_cm3=float(row["n_gmc_cm3"]), shell_peak_pc=radius,
                           shell_contrast=contrast, shell_fwhm_cells=width_cells,
                           shell_fwhm_fraction=width_fraction, accepted=accepted))
    accepted = sorted((point for point in points if point["accepted"]),
                      key=lambda point: point["n_ref_cm3"])
    if len(accepted) < 3:
        raise ValueError("at least three sharp, sampled shells are required")
    density = np.array([point["n_ref_cm3"] for point in accepted])
    radius = np.array([point["shell_peak_pc"] for point in accepted])
    n_pivot = float(np.exp(np.mean(np.log(density))))
    x = np.log(density / n_pivot)
    y = np.log(radius)
    slope, intercept = np.polyfit(x, y, 1)
    if slope >= 0:
        raise ValueError("density-radius relation is not decreasing")
    loo = []
    for index in range(len(x)):
        keep = np.arange(len(x)) != index
        p, a = np.polyfit(x[keep], y[keep], 1)
        loo.append(float(np.exp(a + p * x[index] - y[index]) - 1.0))
    result = dict(status="exploratory_not_calibrated", label=label,
                  wind_stage=reference["stage"], age_myr=float(reference["age_myr"]),
                  star_mass_msun=float(reference["star_mass_msun"]),
                  n_gmc_over_n_ref=float(ratios[0]), n_pivot_cm3=n_pivot,
                  radius_at_pivot_pc=float(np.exp(intercept)), exponent=float(slope),
                  n_ref_min_cm3=float(density.min()), n_ref_max_cm3=float(density.max()),
                  radius_min_pc=float(radius.min()), radius_max_pc=float(radius.max()),
                  leave_one_out_fractional_errors=loo,
                  accepted_cases=len(accepted), rejected_cases=len(points) - len(accepted),
                  formula="R_pc=radius_at_pivot_pc*(n_ref_cm3/n_pivot_cm3)**exponent",
                  inverse="n_ref_cm3=n_pivot_cm3*(R_pc/radius_at_pivot_pc)**(1/exponent)",
                  cautions=["Only the fixed GMC/core density-ratio family is identifiable.",
                            "Same-age short-run shell peaks are not late-WR walls.",
                            "Mesh convergence, wind-history, and cloud-physics tests remain open.",
                            "Do not extrapolate outside the accepted density/radius interval."])

    output.mkdir(parents=True, exist_ok=False)
    with (output / "screened_points.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=points[0])
        writer.writeheader()
        writer.writerows(points)
    with (output / "fit_summary.json").open("x", encoding="ascii") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")

    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    ax.scatter(density, radius, color="#236b73", label="screened short-run peaks")
    rejected = [point for point in points if not point["accepted"]]
    if rejected:
        ax.scatter([p["n_ref_cm3"] for p in rejected],
                   [p["shell_peak_pc"] for p in rejected], marker="x",
                   color="#af4d35", label="quality gate failed")
    grid = np.geomspace(density.min(), density.max(), 200)
    ax.plot(grid, np.exp(intercept) * (grid / n_pivot) ** slope,
            color="#252b32", label="exploratory one-parameter fit")
    ax.set(xscale="log", yscale="log", xlabel=r"Core $n_{\rm ref}$ at 1 pc (cm$^{-3}$)",
           ylabel="Native density-excess peak radius (pc)",
           title=f"{label}: {result['age_myr']:.2f} Myr")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(output / "shell_radius_family.png", dpi=180)
    plt.close(fig)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--label", required=True)
    parser.add_argument("--mesh-tag", required=True,
                        help="Case-name token identifying the common native mesh rung")
    args = parser.parse_args()
    fit(load_rows(args.inputs), args.label, args.output, args.mesh_tag)
