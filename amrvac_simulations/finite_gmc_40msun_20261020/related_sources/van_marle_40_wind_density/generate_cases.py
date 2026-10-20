#!/usr/bin/env python3
"""Stage unlaunched 1D single-star density/physics inputs without overwriting."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PROTON_G = 1.6726219e-24
K_B = 1.380649e-16
PC_CM = 3.0857e18
YEAR_S = 3.1536e7
TIME_UNIT = PC_CM / 1.0e7
TEMP_UNIT = (1.4 / 2.3) * PROTON_G * 1.0e14 / K_B
AMBIENTS = {
    "paper": 10.0 ** -22.5 / PROTON_G,
    "n100": 100.0,
    "n1000": 1000.0,
}
PHYSICS = {
    "hydro": (False, False),
    "cooling": (True, False),
    "conduction": (False, True),
    "cooling_conduction": (True, True),
}


def wind_at_age(age_myr: float) -> tuple[float, float]:
    if age_myr < 4.3:
        return 1e-6, 2000.0
    if age_myr < 4.5:
        return 5e-5, 15.0
    if age_myr <= 4.77:
        return 1e-5, 2000.0
    raise ValueError("The wind-only model ends at 4.77 Myr")


def case_text(name: str, rho: float, cooling: bool, conduction: bool) -> str:
    boolean = lambda value: ".true." if value else ".false."
    end = 4.77e6 * YEAR_S / TIME_UNIT
    save = 0.05e6 * YEAR_S / TIME_UNIT
    floor = 100.0 / TEMP_UNIT
    return f"""! 40 Msun wind-only pilot, van Marle et al. (2012) Table 1.
! No supernova, companion, production launch, or convergence claim.
&filelist
  base_filename = 'output/{name}'
  saveprim = .true.
  autoconvert = .true.
  convert_type = 'vtuBmpi'
/
&savelist
  itsave(1,1) = 0
  itsave(1,2) = 0
  ditsave_log = 1000
  dtsave_dat = {save:.16e}
/
&stoplist
  time_max = {end:.16e}
  final_dt_reduction = .true.
  dtmin = 1.0d-12
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
  refine_criterion = 3
  refine_max_level = 2
  w_refine_weight(1) = 0.5d0
  w_refine_weight(2) = 0.25d0
  w_refine_weight(3) = 0.25d0
  refine_threshold = 20*0.15d0
  derefine_ratio = 20*0.1d0
  domain_nx1 = 512
  block_nx1 = 8
  xprobmin1 = 1.5d0
  xprobmax1 = 100.0d0
/
&paramlist
  typecourant = 'maxsum'
  courantpar = 0.3d0
  slowsteps = 50
/
&hd_list
  hd_energy = .true.
  hd_radiative_cooling = {boolean(cooling)}
  hd_thermal_conduction = {boolean(conduction)}
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
  ! Built-in solar CLOUDY table is a candidate, not proven paper-identical.
  coolcurve = 'cloudy_solar'
  coolmethod = 'exact'
  Tfix = .true.
  tlow = {floor:.16e}
/
&usr_list
  ambient_rho_cgs = {rho:.16e}
/
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "cases")
    args = parser.parse_args()
    root = args.output_dir.resolve()
    if root.exists() and any(root.iterdir()):
        parser.error(f"refusing to overwrite nonempty directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for density, n_ism in AMBIENTS.items():
        for physics, (cooling, conduction) in PHYSICS.items():
            name = f"star40_{density}_{physics}"
            folder = root / name
            folder.mkdir()
            (folder / "run.par").write_text(
                case_text(name, n_ism * PROTON_G, cooling, conduction), encoding="ascii"
            )
            (folder / "mod_usr.t").symlink_to(Path("../..") / "mod_usr.t")
            rows.append((name, f"{n_ism:.10g}", f"{n_ism * PROTON_G:.10e}",
                         int(cooling), int(conduction), "not_run"))
    with (root / "matrix.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.writer(handle)
        writer.writerow(("case", "n_ism_cm-3_rho_over_mp", "rho_ism_g_cm-3",
                         "cooling", "conduction", "status"))
        writer.writerows(rows)
    with (root / "wind_history.csv").open("w", newline="", encoding="ascii") as handle:
        writer = csv.writer(handle)
        writer.writerow(("phase", "start_myr", "end_myr", "mdot_msun_per_yr",
                         "velocity_km_per_s", "assumed_wind_temperature_k"))
        writer.writerows((
            ("MS", 0.0, 4.3, 1e-6, 2000.0, 10000.0),
            ("RSG", 4.3, 4.5, 5e-5, 15.0, 1000.0),
            ("WR", 4.5, 4.77, 1e-5, 2000.0, 10000.0),
        ))
    print(f"Staged {len(rows)} unlaunched 1D inputs at {root}")


if __name__ == "__main__":
    main()
