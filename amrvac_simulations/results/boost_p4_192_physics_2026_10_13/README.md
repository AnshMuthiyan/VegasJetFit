# BoOST p4 192-cell physics controls

This is the completed original-domain (0.19677-32.36185 pc), 192-base-cell
AMRVAC v3.1 physics matrix for the BoOST p4 evolving wind. It is separate
from the fixed-4x-domain 12288/24576-cell **cooling-only** results in
[`boost_p4_2026_10_13`](../boost_p4_2026_10_13/README.md). These are
simulations, not GRB fits or approved fitting templates.

| Case | Cooling only | Conduction only | Cooling + conduction |
| --- | --- | --- | --- |
| n22 (1e-22 g/cm3) | Complete | Complete | Complete |
| n23 (1e-23 g/cm3) | Complete | Complete | Failed at 4.78 Myr |
| n24 (1e-24 g/cm3) | Complete | Complete | Complete |

Hydro-only controls also completed for all three densities. Each completed
case has guarded exit 0, the normal AMRVAC completion marker, 54 finite,
positive VTUs, and a 5.24-Myr endpoint in the canonical Lyra run tree.
`data/full_validation.csv` records all 12 outcomes. The n23 combined run
has guarded exit 139 after 48 VTUs; its last saved age is about 4.70 Myr,
so it is **not** a completed endpoint. Its stdout/stderr are retained under
`inputs/p4_n23_both/`. It has not been retried.

The three `plots/` PNGs compare the final-age hydro, cooling-only,
conduction-only, and available combined profiles at each density, alongside
the historical Mac hydro reference. The n23 plot omits the failed combined
case. [Download all three PNGs](boost_p4_192_physics_plots_2026_10_13.zip).
`data/matched_age_profile_comparison.csv` contains five historical-vs-new
comparison ages per completed variant; the old Mac and new v3.1 problems
differ in more than one way and are not exact matched-physics controls.

`inputs/<case>_<variant>/run.par` gives the explicit cooling and conduction
switches for each run; `input_sha256.txt` and `run.exit` preserve input and
guarded-exit provenance. The full source, binary, run logs, and raw VTUs
remain in Lyra's
`Run_Staging/amrvac_boost_p4_physics_20261009/results_full/` tree, not Git.
The [science report](../boost_p4_2026_10_13/SCIENCE_REPORT.md) details
the boundary and cold-gas caveats. No 24576-cell conduction-on full result
exists: the later 384-cell conduction smokes failed with negative pressure,
and no longer conduction-on resolution ladder was launched.
