# m40_n5477_pk1000000000: complete 40-Msun history

Survey-grid history; publication does not approve a surrogate or physical-width claim.

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 5477 cm^-3 at 1 pc; external P/k_B = 1000000000 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 190 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/keohane1_midpoint40_20261028T110114Z/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.10075681%, pressure drift = 0.099646662% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 0.307621818718727,
      "r50_pc": 0.31056309062284165,
      "r90_pc": 0.31263937046495044,
      "width_10_90_pc": 0.005017551746223425,
      "cells_10_90": 1.7730073118953555,
      "contrast": 1425.789699839263,
      "upstream_density_g_cm3": 5.469155950652382e-23,
      "downstream_density_g_cm3": 7.797866221254779e-20,
      "maximum_log_jump_cell": 273,
      "window_cell_indices": [
        267,
        280
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
    "peak_pc": 0.3156934327592341,
    "r10_pc": 0.3076257581499041,
    "r50_pc": 0.31058898253543055,
    "r90_pc": 0.3126886548622796,
    "width_10_90_pc": 0.005062896712375475,
    "cells_10_90": 1.7889571505012896,
    "local_peak_fwhm_pc": 0.2011578652742252,
    "local_peak_fwhm_cells": 55.95070858893308,
    "peak_to_local_baseline": 17828.643664258358,
    "peak_to_initial": 1.009794975358937,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.08028520893415136,
    "upstream_mach": 186.10179578892192,
    "downstream_mach": 0.9730419922523762,
    "pressure_jump": 39140.36838075175,
    "density_jump": 3.586503656041831,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
