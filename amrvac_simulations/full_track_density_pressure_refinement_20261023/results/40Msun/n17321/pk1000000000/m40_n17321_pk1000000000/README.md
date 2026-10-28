# m40_n17321_pk1000000000: complete 40-Msun history

Survey-grid history; publication does not approve a surrogate or physical-width claim.

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 17321 cm^-3 at 1 pc; external P/k_B = 1000000000 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 190 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/keohane2_m40_n17321_pk1000000000/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.1934706%, pressure drift = 0.4009578% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 0.33688838441547153,
      "r50_pc": 0.3399621529049734,
      "r90_pc": 0.3421954670176486,
      "width_10_90_pc": 0.005307082602177049,
      "cells_10_90": 1.7280685179911188,
      "contrast": 2240.648206286357,
      "upstream_density_g_cm3": 9.935668265074209e-23,
      "downstream_density_g_cm3": 2.2262337276394808e-19,
      "maximum_log_jump_cell": 283,
      "window_cell_indices": [
        277,
        290
      ],
      "flags": [
        "UNRESOLVED_LT5_NATIVE_CELLS"
      ]
    },
    "quality_flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "legacy_first_rise": {
    "peak_pc": 0.34566446231608894,
    "r10_pc": 0.3368979195211105,
    "r50_pc": 0.3400037767474627,
    "r90_pc": 0.34227228102156293,
    "width_10_90_pc": 0.005374361500452451,
    "cells_10_90": 1.7498627797406812,
    "local_peak_fwhm_pc": 0.19101257376374886,
    "local_peak_fwhm_cells": 50.21504366977621,
    "peak_to_local_baseline": 43940.317000075825,
    "peak_to_initial": 1.0322075952868308,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.07473409400869002,
    "upstream_mach": 287.0440903700991,
    "downstream_mach": 0.7503128956755513,
    "pressure_jump": 94077.52416204487,
    "density_jump": 3.615848692948851,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
