# AMRVAC October 9 wind-bubble audit and VM runs

## Status update: 2026-10-09 21:50 UTC

Guarded `run.exit=0`, the AMRVAC completion marker, and code time 535.5
(5.24 Myr) confirm that the evolving-wind 192- and 384-base-cell jobs
finished on Keohane2 and Keohane3 in 5,173 and 13,148 wall seconds. The
768-cell job on Keohane4 was still advancing at code time 402.48/535.53
(about 75% of the requested simulation time); it had no exit marker yet.
These are execution results, not a spatial-convergence finding.

Two of seven 192-cell constant-wind full-duration cases completed: the
`Mdot=1e-7` Msun/yr case in 13,050 seconds and the `Twind=1e5` K case in
26,877 seconds. The baseline, `Mdot=5e-5`, `Vwind=1500/2500` km/s, and
`Twind=5000` K cases exited 139 with explicit negative-pressure errors.
Separately labeled, matched CFL 0.05 full-duration reruns of the baseline
and 5000 K cases also exited 139 around code time 89. Thus halving the
time step did not cure the full-duration failure. The 384-cell 5000 K
controls likewise failed earlier than the 192-cell case; cooling-off and
hard-30-K-floor controls passed only as diagnostics, not approved physical
models. Preserve the failed runs for a cooling/pressure-positivity and
cold-gas EOS investigation before promoting any endpoint sweep as a
validated physical comparison. Keohane1-3 had no active AMRVAC `tmux`
sessions at this check; only the Keohane4 evolving 768-cell job was active.

Status at 2026-10-09 11:21 UTC: ten full-duration simulations have started;
none has finished yet. This is an execution and methods record, not a claim
of spatial convergence or of physically validated bubble profiles.

Update at 11:51 UTC: the three evolving-grid jobs, three automatic
constant-wind queues, and two matched CFL 0.05 full runs remain active.
The original central and 5000 K CFL 0.1 full runs have failed with explicit
exit 139; the queues advanced. No full-duration science result is yet
validated.

## Provenance and meaning

- Collaborator branch `feature/amrvac-wind-bubble-models` was fast-forwarded
  from `e640710` to Ansh's `ecc7b91` without discarding existing local work.
  The new `CONVERGENCE.txt` and `handoff/RUN.txt` define a 5.24-Myr evolving
  wind run and matched 192/384/768-base-cell comparison. The Windows
  `prepare_resolution_runs.ps1` was not used on the Ubuntu VMs.
- MPI-AMRVAC v3.1 is pinned to
  `244c677fd6095bb019587a2fdc97feb67a66f06a`. The revised evolving
  executable, built on Keohane1 with `setup.pl -d=1` and `make -j1`, has
  SHA-256 `b2b14207397ef1829f2f3eca513bffe4ba50d7ebaef41c651948403e8f3681ff`.
  Identical bytes were staged on Keohane2-4. The constant-wind test variant
  executable has SHA-256
  `dd8eb86b98dfe90d98e225e5550e444eec8fa2e2e11e32b076c1705555869c99`.
- The model is 1D spherical HD in 0.01-8 pc, with 30 K ambient gas,
  `n_H=1e4` hydrogen nuclei/cm3 including helium (`rho=2.34164e-20` g/cm3),
  exact SPEX_DM radiative cooling, and saturated Spitzer conduction with STS.
  The 30 K cooling cutoff has `Tfix=false`, so it is not a hard temperature
  floor. The inherited fully ionized EOS at 30 K remains a physical caveat.
  The cooling startup message separately states an assumed ionization fraction
  of 1e-3 below 10^4 K; that cooling prescription does not fix the EOS
  inconsistency.
  The wind-history loader retains the last row of each rounded duplicate
  age; the lost transition timing cannot be recovered by merely extending
  the stop time. The raw table has 607 rows but only 299 distinct ages.

## Preflight evidence

- The revised evolving source completed four-rank 0.1-code-time (~978-year)
  smokes at 192 cells on Keohane1 and Keohane2, 384 on Keohane3, and 768 on
  Keohane4. Each logged the configured ambient density, temperature, cooling
  cutoff, and loaded history; the `Finished AMRVAC in` marker was present.
- First full-run snapshots at 0.10000 Myr were copied to Lyra and parsed by
  the existing `read_vtu` validator: evolving 192 (241 points), evolving 384
  (457 points), evolving 768 (897 points), and central constant wind
  (385 points) all had finite,
  positive density, pressure, and temperature fields over 0.01-8 pc.
  The evolving snapshots reached about 27 K, consistent with `Tfix=false`
  and confirming that the 30 K cutoff is not a hard gas-temperature floor.
  These VTU arrays are node-interpolated diagnostics, not native-cell
  conservation measurements. At this early age, node-interpolated peak
  densities still rise from 4.11e-20 to 4.52e-20 to 5.04e-20 g/cm3 with
  refinement; they should not be treated as a converged shell diagnostic.
- The supplied constant-wind central case (`Mdot=1e-5` Msun/yr,
  `Vwind=2000` km/s, `Twind=1e4` K) failed at the supplied CFL 0.2 at both
  192 and 384 base cells near code time 0.039. The solver encountered a
  negative pressure; radiative cooling then segfaulted in `findy` (MPI exit
  139). At CFL 0.1, the 192-cell case completed the same short smoke and a
  10-code-time (~98-kyr) run in 191.43 wall seconds on four ranks. This
  establishes a numerical-stability issue, not that the altered CFL has
  delivered temporal convergence. A matched CFL-halving control remains due.
- For a one-factor-at-a-time sweep, a local test variant of `mod_usr.t` adds
  optional constant-wind `usr_list` overrides in Msun/yr, km/s, and K. These
  are applied only when `use_stellar_evolution=false`; Ansh's tracked source
  was not altered. Six four-rank smokes completed at `Mdot=1e-7, 5e-5`
  Msun/yr, `Vwind=1500, 2500` km/s, and `Twind=5000, 1e5` K. Each log prints
  the intended wind values. These endpoint tests do not sample interactions
  among the three parameters. An intentionally invalid `Twind=-2 K` input
  stopped with the expected validation message and guarded exit 128.
- The October 8 matched conduction-on/off and cooling-on/off pilots confirmed
  both terms affect the simulated profiles. Saturation-off failed internally;
  the supplied saturation-on model completed. The guarded launcher requires
  both MPI success and the application completion marker, since one previous
  internal failure returned MPI exit zero. See
  `2026_10_08_ansh_conduction_multivm_audit.md` for the control comparisons.

## Running full study

All full runs target the table endpoint, 5.24 Myr (535.5304793077746 code
units), save at matching 100,000-year intervals, use AMR max level 4, and
use CFL 0.1. This CFL is deliberately lower than Ansh's supplied 0.2 because
of the constant-wind failure; it is held fixed across the spatial comparison.
After normalizing only the `domain_nx1` line, the three evolving input files
have the same SHA-256 (`677e1eae5e5061290d2b17638d29ab33da1690c2b8cd749a8ec3b3bee7ce096a`).
These are independent directories with their own `run.par`, `mod_usr.t`,
binary, history table, input checksums, stdout/stderr, `run.started`, and
`run.exit`. The three evolving source runs use four MPI ranks each:

| Host | Directory under `dense_cooling_ecc7b91/` | Base cells |
| --- | --- | ---: |
| Keohane2 | `evolving_full_192` | 192 |
| Keohane3 | `evolving_full_384` | 384 |
| Keohane4 | `evolving_full_768` | 768 |

Keohane1 runs three four-rank queues (12 of 16 vCPUs in total):

| Queue | Constant-wind directories, in order |
| --- | --- |
| a | `sweep_baseline_full`, `sweep_mdot1e-7_full`, `sweep_mdot5e-5_full` |
| b | `sweep_v1500_full`, `sweep_v2500_full` |
| c | `sweep_t5000_full`, `sweep_t1e5_full` |

The central point is Mdot=1e-5 Msun/yr, Vwind=2000 km/s, Twind=1e4 K.
Only the named parameter changes for each endpoint run. The queues continue
past a failed case but record its failure; they do not silently call it valid.
VM root: `/home/jonathan/GRBs/AMRVAC_Bubble_Models/dense_cooling_ecc7b91/`.
Local exact inputs and launcher: `/Users/jkeohane/GRBs/Run_Staging/amrvac_dense_cooling_20261009/`.
On Keohane1, `constant_queue_{a,b,c}.log` records automatic transitions;
each case's `run.exit` and `run.stdout` is authoritative. On Keohane2-4,
check `evolving_full_{192,384,768}/run.exit` and the completion marker.
While active, `tmux list-sessions` and the last iteration line in
`run.stdout` show progress. A missing `run.exit` is not a success state.

### Failure during the first checkpoint interval

At 11:23 UTC the `sweep_t5000_full` run failed near code time 10.038
(about 98 kyr) with negative pressure at radius 0.476 pc, followed by
radiative-cooling SIGSEGV; its guarded `run.exit` is 139. Queue c recorded
the failure and started `sweep_t1e5_full`. A separate 10.1-code-time
control at CFL 0.05 was launched on Keohane4 in
`sweep_t5000_cfl0p05_10p1/`; its outcome is pending. The 5000 K point
must not be presented as a completed full-duration result, and a smaller
time step is not by itself proof of convergence.
Its `CONTROL_NOTE.txt` clarifies that this is a CFL exception to the general
constant-sweep note; the immutable `run.par` is the authoritative input.
An independent 384-cell, CFL 0.1 control to the same 10.1-code-time age is
in `sweep_t5000_nx384_10p1/`. It failed at code time 1.004 with negative
pressure at radius 0.243 pc in dense shocked gas (guarded exit 139), much
earlier than the 192-cell case. Finer spatial resolution alone does not
repair this instability. The controls vary one numerical dimension at a
time from the failed case.
A further 384-cell/CFL 0.05 diagnostic through code time 1.1 was launched
on Keohane2 in `sweep_t5000_nx384_cfl0p05_1p1/` to test whether halving
the timestep carries the resolved shocked shell past its failure age. It
also failed, at code time 0.987 and radius 0.240 pc. Two matched 384-cell,
CFL 0.05 source-term controls were then started: conduction off on Keohane2
(`sweep_t5000_nx384_conoff_1p1/`) and radiative cooling off on Keohane4
(`sweep_t5000_nx384_cooloff_1p1/`). Each changes just one physics switch;
neither is intended as a final physical model.
The cooling-off control finished normally through code time 1.1 (exit 0).
The conduction-off control still failed with negative pressure at code time
1.009, radius 0.264 pc (exit 139). In this matched setup, cooling is
required for the early 384-cell failure, while conduction is not. This
does not justify turning cooling off for the science run; it directs the
next diagnosis toward cooling-source timestep/positivity handling and the
thin shocked shell.
A separate 384-cell/CFL 0.05 `Tfix=true` control was also launched on
Keohane2 in `sweep_t5000_nx384_tfix_1p1/` to test whether making the
configured 30 K cutoff a hard thermal floor changes this failure. This is
diagnostic only; it is not a physically approved change to the model. It
completed normally through code time 1.1 (exit 0), with cooling and
conduction both enabled. Together with the source-off controls, this
identifies the low-temperature cooling/floor treatment as a practical
stability lever. It does not establish that a hard 30 K floor is physically
correct; the heating model and cold-gas EOS should be reviewed with Ansh.
The 192-cell CFL 0.05 control completed normally through code time 10.1
in 552.76 wall seconds. A new full-duration 5000 K run at that CFL was
therefore started on Keohane4 in `sweep_t5000_cfl0p05_full/`, with a separate
`CONTROL_NOTE.txt` recording the numerical exception. It is not directly
comparable to CFL 0.1 cases without a matched baseline timestep check.
A matched central-wind, 192-cell, CFL 0.05 full-duration run was therefore
started on Keohane3 in `sweep_baseline_cfl0p05_full/`, with the same source
variant and output cadence. This isolates the CFL effect in the baseline
and supplies a like-CFL reference for the 5000 K result.
Separately, the primary central-wind CFL 0.1 run failed at code time 28.243
(about 0.276 Myr), with negative pressure in fast wind at radius 0.793 pc
(`v1` about 2000 km/s). Queue a recorded exit 139 and advanced to the
`Mdot=1e-7` point. Thus even the 98-kyr successful central control was not
enough to establish full-duration stability.
The bad cell is beyond the internal wind-injection region (`Rwind=0.2` pc).
For a 2000-km/s, 5000-K wind, the code's kinetic energy per unit mass is
about 20,000 times its thermal energy. Loss of pressure positivity in this
high-Mach total-energy calculation is one plausible mechanism for the
192-cell failure, but the 384-cell failure occurs in slower dense shocked
gas, so this is not a complete diagnosis. Cooling/conduction source coupling
and pressure positivity near the resolved shell need direct investigation.

## Required follow-through

1. Check every `run.exit` is zero and `run.stdout` has `Finished AMRVAC in`;
   inspect logs and final ages, rather than inferring success from a missing
   `tmux` session. Keep a failed run and its input checksums for diagnosis.
2. Compare 192/384/768 profiles at identical saved ages, especially across
   wind transitions. Use native-cell spherical volumes for shell mass, and
   measure shock radii, shell mass-weighted radius and width, bubble pressure,
   and global mass conservation. Inspect actual AMR coverage at each front.
   Only then apply the provisional <5% radius/mass and <10% width criteria.
   AMRVAC's own `doc/python_datfiles.md` warns that its legacy Python `.dat`
   reader does not support spherical geometry and recommends `yt`; do not
   reuse its Cartesian regridding for shell-mass estimates.
3. Run a matched smaller-CFL control after spatial comparison to check time
   integration. Resolve rounded duplicate stellar ages and the cold-gas EOS
   before interpreting late-time shell details physically. Compare constant
   wind endpoint cases only within this common numerical setup.

William's infrastructure-use log was updated and pushed to
`git.hackhsc.com:prof/research-infrastructure.git` through commit `1b65919`.
