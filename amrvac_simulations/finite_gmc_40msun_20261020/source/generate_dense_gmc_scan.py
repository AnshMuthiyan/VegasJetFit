#!/usr/bin/env python3
"""Stage distinct finite-GMC core tests without launching full lifetimes."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

CODE_TIME_PER_MYR = 102.20121568819214
DOMAIN_PC = 20.0
CELLS = 2048
# The pinned AMRVAC converter uses character(len=80) for VTU filenames.
VTU_FILENAME_LIMIT = 80
CASES = (
    ("Keohane1", 1000, 100, 0.01, 0.004),
    ("Keohane2", 3000, 300, 0.01, 0.004),
    ("Keohane3", 10000, 1000, 0.001, 0.001),
    ("Keohane4", 30000, 3000, 0.001, 0.001),
)
INTERMEDIATE_CASES = (
    ("Keohane3", 5000, 500, 0.01, 0.004),
    ("Keohane4", 20000, 2000, 0.001, 0.001),
)
WR_ONLY_CASES = (
    ("Keohane1", 3000, 300, 0.01, 0.004),
    ("Keohane2", 5000, 500, 0.01, 0.004),
    ("Keohane3", 10000, 1000, 0.001, 0.001),
    ("Keohane4", 20000, 2000, 0.001, 0.001),
)
ORTHOGONAL_WR_CASES = (
    ("Keohane1", 5000, 250, 0.01, 0.004),
    ("Keohane2", 5000, 1000, 0.01, 0.004),
    ("Keohane3", 10000, 500, 0.001, 0.001),
    ("Keohane4", 10000, 2000, 0.001, 0.001),
)
ORTHOGONAL_WR_MAC_N3000_CASES = (
    ("Pauley404-01", 3000, 150, 0.01, 0.004),
    ("Pauley404-02", 3000, 600, 0.01, 0.004),
)
ORTHOGONAL_WR_MAC_N3000_WIDE_CASES = (
    ("Pauley404-01", 3000, 100, 0.01, 0.004),
    ("Pauley404-02", 3000, 1200, 0.01, 0.004),
)
ORTHOGONAL_WR_MAC_N3000_TRANSITION_CASES = (
    ("Pauley404-02", 3000, 900, 0.01, 0.004),
)
ORTHOGONAL_WR_MAC_N20000_LOW_CASES = (
    ("Pauley404-03", 20000, 1000, 0.001, 0.001),
)
ORTHOGONAL_WR_MAC_N1000_UPPER_CASES = (
    ("Pauley404-03", 1000, 50, 0.01, 0.004),
)
ORTHOGONAL_WR_VM_N5000_WIDE_CASES = (
    ("Keohane1", 5000, 125, 0.01, 0.004),
    ("Keohane2", 5000, 2000, 0.01, 0.004),
)
ORTHOGONAL_WR_VM_N5000_TRANSITION_CASES = (
    ("Keohane2", 5000, 1500, 0.01, 0.004),
)
ORTHOGONAL_WR_VM_N1000_LOW_CASES = (
    ("Keohane2", 1000, 100, 0.01, 0.004),
)
ORTHOGONAL_WR_VM_N1000_UPPER_CASES = (
    ("Keohane2", 1000, 50, 0.01, 0.004),
)
ORTHOGONAL_WR_VM_N20000_EARLY_CASES = (
    ("Keohane1", 20000, 1000, 0.001, 0.001),
)
ORTHOGONAL_WR_VM_N10000_TRANSITION_CASES = (
    ("Keohane3", 10000, 1500, 0.001, 0.001),
    ("Keohane4", 10000, 3000, 0.001, 0.001),
)


def stretch_ratio(inner_pc: float, first_width_pc: float, cells: int,
                  domain_max_pc: float = DOMAIN_PC) -> float:
    distance = domain_max_pc - inner_pc
    if distance <= cells * first_width_pc:
        raise ValueError("domain must exceed the span of uniform first-width cells")
    lo, hi = 1.0, 1.02
    for _ in range(100):
        q = (lo + hi) / 2.0
        span = first_width_pc * (q**cells - 1.0) / (q - 1.0)
        if span < distance:
            lo = q
        else:
            hi = q
    return (lo + hi) / 2.0


def write_new(path: Path, body: str) -> None:
    with path.open("x", encoding="ascii") as stream:
        stream.write(body)


def generate(output: Path, cells: int = CELLS,
             selected: set[str] | None = None, suffix: str = "",
             intermediate: bool = False, wr_only: bool = False,
             wr_duration_myr: float = 0.1, wind_only: bool = False,
             wind_save_interval_myr: float | None = None,
             orthogonal_wr: bool = False,
             orthogonal_wr_mac_n3000: bool = False,
             orthogonal_wr_vm_n5000_wide: bool = False,
             orthogonal_wr_vm_n5000_transition: bool = False,
             orthogonal_wr_vm_n1000_low: bool = False,
             orthogonal_wr_vm_n1000_upper: bool = False,
             orthogonal_wr_vm_n20000_early: bool = False,
             orthogonal_wr_vm_n10000_transition: bool = False,
             orthogonal_wr_mac_n3000_wide: bool = False,
             orthogonal_wr_mac_n3000_transition: bool = False,
             orthogonal_wr_mac_n20000_low: bool = False,
             orthogonal_wr_mac_n1000_upper: bool = False,
             domain_max_pc: float = DOMAIN_PC,
             atmosphere_outer_pc: float | None = None,
             inner_override_pc: float | None = None,
             first_width_override_pc: float | None = None,
             host_override: str | None = None) -> None:
    if cells < CELLS or cells % 8:
        raise ValueError("cells must be at least 2048 and divisible by 8")
    if intermediate and wr_only:
        raise ValueError("intermediate and WR-only case sets are exclusive")
    orthogonal_sets = sum((orthogonal_wr, orthogonal_wr_mac_n3000,
                           orthogonal_wr_vm_n5000_wide,
                           orthogonal_wr_vm_n5000_transition,
                           orthogonal_wr_vm_n1000_low,
                           orthogonal_wr_vm_n1000_upper,
                           orthogonal_wr_vm_n20000_early,
                           orthogonal_wr_vm_n10000_transition,
                           orthogonal_wr_mac_n3000_wide,
                           orthogonal_wr_mac_n3000_transition,
                           orthogonal_wr_mac_n20000_low,
                           orthogonal_wr_mac_n1000_upper))
    if orthogonal_sets and not wr_only:
        raise ValueError("orthogonal GMC brackets require --wr-only")
    if orthogonal_sets > 1:
        raise ValueError("select one orthogonal case set")
    if (wind_only or wr_duration_myr != 0.1) and not wr_only:
        raise ValueError("wind-only and WR duration require --wr-only")
    if wr_only and not 0.001 <= wr_duration_myr <= 0.27:
        raise ValueError("WR duration must be 0.001-0.27 Myr")
    overrides = (domain_max_pc != DOMAIN_PC or atmosphere_outer_pc is not None
                 or inner_override_pc is not None or first_width_override_pc is not None
                 or host_override is not None)
    if overrides and (not wr_only or selected is None or len(selected) != 1 or not suffix):
        raise ValueError("boundary/host overrides require one selected WR case and a suffix")
    if (inner_override_pc is None) != (first_width_override_pc is None):
        raise ValueError("inner radius and first-cell width overrides must be paired")
    if domain_max_pc < DOMAIN_PC and atmosphere_outer_pc is None:
        raise ValueError("short evolved domains require an explicit atmosphere reference")
    reference_outer_pc = (domain_max_pc if atmosphere_outer_pc is None
                          else atmosphere_outer_pc)
    if not 0 < domain_max_pc <= reference_outer_pc:
        raise ValueError("atmosphere reference must cover the positive evolved domain")
    if wind_save_interval_myr is None:
        intervals = max(1, round(wr_duration_myr / 0.02))
    else:
        if not wr_only or wind_save_interval_myr <= 0:
            raise ValueError("wind save interval must be positive and requires WR-only mode")
        intervals = round(wr_duration_myr / wind_save_interval_myr)
        if intervals < 1 or not math.isclose(intervals * wind_save_interval_myr,
                                             wr_duration_myr, rel_tol=0, abs_tol=1e-10):
            raise ValueError("WR duration must be an integer number of save intervals")
    cases = (ORTHOGONAL_WR_MAC_N1000_UPPER_CASES if orthogonal_wr_mac_n1000_upper
             else ORTHOGONAL_WR_VM_N20000_EARLY_CASES if orthogonal_wr_vm_n20000_early
             else ORTHOGONAL_WR_MAC_N20000_LOW_CASES if orthogonal_wr_mac_n20000_low
             else ORTHOGONAL_WR_MAC_N3000_TRANSITION_CASES if orthogonal_wr_mac_n3000_transition
             else ORTHOGONAL_WR_VM_N10000_TRANSITION_CASES if orthogonal_wr_vm_n10000_transition
             else ORTHOGONAL_WR_VM_N1000_LOW_CASES if orthogonal_wr_vm_n1000_low
             else ORTHOGONAL_WR_VM_N1000_UPPER_CASES if orthogonal_wr_vm_n1000_upper
             else ORTHOGONAL_WR_VM_N5000_TRANSITION_CASES if orthogonal_wr_vm_n5000_transition
             else ORTHOGONAL_WR_VM_N5000_WIDE_CASES if orthogonal_wr_vm_n5000_wide
             else ORTHOGONAL_WR_MAC_N3000_WIDE_CASES if orthogonal_wr_mac_n3000_wide
             else ORTHOGONAL_WR_MAC_N3000_CASES if orthogonal_wr_mac_n3000
             else ORTHOGONAL_WR_CASES if orthogonal_wr else WR_ONLY_CASES if wr_only
             else INTERMEDIATE_CASES if intermediate else CASES)
    known = {f"n{n_ref:05d}b{n_gmc:04d}" for _, n_ref, n_gmc, _, _ in cases}
    if selected is not None and not selected <= known:
        raise ValueError(f"unknown case tags: {sorted(selected - known)}")
    stages = ("wind",) if wind_only else ("atmosphere", "wind") if wr_only else ("atmosphere", "wind", "full")
    for _, n_ref, n_gmc, _, _ in cases:
        tag = f"n{n_ref:05d}b{n_gmc:04d}"
        if selected is not None and tag not in selected:
            continue
        for stage in stages:
            filename = f"cloudmass_gmc_{tag}{suffix}_{stage}0000.vtu"
            if len(filename) > VTU_FILENAME_LIMIT:
                raise ValueError(f"VTU filename exceeds {VTU_FILENAME_LIMIT} characters: {filename}")
    output.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, object]] = []
    for host, n_ref, n_gmc, inner_pc, reference_first_width_pc in cases:
        tag = f"n{n_ref:05d}b{n_gmc:04d}"
        if selected is not None and tag not in selected:
            continue
        if host_override is not None:
            host = host_override
        if inner_override_pc is not None:
            inner_pc = inner_override_pc
        first_width_pc = (reference_first_width_pc * CELLS / cells
                          if first_width_override_pc is None else first_width_override_pc)
        if not 0 < inner_pc < domain_max_pc or not 0 < first_width_pc < domain_max_pc - inner_pc:
            raise ValueError("invalid inner radius or first-cell width")
        base_name = f"dense_gmc_base_{tag}{suffix}.par"
        q = stretch_ratio(inner_pc, first_width_pc, cells, domain_max_pc)
        atmosphere_reference = (f"  atmosphere_outer_pc = {reference_outer_pc:.8f}d0\n"
                                if atmosphere_outer_pc is not None else "")
        base = f"""! Finite 15-pc GMC with 2-pc massive core; no cooling or conduction.
&filelist
  base_filename = 'output/'
/
&savelist
  itsave(1,1) = 0
  itsave(1,2) = 0
  ditsave_log = 1000
/
&methodlist
  time_stepper = 'threestep'
  flux_scheme = 20*'tvdlf'
  limiter = 20*'minmod'
  loglimit(1) = .true.
  loglimit(3) = .true.
  check_small_values = .true.
  fix_small_values = .true.
  small_values_method = 'error'
  small_pressure = 1.0d-16
  small_density = 1.0d-14
/
&boundlist
  typeboundary_min1 = 3*'special'
  typeboundary_max1 = 3*'special'
/
&meshlist
  refine_max_level = 1
  domain_nx1 = {cells}
  block_nx1 = 8
  xprobmin1 = {inner_pc:.8f}d0
  xprobmax1 = {domain_max_pc:.8f}d0
  stretch_dim(1) = 'uni'
  qstretch_baselevel(1) = {q:.16f}d0
/
&paramlist
  typecourant = 'maxsum'
  courantpar = 0.2d0
  slowsteps = 10
/
&hd_list
  hd_energy = .true.
  hd_radiative_cooling = .false.
  hd_thermal_conduction = .false.
/
&usr_list
  n_ref_cm3 = {n_ref}.0d0
  r_flat_pc = 0.2d0
  slope_p = 1.8d0
  cloud_pc = 2.0d0
  edge_width_pc = 0.5d0
  n_bg_cm3 = {n_gmc}.0d0
  finite_gmc_enabled = .true.
  n_ext_cm3 = 10.0d0
  gmc_pc = 15.0d0
  gmc_edge_width_pc = 1.0d0
  star_mass_msun = 40.0d0
  support_kms = 0.72d0
  q_ms = 2.0d49
  q_rsg = 0.0d0
  q_wr = 2.0d49
{atmosphere_reference.rstrip()}
/
"""
        write_new(output / base_name, base)
        wr_intervals = intervals
        stages = (
            ("atmosphere", False, False, 0.1, 1, 7200),
            ("wind", True, True, wr_duration_myr if wr_only else 0.1,
             wr_intervals if wr_only else 5,
             36000 if wr_only and wr_duration_myr > 0.1 else 28800),
            ("full", True, True, 4.77, 48, 0),
        )
        for stage, wind, ionized, age, intervals, guard in (
            stages[1:2] if wind_only else stages[:2] if wr_only else stages
        ):
            case = f"cloudmass_gmc_{tag}{suffix}_{stage}"
            par = f"""&filelist
  base_filename = '{case}'
  saveprim = .true.
  autoconvert = .true.
  convert_type = 'vtuBmpi'
/
&savelist
  dtsave_dat = {age * CODE_TIME_PER_MYR / intervals:.16e}
/
&stoplist
  time_max = {age * CODE_TIME_PER_MYR:.16e}
  final_dt_reduction = .true.
  dtmin = 1.0d-12
/
&hd_list
  hd_gravity = .true.
/
&usr_list
  wind_enabled = {'.true.' if wind else '.false.'}
  ionization_enabled = {'.true.' if ionized else '.false.'}
  cloud_gravity_enabled = .true.
  wind_phase_age_offset_myr = {4.5 if wr_only and wind else 0.0:.1f}d0
/
"""
            write_new(output / f"{case}.par", par)
            rows.append(dict(case=case, host=host, stage=stage,
                             n_ref_cm3=n_ref, n_gmc_cm3=n_gmc,
                             inner_pc=inner_pc, first_width_pc=first_width_pc,
                             base_file=base_name, domain_max_pc=domain_max_pc,
                             atmosphere_outer_pc=reference_outer_pc,
                             endpoint_myr=age, expected_vtus=intervals + 1,
                             guard_seconds=guard,
                             wind_phase_age_offset_myr=4.5 if wr_only and wind else 0.0))
    with (output / "manifest.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cells", type=int, default=CELLS)
    parser.add_argument("--case", action="append", dest="cases",
                        help="Select a density tag; repeat for multiple cases")
    parser.add_argument("--suffix", default="",
                        help="Distinct case suffix for a new resolution rung")
    parser.add_argument("--intermediate", action="store_true",
                        help="Generate the 5000 and 20000 cm^-3 bracket cases")
    parser.add_argument("--wr-only", action="store_true",
                        help="Generate matched direct-WR pilots without full stages")
    parser.add_argument("--wr-duration-myr", type=float, default=0.1,
                        help="WR-only wind duration, at most the 0.27-Myr WR phase")
    parser.add_argument("--wind-save-interval-myr", type=float,
                        help="WR-only output cadence, exactly dividing the duration")
    parser.add_argument("--wind-only", action="store_true",
                        help="Stage only a WR wind after the identical base atmosphere was validated")
    parser.add_argument("--domain-max-pc", type=float, default=DOMAIN_PC)
    parser.add_argument("--atmosphere-outer-pc", type=float,
                        help="Hydrostatic pressure-table reference radius when evolving a short domain")
    parser.add_argument("--inner-pc", type=float, help="Opt-in inner boundary for one WR case")
    parser.add_argument("--first-width-pc", type=float,
                        help="Opt-in first native cell width for one WR case")
    parser.add_argument("--host", help="Manifest host for one selected WR case")
    parser.add_argument("--orthogonal-wr", action="store_true",
                        help="Vary GMC density independently at fixed core density")
    parser.add_argument("--orthogonal-wr-mac-n3000", action="store_true",
                        help="Stage the 3000 cm^-3 core, GMC 150/600 Mac bracket")
    parser.add_argument("--orthogonal-wr-mac-n3000-wide", action="store_true",
                        help="Stage the 3000 cm^-3 core, GMC 100/1200 Mac bracket")
    parser.add_argument("--orthogonal-wr-mac-n3000-transition", action="store_true",
                        help="Stage the 3000 cm^-3 core, GMC 900 temporal-transition case")
    parser.add_argument("--orthogonal-wr-mac-n20000-low", action="store_true",
                        help="Stage the 20000 cm^-3 core, GMC 1000 Mac contrast test")
    parser.add_argument("--orthogonal-wr-mac-n1000-upper", action="store_true",
                        help="Stage the 1000 cm^-3 core, GMC 50 Mac mesh test")
    parser.add_argument("--orthogonal-wr-vm-n5000-wide", action="store_true",
                        help="Stage the 5000 cm^-3 core, GMC 125/2000 VM bracket")
    parser.add_argument("--orthogonal-wr-vm-n5000-transition", action="store_true",
                        help="Stage the 5000 cm^-3 core, GMC 1500 transition case")
    parser.add_argument("--orthogonal-wr-vm-n1000-low", action="store_true",
                        help="Stage the 1000 cm^-3 core, GMC 100 upper-radius test")
    parser.add_argument("--orthogonal-wr-vm-n1000-upper", action="store_true",
                        help="Stage the 1000 cm^-3 core, GMC 50 upper-radius bracket")
    parser.add_argument("--orthogonal-wr-vm-n20000-early", action="store_true",
                        help="Stage the 20000 cm^-3 core, GMC 100 early-radius mesh test")
    parser.add_argument("--orthogonal-wr-vm-n10000-transition", action="store_true",
                        help="Stage the 10000 cm^-3 core, GMC 1500/3000 transition bracket")
    args = parser.parse_args()
    generate(args.output, args.cells,
             set(args.cases) if args.cases else None, args.suffix,
             args.intermediate, args.wr_only,
             args.wr_duration_myr, args.wind_only, args.wind_save_interval_myr,
             args.orthogonal_wr,
             args.orthogonal_wr_mac_n3000,
             args.orthogonal_wr_vm_n5000_wide,
             args.orthogonal_wr_vm_n5000_transition,
             args.orthogonal_wr_vm_n1000_low,
             args.orthogonal_wr_vm_n1000_upper,
             args.orthogonal_wr_vm_n20000_early,
             args.orthogonal_wr_vm_n10000_transition,
             args.orthogonal_wr_mac_n3000_wide,
             args.orthogonal_wr_mac_n3000_transition,
             args.orthogonal_wr_mac_n20000_low,
             args.orthogonal_wr_mac_n1000_upper,
             args.domain_max_pc, args.atmosphere_outer_pc,
             args.inner_pc, args.first_width_pc, args.host)
