# Finite-GMC 40-Msun bubble meeting book provenance

Meeting: 2026-10-20 16:00 America/New_York. This is the 15:11 EDT
premeeting teaching and evidence edition. The GMC 1,000 20,480-cell wind
is independently validated; the GMC 2,000 20,480-cell wind has not run.
The primer explains physical possibilities, not conclusions inferred from
an active or unlaunched stage. Update main.tex and recompile main.pdf only
from validated, newly pulled products for quantitative claims.

## Postmeeting status (2026-10-20 20:09 UTC)

The 15:11-EDT eight-page PDF remains the compiled, visually checked
meeting edition; it has not been regenerated after the meeting. Both
scoped guards are reconciled in the validated update below. The GMC
2,000 wind remains staged only and unlaunched: its host-measured
49,375.262-s projection exceeds the 34,560-s safety ceiling for the
43,200-s guard. Jonathan has been asked whether to leave it held or
prepare an 18-hour guard for separate approval. The monitoring
heartbeat is PAUSED while that decision is pending. No new AMRVAC
launch, automatic retry, guard change, or physics change was made.

## 15:11 EDT validated update and hold

Pauley404-02's GMC 1,000 20,480-cell WR wind completed with guard exit 0,
one `Finished AMRVAC`, empty stderr, seven exact VTUs and 27,203.788-s
AMRVAC runtime. NEW non-overwriting local wind tree:
`results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_20480_f12_0015myr_20261019/Pauley404-02/n20000b1000/wind/`.
Independent `validate_cloud_mass.py` passed exact 0.0015-Myr age,
1,173 initial H II elements, finite-GMC initial mass/density/pressure,
stable 2.5-pc outer state with 20-pc pressure anchor, 2000.794-km/s
maximum WR speed, and 1.000196e-5-Msun/yr inner mass flux. Its exact
base/wind SHA values match the manifest-pinned local inputs; binary,
source, and runner pins remained unchanged. NEW full-density plots and
age-fixed full+zoom rise diagnostics are under
`results/dense_gmc_plots_20261020/meeting_n20000b1000_mac20480_0015/`
and
`results/dense_gmc_inner_edge_20261020/meeting_n20000b1000_mac20480_0015_agefix/`.
At 0.0015 Myr, R10=0.064086668 pc, FWHM=17.662 native cells,
contrast=55.931, FWHM/radius=0.00651, and the local 10--90% rise is
5.581 cells/0.000132181 pc. Both numerical shell and local-ramp gates
pass; these are not a physical width, convergence result, termination
shock or GRB wall. At the identical saved age, the 16,384-cell GMC
1,000 control had R10=0.063717328 pc and a 0.000148013-pc/5.375-cell
rise.

Pauley404-03's GMC 2,000 20,480-cell no-wind static completed with
guard exit 0, one normal finish, empty stderr, two exact VTUs, and
60,722.057-s AMRVAC runtime. NEW non-overwriting local static tree:
`results/dense_gmc_wr_local_inner_outer_n20000_gmc2000_mac_20480_f12_0015myr_20261019/Pauley404-03/n20000b2000/atmosphere/`.
Independent validator passed exact 0.1-Myr age, 1,173 calculated
potential-front cells (ionization is OFF), finite-positive finite-GMC
initial mass/pressure/density, and stable 2.5-pc outer state with 20-pc
pressure anchor. The exact base/static SHA values match local inputs.
Host-measured scaling against its own matched 16,384-cell static/wind
runtimes, `60722.057/27072.209*22013.375`, projects 49,375.262 s for
the staged wind, above the 34,560-s 80%-of-43,200-s ceiling. Therefore
the GMC 2,000 wind is HELD and unlaunched. No new long run before the
meeting; after it, ask Jonathan before any guard change or launch. The
static success does not supply a GMC 2,000 20,480-cell shell result.

NEW inventory v28 at
`results/dense_gmc_radius_coverage_20261017/v28_mac20480_gmc1000_0p001to10/`
includes the new validated age-fixed wind diagnostics with both dated
20261017/20261018 roots: 13/20 occupied 0.001--10-pc bins, 331 accepted
snapshots and 56 locally resolved rises. No accepted shell lies below
0.0251 pc. The .0251--.0398-pc bin has four accepted/zero locally
resolved; .0398--.0631 pc has 36 accepted/three resolved. Snapshot
counts are not independent models or a forced fit.

Historical 11:26 EDT status, superseded by the validated update above:
the GMC1000 20,480-cell no-wind static alone
has passed its full guard and independent finite-GMC/age/potential-front
mesh/outer gate. Ionization is off in this static control; its quoted
"initial H II cells" count is a calculated potential-front mesh diagnostic,
not ionized gas evolved during the static run.
Its new, non-overwriting local validation is at
`results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_20480_f12_0015myr_20261019/Pauley404-02/n20000b1000/atmosphere/validation.csv`
relative to the case root. The matching wind is running under its
43,200-s guard after a 27,184-s host-measured projection met the 20%
margin requirement. Read-only checks found no GMC1000 wind exit, empty
stderr, and an advancing age near 0.000797 Myr (four VTUs so far). The
GMC2000 static had no exit, empty stderr, and an advancing age near
0.0973 Myr; its wind has not launched. These are progress indicators, not
validated results. Jonathan directed no new long AMRVAC launches before
the meeting, including the staged GMC2000 wind. The already running guards
continue. After the meeting, any GMC2000 wind still requires its full
static gate, NEW pull, and host-measured >=20% margin under 43,200 s;
if the margin fails, hold for a decision. No Xcode or networking change.

## Roots

- Local case: /Users/jkeohane/GRBs/AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d
- Book: /Users/jkeohane/GRBs/Share_Folder/Reports/Meeting_Books/26_10_20__finite_gmc_40msun_bubble_resolution
- The book folder resolves to the existing VegasGRBruns Google Drive
  meeting-books location. No environment or build cache was created there.

## Validated controls

| GMC background | Host | Exact 16,384-cell manifest | Validated wind / diagnostics |
| --- | --- | --- | --- |
| 1,000 cm^-3 | Pauley404-02 | dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_16384_f12_0015myr_20261018/manifest.csv (SHA-256 3f28af7e5f4f56681f702df6dad5fdbb1e2f9d4c24f3ba519d109f05621042fa) | results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_16384_f12_0015myr_20261018/Pauley404-02/n20000b1000/wind/validation_with_flux.csv; precise-age metrics results/dense_gmc_inner_edge_20261020/meeting_n20000b1000_mac16384_0015/inner_shell_metrics.csv |
| 2,000 cm^-3 | Pauley404-03 | dense_gmc_inputs_wr_local_inner_outer_n20000_gmc2000_mac_16384_f12_0015myr_20261018/manifest.csv (SHA-256 aea62d00a6383cabc5130150784aea6d78eb0b1006fd5a894f11bea851e12deb) | results/dense_gmc_wr_local_inner_outer_n20000_gmc2000_mac_16384_f12_0015myr_20261018/Pauley404-03/n20000b2000/wind/validation_with_flux.csv; precise-age metrics results/dense_gmc_inner_edge_20261020/meeting_n20000b2000_mac16384_0015/inner_shell_metrics.csv |

The coarser first-width 0.000025-pc controls use the parallel
dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_16384_0015myr_20261018/
and GMC2000 manifests. Their 0.0015-Myr rows are the "coarse" rows in
the meeting book.

The current radius-coverage figure reads only
results/dense_gmc_radius_coverage_20261017/v28_mac20480_gmc1000_0p001to10/log_radius_bins.csv.
It does not read active or failed farms.

## Controlled rung and exact pins

Only cell count (16,384 to 20,480) and geometric stretch ratio
(1.0002367446884142 to 1.0001749835610765) differ from the matched
first-width-0.0000125-pc control. The 0.0002-pc inner boundary,
2.5-pc evolved outer boundary, 20-pc atmosphere anchor, physical source,
wind phase, and output cadence are unchanged. Both statics completed
under 54,000-s guards and passed independent validation. The GMC1000
wind also passed; the GMC2000 wind is held and unlaunched for the measured
margin reason above.

| GMC background | Host | Exact manifest SHA-256 | Remote farm |
| --- | --- | --- | --- |
| 1,000 cm^-3 | Pauley404-02 | 0fc3d471a609286fb5c0071984affc361dc063ed67f57ed8c97613dc266080bb | /private/tmp/van_marle_wr_local_inner_outer_n20000_gmc1000_20480_f12_0015myr_20261019_mac_farm/ |
| 2,000 cm^-3 | Pauley404-03 | e410b673e8c1dfe459ad3257d2c67490d546097072ff314b6a143acb974eda06 | /private/tmp/van_marle_wr_local_inner_outer_n20000_gmc2000_20480_f12_0015myr_20261019_mac_farm/ |

The manifests are, respectively,
dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_20480_f12_0015myr_20261019/manifest.csv
and the corresponding GMC2000 path in the case root. Transferred base,
static, wind, and manifest SHA-256 values match their local originals.
The Mac arm64 AMRVAC binary SHA-256 is
9b01f5e38b37c1436169b4b8f8d478058697f3db28e441bbeed6f70a7b529153;
mod_usr.t is
4b39192f46140b3419800bc65df0b71b0985dcc92ce250499bf0949e02e4383d;
run_cloud_mass_case_mac.py is
489190981c188c143bbe445fc80d13504f1f60cbdc4ff7dc8a2dcb00703c621e.
Each is identical to the corresponding validated host-control farm.

Mac03's first dispatch log records that /usr/bin/python3 was blocked by
the pre-existing Xcode license state before AMRVAC or the runner started.
It is preserved as *.dispatch.log. The actual static uses the installed
/opt/homebrew/bin/python3; its separate *.dispatch-homebrew.log and
*.run.* records are the active evidence. No Xcode setting was changed.

## Primer sources and model meaning

- The exact pinned physics source is
  `AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/mod_usr_cloud_mass.t`
  (SHA-256 above), not the older root `mod_usr.t`. The exact 20,480-cell
  base/atmosphere/wind inputs are named in the manifests above. The base
  defines the 0.2-pc flattening scale, 1.8 slope, 2-pc core, 15-pc GMC,
  backgrounds 1,000/2,000 cm^-3, external 10 cm^-3, hydrostatic anchor
  20 pc, fixed gravity/support, 2.5-pc evolved mesh, cooling and conduction
  off. The static input disables both wind and ionization. The wind input
  enables both and sets the 4.5-Myr phase offset, selecting WR immediately;
  the MS/RSG branches in the source are not evolved in these runs.
- RSG illustrative rates and their uncertainty: Beasor et al. (2020),
  https://arxiv.org/abs/2001.07222 ; slow RSG wind modeling: Mackey et al.
  (2015), https://arxiv.org/abs/1508.07003 . The broad RSG range in the
  primer combines quiescent and brief enhanced/dusty cases and is not a
  single sustained mass-loss prescription.
- WR illustrative WN and WC spectra/winds: Hainich et al. (2014),
  https://arxiv.org/abs/1401.5474 ; Sander et al. (2012),
  https://arxiv.org/abs/1201.6354 . Hainich's bulk-WN RSG inference is
  not a guarantee for this specific 40-Msun star.
- The termination-shock/afterglow issue and limited compact-shock
  mechanisms: van Marle et al. (2006),
  https://arxiv.org/abs/astro-ph/0605698 . The book's ~1e-7 dyn cm^-2
  at 0.1 pc follows `Mdot_WR*v_WR/(4*pi*r^2)` using the pinned 1e-5
  Msun/yr and 2,000 km/s inputs. This is an idealized pressure scale,
  not a measured cloud or termination-shock pressure.
- `R10` in the diagnostics is the inner 10% rise of a swept density excess,
  not the WR wind termination shock or a GRB-fit wall. The 1,500-year
  direct-WR shell cannot establish long-term confinement inside a cold GMC.

## Book products and build

- images/gmc1000_inner_16384.png and images/gmc2000_inner_16384.png
  are copies of new, non-overwriting measure_shell_inner_edge.py plots
  under results/dense_gmc_inner_edge_20261020/meeting_*. Their title now
  prints four decimal places, including the exact 0.0015-Myr endpoint.
- images/gmc1000_inner_20480.png is a copy of the NEW validated,
  age-fixed GMC 1,000 refinement profile named above.
- images/coverage_v28.png was generated from the v28 log-radius-bin CSV
  by plot_coverage.py in this folder. The earlier v27 image remains for
  provenance but is no longer embedded in main.pdf.
- The original five-page PDF used desktop LaTeX and Tectonic and passed
  visual QA. The revised seven-page primer edition was compiled from
  main.tex with `tectonic -X compile main.tex -o
  /tmp/finite_gmc_40msun_book_build_20261020`, rendered with `pdftoppm`
  in that non-Drive scratch directory, and visually checked across all
  seven pages. The checked PDF was copied to main.pdf with matching
  SHA-256 `b19d1bca7ec233361d02face2798ebb9d026be58441bb8225463e4f3c6a4cfca`.
- The current eight-page premeeting edition compiled with Tectonic in
  `/tmp/finite_gmc_40msun_book_build_20261020_1511/`; `pdftoppm`
  rendered all eight pages for visual QA. The compiled PDF SHA-256 is
  `58b92dfb89e3cac0f38c0ecfc7c95ac2995abb35f74fcdaec2ec182effd86c4f`.

No full 4.77-Myr evolution, cooled/conductive variant, identical-input
failed-case retry, convergence/physical-width inference, or GRB-wall fit
is included.
