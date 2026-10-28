# m40_n24762_pk56234133: complete 40-Msun history

WITHHELD VALIDATION HOLDOUT: never include this case in surrogate training or coefficient fitting. Publication does not release the holdout reservation.

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 24762 cm^-3 at 1 pc; external P/k_B = 56234133 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 54 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/keohane4_m40_n24762_pk56234133/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.19074792%, pressure drift = 0.015302943% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 0.9328916634276836,
      "r50_pc": 0.9390995837941306,
      "r90_pc": 0.9473609675051792,
      "width_10_90_pc": 0.014469304077495582,
      "cells_10_90": 1.8105524624145346,
      "contrast": 7759.321427624839,
      "upstream_density_g_cm3": 9.38150510170452e-24,
      "downstream_density_g_cm3": 7.279411355902762e-20,
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
    "peak_pc": 0.958171901889772,
    "r10_pc": 0.9329686351986314,
    "r50_pc": 0.9391749714863613,
    "r90_pc": 0.9476752568770478,
    "width_10_90_pc": 0.01470662167841641,
    "cells_10_90": 1.8399170132223048,
    "local_peak_fwhm_pc": 0.5285884391398386,
    "local_peak_fwhm_cells": 52.906757753753254,
    "peak_to_local_baseline": 107226.43129575382,
    "peak_to_initial": 1.1971688292441618,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.20447739389907338,
    "upstream_mach": 416.87335882087064,
    "downstream_mach": 0.6426516703592425,
    "pressure_jump": 200792.8645947648,
    "density_jump": 3.736976010012146,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
