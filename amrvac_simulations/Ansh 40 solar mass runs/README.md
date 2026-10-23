<!-- Purpose: Describe the active physics, VM build/run steps, and parameters for the four evolving-wind simulations. -->

# Ansh 40 solar mass runs

Minimal inputs and native checkpoints for the current 1D spherical stellar-wind
model. Each `run.par` automatically loads its copied checkpoint and retains the
saved stellar age and gas state. The original target remains 4.77 Myr.
Build a new executable with the VM's MPI-AMRVAC 3.2 installation.

Verified against official v3.2 (`c45d84650ed3379eb22dcfa6fb927a45734e5d8c`):
the source compiled and all four checkpoints advanced ten years in isolated
tests with the correct physics switches, finite states, and positive pressure.
No changes to the source interfaces were required. Full-lifetime stability and
performance on the VM remain to be checked.

## Physics modules

All cases use ideal-gas hydrodynamics with total energy and gamma = 5/3.

| Case folder | Conduction | Cooling | Restart age (years) | Included checkpoint |
|---|---|---|---:|---|
| `tc_off_rc_off` | Off | Off | 1214065.410945 | `test0013.dat` |
| `tc_on_rc_off` | On | Off | 1073816.474477 | `test0011.dat` |
| `tc_off_rc_on` | Off | On | 1067801.003334 | `test0011.dat` |
| `tc_on_rc_on` | On | On | 1022650.888509 | `test0011.dat` |

Conduction: saturated Spitzer transport with super-time-stepping.
Cooling: `SPEX_DM`, exact integration, and `Tfix` at 100 K. `Tfix` acts only in
cooling-enabled cases; cooling-disabled gas may expand below 100 K.

## Run on the Linux VM

1. Copy this entire folder to the VM. Open a terminal in `SkynetVMTesting`.
2. Set the path to the installed **3.2 source tree**, generate its Makefile,
   and build once. Use a Linux path without spaces. MPI, gfortran, Perl, make,
   and rsync must be available. These flags retain floating-point traps.
   ```sh
   export AMRVAC_DIR=/absolute/path/to/amrvac
   export PATH="$AMRVAC_DIR:$PATH"
   perl "$AMRVAC_DIR/setup.pl" -d=1
   make hdr
   make -j4 F90FLAGS='-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'
   ```
3. Choose a case and run from its directory. This example activates both
   conduction and cooling. `run.par` selects the checkpoint automatically.
   ```sh
   cd tc_on_rc_on
   mkdir -p output
   export OMP_NUM_THREADS=1
   mpirun --bind-to none -np 1 ../amrvac -i run.par > run.log 2>&1
   ```
   Replace the case name to run another combination. Change `-np 1` if testing
   more MPI ranks. Use a fresh copy of the case folder for repeated runs.
   Keep the numbered checkpoint file in `output/`; do not reset time or
   replace the checkpoint with a visualization file.
4. From another terminal in that case directory, inspect progress:
   ```sh
   tail -f run.log
   ```
   Native restart snapshots and visualization files appear in `output/`.
   Successful completion prints `Finished AMRVAC`; confirm the final age is
   4.77 Myr (code time approximately 487.4963). This minimal bundle has in-code
   safeguards but no Python watchdog. New output goes into `output/`, preserving
   the input checkpoint. Native files are binary and copied without modification.

Build procedure: [official getting-started guide](https://amrvac.org/md_doc_2getting__started.html).
Generate a new 3.2 Makefile; do not reuse the original campaign's build files.

## Simulation parameters

| Wind phase | Age interval (Myr) | Mass loss (solar masses/year) | Speed (km/s) | Temperature (K) |
|---|---|---|---|---|
| MS | 0-4.3 | 1e-6 | 2000 | 10000 |
| RSG | 4.3-4.5 | 5e-5 | 15 | 1000 |
| WR | 4.5-4.77 | 1e-5 | 2000 | 10000 |

- Final stellar age: 4.77 Myr, rather than another 4.77 Myr after restart;
  abrupt, constant-within-phase wind parameters.
- Wind temperatures are assumptions absent from the user's screenshot.
- Original ambient: total particle density 1e4 cm^-3, temperature 100 K, static.
  Restarts retain the evolved bubble, rather than reinitializing the ambient gas.
- Fixed ionized H/He EOS: mu approximately 0.609; ambient mass density
  approximately 1.018e-20 g/cm^3. This is an approximation for cold gas.
- Domain: 0.01-20 pc; spherical wind injection at the inner boundary and fixed
  ambient conditions at the outer boundary.
- Grid: 192 base cells, 8 cells/block, maximum AMR level 3, base width ratio 1.03.
- Method: TVDLF, minmod, SSPRK3, logarithmic density/pressure reconstruction,
  CFL 0.1, 50 startup slow steps; conduction `sts_dtpar=0.4`.
- Refinement: density/pressure weights 0.7/0.3, threshold 0.05, derefine ratio 0.1.
- Numerical floors: density and pressure 1e-14 in code units; `dtmin=1e-14`.
- Energy safeguard: 32 representable spacings; cell/evaluation-budget limits 0.1%.
  Corrections are logged in `output/test_guard.csv`; the evaluation sum is not
  a measurement of net conservation error. Counters restart at zero; all four
  original cases had zero corrections before their saved checkpoints.
- Units: length 1 pc (3.0857e18 cm), density 1e-25 g/cm^3, velocity 100 km/s.
- Snapshot spacing: 100000 years, with initial/final output; temperature auxiliary
  output is in kelvin. Input `time_max=487.4962569271154` is in code units.
