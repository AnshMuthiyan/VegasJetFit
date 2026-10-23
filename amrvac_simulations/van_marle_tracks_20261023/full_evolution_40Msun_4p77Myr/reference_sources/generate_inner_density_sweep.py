#!/usr/bin/env python3
"""Generate isolated, smaller-inner-boundary density tests without overwrites."""

from __future__ import annotations

from pathlib import Path


HERE = Path(__file__).resolve().parent
OUT = HERE / "density_inputs_inner0p01_20261014"
RUNS = {
    1024: {20000: ("0p1myr", "4p77myr"),
           40000: ("0p1myr", "4p77myr")},
    2048: {20000: ("0p1myr",),
           40000: ("0p1myr",),
           80000: ("0p1myr",)},
}
DURATIONS = {
    "0p1myr": ("2.044024313763843d0", "1.0220121568819214d1"),
    "4p77myr": ("1.0220121568819214d1", "4.8749979883267656d2"),
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for resolution, densities in RUNS.items():
        for n0, durations in densities.items():
            for gravity in (True, False):
                branch = "gravity" if gravity else "nogravity"
                for duration in durations:
                    save_step, stop_time = DURATIONS[duration]
                    prefix = f"ion_{branch}_n{n0:05d}_inner0p01_r{resolution}_{duration}"
                    path = OUT / f"{prefix}.par"
                    content = f"""! Separate 0.01 pc inner-boundary density series; see README.
&filelist
  base_filename = '{prefix}'
  saveprim = .true.
  autoconvert = .true.
  convert_type = 'vtuBmpi'
/
&savelist
  dtsave_dat = {save_step}
/
&stoplist
  time_max = {stop_time}
  final_dt_reduction = .true.
  dtmin = 1.0d-12
/
&hd_list
  hd_gravity = {'.true.' if gravity else '.false.'}
/
&usr_list
  n0_cm3 = {n0}.0d0
  wind_enabled = .true.
  ionization_enabled = .true.
/
"""
                    if path.exists():
                        if path.read_text(encoding="ascii") != content:
                            raise FileExistsError(f"different existing case file: {path}")
                        continue
                    path.write_text(content, encoding="ascii")
                    print(path)


if __name__ == "__main__":
    main()
