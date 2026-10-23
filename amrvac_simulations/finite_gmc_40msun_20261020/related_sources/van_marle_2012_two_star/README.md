# van Marle et al. (2012) two-star AMRVAC comparison

Status: **12 pilot inputs configured; all 12 initialization checks passed, but
all 12 time-advancing smokes failed at the first timestep. No full simulation
or scientific result is validated.** This is a new campaign, not a
continuation of the stopped BoOST resolution ladder.
The source paper is A&A **541**, L8, DOI
[`10.1051/0004-6361/201219180`](https://doi.org/10.1051/0004-6361/201219180).
The local PDF is in the shared `Reference/Literature/` collection.

## Comparison matrix

`generate_cases.py` creates twelve isolated case directories: 40-solar-mass
star alone, 25-solar-mass star alone, and both stars, each with hydro only,
cooling only, conduction only, and cooling plus conduction. The generated
`cases/matrix.csv` labels every physics switch. No launcher is included;
generating inputs does not start AMRVAC. Each case uses a separate output
prefix and points to the shared `mod_usr.t` source. In that CSV, `not_run`
means **no production run**; isolated initialization and smoke diagnostics
described below were attempted in remote scratch only.

## Paper-defined setup

- 2D cylindrical `(r,z)` grid, `r=0..100 pc`, `z=-100..100 pc`, matching the
  paper's 100 x 200 pc size. Ambient mass density is `10^-22.5 g cm^-3`,
  initially stationary at 100 K. The paper describes this as about 20
  particles per cubic centimeter, depending on composition.
- Each active star injects wind within a 1.5 pc sphere. For the paired case,
  the stars are 16.2 pc apart on the symmetry axis. We center them at
  `z=-8.1` and `+8.1 pc`; this placement is inferred from the separation and
  figures, not explicitly fixed by the paper. Single-star cases use `z=0`.
- 40-solar-mass star: MS to 4.3 Myr (`1e-6 Msun/yr`, `2000 km/s`), RSG to
  4.5 Myr (`5e-5`, `15`), WR to 4.77 Myr (`1e-5`, `2000`), then a `10 Msun`,
  `1e51 erg` supernova in a 0.75 pc sphere.
- 25-solar-mass star: MS to 6.5 Myr (`2e-7`, `1500`), RSG to 7.0 Myr
  (`1e-5`, `15`), then a `7 Msun`, `1e51 erg` supernova in a 0.75 pc sphere.
  All cases are configured to 7.1 Myr for common output ages; the 40-star
  single case's post-SN evolution extends past the paper's single-star figure.

## Explicit approximations and gates

- The paper used a solar-metallicity CLOUDY cooling curve that is not printed
  in the PDF. The pinned AMRVAC v3.1 source **does contain** a 151-point
  `cloudy_solar` log-temperature/log-cooling table (10 to 10^9 K), credited
  in its source to Wang Ye in 2011. This is plausibly the paper's curve but
  has not been proven identical to the authors' run inputs. The current
  cooling-on `run.par` files still select `SPEX_DM` as a **proxy** with a
  100 K floor; changing that switch requires an explicit, documented choice
  and fresh tests, not a silent edit. The current cooling cases are not
  numerical reproductions of the published cooling model.
- The paper explicitly says radiative cooling was included but does not
  specify an active thermal-conduction implementation in its numerical
  setup. Conduction-on cases are a requested extension. They use AMRVAC's
  saturated thermal-conduction option and super-time-stepping, not a
  paper-calibrated conductivity. Cooling-plus-conduction has failed in
  earlier, different 1D BoOST controls; these new cases must pass separate
  stability checks before any science comparison.
- Wind temperatures are not tabulated in the paper. We use 10,000 K for
  MS/WR and 1,000 K for RSG as setup assumptions. The fixed fully-ionized
  AMRVAC v3.1 equation-of-state composition is also an approximation for a
  cold ambient medium. Photoionization is omitted, as in the paper.
- The injection sphere has a capped `1/r^2` density near its center to
  avoid a singularity. Its surface mass flux matches the tabulated wind.
  The supernova callback resets the inner 0.75 pc to the tabulated ejecta
  mass and thermal energy at the timestep crossing the event age. This
  event behavior, especially across integrator substeps and restarts, still
  needs a dedicated smoke test before a full run.
- The generated inputs are **pilot scale**: 120 x 240 base cells and two
  AMR levels, at most 240 x 480 effective cells. The paper used four AMR
  layers and reached 960 x 1920 effective cells. Its resolution is **not**
  authorized here; the stopped high-resolution decision remains in force.
  The pilot grid resolves the 1.5 pc injection radius by only about 3.6
  finest cells, so morphology and front widths cannot yet be compared
  quantitatively to the paper.

## Before any run

1. Decide whether to replace the current `SPEX_DM` proxy with pinned
   `cloudy_solar`; review fixed composition, wind temperatures, and the
   conduction extension with Jonathan. Preserve all four physics labels.
2. Resolve the first-step negative-pressure failure in the hydro-only case
   before testing any optional physics again. Verify finite-positive fields,
   2D geometry, source-cell mass flux, and no boundary artifacts before
   dispatching the matrix.
   `initialization_only.par` can be appended after a generated `run.par`
   to request a zero-duration initialization check in an isolated directory;
   it is not a substitute for a time-advancing smoke. `short_smoke.par`
   advances 1,000 years and saves the endpoint in isolated scratch, still
   far short of the first 4.3-Myr wind transition.
3. Smoke around the 4.3/4.5/4.77/6.5/7.0 Myr transitions and both SN
   events. Do not interpret any three-system or four-physics comparison
   until those events and all relevant cases have validated endpoints.

## Diagnostic record (2026-10-13)

- The shared source built against pinned AMRVAC v3.1 `244c677` on Keohane1.
  All 12 zero-duration, serial initialization checks produced finite-positive
  VTUs with the expected ambient density and source count; these validate
  **initial states only**.
- Isolated serial 1,000-year smokes for all 12 cases stopped at the first
  hydrodynamic update with `small value of p ... multi-D finite_volume`.
  No endpoint VTU exists. AMRVAC's `MPI_ABORT` reported errorcode 0, so a
  process exit code of 0 is **not** evidence of successful completion; require
  the `Finished AMRVAC` marker and the expected saved age.
- Hydro-only `star40` reached two steps with `courantpar=0.01` and a tiny
  `time_max=1e-5` code units, but a separate 1,000-year low-CFL smoke still
  stopped on step 2 with negative pressure near the wind center. Reducing
  CFL alone does not fix this. Do not use a positivity repair, smoothing,
  higher resolution, or altered wind physics without a documented science
  decision and new validation. Do not retry the failed conduction/combined
  cases during hydro diagnosis. All diagnostic runs remain isolated in
  Keohane1 `/tmp/van_marle_2012_*_20261013/`; no production job was started.

Input generation command (does not start AMRVAC):

```bash
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_2012_two_star/generate_cases.py
```
