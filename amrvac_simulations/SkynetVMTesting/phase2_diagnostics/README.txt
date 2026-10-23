# Purpose: Document local AMRVAC 3.2 tests of the deliberately advanced MS-to-RSG restart.

These are isolated diagnostic experiments, not production restarts.
All tests load the SAME tc_on_rc_on/test0011.dat gas state (age
1,022,650.888508874 yr), then reset the stellar clock to 4,300,000 yr.
This changes the injected wind immediately to the RSG phase without
evolving the bubble through the intervening main-sequence years.

Original checkpoint SHA256:
64043eecd126873a4fa1bdc08bdd53b8e73e7ddab1a8bd8c1ecfc2e24cb4157b

Build: official AMRVAC 3.2, commit
c45d84650ed3379eb22dcfa6fb927a45734e5d8c.
Existing local debug executable:
/tmp/skynet-v32-qdvc32bu/problem/amrvac
Flags: -cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds
       -fbacktrace -ffpe-trap=invalid,zero,overflow

Numerics: original TVDLF/minmod/SSPRK3, stretched spherical AMR mesh,
courantpar=0.02, sts_dtpar=0.1; original energy-deficit safety guards.
Tfix stays enabled in input and is active when cooling is enabled.
Snapshots are saved every 50 simulated years to inspect valid states
before a failure. A 500-yr target is used for the initial isolation tests;
the subsequent controls target 250 yr, beyond the earlier failure interval.
An external timeout stops an individual test if it exceeds its allowance.

20261019_235603_baseline (8 MPI ranks, sequential):
  both: floating-point trap in thermal conductivity calculation.
  cooling_only: excessive thermal-energy deficit at iteration 38399,
                radius 0.299995 pc; guard rejects repair >0.1% energy scale.
  conduction_only: floating-point trap in thermal conductivity calculation.
All three have valid saved snapshots through 150 yr after the reset.

20261020_000334_controls (2 MPI ranks, sequential):
  neither: excessive thermal-energy deficit at iteration 36294,
           radius 0.297354 pc; guard rejects repair >0.1% energy scale.
  both_ghost_copy: PASSED to 4,300,250 yr; all saved cells have finite
                  conserved variables and positive thermal pressure.
                  Only additional change: ghost_copy=.true. in boundlist.

20261020_000703_ghost_copy (8 MPI ranks):
  FAILED during the longer 500-yr target, iteration 90668, in prolong_2nd,
  radius 0.594026 pc. The required energy rescue would be 0.2866% of the
  local energy scale, above the unchanged 0.1% safety limit.
  Valid saved checkpoints extend through 400 yr, not 500 yr.
  Comparison with the failed baseline both/run.par confirms that
  ghost_copy=.true. is the ONLY input difference.
  The short 250-yr pass is therefore NOT a complete fix.

20261020_001244_primitive_prolong (8 MPI ranks):
  Tried ghost_copy plus prolongprimitive=.true., retaining conservative
  coarsening (coarsenprimitive=.false.). FAILED at startup: the primitive
  conversion guard encounters a zero-filled buffer at radius 3.422262 pc.
  This combination cannot be recommended as a parameter-only solution.
  No physical evolution occurred in this test.

The conduction backtrace identifies generated mod_thermal_conduction.f,
line 825, inside set_source_tc_hd:
  qd(ixmin1:ixmax1)=fl%tc_k_para*sqrt(Te(ixmin1:ixmax1)**5)
This is the operation where an exception occurs, not proof of where the
underlying invalid thermal state first originates. The hydro-only failure
demonstrates a stability problem independent of cooling or conduction.
Do not infer that disabling a source term is an adequate physical fix.
Do not infer that an uninterrupted 4.3-Myr main-sequence run will fail:
these tests use a much younger bubble with its stellar clock advanced.

Why test ghost_copy: the default fine-grid ghost interpolation applies
limited linear slopes to conserved variables independently. It need not
preserve E - momentum^2/(2*rho) > 0 in a cold, fast rarefaction. Copying
the parent state removes those interpolation slopes at coarse/fine ghost
interfaces. This changes the numerical boundary interpolation and can
increase diffusion there; it does not prescribe a new physical heating
term, turn off either source term, or change stellar wind parameters.
The passing short test supports this hypothesis, not full-run stability.
The longer test directly identifies second-order mesh refinement as
another source of negative thermal energy. A robust solution must address
both ghost filling and creation of refined cells, and should preserve
mass, momentum, and energy while keeping thermal pressure positive.
Do not disable the guards or enlarge their thresholds to call a test a pass.

Two earlier added controls, 20261020_000050_hydro_control and
20261020_000134_ghost_copy, were deliberately stopped to remove CPU
contention and replaced by the sequential controls. Their nonzero exit
codes are not numerical failure evidence; their reports are annotated.

Each batch includes mod_usr.t, amrvac.h, stellar_evolution.dat,
per-case run.par and checkpoint copies, run.log, native outputs, and
results.json with checkpoint/binary hashes and checkpoint validation.
The original production and transfer inputs are not edited by this runner.
summary.json independently audits every saved snapshot in all completed
diagnostic batches; regenerate it with python3 summarize.py.

To repeat from WSL (replace the executable if rebuilding it):
  python3 run_tests.py --executable /path/to/amrvac --ranks 2 --timeout 600
To repeat the controls:
  python3 run_tests.py --executable /path/to/amrvac --ranks 2 --timeout 600 \
      --cases neither both_ghost_copy --years 250 --label controls
The executable must be a compatible 1D HD build. Read results.json and
run.log: the runner itself exits normally even when a simulation fails.

Wrap-up, 2026-10-20:
The final portable inputs are ../ConservativeAMRRestart/README.txt.
Use that package, rather than the older solution_candidate folder.
The audited final build completed 4.3-4.501 Myr with conduction and cooling
on. Extended WR evolution reached 4.610042 Myr with no invalid saved cells;
diagnostics were checkpointed and stopped at the user's wrap-up request.
The full 4.77-Myr endpoint remains untested. wrapup_validation.json checks
all saved final-source states and records exact validation limits.
The source fix is conservative parent-copy fallback for invalid refined
children, with ghost_copy enabled. Phase-aware boundary CFL and prescribed
inner-face wind states complete the supplied mod_usr.t changes. TC floor
observations preserve the original floor behavior and recorded zero events.
Original production inputs and their paused processes were not changed.
