# Full-track within-range validation holdouts

Twelve distinct full-lifetime cases sample the interior of the 25/40-Msun
density-pressure domain with a deterministic six-bin log-space Latin-hypercube
design for each mass. They are reserved as withheld validation points for an
eventual registered-profile surrogate, not training points. No original or
midpoint-refinement grid case is duplicated. `manifest.csv` and `design.json`
record exact values and host assignments.

The six densities at 1 pc are 3635, 5335, 7830, 11494, 16870 and 24762
hydrogen nuclei cm^-3. Boundary P/k_B values are permuted by stellar mass
from 1778279, 5623413, 17782794, 56234133, 177827941 and 562341325
K cm^-3. All lie strictly within the original approved density and pressure
bounds. The pinned AMRVAC source and Linux binary, 1024-cell 0.001--160-pc
stretched mesh, finite GMC, fixed initial gravity, neutral support, no
photoionization/cooling/conduction, complete 25/40-Msun tracks and output
cadence are exactly inherited from `van_marle_full_track_grid_20261023`.

`generate_holdouts.py` writes 12 cases and 48 namelists once. The independent
`verify_holdouts.py` checks uniqueness against both existing campaigns,
within-range coverage, every input SHA and all unchanged numerical settings.
`grid_runtime.py` requires an individual 0.01-Myr static and 0.0001-Myr smoke
gate before each full run. `dispatch_grid.py` requires the original and
midpoint AMRVAC processes still healthy in their own farms, available CPU and
disk, exact transferred SHA and a NEW non-overwriting holdout farm. Each full
run has a finite 30-day safety timeout. No failed AMRVAC input is retried
automatically.

Full 25-Msun completion requires exact 7.0 Myr, 71 saves and MS/RSG phase
coverage; 40-Msun requires exact 4.77 Myr, 49 saves and MS/RSG/WR coverage.
Both require exit 0, one finish marker, empty stderr, exact source/input pins,
finite-positive fields, correct initial density and boundary pressure, and
stable outer profile. All complete products require an independent NEW pull,
checksum and visual/native-resolution validation before publication. Running
cases do not establish convergence, physical shock width or a GRB wall.
