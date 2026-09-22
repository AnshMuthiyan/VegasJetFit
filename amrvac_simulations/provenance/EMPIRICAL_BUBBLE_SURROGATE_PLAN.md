# Empirical Bubble Surrogate Plan

## Goal

Fit GRB afterglows for ambient density at a chosen ambient pressure using an
AMRVAC-calibrated bubble profile. The GRB-facing model should expose a small
number of physical parameters, with the first production target being:

- fixed ambient pressure `p`
- fitted ambient density exponent `n`, where `rho_ISM = 10^n g cm^-3`

## Main Lesson

The seven-feature `p4_n22` template warp is not the right generator for the
profile. It can remove isolated numerical spikes, but it also breaks coupled
parts of the bubble structure and makes some overlays worse. The density
profile should be treated as a single connected object.

## Proposed Surrogate

For each pressure slice:

1. De-spike each AMRVAC profile only for isolated one-cell numerical extrema.
2. Extract two robust global registration radii:
   - the true first shock / termination-shock rise
   - the onset of the outer bubble-wall rise
3. Register the full profile with

   ```text
   z = [log10(r/R_t) - log10(x_ts)] / [log10(x_outer) - log10(x_ts)]
   ```

   where `x_ts` and `x_outer` are both measured in `r/R_t`.
4. Store the full de-spiked `log10(rho/rho_ISM)` profile on a common `z` grid.
5. Interpolate the entire registered curve as a function of `n`.
6. Map back to physical radius using smooth fits or table interpolation for
   `x_ts(p,n)` and `x_outer(p,n)`.

This keeps the morphology whole while still providing a continuous ambient
density parameter for GRB fitting.

## Why Registration Matters

Plain pointwise interpolation in `r/R_t` has a predictable failure mode: moving
shocks smear into broad ramps between grid densities. Registering by the two
physical shock radii lets the outer wall move while staying sharp.

## Mass Constraint

For production use in VegasAfterglow, the table should also carry a cumulative
swept-mass profile or a mass-normalization check. The density interpolation
must preserve the mass relevant for jet deceleration, not just look visually
reasonable.

Practical production rule:

- use the AMRVAC profile directly at simulated grid points
- interpolate registered full profiles between grid points
- verify the integrated mass against the AMRVAC/interpolated mass table
- if needed, apply a smooth shell-region normalization to enforce the target
  swept-up mass while keeping the ISM asymptote fixed

## Current Prototype Outputs

- `plots/p4_full_profile_interpolator_density_family.png`
- `plots/p4_registered_profile_interpolator_density_family.png`
- `plots/p4_registered_profile_interpolator_leave_one_out.png`
- `plots/p4_registered_profile_interpolator_report.txt`
- `plots/p4_registered_surrogate_cumulative_mass_profiles.png`
- `plots/p4_registered_surrogate_mass_and_radii_vs_density.png`
- `plots/p4_registered_surrogate_registered_density_heatmap.png`
- `plots/p4_registered_surrogate_physics_report.txt`
- `plots/p4_registered_surrogate_table.npz`
- `plots/p4_registered_surrogate_table_summary.csv`
- `plots/p4_registered_surrogate_table_readme.txt`
- `P4_REGISTERED_SURROGATE_PHYSICS_REPORT.md`

The registered prototype is the preferred direction. The unregistered
full-profile table is useful as a control, but not as the final production
model.

## p4 Physics-Check Result

The p4 registered surrogate passed the current internal checks:

- zero isolated spikes over the dense interpolated density grid
- positive density everywhere
- monotone cumulative mass with radius
- outer asymptote tied to `rho/rho_ISM = 1`
- first-shock jump close to the expected strong-shock factor of four
- smooth mass and radius trends over `n = log10(rho_ISM / g cm^-3)`

The next implementation step is to export both the density table and cumulative
mass table so that any VegasAfterglow implementation can be tested against the
same swept-mass profile.
