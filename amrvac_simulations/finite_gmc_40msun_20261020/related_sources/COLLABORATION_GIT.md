# AMRVAC simulation Git handoff

The canonical run trees and raw outputs remain in this Lyra directory. This
directory is not itself a Git repository. Do not initialize Git across the
whole run tree or commit logs, executables, checkpoints, and bulk outputs.

Ansh's separate, simulation-facing branch is
`feature/amrvac-wind-bubble-models` in
`git@github.com:AnshMuthiyan/VegasJetFit.git`. On Lyra its clean checkout is
`/Users/jkeohane/GRBs/VegasJetFit_wind_bubble_handoff`. Start with
`AMRVAC_WIND_BUBBLE_HANDOFF.md` and `amrvac_simulations/README.md` there.

That branch includes a curated May 1 pressure-grid source bundle, the 12
selected valid VTUs, analysis tables, copied method notes, and a SHA-256
manifest. The p5/p6 snapshots in the bundle came from the pre-inner-fix
archive so they match the May 1 quality table. Later reruns in this workspace
must be audited as a new dataset before replacing the bundle.

The `jonathan-mac-version` branch is for VegasAfterglow fitting. Only after a
validated, fast simulation-derived density surrogate is ready should the fit
branch consume it. AMRVAC is run offline, not during an MCMC fit.
