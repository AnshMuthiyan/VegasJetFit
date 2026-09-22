# p4 Registered Empirical-Bubble Surrogate Physics Report

## Purpose

The science goal is to fit GRB afterglows for ambient density at a chosen
ambient pressure. For this first pressure slice, the pressure is fixed at
`p = 4`, and the fitted environmental parameter is

```text
n = log10(rho_ISM / g cm^-3).
```

The model should therefore be a smooth one-parameter density-profile family in
`n`, while preserving the physically important swept-up mass.

## Main Conclusion

The seven-feature `p4_n22` template warp is not a good production model. It can
match selected landmarks, but it breaks the connected profile morphology and
can make overlays worse.

The better surrogate is the registered full-profile model:

1. Lightly de-spike each AMRVAC curve only for isolated one-cell extrema.
2. Measure two physical anchor radii for each AMRVAC profile:
   - `x_ts`, the true first shock / termination-shock rise.
   - `x_outer`, the onset of the outer bubble-wall rise.
3. Map each full profile onto the registered coordinate

   ```text
   z = [log10(r/R_t) - log10(x_ts)] / [log10(x_outer) - log10(x_ts)].
   ```

4. Interpolate the full `log10(rho/rho_ISM)` profile as a function of `n`.
5. Map back to `r/R_t` using the interpolated shock radii.

This keeps the profile whole. The shocks move with density, but they do not get
smeared into broad ramps.

## Mass Definition

For `x = r/R_t` and `y = rho/rho_ISM`, the per-solid-angle swept mass is

```text
dM/dOmega = rho_ISM * R_t^3 * integral y(x) x^2 dx.
```

The check script evaluates both:

- dimensionless mass: `integral y x^2 dx`
- physical mass per solid angle: `rho_ISM R_t^3 integral y x^2 dx`

This is the quantity that matters most for GRB deceleration.

## Physics Checks

The script

```text
check_p4_registered_surrogate_physics.py
```

checks the following:

- The AMRVAC training profiles are reproduced exactly after light de-spiking.
- The profile is positive everywhere.
- The cumulative swept mass is monotone with radius.
- The isolated-spike count is zero across a 61-point interpolated density grid.
- The outer asymptote returns to `rho/rho_ISM = 1`.
- The first-shock jump is close to the strong-shock factor of 4.
- The total mass to the outer wall varies smoothly with `n`.

Training-run summary:

```text
p4_n24: x_ts=0.7078, x_outer=7.119, x_ism90=8.692, shock ratio=4.47, outer ISM=0.994
p4_n23: x_ts=0.7304, x_outer=7.070, x_ism90=8.674, shock ratio=4.47, outer ISM=1.01
p4_n22: x_ts=0.6573, x_outer=6.153, x_ism90=7.454, shock ratio=4.45, outer ISM=1.00
p4_n21: x_ts=0.4017, x_outer=3.882, x_ism90=4.703, shock ratio=4.19, outer ISM=1.00
```

The shock ratios are slightly above 4 because the diagnostic samples a
finite-width region just outside a sharp jump. That is acceptable for a
resolved hydro profile; the measured rise is still physically consistent with
the strong-shock jump.

## Smoothness

The dense interpolated grid samples 61 density values from `n = -24` to
`n = -21`.

Results:

```text
mass_positive: True
x90_finite: True
all_cumulative_mass_monotone: True
max_spike_count: 0
```

The registered density heatmap is smooth in `n`. The outer wall moves inward as
the ambient density increases. The physical mass to the wall rises with
density, but not as a pure power law because the bubble radius is shrinking at
the same time.

## Caveats

This is a p4 pressure-slice surrogate, not yet the full `(pressure, density)`
surface.

The `x_ts` sequence is not strictly monotonic over the four p4 AMRVAC runs. The
outer wall and swept mass are smooth enough for interpolation, but we should
revisit this once the full pressure grid is analyzed.

Before putting this into VegasAfterglow, the exported model should include the
cumulative mass table, not just the density table. That gives us a direct check
that any future implementation preserves the mass relevant for the light curve.

## Generated Files

```text
plots/p4_registered_surrogate_training_physics_checks.csv
plots/p4_registered_surrogate_dense_physics_checks.csv
plots/p4_registered_surrogate_cumulative_mass_profiles.png
plots/p4_registered_surrogate_mass_and_radii_vs_density.png
plots/p4_registered_surrogate_registered_density_heatmap.png
plots/p4_registered_surrogate_physics_report.txt
plots/p4_registered_surrogate_table.npz
plots/p4_registered_surrogate_table_summary.csv
plots/p4_registered_surrogate_table_readme.txt
```

The `.npz` table is the current implementation target for later
VegasAfterglow work. It contains the registered density table, a dense
interpolated profile grid, and cumulative-mass arrays.
