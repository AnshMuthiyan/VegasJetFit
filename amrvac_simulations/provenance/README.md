# AMRVAC Retarded-Wind p6 Diagnostic, x_min = 0.2 R_t

This campaign tests whether the `x_min = 0.8 R_t` full-timeline run truncated
too much of the free-wind region to produce a useful bubble density profile.
It keeps the same corrected retarded wind boundary and full BoOST timeline, but
moves the inner boundary inward:

- the grid is initialized as free wind inside `R_t`, not as ISM everywhere;
- the inner boundary uses the BoOST wind history at a retarded time.

No empirical-bubble profile is used as an initial condition.
The old internal source-region injector is not registered in this campaign;
the retarded inner boundary is the only active wind injector.

## Version

- MPI-AMRVAC: `v3.2`
- Commit: `c45d84650ed3379eb22dcfa6fb927a45734e5d8c`
- Hosts: `lyra`, `pauley404-01`, `pauley404-02`, `pauley404-03`

## Runtime Defaults

- `time_max = 5.35530d2`
- `dtsave_dat = 1.338825d2`
- `AMRVAC_NP = 8`
- `AMRVAC_FORCE_CLEAN = 0` by default, because the v3.2 library was already built in the previous campaign

## Grid Rule

- `xprobmin1 = 0.2 R_t`
- `xprobmax1 = 4 R_b`
- `stretch_dim(1) = 'uni'`
- `domain_nx1` is rounded to a multiple of `16`, so `domain_nx1 / block_nx1` is even

## Initial Condition

The initial condition is intentionally simple and physical:

- for `r < R_t`, free wind with `rho = Mdot / (4 pi r^2 vwind)` and `v_r = vwind`;
- for `r >= R_t`, static ISM with the selected ambient density and pressure.

This provides a physically interpretable termination-shock seed without imposing
the empirical-bubble profile.

## Inner Boundary

The stellar wind outflow is imposed at the inner radial boundary. In the
truncated domain this is numerically an inflow through `r_min`.

The BoOST parameters are evaluated at retarded time:

```text
t_ret = t - r / vwind(t_ret)
```

The implementation uses three fixed-point iterations and then applies:

```text
rho(r,t) = Mdot(t_ret) / [4 pi r^2 vwind(t_ret)]
v_r(t)   = vwind(t_ret)
p(t)     = rho * Twind(t_ret) * Tscale
```

## Refinement

The obsolete forced-refinement rule near `Rwind` is disabled. AMRVAC's automatic
error estimator is allowed to refine shocks and gradients.

## Queue Layout

- `pauley404-03`: `p6_n20 p6_n21 p6_n19 p6_n22`

This uses only `pauley404-03`, leaving `pauley404-01` and `pauley404-02` for
the structured-jet SBPL fits. The p6 cases are the most numerically demanding
and give the strongest test of whether moving the inner boundary inward
recovers a nontrivial density profile.

## 2026-05-03 Stability Rerun (Lyra)

Based on diagnostics of corrupted `test0004` snapshots in p5/p6, a Lyra-only
rerun queue was started to reduce inner-boundary stiffness while preserving the
termination-shock structure:

- `inner_rt_fraction` policy:
  - p4: `0.2`
  - p5/p6: `0.3`
- `courantpar` policy:
  - p4: `0.3d0`
  - p5/p6: `0.25d0`

Corrupted/legacy p5/p6 run directories were archived under:

- `_archive_pre_innerfix_20260503T174140Z/`

Active rerun tmux session on Lyra:

- `amrvac_innerfix_lyra_p5p6`
