# Purpose: Explain the portable candidate for stable phase-2 restarts with conduction, cooling, and Tfix retained.

STATUS: Extended testing is ongoing. See validation_status.json; this is
not yet a claim that the entire remaining stellar evolution is validated.

Active physics: 1D spherical ideal-gas hydrodynamics, saturated Spitzer
thermal conduction, SPEX_DM radiative cooling, and cooling Tfix at 100 K.
Stellar mass-loss rate and velocity follow the original MS/RSG/WR table.

Numerical fix: copy parent states into coarse/fine ghost cells. During
refinement, keep the original second-order result unless a child has
nonfinite values, invalid density, or insufficient internal energy.
For an invalid pair, copy the valid parent state into both children.
This preserves volume-integrated mass, momentum, and total energy;
the code checks that conservation to 1e-12 relative tolerance.
The fallback lowers local interpolation order; it does not add heat.
Existing energy-deficit abort checks remain enabled.
The boundary CFL bound uses the current wind phase and accounts for
roundoff near a switch; the ordinary CFL still limits interior fast gas.

Run on the VM using tcsh, with a separate clean AMRVAC source tree:

1. Create the dedicated source tree (requires git/network; no sudo):
   git clone --branch v3.2 --depth 1 --recurse-submodules https://github.com/amrvac/amrvac.git "$HOME/amrvac32-positive"
   setenv AMRVAC_DIR "$HOME/amrvac32-positive"

2. In THIS solution_candidate folder, install the source patch:
   python3 install_positive_amr.py --amrvac-dir "$AMRVAC_DIR" --patch-dir .
   The installer verifies source hashes and records exact originals.
   This patch is restricted to the supplied 1D HD rho/m1/e problem.

3. Build the supplied mod_usr.t using your working MPI installation:
   perl "$AMRVAC_DIR/setup.pl" -d=1
   make hdr F90=mpifort
   make -j4 F90=mpifort F90FLAGS='-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'

4. Start the packaged case:
   cd tc_on_rc_on
   mkdir -p output
   setenv OMP_NUM_THREADS 1
   nohup mpirun --bind-to none -np 8 ../amrvac -i run.par < /dev/null >& run.log &
   tail -f run.log

5. Verify iteration zero starts near code time 439.462 (4.3 Myr).
   Check output/test_guard.csv as well as run.log. AMR parent-copy
   messages describe conservative fallback events, not added energy.
   Ctrl+C exits tail; it does not stop the background simulation.

Simulation parameters:
  Starting gas: supplied test0011.dat, originally 1,022,650.8885 yr old.
  Stellar clock reset: 4.3 Myr; this deliberately skips the remaining MS
  evolution and does not make the saved bubble a fully evolved 4.3-Myr bubble.
  RSG: 4.3-4.5 Myr, 5e-5 Msun/yr, 15 km/s, assumed wind T=1000 K.
  WR: 4.5-4.77 Myr, 1e-5 Msun/yr, 2000 km/s, assumed wind T=10000 K.
  Ambient: total gas particles n=1e4 cm^-3, T=100 K; original fixed H/He EOS.
  Domain: 0.01-20 pc; 192 base cells; maximum AMR level 3; 8 cells/block.
  Original stretched grid q=1.03; gamma=5/3; TVDLF/minmod/SSPRK3.
  Packaged CFL=0.1; STS dtpar=0.1; saturated conduction; exact cooling.
  ghost_copy=true; prolongprimitive=false; coarsenprimitive=false.
  Native output interval: 10,000 yr; output prefix: output/test.
