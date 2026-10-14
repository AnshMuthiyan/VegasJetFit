# BoOST p4 added-physics controls (2026-10-09)

## Purpose and provenance

Test Ansh's newer AMRVAC implementation with the **original BoOST evolving
wind**, not a constant-wind substitute. The three matched atmospheric cases
are `pressure_p4_n22`, `pressure_p4_n23`, and `pressure_p4_n24`. The historical
Mac outputs remain untouched under
`Boost_Test_runs_2026_04_25_rtwind_fulltimeline_xmin0p2_p6diag/`.

The new isolated workspace is
`../Run_Staging/amrvac_boost_p4_physics_20261009/`, with separate directories
for hydro only, radiative cooling only, thermal conduction only, and both.
Ansh's user problem was taken from `dense_cooling_run` at source commit
`ecc7b91` and built against MPI-AMRVAC v3.1 commit `244c677`. The BoOST
retarded wind table is numerically identical to the historical one. The new
source adds an explicit optional initial free wind inside the historical
termination radius. The compiled binary SHA-256 on Keohane1-3 is
`046b7402e3525c750ca288a83932e63c5bbcc481a101da9082371fbd80a1d60c`.

All four variants of a given density use the same domain (0.19677-32.36185
pc), base grid (192), AMR maximum level (4), refinement weights (0.4/0.4/0.2),
CFL (0.3), `threestep` integrator, free-wind initialization, BoOST table,
30 K cooling cutoff, and `Tfix=false`. Only the two physics switches change:
`hd_radiative_cooling` (SPEX_DM, exact) and `hd_thermal_conduction`
(saturated Spitzer, STS). Density/T pairs are 1e-22 g/cm3 / 217.44 K,
1e-23 / 2174.41 K, and 1e-24 / 21744.09 K. Each full run is nominally
5.24 Myr. Keohane1, Keohane2, and Keohane3 each run one density with 15 MPI
ranks; Keohane4 was already occupied by another evolution.

## Validation and caveats

All 12 smoke cases completed to 0.000978 Myr with finite positive saved
density, pressure, and temperature proxy, correct ambient density, and
active-physics log markers. All 12 longer checkpoints completed to 0.100000
Myr with five ordered, finite VTU snapshots each. The exact per-case checks
and exploratory hydro-relative differences are in `smoke_validation.csv` and
`checkpoint_validation.csv` in the isolated workspace. These checks do **not**
establish full-duration stability or scientific convergence.

The old Mac hydro profiles are a historical reference, not an exactly
identical v3.1 control. Old `mod_usr.t` used density/velocity conversion
factors that differed from the units AMRVAC used for source terms; the new
matrix uses self-consistent units. The old p4_n22 initial outer density is
1.00000003e-22 g/cm3, matching the new one, but its initial outer thermal
pressure is 1.79484357e-12 dyn/cm2 versus 2.94867169e-12 dyn/cm2 now.
Consequently, an old/new hydro profile difference cannot be assigned to
cooling or conduction. A prior suggestion that the old gas evolved for only
4.09 Myr was **not established**: the old final VTU TIME is 5.2399955 Myr.
The source-term-unit mismatch is the verified concern. Final hydro-only
profiles were compared at matched physical ages as summarized below.

Update after the three full hydro-only controls completed: the new 5.24-Myr
density profiles have broadly similar shapes to the historical Mac profiles,
but they do **not** match exactly. At the final matched age, the mean absolute
log10 density differences across the common radial domain are 0.148 dex
(n22), 0.188 dex (n23), and 0.149 dex (n24); the analogous thermal-pressure
differences are 0.200, 0.224, and 0.229 dex. Sharp displaced interfaces give
much larger pointwise maxima, so the means should not be read as local error
bounds. The old/new differences cannot be assigned to a single cause because
the AMRVAC version, unit handling, initial thermal pressure, and numerical
solver setup changed together. See `matched_age_profile_comparison.csv` and
`comparison_plots/` in the isolated workspace for the measured profiles.

The earlier Ansh evolving-wind runs showed pressure-positivity failures in
some dense, cooling-enabled configurations after short tests had passed.
Each full variant therefore runs in a guarded, non-overwriting directory;
a failed variant is recorded and the next independent variant proceeds.
Do not use a failed result or these preliminary profiles as a fitting
surrogate. The cold-gas equation of state and rounded duplicate BoOST ages
also remain scientific limitations to discuss with Ansh.

All three 192-cell cooling-only full runs subsequently completed to 5.24 Myr,
with 54 finite, positive VTUs each. This establishes numerical completion,
**not** boundary-independent physics. In the last 2 pc of the domain their
final maximum radial speeds are 2.09, 6.74, and 3.18 km/s for n22/n23/n24,
versus 0, 0.037, and 0.032 km/s in the corresponding hydro controls.
The cooling density profiles contain strong outer-domain structure, most
notably n24. `validate_full.py` records these checks in `full_validation.csv`
and flags outer speeds above 0.5 km/s as possible boundary influence; that
threshold is a diagnostic, not a physical acceptance limit.
All three conduction-only full runs also completed. Their outer-2-pc
maximum speeds are 0, 0.027, and 0.035 km/s for n22/n23/n24. Thus the
large far-field motion is specific to cooling, not conduction, among the
completed single-feature controls.

The combined cooling-plus-conduction runs completed for n22 and n24, each
with 54 finite-positive VTUs and a 5.24-Myr endpoint. Their final outer-2-pc
speeds are 2.09 and 3.19 km/s, respectively. The n23 combined run failed
after 48 VTUs (`run.exit=139`). Immediately before the crash, AMRVAC reported
negative code-unit pressure (-8.516e-7) at code time 488.405 (about 4.78
Myr), radius 1.841 pc; the stack trace enters `findy`/`cool_exact` in the
radiative-cooling source. Its last saved 4.70-Myr VTU is finite and positive.
The failed result is preserved, not restarted or treated as a completed
profile. A cooling/pressure-positivity cascade is plausible, but the precise
cause remains unproven and should not be conflated with the outer-boundary
warning.

The code fixes the outer ghost gas at its initial `rhoISM`, zero velocity,
and `TISM`, while radiative cooling can lower pressure in the adjacent
interior. A pressure-driven inward disturbance from this boundary is a
plausible explanation, but requires a larger-domain control to establish.
Do not treat the cooling profiles as converged wind bubbles or launch a
384-cell combined-physics *spatial* refinement solely on these outputs:
halving the cell width at the same outer radius cannot remove a domain
boundary effect. The 192-cell matrix is now complete as 11 successes and
one preserved failure.

## Dispatch and next checks

After all checkpoint VTUs were parsed on Lyra, the full-duration queues were
released at approximately 22:28 UTC on 2026-10-09. Keohane1 runs n22,
Keohane2 n23, Keohane3 n24; each queue runs hydro, cooling, conduction, then
both in separate directories. `run.started`, `run.exit`, `run.stdout`,
`run.stderr`, `input_sha256.txt`, and `<case>.full_queue_log` are the
authoritative run records on each VM under
`~/GRBs/AMRVAC_Bubble_Models/boost_p4_physics_20261009/`.

All 12 full-run directories were pulled to Lyra. `validate_full.py` wrote
`full_validation.csv`, validated the 11 successful runs, flagged n23 both as
failed, and exited nonzero as intended. `compare_full_profiles.py` produced
55 matched-age rows and profile overlays while excluding the failed run.
Inspect the outer-boundary behavior and cold-gas/pressure-floor events before
interpreting shell shapes or launching same-domain higher-resolution physics.

## Weekend spatial-convergence follow-up

Isolated 384-base-cell inputs for hydro-only and cooling-plus-conduction were
prepared for each p4 density at
`cases/<case>_<variant>_<smoke|checkpoint|full>_384/` on Lyra and its assigned
Keohane VM. The 384 full input differs from the corresponding 192 input only
in `domain_nx1` and a corrected explanatory comment about ambient hydrogen
density; executable, AMR depth, wind, domain, CFL, and physics switches are
unchanged. The hydro-only variants passed smoke/checkpoint gates and completed
as detailed below. The combined-physics inputs remain staged, **not
launched**: the wider-domain test confirmed boundary sensitivity in cooling,
and the 192-cell n23 combined run failed. Neither issue is resolved by a
same-domain grid refinement.

## Weekend boundary-placement control

Cooling-only smoke, checkpoint, and full inputs for all three p4 densities
are staged on Lyra and their assigned VMs as
`cases/<case>_cooling_<stage>_domain2x_384/`. The outer radius changes from 32.36185 to 64.52693 pc,
and the base grid from 192 to 384 cells. The inner radius stays 0.19677 pc,
so base and finest physical cell widths remain the same. All other physics,
wind, boundary *prescription*, AMR criteria, CFL, and solver settings are
unchanged. This is a boundary-placement test, not a resolution refinement.
All three 4-rank smokes and 15-rank, 0.1-Myr checkpoints passed finite-positive
field and age validation using `--base-cells 384 --domain-scale 2`. Their
outputs are on Lyra in `results_smoke_domain2x_384/` and
`results_checkpoint_domain2x_384/`. The full-duration cooling-only controls
then completed on Keohane1-3 at 15 ranks each: n22 took 15m28s, n23 14m44s,
and n24 11m02s. They were pulled to `results_full_domain2x_384/`; all 54
saved fields per run were finite-positive and reached 5.24 Myr. The
`full_validation_domain2x_384.csv` and `domain_comparison.csv` contain the
validation and 162 matched-age comparisons. The final-age measurements are:

| Case | Narrow outer speed near 32 pc (km/s) | Wide speed near 32 pc (km/s) | Wide outer speed near 64 pc (km/s) | Mean inner density difference (dex) | Mean inner pressure difference (dex) |
|---|---:|---:|---:|---:|---:|
| p4_n22 | 2.09 | 0.00 | 2.09 | 0.050 | 0.050 |
| p4_n23 | 6.74 | 0.00 | 6.95 | 0.193 | 0.254 |
| p4_n24 | 3.18 | 0.97 | 4.68 | 0.084 | 0.172 |

The mean log differences sample 0.25-30 pc on a common interpolated radius
grid; displaced sharp interfaces have much larger local differences (up to
3.03 dex in n24 density). The far-field flow appears near the *new* outer
boundary and is reduced at the old boundary. This supports boundary-placement
influence, especially for n22/n23, but does not isolate the entire effect of
cooling or validate the shell profiles. The final n24 density spike visibly
shifts between domains. Retain the wide-domain cooling runs as diagnostics,
not fitting templates; investigate the cold-gas treatment and boundary
prescription before claiming physical or spatial convergence. Even a matching
inner profile would not by itself validate the cold-gas physics.

Hydro-only 384-cell tests at the original domain are a separate *spatial*
check. Smokes and 0.1-Myr checkpoints passed for all three densities, and
their full runs completed on Keohane1-3 at 15 ranks. The n22/n23/n24 wall
times were 31m11s/32m01s/22m09s, respectively. All were pulled to Lyra,
and `validate_full.py --base-cells 384` passed 54 finite-positive VTUs and
5.24-Myr endpoints for each. Their final outer-2-pc speeds are 0/0.034/0.032
km/s; none triggered the outer-motion warning. The 162 matched-age hydro
comparisons in `spatial_comparison.csv` give these final-age differences
over a common 0.25-30-pc physical-radius grid:

| Case | Mean absolute log10 density difference (dex) | 95th percentile (dex) | Maximum (dex) | Mean absolute log10 pressure difference (dex) |
|---|---:|---:|---:|---:|
| p4_n22 | 0.029 | 0.146 | 0.708 | 0.0019 |
| p4_n23 | 0.028 | 0.138 | 0.691 | 0.0009 |
| p4_n24 | 0.023 | 0.108 | 0.562 | 0.0009 |

The broad hydro density, pressure, and velocity curves agree closely, while
each density interface shifts visibly with resolution. The local maxima are
dominated by these displaced sharp features, not a domain-wide error. A
single 192-to-384 comparison cannot establish an asymptotic convergence
rate, and hydro convergence would not validate the cooling physics.
Combined-physics 384-cell tests remain
on hold because n23 combined physics failed at 192 cells and cooling showed
boundary sensitivity.
`compare_spatial_profiles.py` compares density and pressure at 54 matched
ages on a common physical-radius grid and writes final radial overlays to
`spatial_comparison_plots/`.

## 2026-10-10 controlled continuation

Jonathan authorized further grid/domain checks while keeping the VMs occupied.
This is a diagnostic ladder, not approval to adopt a profile for fitting.
Three original-domain hydro-only 768-base-cell cases (n22/n23/n24) passed
four-rank smokes and 15-rank 0.1-Myr checkpoints. A twice-as-wide cooling-only
n22 case at 768 base cells passed the same gates. Their isolated 15-rank full
runs are active on Keohane1/2/3/4, respectively. The 384-to-768 original
hydro and wide cooling changes halve cell width at fixed domain; these are
distinct from the earlier 192-to-384 *domain-placement* test, which held cell
width approximately fixed. Input comparison confirmed that new full inputs
change only `domain_nx1` relative to corresponding 384-cell controls.

On validated completion, compare 384 vs 768 at matched ages and inspect
shell/interface motion, outer-boundary velocity, and native-cell shell
measures before any convergence claim. Interpolated pointwise log-density
differences can be dominated by moving discontinuities and do not prove mass
conservation. A stopping criterion must include stable physical shell
location and integrated mass, not merely a small mean log-profile difference.
Cooling also needs a boundary/cold-gas diagnosis before any fitting use.

To avoid idle hosts after validation, wide-domain cooling-only 768 inputs for
n23/n24 are staged on Keohane4, and original-domain conduction-only 384
inputs for n22/n23/n24 are staged on Keohane1/2/3. Each next case requires
its own smoke and 0.1-Myr checkpoint validation before a full run. These
single-physics controls isolate numerical behavior; neither is automatically
the more realistic bubble. Radiative losses and thermal transport can both
occur, while conduction strength and cold-gas treatment require physical
scrutiny. Keep the failed n23 combined case preserved and original-domain
combined 384 cases held. The 15-minute supervisor is active with this exact
queue and validation gates. Full-run results remain pending.

### First 768-cell wide-cooling result

The n22 wide-domain cooling-only full run completed on Keohane4 in 38m28s
at 15 ranks. `run.exit=0`, the AMRVAC completion marker, all 54 finite-positive
VTUs, and the 5.24-Myr endpoint were verified after a non-overwriting pull
to `results_full_domain2x_768/p4_n22_cooling/`. Its final outer-2-pc maximum
speed is 2.25 km/s, so the boundary-motion warning persists. On an
interpolated common 0.25-30-pc radial grid at 5.24 Myr, the wide-domain
384-vs-768 mean absolute log-density difference is 0.123 dex (95th
percentile 0.411 dex), and mean log-pressure difference is 0.034 dex.
These are diagnostics rather than native-cell conservation or shell metrics;
the cooling profile is not demonstrably converged or ready for fitting.
The full 54-age comparison is in
`spatial_comparison_cooling_384vs768_domain2x.csv` and its final overlay is
in `spatial_comparison_plots/`. Keohane4 then passed a four-rank smoke and
15-rank 0.1-Myr checkpoint for wide-domain n23 cooling at 768 cells and
started its isolated 15-rank full run. The three hydro-only 768-cell full
runs remain active on Keohane1-3.

### 768-cell hydro and n23 cooling; conduction hold

All three original-domain hydro-only 768-cell full runs subsequently finished
on Keohane1-3. Their non-overwriting Lyra pulls passed `validate_full.py
--base-cells 768`: 54 finite-positive VTUs and the 5.24-Myr endpoint each.
Final outer-2-pc maximum speeds were 0, 0.0356, and 0.032 km/s for
n22/n23/n24. The 384-vs-768 matched-age hydro comparison contains 162 rows.
At 5.24 Myr, mean absolute log-density differences over interpolated
0.25-30 pc are 0.0199, 0.0203, and 0.0165 dex, smaller than the earlier
192-vs-384 means of 0.029, 0.028, and 0.023 dex. However, displaced sharp
interfaces still yield local maxima of 0.799, 0.756, and 0.607 dex; native
cell shell-position and mass tests remain necessary. These measurements
justify a controlled 1536-cell hydro test, not a convergence claim. The
1536-cell inputs differ from 768 only in `domain_nx1`. Four-rank smokes
and 15-rank 0.1-Myr checkpoints passed saved-field/age validation for all
three. The isolated 15-rank full runs started on Keohane1-3 at approximately
16:16 UTC; full-duration outcomes remain pending.

Keohane4 n23 wide-domain cooling 768 completed at 5.24 Myr with 54
finite-positive VTUs. Its final outer-2-pc maximum speed is 7.02 km/s,
again triggering the boundary warning. The 384-vs-768 final interpolated
mean absolute log-density difference is 0.148 dex (95th percentile 0.584
dex) over 0.25-30 pc. The corresponding matched-age table has 108 rows
for n22/n23. Keohane4 then passed smoke and checkpoint gates for n24 wide
cooling 768 and started the isolated 15-rank full run at 16:14 UTC.

The original-domain conduction-only 384-cell smokes failed for all three
densities after 236-263 steps, at code times 0.048-0.054 and the same
radius (0.85117 pc). Each log reports negative thermal pressure near the
inner shocked-wind region; AMRVAC aborted although MPI returned exit 0.
The guarded wrapper correctly records `run.exit=1` because the normal
completion marker is absent. All three failed directories and logs are
preserved on their VMs and in `results_smoke_384/`. Do not launch their
checkpoint/full stages or infer that a finer grid improves conduction.
The likely numerical sensitivity must be tested in separately labeled
single-parameter controls (for example STS step fraction or CFL), without
silently changing the science model. No cause has yet been established.
Two n22 conduction 384 *smoke-only* controls are staged on Keohane4 for
after its live cooling job: `_sts0p4` changes only `sts_dtpar` from 0.8 to
0.4, and `_cfl0p15` changes only `courantpar` from 0.3 to 0.15. Their
`run.par` diffs confirm one numerical setting changed in each. The pinned
executable SHA matches the failed base case. Neither has run yet; do not
interpret a successful smoke as full-duration stability.

### Wider-boundary diagnostic after all wide cooling controls

The n24 twice-as-wide cooling-only 768-cell full run completed on Keohane4,
was pulled without overwrite, and passed 54 finite-positive VTUs and the
5.24-Myr endpoint. Its final outer-2-pc maximum speed is 4.80 km/s, so
all three wide-domain cooling runs still flag boundary motion. The full
384-vs-768 wide-domain matched-age comparison now has 162 rows. At final
age, n22/n23/n24 mean absolute log-density differences on interpolated
0.25-30 pc are 0.123/0.148/0.0318 dex; local maxima are much larger.
These are not science-ready fitting profiles.

The two isolated n22 conduction 384 numerical-control smokes both failed
despite changing only one setting: `sts_dtpar=0.4` stopped at code time
0.05310 and `courantpar=0.15` at 0.05288, both at r=0.85117 pc. The
baseline `sts_dtpar=0.8, courantpar=0.3` failed at 0.05287 at the same
radius. Their guarded `run.exit=1` and logs are preserved in tagged
`results_smoke_384_*` directories. Neither proposed numerical reduction
removed the early negative-pressure error; do not launch long conduction
jobs or attribute a cause without further analysis.

To test whether the cooling outer disturbance still follows the boundary,
one more isolated n22 cooling-only domain-placement control is running on
Keohane4. It extends the outer radius from 64.53 to 128.86 pc and doubles
base cells from 768 to 1536, preserving physical cell width. A `run.par`
diff confirms only `domain_nx1` and `xprobmax1` changed; wind, physics,
solver, and AMR settings are fixed. Its 4-rank smoke and 15-rank 0.1-Myr
checkpoint passed field/age validation. The 15-rank full run started at
2026-10-10T16:55:48Z. After completion, compare `results_full_domain2x_768`
to `results_full_domain4x_1536` with `compare_domain_profiles.py
--domain-pair 2x-4x`, including motion near both outer radii and the
common inner profile. No extrapolation beyond this single measured control
is preapproved.

### First 2x-to-4x boundary result

The n22 4x-domain/1536-cell cooling-only run completed on Keohane4 in
45m37s at 15 ranks, with `run.exit=0`, a normal AMRVAC completion marker,
54 finite-positive VTUs, and a 5.24-Myr endpoint. Its final outer-2-pc
maximum radial speed is 2.25 km/s, so the disturbance still follows the
moved boundary. Comparing the 2x/768 and 4x/1536 runs at 54 matched ages,
the final mean absolute log-density difference over their common inner
0.25-30 pc is only 1.24e-11 dex; maximum difference 2.24e-8 dex; the
pressure profiles agree exactly at the saved/interpolated precision.
Velocity near the former 64.53-pc boundary is 0 in the 4x run, while it
is 2.25 km/s near the new 128.86-pc boundary. This supports boundary
independence of the *inner n22 profile* once the outer boundary is at
64.53 pc. It does not establish spatial convergence: the separate 384-vs-
768 wide-domain comparison still differs substantially, and no native-cell
mass or shell metric has yet been accepted.

Because n23 had a much larger inner change in the earlier 1x-to-2x
comparison, an n23 2x-to-4x test is scientifically motivated. Its isolated
4x-domain/1536-cell inputs change only domain length and cell count from
the 2x/768 run, retaining physical cell width. Four-rank smoke and 15-rank
0.1-Myr checkpoint passed saved-field/age validation; Keohane4 started the
15-rank full run at 2026-10-10T17:54:47Z. Do not extrapolate the n22 result
to n23 without its measured comparison.
The analogous n24 4x-domain/1536-cell smoke/checkpoint/full inputs are
staged on Keohane4 but not launched. Its earlier 1x-to-2x inner-profile
change motivates the same measured boundary test after n23 completes;
each n24 stage still requires its own validation gate. The n24 full input
diff from 2x/768 again contains only domain length and base-cell count.

### 1536-cell hydro and second 4x-domain cooling results

All three original-domain hydro-only 1536-cell full controls completed on
Keohane1-3 with guarded exit 0, normal AMRVAC completion markers, 54 saved
finite-positive VTUs, and the 5.24-Myr endpoint. None triggers the
outer-boundary speed flag. The 768-vs-1536 matched-age comparison has 162
rows. At 5.24 Myr, mean absolute log-density differences over interpolated
0.25-30 pc are 0.0144/0.0131/0.00419 dex for n22/n23/n24, compared with
0.0199/0.0203/0.0165 dex at 384-vs-768. Local maxima remain
0.871/0.805/0.145 dex at sharp interfaces. The broad profile is improving,
but the interface and native-cell shell/mass metrics have not yet met an
agreed convergence tolerance. These are numerical diagnostics, not final
fitting templates. Do not automatically double the grid again solely to
keep a VM occupied; define and inspect physically relevant shell-position,
mass, and time-step criteria first.

The n23 cooling-only 4x-domain/1536-cell control also completed on
Keohane4, passed the same 54-VTU/5.24-Myr field validation, and retained
an outer-boundary speed warning (7.12 km/s). Against its 2x/768 partner
at the same physical cell width, the inner 0.25-30-pc density profiles
agree exactly at saved/interpolated precision at 5.24 Myr; mean absolute
log-pressure difference is 1.06e-11 dex. Motion at the former 64.53-pc
boundary is 0 in the 4x case, versus 7.02 km/s in the 2x case; motion
follows the new ~128.86-pc boundary. As for n22, this supports inner-domain
independence once the boundary is at 64.53 pc, not spatial convergence.

Keohane4's n24 4x-domain/1536-cell cooling-only smoke (4 ranks) and
0.1-Myr checkpoint (15 ranks) passed guarded completion and saved-field
validation. Its isolated 15-rank full run started at
2026-10-10T18:54:36Z and later completed as recorded below. Keohane1-3 are idle after
their completed hydro controls because no additional full science run has
passed a convergence or physics gate; the original-domain conduction
failure and combined-physics hold remain in force.

### N24 boundary sensitivity and finite 8x test

The n24 4x-domain/1536-cell cooling-only full run has since completed
with guarded exit 0, a normal marker, 54 finite-positive VTUs and 5.24 Myr.
It still has a 6.68-km/s outer-2-pc boundary-speed warning. Unlike n22/n23,
its 2x/768-vs-4x/1536 common inner 0.25-30-pc profile differs strongly:
final mean absolute log-density difference 0.801 dex, maximum 3.80 dex;
mean absolute log-pressure difference 0.529 dex. The density mean first
exceeds 0.001 dex at about 2.2 Myr and 0.1 dex at about 3.0 Myr.
The two runs use the same executable SHA and `mod_usr.t`; their full
`run.par` files differ only in `domain_nx1` and `xprobmax1`, doubled
together to keep the physical base-cell width. The discrepancy is thus a
measured domain-placement sensitivity, not an identified setup mismatch.
Its physical mechanism remains unresolved; do not adopt either n24 cooling
profile as a fitting template.

One finite diagnostic is authorized by this measured discrepancy: compare
the 4x/1536 run with an 8x/3072 n24 cooling-only run at the same physical
cell width. No other physics, solver or wind setting changes. The 8x
4-rank smoke and 15-rank 0.1-Myr checkpoint passed guarded completion,
correct ages and finite-positive saved fields. Before seeing the full
result, use the common 0.25-30-pc profile as a screening criterion:
final mean absolute log-density difference <0.01 dex, maximum <0.1 dex,
and similarly inspect pressure, native-cell interface locations, and
velocity near the former 128.86-pc boundary. These numerical thresholds
are diagnostic, not a physical proof of convergence; failure requires
further diagnosis rather than automatic 16x expansion. Spatial resolution
and conduction-positivity questions remain separate.

The n24 8x-domain/3072-cell cooling full run completed in 34m14s on
Keohane4 at 15 ranks, with guarded exit 0, normal AMRVAC marker, 54
finite-positive VTUs, and the 5.24-Myr endpoint. The 4x-vs-8x comparison
has 54 matched ages. At final age the common-inner 0.25-30-pc mean and
maximum log-density and log-pressure differences are all zero at the
saved/interpolated precision. Across all 54 native grids, the 4x and 8x
profiles have the same radius samples in this region; relative density or
pressure differences occur at only six ages and stay below 1.2e-7. The
strongest final native density-gradient radius is 5.212093 pc in both.
At final age, speed near the former 128.86-pc boundary is 6.68 km/s in
the 4x case and 0 in the 8x case, while the new ~257.52-pc boundary has
7.65 km/s. The predeclared inner-profile screen passes. This supports
inner-region *domain independence* for the 4x configuration at this cell
width; it does not establish spatial/time convergence or validate the
cooling thermodynamics for fitting. No 16x expansion is warranted by this
measured result.

### Finite hydro time-step control

The completed 768-vs-1536 hydro tests improved broad density agreement,
but n22/n23 interface maxima remain ~0.87/0.81 dex. Before attributing
these solely to spatial resolution, run one matched half-CFL test per
case at the same original-domain 1536-cell grid: `courantpar=0.15`
instead of 0.3, with BoOST table, hydro-only physics, AMR, other solver
settings, and all other inputs held fixed. Each case requires its own
4-rank smoke and 15-rank 0.1-Myr checkpoint before a 15-rank full run.
The predeclared diagnostic screen for the 54 matched-age comparisons is
final common-inner 0.25-30-pc mean absolute log-density difference
<0.01 dex, maximum <0.1 dex, and native interface position agreement
within one local 1536-grid cell. These are numerical screening values,
not physical tolerances. Failure calls for diagnosing time discretization,
not automatically halving CFL again or claiming spatial convergence.
The same finite half-CFL test is also justified for n24 cooling on the
4x-domain/1536-cell grid, whose inner region passed the fixed-cell-width
boundary test. Compare it only with that 4x cooling baseline, using the
same predeclared profile/interface screen; the cooling and hydro outcomes
must not be conflated. Do not extend this into an automatic cooling sweep.

All four half-CFL smoke tests completed at 4 MPI ranks and passed
`validate_smokes.py`. Their independent 15-rank 0.1-Myr checkpoints
also passed `validate_checkpoints.py`: five finite-positive VTUs and the
correct endpoint for each. Audited full input diffs show that only
`courantpar` changes from 0.3 to 0.15 in each matched pair; the executable
SHA remains `046b7402e3525c750ca288a83932e63c5bbcc481a101da9082371fbd80a1d60c`.
The isolated full runs started on Keohane3 n24 hydro at 20:16:07 UTC,
Keohane4 n24 cooling at 20:16:10 UTC, Keohane1 n22 hydro at 20:18:14 UTC,
and Keohane2 n23 hydro at 20:18:16 UTC. All used 15 MPI ranks. All four
full runs have now completed and passed their saved-field and endpoint
checks; checkpoint success alone was not used as evidence of full success.

Keohane3's n24 hydro half-CFL full completed in 17,903 s (4 h 58 min)
of AMRVAC time and was pulled to Lyra without overwriting the remote
evidence. Guarded exit 0, the normal completion marker, all 54 finite-
positive VTUs, and the 5.24-Myr endpoint passed `validate_full.py
--base-cells 1536 --numerical-tag cfl0p15`. Its final outer 2-pc speed
is 0.032 km/s (no boundary flag). The 54-age paired comparison in
`Run_Staging/amrvac_boost_p4_physics_20261009/timestep_comparison_hydro_1536_cfl0p3_vs_0p15.csv`
gives final inner 0.25-30-pc mean/max absolute log-density differences
of 1.85e-7/1.22e-5 dex. The strongest native density-gradient interface
is at 0.560616 pc in both runs (zero shift; local cell width 0.002618 pc).
This passes the predeclared *time-step* screen for n24 hydro, but does
not establish spatial or physical convergence.

Keohane1 n22 and Keohane2 n23 hydro half-CFL full runs also completed.
AMRVAC integration times were 18,829 s (5 h 14 min) and 18,612 s
(5 h 10 min), respectively. Each had guarded exit 0, normal completion,
54 finite-positive VTUs, and a 5.24-Myr endpoint; neither raised an
outer-boundary flag. The refreshed three-case validation table is
`Run_Staging/amrvac_boost_p4_physics_20261009/full_validation_1536_cfl0p15.csv`.
The paired 162-row, 54-ages-per-case comparison is in
`Run_Staging/amrvac_boost_p4_physics_20261009/timestep_comparison_hydro_1536_cfl0p3_vs_0p15.csv`.
At final age, n22 has mean/max inner absolute log-density differences
of 1.72e-7/1.32e-5 dex, while n23 has 2.97e-8/8.29e-7 dex. Both
strongest-gradient native interfaces have zero shift at final age;
local cell width is about 0.002618 pc. Thus all three hydro cases pass
the predeclared final-age time-step screen. These small CFL differences
do not remove the much larger 768-vs-1536 localized interface
differences; spatial/physical convergence still requires native-cell
shell and mass criteria. No further automatic CFL or grid ladder is
justified by these controls.

Keohane4's n24 cooling half-CFL full completed in 1:29:32 wall time and
passed the guarded exit, normal completion, 54 finite-positive VTUs, and
5.24-Myr endpoint checks. The 54-age paired comparison with its 4x-domain,
1536-cell baseline is in
`Run_Staging/amrvac_boost_p4_physics_20261009/timestep_comparison_cooling_domain4x_1536_cfl0p3_vs_0p15.csv`.
At final age the common-inner 0.25-30-pc mean/max absolute log-density
differences are 1.06e-5/7.49e-4 dex; the native strongest-gradient
interface is at 5.212093 pc in both runs (zero shift, local cell width
0.01047 pc). This passes the predeclared time-step screen, but the
outer-speed boundary flag remains (6.68 km/s). This neither establishes
spatial convergence nor validates cooling physics or fitting readiness.
Keohane4 is idle after this controlled test, pending scientific review;
no further automatic CFL sweep is justified.

### Pauley Mac cross-platform controls (2026-10-10)

Ansh's `ecc7b91` BoOST problem was built on Pauley404-01/02 against a
separate MPI-AMRVAC v3.1 worktree at commit `244c677`; their existing
v3.2 checkouts were not changed. Both Macs run macOS 27.0.1, Homebrew
GCC 16.2.0 and Open MPI 5.0.11. After the new command-line tools made
the default macOS 27 SDK fail to link (`malformed file` / unknown
`arm64e.x1` architecture), selecting the installed Xcode 26.5 SDK with
`SDKROOT=$(xcrun --sdk macosx --show-sdk-path)` made the build succeed.
This was a per-build environment setting, not a system toolchain change.
Both Mac executables have SHA-256
`24bb1f47e7775210de871d0eb1c737928b5200195d8c99f7d20975f3eb1ef6e6`.

Isolated 4-rank smoke (three VTUs) and 0.1-Myr checkpoint (five VTUs)
gates passed before each full run. The Mac launcher
`Run_Staging/amrvac_boost_p4_physics_20261009/run_mac_pilot.sh` records
input hashes and guarded application completion without Linux-only
`sha256sum` or `time -v`. Full outputs are preserved under
`results_mac_full/`; `validate_full.py --results-root ... --output ...`
found four normal 5.24-Myr endpoints, each with 54 finite-positive VTUs.
The Mac and VM `run.par` inputs match byte-for-byte. These are
cross-platform controls of the same 192-base-cell model, not new physics.

| Case | Mac host, ranks | Mac AMRVAC sec | VM host, ranks | VM AMRVAC sec | VM/Mac time |
| --- | --- | ---: | --- | ---: | ---: |
| n22 hydro | Pauley404-01, 4 | 148.144 | Keohane1, 15 | 907.067 | 6.12 |
| n23 hydro | Pauley404-02, 4 | 149.203 | Keohane2, 15 | 939.522 | 6.30 |
| n24 hydro | Pauley404-01, 4 | 149.441 | Keohane3, 15 | 680.039 | 4.55 |
| n22 cooling | Pauley404-02, 4 | 175.001 | Keohane1, 15 | 835.509 | 4.77 |

`compare_mac_vm_profiles.py` produced 216 matched-age rows in
`mac_vm_matched_age_profiles.csv`, interpolating each node-saved profile
onto the same 1000-point, 0.25-30-pc radial grid. Native saved radii
match for all rows. Across all four cases and ages, the maximum
absolute log-density difference is 2.74e-8 dex and maximum absolute
log-pressure difference is 3.12e-8 dex; final density differences round
to zero at saved precision. This demonstrates platform parity for these
outputs, not spatial convergence. The Mac n22 cooling case reproduces
the VM's 2.09-km/s outer-2-pc speed and boundary flag, so it remains a
diagnostic rather than a fitting template. Different rank counts and VM
sharing make the time ratios practical throughput comparisons, not
per-core hardware benchmarks. Pauley404-03 was not used because its
Xcode license is still unaccepted, blocking Git/toolchain validation.

### Fixed-domain cooling spatial ladder (2026-10-11)

The moving outer compression is not the inner wind-bubble shell. At the
5.24-Myr endpoint its outer density peak follows the box edge as the
physical domain is moved; for n22 the peak is at 30.16, 62.19, and
126.51 pc in the 1x, 2x, and 4x domains, respectively. Similar motion
occurs for n23 and n24. Fixed outer ghost gas adjoining a radiatively
cooling ambient medium is a plausible numerical explanation, but the
mechanism has not yet been proven. Do not interpret this outer peak as
a converged wind-bubble shell or use these controls as fitting profiles.

The inner shell is not yet spatially converged. At the *same 2x physical
domain*, n22 cooling 384-to-768 cells shifts its inner peak from 6.982
to 7.359 pc (peak density contrast 2.34 to 2.58); n23 shifts from
12.698 to 13.212 pc (6.93 to 7.53); n24 shifts from 1.411 to 1.746 pc
and changes peak contrast from 57.33 to 10.46. The earlier 2x-to-4x
and 4x-to-8x domain comparisons kept physical cell width fixed, so they
establish aspects of inner *domain* independence, not spatial convergence.

Jonathan authorized a finite, true spatial refinement at the fixed 4x
domain (~128.86 pc): existing 1536 base cells, then 3072, then 6144
for each of p4_n22/n23/n24, cooling-only. The staged full `run.par`
inputs differ between rungs only in `domain_nx1`. BoOST wind history,
initial and boundary conditions, AMR rules, cooling, source units,
integrator, CFL, and AMRVAC executable are held fixed. Each rung has
an isolated 4-rank smoke, 15-rank 0.1-Myr checkpoint, and 15-rank
5.24-Myr full evolution; a full run requires guarded exit 0, normal
AMRVAC marker, 54 finite-positive VTUs, and the physical endpoint.

All three 3072-cell smokes and checkpoints passed validation. Their
full evolutions began on 2026-10-11 at 02:26 UTC: Keohane1 n22,
Keohane2 n23, Keohane4 n24, each at 15 MPI ranks. All three 6144-cell
smokes passed on Keohane3. Its n22 6144-cell checkpoint passed the
guarded exit, normal marker, five finite-positive VTUs and 0.100-Myr
endpoint. N23 and n24 passed the same checks. The final three-case
6144-cell checkpoint validation CSV is
`Run_Staging/amrvac_boost_p4_physics_20261009/checkpoint_validation_domain4x_6144.csv`.
Keohane3 is now idle because all authorized finer-grid preflights are
complete and the 6144-cell fulls must wait for their paired 3072-cell
full results and scientific comparison. No 6144-cell full may begin until
its own preflights and the corresponding 3072-cell full pass validation
and are compared with 1536 cells. Keep the three 3072 fulls intact
and advancing; do not oversubscribe or overwrite their outputs.

For each matched-age same-domain comparison, inspect the inner shell
on native saved radii (position, width, contrast, and an explicitly
defined swept-mass proxy), as well as density and pressure through the
common 0.25-30-pc region and velocity near the boundary. A smaller
mean interpolated profile difference alone is insufficient: a sharp
shell can move by cells while that mean decreases. Compare changes
1536-to-3072 and 3072-to-6144 against local cell width and each other.
The paired half-CFL controls constrain time-step error separately.
No spatial-convergence or fit-readiness claim is made before both
doublings finish and these native-shell checks are recorded. A failure
is preserved and diagnosed, not restarted blindly.

The n24 3072-cell full run finished first and passed guarded exit 0,
normal AMRVAC completion, 54 finite-positive VTUs, and the 5.24-Myr
endpoint. Its outer-2-pc speed is 6.92 km/s, so the boundary warning
persists. The 54-age 1536-vs-3072 comparison at the same 4x domain is
`Run_Staging/amrvac_boost_p4_physics_20261009/spatial_comparison_cooling_1536vs3072_domain4x.csv`;
the final 0.25-30-pc mean/max absolute log-density differences are
0.1465/3.2398 dex. The final plot shows the inner transition moving
outward; this is not a converged shell. N24's already validated 6144
checkpoint cleared the second-rung gate, and its 15-rank full evolution
started on Keohane4 at 04:13 UTC 2026-10-11.

`Run_Staging/amrvac_boost_p4_physics_20261009/measure_cooling_fronts.py`
adds a reproducible native-grid diagnostic. It defines the inner front
as the steepest positive `d log10(rho)/dr` between 2 and 30 pc, avoiding
the outer boundary-following compression. Density contrast uses median
log densities 0.2-0.5 pc on either side; width is the 10-90% rise in
log density, located by crossings on native saved radii. It reports the
initial uniform ambient mass inside the front,
`(4 pi / 3) rho_ISM R_front^3`, explicitly as a *proxy*, not actual
simulated shell mass. The initial n24 comparison in
`cooling_inner_front_1536vs3072_domain4x.csv` finds the front at
5.2173 vs 6.5026 pc, contrast 1.23e3 vs 1.71e3, and 10-90% width
0.1814 vs 0.1216 pc (17.3 vs 23.2 native radial intervals). The
ambient-mass proxy changes from 8.79 to 17.02 solar masses. A further
6144-cell comparison is required before assessing spatial convergence.

The n22 and n23 3072-cell full runs subsequently finished on Keohane1/2.
Both passed guarded exit 0, normal completion, 54 finite-positive VTUs,
and the 5.24-Myr endpoint; their outer boundary speeds are 2.36 and
7.16 km/s, so boundary warnings remain. The regenerated 162-age
`spatial_comparison_cooling_1536vs3072_domain4x.csv` gives final
0.25-30-pc mean/max absolute log-density differences of 0.1224/5.6078
dex (n22) and 0.1247/5.6052 dex (n23). Native-grid front radii moved
6.3795 to 6.8429 pc (n22) and 12.5990 to 13.0570 pc (n23); n24 moved
5.2173 to 6.5026 pc as recorded above. The corresponding initial-
ambient-mass proxies changed 1606.9 to 1983.1 solar masses (n22) and
1237.7 to 1377.7 solar masses (n23). These are not measured shell
masses. Since all three fronts still shift materially with grid spacing,
the already preflighted n22/n23 6144-cell full runs began on Keohane1/2
at 04:28:53/04:29:00 UTC on 2026-10-11 (15 MPI ranks each). Keohane4
continues n24 at 6144; Keohane3 is free after preflights. The second
spatial rung remains necessary before any convergence assessment.

The n24 second-rung 6144-cell full run on Keohane4 completed at 5.24
Myr with guarded exit 0, normal AMRVAC marker, and 54 finite-positive
VTUs; it was copied to Lyra without overwriting VM evidence and passed
`validate_full.py --base-cells 6144 --domain-scale 4`. Its outer-2-pc
speed is 7.47 km/s, so the boundary warning remains. The 54-age
`spatial_comparison_cooling_3072vs6144_domain4x.csv` gives a final
0.25-30-pc mean/max absolute log-density difference of 0.1292/3.3262
dex. The native inner front moved again, from 6.5026 to 7.6111 pc;
its 10-90% width narrowed from 0.1216 to 0.08625 pc while spanning
23.2 to 33.0 local radial intervals. The initial-ambient-mass proxy
rose from 17.02 to 27.29 solar masses; this is not simulated shell
mass. The full-profile figure shows the broad outer structure closely
overlapping but the innermost front displaced. Thus n24 fails a
spatial-convergence assessment at the tested grids despite earlier
inner-domain independence and the separate half-CFL time-step check.
Do not promote it to a fitting template or infer a physical cooling
front radius. Diagnose the cooling/AMR/front behavior before deciding
whether a further finite refinement is scientifically useful; no
automatic 12288-cell rung is authorized by this result alone.

### Completed three-case cooling spatial ladder (2026-10-11)

The n22/n23 6144-cell fulls then completed on Keohane1/2. Along with
n24, all three passed guarded exit 0, normal AMRVAC completion, 54
finite-positive VTUs, and the 5.24-Myr endpoint after non-overwriting
pulls to Lyra. `full_validation_domain4x_6144.csv` records outer-2-pc
speeds 2.44/7.18/7.47 km/s (n22/n23/n24); all remain boundary-flagged.
The 3072-vs-6144 comparison now has 162 matched ages and three
full-profile plots. At 5.24 Myr, the native inner-front measurements
are:

| Case | Front 1536 / 3072 / 6144 (pc) | Last shift (pc) | Width 3072 / 6144 (pc) | Final mean / max inner log-density difference (dex) |
|---|---:|---:|---:|---:|
| p4_n22 | 6.3795 / 6.8429 / 7.2656 | +0.4227 | 0.1027 / 0.0626 | 0.1106 / 5.6868 |
| p4_n23 | 12.5990 / 13.0570 / 13.4117 | +0.3547 | 0.1369 / 0.0877 | 0.0960 / 5.6545 |
| p4_n24 | 5.2173 / 6.5026 / 7.6111 | +1.1086 | 0.1216 / 0.0862 | 0.1292 / 3.3262 |

The plotted broad profiles often nearly overlap, but each sharp
inner transition shifts by far more than its local native cell width
(about 0.0026 pc at 6144 base cells). The front narrows in physical
units while occupying more native radial intervals. The initial-
ambient-mass proxies at 6144 cells are 2373.8/1493.1/27.29 solar
masses for n22/n23/n24; these are not measured swept-up masses.
Thus the *finite numerical ladder is operationally complete but
spatial convergence is not established for any of the three cooling
cases*. Passing the n24 fixed-cell-width domain test and its 1536-cell
half-CFL test does not resolve the grid-dependent front position.

Before another costly refinement, diagnose when the front trajectories
separate in saved time, whether AMR selects comparable refinement
levels around the front, the cooling length/time versus native cell
width and timestep, and how the 30-K cooling cutoff and source update
behave. Compare to the hydro-only controls to isolate cooling from
pure advection. Any new run should change one numerical/physical
choice at a time and declare its acceptance test in advance. Do not
use these cooling profiles as physical bubble templates yet, and do
not launch a 12288-cell ladder simply because hosts are idle.

An additional read-only diagnostic, `track_cooling_fronts.py`, applies
the same steepest-rising-native-density-gradient locator (2-30 pc) to
all 54 saved ages for each case and grid. It writes 486 rows to
`cooling_inner_front_history_domain4x.csv` and a three-panel plot in
`spatial_comparison_plots/cooling_inner_front_history_domain4x.png`.
The plotted tracks separate early and remain ordered by resolution;
they do not suddenly diverge only near the final age. At 1.0 Myr,
the 1536/3072/6144 front radii are 2.464/2.566/2.651 pc (n22),
4.160/4.325/4.460 pc (n23), and 2.935/3.372/3.724 pc (n24).
At 0.5 Myr, n24 already differs at 2.526/2.796/2.994 pc. This
supports a history-dependent grid effect in cooling/front propagation,
not a single late-time transition. The locator is a diagnostic
definition, not a proof that the steepest gradient is always the same
physical discontinuity at every age; confirm with temperature,
pressure, and AMR-level histories before attributing a mechanism.

`inspect_front_thermal_state.py` now makes the final-age temperature
comparison reproducible in `cooling_inner_front_thermal_state_domain4x.csv`.
It converts saved `Te` with each run's logged temperature unit and
reports medians 0.2-0.5 pc inside/outside the measured front, a median
within 0.02 pc, and the minimum/fraction below 30.5 K within 0.5 pc.
The hot-side median rises with resolution in all three cases: n22
6.02/8.06/9.85 million K, n23 6.51/8.70/10.33 million K, and n24
6.65/8.66/10.76 million K for 1536/3072/6144 cells. This is
consistent with less numerically mixed/cooling hot gas at finer grids,
but does not prove that mechanism. N24's outside median stays about
5,100-5,500 K and its local minimum stays above 5,000 K, so the 30-K
cutoff cannot directly explain its displacement. N22/n23 have gas
below 30 K outside the front; the cutoff stops *radiative cooling*
without reheating and is not a hard temperature floor. Quantify
cooling rates and AMR histories before interpreting those values as
a code defect or physical shell property.

The front-history CSV now includes the native interval width at the
selected front. From 0.5 Myr onward wherever the 2-30-pc locator
finds a front, local widths stay near 0.01047/0.005235/0.002618 pc
for 1536/3072/6144 base cells. These equal the configured finest
level-4 spacing (three binary refinements) to saved precision, so
the tracked front is already at maximum AMR refinement during the
measured evolution. The early `nan` entries mean no qualifying rising
front was found inside the deliberately restricted 2-30-pc window,
not a failed run. Lack of AMR *triggering at the tracked front* is
therefore unlikely to explain the persistent drift; its finite
physical cell width, refinement history elsewhere, cooling at mixed
cells, and source integration remain open possibilities.

### Pinned cooling-source audit (2026-10-11)

The actual MPI-AMRVAC v3.1 source used for these runs is pinned at
`244c677f` in `/private/tmp/amrvac_v31_codex`. Its
`src/physics/mod_radiative_cooling.t` selects the `SPEX_DM` table by
joining Dalgarno-McCray low-temperature cooling to SPEX above
approximately 10^4 K (lines 1010-1027). With `coolmethod='exact'`,
`radiative_cooling_add_source` dispatches to `cool_exact`, which
updates each cell from its local density and thermal state using the
tabulated cooling integral (lines 1364-1409, 1828-1898). The cooling
routine's additional cooling-time timestep limiter is guarded by
`coolmethod == 'explicit1'` (lines 1223-1263), so it does not apply to
these exact-method runs. `rc_split` defaults to false and is not set
in the case `run.par`. These are implementation facts, not evidence
that the spatially discretized hot/cold interface is accurate: an
exact cell-local source update still acts on numerically mixed cell
states. The next read-only check should estimate cooling time and
length on both sides of the tracked fronts, then compare those scales
with saved local cell width and the hydro-only profiles. Do not change
the cooling method or launch another refinement based on this audit
alone.

### Saved-state cooling-time screen (2026-10-11)

`Run_Staging/amrvac_boost_p4_physics_20261009/estimate_front_cooling_times.py`
reads all nine validated cooling runs and the pinned `SPEX_DM` table,
then writes `cooling_inner_front_local_timescale_domain4x.csv` (486
saved ages). It estimates the instantaneous thermal cooling time as
`[p/(gamma-1)] / [1.2 n_H^2 Lambda(T)]`, with `n_H=rho/(1.4 m_p)`,
`gamma=5/3`, and the code's He/H number ratio 0.1. The diagnostic
uses a linear interpolation of the source table in log temperature;
AMRVAC uses a 4000-point reinterpolated table, so these are screening
estimates, not an exact reproduction of the source update. The local
1D CFL estimate is `0.3 dx/(|v|+c_s)` using native saved spacing.
For each detected 2-30-pc front, the CSV records the minimum
`t_cool/t_CFL` among cells within 0.5 pc with `T>30 K`. Ages without
a detected front remain `nan`.

| Case | 1536-cell minimum | 3072-cell minimum | 6144-cell minimum |
| --- | ---: | ---: | ---: |
| p4_n22 | 3.24 | 2.43 | 4.86 |
| p4_n23 | 19.28 | 33.19 | 39.82 |
| p4_n24 | 18.82 | 39.04 | 76.97 |

The lowest n22 estimates occur near the 30-K cutoff, where the
actual energy-loss cap can only reduce cooling; they are therefore
conservative for this local screen. All measured ratios exceed one,
but n22's early-time margin is modest. The saved states, approximate
table lookup, and local CFL upper bound do **not** establish coupled
time-step convergence or rule out unsaved transients. They do not
measure spatial convergence either. In particular, exact cell-local
cooling can still act on grid-dependent mixed hot/cold cells. A
finite next test should target that mechanism only after comparing
hydro controls and cooling-zone structure; do not interpret this
screen as a reason to launch another resolution rung automatically.

### Authorized continuing spatial ladder (2026-10-11)

Jonathan clarified that the fixed-domain cooling grid should keep
doubling while the Keohane VMs are available. The immediate next rung
is 6144 to 12288 base cells for all three p4 density cases at the
same 4x physical domain, BoOST wind, exact `SPEX_DM` cooling,
AMR level/weights, CFL, output times, and units. Only `domain_nx1`
changes within each pair. Use isolated directories, a guarded
four-rank smoke, a 15-rank 0.1-Myr checkpoint, and then a 15-rank
5.24-Myr full run on Keohane1/2/4 respectively. Keohane3 will run
an independent n24 4x-domain hydro-only 6144-cell control, gated the
same way, so cooling-specific grid behavior can be compared against
the same-domain hydro profile. Do not overwrite completed runs.

The n24 hydro-only 6144-cell full control completed on Keohane3 and
passed `validate_full.py --base-cells 6144 --domain-scale 4`:
guarded exit 0, normal completion, 54 finite-positive profiles, and
5.24-Myr endpoint. Its outer-2-pc speed is 0 km/s and the validator's
boundary-motion flag is false, unlike n24 cooling at this grid
(7.47 km/s). This is a controlled physics difference at one grid,
not proof that the cooling solution is converged or physically valid.
The isolated hydro-only 12288-cell smoke and 15-rank 0.1-Myr
checkpoint passed guarded completion, finite-positive-field and age
checks. Its 15-rank full started on Keohane3 at 2026-10-11 17:54 UTC;
the endpoint remains unvalidated.

Keohane4's n24 cooling-only 12288-cell full subsequently completed and
passed `validate_full.py --base-cells 12288 --domain-scale 4` after a
non-overwriting Lyra pull: guarded exit 0, normal marker, 54
finite-positive VTUs, and 5.24 Myr. The 54-age 6144-to-12288
comparison and native-front measurement place the final inner front
at 7.6111 versus 8.5031 pc, an 11.7% shift; measured width and
contrast also change. The outer-2-pc speed remains 7.89 km/s with
the boundary-motion flag. A separate 54-age Mac/VM comparison has
identical native radii and final mean/max log-density differences
1.29e-9/1.94e-7 dex. This reproduces the numerical result across
platforms but fails the provisional spatial-convergence screen.
At that point Keohane1/2 cooling and Keohane3 hydro 12288 fulls remained active.

Keohane3's n24 hydro-only 12288-cell full subsequently completed and
passed the same full validator: guarded exit 0, normal marker, 54
finite-positive VTUs, and 5.24 Myr. The outer-2-pc speed remains
0 km/s, unlike the matched cooling result (7.89 km/s). The 54-age
6144-to-12288 hydro comparison has final interpolated inner-grid
mean absolute log-density difference 0.00230 dex (maximum 0.11871
dex), compared with 0.10695 dex (maximum 3.40290 dex) for n24
cooling. This is evidence of a cooling-specific grid discrepancy,
not proof of its physical or numerical cause and not a hydro
convergence claim. Keohane1/2 n22/n23 cooling fulls remain active.

For each validated cooling full result, compare all matched ages and
native front radius, 10-90% density width, density contrast, hot-side
temperature, and outer-boundary motion to the 6144-cell result. A
provisional convergence screen is relative native-front shift <1%,
width and contrast changes <5%, and no new boundary/positivity
failure; require the same screen again on a subsequent doubling
before calling spatial convergence. The screen is stricter than a
broad interpolated-density mean and is not itself physical
validation. Continue rung by rung only after each run passes its
preflights, endpoint/field checks, comparison, and fresh resource
check; stop and diagnose on failure, resource exhaustion, or a
resolved convergence screen rather than silently changing physics.

### Pauley Mac fixed-domain ladder (2026-10-11)

Jonathan also requested the same recursive cooling-resolution study on
Pauley404-01/02/03. This is a cross-platform replication of Ansh's
BoOST p4 cases, not Ansh's separate dense-cooling wind sweep. The
Mac 192-cell controls above used the original 1x domain; they are not
the coarse member of a pure fixed-domain grid comparison. The Mac
ladder instead starts at the same 4x domain and 1536 base cells used
on the VMs, then doubles to 3072 and 6144 without changing physics,
domain extent, AMR rules, wind history, output cadence, or units.

Pauley404-01 runs p4_n22 cooling, -02 p4_n23 cooling, and -03 p4_n24
cooling. The pinned Mac executable SHA-256 is
`24bb1f47e7775210de871d0eb1c737928b5200195d8c99f7d20975f3eb1ef6e6`.
Pauley404-03 has Open MPI 5.0.9 versus 5.0.11 on -01/02, but its
8-rank smoke and checkpoint passed guarded completion and Lyra
finite-positive-field checks. Its Xcode license is still unaccepted;
it can run the pinned binary but cannot currently rebuild it.
All three 1536-cell 8-rank smokes, checkpoints, and full runs passed
validation in isolated directories under
`~/GRBs/AMRVAC_Bubble_Models/ansh_mac_resolution_20261011/`.
Pull completed stages into distinct
`Run_Staging/amrvac_boost_p4_physics_20261009/results_mac_<stage>_domain4x_<cells>/`
folders; `validate_smokes.py`, `validate_checkpoints.py`, and
`validate_full.py` accept `--results-root` with `--output` so Mac
validation never overwrites VM CSVs. Advance a case only after its
smoke, checkpoint, full endpoint and paired spatial comparison pass;
preserve any failure. Compare Mac and VM at matched age and radius
before interpreting a platform or convergence difference. No Mac
cooling profile is yet a fitting template.

The first Mac fixed-domain rung completed on all three hosts. The
1536-cell n22/n23/n24 cooling full runs passed guarded exit 0, normal
AMRVAC completion, 54 finite-positive saved profiles, and the
5.24-Myr endpoint. AMRVAC wall times were 731.010/748.114/745.678 s
on Pauley404-01/02/03, respectively. Their outer-2-pc speed flags
remain 2.25/7.12/6.68 km/s, so operational completion is not
physical validation. `mac_vm_matched_age_profiles_domain4x_1536.csv`
contains 162 paired ages. Every paired snapshot has identical saved
radii; across all cases/ages the maximum absolute log-density
difference is 4.73e-8 dex and log-pressure difference is 2.95e-6 dex
(a localized n23 difference near 4.3 Myr). Final native inner fronts
on the Macs are 6.3795/12.5990/5.2173 pc, matching the VM baseline.
This supports platform reproduction at the tested grid, not spatial
convergence. The 3072-cell eight-rank smokes, 0.1-Myr checkpoints,
and full runs passed on all three Macs. The fulls reached 5.24 Myr
with 54 finite-positive saved profiles each. Outer-2-pc speed flags
remain 2.36/7.16/6.92 km/s for n22/n23/n24, respectively.
`mac_vm_matched_age_profiles_domain4x_3072.csv` contains 162 paired
ages; native radii agree at every age and final inner log-density
differences are zero to saved precision for n23/n24 (n22 final maximum
2.51e-8 dex). The native inner fronts move from 6.3795 to 6.8429 pc,
12.5990 to 13.0570 pc, and 5.2173 to 6.5026 pc at 1536->3072;
these match the VM results but fail the spatial-convergence screen.
The three isolated 6144-cell four-rank smokes and eight-rank 0.1-Myr
checkpoints passed guarded exit, normal completion, and Lyra
finite-positive-field/age checks. After fresh resource checks, the
eight-rank 6144-cell fulls started on Pauley404-01/02/03 at
2026-10-11 15:24 UTC. All three subsequently passed guarded exit 0,
normal AMRVAC completion, 54 finite-positive saved profiles, and
the 5.24-Myr endpoint. The 162 matched-age Mac/VM comparisons have
identical native radii; final inner log-density maxima differ by at
most 4.81e-8 dex. The final native inner fronts are 7.2656, 13.4117,
and 7.6111 pc for n22/n23/n24, exactly the corresponding VM values.
The shift relative to 3072 persists, so these are not spatially
converged or fit-ready. Outer-2-pc speed flags remain 2.44, 7.18,
and 7.47 km/s. Isolated 12288-cell Mac inputs have been staged with
only `domain_nx1` changed; n24 smoke passed and its eight-rank
checkpoint passed on Pauley404-03. N22/n23 four-rank smokes and all
three eight-rank 0.1-Myr checkpoints passed Lyra validation. After
fresh resource checks, isolated eight-rank 12288-cell fulls started
on Pauley404-01/02/03 at 2026-10-11 17:55 UTC. All three
subsequently completed with guarded exit 0,
normal AMRVAC completion, 54 finite-positive VTUs, and 5.24-Myr
endpoints; `full_validation_mac_domain4x_12288.csv` records the
saved-field checks. The 6144-to-12288 comparison covers 162 matched
ages in `spatial_comparison_mac_cooling_6144vs12288_domain4x.csv`.
Final native inner fronts moved 7.2656->7.6222 pc (n22),
13.4117->13.6702 pc (n23), and 7.6111->8.5031 pc (n24), relative
shifts of about 4.9%, 1.9%, and 11.7%. Their measured 10-90% widths
also changed by more than 5%, so all three fail the provisional
spatial-convergence screen. Outer-2-pc speeds remain 2.49/7.20/7.89
km/s and all three retain boundary-motion flags. The matching n24
VM12288 full has validated and agrees with the Mac at 54 ages as
recorded above. N22/n23 VM12288 fulls were still active at that
point; their later results are recorded below. Fit-template approval
remains pending.
Numerical replication is not independent evidence that the cooling
physics is correct.

### Complete 12288-cell comparison and next finite rung (2026-10-12)

Keohane1/2 n22/n23 cooling 12288 fulls completed and were pulled
without overwriting. Along with the earlier n24 cooling and hydro
results, `validate_full.py --base-cells 12288 --domain-scale 4`
passed guarded exit 0, normal AMRVAC markers, 54 finite-positive
VTUs, and 5.24-Myr endpoints for all four. Cooling outer-2-pc speeds
are 2.49/7.20/7.89 km/s for n22/n23/n24 and all retain the boundary
flag; n24 hydro remains at 0 km/s.

The 6144-to-12288 cooling comparison covers 162 matched ages. Native
final front radii shift 7.2656->7.6222 pc (4.9%) for n22,
13.4117->13.6702 pc (1.9%) for n23, and 7.6111->8.5031 pc (11.7%)
for n24. The 10-90% widths narrow by about 38%, 34%, and 46%, and
density contrasts rise by about 10%, 15%, and 20%. All fail the
predeclared convergence screen. The 162-age Mac/VM comparison has
identical native radii and final mean/max log-density differences
of 0/0, 5.71e-11/2.92e-8, and 1.29e-9/1.94e-7 dex respectively.
This is excellent numerical replication, not spatial convergence or
physical validation. The initial-ambient-mass proxy is still not
actual simulated shell mass.

Next finite one-variable test: double `domain_nx1` from 12288 to
24576 at the same fixed 4x domain for n22/n23/n24 cooling, with n24
hydro as an independent control. Hold the BoOST history, wind model,
SPEX cooling settings, AMR level/weights, CFL, physical box, units,
output ages, and binaries fixed within each platform. Hypothesis:
if underresolved cooling-layer mixing drives the drift, the cooling
front will continue to move and sharpen relative to 12288 while the
n24 hydro profile remains much less grid-sensitive. This is a
diagnostic hypothesis, not an established explanation. Predeclared
screen: compare all 54 matched ages and native final front position,
10-90% width, density contrast, pressure, and outer motion; require
front shift <1%, width and contrast changes <5%, no new nonpositive
fields or boundary regression. A passing pair still requires another
doubling before convergence may be claimed. Gate every isolated case
through a four-rank smoke, a 0.1-Myr checkpoint at host-appropriate
ranks, and then a full run only after resource and saved-field checks;
preserve all prior cases. Stop to diagnose any failure or resource
exhaustion instead of blindly escalating.

The 24576-cell cases were staged in separate VM and Mac directories.
For a matching 12288/24576 VM smoke pair, `run.par` differs only in
`domain_nx1`; Mac `run.par` matches its VM counterpart and all three
Mac cases use the same pinned binary SHA-256
`24bb1f47e7775210de871d0eb1c737928b5200195d8c99f7d20975f3eb1ef6e6`.
All four VM cases use pinned binary SHA-256
`046b7402e3525c750ca288a83932e63c5bbcc481a101da9082371fbd80a1d60c`.
Memory/disk checks found 46-62 GiB available memory and >111 GB
free disk on Keohane1-4, and 32 GiB physical RAM with >90% free
memory and >522 GiB disk free on Pauley404-01/02/03. No competing
AMRVAC processes were present. Seven isolated four-rank smokes
started at about 08:56 UTC on 2026-10-12; each was observed with
four live ranks and two early VTUs. All seven later exited 0,
were pulled without overwriting to separate VM/Mac Lyra roots, and
passed `validate_smokes.py --base-cells 24576 --domain-scale 4`
(Mac with distinct results root/output): normal marker, three
finite-positive VTUs, and 0.000978-Myr endpoint. Separate 0.1-Myr
checkpoints then started at 15 ranks on each VM and eight ranks on
each Mac, with all 84 expected ranks observed. Full directories
were staged but unlaunched pending checkpoint validation and fresh
resource checks.

The three Pauley404 n22/n23/n24 24576-cell checkpoints subsequently
finished with guarded exit 0, normal AMRVAC completion, and five
finite-positive VTUs through 0.1 Myr. Non-overwriting pulls saved
them in the separate `results_mac_checkpoint_domain4x_24576/` tree;
`checkpoint_validation_mac_domain4x_24576.csv` records the passed
Lyra validation. Their stderr contains only `/usr/bin/time -l`
statistics. With no competing AMRVAC processes or prior use of the
staged full directories, 93-94% free memory and 521-706 GiB free
disk, their separate eight-rank fulls started at 09:48:48 UTC on
2026-10-12. All 24 Mac ranks were observed. The four Keohane
checkpoints remain active at 15 ranks each and their fulls remain
unlaunched. No 24576 full endpoint or spatial-convergence result
exists yet.

Keohane3's n24 hydro 24576-cell checkpoint later completed with
guarded exit 0, normal marker and five VTUs through 0.1 Myr.
Non-overwriting Lyra pull and `validate_checkpoints.py --base-cells
24576 --domain-scale 4` confirmed finite-positive fields and the
endpoint. Its staged full was unused and the host had no competing
AMRVAC ranks, 46 GiB available memory and 112 GiB free disk. An
isolated 15-rank hydro full started at 10:23:49 UTC on 2026-10-12;
all 15 ranks were observed. Keohane1/2/4 cooling checkpoints remain
active and their fulls unlaunched. No 24576 full is validated yet.

Keohane1/2/4 n22/n23/n24 24576-cell cooling checkpoints then
completed with guarded exit 0, normal markers, and five VTUs through
0.1 Myr each. Non-overwriting pulls joined the hydro checkpoint in
`results_checkpoint_domain4x_24576/`; `validate_checkpoints.py
--base-cells 24576 --domain-scale 4` passed all four VM cases with
finite-positive fields and endpoint. Fresh checks found all three
cooling full directories unused, no competing AMRVAC ranks, and
46/46/62 GiB available memory plus 111/112/112 GiB disk free on
Keohane1/2/4. Separate 15-rank cooling fulls started at 10:38:54
UTC on 2026-10-12, with all 45 ranks observed. Alongside Keohane3
hydro and three Pauley404 cooling fulls, all seven full controls are
now active. No 24576 full is yet validated or spatially compared.

### First 24576-cell full endpoint: Mac n23 cooling (2026-10-13)

Pauley404-02's n23 cooling full completed with guarded exit 0, normal
`Finished AMRVAC in` marker, and 54 VTUs. The non-overwriting Lyra pull
is in `results_mac_full_domain4x_24576/p4_n23_cooling/`.
`full_validation_mac_domain4x_24576.csv` confirms every saved field
finite/positive and the 5.24-Myr endpoint. The outer-2-pc maximum speed
is 7.20 km/s and remains boundary-flagged, close to the validated
12288-cell Mac value of 7.20 km/s.

`spatial_comparison_mac_cooling_12288vs24576_domain4x.csv` compares all
54 matched ages. At 5.24 Myr its inner 0.25-30 pc pressure-grid
comparison has mean absolute log10 difference 0.0136 dex and 95th
percentile 0.0162 dex; the large local maximum is sensitive to
front displacement. Native-grid front measurements in
`cooling_inner_front_mac_12288vs24576_domain4x.csv` give front radius
13.6702 -> 13.8531 pc (+1.34%), 10-90% width 0.05783 -> 0.03929 pc
(-32.1%), density contrast 5.99e5 -> 6.65e5 (+11.1%), and front
slope 222.9 -> 362.8 dex/pc. This is one grid pair, with a flagged
outer boundary and materially changing front structure: no spatial
convergence or fit-template approval follows. The other six 24576
full controls continue; matched 24576 Mac/VM cooling comparison awaits
the corresponding VM endpoint.

### Second 24576-cell full endpoint: Mac n24 cooling (2026-10-13)

Pauley404-03's n24 cooling full completed with guarded exit 0,
normal AMRVAC completion marker, and 54 VTUs. The non-overwriting
Lyra pull is in `results_mac_full_domain4x_24576/p4_n24_cooling/`.
The distinct `full_validation_mac_domain4x_24576_n23_n24.csv`
confirms all 54 saves finite/positive and the 5.24-Myr endpoint.
Its outer-2-pc maximum speed is 8.18 km/s versus 7.89 km/s at
12288; both are boundary-flagged.

`spatial_comparison_mac_cooling_12288vs24576_domain4x_n23_n24.csv`
records all 54 matched n24 ages (108 rows including n23). At
5.24 Myr the inner 0.25-30 pc mean absolute pressure-grid difference
is 0.00347 dex and the 95th percentile is 0.00712 dex, while the
local maximum reflects displaced sharp structure. The native-grid
`cooling_inner_front_mac_12288vs24576_domain4x_n23_n24.csv` gives
front radius 8.5031 -> 9.1585 pc (+7.71%), 10-90% width
0.04647 -> 0.03025 pc (-34.9%), density contrast 2534 -> 2848
(+12.4%), and slope 142.1 -> 230.8 dex/pc. The n24 front is still
moving and narrowing materially. This pair, with a flagged outer
boundary, does not establish convergence or fitting readiness.
Five original 24576 fulls remain active. `compare_spatial_profiles.py`
and `measure_cooling_fronts.py` now accept an optional `--output`
for distinct per-milestone CSVs; existing spatial plots are left
untouched on subsequent comparison runs.

### Third 24576-cell full endpoint: Mac n22 cooling (2026-10-13)

Pauley404-01's n22 cooling full completed with guarded exit 0, normal
AMRVAC completion marker, and 54 VTUs. Its non-overwriting Lyra pull
is in `results_mac_full_domain4x_24576/p4_n22_cooling/`. The distinct
`full_validation_mac_domain4x_24576_all3.csv` confirms all three Mac
cooling runs' 54 saved fields finite/positive through 5.24 Myr. For
n22, the outer-2-pc maximum speed is 2.52 km/s versus 2.49 km/s at
12288; both are boundary-flagged.

`spatial_comparison_mac_cooling_12288vs24576_domain4x_all3.csv` now
covers all 162 matched cooling ages. For n22 at 5.24 Myr, the inner
0.25-30 pc mean absolute pressure-grid difference is 0.0204 dex and
its 95th percentile is 0.0504 dex. The separate native-grid
`cooling_inner_front_mac_12288vs24576_domain4x_all3.csv` gives n22
front radius 7.6222 -> 7.9112 pc (+3.79%), 10-90% width
0.03862 -> 0.02389 pc (-38.1%), density contrast 6.31e5 -> 6.84e5
(+8.34%), and slope 319.2 -> 540.8 dex/pc. All three Mac cooling
fronts moved and narrowed materially from 12288 to 24576; this is
not spatial convergence. All three Mac hosts are idle, while four
Keohane VM 24576 fulls continue. Matched 24576 Mac/VM cooling
comparison and any further rung need those VM endpoints and a
separate science/resource decision, respectively.

### Curated results publication (2026-10-13)

The three validated Pauley404 24576-cell cooling fulls, their
12288-to-24576 matched-age and native-front comparisons, prior
validated 12288 controls, and per-case Pauley input/hash records were
published as a compact snapshot at
`AnshMuthiyan/VegasJetFit` branch `codex/boost-p4-results-2026-10-13`,
commit `e2dbd67`, directory
`amrvac_simulations/results/boost_p4_2026_10_13/`. Raw VTUs and
active VM partial outputs were not published. The four VM 24576 fulls
continue; no convergence or fit-template approval is implied.

### Published original-domain 192-cell physics matrix (2026-10-13)

The already completed 192-cell controls were published separately on
`AnshMuthiyan/VegasJetFit` branch `codex/boost-p4-results-2026-10-13`
at commit `cbc1292`, in
`amrvac_simulations/results/boost_p4_192_physics_2026_10_13/`.
It contains validation and historical-comparison CSVs, final-age PNGs
and a download ZIP, and byte-identical run settings/hashes/exits for all
12 cases. The n23 combined failure stdout/stderr are included; it was
not retried. Cooling-only and conduction-only completed for all three
densities, while combined cooling plus conduction completed only for
n22/n24. This publication made existing results accessible; it did not
run new simulations or imply that the distinct 24576-cell cooling-only
series has a matched conduction-on counterpart.

### Keohane3 n24 hydro-only 24576-cell full (2026-10-13)

The fixed-4x-domain n24 hydro-only full finished normally on Keohane3:
guarded exit 0, 54 VTUs, 5.24-Myr endpoint. A non-overwriting pull to
`results_full_domain4x_24576/p4_n24_hydro/` passed
`full_validation_domain4x_24576_hydro_n24_20261013.csv`: every saved
density, pressure, and temperature-ratio field is finite and positive;
velocity is finite, radii and ages are ordered. The final minimum density
and pressure are 1.18e-27 g/cm^3 and 2.58e-14 dyn/cm^2. The outer 2 pc
remain at ambient density and 0 km/s, so the boundary flag is false.

`spatial_comparison_hydro_12288vs24576_domain4x_20261013.csv` compares
all 54 matched ages against the validated VM 12288 hydro full. At the
5.24-Myr endpoint, the mean absolute log-density/pressure differences
over 0.25-30 pc are 0.00252/0.000481 dex; the local maxima are
0.157/0.819 dex. The separate native-grid
`hydro_inner_front_12288vs24576_domain4x_20261013.csv` gives front
radius 6.7447 -> 6.7421 pc, 10-90% width 0.3526 -> 0.3812 pc,
and density contrast 404 -> 511. These are diagnostic definitions,
not a proof of spatial convergence. No Mac hydro 24576 counterpart was
requested or run; three VM cooling 24576 fulls remain active.

### 24576-cell VM cooling ladder intentionally stopped (2026-10-13)

At Jonathan's direction, Keohane1/2/4 n22/n23/n24 cooling-only
fixed-4x-domain 24576-cell fulls were interrupted at 23:59:02 UTC.
Their guarded `run.exit=1` and MPI exit 1 mean intentional cancellation,
not a diagnosed instability. All 45 AMRVAC ranks exited. The partial
output counts are 26/25/31 VTUs, respectively; these are not complete
54-VTU, 5.24-Myr runs and were not passed through the full validator.
Their original VM files remain intact, with non-overwriting Lyra copies in
`Run_Staging/amrvac_boost_p4_physics_20261009/results_stopped_domain4x_24576/`.
The three completed Mac cooling fulls and the completed Keohane3 hydro
full are unaffected. The planned matched 24576-cell Mac/VM cooling endpoint
comparison cannot be performed, and the available grid pairs do not
establish convergence. The monitoring heartbeat is paused; no further
high-resolution rung or replacement run is authorized.
