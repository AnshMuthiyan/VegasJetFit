<!-- Purpose: Explain the Van Marle screenshot-based stellar-wind campaign, its inputs, outputs, and live-folder access. -->

# VanMarleStellarParameterRuns

This folder contains four matched, one-dimensional spherical MPI-AMRVAC simulations
of an evolving stellar wind expanding into a dense ambient medium. The mass-loss
rates, wind speeds, and phase endpoints follow the user's 40-solar-mass-star
screenshot. This is a controlled setup using those parameters, rather than a
reproduction of every physical assumption in a published model.

## Stellar wind and ambient medium

| Phase | Age interval (Myr) | Mass-loss rate (solar masses/year) | Speed (km/s) | Assumed wind temperature (K) |
|---|---|---|---|---|
| Main sequence | 0 to 4.3 | 1e-6 | 2000 | 10000 |
| Red supergiant | 4.3 to 4.5 | 5e-5 | 15 | 1000 |
| Wolf-Rayet | 4.5 to 4.77 | 1e-5 | 2000 | 10000 |

The target duration is **4.77 million years**. Parameters are constant within
each phase and change abruptly at the listed boundaries. Wind temperatures are
assumptions absent from the screenshot. The inner boundary supplies density
`rho = Mdot / (4*pi*r*r*v)`; phase age is evaluated at that injection boundary.
The ambient medium initially fills the domain, with total particle density
**1e4 cm^-3**, temperature **100 K**, and zero velocity. The outer boundary retains
those ambient values.

The inherited ideal-gas equation of state has gamma=5/3 and fixed ionized H/He
composition (mu approximately 0.609). Its ambient mass density is approximately
1.018e-20 g/cm^3. This composition is an approximation for cold gas; neutral or
molecular chemistry and evolving WR abundances are not modeled.

## Four runs

| Case directory | Thermal conduction | Radiative cooling |
|---|---|---|
| `tc_off_rc_off` | Off | Off |
| `tc_on_rc_off` | On | Off |
| `tc_off_rc_on` | Off | On |
| `tc_on_rc_on` | On | On |

Conduction uses saturated Spitzer transport and super-time-stepping. Cooling
uses the SPEX_DM table with the exact integration method. `Tfix` is enabled
with a 100 K cooling floor in cooling-enabled runs. Cooling-disabled controls
have no physical 100 K floor and can cool adiabatically below that temperature.

## Numerical setup and validation limits

The domain is 0.01 to 20 pc, with 192 base cells, 8 cells per block, maximum
AMR level 3, and geometric base-cell width ratio 1.03. The scheme uses TVDLF,
minmod limiting, SSPRK3, logarithmic density/pressure reconstruction, and CFL 0.1.
Conduction's `sts_dtpar` is 0.4. Boundary-aware timesteps account for the fast
injected wind and the phase changes.

Finite-state checks and floating-point traps stop invalid calculations. A
representable internal-energy safeguard logs small energy corrections and
rejects excessive corrections; its evaluation sum is not a net conservation
error measurement. See `FINAL_REPORT.txt` and `README.txt` for implementation
details and rejected alternatives.

Before production, all four 1000-year tests and eight accelerated transition
tests passed with positive finite states and zero new energy-safeguard events.
Those tests do not establish full-lifetime stability or spatial convergence.
TVDLF diffusion, cold-gas thermodynamics, cooling-layer resolution, conservation,
and eventual boundary influence remain scientific limitations to evaluate.

## Files and outputs

- Each case contains `mod_usr.t`, `run.par`, `stellar_evolution.dat`, `run.log`,
  and its `output/` directory.
- `output/test*.dat` are native snapshots; converted VTU files provide visualization.
  Production snapshot spacing is 100000 simulated years, with initial/final output.
- `output/test.log` records numerical progress. `output/test_guard.csv` records
  energy-safeguard events and correction diagnostics.
- `campaign.log` and `campaign_pid.txt` identify the persistent supervisor.
  A `campaign_failed.txt` records an automatic campaign failure if one occurs.
  Successful campaign completion is recorded in `run_results.txt`.
- `validation_tools/` contains the checking and test scripts. `validation/`
  retains experiments and evidence. `validation_summary.csv` summarizes them.
- `build/` contains the executable. `manage.py`, `launch_campaign.py`, and
  `supervise.py` manage the campaign. The root `audit_native.py` is an import
  compatibility bridge for already-running jobs.

## Checking the running campaign

From this directory in WSL/Ubuntu:

```sh
python3 launch_campaign.py status
python3 manage.py validate
python3 validation_tools/summarize_validation.py --require-selected
```

The current campaign runs four cases concurrently with one MPI rank per case.
Do not launch duplicate runs or overwrite existing outputs. Keep WSL running
and the computer awake. A successful process exit alone is insufficient:
completion checks also audit native cells, final age, and physics activation.

## Folder access while running

`VanMarleStellarParameterRuns` is a Windows directory junction pointing to
`evolving_wind_repaired`. Both names access the same live files, with no duplicate
data. Windows blocked a physical directory move because the running jobs hold
the campaign open. The junction provides the requested folder name without
interrupting those jobs. A physical rename can be performed after all jobs exit.
**Retain the original directory and the import compatibility bridge while the
current jobs are running.** Earlier failed campaign data remain separately in
`../evolving_wind_four_physics/`.

Git tracks the campaign files once, under `VanMarleStellarParameterRuns/`, and
ignores the duplicate local name. On a fresh clone this is an ordinary directory;
the local junction is only needed to preserve the original paths of these jobs.
