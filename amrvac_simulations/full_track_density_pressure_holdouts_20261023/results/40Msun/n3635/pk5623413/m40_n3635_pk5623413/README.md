# m40_n3635_pk5623413: complete 40-Msun history

WITHHELD VALIDATION HOLDOUT: never include this case in surrogate training or coefficient fitting. Publication does not release the holdout reservation.

Exact Float64 DAT endpoint 4.77 Myr, 49 full saves from age zero at 0.1-Myr cadence plus endpoint. Wind: MS to 4.3 Myr (1e-6 Msun/yr, 2000 km/s), RSG to 4.5 Myr (5e-5 Msun/yr, 15 km/s), WR to 4.77 Myr (1e-5 Msun/yr, 2000 km/s); no SN. n_ref = 3635 cm^-3 at 1 pc; external P/k_B = 5623413 K cm^-3. Effective external confinement may represent surrounding cloud weight; fixed initial star+cloud gravity is already modeled and must not be double-counted. Neutral support/relaxation retained; no evolving self-gravity/photoionization/tabulated cooling/conduction.

Original static/smoke/full guards exited 0 with one finish and empty stderr; 54 original source/binary/runtime/input pins passed. The new selected pull matches every remote/local SHA256 and byte count with empty checksum dry-runs. `raw/` preserves all completed case files, including static/smoke saves, full DAT/VTU pairs, logs, original validation and COMPLETE marker. Other active outputs/queue logs were excluded. Shared dataset provenance: `provenance/keohane3_withheld_validation40_20261028T110114Z/`.

`native_profiles/` contains 49 CSVs of 1024 native conservative cells. The VTU representation has 1152 interpolated vertices. Float64 DAT controls age/cadence; Float32 VTU labels retain rounding. Units cm, g, s; 365-day year; AMRVAC Msun = 1.98892e33 g. Cumulative gas excludes the star and r < 0.001 pc. Positive density-excess mass is Eulerian, not tracer-defined swept mass; signed gas change is retained. Independent mass reintegration passed. `images/` has every density PNG; preferred full/inner phase/mass/flow and all-save sheet are in `reviewed_diagnostics/`. All 59 PNGs were integrity-checked; visual QA is described in shared scientific_review_qa.json. Mass axes: cm bottom/pc top, g left/Msun right.

Native/frozen-runtime positivity, analytic initial atmosphere, exact endpoint/cadence and phase-rate/speed gates passed. Endpoint outer 40--160 pc density drift = 0.57544449%, pressure drift = 0.069549365% (<2%); the full transient history is retained. local_jump_v1 is an operational search beyond 1.2 times the separately flow-selected termination candidate when present. Missing separate rise/outer peaks do not prove absence of swept gas; legacy peak-envelope diagnostics remain separately defined. Exact endpoint candidate records below are numerical diagnostics, not physical shock thickness, converged GRB-wall evidence or an approved fit surrogate.

```json
{
  "local_jump": {
    "snapshot": 48,
    "age_myr": 4.769999999999999,
    "phase": "WR",
    "method": "local_jump_v1",
    "fit_eligible": false,
    "candidate": {
      "r10_pc": 2.2297631040074015,
      "r50_pc": 2.250502710180478,
      "r90_pc": 2.273539235749662,
      "width_10_90_pc": 0.04377613174226047,
      "cells_10_90": 2.3379412730621993,
      "contrast": 1897.5588347989803,
      "upstream_density_g_cm3": 1.6955551676365582e-24,
      "downstream_density_g_cm3": 3.2174156882378172e-21,
      "maximum_log_jump_cell": 503,
      "window_cell_indices": [
        497,
        510
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
    "peak_pc": 3.4718734161556886,
    "r10_pc": 2.2348754260889727,
    "r50_pc": 2.2589972615709084,
    "r90_pc": 3.088176096594824,
    "width_10_90_pc": 0.8533006705058512,
    "cells_10_90": 38.95901870118564,
    "local_peak_fwhm_pc": 1.372252713108585,
    "local_peak_fwhm_cells": 57.240939592818734,
    "peak_to_local_baseline": 44135.3189805191,
    "peak_to_initial": 1.8721032012587266,
    "flags": []
  },
  "termination_flow_candidate": {
    "radius_pc": 0.5362020402975279,
    "upstream_mach": 446.0985399943967,
    "downstream_mach": 0.6318795489188703,
    "pressure_jump": 234990.1696732191,
    "density_jump": 3.732707608240927,
    "flags": []
  },
  "outer_shell_candidate": null
}
```

Prescribed injection rates/speeds pass TRACK gates. Shared scientific_review_qa.json retains first-cell evolved flux/speed estimates, which are not boundary Riemann flux measurements; single-mesh flux convergence remains unestablished. Keep all 12 holdouts withheld. No surrogate training/MCMC/silent extrapolation or universal-law fit.
