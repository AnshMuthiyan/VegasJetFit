# Purpose: Run the four conservative-AMR phase-2 restart experiments on an AMRVAC 3.2 VM.

HISTORICAL EXPERIMENT: This source-patch package is superseded by the current
../mod_usr.t and the four ../tc_*/run.par inputs, which use unmodified AMRVAC 3.2.
See ../README.md. Do not install this patch for the current 25 Msun runs.

Each case uses spherical ideal-gas hydrodynamics. The folder names select
thermal conduction (tc) and radiative cooling (rc):
  tc_on_rc_on:   saturated Spitzer conduction + SPEX_DM exact cooling.
  tc_on_rc_off:  conduction only.
  tc_off_rc_on:  cooling only.
  tc_off_rc_off: neither source term.
Tfix is enabled at 100 K when cooling is active.

The fix retains second-order AMR refinement when its child states are valid.
If refinement creates invalid children, both receive the valid conservative
parent state. Volume-integrated mass, momentum and energy are preserved,
with a checked relative tolerance of 1e-12. Coarse/fine ghost copies use
first-order interpolation. This trades local interpolation order for valid
thermal states. Existing small-energy repair guards still abort on large
deficits. Conduction/cooling coefficients and physical floors are unchanged.
The inner face uses the prescribed wind state so its numerical flux matches
the specified mass loss. A phase-aware boundary CFL bounds the fast WR wind.
The TC floor observer logs existing floor operations without changing them.

Validation: the final source completed stellar ages 4.3-4.501 Myr with both
modules on. An extended WR continuation reached 4.610042 Myr before being
checkpointed and stopped at wrap-up. All 45 saved states in those two tests
were valid; TC floor counters remained zero through their last audit rows.
The long WR segment used CFL=0.4; these packaged inputs use CFL=0.1.
Earlier tests passed the other three module combinations through 201,000 yr
with the AMR fix, before the wind-flux correction and TC observer were added.
The full 4.77-Myr endpoint and full final-source matrix remain untested.
See validation_status.json for exact coverage and checkpoint ages.
A clean official-v3.2 build passed, followed by a 1,000-step WR restart
whose decoded physical states exactly matched the previously tested build.

Steps on the VM (tcsh; working mpifort and mpirun required):

1. Copy this entire folder to the VM. Use a dedicated official v3.2 tree:
   git clone --branch v3.2 --depth 1 --recurse-submodules https://github.com/amrvac/amrvac.git "$HOME/amrvac32-positive"
   setenv AMRVAC_DIR "$HOME/amrvac32-positive"

2. In this ConservativeAMRRestart folder, install the supplied source patch:
   python3 install_positive_amr.py --amrvac-dir "$AMRVAC_DIR" --patch-dir .
   It checks source hashes and saves exact originals. The patch supports only
   this 1D HD rho/m1/e layout. Both this patch and mod_usr.t are required.

3. Build in this folder (no spaces in its Linux path):
   perl "$AMRVAC_DIR/setup.pl" -d=1
   make hdr F90=mpifort
   make -j4 F90=mpifort F90FLAGS='-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'

4. Launch a case from INSIDE its folder:
   cd tc_on_rc_on
   mkdir -p output
   setenv OMP_NUM_THREADS 1
   nohup mpirun --bind-to none -np 8 ../amrvac -i run.par < /dev/null >& run.log &
   tail -f run.log
   Ctrl+C exits tail; the background run continues. Repeat from each other
   case folder to run all four concurrently with 8 ranks each on 32 cores.

5. Status prints every 30 seconds. Check run.log, output/test_guard.csv and
   output/test_tc_floor.csv. Parent-copy messages describe conservative
   interpolation fallbacks. Native output/testNNNN.dat files are restartable.

6. To save before stopping, create savenow in the running case directory:
   touch savenow
   Wait for savenow to disappear and the new checkpoint to finish writing,
   then send kill -TERM to that case's recorded mpirun PID. To resume, set
   restart_from_file='output/testNNNN.dat' to that completed checkpoint and
   set reset_time=.false. and reset_it=.false. in run.par before relaunching.

Simulation parameters:
  Initial gas: original per-case checkpoints, approximately 1 Myr old.
  Stellar age is deliberately RESET to 4.3 Myr to start phase 2; this does
  not reconstruct the omitted MS evolution or a fully aged 4.3-Myr bubble.
  To continue the original MS history instead, set reset_time and reset_it
  false before the FIRST launch. Later resumes must also disable both resets.
  Stop age: 4.77 Myr. Native output interval: 10,000 yr; prefix output/test.
  MS: 0-4.3 Myr; 1e-6 Msun/yr; 2000 km/s; assumed wind T=10000 K.
  RSG: 4.3-4.5 Myr; 5e-5 Msun/yr; 15 km/s; assumed wind T=1000 K.
  WR: 4.5-4.77 Myr; 1e-5 Msun/yr; 2000 km/s; assumed wind T=10000 K.
  Ambient total gas particles: 1e4 cm^-3; T=100 K; rho=1.0181176e-20 g/cm^3.
  Fixed inherited H/He EOS; gamma=5/3. Domain 0.01-20 pc.
  Grid: 192 base cells; 8 cells/block; max AMR level 3; stretching q=1.03.
  TVDLF/minmod/SSPRK3; CFL=0.1; STS dtpar=0.1; slowsteps=50.
  ghost_copy=true; prolongprimitive=false; coarsenprimitive=false.
  Code density/pressure floors=1e-14; energy guards=32 ULP and 0.001 fractions.
