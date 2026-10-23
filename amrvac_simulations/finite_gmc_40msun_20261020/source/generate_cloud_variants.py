#!/usr/bin/env python3
"""Generate one-factor-at-a-time finite-cloud profile/gravity controls."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from generate_cloud_mass_cases import CODE_TIME_PER_MYR

VARIANTS = (
    ("core1pcw05", "Keohane1", 1.0, 0.5, 1.8, 40.0),
    ("core3pc", "Keohane2", 3.0, 0.75, 1.8, 40.0),
    ("slope16", "Keohane3", 2.0, 0.5, 1.6, 40.0),
    ("gasonly", "Keohane4", 2.0, 0.5, 1.8, 0.0),
)


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for name, host, cloud, width, slope, star in VARIANTS:
        for stage, wind, ionization, intervals in (
            ("atmosphere", False, False, 1),
            ("wind", True, True, 5),
        ):
            prefix = f"cloudmass_{name}_nref1000_{stage}"
            text = f"""! One-factor cloud/gravity control against nref1000 baseline.
&filelist
  base_filename = '{prefix}'
  saveprim = .true.
  autoconvert = .true.
  convert_type = 'vtuBmpi'
/
&savelist
  dtsave_dat = {0.1 * CODE_TIME_PER_MYR / intervals:.16e}
/
&stoplist
  time_max = {0.1 * CODE_TIME_PER_MYR:.16e}
  final_dt_reduction = .true.
  dtmin = 1.0d-12
/
&hd_list
  hd_gravity = .true.
/
&usr_list
  n_ref_cm3 = 1000.0d0
  cloud_pc = {cloud:.2f}d0
  edge_width_pc = {width:.2f}d0
  slope_p = {slope:.2f}d0
  star_mass_msun = {star:.2f}d0
  wind_enabled = {'.true.' if wind else '.false.'}
  ionization_enabled = {'.true.' if ionization else '.false.'}
  cloud_gravity_enabled = .true.
/
"""
            (output / f"{prefix}.par").write_text(text, encoding="ascii")
            rows.append(dict(case=prefix, variant=name, host=host, stage=stage,
                             n_ref_cm3=1000, cloud_pc=cloud,
                             edge_width_pc=width, slope_p=slope,
                             star_mass_msun=star, endpoint_myr=0.1,
                             expected_vtus=intervals + 1))
    with (output / "manifest.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    generate(parser.parse_args().output)
