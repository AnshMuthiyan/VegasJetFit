# Lyra 40-Msun finite-GMC bubble handoff (20 October 2026)

This is a dated, additive handoff of Jonathan's local AMRVAC bubble work to
Ansh's `feature/amrvac-wind-bubble-models` branch. It does not modify Ansh's
`VanMarleStellarParameterRuns`, cooling/conduction experiments, or any
VegasAfterglow fit. The full canonical run tree remains on Lyra at
`/Users/jkeohane/GRBs/AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/`.
Its `README.md` is copied under `source/` and remains the detailed dated run
record. The compiled meeting edition, editable TeX, figures, and provenance
are under `meeting_book/` (the live shared copy is in
`Share_Folder/Reports/Meeting_Books/26_10_20__finite_gmc_40msun_bubble_resolution/`).

## What is here

- `source/`: full small-file mirror of the active 40-Msun case: Fortran user
  modules, Python generators/validators/plotters/tests, parameter files,
  generated exact input sets, manifests, and the case README. Runtime
  `results/`, `builds/`, and caches are excluded. Some inputs are historical
  or staged but never run; presence of a parameter file is not validation.
- `related_sources/`: small source and method files from the local two-star,
  40-Msun wind-density, and earlier pressure-grid work. They are context,
  not a claim of a combined physical model or completed campaign.
- `evidence/`: copied validation CSVs, shell-metric CSVs, age-fixed inner-rise
  metrics, the v28 log-radius inventory, latest corrected plots, and the
  two 20,480-cell guard exit/SHA records. Preserve the directory names:
  each measurement retains its original case and date. Older metrics are
  historical and must be checked against the case README before use.
- `selected_vtu/`: five precisely identified snapshots: the two 16,384-cell
  matching wind endpoints, the validated 20,480-cell GMC1000 wind endpoint,
  and both validated 20,480-cell no-wind static endpoints. See
  `selected_vtu_manifest.csv` for original paths, byte counts, and SHA-256.
  This is a small inspection set, not the complete time series.
- `meeting_book/`: the eight-page 15:11 EDT meeting edition and its editable
  sources. `main_asof_1126.pdf` is an older as-of copy, not the current book.
- `LITERATURE_CONTEXT.md`: a short reading note on the three connected
  Reichart dark-afterglow/cloud papers and their limits for local WR claims.

## Current scientific status

The controlled 20,480-cell pair has inner radius 0.0002 pc, first-cell width
0.0000125 pc, evolved outer radius 2.5 pc, and a 20-pc hydrostatic pressure
anchor. Both static atmospheres passed their independent 0.1-Myr/two-VTU
checks. The static has wind and ionization OFF: the reported H II-cell count
is a calculated potential-front mesh check, not an evolved H II region.

Pauley404-02's GMC1000 direct-WR wind passed guard exit 0, one normal AMRVAC
finish, empty stderr, seven VTUs, exact 0.0015-Myr age, finite-GMC initial
and outer checks, and the 2000-km/s and 1e-5-Msun/yr WR wind gates. Its
endpoint inner 10% shell-rise radius is 0.064086668 pc, shell FWHM 17.662
native cells, contrast 55.931, and local 10--90% rise 5.581 native cells
(0.000132181 pc). These pass the stated *numerical* gates. The matched
16,384-cell control has radius 0.063717328 pc and local rise 5.375 cells
(0.000148013 pc), so the physical rise still moves with the mesh.

Pauley404-03's GMC2000 20,480-cell **static only** passed its independent
gate. Its matching wind has **not** launched. Host-measured projected wind
runtime is 49,375.262 s, exceeding the 34,560-s safety ceiling (80% of
the staged 43,200-s guard). Jonathan's decision on the guard is pending;
do not change it or launch from this handoff. Preserve the original Mac03
Xcode-license failure log and environment on Lyra.

The v28 quality-gated 0.001--10-pc inventory contains 331 accepted
snapshots in 13 of 20 bins, with 56 resolved local ramps and none below
0.0251 pc. These cases are direct-WR injection into a prescribed finite
cloud atmosphere, **not** a fully evolved main-sequence/RSG/WR history.
The measured rise is a swept-shell diagnostic, not a demonstrated WR wind
termination shock, physical width, converged density profile, or GRB wall.
Do not mix ages, core densities, GMC densities, domains, or physics switches
when comparing profiles. The book and case README spell out the caveats.

## Integrity and use

`selected_vtu_manifest.csv` pins the inspection snapshots; run
`python verify_bundle.py` from this folder to check them and the PDF. The
exact input files for the current pair are in `source/dense_gmc_inputs_*20480*/`;
their transferred SHA records are in `evidence/guard_*20480/`. The shared
`meeting_book/main.pdf` SHA-256 is
`58b92dfb89e3cac0f38c0ecfc7c95ac2995abb35f74fcdaec2ec182effd86c4f`.
The canonical Lyra tree retains all VTUs, logs, failed-guard evidence, and
intermediate products; none were removed or overwritten for this handoff.

The source tests live at `source/test_*.py`; they exercise the diagnostics
and input-generation invariants, not AMRVAC physics or convergence. The
scripts still assume the original Lyra directory layout for some paths.
Inspect or adapt their paths before running them elsewhere. No new AMRVAC
run was started to build this Git package.
