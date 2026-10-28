# m40_n3000_pk1000000: complete 40-Msun history

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 3000 cm^-3 at 1 pc; external P/k_B = 1000000 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 102 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/keohane2_remaining40_20261028T065508Z/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 1.474684%, pressure drift = 1.4746426% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 2.7089187963979513,
      "r50_pc": 2.7293602115095874,
      "r90_pc": 2.755649502467737,
      "width_10_90_pc": 0.04673070606978591,
      "cells_10_90": 2.0614146675360416,
      "contrast": 2758.973378845815,
      "upstream_density_g_cm3": 1.1309287660904435e-24,
      "downstream_density_g_cm3": 3.1202023590144794e-21,
      "maximum_log_jump_cell": 526,
      "window_cell_indices": [
        520,
        533
      ],
      "flags": [
        "UNRESOLVED_LT5_NATIVE_CELLS",
        "LEGACY_10_90_WIDTH_SPANS_BROAD_ENVELOPE"
      ]
    },
    "quality_flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS",
      "LEGACY_10_90_WIDTH_SPANS_BROAD_ENVELOPE"
    ]
  },
  "legacy_first_rise": {
    "peak_pc": 3.443266186244586,
    "r10_pc": 2.7111734221412576,
    "r50_pc": 2.742823788810811,
    "r90_pc": 3.2431858847938897,
    "width_10_90_pc": 0.5320124626526321,
    "cells_10_90": 21.618541313551646,
    "local_peak_fwhm_pc": 1.0242160681434092,
    "local_peak_fwhm_cells": 38.31933246138158,
    "peak_to_local_baseline": 59661.31024496645,
    "peak_to_initial": 1.9241806087148445,
    "flags": []
  },
  "termination_flow_candidate": {
    "radius_pc": 0.6109275569623331,
    "upstream_mach": 435.07845890393827,
    "downstream_mach": 0.9232203139015654,
    "pressure_jump": 213957.5728303922,
    "density_jump": 3.6741049989412042,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
