# Full-track density-pressure midpoint refinement

This is a separate, additive 46-case refinement of the frozen 24-case
`van_marle_full_track_grid_20261023` campaign. It contains exactly the
previously missing points in a 2 stellar-mass x 5 density x 7 boundary-pressure
tensor grid. Original cases, inputs, farms, guards and evidence are untouched.

The two inserted density normalizations, 5477 and 17321 hydrogen nuclei cm^-3
at 1 pc, and three inserted boundary pressures, P/k_B = 3162278, 31622777 and
316227766 K cm^-3, are rounded geometric midpoints of adjacent parent values.
They are interpolation and eventual withheld-profile validation points, not a
new wind or cloud prescription. The stars, source, binary, 1024-cell stretched
0.001--160-pc mesh, finite GMC, fixed initial-mass gravity, neutral support,
no photoionization, no tabulated cooling, no conduction, output cadence and
exact 25/40-Msun phase ages match the parent. No supernova is modeled.

`generate_refinement.py` creates `manifest.csv`, `design.json` and 184 namelists
in `inputs/` once, refusing overwrite. `mod_usr.t` and the arm64/Linux binaries
are exact copies of the parent pinned build; build preflight evidence is copied
with them. `grid_runtime.py` enforces an independent 0.01-Myr static and
0.0001-Myr smoke gate for every case before its full guarded evolution. Each
new host farm is separate and non-overwriting. `dispatch_grid.py` refuses a
second dispatch, checks the expected original-grid workers, core headroom,
disk and every transferred SHA before launching. A failed case is recorded and
is never automatically retried.

Only an exact 7.0-Myr 25-Msun MS/RSG endpoint or 4.77-Myr 40-Msun MS/RSG/WR
endpoint with the required 71/49 saves, phase diagnostics, finite-positive
fields, initial density and pressure, stable outer profile, exit 0, one finish
marker, empty stderr and original source/input pins can be labeled complete.
The midpoint grid does not itself establish spatial convergence, a physical
shock width or a GRB wall. Outputs must be pulled to NEW non-overwriting trees
and independently reconciled before scientific publication.
