# AMRVAC pressure-grid source bundle

This directory is a compact, versioned starting point for **offline** wind-bubble simulation analysis. It is not a VegasAfterglow fitting model and does not contain all AMRVAC run outputs.

Source on Lyra: `/Users/jkeohane/GRBs/AMRVAC_Bubble_Models/Boost_Test_runs_2026_04_25_rtwind_fulltimeline_xmin0p2_p6diag/`. The source campaign reports MPI-AMRVAC v3.2 at commit `c45d84650ed3379eb22dcfa6fb927a45734e5d8c`. Its README, surrogate plan, p4 physics report, and May 1 analysis notes are copied into `provenance/`, so Ansh can inspect the rationale without a Lyra mount. This bundle is a snapshot of selected source inputs and data, not a claim that the prototype is scientifically final.

## Contents

- `template/`: copied AMRVAC problem source, parameter templates, run wrapper, and stellar-evolution input. Per-run changes in later campaigns are **not** represented by this one template.
- `analysis/`: historical prototype analysis scripts copied verbatim. Several scripts expect the full original campaign tree; `plot_tight_density_profiles.py` also imports JetFit. They are provenance/reference code, **not** a standalone runnable package. Decoupling is an explicit next task.
- `tables/`: May 1 quality, feature, training, and leave-one-out CSVs, plus planning tables. They describe the **May 1 analysis dataset**, not the later p5/p6 reruns.
- `selected_vtu/`: one VTU per quality-table row, named `<run_id>__<chosen_snapshot>`. Four p4 files came from the current `pressure_p4_*` directories. Eight p5/p6 files came from `_archive_pre_innerfix_20260503T174140Z/pressure_p5_*` and `pressure_p6_*`, because the current directories were changed by later reruns. The May 1 report rejected seven corrupt final p5/p6 snapshots and selected earlier valid ones.
- `selected_vtu_manifest.csv`: source path within the campaign, byte count, and SHA-256 for every committed selected snapshot. Generate/check it with `python verify_bundle.py`.
- `provenance/`: verbatim copies of the run index, AMRVAC lessons, campaign README, surrogate plan, p4 physics report, May 1 analysis README, and quality summary. Their original paths and dates still matter; these are historical records, not a new analysis.

This is small enough to review in Git. Large logs, executables, checkpoints, and full output trees remain only in the Lyra simulation workspace or its archive. Do not `git add` them.

## Scientific target

Derive a compact, fast parameterization of the AMRVAC radial **mass density** `rho(r)` across the simulated ambient pressure and density grid. Register the first-shock and outer-rise positions before interpolating full profiles, and check cumulative swept-up mass. Do not use a simple visual match or a seven-feature warp alone as acceptance. Report the valid parameter box and behavior at its edges; extrapolation needs an explicit policy.

When the surrogate passes withheld-run and physics checks, hand off a versioned formula/table and exact units to the separate VegasAfterglow fitting branch. That later branch will adapt it for repeated likelihood evaluation; AMRVAC itself is not in the likelihood loop.

## Integrity check

From this directory:

```bash
python verify_bundle.py
```

This checks the quality-table row set, selected filenames, sizes, and checksums. It does not establish physical correctness or validate a later rerun. A deliberate bundle update requires a new source analysis date and an explicit `--write-manifest` followed by review of every changed hash.
