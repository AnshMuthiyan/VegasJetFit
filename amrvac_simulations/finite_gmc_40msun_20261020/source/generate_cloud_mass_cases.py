#!/usr/bin/env python3
"""Create a collision-checked finite-cloud 40 Msun test matrix."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

CODE_TIME_PER_MYR = 102.20121568819214
DENSITIES = (300, 600, 1000, 3000)
HOSTS = ("Keohane1", "Keohane2", "Keohane3", "Keohane4")
STAGES = (
    ("atmosphere", 0.1, False, False, 1, 7200),
    ("wind", 0.1, True, True, 5, 7200),
    ("full", 4.77, True, True, 48, 36000),
)


def generate(output: Path, densities: tuple[int, ...] = DENSITIES,
             hosts: tuple[str, ...] = HOSTS,
             base_file: str = "cloud_mass_base_1024_wideedge.par",
             domain_max_pc: float = 40.0,
             case_suffix: str = "") -> None:
    if len(densities) != len(hosts):
        raise ValueError("provide one assigned host per independent density case")
    if case_suffix and (not case_suffix.isalnum() or not case_suffix.islower()):
        raise ValueError("case suffix must be lowercase alphanumeric")
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for density, host in zip(densities, hosts, strict=True):
        for stage, age, wind, ionization, intervals, guard_s in STAGES:
            prefix = f"cloudmass_nref{density:04d}{'_' + case_suffix if case_suffix else ''}_{stage}"
            text = f"""! Finite tapered cloud; density parameter is n_H at 1 pc.
&filelist
  base_filename = '{prefix}'
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
  n_ref_cm3 = {density}.0d0
  wind_enabled = {'.true.' if wind else '.false.'}
  ionization_enabled = {'.true.' if ionization else '.false.'}
  cloud_gravity_enabled = .true.
/
"""
            (output / f"{prefix}.par").write_text(text, encoding="ascii")
            rows.append(dict(case=prefix, host=host, stage=stage,
                             n_ref_cm3=density, edge_width_pc=0.5,
                             base_file=base_file, domain_max_pc=domain_max_pc,
                             endpoint_myr=age,
                             expected_vtus=intervals + 1,
                             guard_seconds=guard_s))
    with (output / "manifest.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--densities", default=",".join(map(str, DENSITIES)))
    parser.add_argument("--hosts", default=",".join(HOSTS))
    parser.add_argument("--base-file", default="cloud_mass_base_1024_wideedge.par")
    parser.add_argument("--domain-max-pc", type=float, default=40.0)
    parser.add_argument("--case-suffix", default="")
    args = parser.parse_args()
    generate(args.output, tuple(map(int, args.densities.split(","))),
             tuple(args.hosts.split(",")), args.base_file, args.domain_max_pc,
             args.case_suffix)
