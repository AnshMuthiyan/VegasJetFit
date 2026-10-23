#!/usr/bin/env python3
"""Generate distinct low-resolution density-sweep AMRVAC case files."""

from __future__ import annotations

from pathlib import Path


HERE = Path(__file__).resolve().parent
OUT = HERE / "density_inputs_20261014"
RUNS = ((256, (4000, 6000, 8000, 10000)),
        (512, (4000, 6000, 8000, 10000)),
        (1024, (4000, 10000, 20000)),
        (2048, (20000,)))
DURATIONS = {
    "0p1myr": ("2.044024313763843d0", "1.0220121568819214d1"),
    "4p77myr": ("1.0220121568819214d1", "4.8749979883267656d2"),
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for resolution, densities in RUNS:
        for n0 in densities:
            for gravity in (True, False):
                branch = "gravity" if gravity else "nogravity"
                for duration, (save_step, stop_time) in DURATIONS.items():
                    if resolution == 1024 and n0 == 4000 and duration != "0p1myr":
                        continue
                    if resolution == 2048 and duration != "0p1myr":
                        continue
                    suffix = "" if resolution == 256 else f"_r{resolution}"
                    prefix = f"ion_{branch}_n{n0:05d}{suffix}_{duration}"
                    path = OUT / f"{prefix}.par"
                    content = f"""! Three-phase 40 Msun wind density sweep; base mesh and physics unchanged.
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
