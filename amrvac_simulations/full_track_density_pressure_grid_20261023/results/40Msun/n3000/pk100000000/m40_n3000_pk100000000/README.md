# m40_n3000_pk100000000: complete full-lifetime simulation

Host: Pauley404-02. Exact DAT endpoint: 4.77 Myr; 49 full saves, 1024 native cells each. The original24 campaign has four validated completed40-Msun cases; 20 original, 46 midpoint and 12 withheld cases remain running at the 26October01:48 UTC check.

- `raw/`: all121 transferred files, including all49 full `.dat` and `.vtu` files, static/smoke products, complete logs and original validation. Bytes match retained remote inventory; checksummed rsync dry-run was empty.
- `native_profiles/`:49 native conservative-cell CSV profiles, including density, radial velocity, pressure, Mach number, cumulative gas mass, positive density-excess mass and signed gas-mass change. Positive excess is Eulerian and is not tracer-defined swept mass.
- `images/`:49 individual density PNGs, initial phase/flow plots and the outer-atmosphere history.
- `reviewed_diagnostics/`: preferred full/inner density-and-mass figures, separate endpoint flow figures, all-save review sheet, reviewed feature diagnostics and provenance. These add complete mass tick labels while retaining the first figures.
- `independent_validation/`: fresh frozen-runtime check, exact DAT cadence/age/finite-positive/analytic initial atmosphere/endpoint outer gates, supplementary interior injection measurements and product/hash/visual QA.

Float64 DAT headers control exact ages. Original Float32 VTU time labels round the endpoint to4.769999874437143Myr. VTU piece vertices number1152, with duplicated block edges; native cell count is1024. No fields were regridded. Units retain365 days/year and1.98892e33 grams/solar mass from the pinned source.

At the endpoint the operational inner R50 is 1.398264 pc; local10--90 width 0.026466955 pc spans only 2.255 native cells and is UNRESOLVED. The flow-selected wind termination candidate is 0.25899887 pc. No independent outer compressed-shell peak meets the stated >2-times-initial-density criterion; this is a missing candidate, not proof that no swept material exists. Half-height envelope widths can include the initial cloud gradient and are not physical wall thicknesses. No convergence, GRB-wall or surrogate eligibility is claimed.

The endpoint outer40--160pc density/pressure changes are 0.11919%/0.005379%; all transient drift values are retained. The n10000/P1e7 case has a transient pressure change4.55% at1.8Myr and a0.69% endpoint change. The first analysis incorrectly imposed the endpoint2% tolerance at every transient save; its postprocessing gate correction is preserved. No AMRVAC run failed or was retried.

Injected MS/RSG/WR rates and speeds pass the exact source/log/phase gates. First-cell center fluxes are evolved interior values: fast-wind estimates are about1.2% above prescribed rates; RSG estimates are about11--13% lower, with speeds13.65--13.73km/s rather than the imposed15km/s. They are not recorded boundary Riemann fluxes and must not be described as exact injection-flux measurements. Slow flow evolves in the fixed star-plus-cloud gravity field. This is a numerical survey, pending refinement and mass-flux convergence work.

Shared host transfer/build/source/input provenance: `../../../../../provenance/Pauley404-02_20261026/`. The retained original farm remains untouched.
