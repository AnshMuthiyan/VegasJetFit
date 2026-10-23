# Full 25/40-Msun density-pressure grid (23 October 2026)

Jonathan approved 24 complete stellar-track models, using the current dense finite-GMC model, and then shifted the pressure range to target mostly sub-parsec rising-density structure. This campaign is separate from BoOST and from the earlier 1500-year direct-phase tests. It is not a promise that a selected density/pressure produces a sub-parsec feature: that is an output to measure.

## Approved matrix and wind histories

- Initial stellar masses: 25 and 40 Msun.
- Core normalization n_ref: 3000, 10000, 30000 hydrogen nuclei cm^-3 at 1 pc in the untapered core profile. Actual central density is approximately 26^0.9 times n_ref; exact tapered values must be read from the initial state.
- Independent boundary P/k_B: 10^6, 10^7, 10^8, 10^9 K cm^-3.
- 25-Msun wind: MS to 6.5 Myr at 2e-7 Msun/yr, 1500 km/s; RSG to 7.0 Myr at 1e-5 Msun/yr, 15 km/s; no WR and no SN.
- 40-Msun wind: MS to 4.3 Myr at 1e-6 Msun/yr, 2000 km/s; RSG to 4.5 Myr at 5e-5 Msun/yr, 15 km/s; WR to 4.77 Myr at 1e-5 Msun/yr, 2000 km/s; no SN.
- Source: van Marle et al. (2012), Table 1, https://arxiv.org/html/1204.2078v3 . Injection temperatures 10000/1000 K for fast/slow winds remain numerical assumptions.

## Pressure, gravity and retained cloud physics

P_boundary is an independent effective confining pressure, set in cgs as k_B times the manifest value. It can represent the weight of overlying self-gravitating cloud material, and need not be interpreted solely as hot external gas. It is added as the outer integration constant in P(r)=P_boundary+integral_r^R rho(r')G M_initial(<r')/r'^2 dr'. The modeled star-plus-cloud gravity is already in that integral and in the momentum equation. Do not add the same cloud weight a second time as another force or pressure term. A plane-sheet relation P~pi G Sigma^2/2 is an interpretation guide, not an exact identity for this spherical geometry.

Retained: core flattening0.2pc, slope1.8, core edge2pc/taper0.5pc, GMC density1000cm^-3/edge15pc/taper1pc, external density10cm^-3, support speed0.72km/s, the original prescribed initial-mass gravity field, and neutral support-floor/relaxation prescription. Gravity is FIXED to the initial mass profile; this is not evolving self-gravity. The two stellar tracks use the same non-ionizing cloud prescription: photoionization, tabulated radiative cooling and conduction are OFF. The retained neutral pressure-relaxation term is effective thermal support, not a calibrated cooling curve. High pressure is effective isotropic confinement, not an independently calibrated thermal/magnetic/radiation mixture.

## Domain and numerical limits

The survey mesh has 1024 stretched cells over0.001--160pc, first width0.0003pc. The wide outer domain avoids forcing the full stellar history into the old2.5pc box. The small inner boundary retains the high-pressure sub-0.01pc region, but profiles near the injection boundary and unresolved local rises must be flagged. Full-lifetime sampling does not establish spatial convergence or physical shock thickness. Source `wind_boundary_dt` bounds the boundary CFL by the fastest track wind even during RSG: a transition fixture demonstrated negative density when an RSG-sized timestep straddled the jump to WR. The failure also exposed nominal rather than physical stretched-cell spacing in the boundary CFL. The new bound uses local cell-center spacing and the fastest track speed. Failed fixtures are retained; this numerical correction does not change wind rates, speeds or phase ages. Both exact endpoints tolerate only1e-9Myr roundoff and reject actual post-track evolution.

## Parameterization deliverable

Preserve all saved .dat/.vtu files and density-profile PNGs under explicit mass/density/pressure/case paths. Save every0.1Myr plus the exact endpoint:71 saves for25Msun and49 for40Msun. Full evolution starts at zero with no phase-age shortcut. Separately measure the wind termination shock, local inner rising-density transition (R10/R50/R90), outer swept shell, native rise/FWHM cell counts, density contrast and cumulative enclosed/swept mass. The GRB-facing target is mostly sub-parsec rising density, not an assumption that every radius equals the outer bubble wall.

For the eventual surrogate, register complete log-density profiles by physically identified radii before interpolating across density and pressure. Retain the native mass profile and validate withheld grid points, positive density, outer asymptote, cumulative mass and behavior at parameter boundaries. Do not train on unresolved or boundary-contaminated profiles, extrapolate silently, or replace full phase evolution with an artificial direct-WR start. AMRVAC runs offline; only a validated compact surrogate belongs in VegasAfterglow/MCMC.

## Execution status

All24 models were dispatched once on23October2026 and are now in full evolution after individual static and smoke gates. Four independent one-core models run per host on Keohane1--4 and Pauley404-01/02. Mac03 is omitted from this long grid because the previous campaign measured much slower per-core throughput. Each full run has a generous finite30-day safety timeout; this is not a runtime forecast. Short benchmarks imply days rather than hours for a full track. Do not restart or duplicate active cases. `manifest.csv` is authoritative for the24 cases and exact SHA values; `design.json` records the common model. Read the newest root CODEX_HANDOFF.md for subsequent dispatch status. Each case must pass a fresh static atmosphere and short wind gate before its full run. Independent cases may run concurrently as separate serial one-core jobs; workers are limited to four per host and at most half the detected CPUs. Do not restart failed cases automatically. Record nonzero exits and failed scientific gates without relabeling them as completed results.

## Verified implementation and current commands

Both pinned-AMRVAC-v3.1 architectures passed five actual compiled transition/endpoint fixtures and four independent boundary-pressure initializations, plus static/smoke tests at two opposite grid corners. Final static maximum core-density drifts were0.0681% and0.1988%. All24 individual cases subsequently passed their own gates before entering full evolution. The original transition fixture failed with negative density on both architectures; its logs are preserved in build scratch and the resolved stretched-cell CFL correction is documented above. Historical validation demanded an unshocked active-cell wind speed at an arbitrary time; that is inappropriate for a confined wind. The new checker independently verifies injected rates/speeds from runtime track diagnostics, phase-age snapshots and finite-positive evolved fields, and does not require shocked gas to keep its injection speed.

- Read-only status: `/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_full_track_grid_20261023/status_grid.py`.
- Exact inputs/source: `manifest.csv`, `design.json`, `inputs/`, `mod_usr.t`. Inputs are frozen after build.
- `dispatch_records.json` gives six exact farm paths, host allocations and launcher PIDs; `builds/<architecture>/pins_<host>.json` pins every transferred source/input/binary file.
- Runtime queue: `grid_runtime.py`, four workers at most and at most half the host CPUs; isolated case/stage records, no automatic failed-input retries.
- No subsequent reproduction or dispatch command is authorized by this README alone. Read newest root handoff and current user instructions.
