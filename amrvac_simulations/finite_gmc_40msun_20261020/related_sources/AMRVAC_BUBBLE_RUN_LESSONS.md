# AMRVAC Bubble Run Lessons

Last updated: 2026-04-24

## Current AMRVAC Version

- Lyra has been updated to MPI-AMRVAC `v3.2`.
- The intended production version for the Pauley machines is also MPI-AMRVAC `v3.2`.
- Verified Lyra commit: `c45d84650ed3379eb22dcfa6fb927a45734e5d8c`.
- The previous version on Lyra and Pauley was `v3.1`, commit `244c677fd6095bb019587a2fdc97feb67a66f06a`.

## v3.2 Caveat

MPI-AMRVAC `v3.2` changes generated build details. In the smoke test, the library path changed from:

```text
lib/1d_default
```

to:

```text
lib/1d1_default
```

Therefore, old problem directories should not be reused with stale makefiles. After switching to `v3.2`, run:

```bash
setup.pl -d=1
make allclean
make
```

or use the existing `run.zsh` pattern with `AMRVAC_FORCE_CLEAN=1`, which regenerates the problem makefile and rebuilds cleanly.

## Log-Radial Grid

The simple log-radial grid is implemented with AMRVAC's unidirectional stretched grid:

```fortran
stretch_dim(1) = 'uni'
```

If `qstretch_baselevel(1)` is not specified, AMRVAC chooses:

```text
q = (xprobmax1 / xprobmin1)^(1 / domain_nx1)
```

For our positive radial coordinate, this is the geometric/log-like spacing we want.

## Smoke-Test Result

Smoke-test directory:

```text
/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_24_pressure_grid_log_smoke/pressure_p6_n21_log_smoke
```

The `p6_n21` log-grid smoke test succeeded under `v3.2` with:

```text
domain_nx1 = 288
xprobmin1 = 0.0019676954697354647 pc
xprobmax1 = 6.9721496361284325 pc
Rwind     = 0.009838477348677323 pc
time_max  = 1.0e-4
```

AMRVAC reported:

```text
q(level 1)          = 1.0287843193743433
first dx(level 1)   = 5.6638774832316102e-5 pc
first dx(level 4)   = 6.9922608540368320e-6 pc
```

This confirms that the wind injection radius is safely resolved in the high-pressure, small-`R_t` case.

## Time-Step Caveat

The initial log-grid cells are very small. A smoke test with `time_max = 10` was not useful: after about 30 seconds, it had only reached code time `9.35e-5`. For future smoke tests, use short code times such as:

```text
time_max = 1e-4
```

This is enough to validate parsing, mesh construction, source placement, early timestepping, and output without wasting wall time.

## Grid Planning

The current recommended preliminary campaign rule is:

```text
xprobmin1 = 0.02 R_t
xprobmax1 = 4 R_b
Rwind     = 0.1 R_t
domain_nx1 from cells-per-decade, rounded so domain_nx1 / block_nx1 is even
```

For the pressure-grid preliminary runs, `80` cells per decade gives roughly:

```text
max domain_nx1 ~ 288
~56 cells from xprobmin1 to Rwind
~138 cells from xprobmin1 to R_t
```

This is much more practical than the uniform-grid plan, whose worst case required `7088` base cells.

AMRVAC also requires an even number of level-1 blocks in 1D. With `block_nx1 = 8`,
round `domain_nx1` to a multiple of `16`, not merely a multiple of `8`. The first
full pressure-grid launch failed for the `p4` cases with `domain_nx1 = 248` and
`264`, because these correspond to `31` and `33` level-1 blocks.

## Cleanup Policy

These are preliminary AMRVAC campaigns. To reduce future confusion:

- Prefer clean, version-labeled campaign directories.
- Do not keep multiple stale AMRVAC source trees on the Pauley machines unless needed for a specific comparison.
- It is acceptable to remove old preliminary outputs and stale build artifacts from Pauley machines.
- Keep important analysis products, grid plans, and final plots on Lyra or the shared drive.
- When changing AMRVAC versions, record the exact tag and commit in the campaign README.

## Current Operational Rule

Before dispatching production-like runs:

1. Confirm all hosts report the same AMRVAC tag and commit.
2. Regenerate problem makefiles after any AMRVAC version change.
3. Run one short log-grid smoke test on Lyra.
4. Run one short log-grid smoke test on a Pauley machine.
5. Only then dispatch the full preliminary campaign.

## 2026-04-24 Pressure-Grid Debugging Notes

The first full pressure-grid launch exposed two operational bugs that the smoke
test did not catch:

1. `domain_nx1` must not only be compatible with `block_nx1`; the number of
   level-1 blocks must also be even. For `block_nx1 = 8`, round `domain_nx1`
   to a multiple of `16`. The failed p4 cases had `248/8 = 31` and `264/8 =
   33` level-1 blocks, and AMRVAC aborted with `number level 1 blocks in D
   must be even`.
2. The unattended watcher must not blindly relaunch failed runs, because the
   run script rebuilds each run directory from the template and can erase the
   evidence. Failed runs now write a `FAILED` marker, and the watcher syncs the
   failed directory back but does not relaunch it automatically.

The corrected preliminary pressure-grid launch started at about
`2026-04-24T19:59Z`. The first checkpoint verified that all four hosts passed
the previous abort point, entered `mpirun -np 8`, and began AMRVAC time
integration:

```text
lyra         pressure_p4_n21
pauley404-01 pressure_p4_n22
pauley404-02 pressure_p4_n23
pauley404-03 pressure_p4_n24
```

Testing protocol for this campaign:

1. Check the watcher log for `active` records and absence of repeated
   `launching` records for the same run.
2. Check each host for one `host_pressure_queue.zsh` plus one `prterun -np 8`
   and eight `./amrvac` ranks.
3. Check the first AMRVAC log after startup for a valid stretched grid report,
   `Domain size (cells)`, and the first timestep/status table.
4. After each run exits, check for either `Finished AMRVAC` in `amrvac.log` or
   a `FAILED` marker. Do not delete failed directories until the abort reason
   has been recorded.

When writing remote monitoring commands, avoid nesting single-quoted grep
patterns inside `ssh host "zsh -lc '...'"`; the remote shell can split the grep
pattern on pipes and attempt to run commands such as `prterun` with no
arguments. Use double-quoted `grep -E` patterns inside the remote command
instead.

## 2026-04-24 Long-Run Timing Failure

The corrected pressure-grid campaign was numerically stable, but it was not a
useful preliminary run. It used the inherited full-run stop time:

```text
time_max = 5.35530d2
dtsave_dat = 1.338825d2
```

After about 3.7 hours of wall time:

```text
lyra          p4_n21: t ~= 0.317 / 535.53
pauley404-01 p4_n22: t ~= 6.27  / 535.53
pauley404-02 p4_n23: t ~= 6.42  / 535.53
pauley404-03 p4_n24: t ~= 5.20  / 535.53
```

Extrapolated full-run wall times were roughly 13-16 days for the Pauley p4
cases and hundreds of days for the cold dense `p4_n21` case on Lyra. This is
far too slow for a preliminary grid test. The run was stopped cleanly at
`2026-04-24T23:47Z`, with logs preserved in the campaign directory.

For future preliminary campaigns:

1. Do not inherit the full stellar-evolution stop time.
2. Set a short `time_max` first, such as `1.0d0` or less.
3. Set `dtsave_dat` small enough to save several intermediate profiles, e.g.
   `time_max / 5`.
4. Estimate wall time from the first 10-30 minutes before committing all hosts
   to a long run.
5. Treat the cold dense pressure case (`p4_n21`) as a likely worst-case timestep
   limiter.

## Tight Inner Boundary Test

For a fast preliminary test of the shell and outer bubble, it is reasonable to
move the inner boundary close to the termination shock instead of resolving the
whole free-wind region. The current test choice is:

```text
xprobmin1 = 0.8 R_t
```

This requires changing the inner boundary from reflecting/symmetric to a
special wind boundary. Physically the star is launching a wind outflow; in the
truncated computational domain this is implemented as wind entering through the
inner radial boundary:

```text
rho = Mdot / (4 pi r^2 vwind)
v_r = vwind
p   = rho * Twind * Tscale
```

Do not use the old internal source-region logic alone with this grid, because
`Rwind = 0.1 R_t` lies outside the simulated domain once `xprobmin1 = 0.8 R_t`.

## 2026-04-24 Retarded Wind Boundary Fix

The tight-domain retarded-wind campaign is:

```text
/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_24_pressure_grid_log_v32_tight_rtwind_v1
```

The corrected setup deliberately does not seed the simulation with the
empirical bubble profile. The initial state is:

```text
r < R_t  : free wind, rho = Mdot / (4 pi r^2 vwind), v_r = vwind
r >= R_t : static ISM at the chosen pressure and density
```

The stellar wind enters only through the special inner boundary. The obsolete
internal source injector near `Rwind = 0.1 R_t` is not registered, because this
radius is outside the truncated domain and its non-retarded parameter update can
confuse the boundary-state logic.

The boundary evaluates the BoOST wind history at retarded time:

```text
t_ret = t - r / vwind(t_ret)
rho(r,t) = Mdot(t_ret) / [4 pi r^2 vwind(t_ret)]
v_r(t)   = vwind(t_ret)
```

The current implementation uses three fixed-point iterations. This is adequate
for the preliminary run because the correction only matters when the wind speed
changes appreciably over a light/travel time across the inner boundary radius.

Forced refinement near the old `Rwind` is disabled. AMRVAC's automatic error
estimator should choose refinement from the actual density/pressure gradients
and shocks.

## 2026-04-24 Full-Timeline Science Triad

The overnight science-priority campaign is:

```text
/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_24_pressure_grid_log_v32_tight_rtwind_fulltimeline_science_triad_overnight
```

The first three runs deliberately hold the ambient temperature slice fixed near
`217 K` while varying pressure by decade:

```text
p4_n22 : P/k = 1e4, rho_ism = 1e-22 g cm^-3
p5_n21 : P/k = 1e5, rho_ism = 1e-21 g cm^-3
p6_n20 : P/k = 1e6, rho_ism = 1e-20 g cm^-3
```

Each run covers the full BoOST stellar timeline:

```text
time_max  = 5.35530d2
dtsave_dat = 1.338825d2
```

The science objective is the final radial density profile for GRB fitting, not
high-fidelity resolution of every contact discontinuity. We therefore preserve
the corrected retarded wind boundary and automatic AMR, but accept that this is
a preliminary density-profile campaign rather than a production hydro run.

To reduce dead time, the p4 and p5 hosts queue additional full-timeline cases
after the primary fixed-temperature comparison:

```text
pauley404-01: p4_n22 p4_n23 p4_n21 p4_n24
pauley404-02: p5_n21 p5_n22 p5_n20 p5_n23
pauley404-03: p6_n20 p6_n21 p6_n19 p6_n22
```

Lyra is intentionally not used for AMRVAC in this campaign because it is still
running the 080319B VegasAfterglow/JetFit process.

## 2026-04-25 x_min = 0.2 R_t p6 Diagnostic

The full-timeline `x_min = 0.8 R_t` pressure-grid campaign completed all 12
runs quickly and without failures, but the first final-density plots were mostly
flat at the imposed ISM density. That suggests the truncated domain may be too
aggressive for recovering a useful bubble density profile for GRB work.

A follow-up diagnostic campaign was started on `pauley404-03` only, leaving
`pauley404-01` and `pauley404-02` for the structured-jet SBPL fits:

```text
/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_25_rtwind_fulltimeline_xmin0p2_p6diag
```

This keeps the same retarded BoOST wind boundary and full stellar timeline, but
moves the inner boundary inward:

```text
xprobmin1 = 0.2 R_t
```

The queued p6 cases are:

```text
p6_n20 p6_n21 p6_n19 p6_n22
```

The goal is not high-precision hydro, but a quick check of whether giving the
free wind more radial lever arm restores nontrivial termination-shock/bubble
structure in the final density profiles.
