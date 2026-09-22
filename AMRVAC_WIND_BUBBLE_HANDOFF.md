# AMRVAC simulation and surrogate handoff

Status: research handoff, 2026-09-22. This branch does **not** change any VegasAfterglow fit or launch a new AMRVAC run.

## Two branches, two jobs

- `feature/amrvac-wind-bubble-models` in `git@github.com:AnshMuthiyan/VegasJetFit.git` is Ansh's **offline AMRVAC simulation and profile-parameterization branch**. Start with `amrvac_simulations/README.md`. The name is historical; work committed here should concern simulations, quality control, or a compact surrogate, not MCMC.
- `jonathan-mac-version` is the **VegasJetFit/VegasAfterglow fitting branch**. The fitting code later consumes a validated, fast surrogate. New fit coordinates, priors, optional reverse-shock emission, likelihoods, and production runs belong there (or on a fit-feature branch based on it), not in the AMRVAC simulation workstream.
- Both branches share a Git repository for now, so each Git checkout contains the repository's baseline files. Branch *purpose and commits* are separate. Do not merge an exploratory surrogate into the fitting branch until the science and speed gates below pass.

The computational architecture is: **run expensive AMRVAC hydrodynamics offline -> extract density profiles -> parameterize/interpolate a small profile family -> evaluate that surrogate cheaply inside VegasAfterglow during many MCMC likelihood calls**. AMRVAC itself is never called during a fit. The reverse shock of GRB ejecta is a separate emission question; it is not the progenitor wind termination shock in an AMRVAC density profile.

## Canonical starting point

On Lyra, `AMRVAC_Bubble_Models/RUN_INDEX.md` points to `Boost_Test_runs_2026_04_25_rtwind_fulltimeline_xmin0p2_p6diag/` as the completed 12-run pressure-grid campaign. A copy of that index and the campaign method notes is in `amrvac_simulations/provenance/`. That campaign used MPI-AMRVAC v3.2, commit `c45d84650ed3379eb22dcfa6fb927a45734e5d8c`, with a retarded wind inner boundary and no empirical bubble imposed as an initial condition. The 12 cases are p4/p5/p6 slices of ambient pressure and density. The branch contains a **curated, immutable starting bundle**, not the whole simulation tree; see the manifest and provenance note in `amrvac_simulations/README.md`.

The May 1 all-pressure analysis selected the last sufficiently valid snapshot for each run. Seven p5/p6 final snapshots contained inner-domain NaNs and were rejected in favor of `test0003.vtu`; the associated quality table is copied with the bundle. Later p5/p6 reruns changed the current campaign directories. For fidelity to the May 1 analysis, the selected p5/p6 VTUs here come from the preserved pre-inner-fix archive, while p4 VTUs come from the current p4 directories. **Do not silently mix later snapshots with the May 1 tables.** The later runs should be audited as a new, versioned dataset before replacing this bundle.

## Modeling target for Ansh

The copied `amrvac_simulations/provenance/EMPIRICAL_BUBBLE_SURROGATE_PLAN.md` recommends registering **whole** density profiles by two physically meaningful radii: the first/termination-shock rise and the onset of the outer wall. Interpolating unregistered profiles pointwise smears moving shocks. The seven-feature `p4_n22` warp was rejected as a general generator because it distorted coupled structure; it remains a control, not the production choice. A p4 registered-profile prototype passed internal positivity, outer-ISM asymptote, shock-jump, and monotone cumulative-mass checks. The all-pressure prototype has training and leave-one-out metrics in `amrvac_simulations/tables/`, but it is not a validated fast fitting component.

Recommended sequence:

1. Reproduce the selected-profile read, units, pressure/density labels, and quality decisions from the committed bundle. Inspect the later reruns separately, especially the p5/p6 inner-domain failures, before expanding the training set.
2. Choose a low-dimensional parameterization of `rho(r)` over the simulated pressure/density range. Keep shocks/walls registered before interpolation and preserve a physically correct outer asymptote. State which quantities are free and which are fixed by the simulation grid.
3. Validate withheld simulations, not just training overlays: location and width of the shocks, radial density residuals, cumulative swept-up mass, continuity or intended jumps, and positive finite density. Flag extrapolation outside the simulated pressure/density box rather than silently extending it.
4. Export a compact, versioned table or formula plus units, parameter bounds, source-snapshot checksums, and a pure function `rho(r, parameters)` (or equivalent). Measure per-evaluation time and memory so the future VegasAfterglow fit can call it thousands of times.
5. Only after that science review, transfer the surrogate interface to the fitting branch and compare light curves with the existing simple/empirical-bubble and smoothly broken controls using identical data and fit settings. Do not treat a surrogate match to AMRVAC as proof of a good GRB fit.

The existing VegasJetFit `BubbleVegasModel` and `EmpiricalBubbleVegasModel` are fitting-side surrogates. They are useful baselines, but are not the AMRVAC simulation itself and are not automatically the final parameterization. Their fit parameters `rt`, `nt`, and `nism` need not be the independent parameters chosen from the all-pressure AMRVAC family.

## Scope and ownership

- Ansh: simulation provenance, selected-profile quality control, profile registration/interpolation, mass validation, fast surrogate export, and tests on this branch.
- Jonathan/Codex: fit-coordinate change from `n017` to a defined averaged density, priors, and optional reverse-shock tests for Dylan's 080319B and 080413B smoothly broken fits. These are tracked in `/Users/jkeohane/GRBs/CODEX_TODO_WHEN_TOKENS_RETURN.md`, not assigned to the AMRVAC branch.
- Joint review: agree on the numerical interface and units before the surrogate enters VegasAfterglow. Specify whether `n` is total particles, hydrogen nuclei, or another number density; the current bubble callback uses `rho=1.3*m_p*n`, while other medium paths use different conventions.

## Before any new long simulation

Read `amrvac_simulations/provenance/AMRVAC_BUBBLE_RUN_LESSONS.md` and the copied campaign README. Verify the AMRVAC version on each host, rebuild problem makefiles after version changes, and use short Lyra/Pauley smoke tests. The old analysis scripts in `amrvac_simulations/analysis/` are copied unchanged as provenance; they still use the old directory layout and some import JetFit. Make a standalone analysis entry point and tests rather than assuming those scripts can run as-is from this curated bundle.

No fit prior, production chain, or science claim is changed by publishing this branch. The next deliverable is a validated and benchmarked **simulation-derived density surrogate**, not another MCMC run.
