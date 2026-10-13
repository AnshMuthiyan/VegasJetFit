# BoOST p4 physics controls: validated results snapshot

This is a compact snapshot of the BoOST p4 fixed-4x-domain controls as of
2026-10-13. Start with [the science report](SCIENCE_REPORT.md) for methods,
provenance, earlier physics variants, and limitations. The canonical run
trees remain on Lyra under
`/Users/jkeohane/GRBs/Run_Staging/amrvac_boost_p4_physics_20261009/`;
raw VTUs, checkpoints, executables, and in-progress runs are not in Git.

## Physics in this snapshot

| Pauley404 case | Ambient density | Radiative cooling | Thermal conduction |
| --- | --- | --- | --- |
| `p4_n22_cooling` | 1e-22 g/cm3 | On | Off |
| `p4_n23_cooling` | 1e-23 g/cm3 | On | Off |
| `p4_n24_cooling` | 1e-24 g/cm3 | On | Off |

All three published 24576-cell Pauley full runs are **cooling-only**.
Their `inputs/<case>/run.par` files explicitly set
`hd_radiative_cooling = .true.` and
`hd_thermal_conduction = .false.`. No conduction-only or
cooling-plus-conduction 24576-cell Pauley result is included. The
science report discusses separate, earlier conduction and combined
controls; those are not the three Pauley runs summarized here.

## What is complete

- The 12288-cell VM and Mac full controls passed 54-snapshot, 5.24-Myr
  validation. Their matched-age cooling comparison is in
  `data/mac_vm_matched_age_profiles_domain4x_12288.csv`.
- All three Pauley404 Mac 24576-cell cooling full controls passed guarded
  exit 0, normal AMRVAC completion, 54 finite-positive VTUs, and the
  5.24-Myr endpoint; see `data/full_validation_mac_domain4x_24576_all3.csv`.
- `data/spatial_comparison_mac_cooling_12288vs24576_domain4x_all3.csv`
  records all 162 matched ages (54 per density). The native final-age
  front, width, and contrast measurements are in
  `data/cooling_inner_front_mac_12288vs24576_domain4x_all3.csv`.
- The three `plots/` PNGs show final-age Mac cooling profiles for the
  12288-to-24576 comparison. Earlier completed 6144-to-12288 and
  1536-to-12288 summaries are retained in `data/` for context.
- `inputs/` preserves each Pauley case's `run.par`, `RUN.txt`, and input
  SHA-256 listing, so the Mac settings and pinned executable can be audited.

## What is not complete

The four Keohane VM 24576-cell full controls (n22/n23/n24 cooling and
n24 hydro) were still running when this snapshot was made. No VM
24576-cell endpoint or paired Mac/VM 24576-cell comparison is published
here. The three Mac cases remain outer-boundary flagged, and their native
fronts and widths change materially between 12288 and 24576 cells.
Numerical completion or Mac/VM agreement is **not** spatial or physical
convergence. These profiles are not approved fitting templates.

The underlying AMRVAC user problem derives from source commit `ecc7b91`
and MPI-AMRVAC v3.1 commit `244c677`; the pinned VM executable SHA-256 is
`046b7402e3525c750ca288a83932e63c5bbcc481a101da9082371fbd80a1d60c`.
The Pauley Mac runs used pinned MPI-AMRVAC v3.1 binary SHA-256
`24bb1f47e7775210de871d0eb1c737928b5200195d8c99f7d20975f3eb1ef6e6`.
Validation and comparison scripts are retained in Lyra's canonical
`Run_Staging/amrvac_boost_p4_physics_20261009/` workspace. This branch
publishes their finished outputs, not a new calculation or physics change.
