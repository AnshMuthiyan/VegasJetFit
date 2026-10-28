# m40_n17321_pk100000000: complete 40-Msun history

Survey-grid history; publication does not approve a surrogate or physical-width claim.

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 17321 cm^-3 at 1 pc; external P/k_B = 100000000 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 190 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/keohane4_m40_n17321_pk100000000/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.2302643%, pressure drift = 0.0090146677% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 0.9280628299032534,
      "r50_pc": 0.936409961465198,
      "r90_pc": 0.9416661222413995,
      "width_10_90_pc": 0.013603292338146056,
      "cells_10_90": 1.7123686712097879,
      "contrast": 2973.4164620784277,
      "upstream_density_g_cm3": 1.5374950532098418e-23,
      "downstream_density_g_cm3": 4.571613101578292e-20,
      "maximum_log_jump_cell": 399,
      "window_cell_indices": [
        393,
        406
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
    "peak_pc": 0.9500673146719422,
    "r10_pc": 0.9280822032090562,
    "r50_pc": 0.9364737428526924,
    "r90_pc": 0.9417843036168894,
    "width_10_90_pc": 0.013702100407833151,
    "cells_10_90": 1.7247416502476653,
    "local_peak_fwhm_pc": 0.5633152964656976,
    "local_peak_fwhm_cells": 55.82013130256462,
    "peak_to_local_baseline": 65666.14116901136,
    "peak_to_initial": 1.0568199168461667,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.20057898338063773,
    "upstream_mach": 441.0486053393152,
    "downstream_mach": 0.8962449217915714,
    "pressure_jump": 224200.9373156923,
    "density_jump": 3.671514206828125,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
