# Ansh dense-cooling bubble: conduction and four-VM audit (2026-10-08)

## Scope and provenance

The input is Ansh's `feature/amrvac-wind-bubble-models` commit `e640710`
(`dense_cooling_run/{mod_usr.t,amrvac_evolving.par,stellar_evolution.dat,handoff/RUN.txt}`).
The executable on every Keohane VM was built from MPI-AMRVAC v3.1 commit
`244c677fd6095bb019587a2fdc97feb67a66f06a`. Input and binary SHA-256
hashes matched across hosts. This is a 1D spherical hydrodynamic wind bubble,
not a GRB fit, 2D polar wind, or complete AMRVAC profile library.

Each pilot used the submitted code and physics flags but stopped at code time
45 (0.4403 Myr) and saved every 10 code units. One four-rank MPI run was
dispatched simultaneously to each VM, each in an immutable directory under
`~/GRBs/AMRVAC_Bubble_Models/dense_cooling_e640710/`. The independent
parameters were:

| VM | Nominal n (cm^-3) | Ambient T (K) | rho (g cm^-3) | Wall time |
| --- | ---: | ---: | ---: | ---: |
| Keohane1 | 100 | 10 | 1.6726e-22 | 4:40 |
| Keohane2 | 1,000 | 20 | 1.6726e-21 | 4:04 |
| Keohane3 | 10,000 | 20 | 1.6726e-20 | 3:47 |
| Keohane4 | 100,000 | 40 | 1.6726e-19 | 3:31 |

These times are for different density/temperature cases and cannot be used
as a cross-VM speed ranking.

All four exited 0, printed the normal AMRVAC completion marker, initialized
Spitzer conduction, and produced six increasing-time VTU snapshots each.
Parsed radius, density, pressure, and temperature fields were finite and
positive; outer 0.5 pc density remained at the requested ambient value to
better than 5e-8 fractional difference at the final snapshot. No warnings
were found in the six run logs. The four-rank jobs each used about 398-399%
CPU by `/usr/bin/time`; the reported maximum RSS was about 58-60 MiB per
process, not an aggregate MPI memory measurement. These short jobs establish
that four different cases can run concurrently, one on each VM, without an
observed resource bottleneck. They do not establish full-history stability.
Final maximum temperatures were approximately 3.0e6, 3.2e6, 2.1e6, and
2.2e4 K for Keohane1-4 respectively; the densest ambient case cools much
more strongly in this early pilot. This is a model output, not a physical
interpretation approved for the eventual surrogate.

## Conduction and cooling are active

The supplied `.par` explicitly sets `hd_thermal_conduction=.true.`,
`tc_saturate=.true.`, `sts_method=1`, `sts_dtpar=0.8`, and
`sourcetype_sts=2`; it also sets `hd_radiative_cooling=.true.` with
`SPEX_DM`, `coolmethod='exact'`, and `Tfix=.false.`. AMRVAC v3.1's
`mod_hd_phys.t` activates the conduction and cooling modules from these
flags. The runtime `Spitzer HD par` log confirms that conduction initialized.
The [AMRVAC thermal-conduction documentation](https://amrvac.org/md_doc_2thermal__conduction.html)
describes its Spitzer-law, optionally saturated, super-time-stepping path;
the [radiative-cooling documentation](https://amrvac.org/md_doc_2radiative__cooling.html)
describes the high-temperature SPEX/Dalgarno-McCray extension. The online
pages may describe a newer AMRVAC release; the exact v3.1 source was checked
for this audit.

The handoff's `amrvac_evolving.par` is the canonical v3.1 parameter file.
`conduction.par` only repeats flags already present there, so it is not
needed. The nearby `test_GBT.par` uses a different INI-like grammar and is
not a valid v3.1 run input; `run.zsh` and `run_conduction.ps1` are
platform-specific helpers, not authoritative Linux launchers. Archived
snapshot directories do not represent matched physics controls because
their numerical settings differ. The matched controls in this audit were
constructed from a byte-identical baseline `.par` except one physics flag.

Matched four-rank controls changed exactly one flag each from Keohane3's
`n=10^4`, `T=20 K` pilot and ran to the same 0.4403-Myr endpoint. At the
saved-point threshold `T >= 10^4 K`, the hot region reached 0.228 pc with
both physics modules, 0.254 pc without conduction, and 0.624 pc without
cooling. The changes in density and temperature profiles are visible in
the comparison figures. This is a numerical sensitivity test, not a claim
that any one profile has been validated by observations or grid convergence.

For a same-host timing check on Keohane2, the exact 10^4-cm^-3, 20-K
baseline took 3:44.55 with conduction and cooling, versus 3:12.50 with only
conduction disabled. Conduction increased this short-run wall time by about
16.6% relative to the no-conduction control. The repeated baseline's final
VTU was byte-identical to Keohane3's baseline, ruling out a parameter or
output mismatch. This timing ratio may change at later stellar phases and
different grid resolutions.

The third single-flag control kept conduction on but changed
`tc_saturate=.true.` to `.false.`. It failed at code time 0.9081 (about
8,885 yr): the first conduction step produced negative pressure at
`r=0.01260 pc`, adjacent to the inner wind boundary. This is evidence that
flux saturation is numerically important for this setup, not a failure of
Ansh's supplied run, where saturation is **on**. AMRVAC printed `run crash`
but returned MPI process status 0. The pilot launcher was therefore fixed
to require `Finished AMRVAC in` before recording success. Repeating the
unsaturated failure with the repaired launcher yielded `run.mpi_exit=0`
and `run.exit=1`, correctly making the job fail closed. The original failed
run and the launcher-check rerun are preserved separately. The independent
profile validator also rejected the original exit-0 crash because the
normal-completion marker was absent.

## Checkpoint restart

Keohane3 was restarted with the same four-rank executable and parameter
file from the first saved checkpoint at code time 10 (0.09785 Myr), then
continued to code time 45. The uninterrupted and resumed final VTUs have
identical SHA-256 `430450d668382670bbbf29be4a4b6b163efe29884578b7bf4947f4ab3719e827`.
This verifies that a same-host, same-rank restart at this early checkpoint
does not lose the completed calculation. It does not establish safe restart
across AMRVAC versions, rank counts, or different input physics.

## First spatial-resolution check

The Keohane3 baseline used 192 base radial cells, AMR maximum level 4,
and minimum saved-point spacing 0.00520 pc. A matched 384-base-cell case on
Keohane1 used 0.00260-pc minimum spacing and exited normally at the same
0.4403-Myr endpoint. The saved-point `T >= 10^4 K` edge moved from 0.2285
to 0.2493 pc (about 9%). The density peak between 0.1 and 1 pc also moved
from about 0.379 to 0.280 pc. Point-by-point RMS log-density difference
over the inner 2 pc is 0.41 dex, but that number is inflated by comparing
slightly displaced sharp fronts at the same coordinate. The profile shapes
outside the bubble remain similar. This is **not converged enough** to use
the 192-cell bubble structure as a validated final physical profile. A
third resolution and shock-position/cumulative-mass convergence measures
are needed after the composition and endpoint decisions.

On the same Keohane1 VM, the repeated 192-cell baseline took 3:46.23,
while the 384-cell run took 10:46.52, a 2.86-fold wall-time cost for this
early segment. The repeated baseline VTU matched the Keohane3 original
byte for byte. Do not extrapolate this factor blindly to the late wind,
where AMR structure and cooling stiffness may change.

## Remaining science gates

1. The submitted stop is 397.161 code units (about 3.89 Myr), while the
   supplied wind table reaches 5.24 Myr. Decide whether the intended
   physical epoch is 3.89 Myr or the end of the stellar history before a
   full sweep; do not label a 3.89-Myr run as full-history evolution.
2. The current `rho_ism_cgs = m_p * n_nominal` uses a nominal density, not
   self-consistently the hydrogen-nucleus density for AMRVAC's default
   helium abundance of 0.1 by number. The exact v3.1 EOS defaults to fully
   ionized H and He, even for the 10-40 K ambient gas. The low-temperature
   cooling approximation uses a different assumed ionization fraction.
   Reconcile composition, pressure, and the meaning of `n_H` before fitting
   or publishing the bubble grid. Spitzer conduction is physically motivated
   for the hot ionized bubble, not automatically for a cold neutral shell.
   With `Tfix=.false.`, some saved cells fell below the ambient temperature
   (for example 16 K in the 20-K case); the cooling cutoff is not a hard
   thermal floor.
3. The wind table has 607 rows but only 299 unique rounded ages. The loader
   retains the last row of a duplicate-age group. One late group near
   4.79 Myr spans 1.35 dex in mass-loss rate and 391 km/s in wind speed;
   retrieve higher-precision ages or otherwise define the intended sharp
   transition before running beyond the present 3.89-Myr stop.
4. At the initial snapshot, AMR gives an inner point spacing of about
   0.0052 pc (not the coarser 0.0416-pc base spacing). Inner-boundary and
   shell properties still need a spatial convergence check. The 8-pc outer
   boundary is unaffected in these short pilots, but must be checked at
   later ages, especially for low ambient density.
5. The original `dtsave_dat=133.8825` gives only about 1.31-Myr checkpoint
   intervals. Preserve a denser, explicit checkpoint cadence for long runs;
   budget the saved snapshots. A matched early checkpoint restart passed as
   described above, but late-wind restart behavior remains untested.
6. Keep `tc_saturate=.true.` in this model pending a physical treatment of
   the steep inner-boundary conduction front. A job's shell exit code alone
   is insufficient: require AMRVAC's own normal-completion marker and
   finite saved profiles. The corrected pilot launcher does so.

## Reproducibility and next decision

Local complete pilot/control artifacts are in
`/Users/jkeohane/GRBs/Run_Staging/amrvac_dense_cooling_20261008/`.
Each remote run contains its exact `.par`, source `mod_usr.t`, wind table,
binary, input hashes, host/rank/start/finish metadata, standard output,
standard error, exit code, and VTUs. The analysis scripts are
`run_vm_pilot.sh`, `validate_vm_pilots.py`, `compare_vm_pilots.py`, and
`check_restart_resolution.py` in
this directory. Validation figures and CSV metrics are in local
`Run_Staging/amrvac_dense_cooling_20261008/validation/`.

The infrastructure and concurrency test passed. Do not yet launch the
proposed 4-by-3 *production* matrix: the composition/epoch definitions and
spatial-convergence gate are still open. Once those are resolved, use four
simultaneous VM jobs, one per host, with Lyra as the sole collection and
publishing host; four MPI ranks per job is the measured short-run latency
choice, and 1-2 ranks per independent job may improve throughput if the
matrix expands beyond four simultaneous cases.

William's dated infrastructure entry was pushed to
`prof/research-infrastructure`, `projects/keohane/README.md`, at commit
`7d584956ee1ff23866a7233a2da21ec211b4f48e`. It records host use and
resource findings only; the scientific details and exact outputs remain
in this report and the local staging tree.
