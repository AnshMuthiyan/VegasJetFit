# VegasJetFit/scripts Handoff

This directory contains active post-fit product scripts.

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

### Discovered Forward-Shock Lorentz Field

- Field: `details.fwd.Gamma`
- Access pattern used in current scripts: `details.fwd.Gamma[0, 0, :]`
- Grid compatibility: aligned with `details.fwd.t_obs[0,0,:]`, `details.fwd.r[0,0,:]`, and `details.fwd.N_p[0,0,:]` in the current VegasAfterglow detail output.
- Current usage locations:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_mass_vs_time_products.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py`

## Spectral/Frequency Plot Convention (2026-06-01)

- Use `/Users/jkeohane/GRBs/VegasJetFit/scripts/batch_weighted_spectral_posteriors.py` for the canonical all-walker `spectral_plot.pdf/.png` product.
- Use `/Users/jkeohane/GRBs/VegasJetFit/scripts/plot_weighted_spectral_breaks.py` when a single minimized/best-fit EATS-weighted break plot and `spectral_breaks_eats_weighted.csv` are needed.
- For structured power-law Dylan-spectrum runs (`PowerlawJetVegasDylanSpectrumModel`), `batch_weighted_spectral_posteriors.py` explicitly passes `break_frequency_mode="eats_weighted"`. The posterior walker cloud and best curve therefore call `nu_a/nu_m/nu_c` through the Dylan-style EATS-weighted break calculation.
- `plot_weighted_spectral_breaks.py` computes breaks directly from `model.vegas_model.details(...)` with observer-frame `nu * Doppler / (1+z)` and weights proportional to `I_nu_max * Doppler^3`. It now fails instead of silently falling back to legacy/local `model.nu_*` curves unless `--allow-local-fallback` is explicitly requested.
- `frequencies.pdf` is a legacy frequency diagnostic. Do not copy or rename it to `spectral_plot.pdf`; `spectral_plot.pdf` is reserved for the EATS-weighted spectral plotting scripts.

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
- On MCMC success the pipeline automatically runs minimization, standard postfit products, EATS-weighted spectral plot regeneration, spectrum-timeseries regeneration, and syncs to `/Users/jkeohane/GRBs/Share_Folder/Fits/jet_structured_powerlaw/csm_powerlaw/spectrum_dylan_smoothed/thawed_viewing_core_and_structure/20260601__090618_structjet_thetav_thetac_electronp_epsbmin10_resume1000_v1/090618`.
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
