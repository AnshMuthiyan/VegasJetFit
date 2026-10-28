# m40_n10000_pk1000000000: complete 40-Msun history

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 10000 cm^-3 at 1 pc; external P/k_B = 1000000000 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 102 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/Keohane4_completed40_n10000_20261028T044757Z/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.14693731%, pressure drift = 0.16553266% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 0.3219922543762003,
      "r50_pc": 0.32501530559884806,
      "r90_pc": 0.32712758640407735,
      "width_10_90_pc": 0.0051353320278770265,
      "cells_10_90": 1.7418596635098424,
      "contrast": 1962.4622436167504,
      "upstream_density_g_cm3": 6.880898255442249e-23,
      "downstream_density_g_cm3": 1.350350302847378e-19,
      "maximum_log_jump_cell": 278,
      "window_cell_indices": [
        272,
        285
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
    "peak_pc": 0.3303721694683065,
    "r10_pc": 0.3219990696762765,
    "r50_pc": 0.3250466865513954,
    "r90_pc": 0.327186080906183,
    "width_10_90_pc": 0.005187011229906502,
    "cells_10_90": 1.7593017416111252,
    "local_peak_fwhm_pc": 0.20707765019269214,
    "local_peak_fwhm_cells": 55.41712155338968,
    "peak_to_local_baseline": 29511.059261517054,
    "peak_to_initial": 1.0179099538423608,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.07934097750586128,
    "upstream_mach": 240.66825627679304,
    "downstream_mach": 0.5482787495702195,
    "pressure_jump": 67600.56074134923,
    "density_jump": 3.687921906629269,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
