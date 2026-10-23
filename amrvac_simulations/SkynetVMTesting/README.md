<!-- Purpose: Explain the four 25 Msun wind simulations using parameter/user-module changes on unmodified AMRVAC 3.2. -->

# SkynetVMTesting

For **modeling-prod01-02**, transfer the clean [VanMarle25Msun](VanMarle25Msun/README.txt)
subfolder. It includes the current inputs, a no-sudo MPI/AMRVAC installer,
and a four-case launcher. Follow its README to install and build in your
home directory; no existing `/skynet/amrvac3.2` installation is required.

For the **40 Msun production run on modeling-prod01-01** that stopped with
`Ambiguous fine-block geometry`, use [RECOVERY40_GEOMETRY.txt](RECOVERY40_GEOMETRY.txt)
and `resume_40Msun_geometry.par`. That overlay selects the reported latest
`recovery40/test0050.dat`, retains its age and iteration, and requires the
updated user module plus the original 40 Msun primary parameters.

The four case `run.par` files now start a fresh **25-solar-mass** wind model
at age zero and stop at **7 Myr**. They select
[stellar_evolution_25Msun.dat](stellar_evolution_25Msun.dat): MS until 6.5 Myr,
then RSG until 7 Myr. No WR phase is specified in the screenshot. The old
40-solar-mass checkpoints are retained but are not loaded by these inputs.

Use **unmodified AMRVAC 3.2**. No AMRVAC source patch is needed or installed.
`mod_usr.t` uses the existing `phys_handle_small_values` callback after mesh
refinement. If a child pair has an invalid thermal state, it replaces both
children with their volume-weighted conserved average. This preserves pair
mass, momentum and total energy without adding heat; an invalid pair average
still aborts. Actual fine-grid volumes are identified from the supplied
coordinates. `ghost_copy` avoids invalid interpolated coarse/fine ghosts.
Coordinate matches need not identify a unique allocated entry. The user
hook now accepts multiple entries only if their positive, finite cell
volumes agree within 64 machine epsilons; conflicting volumes still abort.
This fixes the later `Ambiguous fine-block geometry` abort without changing
the volume-weighted fallback or engine code. Its direct before/after
regression is recorded in `phase2_diagnostics/geometry_alias_regression/`.
Startup initializes the analytic freely expanding MS wind inside 0.03 pc;
ambient gas outside stays unchanged. This avoids the separate instability
caused by switching the wind on directly against dense boundary cells.
The usual TVDLF/minmod reconstruction remains in use throughout the domain.
The user module retains the prescribed wind face, phase-aware CFL and guards.

Tests use official v3.2 commit c45d84650ed3379eb22dcfa6fb927a45734e5d8c with
bounds checks and floating-point traps. The build checks hashes for all 187
core source/architecture files and confirms that they stayed unchanged.
Current test scope is recorded in `phase2_diagnostics/user_only_validation.json`.
All four fresh 25-solar-mass cases completed 1,000 years: 160 valid saved
states, zero numerical energy repairs, and zero recorded TC floor events.
The historical failure regression passed 1,000 years with 39 conservative
pair fallbacks and maximum measured relative conservation error 1.59e-16.
The earlier source-patch tests in `ConservativeAMRRestart` are historical;
do not install that patch for these inputs. Full 7-Myr stability is untested.

The user hook adds checks during refinement, but searches for cell volumes
only when it finds an invalid pair. Audit counters share the existing MPI
reductions. Moving checks into a user module does not eliminate their cost;
no isolated runtime percentage has been measured for either implementation.

## Physics modules

All cases use ideal-gas hydrodynamics with total energy and gamma = 5/3.

| Case folder | Conduction | Cooling | Initial age |
|---|---|---|---|
| `tc_off_rc_off` | Off | Off | 0 |
| `tc_on_rc_off` | On | Off | 0 |
| `tc_off_rc_on` | Off | On | 0 |
| `tc_on_rc_on` | On | On | 0 |

Conduction: saturated Spitzer transport with super-time-stepping.
Cooling: `SPEX_DM`, exact integration, and `Tfix` at 100 K. `Tfix` acts only in
cooling-enabled cases; cooling-disabled gas may expand below 100 K.

## Run on the Linux VM

1. Transfer `mod_usr.t`, `stellar_evolution_25Msun.dat`, all four `run.par`
   files, and `amrvac.h`. Keep their relative folder layout. No source-patch
   files or Python validation scripts are needed on the VM.
   Open a terminal in `SkynetVMTesting`.
2. Point to an **unmodified 3.2 source tree** and rebuild the user problem.
   If the earlier patch was already installed in a tree, use a separate stock
   3.2 tree. Use a Linux path without spaces and a working MPI installation.
   Commands below use the VM's **tcsh** shell:
   ```tcsh
   setenv AMRVAC_DIR /absolute/path/to/amrvac3.2
   perl "$AMRVAC_DIR/setup.pl" -d=1
   make clean F90=mpifort
   touch mod_usr.t
   make hdr F90=mpifort
   make -j4 F90=mpifort F90FLAGS='-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'
   ```
   This compiles the new `mod_usr.t` and links a new `amrvac` using the stock
   library. `make` builds that library if necessary, without editing core
   sources. `make clean` removes local compiled artifacts, not outputs or
   checkpoints. No sudo or AMRVAC source patch is needed. Validation compiler
   flags include bounds checks; their runtime cost has not been isolated.
3. Choose a case and run from its directory. This example activates both
   conduction and cooling and initializes the 25-solar-mass ambient gas.
   ```tcsh
   cd tc_on_rc_on
   mkdir -p output_25Msun
   setenv OMP_NUM_THREADS 1
   nohup mpirun --bind-to none -np 8 ../amrvac -i run.par < /dev/null >& run.log &
   ```
   Replace the case name to run another combination. To resume later, set
   `restart_from_file='output_25Msun/testNNNN.dat'` to a completed 25-solar-mass
   checkpoint. Keep `reset_time=.false.` and `reset_it=.false.` to retain its
   saved age. Do not use the existing 40-solar-mass checkpoints for a consistent
   25-solar-mass history.
4. From another terminal in that case directory, inspect progress:
   ```sh
   tail -f run.log
   ```
   Native restart snapshots and visualization files appear in `output_25Msun/`.
   Successful completion prints `Finished AMRVAC`; confirm the final age is
   7 Myr (code time approximately 715.4033). This minimal bundle has in-code
   safeguards but no Python watchdog. New output goes into `output_25Msun/`, preserving
   the input checkpoint. Native files are binary and copied without modification.

Build procedure: [official getting-started guide](https://amrvac.org/md_doc_2getting__started.html).
Generate a new 3.2 Makefile; do not reuse the original campaign's build files.

## Benchmarking and downloading results

See [BENCHMARK_AND_TRANSFER.md](BENCHMARK_AND_TRANSFER.md) for the exhaustive
8-16-rank test and the PowerShell script for copying an entire VM folder back
to Windows. The benchmark runs each rank count sequentially from a fixed
checkpoint and writes its own grouped results folder.

For radial plots of every snapshot in a folder, see [PLOTTING.md](PLOTTING.md).
The standalone command is `python3 plot_dat_folder.py /path/to/output`.

## Recover the existing 40-solar-mass production run

For the later geometry-guard abort and `recovery40/test0050.dat`, follow
[RECOVERY40_GEOMETRY.txt](RECOVERY40_GEOMETRY.txt). The recipe below records
the earlier recovery from the original production checkpoint.

Use [resume_40Msun.par](resume_40Msun.par) as an overlay on the original
production `run.par`, with the updated parent `mod_usr.t`. Keep the existing
three-phase `stellar_evolution.dat`; do not substitute the new 25-solar-mass
table or fresh-start parameter files. Copy the overlay into this parent folder.
AMRVAC 3.2 concatenates differing `base_filename` values across parameter
files. Set this value only in the primary recovery copy, not in the overlay.

From the crashed production case, validate the newest candidate first:

```tcsh
python3 ../phase2_diagnostics/inspect_restart.py output/test0043.dat
```

The standalone checker needs only Python's standard library. It rejects
truncated native data, nonfinite active-cell values, and nonpositive thermal
pressure. Its successful result does not guarantee future stability. If that
candidate fails, inspect an earlier checkpoint and change the overlay to match.

Rebuild the updated user module in the parent folder using the commands above.
Then, from the original production case, launch:

```tcsh
cp run.par run_recovery40.par
sed -i "s|^[[:space:]]*base_filename[[:space:]]*=.*| base_filename='recovery40/test'|" run_recovery40.par
sed -i '/^[[:space:]]*base_filename[[:space:]]*=/d' ../resume_40Msun.par
mkdir -p recovery40
setenv OMP_NUM_THREADS 1
nohup mpirun --bind-to none -np 8 ../amrvac -i run_recovery40.par ../resume_40Msun.par < /dev/null >& recovery40.log &
tail -f recovery40.log
```

The overlay preserves checkpoint age/iterations and the original grid. It
enables the user refinement handler and ghost copies, uses STS dtpar=0.1,
retains both conduction/cooling and Tfix, and writes new outputs separately
under `recovery40/` every 10000 years. Initial free-wind seeding is not applied
on this restart. Confirm that the log loads `output/test0043.dat`, prints
`User-module conservative refinement: T`, and uses the three-phase 40-solar-mass
wind history ending at 4.77 Myr. The actual production checkpoint has not been
tested locally; prior phase-switch validation used a different saved gas state.

## Simulation parameters

| Wind phase | Age interval (Myr) | Mass loss (solar masses/year) | Speed (km/s) | Temperature (K) |
|---|---|---|---|---|
| MS | 0-6.5 | 2e-7 | 1500 | 10000 |
| RSG | 6.5-7.0 | 1e-5 | 15 | 1000 |

- Starting stellar age: zero, fresh 25-solar-mass initial state;
  `restart_from_file='undefined'`.
  An empty string is not a valid fresh-start sentinel in AMRVAC 3.2.
- Final stellar age: 7 Myr; MS ends at 6.5 Myr (code time 664.3030754772012);
  abrupt, constant-within-phase wind parameters.
- Wind temperatures are assumptions absent from the user's screenshot.
- Ambient outside the initial free wind: total particle density 1e4 cm^-3,
  temperature 100 K, initially static.
- `wind_init_radius_pc=0.03`: analytic MS wind initially fills 0.01-0.03 pc.
  This is a small initial-condition change, not an evolved bubble restart.
  It represents about 13 years of free-wind travel and 2.6e-6 Msun of wind
  material. The old 40-solar-mass checkpoints are not used.
- Fixed ionized H/He EOS: mu approximately 0.609; ambient mass density
  approximately 1.018e-20 g/cm^3. This is an approximation for cold gas.
- Domain: 0.01-20 pc; spherical wind injection at the inner boundary and fixed
  ambient conditions at the outer boundary.
- Grid: 192 base cells, 8 cells/block, maximum AMR level 3, base width ratio 1.03.
- Method: TVDLF, minmod, SSPRK3, logarithmic density/pressure reconstruction,
  CFL 0.1, 50 startup slow steps; conduction `sts_dtpar=0.1`.
- AMR: `ghost_copy=.true.`, user-module `amr_pair_fallback=.true.`;
  `prolongprimitive=.false.`, `coarsenprimitive=.false.`.
- Refinement: density/pressure weights 0.7/0.3, threshold 0.05, derefine ratio 0.1.
- Numerical floors: density and pressure 1e-14 in code units; `dtmin=1e-14`.
- Energy safeguard: 32 representable spacings; cell/evaluation-budget limits 0.1%.
  Corrections are logged in `output_25Msun/test_guard.csv`; the evaluation sum is not
  a measurement of net conservation error. Counters restart at zero; all four
  original 40-solar-mass cases had zero corrections before their saved checkpoints.
- Guard CSV also records `amr_pair_fallbacks` and
  `amr_pair_max_relative_conservation_error` for conservative child-pair handling.
- Units: length 1 pc (3.0857e18 cm), density 1e-25 g/cm^3, velocity 100 km/s.
- Snapshot spacing: 10000 years, with initial/final output; temperature auxiliary
  output is in kelvin. Input `time_max=715.4033120523706` is in code units.
