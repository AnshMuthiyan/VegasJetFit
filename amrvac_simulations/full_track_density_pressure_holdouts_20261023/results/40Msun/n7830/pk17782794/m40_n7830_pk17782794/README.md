# m40_n7830_pk17782794: complete 40-Msun history

WITHHELD VALIDATION HOLDOUT: never include this case in surrogate training or coefficient fitting. Publication does not release the holdout reservation.

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 7830 cm^-3 at 1 pc; external P/k_B = 17782794 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 54 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/Keohane1_withheld40_20261028T130944Z/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.2590867%, pressure drift = 0.55589956% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 1.5143742390090225,
      "r50_pc": 1.5283397774674485,
      "r90_pc": 1.5398942085912564,
      "width_10_90_pc": 0.025519969582233903,
      "cells_10_90": 1.9941909193188394,
      "contrast": 2694.0826476456077,
      "upstream_density_g_cm3": 4.50067113764328e-24,
      "downstream_density_g_cm3": 1.2125180014684177e-20,
      "maximum_log_jump_cell": 457,
      "window_cell_indices": [
        451,
        464
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
    "peak_pc": 1.5623405102517718,
    "r10_pc": 1.514393326815834,
    "r50_pc": 1.5284140824874035,
    "r90_pc": 1.5404639907513857,
    "width_10_90_pc": 0.026070663935551686,
    "cells_10_90": 2.036769806291886,
    "local_peak_fwhm_pc": 0.5355269215429079,
    "local_peak_fwhm_cells": 35.95727449541283,
    "peak_to_local_baseline": 54858.439116200585,
    "peak_to_initial": 1.6301761410173292,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.35675111255445136,
    "upstream_mach": 522.9841605906786,
    "downstream_mach": 0.8018999770963856,
    "pressure_jump": 314726.88253044424,
    "density_jump": 3.6929154539179807,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
