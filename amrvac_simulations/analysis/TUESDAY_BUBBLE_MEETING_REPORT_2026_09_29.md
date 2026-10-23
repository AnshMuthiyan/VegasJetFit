# What radius are we fitting? AMRVAC wind-bubble profile comparison

Prepared for the Tuesday, 29 September 2026 GRB discussion. This is an
offline comparison to 12 selected one-dimensional AMRVAC simulation snapshots,
not a fit to GRB observations. Jonathan's unfinished empirical profile is
deliberately excluded from this report.

Meeting PDF and figure folder in the `VegasGRBruns` share:
`Reports/Bubble_Model_Comparisons/2026_09_29_Tuesday_meeting/`.

## Meeting takeaways

1. The wind termination shock and outer wall are different physical radii.
   Across the curated AMRVAC cases, the marked outer-rise radius is 9.4-25.2
   times the first-shock radius (median 17.7). Jonathan's fitted `R_t` is
   intended to describe the first shock. Ansh's fitted `R_pole` is the
   *outer edge* of a swept-up shell. Their numerical values should never be
   identified or transferred directly.
2. Jonathan's simple bubble retains an inner `r^-2` free wind and a
   termination-shock jump. Ansh's shell has a constant inner cavity density
   fixed to `0.01 cm^-3`, no free wind, and no termination shock. It can match
   an outer wall while missing the interior. The AMRVAC profiles commonly
   contain both structures.
3. When the models are allowed their best profile match to the same simulation
   data, Jonathan's simple bubble has lower RMS log-density error in 11 of 12
   cases. The median is 0.387 dex versus 0.677 dex for Ansh's fixed-cavity
   model. This is a shape test, **not** a GRB-data likelihood, evidence ratio,
   or model-selection claim.
4. The fitted radius is not guaranteed to recover the physical shock even
   in Jonathan's model. Across these offline profile matches, fitted
   `R_t/R_first-shock` spans 0.31-2.50 (median 0.91). Fixing `R_t` to the
   AMRVAC first-shock location and optimizing only `n_t` raises the median
   profile RMS from 0.387 to 0.973 dex. This reveals a limitation of the
   *whole-profile simple law*, not a reason to rename the first shock.
5. Ansh's fitted shell thickness fraction `eps` reaches at least 0.49 against
   its 0.50 upper prior in 8/12 cases. Its cavity density is not universal in
   the simulation. For `p6_n19`, Ansh's fixed-cavity profile has 2.497 dex
   RMS error versus 0.922 dex for Jonathan's simple model. Freeing the cavity
   density in a sensitivity check reduces Ansh's error to 0.902 dex, but
   adds a parameter and still does not restore the wind/termination shock.

## What was compared

All comparisons use the same 12 checksum-verified May 1 selected AMRVAC VTU
snapshots. The ambient mass density is fixed to the known simulation value.
It is displayed as an equivalent number density `n_eq = rho/(1.3 m_p)` for
both models. Ansh's *unmodified fitting adapter* uses `mu=1.0` by default;
that difference is standardized away here to isolate radial shape.

Each profile is evaluated at 256 equally weighted points in log radius, from
`0.25 R_t,external` to `3 R_outer-rise`, clipped to the valid simulation
domain. The objective is mean squared difference in `log10(n_eq)`; reported
scores are its square root in dex. Three seeded differential-evolution starts
are used per fit. No posterior, observational uncertainties, temporal
weighting, or blast-wave dynamics enter this calculation.

| Profile | Fixed quantities | Optimized quantities | Inner radial law |
| --- | --- | --- | --- |
| Jonathan simple bubble | AMRVAC ambient density | `R_t`, `n_t` | `n_t(R_t/r)^2`, then `4n_t` |
| Jonathan shock-anchored diagnostic | AMRVAC ambient density and measured first-shock radius | `n_t` | Same law with `R_t` fixed |
| Ansh spheroidal shell at `q=1` | AMRVAC ambient density and `n_cav=0.01 cm^-3` | `R_pole`, shell fraction `eps` | Constant cavity, then constant swept-up wall |

The first-shock and outer-rise markers are extracted from the May 1 AMRVAC
quality table. The outer-rise marker is the *onset* of the simulated outer
increase, not identical to Ansh's shell's outer boundary.

## Representative numerical results

RMS log-density residuals in dex (smaller is a closer match to the simulation
over the stated radial window):

| Simulation | Jonathan free `R_t` | Jonathan shock-anchored | Ansh fixed cavity |
| --- | ---: | ---: | ---: |
| `p4_n22` | 0.960 | 0.973 | 0.966 |
| `p5_n21` | 0.304 | 0.973 | 0.404 |
| `p6_n19` | 0.922 | 0.930 | 2.497 |

The curves show where each residual comes from. In `p4_n22`, both simple laws
miss the extended shocked-wind plateau and deeply depleted cavity even when
their wall is near the right radius. In `p5_n21`, the near-flat cavity gives
a good global match to Jonathan's free-radius approximation, but making its
`R_t` equal the physical first shock worsens the global residual. In
`p6_n19`, Ansh's fixed `0.01 cm^-3` interior lies far below the dense inner
wind and shocked region. The dense outer wall dominates swept-up mass, so a
good total mass ratio alone would hide these failures.

## Interpretation for our GRB fits

Jonathan's choice of `R_t` retains a direct physical connection to the
progenitor wind termination shock. The comparison supports keeping that
definition. It does **not** establish that every fitted `R_t` accurately
recovers a real shock: the current three-region model can move `R_t` to
compensate for its missing radial structure. Ansh's `R_pole` has a different
meaning and cannot be seeded from a posterior on `R_t` without an explicit
mapping and its uncertainty.

A useful next model would preserve a free-wind/termination-shock coordinate
and also describe the cavity and outer wall, with any relations between those
radii calibrated to the AMRVAC profiles. A profile family derived from the
selected simulations should be validated out of sample before using it in
MCMC. Ansh's current VegasAfterglow adapter has separate constructor and
configuration errors recorded in `BUBBLE_MODEL_COMPARISON_2026_09_28.md`; the
figures here evaluate its written radial formula offline, not a working fit.

## Figures and reproducibility

Figures in this folder: `all_12_residuals`, `representative_profiles`,
`p4_profiles`, `p5_profiles`, `p6_profiles`, and `radius_correspondence`, each
as PNG and PDF. `meeting_fit_metrics.csv` contains all 12 optimized radii,
densities, scores, and AMRVAC markers. The generating scripts are
`compare_fitting_profiles.py` and `build_tuesday_bubble_figures.py` in the
AMRVAC handoff checkout. The remote Ansh source inspected was commit
`7d12255` on `feature/amrvac-wind-bubble-models`; the local selected-snapshot
manifest verified all 12 VTU hashes before this analysis. No GRB fits were
started or changed.
