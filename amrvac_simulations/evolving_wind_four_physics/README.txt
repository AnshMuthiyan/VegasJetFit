# Purpose: Screenshot-derived wind phases, four physics combinations, and launch instructions.

Four matched simulations of the screenshot's 40 Msun star

Case              Thermal conduction  Radiative cooling
tc_off_rc_off      OFF                 OFF
tc_on_rc_off       ON                  OFF
tc_off_rc_on       OFF                 ON
tc_on_rc_on        ON                  ON

SOURCE: User attachment Screenshot 2026-10-13 163843.png.
Phase    Simulation ages [Myr]    Mdot [Msun/yr]    speed [km/s]
MS       0 <= t < 4.3             1e-6              2000
RSG      4.3 <= t < 4.5           5e-5                15
WR       4.5 <= t <= 4.77         1e-5              2000

The screenshot's t_end values are cumulative END ages. Durations are 4.3,
0.2, and 0.27 Myr, respectively. Total duration is 4.77 Myr, not 5.24 Myr.
stellar_evolution.dat contains these three phases, with end age, log10(Mdot),
speed, and wind temperature. This replaces the earlier 299-age project table.
There is no interpolation between phases and no artificial transition ramp.
Phases switch at the inner boundary using simulation age, with no travel delay.
The timestep is capped at phase boundaries so the integrator lands on them.

Wind temperatures are NOT specified in the screenshot. Assumptions:
MS/WR=10,000 K; RSG=1,000 K, following the existing constant-phase case values.
Only these temperatures are assumptions; ages, Mdot, and speeds match the image.
The 40 Msun label selects the history; gravity/stellar mass evolution is not solved.

Ambient: n_total=1e4 particles/cm^3, initially stationary at 100 K everywhere.
The inherited fixed fully ionized H/He EOS gives rho about 1.018e-20 g/cm^3.
This is the existing ideal-gas approximation, not neutral/molecular chemistry
at 100 K or a detailed WR abundance model. Ambient outer conditions are fixed.

Cooling ON: SPEX_DM, exact integration, Tfix=true, cutoff 100 K.
Cooling OFF: cooling and its Tfix heating are inactive. Adiabatically expanding
gas may fall below 100 K. The small_pressure fallback is identical across all
cases and is not a density-dependent 100 K floor.
Conduction ON: saturated Spitzer conduction, STS method 1, sts_dtpar=0.4.
Conduction OFF: conduction source and its STS timestep restriction are inactive.

Matched logarithmic mesh: 0.01 to 20 pc, 192 base cells, AMR max level 3.
HLL flux, minmod/log reconstruction, SSPRK3, CFL=0.2; injection CFL uses actual
local widths and the maximum signal speed over all phases, including transitions.
Identical AMR criteria can produce different adapted grids in the four cases.
Snapshots every 100,000 yr plus initial and final states. Phase changes at 4.3
and 4.5 Myr coincide with snapshot ages. Small inner cells make full runs costly.

From this directory in Linux/WSL, with mpif90, mpirun, make, and python3:
  export AMRVAC_DIR=/home/anshm/amrvac
  python3 manage.py validate
  python3 manage.py build
  python3 manage.py smoke --smoke-years 100 --ranks 4
  python3 manage.py run --ranks 4

The last command runs all four cases sequentially. To run just one:
  python3 manage.py run --case tc_on_rc_on --ranks 4
Each case contains mod_usr.t, run.par, stellar_evolution.dat, and output/.
Never use the old constant-wind executable; build/amrvac uses this module.
The builder makes a private library by default; --library PATH reuses a
compatible prebuilt 1D library read-only. Existing production outputs are protected.
To regenerate all inputs before starting production: python3 manage.py prepare

All hand-written files begin with purpose comments. AMRVAC controls formats of
its generated binary objects, snapshots, module files, and simulation outputs.
Smoke tests establish startup and physics activation, not full-lifetime stability
or convergence. Numerical pressure replacement may add thermal energy. Check
native cell positivity, correction energy, shell mass/radius, boundary headroom,
and spatial/timestep convergence before scientific use.

Persistent background launch (used for the user's production campaign):
  python3 launch_campaign.py start --ranks 4
  python3 launch_campaign.py status
campaign.log records the sequential supervisor; campaign_pid.txt records its
WSL PID. Each active run writes CASE/run.log and CASE/output/test.log.
The background process continues after the launching shell exits. Keep this
computer awake and WSL running for the campaign to continue. Do not start a
second copy; the launcher refuses existing campaign logs or production outputs.
