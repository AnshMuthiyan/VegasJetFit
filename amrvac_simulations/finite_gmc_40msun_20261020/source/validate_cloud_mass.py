#!/usr/bin/env python3
"""Check a finite-cloud AMRVAC case before its results enter science plots."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import numpy as np

from validate_smoke import MP_G, RHO_UNIT, read_vtu

MASS_PER_H = 1.4 * MP_G
PC_CM = 3.085677581e18
G_CGS = 6.67430e-8
MSUN_G = 1.98847e33
PRESSURE_UNIT = 1.0e-11
SPEED_UNIT = 1.0e7
N_BG = 10.0


def profile_nh(r: np.ndarray, n_ref: float, edge_width: float = 0.2,
               cloud_pc: float = 2.0, slope: float = 1.8,
               r_flat_pc: float = 0.2, n_bg: float = N_BG,
               finite_gmc: bool = False, n_ext: float = 10.0,
               gmc_pc: float = 15.0, gmc_edge_width: float = 1.0) -> np.ndarray:
    core = n_ref * ((1.0 + (1.0 / r_flat_pc) ** 2) /
                    (1.0 + (r / r_flat_pc) ** 2)) ** (0.5 * slope)
    taper = 0.5 * (1.0 - np.tanh((r - cloud_pc) / edge_width))
    ambient = n_bg
    if finite_gmc:
        ambient = n_ext + (n_bg - n_ext) * 0.5 * (
            1.0 - np.tanh((r - gmc_pc) / gmc_edge_width))
    return ambient + np.maximum(0.0, core - ambient) * taper


def atmosphere_table(n_ref: float, edge_width: float = 0.2,
                     cloud_pc: float = 2.0, slope: float = 1.8,
                     star_mass_msun: float = 40.0,
                     domain_max_pc: float = 40.0, inner_pc: float = 0.01,
                     n_bg: float = N_BG, finite_gmc: bool = False,
                     n_ext: float = 10.0, gmc_pc: float = 15.0,
                     gmc_edge_width: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    radius = np.geomspace(inner_pc, domain_max_pc, 100001)
    midpoint = 0.5 * (radius[:-1] + radius[1:])
    density = profile_nh(midpoint, n_ref, edge_width, cloud_pc, slope,
                         n_bg=n_bg, finite_gmc=finite_gmc, n_ext=n_ext,
                         gmc_pc=gmc_pc, gmc_edge_width=gmc_edge_width)
    excess = density if finite_gmc else np.maximum(0.0, density - n_bg)
    shell_mass = 4.0 * np.pi * (midpoint * PC_CM) ** 2 * (
        excess * MASS_PER_H) * np.diff(radius) * PC_CM
    mass = star_mass_msun * MSUN_G + np.r_[0.0, np.cumsum(shell_mass)]
    g = -G_CGS * mass / (radius * PC_CM) ** 2
    gmid = -G_CGS * 0.5 * (mass[:-1] + mass[1:]) / (midpoint * PC_CM) ** 2
    dp = density * MASS_PER_H * (-gmid) * np.diff(radius) * PC_CM
    pressure = (n_ext if finite_gmc else n_bg) * MASS_PER_H * (0.72e5) ** 2 + np.r_[np.cumsum(dp[::-1])[::-1], 0.0]
    return radius, mass, g, pressure


def stromgren_front_pc(n_ref: float, edge_width: float, cloud_pc: float = 2.0,
                      slope: float = 1.8, domain_max_pc: float = 40.0,
                      inner_pc: float = 0.01, n_bg: float = N_BG,
                      finite_gmc: bool = False, n_ext: float = 10.0,
                      gmc_pc: float = 15.0, gmc_edge_width: float = 1.0) -> float:
    radius = np.geomspace(inner_pc, domain_max_pc, 100001)
    midpoint = 0.5 * (radius[:-1] + radius[1:])
    density = profile_nh(midpoint, n_ref, edge_width, cloud_pc, slope,
                         n_bg=n_bg, finite_gmc=finite_gmc, n_ext=n_ext,
                         gmc_pc=gmc_pc, gmc_edge_width=gmc_edge_width)
    recombinations = 2.6e-13 * density ** 2 * (
        4.0 * np.pi * midpoint**2 * np.diff(radius) * PC_CM**3)
    index = int(np.searchsorted(np.cumsum(recombinations), 2.0e49))
    return float(midpoint[min(index, len(midpoint) - 1)])


def validate(root: Path, prefix: str, n_ref: float, endpoint_myr: float,
             expected_vtus: int, atmosphere: bool, edge_width: float = 0.2,
             cloud_pc: float = 2.0, slope: float = 1.8,
             star_mass_msun: float = 40.0, domain_max_pc: float = 40.0,
             inner_pc: float = 0.01, n_bg: float = N_BG,
             finite_gmc: bool = False, n_ext: float = 10.0,
             gmc_pc: float = 15.0, gmc_edge_width: float = 1.0,
             expected_mdot_msun_yr: float | None = None,
             atmosphere_outer_pc: float | None = None) -> dict:
    reference_outer_pc = (domain_max_pc if atmosphere_outer_pc is None
                          else atmosphere_outer_pc)
    if not 0 < inner_pc < domain_max_pc <= reference_outer_pc:
        raise ValueError("invalid evolved or atmosphere-reference radial domain")
    if (root / f"{prefix}.run.exit").read_text(encoding="ascii").strip() != "0":
        raise ValueError(f"nonzero exit: {prefix}")
    log = (root / f"{prefix}.run.log").read_text(encoding="utf-8")
    if log.count("Finished AMRVAC") != 1 or (root / f"{prefix}.run.err").stat().st_size:
        raise ValueError(f"missing normal completion or nonempty stderr: {prefix}")
    mass_record = re.search(r"^ CLOUD_MASS\s+([\d.E+-]+)\s+([\d.E+-]+)\s+([\d.E+-]+)\s+([\d.E+-]+)", log, re.M)
    if mass_record is None:
        raise ValueError(f"missing enclosed-mass provenance: {prefix}")
    vtu_paths = sorted(root.glob(f"{prefix}[0-9][0-9][0-9][0-9].vtu"))
    if len(vtu_paths) != expected_vtus:
        raise ValueError(f"{prefix}: {len(vtu_paths)} VTUs, expected {expected_vtus}")
    ages = []
    first = None
    last = None
    for path in vtu_paths:
        age_yr, data = read_vtu(path)
        ages.append(age_yr * 365.25 / 365.0 / 1.0e6)
        if not np.all(np.isfinite(data)) or np.any(data[:, 1] <= 0) or np.any(data[:, 3] <= 0):
            raise ValueError(f"bad saved field: {path}")
        if first is None:
            first = data
        last = data
    if not np.all(np.diff(ages) > 0) or abs(ages[0]) > 1e-8 or abs(ages[-1] - endpoint_myr) > 3e-5:
        raise ValueError(f"wrong save ages: {prefix}: {ages[0]}, {ages[-1]}")
    assert first is not None and last is not None
    n_initial = first[:, 1] * RHO_UNIT / MASS_PER_H
    expected_n = profile_nh(first[:, 0], n_ref, edge_width, cloud_pc, slope,
                            n_bg=n_bg, finite_gmc=finite_gmc, n_ext=n_ext,
                            gmc_pc=gmc_pc, gmc_edge_width=gmc_edge_width)
    initial_check = first[:, 0] > (0.0 if atmosphere else 2.0 * inner_pc)
    if not np.allclose(n_initial[initial_check], expected_n[initial_check],
                       rtol=0.005, atol=0.02):
        raise ValueError(f"initial density profile mismatch: {prefix}")
    radial, mass, _, pressure = atmosphere_table(
        n_ref, edge_width, cloud_pc, slope, star_mass_msun, reference_outer_pc,
        inner_pc, n_bg, finite_gmc, n_ext, gmc_pc, gmc_edge_width)
    recorded_n, recorded_slope, recorded_mass, recorded_pressure = map(float, mass_record.groups())
    if (not np.isclose(recorded_n, n_ref, rtol=1e-6)
            or not np.isclose(recorded_slope, slope, rtol=1e-6)
            or not np.isclose(recorded_mass, mass[-1] / MSUN_G, rtol=0.002)
            or not np.isclose(recorded_pressure, pressure[0] / PRESSURE_UNIT, rtol=0.002)):
        raise ValueError(f"Fortran/Python atmosphere mismatch: {prefix}")
    expected_p = np.interp(first[:, 0], radial, pressure) / PRESSURE_UNIT
    # VTU values at the inner interface are reconstructed from cell centers.
    # The VTU boundary vertex mixes the last active and prescribed ghost cells.
    front_pc = stromgren_front_pc(n_ref, edge_width, cloud_pc, slope,
                                 domain_max_pc, inner_pc, n_bg, finite_gmc,
                                 n_ext, gmc_pc, gmc_edge_width)
    if reference_outer_pc != domain_max_pc and front_pc >= 0.8 * domain_max_pc:
        raise ValueError(f"ionized front too close to short-domain outer boundary: {prefix}")
    neutral_lower = ((0.05 if atmosphere else 10.0) if domain_max_pc >= 10.0
                     else max(0.05, 1.2 * front_pc))
    neutral = ((first[:, 0] > neutral_lower)
               & (first[:, 0] < domain_max_pc - 1.0e-5))
    if not np.any(neutral) or not np.allclose(first[neutral, 3], expected_p[neutral], rtol=0.01, atol=0.002):
        raise ValueError(f"initial hydrostatic pressure mismatch: {prefix}")
    outer = last[:, 0] > domain_max_pc - min(2.0, 0.1 * domain_max_pc)
    if (not np.any(outer)
            or not np.allclose(last[outer, 1], first[outer, 1], rtol=0.03)
            or not np.allclose(last[outer, 3], first[outer, 3], rtol=0.03)):
        raise ValueError(f"outer boundary drift: {prefix}")
    front_elements = int(np.count_nonzero(np.unique(first[:, 0]) <= front_pc) - 1)
    if "_full" in prefix and front_elements < 10:
        raise ValueError(f"under-resolved initial ionized zone: {prefix}: {front_elements} elements")
    if "_full" in prefix:
        for index, expected_kms, tolerance in ((44, 15.0, 0.10), (46, 2000.0, 0.05)):
            data = read_vtu(vtu_paths[index])[1]
            inner_speeds = data[data[:, 0] <= 0.15, 2] * SPEED_UNIT / 1.0e5
            # Saved active cells can differ from the prescribed ghost-cell speed.
            if not np.any(np.isclose(inner_speeds, expected_kms, rtol=tolerance)):
                raise ValueError(f"missing {expected_kms:g} km/s phase speed: {prefix}")
    elif "_wind" in prefix:
        inner_speeds = last[last[:, 0] <= 0.05, 2] * SPEED_UNIT / 1.0e5
        if not np.any(np.isclose(inner_speeds, 2000.0, rtol=0.05)):
            raise ValueError(f"missing main-sequence wind speed: {prefix}")
    measured_mdot = None
    if expected_mdot_msun_yr is not None:
        if atmosphere or expected_mdot_msun_yr <= 0:
            raise ValueError("mass-loss check requires a positive wind rate")
        inner = last[np.argsort(last[:, 0])]
        inner = inner[np.unique(inner[:, 0], return_index=True)[1]][:3]
        if len(inner) < 3 or inner[0, 0] > inner_pc * 1.01:
            raise ValueError(f"missing inner wind samples: {prefix}")
        flux = (4.0 * np.pi * (inner[:, 0] * PC_CM) ** 2
                * inner[:, 1] * RHO_UNIT * inner[:, 2] * SPEED_UNIT
                * (365.25 * 86400.0) / MSUN_G)
        measured_mdot = float(np.median(flux))
        if not np.isclose(measured_mdot, expected_mdot_msun_yr, rtol=0.05):
            raise ValueError(f"wrong inner wind mass-loss rate: {prefix}: {measured_mdot}")
    drift = float(np.max(np.abs(last[:, 1] / first[:, 1] - 1.0))) if atmosphere else float("nan")
    max_speed_kms = float(np.max(np.abs(last[:, 2])) * SPEED_UNIT / 1.0e5)
    if atmosphere and (drift > 0.12 or max_speed_kms > 1.0):
        raise ValueError(f"atmosphere unstable: {prefix}: drift={drift}, speed={max_speed_kms}")
    result = dict(case=prefix, n_ref_cm3=n_ref, age_myr=ages[-1],
                edge_width_pc=edge_width, cloud_pc=cloud_pc, slope_p=slope,
                star_mass_msun=star_mass_msun, domain_max_pc=domain_max_pc,
                atmosphere_outer_pc=reference_outer_pc,
                n_bg_cm3=n_bg, finite_gmc=finite_gmc, gmc_pc=gmc_pc,
                initial_front_pc=front_pc, initial_front_elements=front_elements,
                saved_vtus=len(vtu_paths), cloud_excess_mass_msun=(mass[-1] - star_mass_msun * MSUN_G) / MSUN_G,
                max_density_drift=drift, max_speed_kms=max_speed_kms)
    if measured_mdot is not None:
        result["inner_mdot_msun_yr"] = measured_mdot
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("prefix")
    parser.add_argument("n_ref_cm3", type=float)
    parser.add_argument("endpoint_myr", type=float)
    parser.add_argument("expected_vtus", type=int)
    parser.add_argument("--atmosphere", action="store_true")
    parser.add_argument("--edge-width-pc", type=float, default=0.2)
    parser.add_argument("--cloud-pc", type=float, default=2.0)
    parser.add_argument("--slope", type=float, default=1.8)
    parser.add_argument("--star-mass-msun", type=float, default=40.0)
    parser.add_argument("--domain-max-pc", type=float, default=40.0)
    parser.add_argument("--atmosphere-outer-pc", type=float,
                        help="Pressure-table anchor when evolving a short radial domain")
    parser.add_argument("--inner-pc", type=float, default=0.01)
    parser.add_argument("--n-bg", type=float, default=N_BG)
    parser.add_argument("--finite-gmc", action="store_true")
    parser.add_argument("--n-ext", type=float, default=10.0)
    parser.add_argument("--gmc-pc", type=float, default=15.0)
    parser.add_argument("--gmc-edge-width-pc", type=float, default=1.0)
    parser.add_argument("--expected-mdot-msun-yr", type=float)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    result = validate(args.root, args.prefix, args.n_ref_cm3, args.endpoint_myr,
                      args.expected_vtus, args.atmosphere, args.edge_width_pc,
                      args.cloud_pc, args.slope, args.star_mass_msun,
                      args.domain_max_pc, args.inner_pc, args.n_bg,
                      args.finite_gmc, args.n_ext, args.gmc_pc,
                      args.gmc_edge_width_pc, args.expected_mdot_msun_yr,
                      args.atmosphere_outer_pc)
    if args.csv:
        with args.csv.open("x", newline="", encoding="ascii") as stream:
            writer = csv.DictWriter(stream, fieldnames=result)
            writer.writeheader()
            writer.writerow(result)
    print("PASS", result)
