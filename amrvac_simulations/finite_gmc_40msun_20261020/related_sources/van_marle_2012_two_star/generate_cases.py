#!/usr/bin/env python3
"""Create the 3 x 4 van Marle comparison matrix without launching jobs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PC_CM = 3.0857e18
YEAR_S = 3.1536e7
PROTON_G = 1.6726219e-24
BOLTZMANN = 1.380649e-16
VELOCITY_UNIT = 1.0e7
TIME_UNIT = PC_CM / VELOCITY_UNIT
# AMRVAC v3.1 HD defaults: He/H=0.1, fully ionized H and He.
TEMPERATURE_UNIT = (1.4 / 2.3) * PROTON_G * VELOCITY_UNIT**2 / BOLTZMANN

STARS = {"star40": 1, "star25": 2, "both": 3}
PHYSICS = {
    "hydro": (False, False),
    "cooling": (True, False),
    "conduction": (False, True),
    "cooling_conduction": (True, True),
}


def case_text(star: str, physics: str) -> str:
    cooling, conduction = PHYSICS[physics]
    case_id = STARS[star]
    slug = f"{star}__{physics}"
    time_max = 7.1e6 * YEAR_S / TIME_UNIT
    save_dt = 0.1e6 * YEAR_S / TIME_UNIT
    floor_code = 100.0 / TEMPERATURE_UNIT
    bool_str = lambda value: ".true." if value else ".false."
    return f"""! van Marle, Meliani & Marcowith (2012), A&A 541 L8.
! PILOT INPUT ONLY: 120x240 base cells, maximum AMR level 2.
! Case {slug}; no production run is authorized by this file.
&filelist
  base_filename = 'output/{slug}'
  saveprim = .true.
  autoconvert = .true.
  convert_type = 'vtuBmpi'
/
&savelist
  itsave(1,1) = 0
  itsave(1,2) = 0
  ditsave_log = 1000
  dtsave_dat = {save_dt:.16e}
/
&stoplist
  time_max = {time_max:.16e}
  final_dt_reduction = .true.
  dtmin = 1.0d-12
/
&methodlist
  time_stepper = 'threestep'
  flux_scheme = 20*'tvdlf'
  limiter = 20*'minmod'
  loglimit(1) = .true.
  loglimit(4) = .true.
  check_small_values = .true.
  fix_small_values = .true.
  small_values_method = 'error'
  small_pressure = 1.0d-16
  small_density = 1.0d-14
/
&boundlist
  typeboundary_min1 = 'symm','asymm','symm','symm'
  typeboundary_max1 = 4*'cont'
  typeboundary_min2 = 4*'cont'
  typeboundary_max2 = 4*'cont'
/
&meshlist
  refine_criterion = 3
  refine_max_level = 2
  w_refine_weight(1) = 0.5d0
  w_refine_weight(2) = 0.25d0
  w_refine_weight(3) = 0.25d0
  refine_threshold = 20*0.15d0
  derefine_ratio = 20*0.1d0
  domain_nx1 = 120
  domain_nx2 = 240
  block_nx1 = 8
  block_nx2 = 8
  xprobmin1 = 0.0d0
  xprobmax1 = 100.0d0
  xprobmin2 = -100.0d0
  xprobmax2 = 100.0d0
/
&paramlist
  typecourant = 'maxsum'
  courantpar = 0.3d0
  slowsteps = 50
/
&hd_list
  hd_energy = .true.
  hd_radiative_cooling = {bool_str(cooling)}
  hd_thermal_conduction = {bool_str(conduction)}
/
&tc_list
  tc_saturate = .true.
/
&sts_list
  sts_method = 1
  sts_dtpar = 0.8d0
  sts_ncycles = 1000
  sourcetype_sts = 2
/
&rc_list
  ! SPEX_DM is a proxy; the paper's CLOUDY table is not available here.
  coolcurve = 'SPEX_DM'
  coolmethod = 'exact'
  Tfix = .true.
  tlow = {floor_code:.16e}
/
&usr_list
  case_id = {case_id}
/
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "cases")
    args = parser.parse_args()
    root = args.output_dir.resolve()
    source = Path(__file__).resolve().parent / "mod_usr.t"
    if not source.is_file():
        parser.error(f"missing shared source: {source}")
    if root.exists() and any(root.iterdir()):
        parser.error(f"refusing to overwrite nonempty directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for star, case_id in STARS.items():
        for physics, (cooling, conduction) in PHYSICS.items():
            slug = f"{star}__{physics}"
            folder = root / slug
            folder.mkdir()
            (folder / "run.par").write_text(case_text(star, physics), encoding="ascii")
            (folder / "mod_usr.t").symlink_to(Path("../..") / source.name)
            rows.append((slug, case_id, int(cooling), int(conduction), "not_run"))
    with (root / "matrix.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.writer(handle)
        writer.writerow(("case", "star_case_id", "cooling", "conduction", "status"))
        writer.writerows(rows)
    print(f"Wrote {len(rows)} unlaunched pilot cases to {root}")


if __name__ == "__main__":
    main()
