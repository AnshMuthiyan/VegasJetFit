# Purpose: Describe the numerical repair, validation evidence, and production launch procedure.

This separate campaign retains the screenshot's three MS/RSG/WR wind phases,
the 4.77 Myr end age, n_total=1e4 cm^-3 ambient at 100 K, and all four on/off
combinations of thermal conduction and radiative cooling. Wind temperatures
remain the documented assumptions: MS/WR 1e4 K and RSG 1e3 K. Tfix is enabled
in the cooling cases; cooling OFF does not impose a physical 100 K gas floor.
The failed original campaign is preserved in ../evolving_wind_four_physics/.

SELECTED NUMERICS: TVDLF, minmod, SSPRK3, CFL=0.1, log reconstruction of rho/p,
192 base cells, AMR max level 3, geometric cell-width ratio q=1.03 at base level.
The physical domain remains 0.01--20 pc. Gentler stretching increases the
minimum cell width; this is a numerical grid change, not a change in the domain.
TVDLF is more diffusive than HLL. Shell thickness/peaks still need convergence
tests; the final configuration is supported by the specific short tests below.
The new rescue guard was NEVER activated in any of the 12 selected tests.

Repair implemented in mod_usr.t, without changing the installed AMRVAC library:
1. Enable compiler invalid/divide-by-zero/overflow traps and bounds checks.
2. Reject nonfinite states or density below its numerical floor explicitly.
3. Wrap pressure conversion and small-value handling. When a tiny/nonpositive
   internal energy needs rescue, set E=KE+max(small_e,32*spacing(max(|E|,|KE|))).
   The increment survives cancellation in E-KE; the earlier 1e-14 absolute
   pressure floor could disappear when added to a kinetic energy near 5e4.
4. Verify the returned primitive pressure is positive before log reconstruction.
5. Check native states after advancement, and abort if any individual energy
   correction exceeds 0.1% of the cell's energy scale. Numerical density rescue
   is disabled: invalid density stops the run rather than adding mass silently.
6. Record rescue counts, largest fractional correction, and the volume-weighted
   sum of corrections to evaluated native-cell states in output/test_guard.csv.
   The sum includes intermediate Runge-Kutta evaluations; it is a diagnostic
   budget, NOT a measurement of net physical energy error or a conservation proof.
   Abort if that evaluation budget exceeds 0.1% of analytic injected wind energy.

The repair does not claim to remove the upstream truncation error that first
loses thermal energy. It bounds and records small rescues, preserves a usable
positive pressure, and stops on large errors. Accuracy still requires resolution
and timestep comparisons. Failure-free execution alone is insufficient.

Validation commands (from this folder under Linux/WSL):
  python3 validation_tools/repair_tests.py compare --years 1000 --tag compare_1000yr
  python3 validation_tools/repair_tests.py physics --years 1000 --tag physics_1000yr
  python3 validation_tools/repair_tests.py transitions --years 300 --tag phase_300yr
Each validation folder contains its source, parameter file, phase table, logs,
snapshots, rescue audit, and result.txt. Tests refuse to overwrite existing folders.
Accelerated transition tests change phase end ages ONLY in their local test table.
They exercise the MS/RSG and RSG/WR source changes in young bubbles; they do not
replace tests of a physically mature 4.3/4.5 Myr bubble. Production ages stay exact.

validation_tools/audit_native.py reads actual conserved native v5 cells, not interpolated VTU
points. It checks finite values and strictly positive recovered pressure, reports
temperature ranges and integrated mass/energy, and measures shell/radius proxies.
For a completed validation folder:
  python3 validation_tools/audit_native.py validation/compare_1000yr_representable

Build from source with a compatible 1D AMRVAC installation:
  export AMRVAC_DIR=/home/anshm/amrvac
  python3 manage.py build
The optional --library PATH reuses a prebuilt 1D AMRVAC library read-only.

Production (after reviewing validation evidence):
  python3 launch_campaign.py start --parallel --ranks 1
  python3 launch_campaign.py status
  python3 launch_campaign.py stop
The recommended launch runs four cases concurrently, one MPI rank each, in a
persistent background session. MPI CPU binding is disabled so separate jobs use
available cores. A sequential launch remains available by omitting --parallel.
The external supervisor checks numeric logs and stops the campaign if a case
fails or logs NaN/Infinity. Compiler traps and in-code checks provide earlier
protection. Completion also requires an independent native-snapshot audit.
Production
inputs and outputs are protected against accidental overwrite. Keep the machine
awake and WSL running. Never reuse the failed original executable or checkpoints.

Evidence gate before any production launch:
  python3 validation_tools/summarize_validation.py --require-selected
This re-reads every selected native snapshot, checks temperatures and positivity,
checks the exact source and numerical parameters, verifies runtime activation of
conduction/cooling, and requires all 12 selected tests to have zero new-guard
activations. validation_summary.csv also retains rejected and interrupted trials.
See FINAL_REPORT.txt for the selected evidence and limitations.

Validation and checking scripts live in validation_tools/. The root-level
audit_native.py is a compatibility bridge for the deferred import in production
jobs started before this move. Keep that bridge until those jobs finish.
manage.py, launch_campaign.py, and supervise.py remain at the campaign root.
