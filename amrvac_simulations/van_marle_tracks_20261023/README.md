# Phase-complete 40-Msun results and newer 25/40-Msun tests

This23October2026 update responds to the request for complete stellar wind histories and all saved outputs. These are van Marle wind tracks, not the historical BoOST tracks.

## Start here

- `full_evolution_40Msun_4p77Myr/`:17 independently revalidated complete40-Msun calculations, each with49 saved VTUs and49 restart .dat files, evolving continuously from age zero through MS, RSG and WR to4.77Myr. Every case folder contains a compressed archive of ALL its saved files and run records, raw SHA-256 manifest, validation output, a phase overview PNG, and49 individual density-profile PNGs. There are833 saved VTUs,833 .dat files and833 individual profile PNGs across these17 runs. `CASE_INDEX.csv` identifies case, density convention, cloud family, gravity prescription, radial domain and archive SHA.
- `short_tests_25Msun_1500yr/`:all seven recent25-Msun MS winds, complete mirrored static/wind records in per-host archives,49 wind VTUs/49 wind .dat saves and the corresponding density figures. These are1500-year tests, NOT7-Myr evolutions. The25-Msun adopted track has MS to6.5Myr and RSG to7.0Myr; no WR. There is no completed full25-Msun evolution in this bundle.
- `short_tests_40Msun_1500yr/`:the GMC2000 20480-cell direct-WR companion that finished after the20October handoff, with all seven wind saves, validation/provenance and new comparison/profile images. This is an unpreconditioned direct-WR test, not a full MS/RSG/WR history.
- The approved NEW24-model matched full-track grid is in [`../full_track_density_pressure_grid_20261023/`](../full_track_density_pressure_grid_20261023/README.md). All24 cases are running; no completed grid endpoint is claimed here. That grid will supply complete25-Msun MS/RSG and40-Msun MS/RSG/WR evolutions across density and independent external confinement.

## Older full40-Msun model families

The16 `ion_*` full runs use exploratory finite-core models:2 cases at central n0=2000cm^-3,10 density/resolution cases at4000--10000cm^-3, and4 smaller-inner-boundary cases at20000/40000cm^-3. These include illustrative photoionization and a prescribed supporting gravity/no-gravity comparison, with cooling/conduction OFF. The final `cloudmass_nref0300_full` case uses star+initial-cloud gravity and an80-pc domain; its endpoint shell spans only3.97 native elements and is underresolved. The detailed current source notes are copied as `MODEL_NOTES_ASOF_20261023.md`; `reference_sources/` preserves context and inputs. Exact raw outputs are in the archives; copied current reference sources are not a claim that every older executable was rebuilt from this exact source snapshot.

These older full evolutions produce predominantly parsec-to-tens-of-parsec structures. They establish full wind-phase evolution, not the desired mostly sub-parsec GRB rising-density family. They are useful comparison results and must not be mixed with the new density-pressure grid as though the cloud physics were identical. Neither complete execution nor a visually sharp shell proves convergence, a physical shock thickness, a GRB wall or a ready fitting surrogate.

## Use and integrity

Extract each archive into a NEW directory; do not overlay different cases. The raw file manifests pin all saved files and run records. `BUNDLE_SHA256.csv` pins every delivered file, including archives, figures and recipes. Case labels distinguish central density n0 from the later n_ref-at1pc convention. Plots use the native saved points, without interpolation; individual frames share a common density scale within each case. Two representative rendered figures were visually checked and every PNG passed image integrity checks.

The full matched grid targets mostly sub-parsec rising-density structures and an eventual registered-profile surrogate with cumulative-mass validation. The earlier large bubbles are not presented as that deliverable. The adopted wind phase table is van Marle et al.2012 Table1: https://arxiv.org/html/1204.2078v3 . Stop before supernova; the two-dimensional interacting-star/SN calculation is a separate problem.
