# Stellar wind results index (23 October2026)

For Ansh's requested full wind-phase evolutions, start with [`van_marle_tracks_20261023/README.md`](van_marle_tracks_20261023/README.md). It includes17 full40-Msun MS/RSG/WR calculations to4.77Myr, all833 saved VTUs and833 restart files, and a density image for every snapshot. Newer25-Msun and40-Msun short tests are explicitly separated.

The NEW24-model matched25/40-Msun full-lifetime grid has four complete, independently validated40-Msun histories;20 original models remain running: [`full_track_density_pressure_grid_20261023/README.md`](full_track_density_pressure_grid_20261023/README.md). Parameters are n_ref=3000/10000/30000cm^-3 at1pc and P_boundary/k_B=1e6/1e7/1e8/1e9 Kcm^-3. Pressure can represent surrounding cloud weight; initial star+cloud gravity is retained without double-counting. Target: mostly sub-parsec rising density, then a validated density/pressure surrogate. No completed new-grid25-Msun7-Myr result is claimed yet.

The20October finite-GMC bundle is an immutable historical snapshot of short direct-WR tests. The separate historical BoOST results branch is not a substitute for either stellar track above.

First grid delivery (26October2026):196 full DAT snapshots,196 full VTUs,196 native-cell profile CSVs and196 per-save density PNGs, plus reviewed full/inner phase/mass/flow diagnostics and complete raw/provenance checks. See [the endpoint inventory](full_track_density_pressure_grid_20261023/completed_endpoint_inventory_20261026.csv). All four inner rise widths are unresolved on the1024-cell survey mesh. Original20+midpoint46+withheld12 continue; the12 holdouts are reserved for validation. No fitted surrogate or convergence claim is delivered.
