# m40_n16870_pk1778279: complete 40-Msun history

WITHHELD VALIDATION HOLDOUT: never include this case in surrogate training or coefficient fitting. Publication does not release the holdout reservation.

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 16870 cm^-3 at 1 pc; external P/k_B = 1778279 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 54 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/keohane3_m40_n16870_pk1778279/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.88133378%, pressure drift = 0.8819169% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 1.4703889166783402,
      "r50_pc": 1.481726648086975,
      "r90_pc": 1.49581415760508,
      "width_10_90_pc": 0.025425240926739923,
      "cells_10_90": 2.0444923179213674,
      "contrast": 7760.58297049574,
      "upstream_density_g_cm3": 5.020818335676208e-24,
      "downstream_density_g_cm3": 3.8964477273801543e-20,
      "maximum_log_jump_cell": 453,
      "window_cell_indices": [
        447,
        460
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
    "peak_pc": 1.5235613307730946,
    "r10_pc": 1.4704263261009893,
    "r50_pc": 1.4817785610346854,
    "r90_pc": 1.4960051918385195,
    "width_10_90_pc": 0.02557886573753021,
    "cells_10_90": 2.0567235674909625,
    "local_peak_fwhm_pc": 0.493539645822078,
    "local_peak_fwhm_cells": 34.38808146891631,
    "peak_to_local_baseline": 157765.3035276339,
    "peak_to_initial": 2.3379805995243528,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  },
  "termination_flow_candidate": {
    "radius_pc": 0.33794317391689044,
    "upstream_mach": 482.3769396016915,
    "downstream_mach": 0.8213505312742263,
    "pressure_jump": 260867.83298240308,
    "density_jump": 3.7425164546879643,
    "flags": []
  },
  "outer_shell_candidate": {
    "peak_pc": 1.5235613307730946,
    "r10_pc": 1.4704263261009893,
    "r50_pc": 1.4817785610346854,
    "r90_pc": 1.4960051918385195,
    "width_10_90_pc": 0.02557886573753021,
    "cells_10_90": 2.0567235674909625,
    "local_peak_fwhm_pc": 0.493539645822078,
    "local_peak_fwhm_cells": 34.38808146891631,
    "peak_to_local_baseline": 157765.3035276339,
    "peak_to_initial": 2.3379805995243528,
    "flags": [
      "UNRESOLVED_LT5_NATIVE_CELLS"
    ]
  }
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
