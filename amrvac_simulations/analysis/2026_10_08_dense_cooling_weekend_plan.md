# Dense-cooling AMRVAC weekend preflight (2026-10-08)

## Scope and status

Ansh's `feature/amrvac-wind-bubble-models` commit `e640710` supplies
`dense_cooling_run/mod_usr.t`, `amrvac_evolving.par`, the wind history, and
`handoff/RUN.txt`. This is an offline, one-dimensional spherical hydro study,
not a VegasJetFit MCMC run or a two-dimensional polar-wind model. No full
density-temperature sweep has been launched by this preflight.

Use MPI-AMRVAC v3.1 commit `244c677fd6095bb019587a2fdc97feb67a66f06a`
for a version-matched comparison with Ansh's test. Lyra's and Pauley 1/2's
default AMRVAC checkout is v3.2, so set `AMRVAC_DIR` explicitly and build in
an isolated v3.1 tree. Do not replace the existing v3.2 installation.

## Checks completed on Lyra

- Built the four declared inputs from a disposable directory against the
  exact v3.1 commit. A preliminary compile with Lyra's default v3.2 was
  discarded as version-mismatched; the corrected build and all results below
  used `AMRVAC_DIR=/tmp/amrvac_v31_codex`.
- Two-rank starts at (nominal `n_H` in cm^-3, ambient K) = (100, 10),
  (10,000, 20), and (100,000, 40) reached code time 0.05, about 489 years.
  Saved VTU density profiles were finite in all three cases. Ambient density,
  ambient temperature, and cooling cutoff printed the requested values.
- The baseline reached code time 0.5, about 4,892 years, in 6,313 steps;
  saved density remained finite and the shock-heated gas appeared in output.
- A matched baseline to code time 5, about 48,923 years, completed in 64,913
  steps on each of 1, 2, 4, and 8 MPI ranks. Wall times (seconds): 25.29,
  15.73, 12.45, and 40.54, respectively. These are Lyra measurements, not
  VM predictions. Four ranks minimizes one job's wall time; one rank uses
  roughly half the core-seconds of four ranks and is likely preferable for
  throughput across many independent cases. Eight ranks should not be used
  for this small mesh without a changed benchmark. All four reached the same
  simulated endpoint, and the final VTU maximum density matched exactly at
  `4.5646294817816655e-20` g/cm^3.

Smoke output and timing logs are in local disposable
`/tmp/amrvac_ansh_smoke_20261008/`; they are not campaign products.
These short tests do not establish long-time stability, final shell accuracy,
or numerical convergence.

## Science gates before the full matrix

1. The supplied stop time is `397.161` code units, about 3.89 Myr, but
   `stellar_evolution.dat` extends to 5.24 Myr. Confirm whether the intended
   science endpoint is the earlier epoch. If the goal is a pre-collapse bubble
   using the full stellar history, extend the stop time to about 535.5 code
   units and test the changing late wind. Do not label the present 3.89-Myr
   output a final full-history profile.
2. Define whether the requested density is hydrogen nuclei, all particles,
   or another convention. The proposed values in this preflight use
   `rho_ism_cgs = 1.6726e-24 * n` g/cm^3. The hydro/cooling composition and
   the eventual density surrogate must use an explicitly reconciled convention.
3. At the current base grid, `dx=(8-0.01)/192 = 0.0416` pc exceeds the
   0.01-pc inner radius, but AMR refines the initial inner mesh to about
   0.0052 pc. Check the inner wind/ghost geometry and a controlled
   resolution comparison; monitor the outer shock against
   the fixed 8-pc boundary, especially for the lowest density. Preserve
   finite profiles and cumulative-mass checks, not just successful exit.
4. `SPEX_DM` uses the Schure/SPEX high-temperature curve and a
   Dalgarno-McCray low-temperature extension with a fixed ionization fraction.
   This is not a molecular chemistry model for a 10-40 K cloud. Record that
   approximation, especially at the 10 K cooling-table edge.
5. The current `dtsave_dat=133.8825` code units saves snapshots about every
   1.31 Myr. Use denser, versioned checkpoint/profile output through major
   wind transitions (for example 5-10 code units), with a disk estimate and
   restart test. Keep per-run inputs, AMRVAC commit, host, rank count, output
   checksums, and start/end times together.

## Weekend execution strategy

1. Provision v3.1 and the Fortran/MPI toolchain on each selected host, then
   build and smoke-test there. On 2026-10-08 all four Keohane VMs were
   reachable and idle, but `mpif90` was absent; Keohane1 also had no AMRVAC
   source under `/home/jonathan` at depth four. Pauley 1/2 have v3.2 and
   `mpif90`; Pauley 3's Git check was blocked by an unaccepted Xcode license.
   Do not count unprovisioned hosts as runnable.
2. Benchmark the same first 50-kyr segment at 1, 2, and 4 ranks on one VM.
   The 1D mesh may favor several independent one-rank jobs over one large
   MPI job. Cap initial concurrency at 2-4 cases per 16-vCPU VM while
   measuring memory, I/O, and late-time timestep behavior; adjust only from
   measured headroom. A single larger VM is not a prerequisite.
3. Run the four density endpoints/decades at representative temperatures
   through at least a late-wind checkpoint first. Measure wall time per
   simulated interval, minimum timestep, shock radii, finite-state quality,
   and distance from the outer boundary. Stop or revise the grid if any case
   fails a science gate; do not blindly relaunch failures.
4. After those pilots, use a 4 x 3 matrix: nominal densities 10^2, 10^3,
   10^4, 10^5 cm^-3 and temperatures 10, 20, 40 K. Put one case in each
   immutable run directory. Dispatch dynamically to the four VMs, with
   Pauley 1/2 as version-matched overflow/backup. Reserve Lyra for QA,
   collection, and a single publisher to the share folder. Do not depend
   on Carina (laptop) or the student-used PCRC machines overnight.
5. Per case, verify normal AMRVAC termination, finite positive density and
   pressure, profile/checkpoint count, wall/shell location, and that the
   output can be converted to a mass-consistent radial profile. Keep
   failed runs and logs for diagnosis. Only then build the surrogate and
   compare withheld simulations.

Requesting more CPUs or consolidating VMs is premature for this 1D workload.
The next infrastructure need is a consistent AMRVAC v3.1 installation and a
benchmark on the VMs. If measured throughput later
benefits from a different VM layout, ask William with those data.

## Toolchain update, 2026-10-08

The host observations above were made before provisioning. On the same date,
Keohane1-4 were updated with Ubuntu packages `build-essential`, `gfortran`,
`openmpi-bin`, `libopenmpi-dev`, `git`, `perl`, and `rsync`. On each VM,
`mpif90 --showme:command` returned `gfortran`, and `mpirun -np 2 hostname`
completed with two matching hostnames. This establishes the compiler and MPI
runtime, not an AMRVAC build or simulation; the subsequent section records
the version-matched installation and smoke tests. The science gates above
remain pending.
William's infrastructure log records the package change at commit `8002591`.

## VM installation and MPI verification, 2026-10-08

Keohane1 was installed and tested first. The source is pinned in a separate
checkout at `/home/jonathan/codes/amrvac-v3.1-244c677` (Git commit
`244c677fd6095bb019587a2fdc97feb67a66f06a`, tag `v3.1`). Ansh's four
input files and `RUN.txt` from branch commit `e640710` were staged under
`/home/jonathan/GRBs/AMRVAC_Bubble_Models/dense_cooling_e640710/inputs/`;
their hashes matched Lyra. The disposable build and tests are in the sibling
`smoke/` directory. The canonical source and submitted inputs are kept apart
from generated files.

In that `smoke/` directory, use the following version-matched build sequence.
`rank4.par` is a shortened benchmark parameter file, not the submitted
production parameter file:

```sh
AMRVAC_DIR=/home/jonathan/codes/amrvac-v3.1-244c677 /home/jonathan/codes/amrvac-v3.1-244c677/setup.pl -d=1
AMRVAC_DIR=/home/jonathan/codes/amrvac-v3.1-244c677 make -j1
mpirun -np 4 ./amrvac -i rank4.par
```

The first fresh `make -j4` failed because the shared library was started
before `amrvac.h` was copied into its build directory; `make -j1` completed.
This is a build-order race, not a limit on the MPI simulation. Do not confuse
the compile `-j1` setting with the `mpirun -np` runtime rank count. On these
identical VMs, future updates may copy a verified binary instead of rebuilding
four times, then run a local MPI smoke test on each host.

Keohane1 completed 2-rank starts at nominal `(n_H, T)` of `(100, 10)`,
`(10,000, 20)`, and `(100,000, 40)` to code time 0.05 and a baseline pilot
to code time 0.5. Parsed VTUs had finite, positive density, pressure, and
temperature ratio. The matched baseline to code time 5, about 48.9 kyr,
completed at 1, 2, 4, and 8 ranks in 44.50, 26.00, 24.36, and 28.27 wall
seconds respectively. All four final parsed profiles contained 241 unique
radial points and agreed exactly in the saved floating-point values. Four
ranks gave the shortest latency on this segment; 1-2 ranks may give greater
throughput across independent cases. This is a short-segment benchmark only.
An invalid negative ambient-density parameter failed with exit code 128 and
the expected `rho_ism_cgs must be finite and positive` message.

After Keohane1 passed, Keohane2-4 received the same pinned source and inputs.
Each independent serial build, 2-rank short smoke, and 4-rank 50-kyr test
completed. All four executables have SHA-256
`3cbadc3cfd34437196b63342305775374704681c0410207a698813042549da41`,
and their 4-rank final profiles match point-for-point. Source commit and all
five submitted input hashes matched across hosts. GNU Fortran 13.3.0 and
Open MPI 4.1.6 were used on Ubuntu 24.04. No full production matrix has been
launched; the science gates above still apply. The infrastructure usage log
was pushed to William's Git server as commit `a1a53a8`.

## Four-VM physics pilot, 2026-10-08

One four-rank job was run simultaneously on each VM for 0.4403 Myr at
nominal `(n,T)=(100,10), (1000,20), (10000,20), (100000,40)`. All four
exited normally; 24 saved VTUs passed finite-profile and ambient-boundary
checks. Wall times were 4:40, 4:04, 3:47, and 3:31 respectively. Matched
single-flag controls show that disabling conduction or cooling materially
changes the profiles. A same-host, same-rank restart from a saved checkpoint
reproduced the uninterrupted final VTU byte for byte. A doubled-resolution
case also finished, but shifted the hot-bubble edge about 9% and changed the
inner shell, so the current grid is not yet a validated final resolution. See
`2026_10_08_ansh_conduction_multivm_audit.md` for the full results and the
newly identified composition/ionization and rounded stellar-age issues.
An unsaturated-conduction control crashed with negative pressure near the
inner boundary; the supplied saturated setting remained healthy. AMRVAC
returned MPI status zero on that internal crash, so the pilot launcher now
requires its normal-completion marker before writing a successful `run.exit`.
These are science gates, so the 4-by-3 full-duration matrix remains unlaunched.
