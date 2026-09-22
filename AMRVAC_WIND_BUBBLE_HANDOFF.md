# AMRVAC wind-bubble model handoff

Status: development handoff, 2026-09-22. No production model, prior, or fit is changed by this document.

## Where to work

- Git repository: `git@github.com:AnshMuthiyan/VegasJetFit.git`.
- Shared base at handoff: `jonathan-mac-version`, commit `03e4097`.
- Dedicated branch for Ansh's bubble work: `feature/amrvac-wind-bubble-models`.
- On Lyra, the clean branch checkout is `/Users/jkeohane/GRBs/VegasJetFit_wind_bubble_handoff`. The actively running/developed absorption checkout is dirty; do not replace it with this branch or launch a campaign from this checkout merely because it exists.
- Keep AMRVAC/bubble changes on this branch and propose a reviewed merge into `jonathan-mac-version` after validation. Fetch the latest base before merging; do not overwrite students' extinction/filter-integration work.

## Research objective and boundaries

Fit afterglow data with a physically defensible wind-blown circumstellar bubble informed by the AMRVAC simulations. Preserve the forward-shock baseline and compare any new model to it with identical data, attenuation, jet, resolution, and likelihood settings. The purpose is to learn whether the density structure improves the fit, not to assume that a bubble is present.

There are three related but distinct workstreams:

1. **Ansh: AMRVAC wind-bubble model.** Improve and validate the bubble density/profile implementation below on this branch. Document simulation snapshot and calibration provenance.
2. **Jonathan/Codex: density sampling coordinate.** Replace the single-power-law `n017` sampling coordinate and its prior with a precisely defined volume-averaged density. This is a separate parameterization change, not an automatic change to the bubble's `nt` or `nism`. Coordinate the interface before merging.
3. **Jonathan/Codex, with Ansh's input: optional reverse shock (RS).** Add explicit RS-on tests for Dylan's two smoothly broken medium cases, 080319B and 080413B, as requested by Jonathan; use it for other models only where observationally warranted. It must default off generally and demonstrably affect the modeled flux when on. Do not confuse the RS in GRB ejecta with the progenitor wind termination shock at `R_t`. FS below means forward shock.

No numerical prior on mean density, reverse-shock microphysics prior, or production rerun is approved by this handoff alone.

## Existing bubble code and physical definitions

| Component | Current role | Scientific caution |
| --- | --- | --- |
| `jetfit/models/bubbleVegas.py` | Three-parameter `BubbleVegasModel`, a top-hat jet in `n(r)=nt*(rt/r)^2` inside `rt`, `4*nt` from `rt` to `r2`, then `nism`. `r2` uses a legacy spherical shell-mass closure. | The abrupt density jumps and mass closure are a surrogate, not a hydrodynamic calculation. `**kwargs` is currently ignored, so an unknown `reverse_shock` option can be silently ineffective. |
| `jetfit/models/empiricalBubbleProfile.py` | `density_21`-calibrated dimensionless `psi(x)` profile between `rt` and `r2`, with `x=(r-rt)/(r2-rt)` and `log10(n)=log10(4nt)+[log10(nism)-log10(4nt)]*psi(x)`. | This is a fixed empirical profile, not a universal AMRVAC family. `empirical_local_k` is clipped to [-10, 2] for the analytic spectral surrogate; check sensitivity near the wall. |
| `jetfit/models/empiricalBubbleVegas.py` | Uses the same `rt`, `nt`, `nism`, and `r2` closure, replacing the constant shell with the empirical profile. | Compare its GIL-free native callback against the Python profile at all knots and boundaries. Its `_setup_model` also does not install reverse-shock radiation. |
| `jetfit/models/bubbleVegasDylanSpectrum.py` and `jetfit/models/empiricalBubbleVegasDylanSpectrum.py` | Combine Vegas forward-shock dynamics/breaks with Dylan/Granot-Sari analytic spectral smoothing. | Their spectrum is reconstructed from `details.fwd`. They use a native total flux only for a peak normalization. If native RS is later enabled, that is not a valid FS+RS spectral sum; test/add the components explicitly. |
| `scripts/analyze_amrvac_bubble_profiles.py` | Extracts AMRVAC VTU radial profiles and compares a simple surrogate. | Its default simulation path points to an older workspace. Record the actual snapshot, physical units, and conversion file used in each calibration. |
| `scripts/build_bubble_dylan_toml.py`, `scripts/build_empirical_bubble_seeded_toml.py`, `scripts/build_empirical_bubble_from_sbpl_fit.py` | Build event-specific bubble configs and seeds from control fits. | Verify which configuration keys survive each builder; preserve extinction, gas absorption, offsets, slop, data inclusion, and provenance. A seed is not an independent posterior. |
| `jetfit/ampy.py` | Maps TOML model names to implementation classes. | Keep any new model name explicit and testable. |

The native VegasAfterglow `Model` accepts optional `rvs_rad` through `jetfit/models/vegas_resolution.py`; `jetfit/models/powerlawVegas.py` shows an existing `reverse_shock=False` and reverse-radiation construction. That is an implementation example, not evidence that the current bubble or smoothly broken fit paths include RS. `jetfit/models/vegasafterglow.py` (the native smoothly broken medium adapter) does not expose reverse-shock parameters at this handoff.

The two Dylan-thesis-style smoothly broken environment config builders explicitly target 080319B and 080413B (`scripts/build_sbpl_tophat_dylanthesis_seeded_configs.py`). These are **separate** from the AMRVAC bubble models, even if a finished smoothly broken fit is used to initialize a bubble fit.

## Prior AMRVAC work to preserve

- The Lyra-local report `VegasJetFit/reports/amrvac_pressure_environment_note_20260424/amrvac_pressure_environment_note.tex` distinguishes pressure control of the wind termination shock from ambient-density control of accumulated mass and shell structure. Do not infer `R_t` from `nism` alone without revisiting this physics.
- `VegasJetFit/reports/amrvac_prelim_headroom_boxfrac4_v3_factor48_cells6_20260424/` has radial-profile and simple-bubble comparisons for `density_18` through `density_27`. These are historical exploratory outputs, not a declared production calibration set. The source VTU snapshot and simulation settings must be identified before a publication claim.
- The empirical implementation itself states why `density_21` was chosen rather than a median profile: mapping a `density_23` outer wall into the simple-model coordinate created a spurious bump near `x~0.8`. Reproduce this comparison before replacing the knots.
- Number density versus mass density needs one consistent convention. The existing bubble callback uses `rho=mu*m_p*n` with `mu=1.3`; the smoothly broken native medium instead has its own `X_h` convention. Test conversions and label what `n` means (hydrogen nuclei, particles, or baryons) before sharing priors across models.

## Density-coordinate task (separate from bubble development)

The currently reported `mean_number_density_cm3` is the **volume-weighted** shell mean in `scripts/plot/visualize.py::density_shell_properties` / `powerlaw_density_shell_properties`:

`nbar = 3 * integral[n(r) r^2 dr] / (r_outer^3 - r_inner^3)`.

For fixed radii and `n(r)=n017*(r/1e17 cm)^(-k)`, the mapping is analytic, including the logarithmic `k=3` limit. But the current plotted `r_inner,r_outer` are obtained for each proposal from approximate on-axis blast-wave dynamics in `DensityProfiler._blast_wave_radii`; they change with `n017`, `k`, energy, and observation-time range. Thus swapping a TOML name or applying a prior directly to the old diagnostic is **not** a valid replacement. Choose and record the observing-time endpoints and radius convention first; if the endpoints remain proposal-dependent, demonstrate a unique, stable inverse `nbar -> n017` over the supported parameter box. Check off-axis/native trajectories and the induced prior/Jacobian, including near `k=3`. Keep `n017` as a derived quantity in results for comparison with old fits. A simpler fixed physical radial interval is possible, but it is a different physical prior and must be labeled as such.

The earlier exploratory proposal on Lyra is `VegasJetFit/reports/2026_09_09_density_normalization_speed/PHYSICAL_PRIOR_PROPOSAL.md`; it was not implemented. Jonathan has now requested that the averaged quantity become the fit coordinate and receive the prior. The choice of numerical bounds still requires a documented scientific basis and a controlled before/after fit.

## Optional reverse shock: implementation and evidence gates

1. Keep FS-only as the default. Add an explicit per-config switch, and fail validation if a selected model cannot honor it. A silent `**kwargs` swallow is unacceptable.
2. Verify native dynamics/flux support with each medium type. Use the same jet duration, angular grid, observer convention, and independently stated RS microphysics in on/off comparisons. Do not assume RS has the same `eps_e`, `eps_B`, `p`, or accelerated-electron fraction as FS unless testing that hypothesis.
3. For the Dylan-smoothed wrappers, compare the intended `F_nu,FS + F_nu,RS` to what the fitting likelihood actually evaluates across radio, optical, and X-ray times. A native `rvs_rad` combined with FS-only analytic spectral reconstruction does not suffice.
4. For the requested 080319B and 080413B RS-on tests, archive flux-component light curves, residuals/likelihood by band, numerical-resolution checks, and runtime. Judge whether RS is actually required by improvement and physical plausibility, not only the model family name. Explain any poorly modeled early component or excluded flare separately.
5. Ensure the config, output metadata, plots, meeting-book caption, and run provenance state RS on/off and all RS parameters. A changed model requires a new run tag and its own posterior; do not continue an old chain as if it were the same likelihood.

## Suggested first validations for Ansh

- Unit-test `n(r)` and `rho(r)` at `r<rt`, `rt`, interior knots, `r2`, and `r>r2`, including finite positive behavior and native/Python callback agreement. Test continuity and intended jumps explicitly.
- Compare each candidate surrogate to the named AMRVAC snapshot in physical `cm`, `cm^-3`, and `g cm^-3`; report radius and density residuals and flag simulation boundaries, rather than comparing only normalized plots.
- Verify that shell closure, local `k(r)`, and swept-up mass remain physical over the proposed prior box, including `nism >> nt` and `nism << nt`.
- Run deterministic light-curve smoke tests at representative parameters before MCMC. Compare simple bubble, empirical bubble, and smoothly broken controls using identical attenuation/data/resolution settings. Measure evaluation time and memory.
- Add automated tests under `test/models/` for the medium callbacks, TOML model construction, and any RS path; run focused tests and one short, clearly labeled non-production fit. Keep simulation data and large outputs out of Git; commit a small provenance manifest and reproducible commands.

## Handoff checklist

- [ ] Identify canonical AMRVAC snapshot(s), physical time/units, `mod_usr.t`, checksum, and calibration script arguments.
- [ ] Choose which physical profile and parameterization is to be tested, with a comparison to the existing simple and empirical baselines.
- [ ] Record explicit numerical priors and whether they are uniform in linear or logarithmic coordinates; audit the induced physical distributions.
- [ ] Add tests and finite smoke products; examine FS/RS treatment if using a model that needs RS.
- [ ] Review the scientific comparison with Jonathan before any long production fit or merge.

To start: `git fetch origin` and `git switch feature/amrvac-wind-bubble-models` (or track `origin/feature/amrvac-wind-bubble-models` on another machine). Keep commits scoped to the bubble work and push to this branch. The handoff commit is documentation only.
