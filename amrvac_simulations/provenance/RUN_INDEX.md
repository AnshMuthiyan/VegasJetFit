# AMRVAC Run Index

Updated: 2026-05-01

This directory is organized so status checks should use the explicit pointers below, not a broad scan of every historical `Boost_Test_runs_*` directory.

## Current Pointers

- `CURRENT_ACTIVE_LATEST_xmin0p2` -> latest active campaign with `x_min = 0.2 R_t`.
- `NEXT_CANDIDATE_xmin0p5_cpd100` -> prepared candidate campaign with `x_min = 0.5 R_t` and 100 cells/decade.
- `REFERENCE_COMPLETED_xmin0p8` -> completed `x_min = 0.8 R_t` reference campaign that produced mostly flat/ISM-like profiles.
- `LEGACY_SUMMER_2025_RUNS` -> archived summer 2025 runs on `/Volumes/Science_Data`.
- `LEGACY_SIMPLE_WIND_TEST` -> archived legacy CAK/simple-wind tests on `/Volumes/Science_Data`.

## Policy

- Keep active or soon-to-run campaigns on the local disk.
- Move completed, superseded, or legacy campaigns to `/Volumes/Science_Data/GRBs/amrvac_runs_archive`.
- Preserve cleanup manifests in `_cleanup_manifests`.
- Do not infer the latest campaign from alphabetical order or modified time alone. Use `CURRENT_ACTIVE_LATEST_xmin0p2` unless a newer `CURRENT_ACTIVE_*` symlink is intentionally created.

## Current AMRVAC Status

Primary completed campaign:

`Boost_Test_runs_2026_04_25_rtwind_fulltimeline_xmin0p2_p6diag`

Completion status:

- All 12 pressure-grid runs (`p4_n21..n24`, `p5_n20..n23`, `p6_n19..n22`) are present on Lyra.
- AMRVAC run trees on `pauley404-01/02/03` were purged on **2026-05-01** after copy verification.
- Verification + purge manifest:
  - `_cleanup_manifests/pauley_copy_verify_and_purge_20260501T193649Z.txt`

Analysis bundle for this campaign:

- `Boost_Test_runs_2026_04_25_rtwind_fulltimeline_xmin0p2_p6diag/analysis_allP_20260501/`

## Cleanup Notes

- Old preliminary campaigns and summer 2025 legacy data were moved under `/Volumes/Science_Data/GRBs/amrvac_runs_archive/_archive_legacy_prelim_20260425`.
- Pauley host AMRVAC work directories were removed after verification; current AMRVAC canonical data live on Lyra and in `/Volumes/Science_Data` archives.
- The old `simple_wind_test` tree was trimmed before archival:
  - Huge CAK logs were replaced with `head200` and `tail2000` text snapshots.
  - Duplicate `CAK_08_20.tar` was removed because the extracted directory remains.
  - Intermediate `CAK_08_05` VTUs were thinned to preserve first/final snapshots per output directory.

Use `status_latest_campaign.zsh` from this directory for quick status checks.
