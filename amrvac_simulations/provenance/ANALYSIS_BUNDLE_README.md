# All-Pressure Analysis Bundle (`analysis_allP_20260501`)

This folder contains the post-run quality checks, feature fits, and surrogate-model
experiments for the `xmin0p2` pressure-grid campaign.

## Structure

- `plots/`
  - `allP_profiles_with_feature_anchors.png`: all 12 selected profiles with first-shock and outer-rise anchors.
  - `allP_domain_and_resolution_diagnostics.png`: domain headroom, boundary plateau behavior, transition-cell resolution, and snapshot integrity.
  - `allP_feature_fits_pressure_p{4,5,6}.png`: per-pressure feature-vs-density fits (p4/p5/p6 slices).
  - `allP_global_feature_surface_pred_vs_measured.png`: 2D feature-surface sanity check (`p,n` polynomial model).
  - `allP_surrogate_training_overlay.png`: ad-hoc 2D surrogate reconstruction on training runs.
  - `allP_surrogate_leave_one_out_overlay.png`: leave-one-out reconstruction for each run.
  - `allP_pressure_slice_surrogate_loo_metrics.png`: pressure-slice leave-one-out metric summary.
- `tables/`
  - `allP_run_quality_table.csv`: run-by-run quality metrics and flags.
  - `allP_feature_slice_polyfits.csv`: per-pressure polynomial fit coefficients for each extracted feature.
  - `allP_global_feature_surface_coefficients.csv`: 2D polynomial coefficients for feature surfaces.
  - `allP_surrogate_loo_metrics.csv`: leave-one-out metrics for the 2D surrogate across all runs.
  - `allP_pressure_slice_surrogate_loo_metrics.csv`: leave-one-out metrics for per-pressure surrogates.
- `reports/`
  - `allP_quality_and_model_report.txt`: concise text summary of data integrity, flags, and modeling caveats.

## Data-quality policy used in this bundle

- If final snapshot `test0004.vtu` was corrupted (inner-domain NaNs), analysis used the latest fully valid snapshot (typically `test0003.vtu`).
- Domain flags are based on outer-rise headroom and boundary behavior.
- Resolution flags are based on estimated cells across the first shock and the outer-rise transition.

## Rebuild command

Run from this campaign directory:

```bash
/Users/jkeohane/GRBs/.venv/bin/python analyze_all_pressure_features_and_surrogate.py
```
