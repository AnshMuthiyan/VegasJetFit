# BoOST p4 24576-cell campaign: final preserved state

This folder records the fixed-4x-domain, 24576-base-cell controls at the
2026-10-13 stop decision. Read [the science report](SCIENCE_REPORT.md) for
methods, earlier rungs, and interpretation limits. The earlier [Mac cooling
snapshot](../boost_p4_2026_10_13/README.md) and [192-cell physics
matrix](../boost_p4_192_physics_2026_10_13/README.md) remain unchanged.

## Run outcomes

| Host | Run | Cooling | Conduction | Outcome | Saved VTUs | Last saved age (Myr) |
| --- | --- | --- | --- | --- | ---: | ---: |
| Pauley404-01 | `p4_n22_cooling` | On | Off | Complete | 54 | 5.24 |
| Pauley404-02 | `p4_n23_cooling` | On | Off | Complete | 54 | 5.24 |
| Pauley404-03 | `p4_n24_cooling` | On | Off | Complete | 54 | 5.24 |
| Keohane3 | `p4_n24_hydro` | Off | Off | Complete | 54 | 5.24 |
| Keohane1 | `p4_n22_cooling` | On | Off | Stopped by Jonathan | 26 | 2.50 |
| Keohane2 | `p4_n23_cooling` | On | Off | Stopped by Jonathan | 25 | 2.40 |
| Keohane4 | `p4_n24_cooling` | On | Off | Stopped by Jonathan | 31 | 3.00 |

All seven 24576-cell run trees and the seven completed 12288-cell
reference run trees, including raw VTUs, logs, settings, source inputs,
input hashes, and pinned executables, are in [archives/](archives/). Archive
names label grid size and completed versus stopped cases; SHA-256 values are in
[ARCHIVE_SHA256.txt](ARCHIVE_SHA256.txt). Extract an archive into a new
directory, not over another run. The three stopped VM runs have guarded
`run.exit=1` because their MPI launchers were intentionally interrupted at
2026-10-13 23:59:02 UTC. They were not 5.24-Myr endpoints or numerical
failures. No Pauley AMRVAC/MPI jobs remained active when checked after the
stop request.

## Validated comparisons

- [Mac full validation](data/full_validation_mac_domain4x_24576_all3.csv)
  and [hydro full validation](data/full_validation_domain4x_24576_hydro_n24_20261013.csv)
  check the four completed 54-VTU/5.24-Myr runs. The stopped VM cooling
  runs are deliberately excluded from full validation.
- [Mac cooling spatial comparison](data/spatial_comparison_mac_cooling_12288vs24576_domain4x_all3.csv)
  covers 162 matched ages; [native fronts](data/cooling_inner_front_mac_12288vs24576_domain4x_all3.csv)
  record final radius, width, slope, and density contrast.
- [VM hydro spatial comparison](data/spatial_comparison_hydro_12288vs24576_domain4x_20261013.csv)
  covers 54 matched ages; [native hydro fronts](data/hydro_inner_front_12288vs24576_domain4x_20261013.csv)
  record both grid endpoints.
- [data/](data/) also preserves 12288-cell validation, matched Mac/VM
  cooling comparison, and the 24576-cell smoke/checkpoint validation CSVs.
  [plots/](plots/) contains the three completed Mac cooling final profiles
  and the completed VM hydro final profile.

The 12288-cell run archives supply the underlying profiles for these
paired comparisons. The earlier 192-cell original-domain physics matrix
has its own separate published folder and is not duplicated here.

The Mac cooling fulls remain boundary-flagged and their inner fronts
change materially with resolution. The hydro comparison is one grid pair.
Neither platform agreement nor these pairs establish convergence. There
is no complete 24576-cell VM cooling endpoint to pair with Mac cooling,
and no high-resolution conduction-on run in this set. No fitting template
is approved, and no replacement or higher-resolution run is authorized.
