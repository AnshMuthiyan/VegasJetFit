# VegasJetFit/scripts Handoff

This directory contains active post-fit product scripts.

## Last Touched (2026-08-11): 090424 Early-X-Ray SSC+KN Completion

- The PCRC-2 SSC+KN seeded refit completed all 5000 burn-in and 5000
  production iterations with 100 walkers and 10 temperatures. Total recorded
  MCMC wall time was 650471.83 s (180.7 h). Lyra pulled it, completed standard
  post-processing and the numerical-resolution ladder, validated it, and
  published it as `090424_with_early_xray_ssc_kn` in the dedicated August 3
  Share_Folder campaign.
- `write_campaign_latex_summary.py` now recognizes controlled branch directory
  names such as `090424_with_early_xray_ssc_kn`, while extracting canonical
  `090424` for science-product commands, manifest lookup, and tracking-note
  fallback. One-event alternate branches skip canonical-only cross-event
  comparison generators.
- Validation: Python compile, canonical/branch discovery assertions, report dry
  run, Tectonic compilation, and rendered PNG inspection of the first three
  pages passed. The 27-page `campaign_meeting_summary.pdf` and
  `campaign_products.validated` marker were written; the completed watcher then
  exited normally.

## Last Touched (2026-08-03): 090424 Early-X-Ray SSC+KN Seeded Refit

- Launched a controlled posterior refit on PCRC-2 with run tag
  `core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_with_early_xray_ssc_kn_v1`.
  It uses 15 workers, 10 temperatures, 100 walkers, 5000 burn-in, and 5000
  production iterations. The guarded 1+1 preflight accepted all 100 walkers
  in every temperature and completed; the full run then started automatically.
- The dedicated config is
  `structured_jet_core_logangle_powerlaw_090424_early_xray_ssc_kn_final_seeded_10temp_configs/090424.toml`.
  A structural comparison confirmed that it differs from the active
  synchrotron-only early-X-ray seeded config only by fixed `ssc=1` and `kn=1`.
  Its 22 fitted coordinates exactly match the same `(10,100,22)` correlated
  cloud, `initial_positions/090424_early_xray_unseeded_final_seeded_10temp.npz`.
- Campaign records are in
  `reports/090424_with_early_xray_ssc_kn_final_seeded_10temp_5000x5000_campaign/`.
  Publish separately as `090424_with_early_xray_ssc_kn` under the dedicated
  August 3 final-seeded Share_Folder campaign; never overwrite either canonical
  `090424` or synchrotron-only `090424_with_early_xray`.
- Lyra tmux session `postprocess_090424_early_xray_ssc_kn_final_seeded` watches
  the run, then performs the normal minimization, products, resolution ladder,
  validation, and publication. The PCRC-2 model/config/cloud/observation files
  were checksum-synchronized and a remote SSC+KN model-construction smoke test
  passed before dispatch.
- The existing early-X-ray follow-up supervisor's `launched()` predicate was
  also made compatible with macOS awk by replacing an empty regex alternative
  with explicit nonempty/status comparisons. Its live baseline MCMC was not
  disturbed.

## Last Touched (2026-08-03): Native Power-Law Lateral-Spreading Test

- `jetfit/models/powerlawVegas.py` now accepts `lateral_spreading` and passes
  it to the native Vegas jet constructor for top-hat, Gaussian, and power-law
  jets. The default remains `False`; an invariant test found the default and
  explicit-false flux arrays bit-for-bit identical.
- `scripts/compare_lateral_spreading_campaign.py` reruns each minimized model
  at fixed fitted parameters with spreading off and on, using the original
  event data, calibration/extinction treatment, and production resolution.
  This isolates the dynamics response; it does not estimate posterior or
  fitted-parameter changes, which require a spreading-enabled refit.
- Per-event products are written only beneath
  `<CAMPAIGN>/<GRB>/lateral_spreading_comparison/`. Each directory contains
  overlay and diagnostic plots in PNG/PDF, modeled-flux CSV files, a summary
  CSV, and metadata JSON. Across-event rankings and exploratory Spearman
  correlations are under `<CAMPAIGN>/lateral_spreading_comparison/`.
- The complete 15-GRB 2026-07-16 moderate-resolution campaign was processed.
  Sensitivity is much more strongly associated with late-time
  `Gamma * theta_c` than with `theta_v / theta_c`; treat this as an
  experimental-model sensitivity result, especially where the spreading
  prescription produces very large angular expansion.
- The campaign geometry comparison panels are late core-axis `Gamma`,
  `theta_c`, late `Gamma * theta_c`, and late `Gamma * theta_v`. The obsolete
  plotted diagnostics `theta_v/theta_c` and
  `Gamma * max(theta_v - theta_c, 0)` remain only as provenance columns in
  older per-event summaries.
- Exact vendored spreading implementation: `external/VegasAfterglow/src/core/grid-refinement.h`
  defines `theta_s` as the location of the steepest negative gradient in the
  initial angular `Gamma0` profile. For the campaign's fixed power-law
  `k_g=2`, this is approximately `theta_c/sqrt(3)`. Then
  `external/VegasAfterglow/src/dynamics/shock-physics.h` uses
  `f=1/(1+7*u*theta_s)` in `dtheta/dt`, so sensitivity to
  `Gamma*theta_c` is substantially built into the experimental prescription.
  `theta_v` is absent from this dynamics equation and enters through observer
  geometry. The vendored `docs/source/physics.rst` currently gives a different
  expression for `F(u)`; treat the compiled C++ source as authoritative for
  these products until that documentation mismatch is resolved.
- Fixed-solution likelihood timings across all 15 events found essentially no
  spreading overhead: summed spreading/no-spreading runtime ratio `0.987`,
  median event ratio `0.990`, and event-ratio 16th--84th percentile
  `0.978--1.015`. A same-length MCMC should therefore have similar raw wall
  time; retain a roughly 10% contingency for changed posterior behavior.
- Current Dylan-spectrum fits already enable native fast-to-slow cooling
  smoothing by subclass default and native synchrotron includes self-absorption.
  Unused optional physics includes SSC/KN, CMB cooling, free `xi_e`, reverse
  shock plus ejecta duration/magnetization, magnetar or arbitrary injection,
  additional jet families, and smooth broken-power-law media. Add these only
  through documented, one-feature-at-a-time comparison campaigns.
- Validation: both modified Python files passed `py_compile`; all 15 event
  directories contain all eight required nonempty files; campaign summary
  has 15 unique rows; default/no-spreading invariance and native spreading
  evolution smoke tests passed; representative event and aggregate figures
  were inspected visually.

## Last Touched (2026-08-03): 140506A Cooling-Break Diagnostic Audit

- The standard `frequencies.pdf/png` path calls
  `powerlawVegasDylanSpectrumModel.critical_frequencies()` with
  `break_frequency_mode=eats_weighted`. For each native Vegas detail-grid
  cell it converts the local comoving break to observer frame as
  `nu_c * Doppler / (1 + z)`, linearly interpolates in observer time, and
  plots the arithmetic emissivity proxy average
  `sum(I_nu_max * Doppler^3 * nu_c_obs) / sum(I_nu_max * Doppler^3)` over
  finite cells that bracket the requested time. It is not a break recovered
  from the integrated synthetic spectrum.
- In the 140506A 25+100 hybrid pilot, 92/100 terminal cold walkers have a
  greater-than-10-dex `nu_c` temporal range and many have abrupt drops at
  different observer times. The minimized EATS-weighted curve is smoother
  (maximum adjacent 200-point change about 0.71 dex), whereas the legacy
  single-cell local trace is substantially worse at early time. The pilot's
  short chain and boundary-reaching solutions make its translucent ensemble
  unsuitable for a paper inference.
- The diagnostic is resolution-sensitive because individual cells enter or
  leave the finite time-bracketing set discontinuously. The current numerical
  ladder validates modeled flux, not `nu_c` convergence; do not claim this
  cooling-break product is resolution-converged. Before paper use, add a
  fixed-parameter cooling-break ladder and compare the current arithmetic
  EATS proxy with a clearly labeled robust/log-weighted or spectrum-derived
  diagnostic. Do not silently replace the existing plot definition.

## Last Touched (2026-08-03): Paper Methods/Provenance Note

- `reports/PAPER_METHODS_NOTES_SEEDING_FILTERING_AND_RESOLUTION_20260803.md`
  records the paper-facing distinction between unseeded exploration, narrow
  best-fit Gaussian seeds, posterior-cloud warm starts, physically filtered
  branches, burn-in, and numerical-resolution continuation. It documents the
  all-UV and early-X-ray 090424 branches and explicitly states that source
  cloud samples are initialization only, not reused posterior samples.

## Last Touched (2026-08-02): Distributed Post-Fit Compute with Lyra-Only Publication

- Synced the active `VegasJetFit/scripts/` tree from Lyra and syntax/compile
  checked it on PCRC-1/2 and Pauley-01/02/03. Carina was offline and remains
  the only host pending this sync.
- `run_postfit_compute_only.sh EVENT RESULTS_DIR` performs minimization,
  standard products, the numerical-resolution ladder, and local validation on
  a worker host. It writes `.postfit_compute.running/owner` while active and
  only writes `postfit_compute.done` after validation. It never writes to a
  shared campaign directory.
- The common Lyra watcher recognizes those markers: it waits while remote
  compute is active, reuses a validated `postfit_compute.done` result after
  rsync, then remains the sole validator/publisher/meeting-book writer. This
  safely farms expensive diagnostics without competing Google Drive clients.
- First live use: the completed 090424 all-UV-plus-early-X-ray control is
  running compute-only post-fit in PCRC-1 tmux
  `postfit_090424_early_xray_pcrc1`; its Lyra watcher is polling the marker.
  The existing 140506A hybrid post-fit on Lyra was deliberately not disturbed.
- Follow-up validation found and fixed a non-deleting-rsync edge case: a
  removed remote `.postfit_compute.running` directory remained locally after
  `rsync -a`. The Lyra watcher now gives a validated
  `postfit_compute.done` priority over that stale running marker. The 090424
  compute-only job finished at `2026-08-03T00:47:42Z`; Lyra reused it and
  published `090424_with_early_xray` at `2026-08-03T10:18:48Z` without
  recomputing products. The existing automatic seeded follow-up supervisor
  can now advance from that local validation marker.
- The early-X-ray follow-up supervisor had an old free-text decision-record
  host constraint, which the current guarded dispatcher correctly rejected.
  It is now `pcrc_only`; PCRC-1 remains selected by the stage's machine list.
  The validated unseeded cloud was built as
  `initial_positions/090424_early_xray_unseeded_final_seeded_10temp.npz`
  with shape `(10,100,22)` by resampling the full 500,000-sample terminal
  cold-chain population, not by perturbing one best fit. The 10-temperature
  seeded MCMC was dispatched to PCRC-1 at 15 workers on 2026-08-03 after its
  guarded preflight. The supervisor is restored to advance the subsequent
  final-final stage, which will preserve the seeded cloud coordinates and
  initialize only newly thawed `s` around 4.0 (sigma 0.4; bounds 0.1--10).

## Last Touched (2026-08-01): 140506A Ultra-Fine MCMC Forensic Stop

- Stopped the PCRC-2 `140506A` ultra-fine v2 pool after forensic capture and
  checkpoint backup. It was not a slow run: it remained at burn `0/500`, the
  parent was blocked waiting for a lost pool worker, and surviving workers
  waited on task semaphores. A sampled worker peaked at 20.1 GiB; the retained
  pool caused compression before doing useful work. Its `1+1` preflight alone
  took 11,561.96 s (3.21 h), so a 3500-step full MCMC is not feasible at the
  coupled ultra-fine `(0.40, 1.333..., 40)` controls on present hosts.
- Diagnostics, preserved checkpoint, and a detailed record are in
  `reports/core_logangle_powerlaw_140506A_finalfinal_sthawed_ultrafine_5temp_500x3000_campaign/`.
  Its manifest host is now `blocked_memory_runtime`, preventing any automatic
  retry. Keep the validated moderate MCMC and fixed-solution ultra-fine ladder
  as current results. A future full refinement requires a separately approved
  lower-cost strategy and new memory/runtime preflight.
- Jonathan approved a targeted hybrid test at `(phi, theta, time) = (0.20,
  1.00, 30)`: retain moderate azimuth sampling while refining the polar/time
  controls implicated by the ladder. `start_140506A_hybrid_resolution_preflight_pcrc2.sh`
  launched its **preflight only** on PCRC-2 in tmux
  `grb_140506A_hybrid_preflight`, with four workers. It uses the same 5x100
  posterior cloud and all physical/data settings. Do not start its full MCMC
  until the preflight's resource/runtime measurement is reviewed.
- The hybrid preflight completed cleanly in 2,121.45 s (35.4 min): all five
  temperatures had 100 valid walkers and PCRC-2 returned to 35 GiB free with
  370 MiB compressed. The grid is memory-safe at four workers, but a direct
  500+3000-chain extrapolation is an order-of-weeks commitment; it remains
  intentionally not dispatched.
- Jonathan then approved a short, clearly non-final hybrid pilot: 5 workers,
  25 burn-in, and 100 production iterations. It started on PCRC-2 in tmux
  `grb_140506A_hybrid_pilot` with a normal 1+1 preflight first; Lyra watcher
  `postprocess_140506A_hybrid_pilot_lyra` will pull, run the ladder, and
  publish only to its dedicated `26_08_01...25x100_pilot` folder. Estimate
  about 20 hours; do not treat its short chain as final error-bar evidence.

## Last Touched (2026-08-01): 090424 Early-X-ray Checkpoint Migration

- `watch_090424_early_xray_burnin_migration_to_pcrc1.sh` is active in Lyra
  tmux session `watch_090424_early_xray_burnin_migration_to_pcrc1`. It watches
  only the controlled early-X-ray 090424 chain on Pauley-01. When the durable
  state changes from burn to production with burn `5000/5000`, it confirms
  PCRC-1 is idle, stops the source session, copies and validates that exact
  checkpoint, updates the manifest, and resumes the remaining production on
  PCRC-1 at 15 workers. Any copy or launch failure restores the Pauley-01
  chain from its checkpoint at 8 workers.
- The sampler's production-state archive intentionally omits the burn counter
  keys. The migration guard treats `phase=production` as proof that the full
  burn completed and verifies the production checkpoint instead. On 2026-08-02
  the early-X-ray chain was copied at production `300/5000`, then restarted on
  PCRC-1 in `grb_090424_early_xray_test_090424_migrated` with 15 active
  workers. Its manifest now names PCRC-1/15.
- The subsequent automatic early-X-ray follow-ups are PCRC-1-only at 15
  workers: both the 10-temperature final-seeded run and the five-temperature
  final-final thawed-s run wait for that host. The durable queue and decision
  record under `reports/090424_with_early_xray_followup_seeded_pipeline/`
  record this placement; the Lyra supervisor was restarted to load it.

## Last Touched (2026-07-31): 090424 All-UV v2 Completion and Early-X-ray Control

- The provenance-correct 090424 final-final all-UV v2 MCMC on PCRC-1 completed
  all 5,000 production iterations cleanly in 23,333.54 s (6.48 h). Its pulled
  local result is `jetfit/results/090424_core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_alluv_v2`.
  `start_postprocess_090424_finalfinal_alluv_v2_lyra.sh` is the dedicated
  watcher that will minimize, regenerate products, run the numerical ladder,
  validate, and publish it as the canonical July-16 `090424` replacement.
  The older all-UV-v1 shared product was moved to the campaign-local trash
  under a provenance-preserving name before v2 publishing.
- The watcher is correctly waiting behind active Lyra postprocessing of
  `080413B`; it must not compete with that work. It uses the normal Lyra
  postfit lock and will start automatically when that job releases the lock.
- The separate early-X-ray unseeded control remains in its initial/burn-in
  likelihood evaluation on Pauley-01. Its eight workers are CPU-active at
  roughly 94--100%; it has written a durable resume state but no completed
  burn-iteration checkpoint yet. Its watcher and the automatic two-stage
  seeded-followup supervisor remain active.
- Hardened `lyra_busy_processes()` to require both a real Python executable
  and a known compute entry point. A shell command that merely mentions a
  product-script path can no longer create a false busy barrier.

## Last Touched (2026-07-31): Stale-Blocker-Proof Lyra Postprocessing Guard

- `postprocess_core_logangle_powerlaw_15grb_10temp.sh::lyra_busy()` no longer
  uses broad `pgrep` text. The old expression matched the dispatcher argument
  `--busy-pattern jetfit.run` and made every completed job appear permanently
  busy. It now scans only live, exact compute commands and logs the matching
  command whenever it deliberately waits.
- A shared atomic directory lock at
  `logs/postprocess_activity/lyra_postfit.lock` serializes independent
  campaign watchers before minimization/product generation. The lock records
  owner PID/event and removes itself when the PID is gone or no longer belongs
  to this watcher; an ownerless lock is reclaimed after five minutes. Thus a
  killed tmux watcher, reboot, or PID reuse cannot leave a permanent blocker.
  Shell syntax passed and the live guard selected only the actual
  090424/080413B minimizers.
- Both chains were pulled and began minimization after correcting the stale
  guard. Their already-running watcher shells predate the lock; the next
  watcher restart loads the lock implementation. Do not restart them while
  their active minimizers are still running.

## Last Touched (2026-07-29): Serialize Lyra MCMC and Postprocessing

- `postprocess_core_logangle_powerlaw_15grb_10temp.sh::lyra_busy()` now treats
  a local `jetfit.run` as busy work, in addition to minimization and product
  generators. This prevents a rebooted or newly started watcher from launching
  a heavy post-fit suite concurrently with a Lyra-resident MCMC.
- Smoke validation after the Lyra reboot: `bash -n` passed for the watcher and
  final-final launcher. The 080413B MCMC was migrated to PCRC-1 instead, so
  Lyra can resume its designated postprocessing role.

## Last Touched (2026-07-29): 090424 Post-Burn-In PCRC-1 Migration Watcher

- `watch_090424_burnin_migration_to_pcrc1.sh` was briefly armed in Lyra tmux
  session `watch_090424_burnin_migration_to_pcrc1`. It is specific to the corrected
  all-UV intermediate 10-temperature run on Pauley-01. It waits for a stable
  `phase=production` checkpoint, requires PCRC-1 to have no `jetfit.run`,
  rsyncs and validates the checkpoint, stops Pauley only after verification,
  updates the manifest, then resumes on PCRC-1 with 15 workers. If destination
  launch fails it restores the manifest and resumes Pauley from the checkpoint.
- The all-UV override, source cloud, config, MCMC settings, wrapper, and
  manifest were staged on PCRC-1 and verified before arming. The watcher was
  stopped on 2026-07-30 because Pauley-01 is currently faster for this run;
  do not restart it or manually migrate 090424 unless the performance
  situation changes.

## Last Touched (2026-07-29): GRB 090424 All-UV Launch Invariant

- `run_core_logangle_finalfinal_sthawed_5temp_event.sh` defaults `090424` to
  `obs_overrides/090424_early_uvoir_included_no_early_xray.csv` and passes an
  explicit `REQUIRE_090424_ALL_UV=1` into the common runner.
- `jwk_run_thesis_reproduction_event.sh` checks that all 79 UVOT/UVOIR rows
  are included before any 090424 MCMC starts. Historical exclusions can only
  be reproduced with an explicit `REQUIRE_090424_ALL_UV=0`; do not use that
  setting for current science.
- Smoke validation: the approved override reported 79 included, 0 excluded UV
  rows and 144 excluded early X-ray rows. The corrected PCRC-1 preflight
  passed, the full 15-worker final-final run entered production, and the
  standard July-16 Lyra watcher will postprocess, run the ladder, publish, and
  refresh the meeting book.

- Subsequent provenance audit: the June-29 campaign's ordinary `090424`
  unseeded result used the legacy partial-UV file, but its 2026-07-07
  replacement entry (`090424_core_logangle_powerlawcsm_kminus10to3_early_uvoir_noearlyxray_10temp_5000x5000_v1`)
  is the validated all-UV unseeded source: 10 temperatures, 5000 burn/5000
  production, and an `obs.csv` SHA-256 matching the approved override. The
  completed all-UV final-final result used correct data but initialized from a
  legacy partial-UV final-seeded cloud. A finite replacement initializer from
  the validated all-UV unseeded cold chain is staged at
  `initial_positions/090424_alluv_unseeded_finalfinal_sthawed_5temp.npz`
  (shape `(5,100,23)`, source samples 500000, seed 90424). It is prepared,
  not dispatched; see `reports/090424_data_provenance_audit_20260729.md`.

- The ordinary 10-temperature wrapper
  `run_core_logangle_powerlaw_15grb_event.sh` now also forwards
  `INITIAL_POSITIONS` and applies the same 090424 all-UV/no-early-X-ray
  invariant. This supports the queued intermediate replacement
  `core_logangle_powerlawcsm_kminus10to3_final_seeded_alluv_10temp_5000x5000_v2`.
  Its `(10,100,22)` cloud is
  `initial_positions/090424_alluv_unseeded_final_seeded_10temp.npz`, sourced
  only from the validated all-UV unseeded cold chain. Dedicated Lyra dispatch
  and postprocess starters publish into the existing July-7 seeded campaign
  folder. On 2026-07-29 it was dispatched to idle Pauley-01 with 8 workers,
  after both PCRCs were busy; its 1+1 guarded preflight verified the all-UV
  override and source cloud before production is allowed to start.

## Last Touched (2026-07-28): Profile-Averaged Density Correlations

- `plot_campaign_csm_physical_scatters.py` treats
  `mean_number_density_cm3` as the volume average through the data-range
  density profile. Do not call it a literal shell density in plots, captions,
  or paper text. The underlying integrated CSM mass remains the spherical
  mass across that same radial interval.
- Standard campaign products now include `theta_c_vs_profile_mean_density`
  and `theta_c_vs_profile_radius` (PDF/PNG) plus corresponding posterior
  summary columns. The first shades `10^-6`--`10^10 cm^-3` only as a proposed
  future prior range; the second uses the per-walker geometric-mean radius and
  pale posterior-median inner/outer profile limits.
- `write_campaign_latex_summary.py` requires, captions, and gives full-page
  layout to all physical CSM correlation figures. Validated by regenerating
  the July-16 15-GRB book and rendering its new pages 333--334.

## Last Touched (2026-07-28): Safe Resume after Power Interruption

- `run_core_logangle_finalfinal_sthawed_5temp_event.sh` validates a preexisting
  `pt_resume_state.npz` (required arrays and dimensions) before invoking the
  common runner. A valid checkpoint automatically enables `RESUME=1` and
  `CLEAN_INCOMPLETE=0`; use `FORCE_FRESH=1` only to deliberately discard an
  interrupted run. This is required because the lower fresh-launch script
  otherwise removes incomplete results by default.
- Recovery validation on 2026-07-28: `080413B` resumed from production
  700/3000 on Lyra and `140506A` from burn 200/500 on PCRC-2. A generator-
  backed PCRC parent with no worker pool was stopped before restart; always
  inspect process children and CPU use before deciding a generator-hosted job
  survived an outage.

## Last Touched (2026-07-25): CSM Physical Campaign Comparisons

- `plot_campaign_csm_physical_scatters.py` is the standard generator for
  campaign-level physical CSM scatter products.  It matches the terminal
  cold-chain walkers to `density_shell_mass_walkers.csv`, derives total
  two-sided `M_j` with `derive_jet_energy_posterior`, and writes PDF/PNG/CSV
  products under `comparison_plots/`.  Error bars are posterior 16th--84th
  percentiles, not errors propagated from unrelated marginal summaries.
- `write_campaign_latex_summary.py::refresh_campaign_comparisons` requires
  these products and invokes the generator before a meeting book is compiled.
  Its comparison section reserves a full page for each of the three dense
  physical CSM figures; keep this rule when adding further 15-GRB diagnostics.
- Validated with the completed July-16 moderate campaign: 15 events loaded,
  Python compilation passed, and PDF pages 330--332 were rendered and visually
  inspected after rebuilding `campaign_meeting_summary.pdf`.

## Last Touched (2026-07-23): Combined Spectral-Evolution Diagnostic

- Standard postprocessing now writes `spectral_evolution_two_panel.pdf/png`.
  It vertically combines the all-terminal-walker `spectrum_timeseries` plot
  above `frequencies`, while preserving both source products as standalone
  diagnostics. The last of the two independent product
  steps to finish creates the pair, so it also works with parallel post-fit
  generation.
- The compact combined version deliberately omits panel letters and crops the
  standalone frequency title/legend/secondary-time header. Its caption defines
  the green/blue/orange frequency colors. Meeting books retain the combined
  figure *and* the two original standalone diagnostics for detailed review.
  Smoke-tested on July-16 moderate `090424`; visual inspection and Python
  compilation passed.

## Last Touched (2026-07-23): All-Walker Spectral-Evolution Product

- `plot/visualize.py::plot_spectrum_timeseries` now overlays every finite
  terminal cold-chain walker at each of its ten displayed epochs. Thin,
  translucent curves share the epoch color and are drawn beneath the thick
  minimized reference curve; `frequencies.pdf` remains the separate
  spectral-break-evolution diagnostic.
- `generate_postfit_products.py` obtains the full final cold-chain ensemble
  directly from `chain.npz`, records provenance in
  `spectrum_timeseries_sampling.json`, and writes walker identity plus curve
  type to `spectrum_timeseries_curves.csv` and `_data.npz`. The standard plot
  uses 250 logarithmic frequency samples per curve so all 100 walkers remain
  practical during normal post-processing.
- Smoke-tested on the completed July-16 moderate `090424` run: 100/100 finite
  terminal walkers, 252,500 serialized curve samples, PDF and PNG produced
  successfully. `generate_spectrum_timeseries.py` follows the same all-walker
  default; use `--best-only` only for a deliberately lightweight preview.

## Last Touched (2026-07-23): Campaign-Local Tracking-Sheet Snapshots

- `stage_campaign_tracking_notes.py` filters the durable live-sheet snapshot
  `reports/tracking_sheet_snapshots/GRB_Tracking_Sheet1_2026-07-23.json` into
  each campaign's `tracking_sheet_notes.json`. It retains the key current and
  historical note columns (M/N/O/Q/S/T/V/W/X) for the events actually in that
  campaign.
- `write_campaign_latex_summary.py` now renders these snapshots in each GRB
  subsection's decision/tracking note page, including older July campaigns
  that lack a per-event `decision_record.json`. Rebuilds therefore retain the
  contemporaneous tracking context rather than relying on a mutable sheet.
- On 2026-07-23, live `Sheet1!Q2:Q16` was reconciled to all 15 validated
  July 7 final-seeded products and `S2:S16` was reconciled to the active
  refinement queue. Snapshots were staged in all July 7/14/16/20/22/23 shared
  campaign folders and matching report directories. The July 14 meeting book
  was rebuilt and PDF-text verified to include the staged M/N/O/Q/S/T/V notes.

## Last Touched (2026-07-23): Durable Slow-Event PCRC Placement

- `dynamic_dispatch_campaign.py` carries `090618: pcrc_only` as a historical
  default and accepts a decision-record `host_constraint` of `pcrc_only` or
  `lyra_only` (and matching CLI lists). A PCRC-only event remains queued until
  PCRC is free; it cannot dispatch merely because a Pauley frees first. An
  explicit decision-record `any` can supersede the default after a documented
  memory reassessment.
- Classify future full `090618` runs as `pcrc_only`: its present run fits
  Pauley memory at eight workers but is a CPU-bound wall-clock outlier.
  Reassess only if its own preflight/first checkpoint demonstrates high/ultra
  memory use, in which case apply the Lyra high-memory rule.

## Last Touched (2026-07-23): 090618 High-Resolution Progress Baseline

- The resumed `090618` high-resolution final-final run on `pauley404-02` has
  a durable production checkpoint at `4400/5000` (`pt_resume_state.npz`,
  12:19 EDT).  All eight spawned workers were CPU-active at the check; this
  is real forward progress, not a stalled parent process.
- Its current resumed wall time was about 52.1 h, giving a simple linear
  remaining-MCMC estimate of about 7.1 h for the final 600 production
  iterations.  Treat this as an operational ETA only: the known expensive
  event can vary by checkpoint.  The existing checkpoint migration watcher
  remains responsible for a verified move to a free PCRC host, if one appears.

## Last Touched (2026-07-22): Fourteen-GRB Resolution-Refinement Queue

- Jonathan approved every completed July 16 baseline GRB for the next
  full-posterior-cloud refinement cycle. The authoritative planning queue is
  `reports/core_logangle_powerlaw_14grb_finalfinal_sthawed_resolution_refinement_queue/resolution_refinement_master_queue.csv`, copied with its README,
  audit CSVs, and decision records to
  `Share_Folder/Fits/production_runs/final_seeded_runs/26_07_22__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__resolution_refinement_queue_5_temperature_500x3000`.
- Common sampler for a new queue entry: 100 walkers, 5 temperatures, 500
  burn-in, 3000 production, and distinct finite joint samples from the current
  completed posterior. Nine newly dispatchable config/cloud pairs were built
  and validated under
  `structured_jet_core_logangle_powerlaw_14grb_finalfinal_sthawed_resolution_refinement_5temp_configs/`
  and `initial_positions/finalfinal_sthawed_resolution_refinement_5temp/`.
- Per-ladder selection: retain `(0.15,0.50,15)` for `050525A`, `050922C`,
  `080319B`, `090424`, `131030A`, `160131A`, `171010A`, and `220101A`;
  use very-fine `(0.30,1.00,30)` for `111228A` and `210905A`; fine
  `(0.20,0.666667,20)` for `130612A`; ultra-fine `(0.40,1.333333,40)` for
  `140506A`; and the existing fine `(0.20,0.75,20)` for `221009A`.
- Never duplicate a live chain: `130612A` and `210905A` are already running;
  `140506A` needs preflight-restart repair; `221009A` is gated on completion of
  its existing fine postfit/ladder; and `080413B` is gated on its current
  postfit/ladder. `090618` is excluded until its baseline MCMC and ladder are
  complete.
- Appended dated queue/gate notes to `GRB_Tracking` `Sheet1!S2:S16`, preserving
  prior current notes and the formatting. Connector reread confirmed every
  update.

## Last Touched (2026-07-22): Lyra Postprocessing Worker Allocation

- Lyra has 10 logical CPUs and substantial current headroom. All canonical
  Lyra postprocessor starters now set `PRODUCT_WORKERS=8` while retaining
  `MINIMIZER_WORKERS=8`; this reserves modest interactive/OS capacity and
  removes the previous four-worker cap for ordinary independent products.
- Updated starters: `start_postprocess_core_logangle_finalfinal_sthawed_5temp_1000x5000_lyra.sh`, and the dedicated `130612A`, `140506A`, `210905A`,
  and `221009A` starters. `bash -n` passed for each.
- This does not speed an already-running serial product. In particular, the
  `080413B` frequency diagnostic evaluates all 100 posterior curves over 200
  time points in one worker, so its active computation remains single-core by
  design to preserve the all-walker output. Improve that inner loop separately
  only after a safe multiprocessing/caching implementation is tested.

## Last Touched (2026-07-22): 210905A Very-Fine Continuation Launched

- `210905A` was approved for tonight's resolution-only continuation and
  launched on `pauley404-01` at `2026-07-22T23:37:16Z` with 8 workers. The
  active preflight session is `grb_finalveryfine_210905A`; it must complete
  its guarded 1+1 gate before the 500 burn-in plus 3000 production run begins.
- The campaign is
  `Share_Folder/Fits/production_runs/final_seeded_runs/26_07_22__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__veryfine_resolution_210905A__5_temperature_500x3000`.
  Its run tag is
  `core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_veryfine_5temp_500x3000_v1`.
- It uses all five temperatures and 100 walkers from distinct finite joint
  samples of the completed July 16 preferred low-p posterior, not a
  minimized-point Gaussian seed. The selected coupled grid is
  `(phi, theta, time) = (0.30, 1.00, 30)` samples per degree/per degree/per
  log10-time decade, the first tested 210905A level with both p95 and maximum
  flux shifts below 0.01 dex.
- Canonical launch/audit files are
  `reports/core_logangle_powerlaw_210905A_finalfinal_sthawed_veryfine_5temp_500x3000_campaign/{event_decision_records.json,dynamic_event_queue.csv,dispatch_manifest.csv}`.
  `start_postprocess_210905A_finalveryfine_500x3000_lyra.sh` and Lyra tmux
  supervisor `supervise_postprocess_210905A_finalveryfine_lyra` enforce
  minimization, all ordinary products, a fresh production-relative numerical
  ladder, validation, publication, and an incremental meeting-book refresh.
- Validation before dispatch: the cloud is finite with shape `(5, 100, 18)`;
  the event genuinely has 18 fitted parameters (do not impose a 26-parameter
  assertion copied from another GRB). Its TOML grid and dynamic-dispatch dry
  run both matched the requested values; the dispatcher found Pauley-01 idle.

## Last Touched (2026-07-21): Observed-Shell Mass and Mean Number-Density Posterior

- Standard density post-processing now writes a per-terminal-walker observed
  shell diagnostic for the first-to-last observed epoch.  For the analytic
  single-power-law CSM, `plot/visualize.py` evaluates
  `4 pi m_p integral[n(r) r^2 dr]` exactly; non-power-law models retain the
  generic numerical integration fallback.  It writes
  `density_shell_mass_walkers.csv`, `density_shell_mass_summary.json`, mass
  and mean hydrogen-number-density histograms, a mass-number-density corner
  plot (also showing `log10 n17` and `k`), and a slope-colored scatter plot in
  every completed event directory.  The public figures use atoms cm^-3;
  gram-density values remain in the CSV only for traceability.
- Shell radii are the fast analytic relativistic blast-wave radii derived from
  each walker's fitted on-axis `E_iso`, `n017`, `k`, and `Gamma_0`, not the old
  ballistic `2 c Gamma_0^2 t` shortcut.  The old shortcut could overestimate
  late-time radii by many orders of magnitude for high-Gamma walkers.  The
  summary JSON must contain `method_version = spherical-shell-dynamical-radius-v2`;
  `write_campaign_latex_summary.py` treats older products as stale.
- `DensityProfiler.save_profile_plot()` overwrites canonical PDF/PNG names.
  Do not use `save_plot_unique()` for standard regenerated products: it leaves
  stale base figures in place and makes numbered copies that the report does
  not select.
- `plot_campaign_density_shell_histograms.py` produces the matched two-panel
  campaign comparison in `histograms/density_shell_mass_density_comparison_histograms.pdf`.
  `write_campaign_latex_summary.py` requires the walker CSV, adds all four
  event products, and gives this paired campaign figure its own Section 3 page.
- The July 16 expanded-prior campaign was backfilled and validated for all 11
  published events: each CSV has exactly 100 finite positive walkers, and
  `mean_number_density_cm3 = shell_mass_g / (m_p * shell_volume_cm3)` holds to
  floating-point precision.  Its final `campaign_meeting_summary.pdf` has the
  paired comparison on page 216.  The verified existing v2-display products
  were marked `publication-ready-v2-display-masked-mass-gamma`; do not rerun
  expensive all-walker light curves solely for an old marker if direct
  freshness validation succeeds.
- LaTeX table symbols, including `N_phi`, `N_theta`, and `N_t`, are explicitly
  math-mode; long literal campaign identifiers use small fixed-width wrapped
  text on the cover.  Compilation had no overflow, undefined-control, or
  math-rendering errors (only benign underfull long-path notices).
- Validation: `py_compile`, `test_plot_extinction.py` (including the exact
  power-law spherical shell integral against a dense numerical reference), campaign
  product validation, Tectonic PDF compilation, text extraction, and rendered
  visual inspection.  `visualize.py`, the campaign shell plotter, the report
  generator, and the regression test were source-synced, SHA-256 matched, and
  compiled on PCRC-1/2, Pauley-01/02/03, and Carina.

## Last Touched (2026-07-21): 221009A Milky Way Extinction Plot Repair

- The 221009A fit is scientifically configured correctly: fixed
  `E(B-V)_MW=1.3021` with separately fitted `R_V^MW=2.46422` under the
  `milkywayrv` prior. The MCMC likelihood matches a direct `CCM89` evaluation
  exactly on its 105 extinguishable optical/UV data points.
- Fixed `plot/visualize.py` so dust attenuation is evaluated per wavelength.
  The previous vector-wide domain test returned unity for every band whenever
  radio or X-ray entries were present, so standard and spread-out plots omitted
  MW attenuation for their optical/UV curves even though the fit applied it.
  Out-of-domain bands now remain unity individually while valid optical/UV
  entries receive the fitted `R_V^MW` law.
- `plot_spread_light_curves.py` cache is now version 5 and records a signature
  of the chain/model/postfit inputs, preventing stale postfit curves after a
  fit or configuration changes. `test/test_plot_extinction.py` guards the
  mixed radio-plus-optical regression.
- Regenerated the July 16 221009A standard and all spread light-curve products
  plus the campaign meeting book. Validation: the likelihood and plot helper
  both matched direct CCM89 attenuation to machine precision; the mixed-band
  regression test and `py_compile` passed.
- Synced the corrected plotting scripts and regression test to PCRC-1/2,
  Pauley-01/02/03, and Carina. On every host, `py_compile`, the regression
  test, and SHA-256 equality to Lyra passed. Use
  `rsync -e 'ssh -x -o ForwardX11=no -o BatchMode=yes'` for remote source
  updates so rsync does not reintroduce X11-forwarding warning noise.

## Last Touched (2026-07-21): Density-Profile Framing and Walker Extents

- `scripts/plot/visualize.py` retains all finite terminal cold-chain walkers
  in the density profiles, using a robust lower display limit (central 1% plus
  a small margin) while always extending the upper limit through the maximum
  plotted walker value. This avoids a low-side outlier dominating the frame
  without ever clipping a real high-side density curve.
- The fast analytic single-power-law path now restores walker-specific radial
  extents. Each curve uses its own fitted Gamma0 and optional jet-break end
  time to form its radius grid, avoiding the previous shared start/stop while
  also avoiding a costly native VegasAfterglow solve per walker.
- `write_campaign_latex_summary.py` now treats all numerical fitted-parameter
  columns as math-capable and wraps scientific notation in math mode, so
  `times 10^n`, symbols, and subscripts render correctly in the PDF tables.
- Backfilled density-profile PDF/PNG products for 42 canonical completed
  single-power-law runs: June 29 unseeded, July 7 final-seeded, July 14
  prototype, and July 16 final-final. Rebuilt the July 7 (240 pages), July 14
  (29 pages), and July 16 (180 pages) meeting-book PDFs. Validation confirmed
  successful 100-walker metadata for all completed July 7/16 events, no
  density-profile failures, Python compilation, and visual checks of 050525A.

## Last Touched (2026-07-21): Later-Campaign Meeting-Book Refresh

- `write_campaign_latex_summary.py` now renders campaign identifiers with
  literal double underscores and lets them wrap inside the setup table. Long
  seed-source paths use an in-cell line break immediately before the final
  campaign-folder component, rather than breaking the table row.
- Rebuilt the July 14 prototype book (090424) and July 16 expanded-prior
  moderate-resolution book (11 validated GRBs) after regenerating each
  available swept-mass/Gamma diagnostic, v16 resolution ladder, and campaign
  convergence comparison. The July 16 PDF is
  `Share_Folder/Fits/production_runs/final_seeded_runs/26_07_16__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__moderate_resolution__5_temperature_1000x5000/campaign_meeting_summary.pdf`.
- Added campaign-root `campaign_metadata.json` for July 14 and July 16, making
  their seed source, posterior-cloud initialization, thawed-s purpose,
  sampler, and resolution durable.
- Validation: `py_compile`, successful Tectonic compilation of both books, and
  rendered visual inspection of the July 16 setup table.

## Last Touched (2026-07-20): PCRC Worker Policy

- `dynamic_dispatch_campaign.py` has an enforced known-host policy: PCRC is
  15 workers during the current summer allocation (16 logical CPUs, reserve
  one), while Pauley and Lyra are 8. A mismatched `--machines` specification
  fails before dispatch. Pass `--pcrc-workers 14` for the student-use season,
  or the explicit one-off override flag only when intentional.
- `start_dynamic_dispatch_finalfinal_sthawed_5temp_1000x5000_lyra.sh` now
  names PCRC-1 and PCRC-2 at the policy count. The live dispatcher was
  restarted after `bash -n`, `py_compile`, a valid-policy test, and a
  deliberate PCRC:8 rejection test; active MCMC pools were not modified.
- Checkpointed resize is supported without losing samples:
  `watch_finalfinal_checkpoint_worker_resize.sh` verifies the durable
  `pt_resume_state.npz` twice, stops only the named tmux session, resumes with
  `RESUME=1` and `CLEAN_INCOMPLETE=0`, verifies no checkpoint regression, then
  updates manifest workers. Active watcher sessions are
  `watch_220101A_pcrc_workers15` and `watch_080413B_pcrc_workers15`.
  The existing `watch_090618_checkpoint_migration_to_pcrc.sh` now resumes on
  PCRC with 15 workers and records that value in the manifest after a verified
  cross-host handoff.

## Last Touched (2026-07-20): 221009A Fine-Resolution Continuation

- `221009A` was the highest-resolution-priority completed final-final fit:
  its moderate-to-extreme-fine maximum modeled-flux shift was 0.0624 dex. Its
  isolated-control ladder shows the material dependence is polar resolution;
  the approved next coupled grid is `(phi, theta, time) = (0.20, 0.75, 20)`.
- The isolated campaign is
  `reports/core_logangle_powerlaw_221009A_finalfinal_sthawed_fine_5temp_500x3000_campaign`
  and publishes to the correspondingly dated `Share_Folder` fine-resolution
  campaign. It uses the original full 5-temperature, 100-walker posterior
  cloud, 500 burn-in and 3000 production iterations, on `pauley404-01` with
  8 workers. A 1+1 preflight completed with all 500 tempered walkers valid
  before the production tmux session `grb_finalfine_221009A` launched at
  `2026-07-21T01:08:25Z`.
- `start_postprocess_221009A_finalfine_500x3000_lyra.sh` starts the dedicated
  Lyra-only watcher for this one-event campaign. It requires the same complete
  publication-ready products and v2 resolution ladder before publishing.

## Last Touched (2026-07-21): Campaign Meeting-Book Refinement

- `write_campaign_documentation.py` now writes durable `campaign_metadata.json`
  alongside `README.md` and `CAMPAIGN_METHOD_REPORT.md`. It records the
  campaign abstract, scientific purpose, seed-source campaign, and explicit
  initialization method. `write_campaign_latex_summary.py` reads that file
  into the title-page abstract and Campaign Set-up table; if the setup record
  begins in the report directory, the first shared-book refresh copies it into
  the shared campaign folder.
- The meeting book now orders the per-GRB light-curve pages as standard fit,
  16th--84th posterior envelope, all 100 retained terminal walkers, then the
  numerical-resolution overlay/convergence page. Spectra precede critical
  frequencies. Dylan/AMPy parameter-comparison bar charts are retained as
  audit products but omitted from the meeting book.
- Fitted parameter rows use a shared row precision and common scientific
  exponent when needed. Fixed-parameter descriptions include cosmological
  redshift, luminosity distance, jet angular indices, and numerical controls.
  Campaign comparison pages put the two convergence comparisons first in a
  vertical pair, then place related landscape figures two per page.
- `plot_vegas_resolution_ladder.py` v16 preserves the two nearest coarser
  levels, production, and every finer level in the signed/absolute top-panel
  y ranges. Very coarse outliers can clip vertically rather than flattening
  the convergence neighborhood. It also has `--campaign` for the standard
  campaign-wide convergence and viewing-angle figures.
- `plot_structjet_swept_mass_diagnostics.py` masks only zero/underflow-like
  display artifacts after all physical crossings are calculated, and chooses
  mass/Lorentz y limits from the observed time/radius window. The raw model
  arrays and crossing CSV calculations remain unchanged.
- Rebuilt the July 7 final-seeded book and all 15 event mass/gamma and
  resolution-plot products. Shared metadata now explicitly records its June
  29 unseeded source and minimized-center Gaussian posterior-width seeding.

## Last Touched (2026-07-20): 130612A Fine-Resolution Queue

- `130612A` is the second priority resolution refinement. Its isolated
  full-cloud campaign is queued as `pending-next-free` in
  `reports/core_logangle_powerlaw_130612A_finalfinal_sthawed_fine_5temp_500x3000_campaign`.
  It uses `(phi, theta, time) = (0.20, 2/3, 20)`, 100 walkers, 5 temperatures,
  500 burn-in, and 3000 production iterations.
- `start_dynamic_dispatch_130612A_finalfine_500x3000_lyra.sh` only dispatches
  when a host has no `jetfit.run`, preventing unsafe sharing with a different
  campaign. `start_postprocess_130612A_finalfine_500x3000_lyra.sh` is the
  matching Lyra-only publisher and resolution-ladder watcher.

## Last Touched (2026-07-20): Per-Event Meeting Books and Publication-Ready Products

- Canonical watcher `postprocess_core_logangle_powerlaw_15grb_10temp.sh` now
  treats the fixed-minimized-solution VegasAfterglow ladder as a validation
  requirement whenever `RESOLUTION_CONVERGENCE=1`: summary/flux CSVs, overlay
  PDF/PNG, absolute convergence PDF/PNG, signed convergence PDF/PNG, and a
  current versioned metadata record must exist before an event receives
  `core_postfit_products.validated`.
- After each event publishes, the watcher immediately runs
  `write_campaign_latex_summary.py`, which refreshes the partial campaign
  comparisons and meeting book using only validated event directories. It
  writes `.campaign_meeting_summary.pending` while a retry is needed and
  `.campaign_meeting_summary.updated` after success. The final campaign marker
  is still written only once all manifest rows validate.
- The required ladder data version is
  `coupled-grid-relative-to-production-v2`: all three controls use exactly the
  common ratios `1/6, 1/3, 1/2, 2/3, 1, 4/3, 2, 8/3, 4` relative to the actual
  production tuple, plus independent phi/theta/time half/double controls.
  Historical mixed-theta ladders are automatically recomputed before plotting,
  rather than being relabeled as coupled tests.
- Standard products use `publication-ready-v1`. `JETFIT_PLOT_RUN_LABEL` is now
  retained for metadata/debugging but is printed only when
  `JETFIT_STAMP_PLOT_RUN_LABEL=1`; routine figures omit source filenames and
  run tags. `write_campaign_latex_summary.py` supplies scientific figure
  captions suitable as paper-draft starting text.
- Smoke test: recomputed, rendered, and validated final-final `050525A` with
  the v2 ladder; verified every coupled ratio and confirmed representative
  light-curve, corner, spectrum, mass, and AMPy PDFs contain no path/run-tag
  footer. `bash -n` and `py_compile` passed for all touched scripts.
- Synced the tested source files to PCRC-1/2, Pauley-01/02/03, and Carina and
  verified SHA-256 equality at their real paths. Older Pauley/Carina `rsync`
  rejects `--protect-args`; use portable `rsync -a` with explicit relative
  destinations for these hosts. Do not flatten multiple source files into the
  remote project root.
- `write_campaign_documentation.py` now emits the numerical-resolution and
  per-event meeting-book method in `README.md` and `CAMPAIGN_METHOD_REPORT.md`.
  The live 2026-07-16 copies were regenerated. `111228A` is a review-required
  event, not a scheduling block; its live final-final result was pulled to
  Lyra and was in minimization during this audit.
- Recovery test: `111228A` completed minimization successfully
  (`nmap=-11784.621866`), then ordinary products and the v2 ladder. The
  validator correctly stopped publication when the standalone plotter omitted
  `.resolution_plot_version`. `plot_vegas_resolution_ladder.py` now writes its
  own `signed-primary-convergence-and-16core-runtime-v15` marker for both
  event and campaign modes. Replotting and local/shared validation passed;
  `111228A` was published as event 11/15 and the Lyra watcher was restarted
  with a pending meeting-book refresh.

## Last Touched (2026-07-20): Meeting-Book Refresh and Comparison Resilience

- Resolution-ladder light curves now use the cached
  `light_curve_spread_out_shaded_posterior` construction as their template:
  same observations, legend, exact 80-point model grid, and spread factors,
  but deliberately no posterior shading. Resolution alternatives are smooth
  solid curves (coarse light, fine dark); the actual production fit is a thick
  dashed underlay. This avoids the old jagged observation-time-only ladder
  plot. Per-event smooth traces cache in
  `resolution_ladder/resolution_light_curve_model_data.npz`.
- The overlay key belongs at lower left to avoid the data-rich lower-right
  region. It labels the production tuple with units explicitly: phi/theta
  angular samples per degree and time samples per log10 decade. Running report
  headers use the literal campaign folder name in tiny `\texttt{}` form so
  underscores cannot be lost or converted by LaTex.
- `resolution_convergence.pdf` is now a readable 2x2 page: coupled angular
  flux/statistic convergence above, coupled-grid runtime below left, and the
  restored isolated phi/theta/time sensitivity bars below right. Coupled axes
  are explicit ratios to published production, with every actual tested ratio
  ticked and vertical-gridlined. The extreme-fine reference has no
  zero-by-definition marker on log convergence axes; it remains a dashed
  `reference grid` line and contributes its real runtime. New ladder CSVs,
  summaries, and metadata record `production_multiplier` explicitly. The
  report places the page immediately after the posterior envelope and its
  resolution-overlay companion, rather than in a detached end-of-book section.
  The July 7 book was rebuilt and PDF-text-checked for the `140506A` sequence:
  envelope, overlay, convergence, spectral breaks.
- Convergence diagnostics are now referenced to the actual production MCMC
  grid, not extreme fine: the production point is plotted as a meaningful
  zero, while the `reference grid` remains a vertical guide. Flux-difference
  values (already dex) and fit-statistic differences are linear-y plots, so
  smaller means closer to the production calculation. Runtime is an estimated
  full-MCMC wall clock in hours: recorded production `real` time multiplied by
  the fixed-model cost ratio. The left axis names the real source host and
  run-log worker count; the right is a core-count-only normalization to the
  alternate standard host (PCRC 16 cores, Pauley 8 cores).
- Every resolution-ladder directory receives both convergence views. The
  primary meeting-book page is `resolution_convergence_signed.pdf/.png`, a
  2x2 plot with signed 16th/50th/84th-percentile `log10(F/F_production)`,
  signed `fit statistic - production`, repeat-MCMC runtime, and isolated
  control magnitude sensitivity. The absolute-magnitude
  `resolution_convergence.pdf/.png` remains available as a technical
  supplementary tolerance diagnostic.

- Resolution convergence is now a standard completed-event post-fit product.
  `postprocess_core_logangle_powerlaw_15grb_10temp.sh` runs
  `run_vegas_resolution_ladder.py` followed by the per-event plotter before
  validation/publication. The test fixes the minimized solution and changes
  only VegasAfterglow resolution; it is serial by default, so each expensive
  fine evaluation gets an isolated CPU process and does not contend with other
  ladder levels.
- The ladder reads the actual published resolution controls. When older result
  files legitimately lack explicit controls, it records the real engine native
  default `(0.10, 0.25, 10)` rather than borrowing a newer campaign setting.
  Every ladder uses four coupled refinement steps above production (1.33x, 2x,
  2.67x, 4x), satisfying the minimum fine-resolution check.
- `resolution_light_curve_overlay` is one spread-out, all-band panel: observed
  bands retain their standard colors; coarser grids are lighter shades and
  finer grids darker shades of each band; the actual production curve is the
  thickest line but is drawn underneath alternatives. It now uses the same
  portrait `8 x 10` geometry, days/seconds axes, external band key, and
  spacing factors as `light_curve_spread_out_shaded_posterior`. It follows the
  ordinary diagnostic figures directly (not a separate subsection). The
  end-of-book convergence appendix keeps one
  diagnostic per GRB with production marked against the extreme-fine reference.
- Backfilled and regenerated the July books: 2026-07-07 now has all 15
  ladders, 2026-07-14 has its 090424 ladder, and the live 2026-07-16 book has
  ladders for its 10 currently published events. Validation: Python compile,
  Bash syntax, one full old-layout fallback run, PDF text counts, and visual
  inspection of an in-section 090424 overlay.
- Title pages now name the `VegasGRBruns` relative path and exact campaign
  folder, include the saved campaign rationale as an abstract, and give a
  blue linked GRB quick-list. The running header uses the campaign title plus
  file date and document-generation date; the right side retains the current
  GRB subsection. Run-index tables include a final summed wall-clock row.
- Campaign-root plot PNG/PDF/CSV artifacts are organized together. Explicit
  scheduling/organization manifests remain at the root, while histogram,
  scatter, convergence, and resolution data CSVs move beside their figures.
  Comparison figures are non-floating, preventing an empty first comparison
  page; table-local spacing is deliberately compact so common-prior tables do
  not spill onto a nearly empty continuation page.
- `write_campaign_latex_summary.py` now generates a meeting-oriented book with
  no contents page; a linked GRB run index (host and measured `run.log` wall
  time); event `\subsection` headers carried onto their first standard
  one-panel light-curve page; core, CSM, full physical, and non-physical
  corners in that order; the single two-panel swept-mass diagnostic; and
  fitted-parameter tables containing symbol, physical meaning, minimized
  value, posterior median, and plus/minus 68% intervals. Fixed values are kept
  in their own table.
- The report refreshes only completed events with missing/stale products, then
  refreshes campaign histograms and minimized comparison plots before compiling.
  It therefore produces a useful partial book during a live campaign without
  postprocessing active MCMCs. Root aggregate plots are organized into
  `histograms/` and `comparison_plots/`; regenerated same-named plots replace
  their earlier organized copy safely.
- `plot_minimized_core_mass_vs_solid_angle.py` records, rather than aborts on,
  runs whose minimizer reports failure. It writes
  `minimized_comparison_skipped_runs.csv` alongside the valid scatter products.
  On 2026-07-20, the live 2026-07-16 campaign excluded only `171010A` for this
  reason; do not interpret that omission as a scientific rejection.
- Rebuilt and checked July books: 2026-07-07 final seeded (15 events),
  2026-07-14 thawed-`s` prototype (one event), and the live 2026-07-16
  expanded-prior moderate-resolution campaign (10 published events when made).
  Validation: `py_compile`, Tectonic compilation, PDF text checks for no
  contents and presence of the run index, plus rendered setup/index/first-GRB
  pages.

## Last Touched (2026-07-20): Signed Convergence as Primary Report Page

- Replotted all 15 July 7 final-seeded event ladders with the completed signed
  2x2 design and rebuilt `campaign_meeting_summary.pdf` with
  `--no-refresh-products`. The final 247-page book was checked by PDF text:
  15 signed per-GRB captions and 15 resolution-overlay captions are present.
- `write_campaign_latex_summary.py` embeds the signed page directly after the
  resolution overlay. The thick dashed curve is now labeled only
  `production` in both the overlay key and report caption.
- The signed top panels preserve zero and choose the more informative vertical
  scale: finite coarsest-level extent or ten times the largest signed shift at
  the immediate production neighbors, whichever is tighter. If a coarsest
  flux evaluation has no finite values (`050525A`), the neighbor scale is used
  directly so Matplotlib never receives NaN axis limits.
- Zero deliberately sits 30% of the way up each signed panel (30% below,
  70% above). The 10x immediate-neighbor rule defines the entire vertical span
  rather than a symmetric plus/minus half-range.

## Last Touched (2026-07-20): 090618 Safe PCRC Migration Watcher

- `watch_090618_checkpoint_migration_to_pcrc.sh` is a Lyra-only operational
  watcher for the active final-final `090618` MCMC. Start it in tmux session
  `watch_090618_checkpoint_migration_to_pcrc`; it is already armed as of
  2026-07-20 21:08 UTC.
- It requires a stable `pt_resume_state.npz` checkpoint with at least 100
  completed iterations and a completely idle/reachable PCRC host. It stages
  the result directory through Lyra, validates the destination checkpoint,
  stops the source tmux session only after that validation, launches with
  `RESUME=1`, confirms `jetfit.run`, and atomically updates the final-final
  manifest. No PCRC availability means no source interruption. A failed
  destination launch resumes Pauley automatically from its preserved state.

## Vendored Engine Status (2026-05-29)

- The reproducible VegasAfterglow engine is now vendored at:
  - `/Users/jkeohane/GRBs/VegasJetFit/external/VegasAfterglow`
- Install/verify script:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/setup_vendored_vegasafterglow.sh`
- Repro docs:
  - `/Users/jkeohane/GRBs/VegasJetFit/REPRODUCIBILITY.md`
  - `/Users/jkeohane/GRBs/VegasJetFit/ETHAN_SETUP_ON_MAC.md`

## Known Relevant Files

- `generate_postfit_products.py`
  - builds radius-based post-fit products
  - creates `mass_profile.csv` and `mass_profile.pdf`
  - relevant terms: `m_swept_iso_g`, `m_decel_iso_g`, `m_ejecta_iso_g`, `r_decel_cm`, `r_ejecta_equal_cm`

- `build_mass_vs_time_products.py`
  - builds mass-vs-observer-time products
  - calls `model.vegas_model.details(...)`
  - known fields used: `details.fwd.t_obs`, `details.fwd.N_p`
  - need to identify the instantaneous forward-shock Lorentz factor field in `details.fwd`

## Current Swept-Mass Issue

The old diagnostic uses:

```text
M_ej / Gamma0
```

The desired diagnostic uses instantaneous Lorentz factor:

```text
M_ej / Gamma(t or r)
10 M_ej / Gamma(t or r)
```

The Gamma array must be on the same grid as swept-up mass, observer time, and radius, or it must be explicitly interpolated and documented.

Preserve units:

- time plot bottom axis: days
- time plot top axis: seconds
- radius plot bottom axis: cm
- radius plot top axis: parsecs
- mass plot left axis: grams
- mass plot right axis: solar masses

Do not update anything inside a `trash` folder.

## Notes for Future Codex Sessions

Before searching broadly, inspect this file and the root-level files:

- `/Users/jkeohane/GRBs/AGENTS.md`
- `/Users/jkeohane/GRBs/CODEX_HANDOFF.md`
- `/Users/jkeohane/GRBs/WORKSPACE_MAP.md`
- `/Users/jkeohane/GRBs/CODEX_TODO_WHEN_TOKENS_RETURN.md`

If the forward-shock Lorentz-factor field in `details.fwd` is discovered, record it here with the exact field name, array shape, and the line/file where it is used.

## Default Dynamic Dispatch Practice

- Policy document: `/Users/jkeohane/GRBs/VegasJetFit/DISPATCH_POLICY.md`.
- Reusable dispatcher: `/Users/jkeohane/GRBs/VegasJetFit/scripts/dynamic_dispatch_campaign.py`.
- New multi-GRB campaigns should use dynamic dispatch by default:
  first batch fills all machines including Lyra, later events are assigned only
  when a host frees, and Lyra receives no second MCMC run unless explicitly
  overridden.
- Event launchers should enforce the central manifest via `DISPATCH_MANIFEST`
  so stale static queues skip reassigned events instead of duplicating runs.

## Last Touched (2026-07-20): Campaign Meeting Books

- Added `write_campaign_latex_summary.py`, the canonical portable generator for
  a campaign-root `campaign_meeting_summary.tex` and corresponding single PDF.
  It reads published event `model.toml`, `mcmc_settings.toml`, minimized
  parameters, fixed parameters, and product PDFs. It presents thesis-style
  diagnostics first, current additional products next, then campaign comparison
  plots/histograms.
- Safe organization behavior: only loose root-level campaign `.pdf`/`.png`
  files are moved. Histogram-named products go to `histograms/`; scatter,
  comparison, convergence, and other aggregate figures go to
  `comparison_plots/`. It never changes GRB event folders or any `trash` path,
  and writes `campaign_plot_organization.csv` as an audit trail.
- The common postprocessor now calls the generator only after all manifest
  events publish and after campaign aggregate plots are made. The final-final
  Lyra launcher supplies explicit title/purpose text. `tectonic` is installed
  on Lyra via Homebrew to compile the PDF.
- Retroactively generated and visually checked books:
  `26_06_25` unseeded mixed CSM (200 pages), `26_06_27` unseeded single CSM
  (201), `26_06_29` unseeded k[-10,3] (217), `26_07_07` final seeded (203),
  and `26_07_14` 090424 thawed-s prototype (16). The current live final-final
  campaign is deliberately omitted until its `campaign_products.validated`
  marker is written.
- Regenerate one campaign with:
  `/Users/jkeohane/GRBs/.venv/bin/python scripts/write_campaign_latex_summary.py --campaign <campaign-dir>`.
  For finished historical campaigns, use
  `--all-under /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs --complete-only`.
- Validation: Python compile; Bash syntax checks for both watcher scripts;
  `tectonic` compilation; PDF page-count and text-heading checks; visual render
  of the title/setup pages; and campaign-root loose-plot audit.

## Last Touched (2026-07-15): Consolidated Final-Final Prior Defaults

- `build_structured_jet_ejet_configs.py` now defaults to the agreed
  final-final policy: core energy `[-4,2]`, Gamma `[log10(50),5]`, density
  `[-6,10]`, `eps_e [-6,0]`, `eps_B [-10,0]`, `p [2,3.5]`, thawed
  `s [0.1,10]`, log angles `theta_c [-3,0]` / `theta_v [-4,0]`, and
  source-frame `E(B-V) [0,1]`. It removes an existing `Gamma_0_core_avg`
  entry before inserting the canonical core-Gamma parameter, preventing a
  duplicate fitted coordinate.
- `build_core_logangle_15grb_campaign.py` uses the same defaults for future
  campaign builds. Validate new configs with `Parameters.from_toml` and keep
  published/running configuration files immutable.

## Last Touched (2026-07-16): Final-Final Lyra Postprocessor

- `start_postprocess_core_logangle_finalfinal_sthawed_5temp_1000x5000_lyra.sh`
  launches only the final-final postprocessing watcher in Lyra tmux session
  `postprocess_core_logangle_finalfinal_sthawed_5temp_1000x5000_lyra`; it does
  not dispatch MCMC. Products publish to the separate dated expanded-prior v2
  Share_Folder campaign, never the old 090424 v1 prototype folder.
- `postprocess_core_logangle_powerlaw_15grb_10temp.sh` ignores queued, pending,
  blocked, blank, and `n/a` manifest host fields. These are scheduling states,
  not SSH hosts; this prevents repeated SSH lookup errors while the queue is
  deliberately held.

## Last Touched (2026-07-16): Campaign Documentation Standard

- `write_campaign_documentation.py` reads canonical TOMLs and the dispatch
  manifest to write a concise `README.md` and a full
  `CAMPAIGN_METHOD_REPORT.md`. Run it before the first MCMC launch and again
  after any configuration or manifest change; it prevents future run cards from
  drifting away from the actual fitted bounds and special priors.
- `DISPATCH_POLICY.md` now requires those two generated documentation files for
  each new campaign. The final-final campaign's versions are in
  `reports/core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_1000x5000_campaign/`.

## Last Touched (2026-07-15): Density-Profile Walker Coverage

- `generate_postfit_products.py --only-product density-profiles` now evaluates
  the terminal cold-chain state of every finite walker, rather than flattening
  the entire chain and randomly drawing the watcher-limited subset. The
  minimized density profile remains a separate overlay.
- For the production single-power-law CSM models, the posterior curves use the
  exact analytic `n(r)=n017*(r/r_ref)^(-k)` law on each walker's analytic
  relativistic blast-wave radius domain.  The radius approximation uses fitted
  on-axis `E_iso`, `n017`, `k`, and `Gamma_0`, avoiding an expensive native
  VegasAfterglow solve per walker without the unphysical late-time growth of
  the retired ballistic Gamma0 shortcut.
- `JETFIT_DENSITY_PROFILE_SAMPLES=0` means all terminal finite walkers and is
  now the default in the three core campaign postprocessors. A positive value
  is an explicit performance override. Each regenerated result directory now
  writes `density_profile_sampling.json` with available, finite, excluded, and
  plotted walker counts.
- Validation: the completed 050922C unseeded 10-temperature chain has 100/100
  finite terminal cold walkers; its locally regenerated density profiles record
  `plotted_walkers=100` and `uses_all_finite_final_walkers=true`. Shared
  refreshes were also verified for unseeded 050525A and final-seeded 050922C.

## Last Touched (2026-07-15): Remaining Walker-Curve Audit

- Standard frequency plots remain a 100-curve random posterior diagnostic,
  rather than an all-final-walker product. A direct 100-final-walker trial did
  not complete reliably with the native frequency solver; do not claim that
  `frequencies.*` shows all walkers until it is redesigned with isolated or
  batched native-model evaluation.
- Spread-light-curve products already request all final walkers
  (`--walker-limit 0`); their cache is now rejected unless its walker stack
  exactly matches the current final-walker count. Swept-mass/Gamma diagnostics
  already evaluate every final cold-chain walker.
- The 50,000-sample corner cap and the 5,000-per-event campaign density--`k`
  scatter cap are intentional posterior-cloud display limits, not walker-curve
  limits. Their statistics are computed from the full posterior; do not
  describe those dense plots as all-walker curves.

## Last Touched (2026-07-15): 221009A Milky-Way Prior Builder Guard

- `build_structured_jet_ejet_configs.py` now gives 221009A
  `rv_milky_way` the dedicated `{type = "milkywayrv"}` prior and raises if
  generation ever produces anything else. This special prior is required with
  fixed `ebv_milky_way=1.3021`; a generic log-uniform `R_V` range is not an
  acceptable substitute for this event.

## Last Touched (2026-07-07): 171010A Final Seeded One-Event Launch

- One-event release from the pending final-seeded campaign after Jonathan marked
  tracking-sheet row 13 / `171010A` ready.
- Host/session: `pauley404-02`, tmux `grb171010A_final_seeded`.
- Run tag: `core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_v1`.
- Files added:
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/171010A_core_logangle_powerlaw_kminus10to3_final_seeded_10temp_5000_campaign/README.md`
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/171010A_core_logangle_powerlaw_kminus10to3_final_seeded_10temp_5000_campaign/dispatch_manifest.csv`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/171010A.core_logangle_kminus10to3_final_seeded_10temp_5000x5000_v1.pauley02.launch.sh`
- Files synced to `pauley404-02`: event runner, thesis reproduction runner,
  `171010A.toml`, 5000x5000 MCMC settings, one-event report directory, and
  launch wrapper.
- Validation: local/remote `bash -n` passed; remote `Parameters.from_toml`
  loaded 19 fitted parameters and confirmed `n017.upper = 10.0`; preflight
  passed all 10 temperatures with `100/100` valid walkers; full production
  started and worker processes were consuming CPU.
- Remaining uncertainty: MCMC is still running; pull back to Lyra for
  minimization/postfit/Drive publication after completion.

## Last Touched (2026-07-08): 210905A p<2.2 Branch Products

- Added reusable branch-filter helper:
  `/Users/jkeohane/GRBs/VegasJetFit/scripts/make_parameter_filtered_branch.py`.
- Used tracking-sheet row 14 / `M14` to isolate the good `210905A` posterior
  island by filtering fitted `p < 2.2`.
- Branch product folder:
  `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000/210905A/p_lt_2p2_branch_products`.
- Selection: `136370 / 500000` finite samples (`27.274%`), repacked into
  branch `chain.npz` shape `(13637, 10, 17)` with no dropped samples.
- Branch minimization: 10 filtered walkers, `nmap=-2554.0295715`,
  `p=2.0804184`, `k=0.5410675`, `n017=73.246394`, successful Powell.
- Regenerated branch products: trace/summary, corners, jet-energy products,
  light curves, spread light curves, AMPy comparison, swept-mass diagnostics,
  Gamma/jet-break diagnostics, spectrum-timeseries, and frequency products.
- Density-profile plots were intentionally left absent after default,
  20-sample, and 3-sample attempts remained CPU-active without output for
  several minutes; the caveat is recorded in the branch `README.md`.
- Logs:
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/210905A_p_lt_2p2_branch_minimize_20260708.log`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/210905A_p_lt_2p2_branch_postfit_20260708.log`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/210905A_p_lt_2p2_branch_frequencies_fast_20260708.log`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/210905A_p_lt_2p2_branch_density_fast_20260708.log`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/210905A_p_lt_2p2_branch_density_3sample_20260708.log`
- Validation: `py_compile` passed for the new helper; inventory found 61/61
  expected branch files present and non-empty; selected-sample NPZ shape is
  `(136370, 17)` with `max(p)=2.199947`; visual checks of `corner_csm.png` and
  `light_curve.png` rendered normally.
- Superseded later on 2026-07-08: Jonathan approved launching the final seeded
  run from this branch-centered solution; see next note.

## Last Touched (2026-07-08): 210905A Final Seeded Branch-Centered Launch

- Updated pending final-seeded config:
  `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending/210905A.toml`.
- Seeded uniform fitted parameters at the branch-local minimized fit-space
  vector from:
  `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000/210905A/p_lt_2p2_branch_products/minimized/minimized.json`.
- Important seed coordinates: `p=2.0804184`, `k=0.5410675`,
  `log10(n017)=1.8647862`; branch-posterior 16th-84th half-widths from the
  `p < 2.2` samples were used as `initial_sigma`.
- Gaussian offset priors (`J/H/K`) were left scientifically unchanged because
  the current prior class does not use `initial_guess`; their means/sigmas
  remain the calibration priors.
- Added launch/report files:
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/210905A_core_logangle_powerlaw_kminus10to3_final_seeded_10temp_5000_campaign/README.md`
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/210905A_core_logangle_powerlaw_kminus10to3_final_seeded_10temp_5000_campaign/dispatch_manifest.csv`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/210905A.core_logangle_kminus10to3_final_seeded_10temp_5000x5000_v1.pauley01.launch.sh`
- Updated central final-seeded dispatch manifest:
  `/Users/jkeohane/GRBs/VegasJetFit/reports/core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_pending/dispatch_manifest.csv`.
- Synced runner, event config, MCMC settings, manifests, report, and launch
  wrapper to `pauley404-01`.
- Launched on `pauley404-01` in tmux `grb210905A_final_seeded`; run tag
  `core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_v1`.
- Validation: local and remote `bash -n` passed; local and remote
  `Parameters.from_toml` confirmed 17 fitted params and branch-centered
  `p/k/n017`; no existing result directory on `pauley404-01`; preflight passed
  all 10 temperatures with `100/100` valid walkers; full production started and
  all 10 production temperatures reported `100/100` valid walkers.
- Tracking sheet: verified `Sheet1!M14` Dan note and `N2:N3` big-picture notes,
  then wrote Jonathan-style launch note to `Sheet1!O14`.
- Remaining uncertainty: MCMC is still running; pull back to Lyra for
  minimization/postfit/Drive publication after completion.

## Last Touched (2026-07-08): Campaign Plot Archive-Folder Filtering

- Patched campaign-level plotting scripts to ignore side-by-side comparison or
  archived event folders whose names contain `_no_`, plus `trash` and hidden
  folders:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_campaign_physical_parameter_histograms.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_minimized_core_mass_vs_solid_angle.py`
- Reason: Jonathan preserved the previous 090424 product folder as
  `090424_no_early_UVOT` beside the canonical replacement `090424` folder in
  the 26_06_29 k[-10,3] campaign. Campaign summaries should count only the
  canonical event folder, not the preserved comparison folder.
- Validation: `py_compile` passed; campaign histograms/scatterplots regenerated
  for 15 events; refreshed CSVs did not contain `090424_no_early_UVOT`.

## Last Touched (2026-07-08): 160131A k<-4 Cavity Branch

- Used `/Users/jkeohane/GRBs/VegasJetFit/scripts/make_parameter_filtered_branch.py`
  to refresh the `160131A` cavity branch requested from tracking-sheet cell
  `M12`.
- Source run:
  `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/160131A_core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_v1`.
- Output branch folder:
  `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000/160131A/k_lt_minus4_products`.
- Filter: fitted `k < -4`, selected `256662 / 500000` finite samples,
  repacked shape `(25666, 10, 20)`.
- Branch minimization preserved the best selected seed after Powell worsened
  the objective: `nmap=-15133.942111`, `k=-6.6808515`,
  `p=2.0369595`, `n017=23034.2135`.
- Regenerated standard branch products and validation passed. Density profiles
  remain deferred after bounded 10-sample regeneration stayed CPU-active without
  producing files; the branch README documents this caveat.

### Discovered Forward-Shock Lorentz Field

- Field: `details.fwd.Gamma`
- Access pattern used in current scripts: `details.fwd.Gamma[0, 0, :]`
- Grid compatibility: aligned with `details.fwd.t_obs[0,0,:]`, `details.fwd.r[0,0,:]`, and `details.fwd.N_p[0,0,:]` in the current VegasAfterglow detail output.
- Current usage locations:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_mass_vs_time_products.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py`

## Spectral/Frequency Plot Convention (2026-06-04)

- `frequencies.pdf` is the standard frequency diagnostic for final Share_Folder products.
- Do not produce or sync `spectral_plot.pdf`, `spectral_plot.png`, or `spectral_breaks_eats_weighted.csv` in normal production/postfit/share pipelines. These are retired standard products and should remain in `trash` unless Jonathan explicitly asks for a one-off diagnostic.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_weighted_spectral_breaks.py` and `/Users/jkeohane/GRBs/VegasJetFit/scripts/batch_weighted_spectral_posteriors.py` now skip by default; they require `--write-retired-products` before writing the retired spectral outputs.
- `/Users/jkeohane/GRBs/VegasJetFit/jetfit/run.py` keeps `frequencies.pdf` and no longer aliases it to `spectral_plot.pdf`.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` excludes and removes the retired spectral filenames so stale local copies cannot reappear in Share_Folder products.

## Last Touched (2026-06-01)

- Files modified:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_weighted_spectral_breaks.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/batch_weighted_spectral_posteriors.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/run.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh`
  - `/Users/jkeohane/GRBs/CODEX_HANDOFF.md`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/CODEX_HANDOFF.md`
- Validation:
  - Python compile passed for the two spectral scripts and `jetfit/run.py`.
  - `bash -n` passed for `scripts/sync_results_to_drive.sh`.
  - 050525A dry-run of the batch spectral posterior script found exactly the intended run directory.
  - Existing 050525A `spectral_breaks_eats_weighted.csv` has finite positive values in all 220 rows for `nu_a`, `nu_m`, and `nu_c`.
- Outputs regenerated:
  - None in this touch; this was a workflow/code-path lock-in and validation pass.
- Remaining uncertainty:
  - Non-power-law Dylan bubble wrappers should not be treated as EATS-weighted until their `nu_*` helpers are upgraded to weighted details.

## Final-Final 050525A Minimized-Seed Run (2026-06-01)

- Purpose: first GRB in final-final structured-jet production campaign.
- Config builder:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_minimized_seeded_config.py`
- Seed source:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/050525A/minimized/minimized.json`
  - seed `nmap=-2057.097599019691`, `success=true`
- Generated config:
  - `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_finalfinal_minseed10pct_configs_active/050525A.toml`
- Seed audit:
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/finalfinal_minseed10pct/050525A_seed_audit.csv`
- Run card:
  - `/Users/jkeohane/GRBs/VegasJetFit/run_cards/050525A_structjet_finalfinal_minseed10pct_10temp_5000x5000_v1.md`
- Launcher:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/run_050525A_structjet_finalfinal_minseed10pct.sh`
- Result label:
  - `050525A_structjet_thetav_thetac_electronp_minseed10pct_finalfinal_10temp_5000x5000_v1`
- Seeding convention:
  - bounded priors are centered on minimized values;
  - `initial_sigma = 0.10 * (upper - lower)` in TOML fit-space;
  - Gaussian offset priors are left unchanged because the current sampler does not use `initial_guess` for plain Gaussian priors.
- Local Lyra validation:
  - `bash -n` passed for launcher;
  - Python compile passed for builder;
  - seeded audit has 11/11 bounded guesses in-bounds and 11/11 sigmas exactly 10% of prior width;
  - local 10-temperature, 100-walker preflight with 1 burn + 1 production passed;
  - valid walkers by temperature: `88,89,87,86,88,90,88,84,86,78`.
- Pauley_03 queue state:
  - synced config, launcher, and audit CSV to `pauley404-03`;
  - remote waiter script: `/Users/jkeohane/GRBs/VegasJetFit/scripts/wait_then_run_050525A_finalfinal_mcmc_p03.sh`;
  - remote waiter PID file: `/Users/jkeohane/GRBs/VegasJetFit/logs/050525A.finalfinal_minseed10pct.p03_wait.pid`;
  - latest known waiter PID: `11167`;
  - remote waiter log: `/Users/jkeohane/GRBs/VegasJetFit/logs/050525A.finalfinal_minseed10pct.p03_wait_20260601T220653Z.log`;
  - waiter is holding until the current Pauley_03 080319B finalprod slot clears.
- Important operating rule:
  - remote Pauley_03 launch sets `RUN_MINIMIZER=0`; only MCMC should run remotely.
  - Pull completed MCMC products back to Lyra for minimization and post-processing.

## 090618 eps_B Lower-Bound Continuation (2026-06-01)

- Latest 090618 shared source run is the finalprod structured-jet folder under `Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/090618`.
- Local source result copied/resumed from `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/090618_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1`.
- New continuation config/result label: `090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1`.
- Config changes:
  - `eps_b.prior.lower` changed from `-6.0` to `-10.0` in `/Users/jkeohane/GRBs/VegasJetFit/run_configs/090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1/model.toml`.
  - `run_length` changed from `5000` to `6000` in `/Users/jkeohane/GRBs/VegasJetFit/run_configs/090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1/mcmc_settings.toml`; resume checkpoint had `completed_iterations=5000`, so this requests exactly 1000 additional PT iterations.
- Active Lyra pipeline script: `/Users/jkeohane/GRBs/VegasJetFit/logs/090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1.direct_pipeline.sh`.
- Active launch uses conservative detached multiprocessing settings after 8-worker/caffeinate attempts exited during pool startup:
  - `--workers 2`
  - `--start-method spawn`
  - `JETFIT_POOL_EXECUTOR=process`
  - `JETFIT_POOL_PROBE=0`
- Logs:
  - fit: `/Users/jkeohane/GRBs/VegasJetFit/logs/090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1.log`
  - pipeline: `/Users/jkeohane/GRBs/VegasJetFit/logs/090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1.direct_pipeline.log`
  - PID file: `/Users/jkeohane/GRBs/VegasJetFit/logs/090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1.direct_pipeline.pid`
- On MCMC success the pipeline automatically runs minimization, standard postfit products, standard frequency diagnostics (`frequencies.pdf`), spectrum-timeseries regeneration, and syncs to the flattened 090618 exploratory Share_Folder destination. It should not regenerate retired `spectral_plot.pdf/.png` or `spectral_breaks_eats_weighted.csv`.
- Remaining uncertainty: active at handoff; confirm final `pt_resume_state.npz completed_iterations=6000`, minimizer success, and regenerated product timestamps after completion.

### Follow-up Launch Correction (2026-06-01 18:31 EDT)

- Active 090618 eps_B continuation is running in tmux session `grb090618_epsbmin10`.
- Earlier detached `nohup` PID files are not authoritative; Codex's command runner reaped those process groups after the tool command returned.
- Monitor with `/opt/homebrew/bin/tmux capture-pane -t grb090618_epsbmin10 -p | tail -80` and the fit log `/Users/jkeohane/GRBs/VegasJetFit/logs/090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1.log`.

## Structured-Jet Swept-Mass Overlay Update (2026-06-01)

- Canonical script: `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py`.
- The two-panel and single-overlay structured-jet swept-mass products now:
  - use blue for `theta=0` and red for `theta=theta_c`;
  - shade the radius-panel data range using all core-angle radius tracks (`0 <= theta <= theta_c`) mapped from the observed time window;
  - show best-fit crossing markers for `M_swept = M_ej/Gamma` and `M_swept = 10 M_ej/Gamma` at both `theta=0` and `theta=theta_c`;
  - show semi-transparent lighter marker clouds for all final cold-chain walkers underneath the main curves;
  - write `<event>_structjet_swept_mass_crossings.csv` for marker/audit values.
- Batch regeneration completed for 56 `PowerlawJetVegasDylanSpectrumModel` Share_Folder runs with zero failures.
- Batch artifacts:
  - log: `/Users/jkeohane/GRBs/VegasJetFit/logs/structjet_swept_mass_regen_20260601.log`
  - report: `/Users/jkeohane/GRBs/VegasJetFit/reports/structjet_swept_mass_regen_20260601.json`
- Validation summary: no missing/empty expected products; each crossing CSV has 404 data rows (`4` best-fit crossings plus `100 * 4` walker crossings).

## Last Touched (2026-06-02): Structured-Jet Swept-Mass Final Style

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` to keep the approved final overlay comment/logic aligned: red/blue only for non-overlap radial data spans, neutral grey for the mapped overlap.
- The approved overlay style is canonical: no top title, unboxed in-panel `GRB <event>` label in the upper-left, compact lower-right legends, blue `theta=0` plotted above red `theta=theta_c`, and tight bbox saving for LaTeX inclusion.
- Pipeline status: `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` already invokes this canonical script for `PowerlawJet` model names via `maybe_generate_structjet_swept_mass_overlay`; standard launch/sync pipelines that call `generate_postfit_products.py` therefore produce the final-style plot automatically.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py VegasJetFit/scripts/generate_postfit_products.py`
  - `/Users/jkeohane/GRBs/.venv/bin/python /tmp/regenerate_structjet_swept_mass_finalstyle.py`
  - `/Users/jkeohane/GRBs/.venv/bin/python /tmp/validate_structjet_swept_mass_finalstyle.py`
- Outputs regenerated: all structured-jet swept-mass diagnostics in 56 eligible Share_Folder `PowerlawJetVegasDylanSpectrumModel` run directories.
- Batch artifacts:
  - log: `/Users/jkeohane/GRBs/VegasJetFit/logs/structjet_swept_mass_finalstyle_20260602.log`
  - original batch report with stale filename-validator labels: `/Users/jkeohane/GRBs/VegasJetFit/reports/structjet_swept_mass_finalstyle_20260602.json`
  - corrected validation report: `/Users/jkeohane/GRBs/VegasJetFit/reports/structjet_swept_mass_finalstyle_20260602.validated.json`
- Validation: 56/56 runs regenerated with zero plotting-script failures; corrected validator found zero missing/empty products across 15 expected outputs per run; all crossing CSVs have 404 rows.
- Remaining uncertainty: none for this plotting-style/pipeline hook task.

## Last Touched (2026-06-05): Swept-Mass Crossing Marker Domain Fix

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py`.
- Crossing interpolation now returns `NaN` when `M_swept` is already above the target at the first sampled model point.  This avoids the old bug where an unbracketed crossing before the sampled/details domain was plotted as a fake marker at the left edge of the curve.
- Best-fit and walker crossing markers are now filtered against the final best-fit curve domain for the relevant panel (`t_obs_days` for time plots, `radius_cm` for radius plots).  Walker outliers no longer autoscale or populate off-domain panels.
- Standard pipeline remains unchanged because `generate_postfit_products.py` already calls this canonical swept-mass script for structured power-law jet runs.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py --run-dir /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A`
- Outputs regenerated for smoke test:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/mass_swept_ejecta_time.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/mass_swept_ejecta_radius.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/mass_swept_ejecta_two_panel.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/mass_swept_ejecta_crossings.csv`
- Validation:
  - compile passed;
  - synthetic crossing helper check confirmed unbracketed early crossings return `NaN` while bracketed crossings still interpolate;
  - visual smoke check of 140506A two-panel plot showed finite best-fit markers on actual curve crossings.
- Remaining uncertainty:
  - no full batch regeneration was run in this touch; future postfit/pipeline runs will pick up the patched crossing-domain behavior.

## Spread-Out Light-Curve Preview Products (2026-06-02)

- New preview script: `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py`.
- Purpose: make paper-style spread-out light curves before batch generation, with physical time axes but multiplicative per-band flux offsets for visual separation.
- Dylan-style local references found:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/events/spacing.json` for per-GRB band spread factors;
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/sandbox/light_curve.py` and `/Users/jkeohane/GRBs/VegasJetFit/scripts/events/publish.py` for the spread-out plot convention.
- Important performance note: do not use `LightCurvePlot.model_fluxes` naively for structured-jet posterior previews; it evaluates each band separately and is very slow.  `plot_spread_light_curves.py` instead evaluates all spectral band/time pairs for each parameter set in one paired-array VegasAfterglow `spectral_flux` call and reshapes by band.
- 050525A preview generated only; no batch run:
  - shaded posterior product: `/Users/jkeohane/Library/CloudStorage/GoogleDrive-jwkeohane@gmail.com/.shortcut-targets-by-id/1d7HnZ0yxuhMv2vPzbGBL9NNSDX9BjeDp/VegasGRBruns/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/050525A/050525A_spread_light_curve_shaded_posterior.pdf`
  - all-walker product: `/Users/jkeohane/Library/CloudStorage/GoogleDrive-jwkeohane@gmail.com/.shortcut-targets-by-id/1d7HnZ0yxuhMv2vPzbGBL9NNSDX9BjeDp/VegasGRBruns/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/050525A/050525A_spread_light_curve_100_walkers.pdf`
- Task note updated with links, implementation notes, and LaTeX captions:
  - `/Users/jkeohane/Library/CloudStorage/GoogleDrive-jwkeohane@gmail.com/.shortcut-targets-by-id/1d7HnZ0yxuhMv2vPzbGBL9NNSDX9BjeDp/VegasGRBruns/Things_to_do/2026_06_02_Make_additional_light_curves_spread_out_with_errors.md`
- Validation: Python compile passed; output PDFs/PNGs and metadata/spread-factor files are non-empty; markdown task-note links resolve; visual check passed after removing duplicate top-axis labels.
- Remaining review choices: legend is large for 050525A; y-axis label currently says `Scaled Flux Density [mJy]` and may be changed to `Flux Density x offset [mJy]` or `Arbitrarily Scaled Flux Density [mJy]` after review.

## Last Touched (2026-06-02): Spread-Out Light-Curve Preview Cleanup

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` after visual review of the 050525A drafts.
- Cleanup changes:
  - keep only the `LightCurvePlot` top seconds axis, avoiding duplicate top time labels;
  - move the in-panel `GRB <event>` label to the upper-right for negative-slope light curves;
  - move the legend outside the plotting axes to avoid data/model overlap;
  - include integrated-flux bands in the optimized model evaluator so XRT model curves are plotted.  XRT is stored as an integrated-flux datum in `LightCurvePlot.get_integrated_data()`, with bounds `7.25e16` to `2.42e18 Hz`; the script converts integrated flux to mJy flux density by dividing by `datum.int_range.width`, matching `LightCurvePlot.model_fluxes`.
- Regenerated 050525A preview products in `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/050525A`:
  - `050525A_spread_light_curve_shaded_posterior.pdf/.png`
  - `050525A_spread_light_curve_100_walkers.pdf/.png`
  - `050525A_spread_light_curve_spread_factors.csv`
  - `050525A_spread_light_curve_preview_metadata.json`
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_spread_light_curves.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u scripts/plot_spread_light_curves.py --run-dir <050525A-run-dir> --event 050525A --ncurves 100 --walker-limit 100 --ndata 80`
- Validation:
  - compile passed;
  - fast evaluator probe returned finite `xray` model fluxes;
  - visual PNG check confirmed single top seconds axis, upper-right GRB label, non-overlapping right-side legend, and visible XRT model curves/cloud.
- Remaining uncertainty:
  - this is still a preview-only 050525A product.  Before batch generation, decide whether the outside-right legend width is acceptable for paper layout or whether to split/compact the legend.

## Last Touched (2026-06-02): 050525A Walker Spread-Light-Curve Cleanup

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` again for the walker-specific draft.
- Confirmed `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/050525A/chain.npz` has shape `(5000, 100, 22)`, i.e. 100 final walkers.
- Changed `--walker-limit` default to `0`, meaning all final walkers; regenerated 050525A with `--walker-limit 0`.
- Moved the walker-count label to the lower-right (`All 100 final walkers`) so it does not visually duplicate the top seconds-axis title.
- Output regenerated:
  - `050525A_spread_light_curve_100_walkers.pdf`
  - `050525A_spread_light_curve_100_walkers.png`
- Validation: compile passed; visual check confirmed single top axis label, upper-right GRB label, visible XRT cloud, and all 100 walkers used.

## Last Touched (2026-06-02): Spread Light Curves Added to Standard Postfit Products

- Promoted `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` from preview-only use into the standard data-product pipeline.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py`:
  - added `--skip-spread-light-curves` escape hatch;
  - added `maybe_generate_spread_light_curves(results, event)`;
  - standard postfit generation now runs the spread-light-curve script with `--ncurves 100 --walker-limit 0 --ndata 80`, producing the shaded posterior and all-final-walker products.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh`:
  - missing `<event>_spread_light_curve_shaded_posterior.pdf` or `<event>_spread_light_curve_100_walkers.pdf` now triggers `generate_postfit_products.py` before syncing, matching the existing mass/comparison backfill behavior.
- Regenerated/validated through the real postfit hook for 050525A:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/050525A/050525A_spread_light_curve_shaded_posterior.pdf/.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/050525A/050525A_spread_light_curve_100_walkers.pdf/.png`
  - spread factors CSV and metadata JSON were refreshed as well.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/generate_postfit_products.py scripts/plot_spread_light_curves.py`
  - `bash -n scripts/sync_results_to_drive.sh scripts/run_fit_and_sync.sh`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u scripts/generate_postfit_products.py --results <050525A-run-dir> --event 050525A --skip-density-replot`
- Validation:
  - compile and shell syntax checks passed;
  - postfit validation printed both `spread_light_curves_ok` and `postfit_products_ok`;
  - output timestamps confirm the spread posterior and all-walker products were regenerated by the postfit path.
- Remaining uncertainty:
  - Git status/commit could not be checked because `/usr/bin/git` is currently failing during the command-line-tools/Xcode reinstall (`MacOSX26.4.sdk` missing). Re-run git status/commit after the toolchain reinstall finishes.

## Last Touched (2026-06-02): Completed Finalprod Runs Postprocessed to Share_Folder

- Processed completed local/Lyra finalprod structured-jet 5000x5000 runs and refreshed Share_Folder standard products for:
  - `050525A`
  - `050922C`
  - `090424`
  - `090618` original finalprod run, not the active eps_B continuation
  - `111228A`
  - `130612A`
  - `131030A`
- Excluded `050525A_structjet_thetav_thetac_electronp_minseed10pct_finalfinal_10temp_5000x5000_v1` because it has no `chain.npz`/`best_fit.json`; Pauley_03 waiter had not started it yet.
- For each processed event:
  - local `chain.npz` and `best_fit.json` were present;
  - local `minimized/minimized.json` was already present, so no new walker minimization was needed;
  - local result directory was rsynced to the standard Share_Folder campaign event directory;
  - `generate_postfit_products.py --skip-density-replot` was run on the Share_Folder event directory;
  - frequency diagnostics are now standardized on `frequencies.pdf`; retired `spectral_plot.pdf/.png` and `spectral_breaks_eats_weighted.csv` should not be regenerated;
  - `generate_spectrum_timeseries.py --results <event-dir>` regenerated `spectrum_timeseries.pdf`.
- Products validated present/non-empty in each Share_Folder event directory include:
  - `chain.npz`, `best_fit.json`, `minimized/minimized.json`, `light_curve.pdf`
  - `mass_profile.pdf`, `ampy_comparison.pdf`
  - `frequencies.pdf` (retired `spectral_plot.pdf/.png` and `spectral_breaks_eats_weighted.csv` are intentionally excluded)
  - `spectrum_timeseries.pdf`
  - `<event>_spread_light_curve_shaded_posterior.pdf/.png`
  - `<event>_spread_light_curve_100_walkers.pdf/.png`
  - `<event>_spread_light_curve_spread_factors.csv`
  - `<event>_spread_light_curve_preview_metadata.json`
  - `<event>_structjet_swept_mass_single_overlay_two_panel.pdf`
  - `<event>_structjet_swept_mass_crossings.csv`
- Share campaign directory:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1`
- Batch artifacts:
  - log: `/Users/jkeohane/GRBs/VegasJetFit/logs/completed_finalprod_postprocess_to_share_20260602T230541.log`
  - report: `/Users/jkeohane/GRBs/VegasJetFit/reports/completed_finalprod_postprocess_to_share_20260602T230541.json`
- Operational note:
  - an initial full-standard pass without `--skip-density-replot` was interrupted because density-profile regeneration for `050525A` consumed a long CPU-bound tail after core products had already regenerated. The completed batch therefore skipped density replotting; it did not delete existing density diagnostics, but density profile PDFs were not part of the final validation list.

## Last Touched (2026-06-03): Spread-Light-Curve Task Report Moved to Completed

- Converted `/Users/jkeohane/GRBs/Share_Folder/Things_to_do/2026_06_02_Make_additional_light_curves_spread_out_with_errors.md` into a completed report and moved it to:
  - `/Users/jkeohane/GRBs/Share_Folder/Things_to_do/completed/2026_06_02_Make_additional_light_curves_spread_out_with_errors.md`
- The completed report includes:
  - summary of the approved spread-light-curve plot style;
  - pipeline hook locations for `plot_spread_light_curves.py`, `generate_postfit_products.py`, and `sync_results_to_drive.sh`;
  - per-GRB links for the seven processed finalprod Share_Folder events;
  - validation report/log links;
  - draft LaTeX captions for future figure use.
- Remaining notes captured in the report:
  - `140506A` had finished overnight but had not yet completed Share_Folder postfit/product generation at the time of the report;
  - the `090618` eps_B lower-bound continuation had finished MCMC/minimization but was still running postfit at the time of the report.

## Last Touched (2026-06-03): Organized New Plot Products in Share_Folder Campaigns

- Cleaned up the new spread-light-curve and swept-mass plot products in Share_Folder campaign directories so final products live inside each GRB subfolder, not at campaign root.
- Campaigns checked/cleaned:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260601__090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260513__anshstyle_structjet_thetav_thetac_pthawed_v2`
- Final products left in GRB folders use short event-prefixed filenames, e.g.:
  - `<event>_spread_light_curve_shaded_posterior.pdf/.png`
  - `<event>_spread_light_curve_100_walkers.pdf/.png`
  - `<event>_structjet_swept_mass_single_overlay_two_panel.pdf/.png`
  - `<event>_structjet_swept_mass_crossings.csv`
- For the `090618` eps_B continuation, copied long run-label swept-mass final products to canonical short names inside the `090618/` folder, then moved long-run-label duplicates to trash.
- Moved 140 intermediate/draft generated figure files into campaign-level trash folders with path context preserved:
  - `trash/20260603_intermediate_draft_figures/`
  - each trash folder includes a `README.md` manifest.
- Validation: no loose `*spread_light_curve*` or `*structjet_swept_mass*` files remain at the checked campaign roots; final products are present inside the relevant GRB subfolders.

## Last Touched (2026-06-03): Copied 090618 eps_B Restart Products into Main 090618 Share Folder

- User needed the `090618` restart products in the same Share_Folder GRB product folder as the original `090618` finalprod products.
- Copied products from:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260601__090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1/090618`
- Into:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260521__050525A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1/090618`
- Copied files use prefix `090618_epsbmin10_` to avoid overwriting the original finalprod `090618` products.
- Added README pointer:
  - `090618_epsbmin10_restart_PRODUCTS_README.md`
- Copied 39 files including spectral plot, spectrum timeseries, spread-light-curve products, swept-mass final plot/crossings, minimized JSON/walkers, chain/checkpoint, model/obs/settings, profiles, and sync logs.
- Validation: key prefixed products exist and are non-empty in the main `090618` Share_Folder product folder.

## Last Touched (2026-06-04): Made Share_Folder Report Links Portable

- Updated completed task reports in `/Users/jkeohane/GRBs/Share_Folder/Things_to_do/completed/` so Share_Folder links are relative to the report location, not machine-specific absolute paths:
  - `2026_06_01_Make_new_swept_up_mass_plots.md`
  - `2026_06_02_Make_additional_light_curves_spread_out_with_errors.md`
- Link convention from `Things_to_do/completed/*.md` to the Share root is `../../`, e.g. `../../Fits/...`.
- Updated swept-mass report links for draft/intermediate products moved into campaign trash so historical links still resolve through `../../Fits/.../trash/20260603_intermediate_draft_figures/...`.
- Normalized remaining local repo references in those reports from `/Users/jkeohane/GRBs/...` to repo-relative notes or `$GRBS_ROOT` command placeholders.
- Validation: `rg` found no `/Users/jkeohane` paths in `Share_Folder/Things_to_do/*.md`; all relative Share links in both completed reports resolved locally.

## Last Touched (2026-06-04): Reorganized Share_Folder/Fits by Run Maturity

- Followed `/Users/jkeohane/GRBs/Share_Folder/Things_to_do/reorganize_fits_todo.md` to reorganize `/Users/jkeohane/GRBs/Share_Folder/Fits` by maturity/intended use.
- Saved before-tree snapshots:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits_tree_before_reorg.txt`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits_tree_before_reorg_deep.txt`
- Created target structure:
  - `Fits/production_runs/{unseeded_runs,final_seeded_runs,exploratory_runs,trash}`
  - `Fits/pre_production_runs/{unseeded_runs,seeded_runs,exploratory_runs,trash}`
  - `Fits/shorter_diagnostic_runs/{seeded_runs,unseeded_runs,prior_tests,code_tests,trash}`
  - `Fits/trash`
- Moved/renamed 31 campaign directories as whole directories; scientific products, chains, configs, logs, and internal `minimized/` folders stayed with their campaigns.
- Deleted 13 `.DS_Store` files per todo instructions.
- Moved 7 old taxonomy README/FOLDER_DATE_NOTE files into `Fits/trash/old_taxonomy_notes_20260604/` with path context.
- Removed 33 empty old taxonomy directories after inspection.
- Wrote/updated:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/README.md`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/RENAMED_CAMPAIGNS.md`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/REORG_REPORT_20260604.md`
  - category README files under `production_runs/`, `pre_production_runs/`, `shorter_diagnostic_runs/`, and `trash/`.
- Saved after-tree snapshots:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits_tree_after_reorg.txt`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits_tree_after_reorg_deep.txt`
- Validation passed: 31 mapping rows with 0 missing destinations; no old `jet_tophat`/`jet_structured_powerlaw` taxonomy paths remain outside trash; required target folders exist; no `.DS_Store` files remain outside trash.
- Current primary production campaign is now under:
  - `Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/`
- The 090618 eps_B continuation is now under:
  - `Fits/production_runs/exploratory_runs/26_06_01__structured_jet__viewing_core_structure_thawed__power_law_csm__090618_eps_b_min_minus_10__resume_1000/`

## Last Touched (2026-06-04): Consolidated Fits Reorg Text Artifacts

- Moved Codex/provenance text artifacts out of the human-facing `Fits/` folder view into:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/_codex_agent_notes/2026_06_04_reorg/`
- Moved files include:
  - `RENAMED_CAMPAIGNS.md`
  - `REORG_REPORT_20260604.md`
  - `Fits_tree_before_reorg.txt`
  - `Fits_tree_before_reorg_deep.txt`
  - `Fits_tree_after_reorg.txt`
  - `Fits_tree_after_reorg_deep.txt`
  - category helper README files created during the reorg.
- Left only the human-facing `Fits/README.md` plus pre-existing `run_registry.csv` as top-level text/csv files in `Fits/`.
- Updated `Fits/README.md` to point future agents to `_codex_agent_notes/2026_06_04_reorg/` for old-to-new mappings and tree snapshots.

## Last Touched (2026-06-04): Spread-Out Light-Curve Filename Cleanup

- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` so future post-fit generation writes kept spread-out light-curve products without event prefixes:
  - `light_curve_spread_out_shaded_posterior.pdf/.png`
  - `light_curve_spread_out_100_walkers.pdf/.png`
  - `light_curve_spread_out_factors.csv`
  - `light_curve_spread_out_spread_metadata.json`
- Renamed existing kept Share_Folder spread-out products in the flattened production campaign and the 090618 epsilon_B continuation to this convention; did not inspect or modify files inside `trash` except when a duplicate destination would have required trashing, which did not occur.
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot_spread_light_curves.py` passed.
  - Strict search found no old event-prefixed `*_spread_light_curve_*` product names outside `trash` under `Share_Folder/Fits/production_runs`.
  - `60` kept spread-out products now use `light_curve_spread_out*` names across 10 run directories.
- Remaining uncertainty: `plot_spread_light_curves.py` is untracked in the current `VegasJetFit` Git status; stage/commit deliberately if this convention should be versioned.

## Last Touched (2026-06-04): Retired Spectral Plot Products

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_weighted_spectral_breaks.py` and `/Users/jkeohane/GRBs/VegasJetFit/scripts/batch_weighted_spectral_posteriors.py` so they skip by default and require `--write-retired-products` before writing `spectral_plot.pdf`, `spectral_plot.png`, or `spectral_breaks_eats_weighted.csv`.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/jetfit/run.py` to keep `frequencies.pdf` as the standard frequency diagnostic and not alias it to `spectral_plot.pdf`.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` to exclude/remove retired spectral filenames during sync, preventing stale local copies from reappearing in Share_Folder products.
- Moved visible retired spectral products under `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs` into per-run `trash/20260604_retired_spectral_plot_products/` folders. Do not use those trash contents as current products.
- Added missing `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/exploratory_runs/26_06_01__structured_jet__viewing_core_structure_thawed__power_law_csm__090618_eps_b_min_minus_10__resume_1000/090618/frequencies.pdf` using a lean best-fit frequency diagnostic.
- Validation commands run:
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot_weighted_spectral_breaks.py VegasJetFit/scripts/batch_weighted_spectral_posteriors.py VegasJetFit/jetfit/run.py VegasJetFit/scripts/generate_postfit_products.py`
  - `bash -n VegasJetFit/scripts/sync_results_to_drive.sh`
  - default invocations of both retired spectral scripts printed `SKIP` and wrote no retired products.
  - Share_Folder scan found zero visible `spectral_plot.pdf`, `spectral_plot.png`, or `spectral_breaks_eats_weighted.csv` outside `trash`, and found `frequencies.pdf` for the main production campaign plus the 090618 continuation.
- Remaining uncertainty: no broad cleanup was done across all historical local `VegasJetFit/jetfit/results` folders; sync now guards against stale local retired files reaching Share_Folder.

## Last Touched (2026-06-04): Swept-Mass Product Renaming

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` so standard structured-jet swept-mass products are now:
  - `mass_swept_ejecta_time.pdf/.png`
  - `mass_swept_ejecta_radius.pdf/.png`
  - `mass_swept_ejecta_two_panel.pdf/.png`
  - `mass_swept_ejecta_crossings.csv`
- The script no longer writes the old intermediate plot families:
  - `<event>_structjet_swept_mass_diagnostics_vs_*.*`
  - `<event>_structjet_swept_mass_local_vs_coreavg_per_sr_vs_*.*`
  - `<event>_structjet_swept_mass_single_overlay_per_sr_vs_*.*`
  - `<event>_structjet_swept_mass_single_overlay_two_panel.*`
  - `<event>_structjet_swept_mass_crossings.csv`
- Added a retirement helper in the plotting script that moves those old long-name files into `trash/20260604_retired_swept_mass_products/` before writing the clean names.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so missing clean swept-mass files trigger `generate_postfit_products.py`, and sync excludes/removes old long-name swept-mass files from destinations.
- Regenerated clean swept-mass products for 10 current production/continuation `PowerlawJetVegasDylanSpectrumModel` run folders under `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs`.
- Validation:
  - Python compile passed for `plot_structjet_swept_mass_diagnostics.py` and `generate_postfit_products.py`.
  - `bash -n` passed for `sync_results_to_drive.sh`.
  - Production scan found 10 eligible run folders, zero missing clean products, and zero visible old `*structjet_swept_mass*` files outside `trash`.
- Remaining uncertainty: historical report/link-index files may still mention old filenames for older archived campaigns; live production folders and active pipeline now use the clean names.

## Last Touched (2026-06-04): Minimized Light-Curve Overlays

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so standard `light_curve.pdf/.png` products are regenerated from postfit parameters, preferring `minimized/minimized.json` over `best_fit.json`.
- Superseded on 2026-06-05: standard `light_curve.pdf/.png` products should not draw all final cold-chain walkers.  They should show only the postfit/minimized model curves plus observations.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so a missing `light_curve.png` triggers postfit regeneration, catching folders whose old `light_curve.pdf` existed but was not made from the minimized overlay.
- Regenerated `light_curve.pdf` and `light_curve.png` for 10 current production/continuation `PowerlawJetVegasDylanSpectrumModel` folders under `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs`.
- Validation:
  - Python compile passed for `generate_postfit_products.py` and `plot_spread_light_curves.py`.
  - `bash -n` passed for `sync_results_to_drive.sh`.
  - Production scan found 10 eligible folders, zero missing `light_curve.pdf/.png`, and 20 visible standard light-curve files.
- Remaining uncertainty: no visual PDF inspection was performed in this touch; validation confirmed products exist and were regenerated without script errors.

## Last Touched (2026-06-05): Standard vs Spread-Out Light-Curve Walker Convention

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so the standard `light_curve.pdf/.png` postfit regeneration uses only the postfit parameters (`minimized/minimized.json` when present, otherwise `best_fit.json`).  The normal light curve no longer plots all 100 final walkers.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` so only the spread-out walker product keeps all final walkers, with lower transparency: `alpha=0.045` for non-XRT bands and `alpha=0.08` for XRT.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/generate_postfit_products.py VegasJetFit/scripts/plot_spread_light_curves.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/generate_postfit_products.py --results /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --skip-density-replot`
- Outputs regenerated for smoke test:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_spread_out_100_walkers.pdf/.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_spread_out_shaded_posterior.pdf/.png`
- Validation:
  - compile passed;
  - full postfit hook completed for 140506A with `source=minimized/minimized.json`;
  - visual check confirmed standard `light_curve.png` has no walker cloud and spread-out `light_curve_spread_out_100_walkers.png` keeps all 100 walkers with lighter transparency.
- Remaining uncertainty:
  - only 140506A was regenerated in this touch.  Future postfit/sync runs will apply the corrected convention to other folders, or batch regeneration can refresh all existing production products if requested.

## Last Touched (2026-06-05): Standard Light-Curve Dashed Postfit Lines

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so standard `light_curve.pdf/.png` postfit model curves are dashed (`ls="--"`) rather than solid.  This makes the data points easier to see.  Spread-out light-curve plots were not changed in this touch.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/generate_postfit_products.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/generate_postfit_products.py --results /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --skip-density-replot --skip-spread-light-curves`
- Outputs regenerated for smoke test:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.png`
- Validation:
  - compile passed;
  - postfit hook completed with `source=minimized/minimized.json`;
  - visual check confirmed dashed model lines and no walker cloud on the standard 140506A light curve.
- Remaining uncertainty:
  - only 140506A was regenerated in this touch; future postfit/sync runs will apply dashed standard curves elsewhere.

## Last Touched (2026-06-05): Publication Light-Curve Layout and Two-Panel Product

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so standard `light_curve.pdf/.png` products use no top title and instead place `GRB <event>` as a large in-panel label at upper right.  The standard plot still uses dashed postfit/minimized model curves and no walker cloud.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` to write a publication candidate two-panel product:
  - `light_curve_two_panel.pdf`
  - `light_curve_two_panel.png`
- Two-panel convention:
  - top panel: regular physical-flux light curve with dashed postfit curves and in-panel GRB label;
  - bottom panel: spread-out all-final-walker light curve with lighter walker transparency and bold postfit curves;
  - one outside legend on the bottom panel;
  - tight bounding-box saves for LaTeX inclusion.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so a missing `light_curve_two_panel.pdf` triggers standard postfit regeneration.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/generate_postfit_products.py VegasJetFit/scripts/plot_spread_light_curves.py`
  - `bash -n VegasJetFit/scripts/sync_results_to_drive.sh`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/generate_postfit_products.py --results /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --skip-density-replot`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/plot_spread_light_curves.py --run-dir /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --ncurves 100 --walker-limit 0 --ndata 80`
- Outputs regenerated for smoke test:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_two_panel.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_two_panel.png`
- Validation:
  - compile and shell syntax checks passed;
  - full postfit hook completed with `source=minimized/minimized.json`;
  - visual check confirmed the single regular light curve has in-panel GRB label/no title;
  - visual check confirmed the two-panel product combines the regular dashed plot with the spread-out all-walker plot and has a tight publication-style bounding box.
- Remaining uncertainty:
  - only 140506A was regenerated in this touch; future postfit/sync runs will apply the new publication layout and two-panel product elsewhere.

## Last Touched (2026-06-06): Light-Curve Data-On-Top and Dashed Spread-Out Best Curves

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` so the minimized/postfit curve in spread-out light-curve products is dashed, matching the regular `light_curve.pdf/.png` convention.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` so light-curve observations are explicitly drawn above model layers:
  - included data/error bars use `zorder=20`;
  - excluded grey/open data use `zorder=18`.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot_spread_light_curves.py VegasJetFit/scripts/plot/visualize.py VegasJetFit/scripts/generate_postfit_products.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/generate_postfit_products.py --results /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --skip-density-replot --skip-spread-light-curves`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/plot_spread_light_curves.py --run-dir /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --ncurves 100 --walker-limit 0 --ndata 80`
- Outputs regenerated for smoke test:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_spread_out_100_walkers.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_two_panel.png`
- Validation:
  - compile passed;
  - both regeneration commands completed cleanly;
  - visual check confirmed spread-out and two-panel products use dashed minimized curves, with data/error bars visible above model/walker layers.
- Remaining uncertainty:
  - only 140506A was regenerated in this touch; future postfit/sync runs will apply this convention elsewhere.

## Last Touched (2026-06-06): Thinner Dashed Light-Curve Best-Fit Lines

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so standard `light_curve.pdf/.png` dashed postfit curves are thinner: non-XRT `lw=1.45`, XRT `lw=1.8`.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` so spread-out and two-panel dashed postfit curves are thinner: default non-XRT `lw=1.25`, XRT at least `lw=1.6`; regular panel in the two-panel product uses non-XRT `lw=1.45`, XRT `lw=1.8`.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/generate_postfit_products.py VegasJetFit/scripts/plot_spread_light_curves.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/generate_postfit_products.py --results /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --skip-density-replot --skip-spread-light-curves`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/plot_spread_light_curves.py --run-dir /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --ncurves 100 --walker-limit 0 --ndata 80`
- Outputs regenerated for smoke test:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_spread_out_100_walkers.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_two_panel.png`
- Validation:
  - compile passed;
  - both regeneration commands completed cleanly;
  - visual check confirmed the thinner dashed curves remain readable and reduce overlap with data.
- Remaining uncertainty:
  - only 140506A was regenerated in this touch; future postfit/sync runs will apply thinner dashed curves elsewhere.

## Last Touched (2026-06-07): Two-Panel Light-Curve Scaling Labels

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` so `light_curve_two_panel.pdf/.png` explicitly labels the panel scaling:
  - top panel: `unscaled flux density`;
  - bottom panel: `band-scaled flux density`.
- Purpose: make clear that the top panel uses physical/unscaled fluxes even though the shared legend on the bottom panel lists spread factors.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot_spread_light_curves.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u VegasJetFit/scripts/plot_spread_light_curves.py --run-dir /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A --event 140506A --ncurves 100 --walker-limit 0 --ndata 80`
- Outputs regenerated for smoke test:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_two_panel.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/140506A/light_curve_two_panel.pdf`
- Validation:
  - compile passed;
  - regeneration completed cleanly;
  - visual check confirmed the top/bottom scaling distinction is clear without adding a second full legend.
- Remaining uncertainty:
  - only 140506A was regenerated in this touch; future postfit/sync runs will apply the scaling labels elsewhere.

## Last Touched: 2026-06-04 SBPL Wide Top-Hat Dylan-Thesis Seeded Campaign

- Added `build_sbpl_tophat_dylanthesis_seeded_configs.py` to generate wide top-hat SBPL configs from `sbpl_unseeded_tophat_configs_active/` with Dylan thesis median `initial_guess` values.
- Added `run_sbpl_tophat_dylanthesis_seeded_queue.sh` for staged launches of `080319B` and `080413B`; default run tag is `sbpl_tophat_theta1p0_dylanthesis_seeded_2000x2000_v1`.
- Builder expands any prior bound needed to include the exact thesis median seed; this happened for `080413B eps_e` upper bound (`-0.3` -> `-0.25`).
- Validation: shell syntax, Python compile, and TOML parse passed for the generated active configs.

## Last Touched: 2026-06-04 SBPL Top-Hat Minimized-Seeded Queue

- Dylan thesis two-pass correction: do not treat thesis posterior medians as the second-pass seed source. Use first-pass broad-run best-fit/minimized values and `initial_sigma = 0.10 * (upper-lower)` in fit-space.
- Added `/Users/jkeohane/GRBs/VegasJetFit/scripts/run_sbpl_tophat_minseed10pct_queue.sh` for `080319B` and `080413B`; default run tag is `sbpl_tophat_theta1p0_minseed10pct_2000x2000_v1`.
- Guarded `/Users/jkeohane/GRBs/VegasJetFit/scripts/run_sbpl_tophat_dylanthesis_seeded_queue.sh`; it now exits by default because it is a superseded median-seeded diagnostic, not Dylan's thesis two-pass method.
- Validation: `bash -n` passed for both scripts; default invocation of the superseded median queue exits with code 2 and a clear warning.

## Last Touched (2026-06-08): Thesis-Style Frequency Diagnostic Layout

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` so the standard `frequencies.pdf` diagnostic uses a compact break-frequency legend only:
  - `self-abs. ($\nu_a$)`;
  - `injection ($\nu_m$)`;
  - `cooling ($\nu_c$)`.
- Observational band/frequency markers remain on the top panel for context but no longer appear in the legend.
- The critical-frequency panel is larger than the spectral-index panel via subplot height ratios `[3.2, 1.0]`.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py`
  - one-off canonical `plot_frequencies(...)` regeneration from `chain.npz`, `obs.csv`, and `model.toml` for the 140506A empirical-bubble seeded run.
  - `pdftoppm -png -singlefile -r 160 frequencies.pdf /tmp/140506A_frequencies_preview_final`
- Output regenerated:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`
- Validation:
  - Python compile passed.
  - PDF rendered to `/tmp/140506A_frequencies_preview_final.png` and visually checked: the large band-color legend is gone, the break-frequency legend is compact, and the top panel dominates the layout.
- Remaining uncertainty:
  - Only this 140506A preview product was regenerated in this touch; future pipeline/postfit runs will use the new shared `FrequencyPlotter` style automatically.

## Last Touched (2026-06-08): Frequency Plot Header Legend and GRB Panel Label

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` frequency diagnostics again so `frequencies.pdf` has:
  - an in-panel upper-left `GRB <event>` label inferred from the result directory name;
  - a single-row figure-level break-frequency legend above the top panel, outside the data region;
  - compact legend entries only for `self-abs. ($\nu_a$)`, `injection ($\nu_m$)`, and `cooling ($\nu_c$)`.
- Commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py`
  - one-off canonical `plot_frequencies(...)` regeneration for the 140506A empirical-bubble seeded run.
  - `pdftoppm -png -singlefile -r 160 frequencies.pdf /tmp/140506A_frequencies_preview_top_legend`
- Output regenerated:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`
- Validation:
  - Python compile passed.
  - PDF rendered to `/tmp/140506A_frequencies_preview_top_legend.png` and visually checked: GRB label is visible in the panel and the break-frequency legend is one row above the plot, not covering model/data curves.

## Last Touched (2026-06-08): Frequency Plot Tighter Vertical Layout

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` to reduce excess whitespace in `frequencies.pdf` after moving the break-frequency legend above the axes:
  - title y changed to `0.985`;
  - reserved top layout changed to `0.90`;
  - figure-level legend remains one row at `bbox_to_anchor=(0.5, 0.945)`.
- Regenerated the 140506A empirical-bubble seeded preview product:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py` passed.
  - Rendered preview to `/tmp/140506A_frequencies_preview_tighter.png`; visual check confirmed the plot panels are larger and the legend stays outside the data region.

## Last Touched (2026-06-08): Frequency Plot Top Seconds Axis

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` so `frequencies.pdf` now has a top secondary x-axis on the critical-frequency panel:
  - bottom x-axis: `Time Since Trigger [days]`;
  - top x-axis: `Time Since Trigger [seconds]` via `days_to_sec/sec_to_days`.
- Regenerated:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py` passed.
  - Rendered preview to `/tmp/140506A_frequencies_preview_seconds_axis.png`; visual check confirmed the seconds axis appears above the top panel while the one-line break legend remains outside the data region.

## Last Touched (2026-06-08): Frequency Plot Axis Label Font Size

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` so all `frequencies.pdf` axis labels use the same 10 pt font size as the top seconds-axis label:
  - `Frequency [Hz]`;
  - `Spectral Index`;
  - `Time Since Trigger [days]`;
  - `Time Since Trigger [seconds]`.
- Regenerated:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py` passed.
  - Rendered preview to `/tmp/140506A_frequencies_preview_label_fonts.png`; visual check confirmed consistent smaller axis-label styling.

## Last Touched (2026-06-08): Frequency Panel Height Ratio

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` so `frequencies.pdf` gives more vertical space to the critical-frequency panel:
  - subplot height ratios changed from `[3.2, 1.0]` to `[4.2, 0.85]`.
- Regenerated:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py` passed.
  - Rendered preview to `/tmp/140506A_frequencies_preview_taller_frequency.png`; visual check confirmed the frequency panel is taller and the spectral-index panel remains readable.

## Last Touched (2026-06-08): Frequency Plot Tight Bounding Box

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` so `frequencies.pdf` uses a frequency-specific tight save path instead of the generic `save_plot_unique`:
  - `bbox_inches='tight'`;
  - `pad_inches=0.045`.
- The frequency title and break-frequency legend were moved slightly down:
  - title y: `0.965`;
  - figure legend bbox y: `0.925`.
- Regenerated:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py` passed.
  - `pdfinfo` reports one page with tight page size `560.543 x 525.68 pts` for the 140506A preview.
  - Rendered preview to `/tmp/140506A_frequencies_preview_tight_bbox.png`; visual check confirmed the title/legend are not clipped and outer whitespace is reduced.

## Last Touched (2026-06-08): Frequency Plot Added to Standard Postfit Pipeline

- The new `frequencies.pdf` style lives in the shared `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` `FrequencyPlotter`, so normal MCMC-success plots from `/Users/jkeohane/GRBs/VegasJetFit/jetfit/run.py` automatically use it.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so standard postfit/product refreshes also regenerate `frequencies.pdf` by default:
  - loads cold-chain samples from `chain.npz` (`lnprob` or `log_prob` supported);
  - handles older 4-D parallel-tempered chain arrays by selecting temperature 0;
  - deletes stale `frequencies*.pdf` in the run directory before writing the canonical `frequencies.pdf`;
  - passes minimized/postfit parameters as the bold break-frequency curves when available;
  - added `--skip-frequency-plot` as an escape hatch.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so missing `frequencies.pdf` triggers the standard postfit regeneration/backfill before syncing.
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/plot/visualize.py VegasJetFit/scripts/generate_postfit_products.py` passed.
  - `bash -n VegasJetFit/scripts/sync_results_to_drive.sh` passed.
  - Running `generate_postfit_products.py` on the 140506A empirical-bubble seeded preview printed `frequencies_ok` and regenerated the new-style `frequencies.pdf`; that older empirical-bubble run then hit the pre-existing analytic mass-profile limitation (`Cannot infer CSM density profile from model parameters`) after the frequency product was already written.
- Regenerated frequency product:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/frequencies.pdf`

## Last Touched (2026-06-08): AMPy Comparison Quick-Reference Plot

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so `ampy_comparison.pdf` is now the quick-reference difference-over-average plot, not the old log-ratio plot.
- Metric now plotted and written to `ampy_comparison.csv`:
  - `difference_over_average = 2 * (x_this - x_Dylan) / (|x_this| + |x_Dylan|)`.
- Removed log-ratio clutter from regenerated products:
  - no `ratio_to_dylan` or `log10_ratio_to_dylan` columns in `ampy_comparison.csv`;
  - old sidecars `ampy_comparison_symmetric.*` and `ampy_comparison_log_ratio.*` are deleted when this product regenerates.
- Added quick-reference annotation logic:
  - loads Dylan/reference nmap and data-row counts from local audit tables under `VegasJetFit/analysis/nmap_dataset_check*_20260428/`;
  - counts included rows in the current run `obs.csv`;
  - if row counts match, annotates this nmap, Dylan nmap, and `Delta(this-Dylan)`;
  - if row counts differ, annotates the data-count mismatch instead and does not present nmap as apples-to-apples.
- Regenerated preview product:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/ampy_comparison.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/ampy_comparison.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/ampy_comparison.csv`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/generate_postfit_products.py VegasJetFit/scripts/plot/visualize.py` passed.
  - `bash -n VegasJetFit/scripts/sync_results_to_drive.sh` passed.
  - Rendered preview to `/tmp/140506A_ampy_comparison_preview.png`; visual check confirmed the plot uses only the difference-over-average metric and flags `DATA COUNT MISMATCH: this=207, Dylan=695` for that preview run.

## Last Touched (2026-06-08): AMPy Comparison Final Tight Layout

- Finalized `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` AMPy comparison plot wording/layout:
  - data-count mismatch text now says `nmap comparison is apples-to-oranges`;
  - removed the long `apply_plot_run_label` footer that expanded the saved bounding box;
  - moved compact source/nmap/model context into a small subtitle above the axes;
  - saved `ampy_comparison.pdf/.png` with `bbox_inches='tight'` and `pad_inches=0.025`.
- Regenerated preview:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/ampy_comparison.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/ampy_comparison.png`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile VegasJetFit/scripts/generate_postfit_products.py` passed.
  - `pdfinfo` reports tight one-page preview size `632.944 x 383.971 pts`.
  - Rendered preview to `/tmp/140506A_ampy_comparison_tight_preview.png`; visual check confirmed the apples-to-oranges annotation and tight export.

## Last Touched (2026-06-08): Reduced Core/CSM Corner Plots

- Added standard reduced corner products in `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py`:
  - `corner_core.pdf`: requested core physical/microphysical fitted parameters `E52`, `lf0`, `n017`, `eps_e`, `eps_b` when present in the fit;
  - `corner_csm.pdf`: requested spectral/environment/geometry fitted parameters `p`, `k`, `ebv_source_frame`, `theta_c`, `theta_v` when present in the fit.
- The reduced corner helper only plots parameters that are actually in `Parameters.from_toml(...).fitting`; fixed or absent parameters are skipped, and a reduced plot is skipped if fewer than two requested fitted parameters are available.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so standard postfit refreshes regenerate `corner_core.pdf` and `corner_csm.pdf` by default from `chain.npz` plus `model.toml`; added `--skip-reduced-corners` for one-off bypasses.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so missing `corner_core.pdf` or `corner_csm.pdf` triggers postfit regeneration/backfill before syncing.
- Regenerated smoke-test products for 140506A:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/corner_core.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/pre_production_runs/seeded_runs/26_04_18__top_hat__theta_c_1_rad_on_axis__empirical_wind_bubble_csm__seeded_from_simple_bubble__pre_production/140506A/corner_csm.pdf`
- Smoke-test included parameters for that run:
  - `corner_core`: `E52`, `lf0`, `eps_e`, `eps_b`; `n017` was absent/fixed for this empirical-bubble fit.
  - `corner_csm`: `p`, `ebv_source_frame`; `k`, `theta_c`, and `theta_v` were absent/fixed for this top-hat bubble fit.
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile /Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py /Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` passed.
  - `bash -n /Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` passed.
  - Rendered previews to `/tmp/140506A_corner_core_preview.png` and `/tmp/140506A_corner_csm_preview.png`; visual check confirmed reduced corner layout and labels.
- Remaining uncertainty: model families that do not fit at least two requested parameters in a group will not emit that reduced corner plot; this is intentional to avoid misleading empty/fixed-parameter axes.

## Last Touched (2026-06-08): Corrected Reduced CSM Corner Definition

- Corrected `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py` after review: `corner_csm.pdf` must prioritize CSM/density-profile parameters, not just spectral/extinction/viewing geometry.
- Current reduced corner definitions:
  - `corner_core.pdf`: `E52`, `lf0`, `eps_e`, `eps_b`/`eps_B` when fitted.
  - `corner_csm.pdf`: `n017`, `k`, `k1`, `k2`, `sn`, `nt`, `nism`, `rt`, `p`, `ebv_source_frame`, `theta_c`, `theta_v` when fitted.
- Rationale: `n017`, power-law `k`, SBPL `k1/k2/sn`, and bubble density/radius parameters are the scientifically important CSM axes; geometry/extinction are included but should not replace the density-profile terms.
- Note: an initial 2026-06-08 backfill briefly used a too-narrow `corner_csm.pdf` grouping. It was overwritten immediately by the corrected backfill below.
- Corrected backfill regenerated reduced corner products in all completed share-fit directories with both `chain.npz` and `model.toml`, excluding any path containing `trash`:
  - total run directories: 205;
  - successful corrected regenerations: 205;
  - failures: 0.
- Representative corrected parameter checks:
  - structured-jet power-law 140506A production: `corner_csm` includes `n017`, `k`, `p`, `ebv_source_frame`, `theta_c`, `theta_v`.
  - SBPL 080413B pre-production: `corner_csm` includes `k1`, `k2`, `sn`, `nt`, `rt`, `p`, `ebv_source_frame`.
  - empirical bubble 140506A pre-production: `corner_csm` includes `nt`, `nism`, `rt`, `p`, `ebv_source_frame`.
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile /Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py /Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` passed.
  - `bash -n /Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` passed.
  - Rendered `/tmp/140506A_corrected_corner_csm_preview.png` from production 140506A; visual check confirmed `log10 n0,17`, `k`, `p`, `E(B-V)`, `theta_c`, and `theta_v` appear in the corrected CSM corner plot.

## Last Touched (2026-06-08): Beaming-Corrected Jet Energy Products

- Added derived jet-energy post-processing to `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py`.
- Standard postfit products now compute posterior samples for:
  - `E_j_52`: two-sided beaming-corrected true jet energy in units of `1e52 erg`;
  - `E_iso_52`: fitted on-axis isotropic-equivalent energy in units of `1e52 erg`;
  - `theta_c`: fitted/fixed core angle in radians;
  - `Omega_2j_pct_4pi`: two-sided geometric core solid angle as percent of `4*pi`, `100 * (1 - cos(theta_c))`;
  - `E_j_tophat_52`: top-hat/core-angle approximation, `E_iso_52 * (1 - cos(theta_c))`;
  - `Omega_eff_pct_4pi`: energy-weighted effective beaming fraction, `100 * E_j_52 / E_iso_52`.
- Physical convention:
  - Top-hat and top-hat-equivalent cases use the Frail-style two-sided form `E_j = E_iso,0 * (1 - cos(theta))`, with `theta = theta_c` from the fit.
  - Structured `PowerlawJet...` cases integrate the fitted angular energy profile over one hemisphere and apply the two-sided convention via `E_j/E_iso,0 = integral_0^(pi/2) f(theta) sin(theta) dtheta`.
  - The vendored VegasAfterglow profile forms are mirrored exactly for supported structured profiles:
    - Gaussian: `f(theta) = exp[-theta^2 / (2 theta_c^2)]`;
    - Power-law: `f(theta) = 1 / (1 + (theta/theta_c)^k_e)`;
    - Top-hat: `f(theta)=1` inside `theta_c`, zero outside.
- New standard files in each completed run directory:
  - `jet_energy_posterior.npz`: compressed posterior arrays for the derived quantities above;
  - `jet_energy_summary.csv`: mean, standard deviation, median, 16th/84th percentiles, and sample count;
  - `corner_energy.pdf`: corner plot of `E_j_52`, `E_iso_52`, `theta_c`, and `Omega_2j_pct_4pi`.
- `summary.csv` is updated with derived rows when present, using ArviZ-compatible columns where available.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py`:
  - added `plot_energy_corner`;
  - added padded ranges for constant axes so fixed-angle top-hat runs still produce `corner_energy.pdf`;
  - added defensive figure closing when `corner.corner()` throws during a retry.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/base.py` with labels for the derived energy and solid-angle parameters.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so missing `corner_energy.pdf` or `jet_energy_summary.csv` triggers standard postfit regeneration/backfill before syncing.
- Backfilled all completed share-fit directories with both `chain.npz` and `model.toml`, excluding `trash`:
  - `jet_energy_posterior.npz`: 205/205 written;
  - `jet_energy_summary.csv`: 205/205 written;
  - `corner_energy.pdf`: 205/205 written after adding padded ranges for fixed-angle cases;
  - failures: 0.
- Representative visual checks:
  - structured power-law production 140506A rendered to `/tmp/140506A_corner_energy_preview.png` and showed `E_j_52`, `E_iso_52`, `theta_c`, and geometric two-sided core solid-angle percentage;
  - top-hat SBPL 080413B rendered to `/tmp/080413B_tophat_corner_energy_preview.png` and confirmed fixed `theta_c=1` and fixed `Omega_2j/4pi` axes are included rather than skipped.
- Validation:
  - top-hat integration check exactly reproduced `1 - cos(theta_c)` for sample angles;
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile /Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py /Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py /Users/jkeohane/GRBs/VegasJetFit/scripts/plot/base.py` passed;
  - `bash -n /Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` passed.
- Remaining convention note: `Omega_2j_pct_4pi` is the geometric two-sided core solid angle from `theta_c`; for structured jets the profile-weighted effective beaming fraction is separately saved as `Omega_eff_pct_4pi`.

## Last touched: 2026-06-08 postfit product refresh triage

- Modified `scripts/generate_postfit_products.py` to add plotting-only posterior thinning, `--skip-jet-energy`, and per-product warning/continue wrappers so one slow or model-specific product does not abort a whole GRB refresh.
- Modified `scripts/plot/visualize.py` so `plot_frequencies(..., nsamps=...)` can reduce posterior frequency traces for faster standard refreshes; current postfit default is 25 traces plus the minimized/best curves.
- Added `scripts/refresh_share_products_newest_first.py` to move old product files into timestamped `trash/<batch>/` folders and refresh Share_Folder runs in newest-fit order.
- Meeting-mode share refresh on 2026-06-08 prioritized newly minimized Lyra runs over older reprocessing:
  - `Share_Folder/Fits/production_runs/final_seeded_runs/26_06_08__structured_jet__viewing_core_structure_thawed__power_law_csm__seeded_final_final__10_temperature_5000x5000/050525A`
  - `Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/{210905A,220101A,160131A}`
- Commands validated: `python -m py_compile scripts/generate_postfit_products.py scripts/plot/visualize.py scripts/plot/diagnose.py`; direct `generate_postfit_products.py --results ...` runs with `--skip-frequency-plot` for meeting-mode outputs.
- Products confirmed before meeting: reduced corners, standard light curve, AMPy comparison, swept-mass plots for the new local GRBs; `210905A/220101A/160131A` also have `corner_energy.pdf` and `jet_energy_summary.csv`.
- Remaining uncertainty: full `frequencies.pdf`, full spread-light-curve, and/or density-profile tail diagnostics are slow because they enter compiled `VegasAfterglowC`; consider offloading deferred backfill to `pauley404-01`/`pauley404-02` after meeting-critical local products are secure.

## Last touched: 2026-06-08 urgent frequency refresh

- Modified `scripts/plot/visualize.py` so frequency plots accept `nsamps`, `ntimes`, and `fast_indices`; fast mode plots the critical-frequency best/minimized curves and observed spectral-index points while skipping the slow modeled spectral-index curve.
- Modified `scripts/generate_postfit_products.py` to honor `JETFIT_FREQUENCY_POSTERIOR_CURVES`, `JETFIT_FREQUENCY_TIME_SAMPLES`, and `JETFIT_FREQUENCY_FAST_INDICES` for urgent/production frequency refreshes.
- Regenerated urgent `frequencies.pdf` files in Share_Folder for `050525A` final-final, `210905A`, `220101A`, and `160131A` using `JETFIT_FREQUENCY_POSTERIOR_CURVES=0 JETFIT_FREQUENCY_TIME_SAMPLES=40 JETFIT_FREQUENCY_FAST_INDICES=1`.
- Caveat: these urgent frequency PDFs are updated style and minimized/best-track focused; posterior frequency clouds can be backfilled later with a larger `JETFIT_FREQUENCY_POSTERIOR_CURVES` value.

## Last touched: 2026-06-08 restore full corner plots

- Restored existing full posterior `corner.pdf` from local Lyra result directories into the meeting-critical Share_Folder runs for `050525A` final-final and `210905A`, `220101A`, `160131A` unseeded final-production.
- Updated `scripts/refresh_share_products_newest_first.py` so product refreshes no longer move `corner.pdf` to trash, because postfit regeneration currently creates the reduced `corner_core.pdf`, `corner_csm.pdf`, and `corner_energy.pdf` but not the historical full `corner.pdf`.

## Last touched: 2026-06-08 Gamma jet-break diagnostic product

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` to add the standard companion product `gamma_jetbreak_two_panel.pdf/.png` next to `mass_swept_ejecta_two_panel.pdf`.
- The new diagnostic reuses the swept-mass two-panel conventions: top panel is observer time with seconds on the top axis, bottom panel is radius with pc on the top axis, `GRB <event>` appears inside each panel, blue is `theta=0`, red is `theta=theta_c`, and radial data-window shading follows the same angular/overlap convention.
- Physics convention: the plot draws posterior/walker `details.fwd.Gamma` tracks for `theta=0` and `theta=theta_c`; the minimized/best track is emphasized.  The jet-break reference is `Gamma = 1/theta_c`, with a secondary shaded band from `1/(theta_c + theta_v)` to `1/(theta_c - theta_v)` when the upper bound is physically finite.  If `theta_c - theta_v <= 0`, the singular upper bound is skipped.
- Added `gamma_jetbreak_crossings.csv`, with best and walker crossing locations for `Gamma = 1/theta_c` in both observer time and radius.  Crossings outside the plotted/details domain are written as `nan` rather than being pinned to the first model sample.
- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/refresh_share_products_newest_first.py` and `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so the Gamma jet-break product is treated as a standard postfit/share product.
- Validation commands:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_structjet_swept_mass_diagnostics.py scripts/refresh_share_products_newest_first.py scripts/generate_postfit_products.py`
  - `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u scripts/plot_structjet_swept_mass_diagnostics.py --run-dir /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A`
- Regenerated representative products for `220101A`:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A/gamma_jetbreak_two_panel.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A/gamma_jetbreak_two_panel.png`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A/gamma_jetbreak_crossings.csv`
- Remaining uncertainty: visual style is validated on `220101A`; if future bursts have very small `theta_c - theta_v`, the finite upper reference may still create a large shaded band, but singular/non-positive cases are guarded.

## Last touched: 2026-06-08 Gamma jet-break diagnostic style/domain adjustment

- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` so `gamma_jetbreak_two_panel.pdf/.png` places the legend in the lower-left and the GRB label in the upper-right, matching the falling high-to-low Gamma curves.
- Gamma crossing markers now use the full plotted Gamma walker domain, not just the best-fit track domain, so valid walker crossings farther right are shown when the model details arrays extend that far.
- Regenerated the representative Share_Folder product for `220101A`:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A/gamma_jetbreak_two_panel.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A/gamma_jetbreak_two_panel.png`
- Validation: `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_structjet_swept_mass_diagnostics.py` passed; direct regeneration for `220101A` completed successfully.
- Interpretation note: crossing points are computed per posterior sample using that same sample's `theta_c`, i.e. each walker crosses its own `Gamma = 1/theta_c`, not the minimized/best `theta_c`.

## Last touched: 2026-06-08 Gamma jet-break reference simplification

- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` so `gamma_jetbreak_two_panel.pdf/.png` no longer shows the `theta_c +/- theta_v` shaded reference band.
- The Gamma diagnostic now shows only `Gamma = 1/theta_c`: each posterior walker draws its own faint grey dashed `1/theta_c` reference behind the Gamma walker curves, and the minimized/best `1/theta_c` remains the darker dashed line.
- Regenerated the representative `220101A` Share_Folder product after the simplification.
- Validation: `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_structjet_swept_mass_diagnostics.py` passed; direct regeneration for `220101A` completed successfully.

## Last touched: 2026-06-08 Gamma jet-break solid reference lines

- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` so all `Gamma = 1/theta_c` references in `gamma_jetbreak_two_panel.pdf/.png` are solid lines rather than dashed.
- Walker `1/theta_c` lines are faint grey and plotted above the data-window shading but below the Gamma walker curves; minimized/best `1/theta_c` is a darker solid black line at the same z-order layer.
- Regenerated the representative `220101A` Share_Folder Gamma jet-break product.
- Validation: `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_structjet_swept_mass_diagnostics.py` passed; direct `220101A` regeneration completed successfully.

## Last touched: 2026-06-08 Gamma jet-break right ticks and label placement

- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` so `gamma_jetbreak_two_panel.pdf/.png` mirrors y-axis tick marks on the right side of both Gamma panels.
- Moved the GRB label for Gamma jet-break panels to data-space near `Gamma = 100` at the left side of the panel, avoiding the high-Gamma plateaus and late-time descending curves better than the upper-right placement.
- Regenerated the representative `220101A` Share_Folder Gamma jet-break product.
- Validation: `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_structjet_swept_mass_diagnostics.py` passed; direct `220101A` regeneration completed successfully.

## Last touched: 2026-06-08 Gamma jet-break top-panel-only legend

- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` so `gamma_jetbreak_two_panel.pdf/.png` has the GRB label and legend only on the upper time panel.
- Removed the explicit `walker 1/theta_c` legend entry; the faint grey walker reference lines remain in the plot, with the black `Gamma = 1/theta_c` legend entry implying the same reference convention.
- Moved the legend directly below the GRB label near the left side of the upper panel.
- Regenerated the representative `220101A` Share_Folder Gamma jet-break product.
- Validation: `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_structjet_swept_mass_diagnostics.py` passed; direct `220101A` regeneration completed successfully.

## Last touched: 2026-06-08 Gamma jet-break plot approved pipeline style

- Jonathan approved the `gamma_jetbreak_two_panel.pdf/.png` style after the top-panel-only legend/label cleanup.
- Verified this approved style is in the canonical pipeline path: `scripts/generate_postfit_products.py` calls `maybe_generate_structjet_swept_mass_overlay()`, which runs `scripts/plot_structjet_swept_mass_diagnostics.py`; that script now writes `gamma_jetbreak_two_panel.pdf/.png` and `gamma_jetbreak_crossings.csv` next to the swept-mass products.
- Verified `scripts/sync_results_to_drive.sh` treats missing `gamma_jetbreak_two_panel.pdf` as a trigger for postfit product regeneration, and `scripts/refresh_share_products_newest_first.py` includes the Gamma products in its standard product list.
- Validation: `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/plot_structjet_swept_mass_diagnostics.py scripts/generate_postfit_products.py scripts/refresh_share_products_newest_first.py` passed; `bash -n scripts/sync_results_to_drive.sh` passed.

## Last touched: 2026-06-08 mass/Gamma diagnostic pipeline convention

- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so the old `mass_profile.csv/.pdf/.png` product is no longer generated by the standard postfit pipeline.
- Updated `/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_results_to_drive.sh` so `mass_profile.pdf` is no longer required to trigger/satisfy postfit products, and `mass_profile.csv/.png/.pdf` are excluded from sync output.
- Kept `mass_profile.csv/.pdf/.png` in `/Users/jkeohane/GRBs/VegasJetFit/scripts/refresh_share_products_newest_first.py` only as obsolete cleanup targets, so refreshes move old copies to `trash` before regenerating current products.
- Added a code comment in `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py` documenting that red/core-edge walker curves and crossing clouds use each posterior sample's own `theta_c`, not the minimized/best `theta_c`.
- Current canonical products are `mass_swept_ejecta_time.*`, `mass_swept_ejecta_radius.*`, `mass_swept_ejecta_two_panel.*`, `mass_swept_ejecta_crossings.csv`, `gamma_jetbreak_two_panel.*`, and `gamma_jetbreak_crossings.csv`.
- Validation: `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/generate_postfit_products.py scripts/refresh_share_products_newest_first.py scripts/plot_structjet_swept_mass_diagnostics.py` passed; `bash -n scripts/sync_results_to_drive.sh` passed.

## Last Touched (2026-06-08): AMPy Comparison Layout and Data-Count Audit

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` AMPy comparison plotting:
  - kept the agreed quick-reference metric `difference_over_average = 2 * (x_this - x_Dylan) / (|x_this| + |x_Dylan|)`;
  - restored the readable old-style single-panel bar layout instead of the crowded in-axes warning box;
  - moved nmap/data-count context to compact footer text;
  - changed the data-count wording so `raw_grb_data_rows` from `analysis/nmap_dataset_check*_20260428` is treated as a reference/audit count, not asserted as the exact Dylan fitted-row count.
- Regenerated preview:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A/ampy_comparison.pdf`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/220101A/ampy_comparison.png`
- Data-count audit result:
  - final-production run `obs.csv` files checked were byte-identical to `VegasJetFit/jetfit/resources/grbs/<event>/<event>.csv`;
  - those current resource CSVs do not always match the April same-model/thesis-reproduction audit counts, so same-data nmap cannot be assumed for all GRBs;
  - notable final-production mismatches relative to the audit table include `220101A` (`407` current obs rows versus audit raw/reference `627`) and `140506A` (`207` current obs rows versus audit raw/reference `695`).
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/generate_postfit_products.py` passed.
  - Visual inspection of regenerated `220101A/ampy_comparison.png` confirmed the plot layout is readable and the warning is no longer drawn over the bars.
- Remaining uncertainty:
  - Need a source-of-truth Dylan/thesis fitted-data manifest if we want the pipeline to enforce exact Dylan data by default rather than compare against historical audit row counts.

## Last Touched (2026-06-08): AMPy Comparison Label De-Cluttering

- Follow-up after visual review: the first layout repair still had bunched/near-vertical labels.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` again:
  - added compact display labels for AMPy comparison parameters, e.g. `E52 -> E_52`, `lf0 -> Gamma_0`, `n017 -> n_0,17`, `ebv_source_frame -> E(B-V)`;
  - made x-axis tick labels horizontal;
  - widened the figure;
  - moved value labels to bar ends and pulls labels inside the plot when the metric is near the bounded +/-2 limits.
- Regenerated `ampy_comparison.pdf/.png/.csv` for all 12 GRBs in:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000`
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/generate_postfit_products.py` passed.
  - Visual spot-check of `220101A/ampy_comparison.png` confirmed horizontal labels and no top-label clipping.

## Last Touched (2026-06-08): True Jet-Energy Prior Support for Structured-Jet Fits

- Added `/Users/jkeohane/GRBs/VegasJetFit/jetfit/models/jet_energy.py` with shared two-sided jet-energy conversion helpers:
  - `integrated_profile_beaming_fraction(jet_type, theta_c, k_e)`;
  - `e_iso52_from_e_jet52(...)`;
  - `resolve_e_iso52(...)`.
- Modified VegasAfterglow wrappers so configs may sample either historical on-axis isotropic-equivalent `E52` or physical true jet energy `E_j_52`:
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/models/powerlawVegas.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/models/vegasafterglow.py`
- Conversion convention matches postfit products:
  - top-hat: `E_j / E_iso,on-axis = 1 - cos(theta_c)`;
  - Gaussian/power-law structured jets: integrate the angular energy profile over `0..pi/2` using the two-sided convention.
- Updated postfit/diagnostic products to support chains with either `E52` or `E_j_52`:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_mass_vs_time_products.py`
- Added config builder:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_structured_jet_ejet_configs.py`
  - Replaces sampled `E52` with sampled log-scale `E_j_52` using user-specified `--log-ejet-lower/--log-ejet-upper`.
- Added data-row audit guard:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/check_obs_rows_against_audit.py`
  - `jwk_run_thesis_reproduction_event.sh` now supports `REQUIRE_AUDIT_OBS_ROWS=1`, which fails preflight if the selected obs CSV row count does not match the local April 2026 audit table counts.
- Validation:
  - Python compile passed for all modified Python files and `bash -n jwk_run_thesis_reproduction_event.sh` passed.
  - Direct model smoke test: `E_j_52=1`, `theta_c=0.2`, `k_e=2` for a power-law structured jet converts to `E_iso_52=13.2341`.
  - Config-builder smoke test wrote `/tmp/ejet_configs_smoke/220101A.toml` with `E_j_52` replacing `E52`.
  - Derived-energy smoke test with the temporary `E_j_52` config returned `E_j_52=1.0`, `E_iso_52=13.2342`, and `Omega_eff_pct_4pi=7.556%`.
  - Row-count audit correctly flags current `220101A` resource data as mismatched: current obs rows `407`, audit raw `627`, audit curated `629`.
- Remaining decision before launching new fits:
  - choose the physical prior range for `log10(E_j_52)`;
  - decide whether to enforce the row-count audit as strict (`REQUIRE_AUDIT_OBS_ROWS=1`) for the new campaign, or first reconstruct/restore exact Dylan thesis CSVs where the audit mismatches.

## Last Touched (2026-06-08): Generated E_j,kin Prior Config Set

- Generated new structured-jet kinetic-energy-prior configs from `structured_jet_finalprod_unseeded_configs_active`:
  - `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_finalprod_ejetkin_configs_active/`
- Replaced sampled `E52` with sampled log-scale `E_j_52` in all generated configs.
- Hard prior range used:
  - `log10(E_j_52) = [-3, 1]`, i.e. `10^-3 <= E_j,kin,52 <= 10`.
- Scientific note encoded in the config audit:
  - `E_j_52` is two-sided beaming-corrected kinetic afterglow energy;
  - broad sanity range is `1e-3..10`;
  - main plausible ordinary long-soft GRB band is `0.03..3`.
- Config audit:
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/structured_jet_finalprod_ejetkin_config_audit.csv`
- Current row-count audit against selected `jetfit/resources/grbs/<event>/<event>.csv`:
  - Passes strict audit: `050525A`, `050922C`, `090618`, `130612A`, `171010A`, `221009A`.
  - Fails strict audit: `090424`, `111228A`, `131030A`, `140506A`, `160131A`, `210905A`, `220101A`.
- Important launch note:
  - If `REQUIRE_AUDIT_OBS_ROWS=1` is enabled, the failing events will not launch until their selected obs CSVs are restored/replaced with Dylan-sized data or the audit policy is intentionally relaxed.
- Validation:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/build_structured_jet_ejet_configs.py scripts/check_obs_rows_against_audit.py jetfit/models/jet_energy.py jetfit/models/powerlawVegas.py jetfit/models/vegasafterglow.py scripts/generate_postfit_products.py scripts/plot_structjet_swept_mass_diagnostics.py scripts/build_mass_vs_time_products.py` passed.
  - `bash -n jwk_run_thesis_reproduction_event.sh` passed.

## Last Touched (2026-06-08): Structured-Jet E_j Kinetic Prior Configs

- Updated the active final-production structured-jet kinetic-energy config set:
  - `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_finalprod_ejetkin_configs_active/*.toml`
- Current sampled energy convention:
  - `E_j_52` is sampled instead of `E52`.
  - It is the two-sided beaming-corrected kinetic afterglow energy in units of `10^52 erg`, with hard log prior `-3 <= log10(E_j_52) <= 1`.
- Additional hard-prior changes applied to all 13 generated event configs:
  - `lf0` uses `1.69 <= log10(Gamma_0) <= 5.0`.
  - `eps_b` uses `-9.0 <= log10(epsilon_B) <= 0.0`.
- Builder updated:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_structured_jet_ejet_configs.py` now defaults to `--log-gamma0-upper 5.0` and `--log-epsb-lower -9.0`, so regenerated configs preserve these prior choices.
- Audit:
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/structured_jet_finalprod_ejetkin_prior_update_audit.csv`
- Commands run:
  - Python one-off config patch/audit script using `_load_toml` and `_write_toml`.
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/build_structured_jet_ejet_configs.py scripts/check_obs_rows_against_audit.py jetfit/models/jet_energy.py jetfit/models/powerlawVegas.py jetfit/models/vegasafterglow.py scripts/generate_postfit_products.py scripts/plot_structjet_swept_mass_diagnostics.py scripts/build_mass_vs_time_products.py`
  - Temp dry-run regeneration for `220101A` with `scripts/build_structured_jet_ejet_configs.py`.
- Validation:
  - All 13 active configs validate with `E_j_52=(-3.0, 1.0)`, `lf0=(1.69, 5.0)`, and `eps_b=(-9.0, 0.0)`.
  - Builder dry-run produced the same bounds for a temporary `220101A` config.
- Remaining uncertainty:
  - Fits were not launched in this touch.  Earlier strict same-data audit still reported row-count mismatches for several events; resolve or intentionally override that before production launch.

## Last Touched (2026-06-08): Event-Specific Angular Prior Correction

- Correction to the `E_j_52` structured-jet config set:
  - the `theta_c < 0.3 rad` and `theta_v < 0.3 rad` prior caps were intended only for `220101A`, not the full campaign.
- Active config state after correction:
  - `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_finalprod_ejetkin_configs_active/220101A.toml` has `theta_c=(0.001, 0.3)` and `theta_v=(0.0, 0.3)`.
  - The other 12 active configs have the original angular upper bounds restored: `theta_c=(0.001, 1.0)` and `theta_v=(0.0, 1.0)`.
- Builder behavior after correction:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_structured_jet_ejet_configs.py` keeps `--theta-c-upper` and `--theta-v-upper` as optional overrides with no global default cap.
  - Default regeneration preserves angular bounds from the source config.
  - Passing `--theta-c-upper 0.3 --theta-v-upper 0.3` applies the narrow angular prior for an event-specific generated config.
- Audit updated:
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/structured_jet_finalprod_ejetkin_prior_update_audit.csv`
- Validation:
  - Active config readback confirmed only `220101A` has the 0.3 rad angular caps.
  - Builder dry-run confirmed default output keeps `theta_c/theta_v <= 1.0`, while explicit optional args produce `theta_c/theta_v <= 0.3`.
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile scripts/build_structured_jet_ejet_configs.py` passed.
- Remaining uncertainty:
  - Assumed Jonathan meant `220101A` by "this GRB" because that was the inspected config in this correction.  If a different event was intended, move the 0.3 rad caps to that event before launch.

## Last Touched (2026-06-08): Preliminary E_j Structured-Jet Runs Launched

- Launched a same-day preliminary `220101A` run on Lyra with event-specific angular caps:
  - result label: `220101A_structjet_ejetkin_thetacv_lt0p3_prelim_5temp_1000x1000_v1`
  - config: `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_finalprod_ejetkin_configs_active/220101A.toml`
  - MCMC settings: `/Users/jkeohane/GRBs/VegasJetFit/Ansh_Run/mcmc_settings_structjet_prelim_5temp_1000x1000.toml`
  - tmux session: `grb220101A_ejet_prelim`
  - MCMC profile: 5 temperatures, 100 walkers, 1000 burn + 1000 production, checkpoint interval 100.
  - minimizer enabled on Lyra with `MINIMIZE_MAX_WALKERS=20` for preliminary best-fit refinement.
- Launched two additional MCMC-only preliminary runs on idle Pauley hosts using the same new global priors for `E_j_52`, `lf0`, and `eps_b`, but without the `220101A` angular cap:
  - `160131A` on `pauley404-01`, tmux session `ejetprelim_160131A_pauley404_01`, result label `160131A_structjet_ejetkin_prelim_5temp_1000x1000_v1`.
  - `210905A` on `pauley404-03`, tmux session `ejetprelim_210905A_pauley404_03`, result label `210905A_structjet_ejetkin_prelim_5temp_1000x1000_v1`.
- `pauley404-02` was left alone because it was still running the older `221009A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1` job.
- Remote launch scripts:
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/160131A.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-01.launch.sh`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/210905A.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-03.launch.sh`
- Remote logs to monitor:
  - `pauley404-01:/Users/jkeohane/GRBs/VegasJetFit/logs/160131A.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-01.watchrun.log`
  - `pauley404-01:/Users/jkeohane/GRBs/VegasJetFit/logs/160131A.structjet_ejetkin_prelim_5temp_1000x1000_v1.log`
  - `pauley404-03:/Users/jkeohane/GRBs/VegasJetFit/logs/210905A.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-03.watchrun.log`
  - `pauley404-03:/Users/jkeohane/GRBs/VegasJetFit/logs/210905A.structjet_ejetkin_prelim_5temp_1000x1000_v1.log`
- Validation before leaving:
  - Synced `jet_energy.py`, `powerlawVegas.py`, `vegasafterglow.py`, event configs, and the preliminary MCMC settings to `pauley404-01` and `pauley404-03`.
  - Confirmed both Pauley sessions are up and running preflight with `RUN_MINIMIZER=0` and Drive sync disabled.
  - Confirmed `220101A` Lyra preflight passed and the full run started.
- Next check:
  - In ~14 hours, inspect the three result dirs for `chain.npz`, `best_fit.json`, `summary.csv`, and `pt_resume_state.npz` completion state.
  - Pull the two Pauley result dirs back to Lyra, then run minimization and standard products locally if MCMC completed.

## Last Touched (2026-06-09): Shared Preliminary E_j Diagnostic Campaign Folder

- Created/synced the new unseeded shorter diagnostic campaign in Share_Folder:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/shorter_diagnostic_runs/unseeded_runs/26_06_08__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_ejetkin_prior_diagnostic__5_temperature_1000x1000`
- Share subfolders synced:
  - `220101A/` from Lyra local result `220101A_structjet_ejetkin_thetacv_lt0p3_prelim_5temp_1000x1000_v1`.
  - `160131A/` from `pauley404-01` result `160131A_structjet_ejetkin_prelim_5temp_1000x1000_v1`.
  - `210905A/` from `pauley404-03` result `210905A_structjet_ejetkin_prelim_5temp_1000x1000_v1`.
- Wrote campaign notes:
  - `README.md`
  - `STATUS.csv`
- Status at sync time:
  - `210905A`: full preliminary products copied, but remote postfit warned for some E_j/E52-dependent products; regenerate on Lyra for final clean products.
  - `160131A`: MCMC artifacts copied only (`chain.npz`, `best_fit.json`, `pt_resume_state.npz`, sidecars); wrapper still alive/stuck after MCMC, no `summary.csv` at sync time.
  - `220101A`: MCMC artifacts copied only (`chain.npz`, `best_fit.json`, `pt_resume_state.npz`, sidecars); wrapper still alive/stuck after MCMC, no `summary.csv` or minimized outputs at sync time.
- Next step:
  - Stop/recover stuck wrappers if needed, pull/refresh 160131A and 210905A to Lyra, run minimization and current standard postfit scripts, then re-sync this same Share_Folder campaign path.

## Last Touched (2026-06-09): Renamed Share E_j Diagnostic Campaign Path

- Renamed the Share_Folder preliminary campaign so the jet-energy purpose comes first in the directory name:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/shorter_diagnostic_runs/unseeded_runs/26_06_08__ejetkin_prior_diagnostic__unseeded_structured_jet__viewing_core_structure_thawed__power_law_csm__5_temperature_1000x1000`
- The old path with `structured_jet...unseeded_ejetkin...` was moved/merged into this renamed path.
- Updated the campaign `README.md` header to emphasize the `E_j` kinetic-energy prior diagnostic.
- Future re-syncs for `220101A`, `160131A`, and `210905A` should target the renamed path above.

## E-jet Diagnostic Pauley Launches (2026-06-09)

- Updated debugged E-jet/postfit code and diagnostic configs were synced to `pauley404-01` and `pauley404-03`; remote `py_compile` validation passed before launch.
- New diagnostic MCMC runs launched with `5temp_1000x1000`, 100 walkers, 8 workers, `RUN_MINIMIZER=0`, and diagnostic minimizer convention `MINIMIZE_MAX_WALKERS=8` for follow-up on Lyra:
  - `050525A` on `pauley404-01`, tmux session `ejetprelim_050525A_pauley404_01`.
    - Remote launcher: `/Users/jkeohane/GRBs/VegasJetFit/logs/050525A.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-01.launch.sh`
    - Remote watch log: `/Users/jkeohane/GRBs/VegasJetFit/logs/050525A.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-01.watchrun.log`
    - Remote result: `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/050525A_structjet_ejetkin_prelim_5temp_1000x1000_v1`
  - `090618` on `pauley404-03`, tmux session `ejetprelim_090618_pauley404_03`.
    - Remote launcher: `/Users/jkeohane/GRBs/VegasJetFit/logs/090618.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-03.launch.sh`
    - Remote watch log: `/Users/jkeohane/GRBs/VegasJetFit/logs/090618.structjet_ejetkin_prelim_5temp_1000x1000_v1.pauley404-03.watchrun.log`
    - Remote result: `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/090618_structjet_ejetkin_prelim_5temp_1000x1000_v1`
- Initial health check: both tmux sessions alive; both wrappers found the updated E-jet configs and entered preflight without immediate errors.
- Related Lyra diagnostics at launch time:
  - `220101A_structjet_ejetkin_thetacv_lt0p3_prelim_5temp_1000x1000_v1` completed 8-walker minimization with `nmap=-17845.244396`; postfit regeneration started in tmux session `diag_postfit_220101A_ejet`.
  - `160131A_structjet_ejetkin_prelim_5temp_1000x1000_v1` 8-walker minimization still running in tmux session `diag_min8_160131A_ejet`.
  - `210905A_structjet_ejetkin_prelim_5temp_1000x1000_v1` postfit regeneration after 8-walker minimization still running.
- Follow-up health check after launch: `050525A` preflight completed successfully and the full production MCMC started (`iterations=1000`, `burn=1000`, checkpoint every 100). `090618` remained healthy in preflight, with valid walkers through at least temperature 2 when checked.

## Last Touched (2026-06-09): 210905A AMPy Comparison Style Refresh

- Issue: `/Users/jkeohane/GRBs/Share_Folder/Fits/shorter_diagnostic_runs/unseeded_runs/26_06_08__ejetkin_prior_diagnostic__unseeded_structured_jet__viewing_core_structure_thawed__power_law_csm__5_temperature_1000x1000/210905A/ampy_comparison.pdf` had been generated from the older AMPy comparison layout, with the in-plot data-count mismatch box and rotated labels.
- Regenerated only the AMPy comparison through the current `scripts/generate_postfit_products.py::plot_ampy_comparison()` code path for:
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/210905A_structjet_ejetkin_prelim_5temp_1000x1000_v1`
- Copied refreshed products to the diagnostic Share_Folder GRB subfolder:
  - `ampy_comparison.pdf`
  - `ampy_comparison.png`
  - `ampy_comparison.csv`
- Validation:
  - Visual check of the regenerated PNG confirmed the revised style: horizontal compact labels, footer nmap/data-count text, no in-plot mismatch box.
  - `cmp` confirmed local and Share_Folder PDF/PNG files match.
- Remaining note:
  - A full `210905A` postfit regeneration was still running at this time; if it later rewrites the AMPy comparison, it should use the same current source, but re-check timestamps if the plot appears stale again.

## Last Touched (2026-06-09): Faster EATS-Weighted Frequency Plot Path

- Optimized the standard `frequencies.pdf` calculation path without changing the break-frequency definition.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py`:
  - `model_freqs()` now first uses a model-level `critical_frequencies(t)` hook when available, avoiding full diagnostic `spectrum()` and unnecessary `f_peak` calculations.
  - posterior spectral-index curves now prefer `model.spectral_index(times, lower, upper, fts=...)`, matching the best-fit path, and fall back to the old `spectrum()` + `SpectralIndexModel` path only if needed.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/jetfit/models/powerlawVegasDylanSpectrum.py`:
  - added `critical_frequencies(t)` returning EATS-weighted `nu_a`, `nu_m`, `nu_c` only;
  - batched EATS-weighted observer-frame break calculation for `nu_a`, `nu_m`, and `nu_c` from one VegasAfterglow `details()` object and one set of angular weights.
- Science convention preserved:
  - local VegasAfterglow detail break fields are transformed as `nu_obs = nu_local * Doppler / (1+z)`;
  - EATS representative breaks use weights proportional to `I_nu_max * Doppler^3`;
  - `break_frequency_mode="local_trace"` still gives the old single-zone trace when explicitly requested.
- Validation:
  - `py_compile` passed for `scripts/plot/visualize.py` and `jetfit/models/powerlawVegasDylanSpectrum.py`.
  - Direct consistency check on minimized `210905A` confirmed batched `_weighted_observed_freqs()` matches the old per-frequency helper exactly for `nu_a`, `nu_m`, and `nu_c` on a small time grid.
  - Smoke test through `model_freqs()` on minimized `210905A` returned finite `nu_a`, `nu_m`, and `nu_c`.
- Note:
  - Any already-running `generate_postfit_products.py` process will not pick up this code until restarted; future postfit/frequency runs will use the faster path.

## Last Touched (2026-06-09): Frequency Plot Data Products and Legend Clarity

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` so `frequencies.pdf` now writes reusable frequency data before plotting:
  - `frequencies_data.npz`: `times_days`, `times_seconds`, posterior-sample arrays `sample_nu_a_hz`, `sample_nu_m_hz`, `sample_nu_c_hz`, and best/minimized arrays `best_nu_a_hz`, `best_nu_m_hz`, `best_nu_c_hz`.
  - `frequencies_best_curve.csv`: easy-inspection best/minimized curve with `time_days,time_seconds,nu_a_hz,nu_m_hz,nu_c_hz`.
- The in-panel GRB label now uses `JETFIT_PLOT_EVENT_TITLE` when available, so postfit plots show e.g. `GRB 210905A` rather than the full run-directory name.
- Clarified the lower-panel legend:
  - `XRT` -> `XRT spectral index`;
  - posterior lower-panel model curves -> `model spectral-index samples`.
- Validation:
  - `py_compile` passed for `scripts/plot/visualize.py`.
  - Smoke regeneration for minimized `210905A` with `nsamps=2`, `ntimes=5`, `fast_indices=True` wrote `frequencies.pdf`, `frequencies_data.npz`, and `frequencies_best_curve.csv` to `/tmp/frequency_smoke_210905A`.
  - Rendered smoke PNG confirmed the in-panel label is `GRB 210905A` and the lower legend says `XRT spectral index`.

## Last Touched (2026-06-09): Frequency/Gamma Label Placement and Faster Frequency Data Path

- Modified `/Users/jkeohane/GRBs/VegasJetFit/jetfit/core/utils.py` with shared plot helpers:
  - `get_plot_event_title()` / `apply_plot_title()` for compact event-aware titles;
  - `choose_axes_label_position()` and `add_collision_aware_grb_label()` for data-aware in-panel GRB labels that try vertical shifts before horizontal shifts.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py`:
  - frequency plots save `frequencies_data.npz` and `frequencies_best_curve.csv` before plotting;
  - standard `frequencies.pdf` uses the compact `JETFIT_PLOT_EVENT_TITLE` GRB label;
  - bottom spectral-index legend was removed so the XRT spectral-index points cannot be confused with legend handles;
  - posterior spectral-index curves use the model's vectorized `spectral_index()` path when available.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/jetfit/models/powerlawVegasDylanSpectrum.py`:
  - added batched EATS-weighted break-frequency evaluation through `critical_frequencies(t)`;
  - preserves the Dylan EATS-weighted convention: observer-frame local breaks weighted by `I_nu_max * Doppler^3`, with the existing `local_trace` fallback unchanged.
- Modified plot-product scripts to use collision-aware GRB labels:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_structjet_swept_mass_diagnostics.py`
- Lorentz-factor diagnostic convention:
  - `gamma_jetbreak_two_panel.pdf` places the GRB label and legend only on the upper panel;
  - the legend anchor is now computed from the chosen GRB-label anchor so the label and legend move together;
  - the swept-mass/gamma standalone script now uses `JETFIT_PLOT_EVENT_TITLE` or a compact inferred event name, not the full run directory name.
- Validation commands run:
  - `/Users/jkeohane/GRBs/.venv/bin/python -m py_compile jetfit/core/utils.py scripts/plot_structjet_swept_mass_diagnostics.py scripts/plot/visualize.py scripts/generate_postfit_products.py scripts/plot_spread_light_curves.py`
  - frequency smoke render for 210905A to `/tmp/frequency_smoke_210905A_label2/frequencies.pdf` with `nsamps=2`, `ntimes=5`, `fast_indices=False`;
  - gamma/swept-mass smoke render for copied 210905A inputs to `/tmp/gamma_smoke_210905A_run2/gamma_jetbreak_two_panel.pdf` and `.png`.
- Visual validation:
  - frequency smoke plot has short `GRB 210905A` label shifted below the XRT data row;
  - gamma smoke plot has short `GRB 210905A` label with the legend directly beneath it, and no legend/name on the lower panel.
- Operational note:
  - postfit processes already running before this patch will not pick up these in-memory plotting changes; rerun/refresh products after those jobs finish if their outputs need the latest label and frequency-cache behavior.

### Follow-up (2026-06-09 11:35 EDT): Cached Frequency Replot Confirmed

- `FrequencyPlotter.plot_dist()` now reuses `frequencies_data.npz` when the cached `times_days` exactly matches the requested time grid.  This avoids recomputing structured-jet EATS break frequencies for style-only replots.
- The cached replot still redraws the bottom spectral-index panel from the current model path, but the expensive top-panel break curves are loaded from the `.npz` cache.
- Full 210905A frequency render before cache-aware replot took about 19 minutes while sharing CPU with old postfit jobs; the cached replot took 16-17 seconds.
- Refreshed local products:
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/210905A_structjet_ejetkin_prelim_5temp_1000x1000_v1/frequencies.pdf`
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/210905A_structjet_ejetkin_prelim_5temp_1000x1000_v1/frequencies_data.npz`
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/210905A_structjet_ejetkin_prelim_5temp_1000x1000_v1/frequencies_best_curve.csv`
- Copied refreshed frequency products to Share_Folder:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/shorter_diagnostic_runs/unseeded_runs/26_06_08__ejetkin_prior_diagnostic__unseeded_structured_jet__viewing_core_structure_thawed__power_law_csm__5_temperature_1000x1000/210905A/frequencies.pdf`
  - same directory: `frequencies_data.npz`, `frequencies_best_curve.csv`
- Visual validation:
  - `/tmp/check_210905A_full_freq_fixed2/frequencies-1.png` shows the GRB label moved below the XRT row; no bottom legend is present.
- Caveat:
  - Existing pre-patch postfit jobs for 210905A and 220101A were still running when this note was written.  If they later overwrite `frequencies.pdf`, rerun the cached refresh or regenerate with the current code.

## Status Check (2026-06-11 07:45 EDT): Pauley and Diagnostic Runs

- Lyra local process check found no active `run.py`, `minimize.py`, or `generate_postfit_products.py` Python jobs.
- `pauley404-01`, `pauley404-02`, and `pauley404-03` process checks found no active tmux sessions and no active user Python fitting/postfit processes.
- Pauley 2 long final-production run status:
  - Remote/local result: `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/221009A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1`
  - `pt_resume_state.npz completed_iterations=5000`, `target_iterations=5000`.
  - `chain.npz` shape is `(5000, 100, 20)`.
  - MCMC completed successfully on `pauley404-02`, but the wrapper failed immediately afterward during plotting due stale remote code: `ImportError: cannot import name 'apply_plot_title' from jetfit.core.utils`.
  - Local Lyra result directory exists with only raw MCMC artifacts (`chain.npz`, `pt_resume_state.npz`, `best_fit.json`, model/obs/settings); no minimized/postfit products yet.
- Diagnostic E_j campaign status in Share_Folder path `/Users/jkeohane/GRBs/Share_Folder/Fits/shorter_diagnostic_runs/unseeded_runs/26_06_08__ejetkin_prior_diagnostic__unseeded_structured_jet__viewing_core_structure_thawed__power_law_csm__5_temperature_1000x1000`:
  - `160131A`, `210905A`, and `220101A` have local and share postfit products including reduced corners, light curves, mass/gamma plots, jet-energy products, and density plots.
  - `050525A` and `090618` have many postfit products in Share_Folder, but frequency plot generation failed/was skipped on remote repair paths; regenerate `frequencies.pdf`, `frequencies_data.npz`, and `frequencies_best_curve.csv` locally with current code.
  - `050525A` remote postfit log shows `WARNING: frequency plot failed: TypeError: plot_frequencies() got an unexpected keyword argument 'ntimes'`, then other products completed.
  - `090618` remote postfit finished many standard products after a skip-frequency repair, but no frequency files are present in the share folder.
- Recommended next action: run 8-walker minimization and current local postfit pipeline for `221009A` on Lyra, then sync to the production Share_Folder; separately regenerate missing frequency products for `050525A` and `090618` diagnostic runs with the current cached frequency code.

## Last Touched (2026-06-11): Pauley 2 Code Sync

- Synced current Lyra code/configs to `pauley404-02` without touching `jetfit/results/`:
  - `VegasJetFit/jetfit/` excluding `results/`, `__pycache__/`, `*.pyc`, `.DS_Store`;
  - `VegasJetFit/scripts/` excluding `__pycache__/`, `*.pyc`, `.DS_Store`, `runtime_logs/`;
  - `structured_jet_finalprod_ejetkin_configs_active/`;
  - `structured_jet_finalprod_unseeded_configs_active/`;
  - `Ansh_Run/mcmc_settings_structjet_prelim_5temp_1000x1000.toml` and `Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml`.
- Remote validation on `pauley404-02` passed:
  - `py_compile` for `jetfit/core/utils.py`, `jetfit/models/powerlawVegasDylanSpectrum.py`, `jetfit/models/powerlawJetVegasDylanSpectrum.py`, `jetfit/models/jet_energy.py`, `scripts/plot/visualize.py`, `scripts/generate_postfit_products.py`, `scripts/plot_structjet_swept_mass_diagnostics.py`, and `scripts/plot_spread_light_curves.py`.
  - Import check passed for `apply_plot_title`, `add_collision_aware_grb_label`, and `plot_frequencies`.
- Important active-process note:
  - `pauley404-02` had an active short diagnostic run at sync time: tmux `ejetprelim_221009A_pauley404_02`, result `221009A_structjet_ejetkin_prelim_5temp_1000x1000_v1`.
  - The active run is the 5-temperature 1000x1000 E-jet diagnostic, not the old completed 5000x5000 production run.
  - Log showed valid walkers through temperatures 0-4 and no checkpoint yet at the last check.
- Old Pauley 2 final-production result remained intact after sync:
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/221009A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1`
  - `completed_iterations=5000`, `target_iterations=5000`, `chain_shape=(5000,100,20)`.

## Last Touched (2026-06-11): 221009A Final-Production Lyra Minimization/Postfit Started

- Started Lyra pipeline in tmux session `minpost_221009A_finalprod` for completed long-production run:
  - result: `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/221009A_structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1`
  - share target: `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_05_21__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_final_production__10_temperature_5000x5000/221009A`
  - launcher script: `/Users/jkeohane/GRBs/VegasJetFit/logs/221009A.finalprod_5000x5000.minimize_postfit_lyra.sh`
  - log: `/Users/jkeohane/GRBs/VegasJetFit/logs/221009A.finalprod_5000x5000.minimize_postfit_lyra_20260611T153835Z.log`
- Minimized with:
  - `scripts/minimize.py --mode walkers --max-walkers 20 --parallel-workers 8 --scipy-method Powell --fallback-scipy-method Nelder-Mead`
  - run-sidecar `obs.csv` and `model.toml` were used.
- Minimization completed at `2026-06-11T15:45:58Z`:
  - `processed_walkers=20`
  - `minimized/minimized.json` and `minimized/minimized_walkers.csv/json` were written.
  - selected result: `success=True`, `nmap=-73311.487691`, `method=seed_preserved`.
  - Interpretation: runtime mismatch guard preserved the best MCMC seed rather than trusting an optimizer step that was not apples-to-apples.
- Postfit is running automatically after minimization:
  - command: `scripts/generate_postfit_products.py --results <run> --event 221009A`
  - as of 2026-06-11 11:58 EDT, PID `50656` was active at ~100% CPU and no key postfit products had been written yet.
- Next check:
  - inspect the same log and tmux session;
  - verify `frequencies.pdf`, `summary.csv`, `ampy_comparison.pdf`, reduced corners, jet-energy products, swept-mass/gamma products, and light-curve products;
  - confirm rsync to the share target and `sync_manifest.txt` after postfit completes.

## Last touched: 2026-06-11 light-curve model-data caches

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` so the standard postfit light curve writes `light_curve_model_data.npz` with best-fit unscaled model fluxes by band, `times_days`, and metadata.
- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` so spread-out light-curve generation writes `light_curve_spread_out_model_data.npz` with best-fit, posterior percentile-sample, and final-walker model flux stacks before spread factors are applied.
- `plot_spread_light_curves.py` now automatically reuses `light_curve_spread_out_model_data.npz` when `ndata`, `ncurves`, `seed`, and `walker_limit` match, avoiding repeated VegasAfterglow model evaluations for quick restyling/replotting.
- Validation: `py_compile` passed for both scripts; a temporary symlinked 050525A run created both cache files, and a second spread-light-curve run printed `light_curve_cache_reused` with XRT included in best/posterior/walker arrays.
- Remaining uncertainty: the already-running 221009A serial postfit started before this patch and will not produce these caches unless its light-curve steps are rerun after completion.

## Last Touched 2026-06-12: log10(E_j,52) Config Builder and Corner Labels
- `build_structured_jet_ejet_configs.py` now handles both source styles: old configs with `E52` and already-converted configs with `E_j_52`. Existing `E_j_52` entries are updated in place, avoiding duplicate fitted energy parameters.
- Raw-chain diagnostic corner labels now treat fitted `E_j_52` with `scale='log'` as `log10(E_j,52)`. This is intentionally separate from the derived `corner_energy.pdf`, whose `E_j_52` samples are linear physical energies from `jet_energy_posterior.npz`.
- `corner_core.pdf` now includes `E_j_52` when present, so ejet configs do not drop the fitted energy coordinate from the reduced physical corner plot.
- New smoke-only queue helper: `/Users/jkeohane/GRBs/VegasJetFit/scripts/run_logejet52_smoke_queue.sh`.
- New full preliminary queue template, not launched: `/Users/jkeohane/GRBs/VegasJetFit/scripts/run_logejet52_prelim_queue.sh`.

## Last Touched 2026-06-24: 050525A Final-Final AMPy Comparison Repair

- Regenerated only the AMPy comparison product for:
  `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/050525A_structjet_thetav_thetac_electronp_minseed10pct_finalfinal_10temp_5000x5000_v1`
- Command:
  `PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python -u scripts/generate_postfit_products.py --results <run> --event 050525A --only-product ampy-comparison`
- Replaced `ampy_comparison.csv/.pdf/.png` in:
  `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/final_seeded_runs/26_06_08__structured_jet__viewing_core_structure_thawed__power_law_csm__seeded_final_final__10_temperature_5000x5000/050525A`
- Current approved product uses the wide horizontal difference-over-average layout, labels each bar with this-fit and Dylan values, includes both nmap values and their difference, and reports the exact data-row audit.
- Validation:
  - rendered the replacement PDF with `pdftoppm`;
  - visual inspection found no bunching, clipping, or overlapping labels;
  - current and shared CSV/PDF/PNG SHA256 hashes match;
  - data-row audit reports `N=110` for both fits.

## Last Touched 2026-06-24: Standard Ejet and Gamma0 Priors

- New standard structured-jet bounds:
  - `-3 <= log10(E_j,kin,52) <= 2`, equivalent to `10^49--10^54 erg`.
  - `log10(50) <= log10(Gamma_0) <= 4`, equivalent to `Gamma_0=50--10000`.
- Updated `scripts/build_structured_jet_ejet_configs.py` defaults to generate both bounds, including the lower `lf0` bound.
- Regenerated four canonical config families (30 TOMLs total):
  - `structured_jet_logejet52_configs_active`
  - `structured_jet_finalprod_ejetkin_configs_active`
  - `structured_jet_sbpl_logejet52_penultimate_configs_active`
  - `structured_jet_logejet52_sbpl_pair_powerlaw_csm_configs_active`
- Updated `jwk_run_thesis_reproduction_event.sh` to reject fitted log-Ejet runs whose standard energy or Gamma bounds differ. Approved one-off experiments must explicitly set `REQUIRE_STANDARD_EJET_GAMMA_PRIORS=0`.
- Existing completed/running and seeded/mode-specific configs were not rewritten. The pending `080413B` structured-jet SBPL run was not yet launched and will use the new standard bounds.
- Synced the builder, launch guard, queue templates, and canonical config families to both PCRCs and all three Pauley machines.
- Validation:
  - all 30 TOMLs have exact expected bounds and no out-of-bounds initial guesses;
  - Python and shell syntax checks passed;
  - a standard config passed the launch guard;
  - a deliberately altered `E_j_52=[-3,1.5]` config was rejected;
  - audit report: `/Users/jkeohane/GRBs/VegasJetFit/reports/standard_prior_update_20260624/README.md`.
- Same-day revision: Jonathan increased the standard upper jet-energy limit from `10^53` to `10^54 erg`; canonical configs and the launch guard now use `log10(E_j,52) <= 2`.
- Same-day Gamma revision: Jonathan increased the standard upper bound from `Gamma_0=1000` to `Gamma_0=10000`; canonical configs and the launch guard now use `lf0 <= 4`.

## Last Touched 2026-06-24: Jet-Mass Posterior and Corner Plot

- Added a derived two-sided jet-mass posterior to the standard `jet-energy` postfit product family.
- Definition, consistent with the existing swept-mass diagnostics:
  `M_j = 2 integral [(dE/dOmega)/(Gamma_0(theta) c^2)] dOmega`.
  - Top-hat reduction: `M_j = E_j/(Gamma_0 c^2)`.
  - Power-law structured jets use each sample's own `theta_c`, `k_e`, `k_g`, and core `Gamma_0`, including the angular Lorentz profile.
  - `PowerlawJetCommonSVegasDylanSpectrumModel` uses sampled `s` for both effective `k_e` and `k_g`.
- New standard plot:
  `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py::plot_jet_mass_corner`
  writes `corner_jet_mass.pdf` with `log10(E_j,52)`, `log10(Gamma_0)`, and `log10(M_j/Msun)`.
- `jet_energy_posterior.npz` now includes `Gamma_0`, `M_j_g`, `M_j_msun`, and explicit jet-mass definition/unit metadata.
- `jet_energy_summary.csv` now includes these quantities plus `units` and `definition` columns; derived rows are also appended to `summary.csv`.
- Pipeline requirements updated in:
  - `scripts/sync_results_to_drive.sh`
  - `scripts/refresh_share_products_newest_first.py`
  - current recent-run postfit/audit scripts.
- Validation:
  - analytic top-hat mass factor matches `(1-cos(theta_c))/Gamma_0`;
  - real 090424 structured-jet diagnostic produced 100000/100000 finite mass samples;
  - median test mass was `2.083956e-4 Msun`;
  - rendered `corner_jet_mass.pdf` was visually clean;
  - preview products copied to the 090424 off-axis mode Share_Folder;
  - Python/shell syntax and `git diff --check` passed;
  - updated plotting/postfit scripts compile on both PCRCs and all three Pauley hosts.
- Same-day campaign backfill:
  - ran the jet-energy product family for all 12 completed June 13 unseeded penultimate Share_Folder runs;
  - 12/12 wrote `corner_jet_mass.pdf` and updated mass posterior/summary products;
  - every run has 500000 finite positive jet-mass samples;
  - report: `/Users/jkeohane/GRBs/VegasJetFit/reports/penultimate_jet_mass_20260624_validation.csv`.
- Added campaign comparison script `scripts/plot_campaign_jet_mass_histogram.py`.
- June 13 penultimate campaign root now contains `jet_mass_posterior_histogram.pdf/.png` plus histogram data and posterior summary CSVs for all 12 GRBs.

## Last Touched 2026-06-13: 050525A log-Ejet penultimate production launch
- Production MCMC uses `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_logejet52_configs_active/050525A.toml` and `/Users/jkeohane/GRBs/VegasJetFit/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml`.
- Run label: `050525A_structjet_logejet52_penultimate_10temp_5000x5000_v1`.
- Remote host/session: `pcrc-mac-studio-2`, tmux `logejet52_050525A_penultimate_pcrc2`.
- Preflight passed; full MCMC started with `workers=14`, remote minimization disabled, Drive sync disabled.
- Lyra watcher: `/Users/jkeohane/GRBs/tmp/watch_050525A_logejet52_penultimate_20260613.sh` in tmux `watch_050525A_logejet52_penultimate_20260613`.

## Last Touched 2026-06-13: Log-Ejet Production Guard and 050922C Launch
- Added a launch-time guard to `/Users/jkeohane/GRBs/VegasJetFit/jwk_run_thesis_reproduction_event.sh`: any fitted `E_j_52` parameter with a prior must use `scale='log'`; linear-space `E_j_52` configs now fail before MCMC launch.
- Scientific convention to preserve: structured-jet production fits must sample `log10(E_j,kin,52)`, not linear `E_j_52`.
- Launched `050922C` production MCMC on `pcrc-mac-studio-1`:
  - config: `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_logejet52_configs_active/050922C.toml`
  - energy prior: `-3 <= log10(E_j,kin,52) <= 1.5`
  - result label: `050922C_structjet_logejet52_penultimate_10temp_5000x5000_v1`
  - remote tmux: `logejet52_050922C_penultimate_pcrc1`
  - launch script: `/Users/jkeohane/GRBs/VegasJetFit/logs/050922C.logejet52_penultimate_pcrc1.launch.sh`
  - remote minimization disabled; Drive sync disabled; PCRC workers set to 14.
- Added one-event Lyra watcher:
  - script: `/Users/jkeohane/GRBs/tmp/watch_050922C_logejet52_penultimate_20260613.sh`
  - tmux: `watch_050922C_logejet52_penultimate_20260613`
  - log: `/Users/jkeohane/GRBs/VegasJetFit/logs/watch_050922C_logejet52_penultimate_20260613.log`
  - behavior: waits for remote `chain.npz` and `best_fit.json`, pulls to Lyra, minimizes with 8 parallel workers, then runs standard postfit with 4 product workers.
- Validation:
  - `bash -n jwk_run_thesis_reproduction_event.sh` passed.
  - `050922C.toml` readback confirmed `E_j_52 scale='log'` and prior `[-3.0, 1.5]`.
  - PCRC-1 was idle before launch; no pre-existing local or remote `050922C_structjet_logejet52_penultimate_10temp_5000x5000_v1` result directory existed.
  - Preflight started successfully and reported valid walkers for temperature 0.
- Operational caution:
  - Do not rsync the whole `VegasJetFit/jetfit/` tree without excluding `jetfit/results/`; use targeted source-code syncs for remote workers.

## Last Touched 2026-06-14: Pauley-03 210905A Cleanup
- `210905A_structjet_logejet52_penultimate_10temp_5000x5000_v1` was safely retrieved from `pauley404-03`; a follow-up `rsync --ignore-existing` filled remote-only gaps without overwriting newer Lyra postfit outputs.
- Stale `pauley404-03` session `logejet52_210905A_penultimate_p03` was flushed after MCMC completion and Lyra pull/minimization.
- Lyra-side postfit continued from `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/210905A_structjet_logejet52_penultimate_10temp_5000x5000_v1`; density-profiles was still active at last check.

## Last Touched 2026-06-14: 131030A Gamma3000 Log-Ejet Production Launch
- Created one-off config directory `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_logejet52_gamma3000_configs_active/` for `131030A` only.
- `131030A.toml` keeps fitted `E_j_52` as log-space `[-3, 1.5]` and sets `lf0.prior.upper = log10(3000) = 3.4771212547196626`.
- Launched `131030A_structjet_logejet52_gamma3000_penultimate_10temp_5000x5000_v1` on `pauley404-03` in tmux `logejet52_131030A_gamma3000_p03` with remote minimization and Drive sync disabled.
- Added watcher `watch_131030A_logejet52_gamma3000_20260614` to pull back to Lyra, minimize with 8 workers, and run standard postfit with 4 product workers after MCMC completion.

## Last Touched (2026-06-14): 221009A Milky Way R_V Prior Support

- `build_structured_jet_ejet_configs.py` now applies a 221009A-only special case when generating log-Ejet configs: insert fitted extinction parameter `rv_milky_way` with `scale='log'` and uniform `log10(R_V_MW)` prior from `log10(2.0)` to `log10(5.0)`; fixed `ebv_milky_way=1.3021` remains separate.
- `plot/diagnose.py` includes `rv_milky_way` in `corner_csm.pdf` when fitted.
- Core likelihood path already handled the physics correctly: source-frame extinction uses `ebv_source_frame`; Milky Way foreground uses `ebv_milky_way` and fitted `rv_milky_way` if present, otherwise `R_V=3.1`.
- Smoke validation: `221009A_structjet_logejet52_mwrv_smoke_v1_preflight` passed with valid walkers `99,100,99,100,100`; `best_fit.json` contains `extinction.rv_milky_way=2.5124` and fixed `extinction.ebv_milky_way=1.3021`.

## Last Touched (2026-06-14): 221009A Fitted Milky Way R_V Production Queue

- Added/validated queue-control scripts for `221009A_structjet_logejet52_mwrv_penultimate_10temp_5000x5000_v1`:
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/221009A.logejet52_mwrv_penultimate_p02.launch.sh`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/wait_then_run_221009A_logejet52_mwrv_p02.sh`
  - `/Users/jkeohane/GRBs/tmp/watch_221009A_logejet52_mwrv_20260614.sh`
- Synced to `pauley404-02`:
  - `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_logejet52_configs_active/221009A.toml`
  - `/Users/jkeohane/GRBs/VegasJetFit/jwk_run_thesis_reproduction_event.sh`
  - the two 221009A launcher/waiter scripts above.
- Validation:
  - `bash -n` passed for the local launcher, waiter, and watcher scripts.
  - Local and remote TOML checks confirmed 221009A fits `rv_milky_way` in log space and keeps `ebv_milky_way=1.3021` fixed.
- Queue state:
  - Remote tmux `wait_221009A_mwrv_p02` is waiting behind the active Pauley-02 `130612A` production run.
  - Local tmux `watch_221009A_logejet52_mwrv_20260614` is active for retrieval, minimization, and postfit products.

## Last Touched (2026-06-15): Remote-MCMC to Lyra Post-Processing Watcher Fix

- Added `/Users/jkeohane/GRBs/VegasJetFit/scripts/cleanup_completed_remote_mcmc.sh` and synced it to `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, and `pauley404-03`.
- Purpose: after Lyra has confirmed/pulled a completed remote MCMC result (`chain.npz` and `best_fit.json`), clean stale remote tmux/wrapper/`jetfit.run` processes so dispatchers do not falsely treat the host as busy.
- Patched active log-Ejet Lyra watcher scripts in `/Users/jkeohane/GRBs/tmp/watch_*logejet52*.sh` so Lyra minimization uses the pulled sidecars explicitly: `scripts/minimize.py --results <local_run> --obs <local_run>/obs.csv --params <local_run>/model.toml ...`.
- Scientific/operational rule: any watcher that pulls remote MCMC products to Lyra must pass the local `obs.csv` and `model.toml` sidecars to `minimize.py`; otherwise data-override runs can silently fall back to default resource observations/configs.
- Restarted waiting watcher tmux sessions so queued runs pick up the patched logic: `watch_090424_logejet52_early_uvoir_20260615`, `watch_131030A_logejet52_gamma3000_20260614`, `watch_160131A_logejet52_kmin3_gamma3000_20260615`, `watch_221009A_logejet52_mwrv_20260614`, and `watch_logejet52_penultimate_runs_20260613`.
- Left `watch_220101A_logejet52_dylan_data_20260614` running because it was already inside Lyra postfit; its script file is patched for future reruns, but the active process started before this change.
- Validation: `bash -n` passed for all patched `/Users/jkeohane/GRBs/tmp/watch_*logejet52*.sh`; cleanup helper passed `bash -n` locally and on all five worker hosts.
- Queue check: `160131A` on `pcrc-mac-studio-2` passed preflight and entered full 5000+5000 MCMC after stale `220101A` remote wrappers were cleared; other restarted watchers are polling normally.
- Remaining uncertainty: `220101A` minimization had already started before this sidecar patch and should be treated cautiously if it used a data override; re-minimize with explicit `--obs <run>/obs.csv --params <run>/model.toml` if that product is used for science.

## Last Touched (2026-06-15): 140506A Gamma3000 Common-s Penultimate Queue

- Created a one-off 140506A log-Ejet production config:
  - `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_logejet52_140506A_gamma3000_sfree_configs_active/140506A.toml`
  - result label: `140506A_structjet_logejet52_gamma3000_sfree_penultimate_10temp_5000x5000_v1`
  - `lf0` prior upper is `log10(3000) = 3.4771212547196626`.
  - `s` is fitted with uniform prior `1 <= s <= 10`.
  - model name is `PowerlawJetCommonSVegasDylanSpectrumModel`.
- Added explicit one-off model class `PowerlawJetCommonSVegasDylanSpectrumModel` in `/Users/jkeohane/GRBs/VegasJetFit/jetfit/models/powerlawJetVegasDylanSpectrum.py`; it maps sampled `s` to `k_e = k_g = s` before constructing the native VegasAfterglow power-law jet.  The existing `PowerlawJetVegasDylanSpectrumModel` is unchanged and still treats `s` as bookkeeping only.
- Registered the new model in `/Users/jkeohane/GRBs/VegasJetFit/jetfit/ampy.py`.
- Created launch/watch/dispatch scripts:
  - launcher: `/Users/jkeohane/GRBs/VegasJetFit/logs/140506A.logejet52_gamma3000_sfree_penultimate.launch.sh`
  - watcher: `/Users/jkeohane/GRBs/tmp/watch_140506A_logejet52_gamma3000_sfree_20260615.sh`
  - dispatcher: `/Users/jkeohane/GRBs/tmp/dispatch_140506A_logejet52_gamma3000_sfree_next_free_20260615.sh`
- Synced the new model/factory/config/launcher to `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, and `pauley404-03`; remote `py_compile` and model-factory import validation passed on all five.
- Started local tmux sessions:
  - `dispatch_140506A_logejet52_gamma3000_sfree_20260615`
  - `watch_140506A_logejet52_gamma3000_sfree_20260615`
- Queue state at setup: all five hosts were busy, so the dispatcher is polling every 600 s.  It will launch on the first free host, preferring PCRC machines before Pauley machines.
- Watcher behavior: after remote MCMC completion, pull to Lyra, clean stale remote wrappers, minimize with explicit sidecars (`obs.csv`, `model.toml`), run parallel postfit products, and publish to the 2026-06-13 log-Ejet penultimate Share_Folder campaign.
- Validation: local `py_compile` passed for `jetfit/models/powerlawJetVegasDylanSpectrum.py` and `jetfit/ampy.py`; TOML readback confirmed model name, `lf0` upper, and `s` prior; `bash -n` passed for launcher/watcher/dispatcher.
- Remaining uncertainty: postfit derived products that read raw `k_e`/`k_g` from saved parameter dictionaries may need a follow-up patch to display/use effective `k_e=k_g=s` for this special model class; the MCMC likelihood itself uses `s` physically through the new model class.

## Last Touched (2026-06-24): Core Apples-to-Apples Jet Products

- Modified `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` to save core, wing, and total angular-profile quantities for every posterior sample.
- Core convention is `0 <= theta <= theta_c`, using the two-sided jet convention:
  - `E_j_core = 2 integral_core (dE/dOmega) dOmega`
  - `M_j_core = 2 integral_core [(dE/dOmega)/(Gamma_0(theta)c^2)] dOmega`
  - `Gamma_0_core_avg = integral_core Gamma_0(theta) sin(theta)dtheta / (1-cos(theta_c))`
- The Gamma average is solid-angle weighted, not energy weighted. For a top-hat it exactly reduces to the fitted single `Gamma_0`.
- Saved keys include `E_j_core_52`, `E_j_wings_52`, `Gamma_0_core_avg`, `M_j_core_g`, `M_j_core_msun`, and corresponding core/wing fractions.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py` now makes `corner_jet_mass.pdf` from `E_j_core_52`, `Gamma_0_core_avg`, and `M_j_core_msun`.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_campaign_jet_mass_histogram.py` now plots `M_j_core_msun`, not the full core-plus-wings mass.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/base.py` contains compact labels for the three core-derived quantities.
- Regenerated all 12 June 13 penultimate runs with:
  `/Users/jkeohane/GRBs/VegasJetFit/logs/regenerate_penultimate_jet_mass_20260624.sh`
- Validation performed:
  - `py_compile` passed for all modified Python files.
  - all 12 runs contain 500000 finite positive samples for all three core quantities.
  - all 12 `corner_jet_mass.pdf` files are nonempty.
  - rendered 050525A corner and campaign histogram were visually checked for clipping and readability.
- Campaign summary:
  `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_13__log_ejetkin_prior__structured_jet__viewing_core_structure_thawed__power_law_csm__unseeded_penultimate__10_temperature_5000x5000/jet_core_apples_to_apples_summary.csv`
- Synced the four modified postfit/plot scripts to both PCRC machines and all three Pauley machines; remote `py_compile` passed on every host.
- Extended `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_campaign_jet_mass_histogram.py` with `--quantity {mass,energy,gamma}` while preserving the original mass default and filenames.
- Generated and visually validated:
  - `jet_core_energy_posterior_histogram.pdf`
  - `gamma0_core_average_posterior_histogram.pdf`
  - matching PNG, binned-data CSV, and posterior-summary CSV files.
- Commands:
  - `/Users/jkeohane/GRBs/.venv/bin/python scripts/plot_campaign_jet_mass_histogram.py --campaign <campaign> --quantity energy`
  - `/Users/jkeohane/GRBs/.venv/bin/python scripts/plot_campaign_jet_mass_histogram.py --campaign <campaign> --quantity gamma`
- Rendered validation images:
  - `/Users/jkeohane/GRBs/tmp/pdfs/core_energy_hist/page.png`
  - `/Users/jkeohane/GRBs/tmp/pdfs/core_gamma_hist/page.png`
- Validation confirmed 12 events and 500000 posterior samples per event in both summary tables. The generalized script was synced to both PCRCs and all three Pauley hosts, where `py_compile` passed.
- Remaining uncertainties: none for these campaign histogram products.

## Last Touched (2026-06-24): Core-Matched Corner Family

- `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py` now accepts posterior-aligned derived arrays in `plot_corner`.
- `corner_core.pdf` is built in the exact order:
  `E_j_core_52`, `Gamma_0_core_avg`, `M_j_core_msun`, `n017`, `eps_e`, `eps_b/eps_B`, using log10 values.
- The full physical `corner.pdf` replaces raw `E_j_52`/`E52` and `lf0` with core energy and core-averaged Gamma, and inserts core mass after Gamma.
- `corner_energy.pdf` replaces total `E_j_52` with `log10(E_j_core_52)`.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` derives the core arrays from the full chain and applies the same deterministic posterior indices to both derived and fitted coordinates before plotting. This preserves sample-by-sample correlations.
- `/Users/jkeohane/GRBs/VegasJetFit/jetfit/run.py` also passes derived core arrays to immediate end-of-MCMC corner generation, preventing temporary old-definition corner files before Lyra postfit.
- Two-sided convention verification:
  - Core energy and mass use the same two-jet angular convention.
  - Numerical top-hat tests matched `1-cos(theta_c)` for energy and `M*c^2/E_iso=(1-cos(theta_c))/Gamma_0` exactly.
- Regenerated all standard corner products for all 12 June 13 penultimate GRBs:
  `corner.pdf`, `corner_core.pdf`, `corner_csm.pdf`, `corner_np.pdf`,
  `corner_energy.pdf`, and `corner_jet_mass.pdf`.
- Batch:
  `/Users/jkeohane/GRBs/VegasJetFit/logs/regenerate_penultimate_core_corners_20260624.sh`
  completed with `failed=0`.
- Visual checks:
  - `/Users/jkeohane/GRBs/tmp/pdfs/core_corner_new/page.png`
  - `/Users/jkeohane/GRBs/tmp/pdfs/140506_core_corner_new/page.png`
  - `/Users/jkeohane/GRBs/tmp/pdfs/full_corner_new/page.png`
  - `/Users/jkeohane/GRBs/tmp/pdfs/energy_corner_final/page.png`
- Synced `diagnose.py`, `generate_postfit_products.py`, and `jetfit/run.py` to both PCRCs and all three Pauley machines. Remote `py_compile` and import checks passed on every host.
- Remaining uncertainties: none for the core convention or the regenerated June 13 penultimate corner products.

## Last Touched (2026-06-24): Strict Core Postfit Validation and Pending Watchers

- Added `scripts/validate_core_postfit_products.py` as the canonical validation gate for core-derived postfit products.
- Patched `scripts/run_fit_and_sync.sh` so failed postfit generation or failed core validation sets a nonzero pipeline status and prevents Drive sync.
- Patched `scripts/sync_results_to_drive.sh` to require `jet_energy_posterior.npz`, rerun missing postfit products without swallowing errors, and validate core arrays/corners before copying.
- Synced and syntax-checked these scripts on `pcrc-mac-studio-{1,2}` and `pauley404-{01,02,03}`.
- Started `watch_220101A_minseed_final_core_20260624`; it will process the active Pauley-02 final run with the current Lyra pipeline and validate both local and Share_Folder products.
- Started `watch_13grb_core_histograms_20260624`; after broad unseeded 111228A is published, it will rebuild all three core histograms with exactly 13 validated GRBs.
- Commands validated:
  - `bash -n` for both watchers and both patched pipeline scripts.
  - `py_compile` for the validator locally and remotely.
  - validator passed against the completed 050525A penultimate products with 500000 samples.

## Last Touched (2026-06-24): Core Physical Sampling Parameters

- `jetfit/models/jet_energy.py` now supports:
  - `E_j_core_52 -> E_iso,0` using the two-sided core energy integral.
  - `Gamma_0_core_avg -> lf0` using the analytic inverse of the core-averaged
    normalized angular Lorentz profile.
- `jetfit/models/vegasafterglow.py` and `jetfit/models/powerlawVegas.py`
  accept the new sampled names while preserving old `E52`, `E_j_52`, and
  `lf0` configs.
- `scripts/generate_postfit_products.py` recognizes either parameterization
  and reconstructs total energy/on-axis Gamma while preserving the sampled
  core quantities exactly.
- `scripts/build_structured_jet_ejet_configs.py` now generates paired
  `E_j_core_52` and `Gamma_0_core_avg` parameters. Standard ranges are
  `[-3,2]` and `[log10(50),4]`.
- `jwk_run_thesis_reproduction_event.sh` validates both new parameters,
  rejects mixed old/new pairs, and warns for legacy total/on-axis configs.
- Generated 13 canonical future configs in
  `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_core_physical_configs_active`.
- Tests:
  - `test/models/test_core_physical_parameterization.py`: 7 passed.
  - real 050525A 5-temperature, 100-walker, 1+1 preflight passed with 95--98
    valid walkers per temperature.
  - one unrelated pre-existing `test_vdh_wind` self-absorption test remains
    4.7% from its reference value.
- The new-parameterization smoke chain was post-processed successfully:
  `validate_core_postfit_products.py` passed with 100 samples.
- Patched `jwk_run_thesis_reproduction_event.sh` to copy model, observation,
  MCMC, and log sidecars into preflight result directories as well as full-run
  directories.
- Installed pytest in the Lyra, PCRC, and Pauley project environments. The
  seven focused core-parameterization tests pass on all six machines.

## Last Touched (2026-06-25): Campaign Physical-Parameter Histograms

- Added `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_campaign_physical_parameter_histograms.py`.
- The script generates matching campaign-level posterior histogram families
  for the shared physical parameters only:
  `E_j_core_52`, `Gamma_0_core_avg`, `M_j_core_msun`,
  `E_j_core_52/(2*pi*theta_c^2)`,
  `M_j_core_msun/(2*pi*theta_c^2)`, `n017`, `eps_e`, `eps_b`, `p`, `k`,
  `theta_c`, `theta_v`, and `ebv_source_frame`.
- Core energy, core-average Gamma, and core mass come from
  `jet_energy_posterior.npz`; the remaining shared coordinates come from the
  full cold-chain posterior in `chain.npz`.
- Log-fitted parameters stay in their native log10 fit space. Core energy,
  core-average Gamma, and core mass are explicitly transformed to log10 for
  plotting. Filter offsets, host fluxes, slop parameters, `s`, and the
  221009A-only Milky Way `R_V` are intentionally excluded.
- Canonical command:
  `/Users/jkeohane/GRBs/.venv/bin/python scripts/plot_campaign_physical_parameter_histograms.py --campaign <campaign>`
- Each parameter produces PDF, PNG, binned-data CSV, and posterior-summary
  CSV products. `physical_parameter_histograms_manifest.csv` records the
  parameter, plotted scale, output stem, event count, and sample counts.
- Regenerated the June 13 unseeded penultimate campaign with 13 histogram
  families. Validation passed for 13 GRBs and 500000 samples per GRB for every
  parameter.
- The two per-solid-angle products use each posterior sample's own
  `theta_c` and Jonathan's requested two-sided small-angle denominator
  `2*pi*theta_c^2`:
  `jet_core_energy_per_solid_angle_posterior_histogram.*` and
  `jet_core_mass_per_solid_angle_posterior_histogram.*`.
- Validation performed: `py_compile`, full output/row-count audit, Poppler PDF
  rendering, and visual inspection of density, epsilon_B, k, theta_c, and
  source-frame reddening plots. No clipping or layout defects found.
- Run log:
  `/Users/jkeohane/GRBs/VegasJetFit/logs/plot_campaign_physical_parameter_histograms_20260625.log`.
- Remaining uncertainty: `2*pi*theta_c^2` is the requested small-angle
  approximation; the exact two-sided core solid angle is
  `4*pi*(1-cos(theta_c))`.

## Last Touched (2026-06-25): Minimized Core Mass vs Solid Angle

- Added reusable script:
  `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_minimized_core_mass_vs_solid_angle.py`.
- For each completed campaign GRB, the script reads the exact optimizer vector
  from `minimized/minimized.json`, derives the two-sided core ejecta mass with
  `derive_jet_energy_posterior`, and plots it against the requested
  `2*pi*theta_c^2` solid-angle approximation.
- Outputs at the campaign root:
  `minimized_core_mass_vs_solid_angle.{pdf,png,csv}`.
- The CSV also records `nmap`, `theta_c`, exact two-sided core solid angle,
  approximation/exact ratio, minimized core energy, core-average Gamma, and
  core mass per approximate steradian.
- Validation passed for all 13 June 13 penultimate GRBs. The PDF was rendered
  with Poppler and visually checked after collision-aware label adjustments.
- The scatterplot now includes posterior uncertainty bars. Horizontal bars
  span the 16th-84th percentiles of each sample's own
  `2*pi*theta_c^2`; vertical bars span the corresponding percentiles of
  `M_j_core_msun`. Markers remain the exact minimized solutions.
- Bars are drawn at their exact marginal intervals rather than forced to touch
  the minimized marker. A detached bar therefore flags a minimum outside the
  posterior central 68% interval instead of silently distorting the interval.
- The CSV includes all posterior quantiles and confirms 500000 joint posterior
  samples for each of the 13 GRBs.
- Added companion outputs:
  `minimized_core_mass_per_solid_angle_vs_solid_angle.{pdf,png}`.
  The minimized ordinate is
  `M_j_core_msun/(2*pi*theta_c^2)`. Its posterior interval is calculated from
  that ratio sample-by-sample, not by dividing independent marginal
  summaries. Both axes include 16th-84th percentile bars.
- Command:
  `/Users/jkeohane/GRBs/.venv/bin/python scripts/plot_minimized_core_mass_vs_solid_angle.py --campaign <campaign>`.

## Last Touched (2026-06-25): Core Log-Angle Campaign Pipeline Fixes

- Added campaign builder/launch/postprocess scripts:
  - `scripts/build_core_logangle_15grb_campaign.py`
  - `scripts/run_core_logangle_15grb_event.sh`
  - `scripts/run_core_logangle_15grb_queue.sh`
  - `scripts/postprocess_core_logangle_15grb_campaign.sh`
  - `scripts/resume_preempted_jobs_after_core_logangle_campaign.sh`
  - `scripts/resume_paused_sbpl_watchers_after_core_logangle_campaign.sh`
  - `scripts/wait_then_start_core_logangle_lyra_queue.sh`
- `jwk_run_vegas_jet_fit.sh`, `scripts/run_fit_and_sync.sh`, and the campaign runner now support `SKIP_MCMC_PLOTS=1` / `--skip-mcmc-plots`, preventing redundant worker-side plots before Lyra postfit.
- `scripts/plot_structjet_swept_mass_diagnostics.py` now accepts core-parameterized fits by resolving `E_j_core_52` and `Gamma_0_core_avg` to the corresponding on-axis engine values for both minimized and posterior-walker curves.
- `scripts/validate_core_postfit_products.py` now requires the standard swept-mass/Gamma PDFs and crossing CSVs for supported structured power-law CSM runs.
- `scripts/plot/visualize.py` density profiles honor `JETFIT_DENSITY_PROFILE_SAMPLES`; the 15-GRB campaign watcher sets this to 10 to keep density overlays bounded.
- Regression tests added in `test/models/test_structjet_swept_mass_core_params.py`; focused test command now passes 9 tests:
  `PYTHONPATH=$PWD /Users/jkeohane/GRBs/.venv/bin/python -m pytest -q test/models/test_core_physical_parameterization.py test/models/test_structjet_swept_mass_core_params.py`.
- Visual smoke rendered and inspected:
  `/Users/jkeohane/GRBs/tmp/pdfs/core_logangle_smoke/mass.png` and
  `/Users/jkeohane/GRBs/tmp/pdfs/core_logangle_smoke/gamma.png`.

## Last Touched (2026-06-26): Core Log-Angle Postprocess Watcher Marker Fix

- Fixed `/Users/jkeohane/GRBs/VegasJetFit/scripts/postprocess_core_logangle_15grb_campaign.sh` to skip already-published event folders using `-e "$dest/core_postfit_products.validated"` instead of `-s`; zero-byte marker files made the previous test fail.
- Marker files are now written with `validated_utc`/`event` content to avoid future ambiguity.
- Restarted the watcher; it moved from the repeated 080413B publish loop to 111228A minimization.

## Last Touched (2026-06-26): 220101A Queue Reassignment

- `220101A` was moved from Pauley-3 to PCRC-1 in the core-logangle campaign manifest.
- Pauley-3 now skips `220101A` when `reports/core_logangle_15grb_campaign/220101A_reassigned_to_pcrc1.flag` exists.
- PCRC-1's after-core-queue resume script now launches `220101A` before resuming its preempted lower-priority SBPL job.

## Last Touched (2026-06-26): Core Log-Angle Watcher Manifest Loop Fix

- Added `ssh -n` in `postprocess_core_logangle_15grb_campaign.sh::remote_complete()` to prevent SSH from consuming the manifest read loop stdin.
- After restart, the watcher pulled `080319B` and began Lyra minimization, confirming backlog processing works.

## Last Touched (2026-06-27): Core Log-Angle Campaign Completed

- Verified all 15 `*_core_logangle_unseeded_5temp_2000x2000_v1` runs have local `chain.npz`, `minimized/minimized.json`, and `core_postfit_products.validated`.
- Verified all 15 published Share_Folder event directories have `core_postfit_products.validated`.
- The postprocess watcher finished campaign histograms/scatter products and resumed the older SBPL-pair watchers.

## Last Touched (2026-06-27): Pair Power-Law CSM Add-On Pipeline

- Added `run_core_logangle_pair_powerlaw_csm_event.sh` for the `080319B`/`080413B` single-power-law CSM add-on to the completed 2000x2000 core-logangle campaign.
- Added `postprocess_core_logangle_pair_powerlaw_csm.sh`; it uses `ssh -n`, waits for remote `chain.npz`/`best_fit.json`, minimizes 8 walkers on Lyra, generates standard products, validates core products, publishes into the main campaign event folder, then rebuilds campaign-level histograms/scatter products.

## Last touched: 2026-06-27 Core-logangle power-law CSM 10-temperature queue scripts

- Added queue/event/postprocess scripts for the single-power-law CSM, core-energy/core-Gamma, log-angle campaign:
  - `run_core_logangle_powerlaw_15grb_event.sh`
  - `run_core_logangle_powerlaw_15grb_queue.sh`
  - `postprocess_core_logangle_powerlaw_15grb_10temp.sh`
  - `launch_deferred_080_core_logangle_powerlaw_10temp.sh`
- These use `/Users/jkeohane/GRBs/VegasJetFit/Ansh_Run/mcmc_settings_core_logangle_10temp_2000x2000.toml` and `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_core_logangle_powerlaw_15grb_10temp_configs_active`.
- `080319B`/`080413B` long 10-temperature runs are intentionally deferred until Jonathan reviews the earlier 5-temperature 2000x2000 single-power-law tests.

## Last touched: 2026-06-28 Dynamic dispatch default

- Added `/Users/jkeohane/GRBs/VegasJetFit/scripts/dynamic_dispatch_core_logangle_powerlaw_10temp.py`.
- Patched `run_core_logangle_powerlaw_15grb_event.sh` to enforce the central dispatch manifest before launching an event, preventing duplicate stale static-queue launches after dynamic reassignment.
- Active policy: Lyra may receive one first-batch MCMC run, but no second MCMC dispatch; reserve it for post-processing/minimization.
- Current campaign dynamic monitor runs in Lyra tmux `dynamic_dispatch_core_logangle_powerlaw_10temp`.

## Last Touched (2026-06-28): Reusable Dynamic Dispatcher

- Added `/Users/jkeohane/GRBs/VegasJetFit/scripts/dynamic_dispatch_campaign.py` as the default dispatcher template for future multi-GRB MCMC campaigns.
- Documented policy in `/Users/jkeohane/GRBs/VegasJetFit/DISPATCH_POLICY.md`: first batch fills all machines including Lyra, later events bind only when a host frees, and Lyra gets no second MCMC dispatch by default.
- The active 10-temperature campaign still uses `/Users/jkeohane/GRBs/VegasJetFit/scripts/dynamic_dispatch_core_logangle_powerlaw_10temp.py`; do not replace it mid-run unless necessary.
- Validation: Python compile passed for both dynamic dispatcher scripts; generic dispatcher dry-run returned `no_dispatches` with Lyra free but excluded after first use.

## Last Touched (2026-06-29): k[-10,3] Dynamic Campaign Launch Fix

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/dynamic_dispatch_campaign.py` so `sync_to_hosts()` creates remote parent directories before `rsync`.
- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/launch_dynamic_core_logangle_powerlaw_kminus10to3_10temp_5000.sh` to pass `--sync-path` for the campaign config directory, MCMC settings, and report directory.
- Launched first wave for `core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_v1`; remote preflights are running after manual sync of missing campaign materials.

## Last Touched (2026-06-30): Postprocess Campaign-Products Break Fix

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh` so after each event publish it checks `all_manifest_published` and breaks directly to campaign product generation.
- This addressed the 26_06_27 10-temperature campaign gap where all event folders were published but campaign-level histograms/scatter/summary products were never created.
- `bash -n` validation passed.

## Last Touched (2026-06-30): PDF/PNG Product Pair Enforcement

- Standard postfit output convention is now: every root-level PDF product should have a same-stem PNG companion.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/diagnose.py` now saves PNG companions natively for `corner.pdf`, `corner_np.pdf`, `corner_host.pdf`, `corner_core.pdf`, `corner_csm.pdf`, `corner_energy.pdf`, and `corner_jet_mass.pdf`.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py` now saves `frequencies.png` alongside `frequencies.pdf`.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` runs `ensure_pdf_png_product_pairs()` after sequential, parallel, and one-product postfit runs; this uses Poppler `pdftoppm` at practical browse resolution as a fallback for any PDF-only product.
- `/Users/jkeohane/GRBs/VegasJetFit/scripts/validate_core_postfit_products.py` now fails if any root-level PDF lacks a non-empty PNG companion.
- Backfilled missing PNG companions for the 26_06_27 and currently published 26_06_29 Share_Folder campaigns; audits found zero remaining PDF-without-PNG products and validation passed for all available event folders.

## Last Touched (2026-06-30): 10-Temp Postprocess Watcher SSH X11 Suppression

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh::remote_complete()` to call `ssh -n -x -o ForwardX11=no ...`; the previous per-host poll inherited local `ForwardX11 yes` and emitted `X11 forwarding request failed on channel 0`.
- Exact noisy call was the remote completion probe that checks `chain.npz`, `best_fit.json`, and remote `jetfit.run` processes before pulling a finished run.
- Validation: `bash -n` passed; direct patched SSH probe to `pcrc-mac-studio-1` for `130612A_core_logangle_powerlawcsm_unseeded_10temp_2000x2000_v1` returned rc 0 with zero stderr lines; `ssh -G -x -o ForwardX11=no pcrc-mac-studio-1` reports `forwardx11 no`.
- Verified the current `26_06_27__core_ejet_gamma_logangles__single_powerlaw_csm__unseeded__10_temperature_2000x2000` campaign has 15 manifest events and 15 published `core_postfit_products.validated` markers. Running the watcher with a temporary log skipped polling, regenerated campaign-level products, wrote `campaign_products.validated`, and produced zero X11 warnings.
- Remaining caveat: already-running shell processes keep the old function until restarted. At check time, the only old `postprocess_core_logangle_powerlaw_15grb_10temp.sh` process was writing `postprocess_core_logangle_powerlaw_kminus10to3_10temp_5000.log`, not the 26_06_27 log.

## Last Touched (2026-06-30): Personal GRB Pipeline Status Commands

- Added executable commands in `/Users/jkeohane/bin`, which is already on Jonathan's `PATH`:
  - `grb-watchers`: list local GRB watcher/dispatcher/queue processes and recent postprocess/dispatch/queue logs.
  - `grb-campaign-status`: summarize a campaign manifest versus published/local event products. Defaults to the current 26_06_27 15-GRB single-power-law 10-temp campaign; accepts `CAMPAIGN=... MANIFEST=...`.
  - `grb-remote-jobs [hosts...]`: list GRB run/watch/postprocess jobs on Lyra or remote hosts using quiet non-X11 SSH options. With no hosts, checks Lyra, PCRC Macs, and Pauley hosts.
  - `grb-logtail [log-name-or-path]`: tail the newest VegasJetFit log or a named log; use `LINES=N` to change the line count.
- Validation: `bash -n` passed for all four commands; smoke tests for `grb-campaign-status`, `grb-watchers`, `grb-remote-jobs lyra`, and `grb-logtail postprocess_core_logangle_powerlaw_15grb_10temp.log` produced expected output.

## Last Touched (2026-07-01): grb-campaign-status Recent-Campaign Default

- Patched `/Users/jkeohane/bin/grb-campaign-status` so, when `CAMPAIGN` is unset, it defaults to the most recently modified directory under `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs`.
- When `MANIFEST` is unset, it scores dispatch manifests under `/Users/jkeohane/GRBs/VegasJetFit/reports` against the selected campaign basename, preferring matching tags such as `kminus10to3`, `5000`, `2000`, `10temp`, and `core_logangle`.
- Explicit `CAMPAIGN=... MANIFEST=... grb-campaign-status` overrides still work.
- Validation: `bash -n` passed; no-argument smoke test selected the 26_06_29 kminus10-to-3 5000x5000 campaign and matching `core_logangle_powerlaw_15grb_kminus10to3_10temp_5000_campaign/dispatch_manifest.csv`; explicit 26_06_27 override still reported 15/15.

## Last Touched (2026-07-01): Cross-Machine zshrc Harmonization

- Replaced `/Users/jkeohane/.zshrc` with a guarded portable shell setup: path helpers, `~/bin`/`~/.local/bin`, Homebrew, X11, Codex when present, conda when present, GRBs `.venv` when present, MESA only when both `~/Software/mesa-24.08.1` and `/Applications/mesasdk/bin/mesasdk_init.sh` exist, AMRVAC only when `~/codes/amrvac` exists, CIAO/CHIANTI only when installed, completion after PATH setup, and final `rehash`.
- Installed the same `.zshrc` on `carina`, `lyra`, `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, and `pauley404-03`.
- Each remote previous file was backed up as `~/.zshrc.bak_20260701T174135Z`.
- Created `~/bin` on PCRC/Pauley hosts where it was missing so personal commands can be added and completed consistently.
- Validation: local `zsh -n` and `zsh -i` smoke passed; remote `zsh -n ~/.zshrc` and `zsh -i` smoke passed on all listed hosts. Local interactive zsh finds `grb-watchers` and `grb-campaign-status` in `/Users/jkeohane/bin`.

## Last Touched (2026-07-01): Pip-Only Shell Startup

- Removed automatic conda initialization from `/Users/jkeohane/.zshrc` and propagated the same pip/venv-only startup to `carina`, `lyra`, `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, and `pauley404-03`.
- New shell policy: use Homebrew/system command-line tools plus `/Users/jkeohane/GRBs/.venv` when present; do not put Anaconda on `PATH` by default.
- Each remote previous file was backed up as `~/.zshrc.bak_20260701T175247Z`.
- Validation: local and remote `zsh -n ~/.zshrc` passed. New interactive shells on Lyra/PCRC/Pauley resolve `python` and `pip` to `/Users/jkeohane/GRBs/.venv/bin` and `conda` is absent from `PATH`. Carina has no GRBs `.venv`, so the shell leaves `python`/`pip` unset rather than falling through to Anaconda.

## Last Touched (2026-07-01): Pauley Anaconda Removal

- Removed the Anaconda payload from `pauley404-01`, `pauley404-02`, and `pauley404-03` after confirming no running `/opt/anaconda3` or conda processes and no active `.zshrc` conda references.
- Pre-removal sizes were approximately 23G on `pauley404-01`, 27G on `pauley404-02`, and 27G on `pauley404-03`.
- `/opt/anaconda3` is now an empty 0B directory on each Pauley host. The empty directory itself remains because `/opt` is root-owned and passwordless sudo is unavailable.
- Removed user conda leftovers `~/.conda` and `~/.condarc` on each Pauley host.
- Validation: new interactive zsh shells on all three Pauley hosts resolve `python` and `pip` to `/Users/jkeohane/GRBs/.venv/bin`, `conda` is absent from `PATH`, and `VIRTUAL_ENV=/Users/jkeohane/GRBs/.venv`.

## Last Touched (2026-07-03): Campaign Worker Guard

- Checked the active `26_06_29` kminus10-to-3 campaign CPU concern: low CPU on the parent `jetfit.run` process is misleading; the multiprocessing child workers are the real load. Active runs had the intended child worker counts: Pauley events use 8 workers and PCRC events use 14 workers.
- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/run_core_logangle_powerlaw_15grb_event.sh` so, when `DISPATCH_MANIFEST` is present, it compares `WORKERS` to the manifest worker column and exits with an explicit error on mismatch.
- This prevents future manual/stale launches from silently falling back to the wrapper default `WORKERS=8` on hosts that should use more workers.
- Synced the patched runner to `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, and `pauley404-03`; `bash -n` passed on each.
- Validation: fake-event manifest with matching workers passed the worker guard and failed later at the expected missing-model check; fake-event manifest with `WORKERS=8` versus manifest `workers=14` failed immediately with the new worker mismatch error.

## Last Touched (2026-07-03): grb-cores CPU Dashboard

- Added `/Users/jkeohane/bin/grb-cores`.
- Default hosts: `lyra`, `carina`, `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, `pauley404-03`; explicit hosts may be passed as arguments.
- Reports logical CPU count, total CPU as busy-core equivalents, total host CPU percent, load averages, and top CPU-consuming process slots. On macOS this is not true physical-core process ownership; it is the practical top-N process view because ordinary user tools do not expose stable per-core ownership.
- `GRB_CORES_LIMIT=N` limits the number of displayed slots per host.
- Validation: `bash -n` passed; local, targeted remote, and all-default-host smoke tests passed. Remote probes use quiet non-X11 SSH but do not use `ssh -n` because the probe script is sent over stdin.

## Last Touched (2026-07-05): 26_06_29 kminus10to3 Campaign Publish Repair

- Fixed `/Users/jkeohane/GRBs/VegasJetFit/reports/core_logangle_powerlaw_15grb_kminus10to3_10temp_5000_campaign/dispatch_manifest.csv` so `090618` points to the completed `pauley404-03` run with `workers=8` instead of a stale duplicate `pcrc-mac-studio-1` assignment.
- Synced the corrected manifest to `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, and `pauley404-03`.
- Stopped the stale duplicate `090618` tmux/MCMC run on `pcrc-mac-studio-1`.
- Restarted the kminus10to3 postprocess watcher so it used the patched non-X11 SSH completion probe; no new `X11 forwarding request failed on channel 0` messages appeared after the restart.
- Pulled, minimized, validated, and published `090618` from `pauley404-03` into the 26_06_29 Share_Folder campaign. Core validation passed locally and in Share_Folder with `samples=500000` for `E_j_core_52`, `Gamma_0_core_avg`, and `M_j_core_msun`.
- The optional `frequencies` postfit diagnostic for `090618` ran for about 28 minutes and was manually decoupled from publication. The required core products had already passed validation; `density-profiles` had completed. Consider moving optional frequency/density regeneration out of the critical publish path for future campaigns.
- Generated campaign-level comparison products in `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000`: 18 physical-parameter histogram families plus `minimized_core_mass_vs_solid_angle.*` and `minimized_core_mass_per_solid_angle_vs_solid_angle.*`.
- Validation: `grb-status` reports `Published/validated events: 15 / 15` and `Campaign products: validated` with `validated_utc=2026-07-05T20:04:53Z`.
- Follow-up (2026-07-06): dispatched the missing `090618` `frequencies` product to `pcrc-mac-studio-2` in tmux session `grb090618_frequencies_kminus10to3`. It ran to completion after about 34 minutes and wrote `frequencies.pdf`; Lyra generated the PNG companion with `ensure_png_companion`.
- Final validation: copied `frequencies.pdf/.png` to both the local result directory and Share_Folder `090618` directory; `validate_core_postfit_products.py` passes in both locations. No `grb090618_frequencies_kminus10to3` tmux or `generate_postfit_products.py --only-product frequencies` process remains on `pcrc-mac-studio-2`.
- Remaining uncertainty: none for the missing `090618` frequency diagnostic.

## Last Touched (2026-07-07): 26_06_29 Meeting Inventory

- Audited `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000` before Jonathan's meeting.
- `grb-status` reports `15 / 15` published/validated events and campaign products validated.
- Ran `validate_core_postfit_products.py` on all 15 Share_Folder event directories; all passed with `samples=500000` for `E_j_core_52`, `Gamma_0_core_avg`, and `M_j_core_msun`.
- Inventory checked required event products including chain/config/obs, minimized JSONs, trace/corner products, jet-energy products, light curves, spread light curves, AMPy comparisons, swept-mass and Gamma/jet-break products, frequencies PDF/PNG/CSV/NPZ, density-profile products, validation markers, and sync manifests.
- Found and fixed one inventory gap: `090618` had `frequencies.pdf/.png` but was missing `frequencies_best_curve.csv` and `frequencies_data.npz` locally/in Share_Folder. These existed on `pcrc-mac-studio-2` from the completed frequency run and were rsynced into both locations.
- Final inventory result: no missing required event products, no empty required products, no PDF without PNG companion, no retired `spectral_plot.*` or `spectral_breaks_eats_weighted.csv` products, no missing campaign-level products.
- Campaign-level products present: `campaign_products.validated`, `physical_parameter_histograms_manifest.csv`, 13 histogram families with PDF/PNG/data/summary files, `minimized_core_mass_vs_solid_angle.pdf/.png/.csv`, and `minimized_core_mass_per_solid_angle_vs_solid_angle.pdf/.png`.
- Remaining uncertainty: none from this inventory pass.

## Last Touched (2026-07-07): Campaign Angle Histogram Labels

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_campaign_physical_parameter_histograms.py` so the campaign-level `theta_c` and `theta_v` posterior histogram x-axes are labeled as `log10(theta/rad)` when the fitted samples are already in log fit-space.
- The `theta_c` and `theta_v` histogram specs now use `transform="log10_fit"` so `physical_parameter_histograms_manifest.csv` and the per-plot summary CSVs do not misleadingly report `identity` scale. This does not re-transform the samples; it only documents the plotted chain-space values correctly.
- Regenerated the 26_06_29 campaign physical-parameter histograms in Share_Folder, including `core_angle_posterior_histogram.pdf/.png` and `viewing_angle_posterior_histogram.pdf/.png`.
- Validation: `py_compile` passed; regenerated histogram manifest has `theta_c` and `theta_v` rows marked `log10_fit`; `pdftotext` sees `log10(.../rad)` labels in the two regenerated PDFs.
- Remaining uncertainty: none for the campaign-level angle histogram labels.

## Last Touched (2026-07-07): 221009A Milky Way Rv Prior Rerun

- Created rerun config `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_core_logangle_powerlaw_221009A_mwprior_kminus10to3_10temp_configs_active/221009A.toml` from the 26_06_29 k[-10,3] 10-temp production config.
- Only scientific config change: `rv_milky_way` now uses `[extinction.prior] type = "milkywayrv"` instead of the previous broad uniform log prior; fixed `ebv_milky_way = 1.3021` is retained.
- Created one-row dispatch manifest `/Users/jkeohane/GRBs/VegasJetFit/reports/221009A_core_logangle_powerlaw_kminus10to3_10temp_mwprior_campaign/dispatch_manifest.csv` assigning `221009A` to `pcrc-mac-studio-2` with `workers=14`.
- Launched tmux session `grb221009A_mwprior_5000x5000` on `pcrc-mac-studio-2` with run tag `core_logangle_powerlawcsm_kminus10to3_mwprior_10temp_5000x5000_v1`.
- Remote result/log targets:
  - `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/221009A_core_logangle_powerlawcsm_kminus10to3_mwprior_10temp_5000x5000_v1`
  - `/Users/jkeohane/GRBs/VegasJetFit/logs/221009A.core_logangle_powerlawcsm_kminus10to3_mwprior_10temp_5000x5000_v1.log`
- Validation before launch: TOML/prior-factory check resolved `milkywayrv` to `MilkyWayRvPrior` with bounds `0.302..0.778`; diff versus production config shows only the `rv_milky_way` prior substitution.
- Validation after launch: remote config contains `type = "milkywayrv"`; runner started with `WORKERS=14`, `Preflight=1`, `caffeinate -is`, and `DISPATCH_MANIFEST` host/worker guard. Preflight passed all 10 temperatures with valid walkers and the full production run started with `iterations=5000`, `burn=5000`, `workers=14`.
- Remaining uncertainty: production is running but not finished; monitor with `ssh -x -o ForwardX11=no pcrc-mac-studio-2 'tmux capture-pane -pt grb221009A_mwprior_5000x5000 -S -80 | tail -80'`.

## Last Touched (2026-07-07): 160131A k<-4 Filtered Products

- Added reusable helper `/Users/jkeohane/GRBs/VegasJetFit/scripts/make_k_filtered_products.py` to create posterior-slice products from a finished run by filtering the fitted linear `k` coordinate.
- Generated `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000/160131A/k_lt_minus4_products` from local result `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/160131A_core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_v1`.
- Selection: `k < -4` on the fitted linear `k` parameter; 256,662 of 500,000 posterior samples selected (`fraction=0.513324`). Selected k range is `[-9.99986895065053, -4.00164187085603]`.
- Products include `README.md`, `selection_manifest.json`, `selected_parameter_samples.npz`, `posterior_summary_k_lt_minus4.csv`, `posterior_histograms.pdf/.png`, reduced `corner_core.*`/`corner_csm.*`, and recomputed `jet_energy_posterior.npz`, `jet_energy_summary.csv`, `corner_energy.*`, `corner_jet_mass.*`.
- Validation: `py_compile` passed for the helper; all selected samples satisfy `k < -4`; every generated PDF has a non-empty PNG companion; posterior and jet-energy summary tables are populated.
- Remaining uncertainty: no refit/minimization was done for the `k < -4` island; these are posterior-slice products from the existing chain.

## Last Touched (2026-07-07): 160131A Spectrum-Timeseries Products

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/visualize.py::plot_spectrum_timeseries()` so it writes `spectrum_timeseries.pdf`, `spectrum_timeseries.png`, `spectrum_timeseries_curves.csv`, `spectrum_timeseries_breaks.csv`, and `spectrum_timeseries_data.npz`.
- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py` to include a first-class `spectrum-timeseries` product family; future runs can use `--only-product spectrum-timeseries`, and full postfit generation includes it by default.
- Generated spectra for local result `/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/160131A_core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_v1` using the minimized/best-fit parameters.
- Copied the products into the Share_Folder event folder and into `k_lt_minus4_products`; the minimized solution has `k=-6.680851491372752`, so the best-fit spectra are consistent with the `k < -4` branch.
- Validation: `py_compile` passed; `generate_postfit_products.py --only-product spectrum-timeseries` passed and reported `pdf_png_pairs_ok`; each destination has non-empty PDF/PNG/CSV/NPZ files with 10 time slices, 500 frequencies, 5,000 curve rows, and 10 break-frequency rows.
- Remaining uncertainty: none for 160131A spectrum-timeseries products.

## Last Touched (2026-07-07): 26_06_29 Campaign Spectrum-Timeseries Backfill

- Ran `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py --only-product spectrum-timeseries` on all 15 local k[-10,3] 5000x5000 result directories:
  `050525A`, `050922C`, `080319B`, `080413B`, `090424`, `090618`, `111228A`, `130612A`, `131030A`, `140506A`, `160131A`, `171010A`, `210905A`, `220101A`, `221009A`.
- Copied each event's `spectrum_timeseries.pdf`, `spectrum_timeseries.png`, `spectrum_timeseries_curves.csv`, `spectrum_timeseries_breaks.csv`, and `spectrum_timeseries_data.npz` into the corresponding Share_Folder campaign event directory under `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000`.
- Validation: Share_Folder inventory found 75 spectrum-timeseries files total, exactly 5 files for each of 15 events. Every event has 10 time slices, 500 frequency samples, 5,000 curve rows, and 10 break-frequency rows.
- Note: model emitted `WARN: ignoring legacy call-time fts override; using smooth_fast_to_slow_transition=True.` during generation; this is expected with the current Dylan-spectrum wrappers.
- Remaining uncertainty: none for the 26_06_29 spectrum-timeseries backfill.

## Last Touched (2026-07-07): Preserve 100 Plot Solutions And Curves

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot/base.py::Profiler.draw()` so requests for 100 posterior curves draw without replacement. This affects frequency/density-style plotters that inherit `Profiler`.
- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_spread_light_curves.py` so posterior light-curve draws use `replace=False`, the spread-light-curve cache version is bumped to `3`, and the cache now preserves both the 100 posterior parameter solutions and the 100 final-walker parameter solutions.
- `light_curve_spread_out_model_data.npz` now includes `parameter_names`, `posterior_samples`, and `walker_samples` alongside the posterior/walker flux-curve stacks.
- `light_curve_spread_out_spread_metadata.json` now records `posterior_solution_count`, `walker_solution_count`, `posterior_curve_count`, `walker_curve_count`, `available_walkers`, `uses_all_final_walkers`, `posterior_sampling`, and `parameter_names`.
- The standard postfit command already invokes spread-light curves with `--ncurves 100 --walker-limit 0`; with the cache bump, future runs regenerate and must use all final walkers when 100 are available.
- Also patched legacy `/Users/jkeohane/GRBs/VegasJetFit/scripts/events/publish.py` to sample 100 unique curves if that old path is used.
- Validation: `py_compile` passed for touched production files; sampling smoke test returned 100 unique draws for a 100-curve request; regenerated 160131A spread-light-curve products and confirmed metadata/cache have `posterior_solution_count=100`, `walker_solution_count=100`, `posterior_curve_count=100`, `walker_curve_count=100`, `available_walkers=100`, `uses_all_final_walkers=true`, `posterior_samples.shape=(100,20)`, `walker_samples.shape=(100,20)`, and flux cache arrays shaped `(100,80)` for both posterior and walker stacks. Refreshed 160131A Share_Folder copies.
- Remaining uncertainty: existing spread-light-curve products for other already-published events were not regenerated in this pass; future pipeline regenerations will invalidate old caches and enforce 100 unique curves. Only non-production `scripts/sandbox/light_curve.py` still uses the old random-with-replacement pattern.

## Last Touched (2026-07-07): Campaign Density-vs-k Scatter Comparison

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_campaign_physical_parameter_histograms.py` so standard campaign comparison generation now also writes `density_n017_vs_csm_slope_k_posterior_scatter.pdf/.png`, `_data.csv`, and `_summary.csv` when runs fit both `n017` and `k`.
- The scatter uses paired posterior samples from each run's `chain.npz`, plotting `log10(n0,17)` against linear `k`; event medians are marked with crosses. The plotted/data CSV defaults to 5,000 deterministic posterior draws per event, while the summary CSV uses the full posterior for quantiles and Pearson correlation.
- New CLI controls: `--scatter-samples-per-event`, `--skip-density-k-scatter`, and `--only-density-k-scatter`. The postprocess scripts already call this generator without restrictive flags, so future campaign postprocessing gets the scatter automatically.
- Regenerated/backfilled the scatter for:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_27__core_ejet_gamma_logangles__single_powerlaw_csm__unseeded__10_temperature_2000x2000`
- Validation: `py_compile` passed; both campaign manifests have exactly one scatter row and 14 total campaign comparison rows; both scatter data CSVs have 75,000 plotted posterior rows plus header and 15 summary rows plus header; PNG visual inspection passed for the 26_06_29 product.
- Remaining uncertainty: none for the density-vs-`k` campaign comparison product.

## Last Touched (2026-07-07): Density-vs-k Scatter Error Bars

- Refined `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_campaign_physical_parameter_histograms.py` so `density_n017_vs_csm_slope_k_posterior_scatter.*` overlays median circles with horizontal and vertical 16th-84th percentile error bars, matching the campaign scatter-plot convention used by the minimized core-mass products.
- Regenerated the density-vs-`k` scatter PDF/PNG/data/summary products for both current single-power-law campaign roots:
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000`
  - `/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/26_06_27__core_ejet_gamma_logangles__single_powerlaw_csm__unseeded__10_temperature_2000x2000`
- Validation: `py_compile` passed; both campaigns still have one scatter manifest row, 75,000 plotted posterior rows plus header, and 15 summary rows plus header; visual inspection passed for the 26_06_29 PNG.
- Remaining uncertainty: none for the density-vs-`k` error-bar styling.

## Last Touched (2026-07-07): Pending Final Seeded k[-10,3] Campaign

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_core_logangle_15grb_campaign.py` so default core-logangle campaign generation now uses density-log upper bound `10.0` instead of `8.0` for `n017`; the analogous SBPL `nt` log-density ceiling is also `10.0`.
- Added `/Users/jkeohane/GRBs/VegasJetFit/scripts/prepare_final_seeded_core_logangle_campaign.py` to prepare final seeded configs without launching jobs.
- Prepared 15 pending configs in `/Users/jkeohane/GRBs/VegasJetFit/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending` from the 26_06_29 unseeded campaign. Each bounded fitted prior has `initial_guess` from `minimized/minimized.json`; `initial_sigma` is half of the posterior 16th-84th interval from `chain.npz` in fit space.
- Wrote pending operational files under `/Users/jkeohane/GRBs/VegasJetFit/reports/core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_pending`: `seed_audit.csv`, `dynamic_event_queue.csv`, header-only `dispatch_manifest.csv`, and `RUN_CARD.md`.
- Updated active core-logangle template config directories so future copied defaults use `n017.upper = 10.0`: `structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_configs_active`, `structured_jet_core_logangle_powerlaw_15grb_10temp_configs_active`, `structured_jet_core_logangle_15grb_configs_active`, and `structured_jet_core_logangle_pair_powerlaw_csm_configs_active`.
- Validation: `py_compile` passed for both scripts; `Parameters.from_toml` parsed all pending configs and all updated active template configs; 60 checked `n017` priors have upper `10.0`; pending queue has 15 events; pending dispatch manifest has only its header; no process contains final-seeded run tag `core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_v1`.
- Remaining uncertainty: per-event meeting-note adjustments have not been applied yet; do that before launching the campaign from `RUN_CARD.md`.

## Last Touched (2026-07-07): 220101A Data Guardrails for Final Seeded Campaign

- Encoded Dan's tracking-sheet M15 note for `220101A` before the pending final seeded run:
  - native HST `F775W/F125W` rows are included;
  - duplicate generic late `i/J` rows are excluded;
  - Dylan's early X-ray clump from `157.112` to `239.2112` s is included.
- Patched launch guard in `/Users/jkeohane/GRBs/VegasJetFit/jwk_run_thesis_reproduction_event.sh`: standard `220101A` launches now fail before MCMC unless the included obs set contains `F775W`, `F125W`, and at least 100 early X-ray rows between 150 and 250 s, and excludes the late generic `i/J` duplicates.
- Patched builders:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_core_logangle_15grb_campaign.py` adds/audits `F775W_offset` and `F125W_offset` for `220101A`.
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/prepare_final_seeded_core_logangle_campaign.py` adds the same offsets during pending seeded config regeneration and documents the data requirements in `RUN_CARD.md`.
- Paper/data-decision audit lives at:
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/220101A_data_decisions/README.md`
  - `/Users/jkeohane/GRBs/VegasJetFit/reports/220101A_data_decisions/220101A_corrected_data_rows_20260707.csv`
- Validation:
  - `bash -n` passed for `jwk_run_thesis_reproduction_event.sh`.
  - `py_compile` passed for both patched builders.
  - `Observation.from_csv` on `jetfit/resources/grbs/220101A/220101A.csv` reads `510` included rows and retains `F775W/F125W`.
  - `Parameters.from_toml` parsed all touched `220101A` configs and both HST offsets were present.
  - Smoke regeneration to `/tmp/grb_final_seeded_hst_xray_smoke_configs` confirmed future final-seeded prep re-creates the HST offsets without launching jobs.
- Remaining uncertainty: no products were regenerated in this pass; this only fixes inputs and guardrails for the next 220101A run.

## Last Touched (2026-07-07): 220101A Corrected-Data Unseeded Rerun Launch

- Fresh unseeded corrected-data `220101A` run launched on `pauley404-03` in tmux session `grb220101A_hst_xray_unseeded`.
- Run tag/result label: `220101A_core_logangle_powerlawcsm_kminus10to3_hst_xray_unseeded_10temp_5000x5000_v1`.
- Uses standard auto-detected obs CSV, not an override:
  `/Users/jkeohane/GRBs/VegasJetFit/jetfit/resources/grbs/220101A/220101A.csv`.
- Launch wrapper:
  `/Users/jkeohane/GRBs/VegasJetFit/logs/220101A.core_logangle_kminus10to3_hst_xray_unseeded_10temp_5000x5000_v1.pauley03.launch.sh`.
- One-row manifest/report:
  `/Users/jkeohane/GRBs/VegasJetFit/reports/220101A_core_logangle_powerlaw_kminus10to3_hst_xray_unseeded_10temp_5000_campaign`.
- Remote launch uses `WORKERS=8`, k[-10,3] 10-temp 5000x5000 MCMC settings, MCMC-only.
- Pre-launch remote validation found `510` included rows, native HST `F775W/F125W`, no late generic `i/J` duplicates, and `103` early X-ray rows from `157.112` to `239.2112` s.
- Preflight valid walkers by temperature: `97,98,99,99,100,98,100,99,98,100`; full 5000 burn + 5000 production MCMC has started.
- Hold final seeded campaign until this corrected-data unseeded 220101A run is complete and reviewed.
- Monitor:
  `ssh -x -o ForwardX11=no pauley404-03 'tmux capture-pane -pt grb220101A_hst_xray_unseeded -S -120 | tail -120'`
- Remaining uncertainty: no minimization/postfit/sync yet; do those after MCMC completion.

## Last Touched (2026-07-07): 221009A Milky Way Rv Prior Guardrail

- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_core_logangle_15grb_campaign.py` to enforce/audit `rv_milky_way.prior.type = "milkywayrv"` for `221009A` when regenerating active core-logangle configs.
- Patched `/Users/jkeohane/GRBs/VegasJetFit/scripts/prepare_final_seeded_core_logangle_campaign.py` to enforce the same prior for regenerated pending final seeded configs and document it in `RUN_CARD.md`.
- Patched `/Users/jkeohane/GRBs/VegasJetFit/jwk_run_thesis_reproduction_event.sh` so standard `221009A` launches fail before MCMC unless `rv_milky_way` uses `milkywayrv`.
- Updated local active/pending 221009A configs in:
  - `structured_jet_core_physical_configs_active`
  - `structured_jet_core_logangle_15grb_configs_active`
  - `structured_jet_core_logangle_powerlaw_15grb_10temp_configs_active`
  - `structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_configs_active`
  - `structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending`
- Added paper-trail note at `/Users/jkeohane/GRBs/VegasJetFit/reports/221009A_prior_decisions/README.md`.
- Synced the patched runner/builders/configs/report to `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`, `pauley404-02`, and `pauley404-03`; remote spot checks confirmed active and pending 221009A configs have `{'type': 'milkywayrv'}`.
- Validation: `bash -n` and `py_compile` passed; local `Parameters.from_toml` parsed all touched 221009A configs; active and final-seeded smoke regenerations preserved `milkywayrv`.
- Remaining uncertainty: no products regenerated; wait for and review the live `221009A` MW-prior rerun before final seeded launch.

## Last Touched (2026-07-13): Posterior-Informed Initial Positions

- Added `build_posterior_informed_initial_positions.py`: it draws distinct
  cold-chain samples from source `chain.npz` files, retains joint fitted
  parameter correlations, appends a newly thawed parameter, and records seed
  provenance in an NPZ file.
- `jetfit.run` now accepts `--initial-positions`, validates exact fitted-name
  ordering and `(ntemps,nwalkers,ndim)` shape, and asks the parallel tempering
  sampler to validate every supplied walker rather than silently replacing one.
  Both thesis launch scripts propagate `INITIAL_POSITIONS`.
- Validated with 090424: seed shape `(5,100,23)` from 500,000 finite source
  samples, with all 500 supplied walkers accepted in remote preflight.
  `py_compile` passed for Python changes; `bash -n` passed for launch scripts.

## Last Touched (2026-07-14): Carina Remote tmux PATH

- `dynamic_dispatch_campaign.py` now prepends
  `/opt/homebrew/bin:/usr/local/bin` to the remote command's `PATH` before
  invoking tmux. This is required for Carina because Homebrew tmux exists at
  `/opt/homebrew/bin/tmux` but non-interactive SSH does not source the shell
  startup files that add Homebrew to `PATH`.
- Validation: `py_compile` passed and a remote Carina tmux create/check/kill
  smoke test passed using the same PATH prefix.

## Last Touched (2026-07-19): 080413B Final-Final Dispatch

- `dynamic_dispatch_campaign.py` dry-run then dispatched `080413B` to
  `pcrc-mac-studio-2` with 8 workers from the final-final thawed-s manifest.
  The event is running in tmux session `grb_finalfinal_080413B` through the
  canonical `run_core_logangle_finalfinal_sthawed_5temp_event.sh` runner.
- Before dispatch, PCRC-2 received the exact final-final config and
  posterior-informed cloud, its vendored engine was rebuilt, and checksums for
  the runner, dispatcher, config, cloud, and engine defaults matched Lyra.
  The guarded preflight log is
  `VegasJetFit/logs/080413B.core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_v2.preflight.log`.
  Use `ssh -x` (or `-o ForwardX11=no`) for polling to suppress stale X11
  forwarding requests.
- `write_campaign_documentation.py` now derives the 080413B prerequisite note
  from its current manifest state, rather than retaining a hard-coded
  "blocked" sentence after dispatch. `py_compile` and regeneration of both
  local and shared reports passed.

## Last Touched (2026-07-19): Fixed-Parameter Resolution Ladder

- Added `run_vegas_resolution_ladder.py`, a no-MCMC/no-minimization diagnostic
  that holds a published final-final minimized solution fixed, changes only
  `(vegas_resolution_phi, vegas_resolution_theta, vegas_resolution_t)`, and
  writes the raw modeled fluxes, chi-squared, finite/NaN state, wall time, and
  log-flux convergence statistics relative to a very-fine reference.
- The durable queue and method note are at
  `reports/vegasafterglow_resolution_ladder_15grb_finalfinal/`. Its eight
  evaluations include the native default `(0.10,0.25,10)` and existing
  campaign setting `(0.15,0.50,15)`, bracket them with coarse/fine/very-fine
  coupled levels, then refine phi, theta, and time separately from moderate.
  Queue rows require a validated final-final minimized product; they must not
  be sent through the MCMC dynamic dispatcher.
- Validation: `py_compile` passed and a `--dry-run` against the published
  090424 final-final product validated all inputs and all eight planned levels.

## Last Touched (2026-07-19): Resolution-Ladder Smoke and Host Sync

- A real two-level 090424 run and the full eight-level ladder completed using
  the published final-final minimized solution. All 570 flux points were finite
  at every level. The eight physics evaluations took about 2.1 seconds total;
  first Python/matplotlib import adds roughly 20 seconds on a cold host. The
  very-fine `(0.30,1.0,30)` evaluation took 0.71 seconds, so these are small
  fixed-model jobs, not MCMC-scale workloads.
- Validation included complete CSV/metadata inventory checks, reference-level
  comparisons, and the invalid-level failure path. The runner correctly rejects
  an unknown resolution ID before invoking the model.
- Non-destructively synced the resolution runner, its queue/report, and this
  handoff to `pcrc-mac-studio-1`, `pcrc-mac-studio-2`, `pauley404-01`,
  `pauley404-02`, and `pauley404-03`. SHA-256 checks match Lyra for the runner
  and critical AMPy/VegasAfterglow dependencies; every remote copy passed
  `py_compile` and `--help`. Carina was unreachable and remains the only
  pending host sync.

## Last Touched (2026-07-19): Expanded Resolution Campaign Completed

- Expanded the fixed-parameter ladder to 15 levels: a coupled sequence from
  `(0.025,0.0625,2.5)` through `(0.60,2.0,60)`, plus lower and higher isolated
  phi, theta, and log-time controls around the current `(0.15,0.5,15)` setting.
  The extreme-fine level is the numerical reference; it is not an MCMC default.
- `run_vegas_resolution_ladder_campaign.sh` runs only queue rows marked
  `ready-when-finalfinal-published`, one at a time on Lyra. It accepts
  `OUT_ROOT`, `RUN_LOG`, and `MPL_CACHE` overrides for clean reruns. Do not send
  this queue through the MCMC dynamic dispatcher.
- Clean sequential campaign: `results_clean_20260719T1909Z/` contains 150
  finite evaluations (10 published final-final events x 15 levels). It was
  independently repeated after an earlier interactive-shell detachment caused
  overlapping log writes; the two passes agree exactly on chi-squared and all
  recorded convergence metrics. The clean rerun is canonical; the earlier
  `results/` folder is retained as noncanonical diagnostic history.
- Published the clean README, queue, log, and ten event bundles to
  `Share_Folder/Fits/production_runs/final_seeded_runs/26_07_16__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__moderate_resolution__5_temperature_1000x5000/numerical_resolution_ladder/`.
  Current moderate maximum deviations from extreme fine are largest for
  221009A (0.0624 dex), 130612A (0.0369 dex), and 210905A (0.0248 dex); all
  remaining currently blocked queue rows await their final-final minimization.

## Last Touched (2026-07-19): Carina Resolution-Ladder Sync

- Carina became reachable after Jonathan refreshed Tailscale. Synced the
  expanded 15-level runner, launcher, queue/report, and handoff without
  touching results, logs, or Drive products. SHA-256 checks match Lyra;
  `py_compile`, `bash -n`, and the runner `--help` smoke test passed remotely.

## Last Touched (2026-07-19): Resolution-Ladder Visualization

- Added `plot_vegas_resolution_ladder.py`. It creates per-event multi-band
  semi-transparent, color-by-resolution light-curve overlays and convergence
  panels, plus the root-level campaign convergence figure and CSV summary.
  The plotter operates only on the fixed-model output CSVs; it does not rerun
  the engine or alter fitted products.
- Generated and visually checked all ten event figures plus the campaign
  overview from `results_clean_20260719T1909Z/`. PNG and PDF versions live
  alongside each event's CSVs and are published in the shared
  `numerical_resolution_ladder/` folder. The 221009A overlay visibly separates
  coarse solutions and converges at higher resolution, consistent with its
  leading campaign-level moderate-resolution sensitivity.
- For Finder discoverability, each completed event now also contains a
  `resolution_ladder/` subfolder directly under its existing shared final-final
  product directory. The campaign overview PNG/PDF/CSV are additionally at the
  shared final-final campaign root; retain `numerical_resolution_ladder/` as
  the complete campaign archive.

## Last Touched (2026-07-19): Viewing-Angle Convergence Diagnostic

- Extended `plot_vegas_resolution_ladder.py` to read each final-final
  minimized solution's `theta_v` and `theta_c` from the result metadata and
  generate root-level `convergence_vs_viewing_angle.png/.pdf`. The x-axis is
  `theta_v` in degrees; the log y-axis is the current moderate setting's
  maximum absolute log-flux difference from `extreme_fine`; point color is
  `theta_v / theta_c`. The campaign CSV now records those geometry columns.
- Regenerated and visually checked the ten-event clean campaign plot. It does
  not show a simple monotonic trend with absolute viewing angle: the largest
  discrepancies are 221009A (0.0624 dex) and 130612A (0.0369 dex), while
  050525A is the most off-axis point and differs by only 0.0008 dex.

## Last Touched (2026-07-19): Finer-Resolution MCMC Cost and 080413B Status

- The completed 090424 expanded-prior final-final v2 run took 12.42 hours on
  PCRC-1 with the five-temperature posterior cloud, 1,000 burn iterations,
  5,000 production iterations, eight workers, and the moderate
  `(0.15,0.5,15)` resolution. The fixed-parameter ladder measured a 1.964x
  090424 cost factor for the next coupled `fine` setting `(0.20,0.75,20)` and
  a 4.456x factor for `very_fine` `(0.30,1.0,30)`. Treat 24--25 PCRC hours at
  `fine` as the directly calibrated same-protocol estimate; a shorter
  cloud-seeded equilibration would reduce it only modestly because production
  dominates the run length.
- At 2026-07-19 20:39 EDT, 080413B final-final v2 on PCRC-2 was not complete.
  Its full run was CPU-active on all eight workers, in burn-in with the latest
  persisted checkpoint containing 400/1000 burn steps; no completed chain,
  summary, minimization, or publication exists yet. Do not build its next
  posterior cloud until this run completes and Lyra post-processes it.

## Last Touched (2026-07-19): Fine-Resolution Rerun Priority Table

- Added `build_fine_resolution_rerun_plan.py`, which joins each completed
  final-final result's manifest launch time, local `chain.npz` completion
  time, and fixed-parameter ladder timings. It writes
  `FINE_RESOLUTION_RERUN_PRIORITY.md` and
  `fine_resolution_rerun_priority.csv` under
  `reports/vegasafterglow_resolution_ladder_15grb_finalfinal/`.
- The first table has ten empirically rankable events. For the next coupled
  `fine=(0.20,0.75,20)` setting, the top numerical priorities are 221009A
  (0.0624 dex; 51.6 h same protocol / 47.3 h with a conservative 500-step
  cloud continuation), 130612A (0.0369 dex; 33.9 / 31.1 h), and 210905A
  (0.0248 dex; 59.0 / 54.1 h). All estimates use each event's own measured
  cost ratio, not a universal factor.
- The remaining five events are deliberately unranked: 140506A and 080413B
  are still running moderate final-final MCMCs; 220101A and 090618 await their
  prior final-seeded results; 111228A remains under scientific review. At
  2026-07-19 20:58 EDT, 140506A was CPU-active on all eight Pauley-03 workers
  at production 1300/5000.

## Last Touched (2026-07-19): 090424 Prototype Runtime Clarification

- The preserved Share_Folder product at
  `Fits/production_runs/final_seeded_runs/26_07_14__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__5_temperature_1000x5000/090424/`
  is the original final-final thawed-`s` v1 prototype. It used the same
  moderate `(0.15,0.5,15)` resolution, five temperatures, 1,000+5,000
  iteration schedule, and a posterior-informed seed cloud, and completed in
  9.14 h on PCRC-1 with 15 workers.
- Do not substitute that number for the current priority table's 090424 v2
  runtime. The replacement v2 has the consolidated expanded bounds
  (`E_j` lower -4 rather than -1, density -6 rather than -5, `eps_e` -6
  rather than -4, `p` upper 3.5 rather than 3, thawed `s` lower 0.1 rather
  than 2) and was run with 8 workers; its measured moderate wall clock is
  12.42 h. The v1 result remains a useful same-grid, higher-worker sanity
  check, not the forecast baseline for the present campaign.

## Last Touched (2026-07-19): 090424 v2 Cloud-Seed Confirmation

- Verified that the completed and published 090424 v2 result is already the
  requested ordinary final-final moderate-resolution run, not the prototype:
  `jetfit/results/090424_core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_v2/`.
  Its persisted initial-position file is byte-for-byte provenance-equivalent
  to `initial_positions/finalfinal_sthawed_5temp/090424.npz`: `(5,100,23)`
  positions, 500,000 source samples, seed 90424, sourced from the July 7
  final-seeded 090424 product. It completed MCMC 2026-07-17 00:08 EDT,
  minimized, and published/validated at 01:01 EDT.
- Do not launch a duplicate moderate 090424 v2 run. The next distinct 090424
  decision is a deliberately finer-resolution rerun, not another moderate
  cloud-seeded final-final run.

## Last Touched (2026-07-19): Final-Seeded Review Candidates

- Verified the current July 7 final-seeded products for 220101A, 090618,
  111228A, and 080413B each have a completed chain, minimized solution,
  summary, full postfit products, and validation marker in Share_Folder. Their
  remote MCMC-only directories lack `summary.csv` by design; Lyra owns the
  postprocessing copy, so that is not an incomplete-run signal.
- Review before changing the final-final manifest: 220101A (corrected HST plus
  early-X-ray final seed) and 090618 (newly completed final seed). 111228A is
  the explicit scientific-review hold because of the swept-mass detail-grid
  anomaly and suspect seed. 080413B's high-resolution final seed was published
  2026-07-19 and is reviewable too, but its cloud was already approved and the
  final-final run has started. The `blocked-final-seeded-in-progress` labels
  for 220101A/090618 are stale scheduling markers, not evidence that their
  final-seeded products are still running; leave them blocked until Jonathan
  reviews/approves the products, then update the manifest deliberately.

## Last Touched (2026-07-19): 111228A Mass-Grid Interpretation

- Jonathan's current interpretation is that the odd 111228A swept-mass/grid
  appearance is likely a plotting/scaling artifact: a quantity fell to zero
  unphysically in a log-style display, making the panel look anomalous. Do not
  characterize this as a physical zero, a failed posterior, or a bad seed
  unless the underlying model-grid arrays themselves contain finite zeros.
- Before using the plot as a scientific gate, audit the raw mass-grid values,
  masks, and log-axis clipping/normalization. The final-final 111228A manifest
  row remains held pending that targeted plot-data check and Jonathan's review;
  it is not rejected on the basis of the current visual artifact alone.

## Last Touched (2026-07-21): Safe 090618 Checkpoint Return

- Corrected `watch_090618_checkpoint_migration_to_pcrc.sh`: PCRC availability
  now means no `jetfit.run` on the host, rather than no run with the same tag.
  The previous test allowed 090618 to migrate onto PCRC-1 while 220101A was
  already present, which overcommitted the 16-core host after both jobs were
  resized to 15 workers.
- Returned 090618 from its verified PCRC-1 production checkpoint (1300/5000)
  to Pauley-02, preserving the prior 200-step destination copy under a
  timestamped sibling directory. It now resumes as tmux
  `grb_finalfinal_090618` with 8 workers. The main final-final manifest and
  corrected watcher were synced to PCRC-1/2 and Pauley-01/2/3; `bash -n`
  passed for the watcher.

## Last Touched (2026-07-22): Finished-Run and Dispatcher Repairs

- `220101A` and `140506A` completed their moderate final-final MCMCs; the
  fine-resolution `221009A` chain also completed. While postprocessing
  220101A, the mandatory ladder plotter failed because
  `read_spread_flux_cache()` gained an `input_signature` requirement. Updated
  `plot_vegas_resolution_ladder.py` to compute and pass
  `cache_input_signature(source)`; `py_compile` passed and the 220101A ladder
  PNG/PDF products were regenerated successfully.
- Fixed a false-busy dispatcher defect in `dynamic_dispatch_campaign.py`.
  With `--busy-pattern jetfit.run`, the former grep pipeline matched itself
  and blocked every host. It now enumerates real `jetfit.run` PIDs and uses
  an in-shell match on each command, with the pattern base64 encoded to keep
  it out of the process scan. A dry run correctly identified PCRC-1, then
  launched the approved 130612A fine run there with 15 workers at
  2026-07-22T13:09:09Z. Both changed scripts were synced to PCRC-1/2 and
  Pauley-01/2/3.

## Last Touched (2026-07-22): Per-Event Decision Records

- Future refinement campaigns use a durable `event_decision_records.json` in
  the campaign report directory. It snapshots the relevant tracking-sheet
  notes, the ladder-derived refinement rationale, selected grid, full-cloud
  seed, and required post-fit decision loop before dispatch.
- `dynamic_dispatch_campaign.py --decision-records FILE` validates that every
  queued event has a record, syncs the file, and passes it to the runner.
  `run_core_logangle_finalfinal_sthawed_5temp_event.sh` invokes
  `stage_event_decision_record.py` before sampling, so the event's
  `decision_record.json` travels from remote results through Lyra publishing
  into the Share_Folder product.
- `write_campaign_latex_summary.py` renders a `Decision Record and
  Tracking-Sheet Notes` page at the beginning of each published GRB subsection
  when that JSON is present. `130612A` is the reference implementation:
  `reports/core_logangle_powerlaw_130612A_finalfinal_sthawed_fine_5temp_500x3000_campaign/event_decision_records.json`.
  Its current PCRC-1 run was already started, so the record was staged and
  verified manually on the remote result directory; later launches get it
  automatically.

## Last Touched (2026-07-22): Post-Processing Watchdog

- `supervise_postprocess_session.sh` keeps a Lyra post-processing tmux session
  available after a recoverable script failure. It checks every event in the
  manifest for `core_postfit_products.validated`, exits only after all are
  published, and otherwise restarts the configured starter when its watcher
  session is absent. It never stops or restarts an MCMC session.
- Active supervisors: `supervise_postprocess_finalfinal_sthawed_lyra` for the
  July 16 15-GRB final-final campaign and
  `supervise_postprocess_130612A_finalfine_lyra` for the one-event fine
  continuation. Both poll every 60 seconds. This protects the incremental
  report/publish path while Jonathan is away from the terminal.

## Last Touched (2026-07-22): Refinement Launch Audit

- Corrected the decision-record lifecycle: the event runner now only validates
  `EVENT_DECISION_RECORDS`, and `jwk_run_thesis_reproduction_event.sh` stages
  `decision_record.json` after `CLEAN_INCOMPLETE` has removed any stale partial
  result directory and before preflight/MCMC begins. This prevents a safe
  restart from deleting the approved scientific rationale.
- `dynamic_dispatch_campaign.py` now validates a decision record only for an
  event it is about to dispatch, rather than demanding records for old,
  completed, or already-owned manifest rows. Thus legacy rows cannot block a
  newly approved refinement, while every new launch still requires its record.
- Validation: `bash -n` for both launchers and `py_compile` for the dispatcher
  passed locally and on PCRC-1/2 and Pauley-01/2/3. The revised launcher stack
  was rsynced to all five hosts. A dry dispatcher poll reported no unassigned
  approved fine event, so it made no unintended launch.

## Last Touched (2026-07-22): Retroactive July 16 Decision Records

- `backfill_standard_finalfinal_decision_records.py` creates an explicitly
  retrospective, standardized decision snapshot from a final-final manifest
  and `campaign_metadata.json`. It records the common full-cloud seeded,
  expanded-prior, thawed-`s` protocol; host/worker allocation; tracking-sheet
  row; known data/configuration exceptions; and the required post-fit ladder
  decision loop. It does not claim to reproduce a contemporaneous verbatim
  tracking-sheet note.
- Backfilled all 15 records into
  `reports/core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_1000x5000_campaign/event_decision_records.json`
  and the July 16 Share_Folder campaign root. Individual records were staged
  into all 12 currently published event directories, all local completed
  result directories, and the two active remote chains (`080413B` on PCRC-2,
  `090618` on Pauley-02). `140506A` is staged locally and will carry its record
  when Lyra publishes it.
- Rebuilt the July 16 partial meeting book with 12 decision-record sections.
  All central records contain the required fields; the book compiled without
  decision-section overfull warnings. The new helper was rsynced and compiled
  on PCRC-1/2 and Pauley-01/2/3.

## Last Touched (2026-07-22): Live Status Correction

- `~/bin/grb-status` now resolves a method report's `Publication destination`
  relative to `Share_Folder` (the documented `Fits/...` convention), while
  accepting either presence or absence of a trailing period. Before this fix,
  the active 130612A fine campaign fell back to the July 16 folder and was
  falsely shown as published. `grb-status` now correctly shows `0 / 1` until
  the fine run finishes and Lyra validates/publishes it. The executable was
  syntax-checked and rsynced to PCRC-1/2 and Pauley-01/2/3; Carina was offline.

## Last Touched (2026-07-22): Per-GRB Resolution Follow-Up Recommendations

- The July 16 campaign now has
  `FINE_RESOLUTION_FOLLOWUP_RECOMMENDATIONS.md` and the machine-readable
  `comparison_plots/fine_resolution_followup_recommendations.csv`. Both cover
  all 15 manifest events and distinguish approved/running continuations,
  science-review holds, deferred active MCMCs, and production-adequate cases.
- Recommended new continuations: `140506A` direct ultra-fine
  `(0.40,1.333,40)` only after confirming its localized excursion is
  scientifically relevant; `210905A` very-fine `(0.30,1.00,30)` with its
  physically selected low-p cloud; `111228A` very-fine `(0.30,1.00,30)` only
  after swept-mass scientific review. `130612A` is currently running its
  approved `(0.20,0.667,20)` fine continuation. `221009A`'s fine MCMC is
  complete but its dedicated postprocessor stopped on the formerly fixed
  resolution-cache signature API change; finish the repaired postfit/ladder
  before deciding whether its `(0.30,1.00,30)` next step is needed.
- `080413B` and `090618` are explicitly deferred until their current
  postfit/ladders complete. The remaining seven stable production cases plus
  `220101A`, `160131A`, and `090424` have no finer MCMC recommendation absent
  a separate scientific reason. CSV validation confirmed exactly 15 unique
  rows with a non-empty recommendation for every manifest event.

## Last Touched (2026-07-22): 140506A Approved Ultra-Fine Continuation

- Jonathan approved the ladder-based `140506A` follow-up on PCRC-2. The new
  one-event campaign is `26_07_22__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__ultrafine_resolution_140506A__5_temperature_500x3000`.
  It uses `(phi,theta,time)=(0.40,1.333333,40)`, 5 temperatures, 100 walkers,
  500 burn-in, 3000 production, and 15 PCRC workers.
- Crucially, `initial_positions/finalfinal_sthawed_ultrafine_5temp/140506A.npz`
  was drawn from the completed current July 16 final-final chain (500,000
  finite samples; 26 matching fitted parameters), not the old pre-campaign
  seed file. `build_posterior_informed_initial_positions.py --new-parameter ''`
  now supports this same-parameter cloud transfer. The structured-config
  builder accepts explicit Vegas resolution controls for future refinements.
- Decision record, queue, manifest, campaign README/method report, dynamic
  PCRC-2 dispatcher, Lyra-only postprocessor, and its supervisor are active.
  The one-step 15-worker preflight began at `2026-07-22T23:26:42Z`; comparable
  PCRC preflights can take roughly 14 minutes, so do not treat initial worker
  spawning as a failure. Production begins automatically only after all
  preflight walkers evaluate validly.

## Last Touched (2026-07-22): 140506A Memory-Safe v2 Restart

- The v1 15-worker PCRC-2 preflight did **not** show a model, cloud, or walker
  failure: all 500 cloud-seeded positions initialized validly, then PCRC-2
  kernel-panicked. Its panic diagnostics recorded watchdog starvation, a 100%
  full memory compressor, and 47 swapfiles. Treat this as a host resource
  incident, not a scientific or numerical rejection of the approved grid.
- Restart tag is
  `core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_ultrafine_5temp_500x3000_v2`.
  It preserves the same data, expanded priors, thawed-`s` model, full July 16
  posterior cloud, `(phi,theta,time)=(0.40,1.333333,40)`, 500 burn-in, and
  3000 production iterations, while deliberately capping **this one job** to
  8 PCRC-2 workers via `--allow-worker-policy-override`. The normal PCRC
  15-worker policy remains unchanged.
- `reports/core_logangle_powerlaw_140506A_finalfinal_sthawed_ultrafine_5temp_500x3000_campaign/restart_attempts.md`
  is the canonical incident/recovery record. It, the v2 decision record, and
  refreshed `README.md`, `CAMPAIGN_METHOD_REPORT.md`, and metadata were copied
  to the matching July 22 Share_Folder campaign. Both v2 launcher scripts pass
  `bash -n`; the dispatcher dry-run selected PCRC-2 with 8 workers; live v2
  preflight began at `2026-07-23T03:13:44Z` and initially showed 95% free host
  memory with zero swap activity.

## Last Touched (2026-07-23): 111228A Very-Fine Continuation

- Launched `111228A` on idle PCRC-1 at `2026-07-23T13:33:03Z` with the
  standard 15 PCRC workers. The run tag is
  `core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_veryfine_5temp_500x3000_v1`;
  the selected coupled grid is `(phi,theta,time)=(0.30,1.00,30)`.
- The cloud at
  `initial_positions/finalfinal_sthawed_veryfine_5temp/111228A.npz` has
  finite shape `(5,100,34)` and was copied from the prepared refinement queue.
  Its exact dedicated TOML is in
  `structured_jet_core_logangle_powerlaw_111228A_finalfinal_sthawed_veryfine_5temp_configs/`.
- `start_dynamic_dispatch_111228A_finalveryfine_500x3000_lyra.sh`,
  `start_postprocess_111228A_finalveryfine_500x3000_lyra.sh`, and
  `supervise_postprocess_111228A_finalveryfine_lyra` provide dispatch,
  Lyra-only post-processing, and recovery supervision. `bash -n` and a
  dry-dispatch passed before launch; the remote tmux session is in its
  guarded 1+1 preflight.
- Shared documentation is under
  `Share_Folder/Fits/production_runs/final_seeded_runs/26_07_23__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__veryfine_resolution_111228A__5_temperature_500x3000`.
  The master refinement queue marks this row `dispatching`.

## Last Touched (2026-07-23): 080413B Ladder Decision

- `080413B` completed its July 16 post-fit, fixed-minimized-solution
  resolution ladder, validation, publication, and 14-GRB meeting-book refresh
  overnight. The previous `postfit_gate` was stale.
- The production grid `(0.15,0.50,15)` has p95/max absolute log10-flux shifts
  of `0.01387/0.02407` dex versus the extreme-fine reference. The first
  coupled fine grid `(0.20,0.666667,20)` has `0.00678/0.00904` dex, satisfying
  the existing `0.01` dex p95-and-maximum refinement threshold. The master
  queue now marks `080413B` as `prepared` for that fine continuation.
- Staged
  `structured_jet_core_logangle_powerlaw_14grb_finalfinal_sthawed_resolution_refinement_5temp_configs/080413B.toml`
  and `initial_positions/finalfinal_sthawed_resolution_refinement_5temp/080413B.npz`.
  The cloud is finite `(5,100,28)` and its names exactly match the target
  model's 28 fitted parameters. The queue, decision record, audit CSV, TOML,
  and cloud are copied to the July 22 shared refinement-queue folder.

## Last Touched (2026-07-29): Measured Placement Correction

- `080413B` is no longer Lyra-only/high-memory. A warm 15-worker PCRC-1 pool
  measured 21.97 GiB aggregate RSS on 48 GiB (46%) with all workers active;
  it is CPU-heavy normal-memory work and is running on PCRC-1 at 15 workers.
- `dynamic_dispatch_campaign.py` now rejects a `lyra_only` constraint unless
  its decision record provides a factual `memory_evidence` record from a warm
  pool or host-memory incident. This prevents a grid label, CPU load, or an old
  eight-worker default from becoming a fleet-wide placement rule. `140506A`
  ultra-fine remains the specific measured PCRC memory exception at 8 workers.

## Historical Note (2026-07-23): Resource-Aware Scheduling Evaluation

- Hardware inventory: Lyra is an M1 Max with 64 GiB/10 logical CPUs; each
  PCRC is an M4 Max with 48 GiB/16 CPUs; each Pauley is an M1 Max with
  32 GiB/10 CPUs.  PCRC has more total cores but slightly less RAM per CPU
  than Pauley, so core count alone is not a valid placement rule.
- `scripts/grb_host_capacity.py` (wrapped by `~/bin/grb-capacity`) reports
  live memory headroom, spawned-MCMC worker RSS, and a conservative proposed
  job admission estimate.  It uses 1.5/3.0/5.0 GiB per worker for
  normal/high/ultra classes, 4 GiB parent overhead, and a 30% host reserve.
- `RESOURCE_SCHEDULING_POLICY.md` is the current placement policy.  New
  high-memory jobs are Lyra-only at 8 workers when no Lyra post-processing is
  active; ultra jobs use the same policy, otherwise an exclusive 8-worker
  PCRC. `dynamic_dispatch_campaign.py --lyra-only-events EVENT,...` enforces
  that manifest-level exception while keeping ordinary jobs off Lyra after its
  first dispatch.
- At that time `080413B` was provisionally classified `high`; this was later
  retired after the 2026-07-29 15-worker PCRC-1 warm-pool measurement. Do not
  reuse this historical classification for future placement.
- `postprocess_core_logangle_powerlaw_15grb_10temp.sh` now writes a per-watcher
  live PID marker in `logs/postprocess_activity/` only while it is actually
  minimizing/generating/ladder-testing/publishing an event. The generic
  dispatcher ignores stale markers and holds a `--lyra-only-events` entry while
  a live marker exists. The four currently idle Lyra post-processing watchers
  were restarted on 2026-07-23 to load this behavior; no MCMC was stopped.
- Standard host tier: Lyra is reserved for post-processing and high/ultra-RAM
  runs; PCRC receives long CPU-bound and historically slow GRBs; Pauley receives
  normal runs with reasonable estimated wall-clock time. Apply this alongside
  the `grb-capacity` admission check, not as a replacement for it.
- `start_supervise_grb_operations_hourly_lyra.sh` runs the hourly Lyra tmux
  fleet audit. Its log is `logs/grb_operations_hourly.log` and includes core
  use, high-memory capacity, post-processing activity markers, and the two
  resource-aware refinement session health checks.

## Last Touched (2026-07-31): Prior-Bound Corners and GRB 090424 Controls

- `scripts/plot/diagnose.py` now writes `corner_prior.pdf/.png`: an all-fit-
  physical-parameter corner in the native coordinates with every axis pinned
  to its explicit fit prior. `corner.pdf/.png` is the companion compact
  posterior-focused (zoomed) diagnostic. The prior version never silently
  falls back to automatic ranges, because that would conceal hard-boundary
  contact. `write_campaign_latex_summary.py` places the prior plot immediately
  before the zoomed plot; validation, sync, and product-style versioning require
  the new product. `replot_corners_with_gamma.py` is the validated-product
  backfill entry point; use it from the VegasJetFit root with
  `PYTHONPATH="$PWD" python scripts/replot_corners_with_gamma.py --root ../Share_Folder/Fits/production_runs`.
- The 090424 all-UV final-final continuation is live on PCRC-1 at 15 workers:
  run tag `core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_alluv_v2`.
  Its initializer `initial_positions/090424_alluv_final_seeded_finalfinal_sthawed_5temp.npz`
  is `(5,100,23)` and derives from the completed all-UV 10-temperature
  final-seeded v2 chain. It uses the expanded-prior, thawed-s 5-temperature
  config and the all-UV/no-early-X-ray override.
- `scripts/make_090424_early_xray_test_override.py` creates the controlled
  comparison CSV `obs_overrides/090424_early_uvoir_included_with_early_xray.csv`.
  It changes exactly 144 X-ray integrated-flux rows (91.1323--247.071 s) from
  excluded to included; the all-UV/no-early-X-ray CSV is otherwise unchanged.
  The dedicated unseeded test is live on Pauley-1 at 8 workers with tag
  `core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_with_early_xray_v1`.
  `ALLOW_090424_EARLY_XRAY_TEST=1` is a required explicit opt-in in the normal
  event runner, so future ordinary 090424 runs keep their early-X-ray exclusion.
- `start_postprocess_090424_early_xray_unseeded_test_lyra.sh` watches that
  test and uses the `PUBLISH_EVENT_SOURCE`/`PUBLISH_EVENT_NAME` mapping added
  to the common postprocessor to publish only to
  `26_06_29.../090424_with_early_xray`, never overwrite canonical `090424`.
  It was syntax-checked and started in tmux session
  `postprocess_090424_early_xray_test`.
- `backfill_prior_bound_corners_and_meeting_books.sh` regenerates the new
  corner pair for all validated shared results and then rebuilds the campaign
  books at low scheduling priority. Its tmux session is
  `grb_prior_bound_corner_backfill`; it was deliberately SIGSTOP-paused on
  2026-07-31 because Lyra had no spare CPU capacity. Resume only when the live
  MCMC pool has released capacity: `pkill -CONT -f replot_corners_with_gamma.py`.
- The early-X-ray experimental branch is now fully serially queued without a
  manual-review gate. `supervise_090424_early_xray_followups.sh` (tmux session
  `supervise_090424_early_xray_followups`) waits for each local validated
  upstream result, builds its correlated cloud, dispatches the next stage, and
  starts a dedicated Lyra postprocessor. It advances from unseeded to 10-temp
  final-seeded (Pauley tier, 8 workers) to final-final thawed-s (PCRC tier,
  15 workers). All experimental products publish as `090424_with_early_xray`.
  The final-final runner also now requires the explicit
  `ALLOW_090424_EARLY_XRAY_TEST=1` opt-in to use the experimental observation
  override; ordinary canonical 090424 runs remain no-early-X-ray by default.

## Last Touched (2026-08-03): Independent Optional-Physics Sensitivity Tests

- `scripts/compare_optional_physics_campaign.py` is the fixed-parameter entry
  point for testing VegasAfterglow options independently. Every family starts
  from the unchanged minimized solution; options are never stacked and these
  are sensitivity diagnostics, not refits or posterior model comparisons.
- `jetfit/models/powerlawVegas.py` now exposes backward-compatible controls for
  `xi_e`, SSC, Klein-Nishina corrections, CMB cooling, reverse radiation,
  ejecta duration, and magnetar-like energy injection. The defaults exactly
  reproduce the prior model. `powerlawVegasDylanSpectrum.py` accepts a
  diagnostic jet-family override for Gaussian/top-hat comparisons, and
  `vegas_resolution.py` passes optional reverse radiation to the native model.
- The July-16 15-GRB campaign now has per-event products under
  `<GRB>/physics_feature_comparisons/<feature>/` and campaign products under
  `physics_feature_comparisons/`. Stable families completed for all 15 GRBs:
  SSC/KN, `xi_e`, CMB cooling, energy injection, and jet profile. Each event
  family has PNG/PDF light curves and diagnostics plus CSV/JSON provenance.
- Energy injection uses `L=L0(1+t/t0)^-q`, `t0=10^4 s`, `q=2`, and integrated
  injected energies of 0.1 or 1 times the initial on-axis isotropic-equivalent
  energy. Reverse-shock trials use durations 1/10/100 s with reverse
  microphysics matched to the forward shock.
- Reverse shock is not campaign-robust: five events completed without native
  ODE warnings, 080413B completed with warning-tainted cells, and 111228A plus
  130612A repeatedly hit the 100000-step native safeguard across many cells.
  The remaining seven trials were intentionally deferred. Consult
  `physics_feature_comparisons/reverse_shock_feasibility.csv`; campaign plots
  include only `completed_clean` reverse-shock rows.
- Validation: all 75 stable event-feature directories contain the eight
  required nonempty files; all expected summary counts/statistics are finite;
  campaign aggregation has 153 scenario rows; explicit optional-off versus
  historical-default 090424 arrays are exactly equal with zero statistic
  change; `pytest -q test/models/test_core_physical_parameterization.py`
  passed 7/7; `py_compile` and `git diff --check` passed. The vendored native
  `pymodel.cpp` was rebuilt during diagnosis but ends with no source diff.

## Last Touched (2026-08-03): Student Multiwavelength Data Standard

- Future student GRB projects should deliver calibrated, provenance-traceable
  multiwavelength observations in the canonical VegasJetFit format, not only a
  literature spreadsheet. Required deliverables are a source manifest, raw and
  converted values, canonical observation CSV, audit report, and reproducible
  conversion script.
- Use Poonam Chandra and Dale Frail (2012), HEASARC `RSSGRBAG` / CDS
  `J/ApJ/746/156`, as the baseline radio catalog: 304 GRBs, 2,995 detections and
  upper limits, 0.6--660 GHz, through 2011. Supplement later data from refereed
  machine-readable tables and GCNs, then use VLA/ATCA/ALMA/other raw archives
  only for verification or an intentional re-reduction.
- Radio rows must retain upper-limit confidence, frequency and bandwidth,
  telescope/configuration, calibration/systematic state, host subtraction,
  scintillation warning, citation/table/row, inclusion flag, and rationale.
  Preserve raw reported values alongside every fitting conversion; never
  silently transform or discard measurements.

## Last Touched (2026-08-11): GRB 090424 Common-Data Fit Comparison

- Added `scripts/compare_090424_data_fit_branches.py`. It evaluates the
  canonical no-early-X-ray synchrotron solution, the included-early-X-ray
  synchrotron solution, and the included-early-X-ray SSC+KN solution against
  one evaluation-only copy of the same 751-row observation table. It does not
  refit or alter any campaign result.
- Outputs live in the SSC+KN campaign's `comparison_plots/`: pointwise and
  per-dataset CSVs, provenance JSON, a full measurement-group overlay, raw
  measurement-error diagnostics, a time-resolved early-X-ray comparison, and
  a short Markdown interpretation. Every plot is written as PNG and PDF.
- `nmap` is `-2 * max(log posterior)` (`jetfit/run.py`), so lower/more negative
  is better. On the identical included dataset, SSC+KN has nmap `-29605.312`
  versus `-29415.599` for synchrotron, an improvement of about 190 with the
  same number of fitted coordinates. Do not reverse this sign in future
  comparisons.
- The improved posterior does not make the early-X-ray morphology adequate.
  Over 91--247 s the observed log-log slope is `-1.77`, versus `-0.93` for the
  included-data synchrotron fit and `-1.30` for SSC+KN. SSC+KN predicts a
  median 0.70 of the observed flux in the earliest time quartile (about 0.55
  for the first ten points). Slop-weighted RMS alone hid this shape failure;
  use the raw model/data and quoted-error diagnostics as well.
- Updated `scripts/write_campaign_latex_summary.py` with specific captions and
  one-full-page treatment for these dense branch-comparison figures. Rebuilt
  and visually inspected the 29-page SSC+KN `campaign_meeting_summary.pdf`;
  comparison pages 27--29 are legible and contain all fitted measurement
  groups, including the two X-ray spectral-index measurements.
- Validation: the comparison script ran cleanly with the root `.venv`; CSV
  counts are 751 common points per fit; standalone PNGs were inspected; the
  meeting book compiled with Tectonic and its final pages were rendered with
  Poppler for visual inspection. Remaining scientific uncertainty: SSC+KN is
  strongly preferred within these fitted models but uses a qualitatively
  extreme parameter solution, so the early interval should still be treated
  as a likely additional flare-like component pending explicit model
  comparison or a model that represents both components.

## Last Touched (2026-08-11): GRB 090424 Early-X-Ray Branch Retired

- At Jonathan's direction, stopped the completed/stale tmux supervisor
  `supervise_090424_early_xray_followups` and moved every active early-X-ray
  090424 branch into a dated trash destination (`2026-08-11_early_xray_retired`):
  the June-29 unseeded branch, July-07 final-seeded branch, July-16 final-final
  branch, and the complete August-03 SSC+KN campaign. The corresponding four
  local `jetfit/results/*with_early_xray*` result directories were retired too.
- Deliberately retained
  `090424_core_logangle_powerlawcsm_kminus10to3_early_uvoir_noearlyxray_10temp_5000x5000_v1`;
  despite its matching words, it is the canonical all-UV result that excludes
  the early X-rays. Also retained the unrelated `220101A_no_early_Xray` branch.
- Rebuilt the three surviving parent meeting books with canonical titles. The
  July-07 and July-16 books each report 15/15 validated GRBs and contain no
  `090424_with_early_xray` references. The June-29 book reports all 18 active
  validated directories, including its other historical non-early-X-ray
  variants, and likewise contains no retired branch reference.
- Final active-tree and process audits found no early-X-ray 090424 campaign,
  result, watcher, or supervisor. Trash contents were not reopened or modified
  after the moves.

## Last Touched (2026-08-28): Manuscript-Only Machine-Neutral Resolution Figures

- `plot_vegas_resolution_ladder.py` now accepts `--publication-labels` and
  `--convergence-only` for manuscript staging. Publication labels retain the
  projected repeat-MCMC wall-time curve but omit host names, worker counts,
  and the alternate-host axis.
- The default plotter behavior is unchanged. Campaign meeting books and their
  canonical ladder products still show source/alternate hosts and worker
  normalization for internal scheduling and provenance review.
- `Share_Folder/Manuscript/scripts/prepare_manuscript_assets.py` regenerates
  all 15 signed convergence pages into `Manuscript/build/publication_resolution/`
  and stages those neutral versions in the external paper. Python byte
  compilation, a complete manuscript build, PDF text extraction, and rendered
  first/last convergence-page inspection passed.

## Last Touched (2026-09-01): Campaign Cardinality and Provenance Guards

- `postprocess_core_logangle_powerlaw_15grb_10temp.sh` now distinguishes the
  active manifest subset from the campaign's expected event set. Expected
  events come from campaign `event_decision_records.json` when available, with
  the manifest as fallback. A one-event replacement watcher can therefore
  refresh one GRB without overwriting a complete 15-event campaign marker with
  `events=1`.
- Repaired the July-16 campaign's `campaign_products.validated` and
  `.campaign_meeting_summary.updated` markers after the corrected 090424
  watcher had overwritten them. They now record all 15 validated/published
  events and the reason for the repair.
- Validation: `bash -n` passed; a one-event 090424 manifest evaluated against
  the July-16 campaign reports 15 expected and 15 validated campaign events
  while retaining a one-event manifest scope. The corresponding manuscript
  provenance guard and full 15-event product validation also passed.

## Last Touched (2026-09-01): Composite Meeting-Book Generator Support

- Updated `write_campaign_latex_summary.py` for composite authoritative books.
  `load_settings()` now reports mixed `burn_length` and `run_length` values as
  `varies by event`; worker counts remain event/host provenance instead of being
  inferred from the first event.
- Added `published_share_path` and `published_folder_name` metadata overrides,
  used for the cover-page location when the build tree is separate from the
  published Drive directory. Added breakable rendering for long decision and
  tracking-note text and break opportunities in the cover's GRB links.
- Generated and compiled the 15-GRB staging tree at
  `VegasJetFit/reports/26_09_01__authoritative_15grb_composite_meeting_book`.
  The final PDF has 349 letter pages; representative title, event, and final
  comparison pages passed visual inspection. Severe filename overflow was
  eliminated; three small prose overfull-box warnings remain without visible
  clipping.

## Last Touched (2026-09-01--02): GRB 080319B Expanded-n17 Posterior-Cloud Refit

- Modified `build_posterior_informed_initial_positions.py` to support optional
  bounded hot-temperature expansion along a two-parameter ridge. The new CLI
  controls are `--ridge-parameter`, `--ridge-coupled-parameter`,
  `--ridge-coupled-factor`, and `--ridge-max-shift`; default behavior remains
  unchanged, and temperature zero is never altered by the ridge step.
- Built event config
  `structured_jet_core_logangle_080319B_n17upper15_finalfinal_sthawed_5temp_configs/080319B.toml`,
  exact observation override
  `obs_overrides/080319B_authoritative_all_early_uvoir_20260901.csv`, and seed
  `initial_positions/080319B_n17upper15_finalfinal_sthawed_5temp.npz`. The only
  model-config change is `n017` upper `10 -> 15`. SHA-256 values are recorded
  in the campaign decision record and enforced by the event wrapper.
- Added guarded runner `run_080319B_n17upper15_event.sh`, dynamic dispatcher
  launcher `start_dynamic_dispatch_080319B_n17upper15_lyra.sh`, and Lyra watcher
  launcher `start_postprocess_080319B_n17upper15_lyra.sh`. The dispatcher now
  targets Pauley404-02 first at eight workers, with the other Pauleys as
  fallback. The watcher performs the standard all-100 walker products,
  minimization, resolution ladder, validation, publication, and one-event
  meeting-book refresh.
- Validation performed: Python byte compilation; shell syntax checks; semantic
  source/config comparison; seed shape, prior, exact-cold-row, and ridge checks;
  and a full local likelihood preflight with 100/100 valid walkers in each of
  five temperatures. The final preflight log is
  `logs/080319B.core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_n17upper15_5temp_1000x5000_v1.preflight.log`.
- The first Pauley404-02 preflight failed before production because the remote
  `jetfit/models/vegas_resolution.py` predated the `reverse_radiation` interface
  used by the synchronized power-law model. Added that file and every other
  active run-path dependency to the sync set, plus fixed SHA-256 guards in the
  event wrapper. The retry passed 100/100 walkers at all five temperatures in
  187.58 s. Production started at `2026-09-02T18:53:48Z`; remote tmux session
  `grb080319B_n17upper15_080319B` and all eight worker processes were verified.
  Lyra session `postprocess_080319B_n17upper15_lyra` remains active.
- Updated `dynamic_dispatch_campaign.py`, `DISPATCH_POLICY.md`, and
  `RESOURCE_SCHEDULING_POLICY.md` for the academic year. Pauley is now the
  dependable normal-run default; PCRC is opportunistic and uses 14 workers
  only when current access is confirmed. Removed the permanent built-in
  `090618: pcrc_only` constraint so uncertain PCRC access cannot become a stale
  queue blocker. `test/test_dynamic_dispatch_policy.py` covers these defaults.

## Last Touched (2026-09-04): GRB 080319B Refit Completion and Corrected Data-Provenance Audit

- Pauley404-02 completed the 5-temperature, 100-walker, 1000-burn plus
  5000-production chain in 36.68 wall-clock hours. Lyra completed minimization,
  all-100-walker products, the resolution ladder, validation, publication, and
  the one-event meeting book by `2026-09-04T08:59:57Z`.
- The completed `log10(n17)` posterior is `11.157` with 16th--84th percentile
  interval `10.524--11.856`, safely below the expanded upper bound of `15`.
- The tracking-sheet instruction about restoring ignored non-X-ray data belongs
  to 080319B and says to restore Dylan's excluded early UVOIR measurements. The
  authoritative July 23 source and September refit `obs.csv` are byte-identical
  (SHA-256
  `6b313ca393b176dbacb1afae7ea99621d1df0cb5032cb75a98c819a23a83ff34`),
  but both contain 2,259 included rows and 113 UVOIR rows with `Include=0`.
  The prior claim that all early UVOIR data were included was wrong. The
  completed refit remains valid for the isolated expanded-`n17` test, not the
  all-UVOIR question.
- Built the corrected observation override
  `obs_overrides/080319B_all_early_uvoir_included_n17upper15_20260904.csv` by
  changing only those 113 flags from `0` to `1`; all 2,372 rows are now
  included and no X-ray data were added. Its SHA-256 is
  `136fc55f192117c6bb5be3b4389e72b5641ca58c94bd47f748fb143adb62fa3e`.
- Built an unmodified `(5,100,37)` whole-posterior-cloud seed from the completed
  expanded-`n17` chain and retained `-6 < log10(n17) < 15`, the same model,
  all other priors, grid `(0.15,0.50,15)`, and 1000+5000 sampler. Campaign
  records are under
  `reports/080319B_alluvoir_n17upper15_posteriorcloud_5temp_1000x5000_campaign/`.
  Local preflight passed 100/100 walkers at all five temperatures. The guarded
  Pauley404-02 preflight independently passed 100/100 at all five temperatures
  in 245.48 s, and production started at `2026-09-04T22:25:21Z`. The remote
  tmux session and all eight worker children were verified. Lyra sessions
  `postprocess_080319B_alluvoir_n17upper15_lyra` and
  `dynamic_dispatch_080319B_alluvoir_n17upper15_lyra` are active.
- Updated the old campaign records, the September 1 authoritative source
  manifest, an adjacent provenance-correction note, and tracking-sheet AB4.
  The fixed September 1 PDF remains the record of what was shown at the meeting.

## Last Touched (2026-09-04): Dynamic Hourly Supervisor Session Audit

- `supervise_grb_operations_hourly.sh` now discovers every current tmux session
  whose name starts with `dynamic_dispatch_` or `postprocess_`, instead of
  checking only two obsolete July session names. Syntax validation passed and
  Lyra session `supervise_grb_operations_hourly_lyra` was started.

## Last Touched (2026-09-04): Authoritative 15-GRB n17 Boundary Audit and Follow-ups

- Added `scripts/audit_authoritative_n17_boundaries.py` and audited the retained
  cold chains named by the September 1 authoritative 15-GRB source manifest.
  The reproducible table and selection rule are in
  `reports/26_09_04__authoritative_n17_upper15_followups/N17_BOUNDARY_AUDIT.md`
  and `n17_boundary_audit.csv`. Follow up when q99 is at least 9.5 or at least
  1% of samples exceed 9.9; a lone maximum at 10 is not enough.
- Selected `080319B`, `130612A`, `050922C`, and `050525A`. The corrected
  all-UVOIR `080319B` run was already active. Built controlled whole-cloud
  continuations for the other three under
  `reports/26_09_04__authoritative_n17_upper15_followups/`; only the `n017`
  upper bound changes from 10 to 15, while the lower bound remains -6 and each
  authoritative observation table, model, other prior, and grid is preserved.
- `130612A` passed 100/100 walkers at all five temperatures and entered full
  1000-burn plus 5000-production sampling on Pauley404-01 with eight workers.
  `050922C` did the same on Pauley404-03. `050525A` remains the next queued
  event. Pauley404-02 continues `080319B`; both PCRC hosts timed out during
  current access checks. Lyra watcher
  `postprocess_authoritative_n17upper15_lyra` will process and publish each
  event independently as it completes.
- Fixed `scripts/dynamic_dispatch_campaign.py` after an unreachable PCRC host
  caused a campaign-wide synchronization timeout even though it had failed the
  reachability probe. Synchronization now targets only selected destinations,
  catches host-local timeouts/failures, restores failed assignments to pending,
  and continues other launches. `test/test_dynamic_dispatch_policy.py` now has
  a timeout-isolation regression test; all six tests pass.
- Updated and verified tracking-sheet column AB for rows 2, 3, 4, and 9. The
  campaign README, method report, decision records, queue, manifest, and audit
  products record the complete provenance and autonomous weekend behavior.

## Last Touched (2026-09-07): Expanded-n17 Weekend Completion

- All four September 4 follow-ups completed normally. MCMC wall times were
  24.8 h for 050525A (Pauley404-03), 28.0 h for 050922C (Pauley404-03),
  56.5 h for 130612A (Pauley404-01), and 63.1 h for the corrected all-UVOIR
  080319B run (Pauley404-02). Each used eight workers and passed 100/100
  walkers at all five temperatures before production.
- Lyra completed minimization, standard all-100-walker products, numerical
  resolution ladders, validation, publication, and meeting-book regeneration.
  The three-event campaign validated 3/3 and has an 85-page meeting book; the
  one-event all-UVOIR campaign validated 1/1 and has a 43-page meeting book.
- Expanded posterior results: 050525A median/q16/q84/q99 =
  5.425/1.674/8.082/10.898 and closes below 15; 050922C =
  6.612/5.314/8.730/12.328 and closes below 15; 130612A =
  7.330/2.256/12.086/14.840 and remains extremely broad near the ceiling;
  all-UVOIR 080319B = 14.205/13.722/14.692/14.971, with 4.10% above 14.9,
  so it is genuinely truncated by the new upper bound. Do not automatically
  expand 080319B or 130612A again; review the physical interpretation and the
  proposed profile-averaged-density prior first.
- Updated campaign metadata, decision records, README files, local tracking
  snapshots, and live tracking-sheet AB2:AB4/AB9. Completed dispatcher sessions
  were stopped after publication; the hourly high-level supervisor remains.
- `$HOME/bin/grb-status` now reads `share_campaign` from structured
  `campaign_metadata.json` before falling back to legacy Markdown/name
  heuristics. It correctly reports the new campaign as 3/3 published and
  validated.

## Current Run (2026-09-07): 080319B All-UVOIR n17 Upper-25 Continuation

- Jonathan approved a controlled continuation of the accepted all-UVOIR
  080319B posterior because `n17` is normalized at `10^17 cm`, outside the
  radial range directly constrained by these data. Only the uniform upper
  bound changes from `log10(n17)=15` to `25`; the lower bound remains `-6`
  and all 2,372 observations, the model, other priors, grid, and sampler are
  unchanged.
- The source is the completed 500,000-sample cold posterior in
  `jetfit/results/080319B_core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_alluvoir_n17upper15_5temp_1000x5000_v1/chain.npz`.
  Temperature zero uses exact source-cloud draws. Hotter temperatures open
  the measured anticorrelated ridge by shifting `n017` upward and `k`
  downward, bounded by the existing priors. If the result reaches `k=-10`,
  review the slope boundary rather than automatically expanding again.
- Canonical campaign records are in
  `reports/080319B_alluvoir_n17upper25_posteriorcloud_5temp_1000x5000_campaign/`;
  the planned Share Folder destination begins
  `Fits/production_runs/final_seeded_runs/26_09_07__080319B__all_uvoir__posterior_cloud__n17_upper25__5_temperature_1000x5000`.

## Last Touched (2026-09-07): Upper-25 Density-Normalization Continuations

- Built, documented, locally preflighted, synchronized, remotely preflighted,
  and launched controlled upper-25 continuations for 080319B and 130612A.
  The semantic config diff in each case is only `n017` upper `15 -> 25`.
  All cold walkers are exact draws from each completed 500,000-sample upper-15
  posterior; hotter ensembles open the `n017`-up, `k`-down ridge.
- 080319B passed 100/100 walkers at all five temperatures remotely in 695.28 s
  and entered production on Pauley404-02 at `2026-09-07T23:52:19Z` with eight
  workers. 130612A passed the same gate in 557.62 s and entered production on
  Pauley404-01 at `2026-09-08T00:00:32Z` with eight workers.
- Lyra postprocessing watchers, dynamic dispatchers, and the hourly supervisor
  are active. Campaign records and initial metadata are present in both report
  directories and their corresponding Share Folder campaign directories.
  Live tracking-sheet cells AB4 and AB9 record the approved decisions and
  launch state.

## Last Touched (2026-09-08): Authoritative Meeting Book with Weekend Fits

- Built the 353-page authoritative 15-GRB meeting book in
  `reports/26_09_08__authoritative_15grb_composite_meeting_book/` and published
  `GRB_authoritative_meeting_book_2026-09-08.pdf` under the matching
  `Share_Folder/Reports/Meeting_Books/` directory. The source and shared PDFs
  have identical SHA-256 checksum
  `386fe26d8aace11f29686f4bb8b903512f66a1be47952b7e0e07359618959595`.
- The source manifest retains the 11 reviewed September 1 sources and replaces
  050525A, 050922C, 080319B, and 130612A with their completed, validated
  September 4-7 upper-15 fits. The 080319B source is the corrected all-UVOIR
  result with all 2,372 reviewed UVOIR rows and no early-X-ray flare.
- The active upper-25 continuations for 080319B and 130612A are explicitly
  documented as pending and excluded from the authoritative scientific source
  set until they complete and are reviewed. The book is ordered by GRB number;
  the meeting discussion resumes with the third event, 080319B.
- Snapshotted live tracking-sheet `Sheet1!A1:AB16` into
  `tracking_sheet_notes.json`. The standard generator refreshed stale 210905A
  and 221009A products, regenerated 15-event histograms/comparison plots,
  organized 65 aggregate figures, and compiled with only three minor overfull
  paragraph warnings. Validation confirmed 15/15 source markers, chains,
  models, minimized results, and resolution ladders. Visual checks covered the
  title, run-index/notes layout, 080319B transition, and comparison pages.

## Last Touched (2026-09-08): GitHub Production-Code Snapshot

- Committed the active fitting models, MCMC implementation, launch/dispatch
  and watcher scripts, post-processing and meeting-book generators,
  diagnostics, tests, and operational documentation on branch
  `jonathan-mac-version`. Campaign configurations, observation overrides,
  posterior chains, logs, reports, figures, and runtime state were deliberately
  excluded from the code snapshot.
- Expanded `.gitignore` for macOS metadata, caches, logs, generated reports,
  plots, temporary directories, and posterior results; tracked `.DS_Store`
  entries were removed from Git without deleting local working files.
- Validation: `git diff --cached --check`, Python byte compilation, shell
  syntax checks, and a staged credential scan passed. The current production
  regression selection passed 18/18 tests. Full historical test collection is
  still blocked by three obsolete tests that import removed `PowerLawPrior`,
  JetSimPy, and `jetfit.core.defns` components; this is a known legacy-suite
  cleanup item, not a failure of the active pipeline.
