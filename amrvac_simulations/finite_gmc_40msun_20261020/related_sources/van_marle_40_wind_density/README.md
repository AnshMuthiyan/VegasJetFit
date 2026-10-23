# 40 Msun multiphase wind bubble, 1D spherical pilot

Status: inputs only, **held for radius redesign**. No case has been compiled,
run, or validated. This is a separate campaign from the stopped
high-resolution BoOST ladder and the first-step-failing 2D van Marle pilot.

The [van Marle et al. (2012) paper](https://doi.org/10.1051/0004-6361/201219180)
sets the 40 Msun wind history. This model includes the complete MS, RSG, and
WR wind phases and stops **before** the 4.77-Myr supernova. There is no
companion star. The shared `mod_usr.t` implements piecewise-constant mass-loss
rate and velocity; `cases/wind_history.csv` records the exact adopted values.
Wind temperatures (10,000 K for MS/WR; 1,000 K for RSG) are numerical
assumptions, not values tabulated by the paper.

| Phase | Age (Myr) | Mass loss (Msun/yr) | Wind speed (km/s) |
| --- | ---: | ---: | ---: |
| Main sequence | 0-4.3 | 1e-6 | 2000 |
| Red supergiant | 4.3-4.5 | 5e-5 | 15 |
| Wolf-Rayet | 4.5-4.77 | 1e-5 | 2000 |

The wind enters the radial domain through a **1.5 pc inner spherical
boundary**, matching the paper's wind injection radius but replacing its 2D
volume source. Initially the domain is uniform, stationary, 100 K ISM; the
wind inflates its own bubble. The outer boundary is fixed ISM at 100 pc. The
pilot has 512 base radial cells and at most two AMR levels. This is not a
reproduction of the paper's 2D morphology or resolution. At 1000 cm^-3 the
wind termination region could approach the injection radius; that is a
specific science-validity check before interpreting profiles.

**Radius hold (2026-10-13):** The negative-`k` afterglow density/radius plots
for GRB 080413B sample approximately 0.003-0.1 pc, and GRB 140506A samples
roughly 0.04-0.8 pc. The current 1.5 pc inner boundary lies outside those
regions, so these staged inputs cannot answer whether the model produces the
small wind structures relevant to those fits. These plot radii locate the
afterglow sampling region, not an observed outer bubble wall or a direct
termination-shock measurement. The GRB 210905A negative-`k` fit stretches
to tens-thousands of parsecs and must not set the numerical target without a
fit-quality screen. Shrinking the 100 pc outer box alone will not shrink the
physical bubble. A revised inner-boundary/grid and computational-cost design
is required before compiling or launching; do not quietly reuse this pilot
as the GRB-scale comparison.

The ambient number-density convention is `n = rho / m_p`, as in
[Chrimes et al. (2022)](https://doi.org/10.1093/mnras/stac1646). The three
staged values are the paper's `10^-22.5 g/cm3` (~18.9 cm^-3), 100 cm^-3,
and 1000 cm^-3. At 1000 cm^-3, rho is `1.6726219e-21 g/cm3` or
`16726.219` in the adopted `1e-25 g/cm3` density unit. These are comparison
inputs, not evidence that 1000 cm^-3 is universal around GRB progenitors.

`generate_cases.py` stages all four explicitly labeled physics variants at
each density: hydro, cooling, conduction, and cooling+conduction. It refuses
to overwrite an existing nonempty `cases/` directory. Cooling selects the
pinned AMRVAC v3.1 built-in `cloudy_solar` table and a 100 K floor. Its
identity with the paper's exact CLOUDY table is unverified. Conduction is a
requested extension, not an explicitly specified ingredient in the paper.
The `conduction` and `cooling_conduction` inputs are **held** because earlier
BoOST/2D pilots failed with negative pressure. Generating inputs does not
authorize rerunning them.

To stage inputs without launching jobs:

```bash
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_40_wind_density/generate_cases.py
```

Before any science run: resolve the radius hold above, compile against pinned
AMRVAC v3.1, check a
zero-duration initialization, then run a guarded hydro-only short smoke at
1000 cm^-3. Verify normal `Finished AMRVAC` marker, positive finite saved
fields, expected endpoint, boundary mass flux, and advancing late-phase wind
through both 4.3 and 4.5 Myr. A process exit code of zero alone is
insufficient after prior MPI aborts. Only then consider cooling; conduction
and combined variants need a separate stability decision. No convergence
claim follows from this pilot grid.
