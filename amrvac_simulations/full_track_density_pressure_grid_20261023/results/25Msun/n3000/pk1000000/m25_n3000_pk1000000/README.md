# m25_n3000_pk1000000: complete 25-Msun history

Survey-grid history; publication does not approve a surrogate or physical-width claim.

Exact Float64 DAT endpoint 7 Myr, 71 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 6.5 Myr (2e-7 Msun/yr, 1500 km/s), RSG to 7 Myr (1e-5 Msun/yr, 15 km/s); no WR; no SN. n_ref = 3000 cm^-3 at 1 pc; external P/k_B = 1000000 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 102 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/Keohane1_original25_pair_20261030T134700Z/`.

`native_profiles/` contains 71 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 80 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.26211302%, pressure drift = 0.26211302% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 70,
    "age_myr": 6.999999999999998,
    "phase": "RSG",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": null,
    "quality_flags": [
      "NO_STRONG_LOCAL_DENSITY_JUMP"
    ]
  },
  "legacy_first_rise": {
    "peak_pc": 0.041071656221976824,
    "r10_pc": 0.03787384153872504,
    "r50_pc": 0.03840420931997162,
    "r90_pc": 0.03907038434596561,
    "width_10_90_pc": 0.0011965428072405679,
    "cells_10_90": 1.9755816075810344,
    "local_peak_fwhm_pc": 0.1859004280109365,
    "local_peak_fwhm_cells": 153.5257228946615,
    "peak_to_local_baseline": 109.00056844164223,
    "peak_to_initial": 1.4388750421876901,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.038302345639423106,
    "upstream_mach": 8.432456828159665,
    "downstream_mach": 0.3746157943532012,
    "pressure_jump": 102.47619211302221,
    "density_jump": 108.76987947035818,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
