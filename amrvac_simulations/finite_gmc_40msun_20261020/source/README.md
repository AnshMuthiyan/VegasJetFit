# Ionized-core 40 Msun single-star pilot

## Postmeeting hold and handoff (2026-10-20 20:09 UTC)

Both scoped 20,480-cell guards are reconciled in the validated meeting
evidence below: GMC1000 wind passed; GMC2000 static passed. The matching
GMC2000 wind remains unlaunched because its host-measured 49,375.262-s
projection exceeds the 34,560-s safety ceiling for the staged 43,200-s
guard. Jonathan has been asked whether to keep this wind held or prepare
an 18-hour guard for separate approval. The quiet monitoring heartbeat
is PAUSED pending his decision. No guard, input, physics, Xcode state,
or run was changed after the meeting; the eight-page PDF remains the
visually checked 15:11-EDT edition. Last touched: case README, root
handoff/TODO, book PROVENANCE, and automation status; the existing
compiled PDF and result trees were not regenerated. Remaining uncertainty:
the guard decision and the physical interpretation of the measured shell.

## Meeting evidence update: one refined wind validated, companion held (2026-10-20 19:13 UTC)

Pauley404-02's n_ref20000/GMC1000 20,480-cell direct-WR wind completed
with guard exit 0, one `Finished AMRVAC` marker, empty stderr, seven
exact VTUs and 27,203.788-s AMRVAC runtime. NEW non-overwriting result
tree `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_20480_f12_0015myr_20261019/Pauley404-02/n20000b1000/wind/`
passed independent `validate_cloud_mass.py` at exactly 0.0015 Myr:
1,173 initial H II cells, finite-positive finite-GMC initial
mass/density/pressure, stable evolved outer 2.5 pc with 20-pc pressure
anchor, maximum WR speed 2000.794 km/s and inner mass flux
1.000196e-5 Msun/yr. The pinned binary/source/runner and exact local
base/wind/manifest SHA remain matched. Do not repeat or re-pull.

NEW corrected full-density plot and age-fixed full+zoom inner-rise
diagnostics are under `results/dense_gmc_plots_20261020/meeting_n20000b1000_mac20480_0015/`
and `results/dense_gmc_inner_edge_20261020/meeting_n20000b1000_mac20480_0015_agefix/`.
The 0.0015-Myr endpoint has R10=.064086668 pc, FWHM17.662 native
cells, contrast55.931, FWHM/radius=.00651, and a local 10--90% rise
of5.581 cells/.000132181 pc. Both numerical shell and local-ramp gates
pass. At the matched age, its 16,384-cell fine control has R10=.063717328
pc and a5.375-cell/.000148013-pc rise; the physical rise still moves.
NEW v28 inventory combining the 20261017, 20261018 and new 20261020
age-fixed diagnostics is `results/dense_gmc_radius_coverage_20261017/v28_mac20480_gmc1000_0p001to10/`:
13/20 occupied bins,331 accepted snapshots,56 resolved local ramps;
none below .0251 pc. No physical width, convergence, termination-shock
or GRB-wall claim.

Pauley404-03's n_ref20000/GMC2000 20,480-cell no-wind static also
completed with guard exit0, one normal finish, empty stderr, two VTUs,
and60,722.057-s AMRVAC runtime. NEW non-overwriting
`results/dense_gmc_wr_local_inner_outer_n20000_gmc2000_mac_20480_f12_0015myr_20261019/Pauley404-03/n20000b2000/atmosphere/`
independently passed exact .1-Myr age,1,173 calculated potential-front
cells (ionization OFF), finite-positive finite-GMC initial
mass/pressure/density and stable outer state. Its exact base/static
SHA matched local inputs. The AMRVAC-reported runtime exceeds the
nominal54,000-s guard despite recorded exit0; do not infer a faster
wind from the guard value. Host-specific measured scaling
`60722.057/27072.209*22013.375=49375.262 s` exceeds the34,560-s
80%-of-43,200-s wind-guard ceiling. Therefore the GMC2000 matching
wind remains STAGED ONLY/HELD, with no launch before the meeting and
no automatic postmeeting guard change. Ask Jonathan before any such
decision. Its validated atmosphere is not a measured GMC2000 shell.

The eight-page, visually checked 15:11-EDT meeting edition now lives at
`/Users/jkeohane/GRBs/Share_Folder/Reports/Meeting_Books/26_10_20__finite_gmc_40msun_bubble_resolution/main.pdf`;
its TeX, images and PROVENANCE.md identify exact sources. Last touched:
NEW GMC1000 wind/validation/plots/age-fixed metrics, NEW GMC2000
static/validation, NEW v28 inventory, book TeX/PDF/images/provenance,
this README and root handoff/TODO. Commands: non-overwriting rsync via
SSH, exact guard/marker/stderr/VTU/SHA checks, finite-GMC validators,
corrected plotter, age-fixed rise diagnostic, inventory, Tectonic,
pdftoppm, visual page QA and SHA-256 PDF check. Remaining: meeting
decision on GMC2000 wind guard; no other scoped case remains in flight.
Older dated notes below are historical, not launch authorization.

## Meeting primer and no-new-launch hold (2026-10-20 15:34 UTC)

Jonathan directed **no new long AMRVAC run before the 16:00 EDT meeting**.
This includes the staged GMC2000 20,480-cell wind even if its static
passes; the already running GMC1000 wind and GMC2000 static continue
under their existing guards. At the 11:26 EDT read-only check, GMC1000
wind had no exit, empty stderr and an advancing age near .000797 Myr;
GMC2000 static had no exit, empty stderr and age near .0973 Myr. These
are progress checks, not validated new results. After the meeting,
GMC2000 wind still requires the full static gate, NEW non-overwriting
pull and host-measured >=20% margin under the 43,200-s guard; if that
margin fails, hold for Jonathan's decision. Do not restart or retry.

The existing Share Folder meeting book at
`/Users/jkeohane/GRBs/Share_Folder/Reports/Meeting_Books/26_10_20__finite_gmc_40msun_bubble_resolution/`
now contains a seven-page `main.pdf` and editable `main.tex` with an
undergraduate primer on massive-star formation in cold clouds, MS/RSG/WR
wind ranges, the compact WR termination-shock problem, the distinction
between that shock and the measured swept shell, and the exact direct-WR
model assumptions. `PROVENANCE.md` records primary sources and pinned
inputs. No new run was started and no physics was changed. The short
direct-WR shell remains an early numerical swept shell, not a measured
termination shock, physical width, converged result, or GRB wall.

Last touched: book `main.tex`, `main.pdf`, `PROVENANCE.md`, this README,
root handoff/TODO and the quiet monitor prompt. Commands: read-only
SSH guard/log/VTU checks; `tectonic -X compile`; `pdftoppm`, `pdfinfo`,
`pdftotext` and rendered-page visual QA; SHA-256 check on final PDF.
Output: seven-page letter-size meeting PDF. Remaining: reconcile both
in-flight guards, update only from fully validated products, prepare an
honest as-of meeting edition at 16:00 EDT, and decide separately about
GMC2000 wind if the postmeeting runtime margin fails. Older dated notes
below are historical status records, not current launch authorization.

## GMC1000 20,480-cell atmosphere gate and wind (2026-10-20 11:25 UTC)

Pauley404-02's bounded no-wind static finished under its 54,000-s guard with exit 0, one `Finished AMRVAC` marker, empty stderr, two exact VTUs, and 33,576.259-s AMRVAC runtime. NEW non-overwriting `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_20480_f12_0015myr_20261019/Pauley404-02/n20000b1000/atmosphere/` passed the independent finite-GMC validator at 0.099999998 Myr, with 1,173 initial H II cells, finite-positive and matching initial mass/density/pressure, and stable outer 2.5 pc with hydrostatic pressure anchored at 20 pc. This validates the atmosphere only; do not re-pull or repeat it.

Its exactly matching 0.0015-Myr/seven-VTU wind now runs under the staged 43,200-s guard. The host-measured projection `33576.259/27155.067*21985.413 = 27184.169 s` leaves more than 20% margin. Pinned arm64 binary/source/runner/base/wind/manifest SHA, idle host, 93% free memory, 675 GiB available disk, empty wind output, first VTU, one AMRVAC rank, and empty stderr passed. Do not restart; require guard0/one marker/empty stderr/seven VTUs/exact age/WR speed and flux/finite-GMC initial and stable outer before NEW pull and diagnostics.

Pauley404-03 GMC2000 static remains active with empty stderr and advancing steps. Its Tailscale address is offline; the LAN host key matches the saved Tailscale identity, so monitoring uses SSH `-o HostKeyAlias=100.91.4.44 -J pauley404-02 jkeohane@pauley404-03.local`. Do not change Xcode or networking. Require its own complete static gate and NEW pull before a measured-margin matching wind. Last touched: GMC1000 NEW static results/validation and this README/root handoff/TODO/book provenance; commands were remote guard/SHA/resource checks, `rsync -av --ignore-existing` over SSH without `-n`, `validate_cloud_mass.py --atmosphere --finite-gmc --edge-width-pc 0.5 --n-bg 1000 --inner-pc 0.0002 --domain-max-pc 2.5 --atmosphere-outer-pc 20`, guarded wind launch, and initial-rank check. Remaining: both winds, GMC2000 static, age-fixed matched comparisons, inventory and meeting book; no physics or interpretation change.

## 20 October meeting and 20,480-cell controlled mesh pair (2026-10-20 02:10 UTC)

Jonathan's new direction resumes a bounded same-physics resolution check
through the 20 October 16:00 EDT meeting; it supersedes the previous
Monday no-new-case cutoff for these two cases only. The validated
16,384-cell GMC1000/GMC2000 controls have 0.0015-Myr endpoint inner
10% radii .063717/.063751 pc and local 10--90% ramps 5.38/5.56 native
cells. Their coarser first-width .000025-pc counterparts have ramps
4.74/4.82 cells. Physical rise widths and radii move with grading, so
there is no convergence claim.

NEW n_ref20000/GMC1000 and GMC2000 20,480-cell, inner .0002-pc,
first-width .0000125-pc, evolved outer 2.5-pc/atmosphere anchor 20-pc
no-wind statics run on Pauley404-02/03 under 54,000-s guards. Exact
manifests are in the new
dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_20480_f12_0015myr_20261019/
and GMC2000 counterpart directories; remote farms have corresponding
names under /private/tmp/. Controlled base diffs change only
domain_nx1 16384->20480 and qstretch_baselevel(1)
1.0002367446884142->1.0001749835610765. Physical inputs, first
width, boundaries, wind phase and save cadence remain fixed.
Host-measured scaling projects static~33.9ks/wind~27.5ks, below
80%-of-guard ceilings 43.2/34.56ks. Pinned binary/source/runner and
exact transferred input SHA, idle/resources/empty output, first VTU,
one rank and empty stderr passed.

Mac03's first /usr/bin/python3 dispatch was blocked by its pre-existing
Xcode license before the runner or AMRVAC started. That log is preserved;
the actual static runs with installed Homebrew Python. No system or
Xcode setting was changed. Do not restart either active guard.

Matching .0015-Myr/seven-VTU winds are staged only. Require static
guard0/one Finished AMRVAC/empty stderr/two VTUs/exact .1-Myr age/
H II>=10/finite-positive finite-GMC initial mass-pressure-density and
stable outer, plus NEW non-overwriting pull, before any wind. Reassess
host-measured >=20% margin under a 43,200-s wind guard. Wind also
requires exact age, WR speed2000 km/s and mass flux1e-5 Msun/yr.
Plot and measure full inward precursor and local 10/50/90 rise in NEW
directories; refresh inventory. At 16:00 EDT freeze an honest as-of
meeting edition of the book; keep monitoring any remaining in-flight
guards and pause heartbeat only after both scoped cases are reconciled.

NEW five-page LaTeX/PDF meeting book:
/Users/jkeohane/GRBs/Share_Folder/Reports/Meeting_Books/26_10_20__finite_gmc_40msun_bubble_resolution/.
It compiled in desktop LaTeX and Tectonic and passed rendered-page QA.
Its PROVENANCE.md records exact inputs, SHA pins, figure sources and
guards. NEW precise-age figure diagnostics are under
results/dense_gmc_inner_edge_20261020/meeting_*; a one-line fix in
measure_shell_inner_edge.py prints four decimal places so .0015 Myr is
not mislabeled .001 Myr. The book uses the v27 gated coverage CSV and
labels the 20,480-cell winds pending.

Last touched: paired generated inputs/manifests, precise-age plotting
fix and two NEW diagnostics, book TeX/PDF/images/provenance/plot script,
README/root handoff/TODO and heartbeat. Commands: generator, base
diffs, SHA/SSH/resource checks, non-overwriting rsync, guarded Mac
static launches, focused pytest (5 passed), Tectonic/desktop LaTeX,
pdftoppm and five-page visual QA. Remaining: static gates, conditional
winds and matched-age book measurements; sub-.0251-pc coverage,
physical width, convergence and GRB interpretation remain unresolved.
Older Monday-cutoff notes below are historical.

## Monday in-flight reconciliation complete; campaign hold (2026-10-19 08:20 UTC)

All AMRVAC cases launched before the Monday 00:00 America/New_York cutoff have now finished and been independently reconciled. No post-cutoff case or staged wind was launched. The final Keohane1 n_ref20000/GMC2000 original20-pc, 16384-cell inner.0005/first.00003125-pc .0015-Myr wind finished under its28800-s guard in19730.874 s with exit0/one Finished AMRVAC/empty stderr/seven VTUs. NEW non-overwriting `results/dense_gmc_wr_full_inner_f31_n20000_gmc2000_vm_k1_16384_20261018/Keohane1/n20000b2000/wind/` passed independent exact-age/472 initial H II/finite-positive and finite-GMC initial mass-pressure-density/stable-outer checks, with WR speed2000.432 km/s and flux1.000195e-5 Msun/yr. Validation uses the pinned edge width.5 pc, evolved and pressure-anchor outer20 pc, and inner.0005 pc; `validation.csv` holds the quantitative gate.

NEW corrected full-density `results/dense_gmc_plots_20261019/full_inner_f31_n20000b2000_k1_vm16384_0015/` and age-fixed full+zoom rise `results/dense_gmc_inner_edge_20261018/full_inner_f31_n20000b2000_k1_vm16384_0015_agefix/` were visually inspected; the full inward precursor and local 10/50/90% rise are retained. Earlier four wind snapshots have no unambiguous inner-side shell jump. At .00125 Myr the numerical shell gates first pass (R10=.055127 pc, FWHM7.53 native cells, contrast52.12), while the local 10-90% ramp is3.47 cells. At endpoint R10=.061374 pc, FWHM9.22 cells, contrast46.38 and width/radius well below.25; the local ramp is3.88 cells, still unresolved by the >=5-cell test. These values are not physical shock widths or convergence evidence.

NEW `results/dense_gmc_radius_coverage_20261017/v27_full_inner_f31_k1_0p001to10/` joins both dated diagnostics roots and has13/20 quality-gated bins,326 accepted snapshots,54 resolved local ramps overall. The .0251-.0398-pc bin has three accepted/three cases/zero resolved; .0398-.0631 pc has33 accepted/15 cases/two resolved, while all bins below .0251 pc remain empty. The selected negative-k analytic first-to-last GRB radii .001225-.719437 pc remain model-dependent and are not measured walls. No full4.77-Myr, stopped BoOST, cooling/conduction/fixed-gravity/support change, identical-input failed retry, convergence, physical-width, GRB-wall or forced-fit claim. Prior failed8192 farms/evidence and Mac03 Xcode licensing are untouched. No further AMRVAC launch is authorized under this bounded campaign; heartbeat is to be paused.

Last touched: NEW K1 wind/validation, corrected full plot, age-fixed rise, v27 inventory, case README/root handoff/TODO. Commands: guarded SSH exit/marker/stderr/VTU and pinned-SHA checks, `rsync -av --ignore-existing`, `validate_cloud_mass.py` with exact inputs and expected WR flux, `plot_dense_gmc_scan.py`, `measure_shell_inner_edge.py`, PNG inspection, `inventory_shell_radius_coverage.py`. Remaining scientific uncertainty: unresolved inner ramps for the original20-pc K1 bracket, unfilled sub-.0251-pc radius bins, model dependence of any GRB-wall interpretation; all require a separately authorized next campaign. Older notes below are historical.

## Monday K4 static and Mac02/03 finer wind reconciliation (2026-10-19 08:11 UTC)

Keohane4 n_ref20000/GMC1000 original20-pc, 16384-cell inner.00025/first.00003125-pc no-wind static finished guard0/one Finished AMRVAC/empty stderr/two VTUs in21694.765 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_f31_n20000_gmc1000_vm_k4_16384_20261018/Keohane4/n20000b1000/atmosphere/` independently passed exact .1-Myr age/479 initial H II/finite-positive and finite-GMC initial mass-pressure-density/stable outer. Its matching wind remains staged and must not launch after the Monday cutoff.

Pauley404-02 GMC1000 and Pauley404-03 GMC2000 inward+short-domain 16384-cell first-width.0000125-pc .0015-Myr winds finished guard0/one marker/empty stderr/seven VTUs in21985.413/22013.375 s. NEW non-overwriting wind pulls under `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_16384_f12_0015myr_20261018/Pauley404-02/n20000b1000/wind/` and the matching GMC2000 `Pauley404-03/n20000b2000/wind/` independently passed exact age/1135 initial H II each/finite-GMC initial mass-pressure-density/stable outer (evolved outer2.5 pc, pressure anchor20 pc), with WR speeds2000.795/2000.797 km/s and fluxes1.000192e-5/1.000192e-5 Msun/yr. Flux-inclusive checks are in `validation_with_flux.csv`. Corrected full-density PNGs in NEW `results/dense_gmc_plots_20261019/local_inner_f12_*_mac16384_0015/` and age-fixed full+zoom rises in NEW `results/dense_gmc_inner_edge_20261018/local_inner_f12_*_mac16384_0015_agefix/` were visually inspected; the broad inward precursor and distinct inner 10/50/90% rise are retained. Both first pass numerical shell gates at .0005 Myr (FWHM5.65/5.90 native cells) but local ramps stay below five until .00125 Myr. Endpoints: R10=.063717/.063751 pc, FWHM15.55/16.47 cells, contrast54.09/51.21, local 10-90% ramps5.38/5.56 cells. These are numerical resolution checks, not physical shock widths or convergence.

NEW `results/dense_gmc_radius_coverage_20261017/v26_inner_f12_mac_pair_0p001to10/` joins both dated diagnostics roots:13/20 quality-gated bins,324 accepted snapshots,54 resolved local ramps overall. The .0251-.0398-pc bin has three accepted/three cases/zero resolved; .0398-.0631 pc has31 accepted/14 cases/two resolved; bins below .0251 pc remain empty. Selected negative-k analytic GRB radii .001225-.719437 pc are model-dependent, not measured walls. Do not repeat/re-pull these completions. K1 finer wind is the only remaining in-flight guard; validate/pull/measure it, then pause heartbeat without launching any new case. Last touched: three NEW stage trees/validations, two plot/age-fixed trees, v26 inventory, README/root handoff/TODO. Commands: guarded SSH checks, `rsync --ignore-existing`, independent finite-GMC validators (including explicit expected WR flux), corrected plot/PNG inspection and log-radius inventory. Failed8192 evidence and Mac03 Xcode remain untouched; no physics, full4.77-Myr, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Monday K2/K3 finer atmosphere reconciliation (2026-10-19 05:21 UTC)

Keohane2 n_ref20000/GMC2000 original20-pc, 16384-cell inner.00025/first.00003125-pc no-wind static finished guard0/one Finished AMRVAC/empty stderr/two VTUs in21987.773 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_f31_n20000_gmc2000_vm_k2_16384_20261018/Keohane2/n20000b2000/atmosphere/` passed independent exact .1-Myr age/479 initial H II/finite-positive and finite-GMC initial mass-pressure-density/stable outer. Keohane3 GMC1000 inner.0005/first.00003125-pc counterpart finished the same guard checks in15545.520 s; NEW `results/dense_gmc_wr_full_inner_f31_n20000_gmc1000_vm_k3_16384_20261018/Keohane3/n20000b1000/atmosphere/` passed exact .1-Myr age/472 initial H II and finite-GMC initial/outer checks. These are atmosphere gates, not measured wind shells; do not repeat/re-pull. Both matching winds remain staged and **must not launch after the Monday cutoff**. Remaining in-flight: Mac02/03 and K1 winds, K4 static; then pause the heartbeat. Last touched: two NEW validated static trees and README/root handoff/TODO; commands were remote guard checks, `rsync --ignore-existing`, and independent finite-GMC validators. No physics, failed8192 evidence, Mac03 Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Monday cutoff and Mac01 GMC1000 wind reconciliation (2026-10-19 04:18 UTC)

Monday 00:00 America/New_York has passed: **launch no new AMRVAC case**, including staged winds after static gates. Reconcile the six guards still in flight, then pause the heartbeat. Pauley404-01 n_ref20000/GMC1000 32768-cell short-domain .001-Myr wind finished guard0/one Finished AMRVAC/empty stderr/nine VTUs in5654.522 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_n20000_gmc1000_mac_32768_001myr_20261018/Pauley404-01/n20000b1000/wind/` passed independent exact age/247 initial H II/finite-GMC initial mass-pressure-density/stable outer with evolved outer2.5/pressure anchor20 pc, WR speed2000.287 km/s and mass flux1.000222e-5 Msun/yr. Corrected full density and age-fixed full+zoom inward-rise profiles in NEW directories were visually inspected; the full precursor is retained. Endpoint R10=.047413 pc/FWHM4.40 native cells/contrast58.04/local 10-90% ramp2.47 cells: no saved age clears the FWHM>=5 shell gate or the >=5-cell local-ramp resolution check. Do not repeat/re-pull or infer convergence, physical shock width, GRB wall or fit.

NEW `results/dense_gmc_radius_coverage_20261017/v25_outer_control_mac32768_gmc1000_001_0p001to10/` joins both dated diagnostic roots and remains at13/20 occupied bins/314 accepted snapshots/50 resolved local ramps overall. The .0251-.0398-pc bin has one accepted/one case/zero resolved ramps; .0398-.0631 pc has25 accepted/12 cases/zero resolved, and smaller bins are empty. Last touched: NEW Mac01 wind/plot/age-fixed/v25 trees and case README/root handoff/TODO; commands were guard/marker/stderr/VTU checks, `rsync --ignore-existing`, independent validator, corrected plot/PNG inspection and inventory. Remaining: six in-flight guards and their non-overwriting validation; no new cases after cutoff. Failed8192 evidence and Mac03 Xcode licensing remain untouched.

## Mac01 GMC1000 and K1 finer static gates; matching winds (2026-10-19 02:47 UTC)

Pauley404-01 n_ref20000/GMC1000 32768-cell short-domain no-wind static finished guard0/one Finished AMRVAC/empty stderr/two VTUs in4709.179 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_n20000_gmc1000_mac_32768_001myr_20261018/Pauley404-01/n20000b1000/atmosphere/` independently passed exact .1-Myr age/247 initial H II/finite-GMC initial mass-pressure-density/finite-positive and stable outer fields with evolved outer2.5/pressure anchor20 pc. Do not repeat/re-pull; this is an atmosphere gate. Matching DISTINCT .001-Myr/nine-VTU wind now runs under28800-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc1000_32768_001myr_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_n20000_gmc1000_mac_32768_001myr_20261018/manifest.csv`. Host-measured same-mesh runtime scaling projects about5643-s wind below23040-s 80%-guard ceiling; pinned Lyra binary/source/runner/input SHA, idle/resources/empty output/initial VTU/one rank/empty stderr passed. **Do not restart.** Validate guard0/one marker/empty stderr/nine VTUs/exact .001 Myr/finite-GMC initial and stable outer/WR2000-km-s speed and1e-5-Msun-yr flux, then NEW pull, corrected full and age-fixed full+zoom rise and inventory.

Keohane1 n_ref20000/GMC2000 original20-pc 16384-cell inner.0005/first.00003125-pc no-wind static finished guard0/one marker/empty stderr/two VTUs in15433.040 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_f31_n20000_gmc2000_vm_k1_16384_20261018/Keohane1/n20000b2000/atmosphere/` independently passed exact .1-Myr age/472 initial H II/finite-GMC initial mass-pressure-density/finite-positive and stable outer. Do not repeat/re-pull. Matching DISTINCT .0015-Myr/seven-VTU wind now runs under28800-s guard in `/tmp/van_marle_wr_full_inner_f31_n20000_gmc2000_k1_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_f31_n20000_gmc2000_vm_k1_16384_20261018/manifest.csv`. Host-measured static ratio projects19807-s wind below23040-s 80%-guard ceiling; pinned Linux SHA/idle/resources/empty output/initial VTU/one rank/empty stderr passed. **Do not restart.** Validate guard0/marker/stderr/seven VTUs/exact age/WR speed+flux/outer, then NEW pull, corrected full/age-fixed full+zoom rise and inventory.

Last touched: two NEW validated static trees and README/root handoff/TODO; commands were guarded SSH/SHA/resource checks, `rsync --ignore-existing`, independent finite-GMC validators and guarded wind launches. Remaining: five winds (including Mac02/03 finer) and K2/3/4 statics, small-radius unresolved ramp gap and Monday 00:00 EDT no-new-case cutoff. No physics/Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim; failed8192 evidence untouched. Older notes below are historical.

## Keohane4 GMC1000 bracket profile and finer-first-cell static (2026-10-19 01:50 UTC)

Keohane4 n_ref20000/GMC1000 original20-pc 16384-cell inner.00025/first.0000625-pc .0015-Myr wind finished guard0/one Finished AMRVAC/empty stderr/seven VTUs in9806.748 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc1000_vm_k4_16384_20261018/Keohane4/n20000b1000/wind/` passed independent exact age/250 initial H II/finite-GMC initial mass-pressure-density/stable outer/2000.652-km-s WR speed and1.000462e-5-Msun-yr flux. Corrected full and age-fixed `results/dense_gmc_inner_edge_20261018/full_inner_bracket_n20000b1000_k4_vm16384_0015_agefix/` full+zoom profiles were visually inspected; full inward precursor retained. At .00125 Myr R10=.053752 pc/FWHM4.62 native cells fails shell gate; endpoint R10=.059806 pc/FWHM5.50/contrast47.60 passes numerical shell gates but local 10-90% ramp2.81 cells remains unresolved. Earlier snapshots have no unambiguous inner-side jump. Do not repeat/re-pull or infer convergence, physical shock width or GRB wall.

NEW `results/dense_gmc_radius_coverage_20261017/v24_full_inner_bracket_k4_0p001to10/` joins both dated age-fixed roots:13/20 quality-gated bins/314 accepted snapshots/50 resolved local ramps overall. The .0251-.0398-pc bin has one accepted/one case/zero resolved; .0398-.0631 pc has25 accepted/12 cases/zero resolved, smaller bins empty. Analytic negative-k radii remain model-dependent, not measured walls.

Freed K4 now runs a DISTINCT same-physics 16384-cell original20-pc inner.00025/first.00003125-pc **no-wind static** under43200-s guard in `/tmp/van_marle_wr_full_inner_f31_n20000_gmc1000_k4_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_f31_n20000_gmc1000_vm_k4_16384_20261018/manifest.csv`. Controlled base diff from validated K4 bracket changes only radial stretch; 2x its measured10682.303-s static runtime projects below34560-s 80%-guard ceiling. Pinned Linux binary/source/runner/exact input SHA, idle/62-GiB RAM available/111-GiB disk/empty output, initial VTU/one rank/empty stderr passed. **Do not restart or pre-launch wind.** Require guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW pull, then host-measured >=20% margin before conditional .0015-Myr/seven-VTU wind under28800 s. Last touched: NEW K4 wind/plot/age-fixed trees, v24 inventory, generated f31 inputs, README/root handoff/TODO; commands were guarded SSH/SHA/resource checks, rsync, independent validator, corrected plot/PNG inspection, inventory, generator/controlled diff and guarded launch. Remaining: active guards and small-radius ramp-quality gap; no physics/Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Mac02/03 finer inward atmosphere gates and early winds (2026-10-19 01:42 UTC)

Pauley404-02 n_ref20000/GMC1000 and Pauley404-03 n_ref20000/GMC2000 inward/short-domain 16384-cell first-width.0000125-pc no-wind statics finished guard0/one Finished AMRVAC/empty stderr/two VTUs in27155.067/27072.209 s. NEW non-overwriting pulls under `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_16384_f12_0015myr_20261018/Pauley404-02/n20000b1000/atmosphere/` and GMC2000 counterpart independently passed exact .1-Myr age/1135 initial H II each, finite-positive/finite-GMC initial mass-pressure-density and stable outer fields with inner.0002/evolved outer2.5/pressure anchor20 pc. **Do not repeat/re-pull:** these are atmosphere gates, not shell results.

Matching DISTINCT .0015-Myr/seven-VTU winds now run under36000-s guards in `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc1000_16384_f12_0015myr_20261018_mac_farm/` and GMC2000 counterpart, exact `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_16384_f12_0015myr_20261018/manifest.csv` and GMC2000 counterpart. Host-specific measured static ratios versus validated first-width.000025-pc controls project22113/22083-s winds, below28800-s 80%-guard ceiling. Pinned Lyra binary/source/Mac runner and exact input SHA, idle/93%-free memory/676-518-GiB disk/empty wind output, initial VTU/one rank/empty stderr passed. **Do not restart.** On completion require guard0/one marker/empty stderr/seven VTUs/exact .0015 Myr/finite-GMC initial and stable outer/2000-km-s speed/1e-5-Msun-yr flux, then NEW non-overwriting pulls, corrected full density and age-fixed full+zoom local 10/50/90-rise inspection and inventory refresh. Last touched: two NEW validated static trees, README/root handoff/TODO; commands were guarded SSH/SHA/resource checks, `rsync --ignore-existing`, independent validators and guarded wind launches. Remaining: active guards and small-radius ramp-quality gap; no physics/Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Mac01 65536 early profile and GMC1000 outer-control static (2026-10-19 01:23 UTC)

Pauley404-01 n_ref20000/GMC2000 65536-cell inner.001/first.00003125/evolved outer2.5-pc .001-Myr wind finished guard0/one Finished AMRVAC/empty stderr/nine VTUs in22818.660 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_65536_001myr_20261018/Pauley404-01/n20000b2000/wind/` independently passed exact age/494 initial H II/finite-GMC initial mass-pressure-density/stable outer with pressure anchor20 pc,2000.282-km-s WR speed and1.000704e-5-Msun-yr flux. Corrected full density and age-fixed `results/dense_gmc_inner_edge_20261018/local_outer_control_n20000b2000_mac65536_001_agefix/` full+zoom inward-rise profiles were visually inspected; the full precursor is retained. First shell-gated at .000625 Myr R10=.037472 pc/FWHM5.08 native cells, local 10-90% ramp2.65 cells. Endpoint R10=.049044 pc/FWHM8.71/contrast62.37, ramp3.88 cells. No local ramp is resolved at >=5 cells; do not repeat/re-pull or claim convergence, physical shock width or GRB wall.

NEW `results/dense_gmc_radius_coverage_20261017/v23_outer_control_mac65536_001_0p001to10/` joins both dated age-fixed roots:13/20 quality-gated bins/313 accepted snapshots/50 resolved local ramps overall. The newly occupied .0251-.0398-pc bin has one accepted snapshot/one case/zero resolved ramps; .0398-.0631 pc has24 accepted/11 cases/zero resolved ramps, and smaller bins remain empty. Selected negative-k GRB analytic radii are model-dependent, not measured walls.

Freed Mac01 now runs a DISTINCT n_ref20000/GMC1000 32768-cell inner.001/first.0000625/evolved outer2.5-pc/pressure-anchor20-pc **no-wind static** under7200-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc1000_32768_001myr_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_n20000_gmc1000_mac_32768_001myr_20261018/manifest.csv`. Controlled base diff from validated GMC2000 32768 outer-control changes only `n_bg_cm3`; pinned Lyra arm64 binary/source/Mac runner/exact input SHA, idle/resources/empty output, initial VTU/one rank/empty stderr passed. Prior same-mesh static4717.082 s is below5760-s 80%-guard ceiling. **Do not restart or pre-launch wind.** Require guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW pull, then host-measured >=20% margin before matching .001-Myr/nine-VTU wind under28800-s guard. Last touched: NEW Mac01 wind/plot/age-fixed trees, v23 inventory, generated GMC1000 inputs, README/root handoff/TODO; commands were guarded SSH/SHA/resource checks, `rsync --ignore-existing`, validator, corrected plot/PNG inspection, inventory, generator/controlled diff and static launch. Remaining: active guards and sub-.0251-pc quality gap; no physics/Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Keohane3 GMC1000 bracket early profile and finer-first-cell static (2026-10-19 00:58 UTC)

Keohane3 n_ref20000/GMC1000 original20-pc 16384-cell inner0.0005/first0.0000625-pc .0015-Myr wind finished guard0/one Finished AMRVAC/empty stderr/seven VTUs in9822.694 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc1000_vm_k3_16384_20261018/Keohane3/n20000b1000/wind/` passed independent exact-age/finite-GMC initial mass-pressure-density/stable outer/2000.427-km-s WR speed/9.991108e-6-Msun-yr flux. Corrected full and age-fixed full+zoom profiles were inspected, retaining the full inward precursor. At .00125 Myr R10=.053624 pc but FWHM4.63 native cells fails the shell gate; endpoint R10=.059667 pc/FWHM5.52/contrast47.39 passes numerical shell gates but local ramp2.80 cells is unresolved. Do not repeat/re-pull or claim convergence, physical width or a GRB wall.

NEW `results/dense_gmc_radius_coverage_20261017/v22_full_inner_bracket_k3_0p001to10/` joins both dated age-fixed roots:12/20 quality-gated bins,309 accepted snapshots,50 resolved local ramps overall. The .0398-.0631-pc bin has21 accepted/ten cases/zero resolved ramps; smaller bins are empty. Selected negative-k analytic radii are not measured walls.

Freed K3 now runs a DISTINCT same-physics 16384-cell original20-pc inner0.0005/first0.00003125-pc **no-wind static** under28800-s guard in `/tmp/van_marle_wr_full_inner_f31_n20000_gmc1000_k3_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_f31_n20000_gmc1000_vm_k3_16384_20261018/manifest.csv`. Controlled base diff from validated GMC1000 K3 bracket changes only radial stretch; about2x its measured7689.699-s static runtime projects below23040-s 80%-guard ceiling. Pinned Linux binary/source/runner and exact input SHA, idle/46-GiB available RAM/111-GiB disk/empty output, first VTU/one rank/empty stderr passed. **Do not restart or pre-launch wind:** require guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW pull, then measured >=20% margin before conditional .0015-Myr/seven-VTU wind under28800 s. Other six hosts remain guarded; failed8192 inward evidence untouched. Last touched: NEW K3 wind/plot/age-fixed trees, v22 inventory, generated f31 inputs, README/root handoff/TODO; commands were guarded remote/SHA/resource checks, `rsync --ignore-existing`, independent validator, corrected plot/PNG inspection, inventory, generator/controlled diff and guarded static launch. Remaining: active guards and small-radius ramp-quality gap; no physics or Xcode change. Older notes below are historical.

## Keohane2 bracket early profile and finer-first-cell static (2026-10-18 23:16 UTC)

Keohane2 n_ref20000/GMC2000 original20-pc 16384-cell inner0.00025/first0.0000625-pc .0015-Myr wind finished guard0/one Finished AMRVAC/empty stderr/seven VTUs in10078.430 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc2000_vm_k2_16384_20261018/Keohane2/n20000b2000/wind/` passed independent exact-age/finite-GMC initial mass-pressure-density/stable outer/2000.653-km-s WR speed/1.000462e-5-Msun-yr flux. Corrected full and age-fixed full+zoom profiles were inspected. At .00125 Myr R10=.053796 pc but FWHM4.82 native cells fails the shell gate; endpoint R10=.059849 pc, FWHM5.89 cells, contrast44.80 passes numerical shell gates but local ramp3.03 cells is unresolved. Preserve the full inward precursor; do not repeat/re-pull or claim convergence, physical width or a GRB wall.

NEW `results/dense_gmc_radius_coverage_20261017/v21_full_inner_bracket_k2_0p001to10/` joins both dated age-fixed roots:12/20 quality-gated bins,308 accepted snapshots,50 resolved local ramps overall. The .0398-.0631-pc bin has20 accepted/nine cases/zero resolved ramps; smaller bins are empty. Selected negative-k analytic radii are not measured walls.

Freed K2 now runs a DISTINCT same-physics 16384-cell original20-pc inner0.00025/first0.00003125-pc **no-wind static** under43200-s guard in `/tmp/van_marle_wr_full_inner_f31_n20000_gmc2000_k2_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_f31_n20000_gmc2000_vm_k2_16384_20261018/manifest.csv`. Controlled base diff from validated K2 bracket changes only radial stretch; roughly2x its10509.521-s static runtime projects ~21 ks below the34.56-ks 80%-guard ceiling. Pinned Linux binary/source/runner and exact input SHA, idle/46-GiB available RAM/111-GiB disk/empty output, first VTU/one rank/empty stderr passed. **Do not restart or launch staged wind before full static gate:** guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW pull. Only after host-measured >=20% margin may its matching .0015-Myr/seven-VTU wind run under36000-s guard. K1 finer static, K3/K4 winds and three Mac guards remain active; failed8192 inward evidence untouched. Last touched: NEW K2 wind/plot/age-fixed trees, v21 inventory, generated f31 input set, README/root handoff/TODO; commands were guard/SHA/resource checks, rsync, validator, corrected plot/PNG inspection, inventory, generator/base diff and guarded static launch. Remaining: active guards and small-radius ramp-quality gap; no physics or Xcode change. Older notes below are historical.

## Keohane4 GMC1000 bracket static and wind (2026-10-18 23:02 UTC)

Keohane4's original20-pc n_ref20000/GMC1000 16384-cell inner0.00025/first0.0000625-pc static finished guard0/one Finished AMRVAC/empty stderr/two VTUs in10682.303 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc1000_vm_k4_16384_20261018/Keohane4/n20000b1000/atmosphere/` passed independent exact .1-Myr age,250 initial H II, finite-positive/finite-GMC initial mass-pressure-density and stable outer validation. Do not repeat/re-pull; this is an atmosphere gate, not a shell result.

The matching DISTINCT .0015-Myr/seven-VTU wind now runs under28800-s guard in `/tmp/van_marle_wr_full_inner_bracket_n20000_gmc1000_k4_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_bracket_n20000_gmc1000_vm_k4_16384_20261018/manifest.csv`. Measured static-runtime scaling of K1's matched wind projects ~13.7 ks, below the23.04-ks 80%-guard ceiling. Pinned Linux binary/source/runner and exact base/wind/manifest SHA, idle/62-GiB available RAM/111-GiB disk/empty wind output, first VTU/one rank/empty stderr passed. Do not restart. Require guard0/one marker/empty stderr/seven VTUs/exact age/finite-GMC initial and stable outer/2000-km-s WR speed and1e-5-Msun-yr flux before NEW pull, corrected full and age-fixed full+zoom inward-rise inspection and inventory. K1 finer static, K2/K3 winds and three Mac guards remain active; failed8192 inward evidence untouched. Last touched: NEW validated K4 static tree, README/root handoff/TODO; commands were guarded SSH/SHA/resource checks, `rsync --ignore-existing`, validator and wind launch. Remaining: active guards and small-radius ramp-quality gap; no physics, Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## K1 bracket early profile and half-first-width static (2026-10-18 22:27 UTC)

Keohane1 n_ref20000/GMC2000 original20-pc 16384-cell inner0.0005/first0.0000625-pc .0015-Myr wind finished guard0/one Finished AMRVAC/empty stderr/seven VTUs in9871.443 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc2000_vm_k1_16384_20261018/Keohane1/n20000b2000/wind/` passed independent exact age/finite-GMC initial mass-pressure-density/stable outer/2000.427-km-s WR speed/9.991108e-6-Msun-yr flux. Corrected full density and age-fixed full+zoom inward-rise profiles were visually inspected. At .00125 Myr R10=.053675 pc, FWHM4.87 native cells fails the shell gate; at .0015 Myr R10=.059708 pc, FWHM5.91 cells, contrast44.62 passes numerical shell gates but local ramp3.06 cells is unresolved. The full inward precursor remains visible. Do not repeat/re-pull or infer convergence, physical shock width or a GRB wall.

NEW `results/dense_gmc_radius_coverage_20261017/v20_full_inner_bracket_k1_0p001to10/` combines both dated age-fixed roots:12/20 quality-gated bins,307 accepted snapshots,50 >=5-cell local ramps overall. The .0398-.0631-pc bin has19 accepted/eight cases/zero resolved ramps; all smaller bins remain empty. Selected negative-k GRB analytic radii are model-dependent, not measured walls.

Freed K1 now runs a DISTINCT same-physics 16384-cell inner0.0005/first0.00003125-pc original20-pc **no-wind static** under28800-s guard in `/tmp/van_marle_wr_full_inner_f31_n20000_gmc2000_k1_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_f31_n20000_gmc2000_vm_k1_16384_20261018/manifest.csv`. Controlled base diff changes only radial stretch versus the validated K1 control; estimated native width at .06 pc falls from7.89e-5 to5.08e-5 pc. A roughly2x K1 static-runtime projection is below the23.04-ks 80%-guard ceiling. Pinned Linux binary/source/runner and exact input SHA, idle/46-GiB available RAM/110-GiB disk/empty output, initial VTU/one rank/empty stderr passed. **Do not restart or pre-launch wind.** Require guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW pull; only after host-measured >=20% margin may its staged .0015-Myr/seven-VTU wind run under28800 s. K2/K3 winds, K4 static and three Mac guards remain active; failed8192 inward farms/evidence untouched. Last touched: NEW K1 wind/plot/age-fixed trees, v20 inventory, generated f31 input set, README/root handoff/TODO; commands were remote guard/SHA/resource checks, rsync, validator, corrected plot/PNG inspection, inventory, generator/diff and guarded launch. Remaining: active guard completions and small-radius ramp-quality gap. No physics or Xcode change.

## Keohane3 GMC1000 bracket atmosphere gate and early wind (2026-10-18 22:10 UTC)

Keohane3 n_ref20000/GMC1000 original20-pc 16384-cell inner0.0005/first0.0000625-pc no-wind static finished guard0/one Finished AMRVAC/empty stderr/two VTUs in7689.699 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc1000_vm_k3_16384_20261018/Keohane3/n20000b1000/atmosphere/` passed independent exact .1-Myr age,247 initial H II elements, finite-GMC initial mass-pressure-density, finite-positive and stable outer fields. Do not repeat/re-pull; this is an atmosphere gate, not a shell measurement.

Matching DISTINCT .0015-Myr/seven-VTU wind now runs under28800-s guard in `/tmp/van_marle_wr_full_inner_bracket_n20000_gmc1000_k3_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_bracket_n20000_gmc1000_vm_k3_16384_20261018/manifest.csv`. K3's measured static runtime relative to the K1 matched bracket projects ~13.6 ks, below23.04-ks 80%-guard ceiling. Pinned Linux binary/source/runner and exact base/wind/manifest SHA, idle/46-GiB RAM available/111-GiB disk/empty wind output, initial VTU/one rank/empty stderr passed. **Do not restart.** Require guard0/one marker/empty stderr/seven VTUs/exact .0015 Myr/finite-GMC initial and stable outer/WR2000-km-s and1e-5-Msun-yr flux before NEW pull, corrected full and age-fixed full+zoom local 10/50/90-rise inspection, and inventory refresh. K1/K2 winds, K4 static and three Mac guards remain active; failed8192 inward farms/evidence untouched. Last touched: NEW validated K3 static tree, README/root handoff/TODO; commands were remote guard/SHA/rank/resource checks, rsync, finite-GMC validator and guarded wind launch. Remaining: active guard completions and small-radius quality gap. No physics, Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Keohane2 bracket atmosphere gate and early wind (2026-10-18 20:22 UTC)

Keohane2 n_ref20000/GMC2000 original20-pc 16384-cell inner0.00025/first0.0000625-pc no-wind static finished guard0/one Finished AMRVAC/empty stderr/two VTUs in10509.521 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc2000_vm_k2_16384_20261018/Keohane2/n20000b2000/atmosphere/` passed independent exact .1-Myr age,250 initial H II elements, finite-GMC initial mass-pressure-density, finite-positive and stable outer fields. Do not repeat/re-pull; the static is not a shell measurement.

Matching DISTINCT .0015-Myr/seven-VTU wind NOW RUNS under28800-s guard in `/tmp/van_marle_wr_full_inner_bracket_n20000_gmc2000_k2_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_bracket_n20000_gmc2000_vm_k2_16384_20261018/manifest.csv`. K2's measured static ratio10509.521/7691.535 against K1's projected13.6-ks bracket wind gives ~18.6 ks, below23.04-ks 80%-guard ceiling. Pinned Linux binary/source/runner and exact base/wind/manifest SHA, host idle/46-GiB available RAM/111-GiB disk/empty wind output, first VTU/one rank/empty stderr passed. **Do not restart.** Require guard0/one marker/empty stderr/seven VTUs/exact .0015 Myr/finite-GMC initial and stable outer/WR2000-km-s and1e-5-Msun-yr flux before NEW pull, corrected full and age-fixed full+zoom local 10/50/90-rise inspection, and inventory refresh. K1 wind, K3/K4 bracket statics and three Mac guards remain active; failed8192 inward farms/evidence remain untouched. Last touched: NEW validated K2 static tree, README/root handoff/TODO; commands were remote guard/SHA/rank/resource checks, rsync, finite-GMC validator and guarded wind launch. Remaining: active guard completions and small-radius quality gap. No physics, Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## K3/K4 32768 early profiles and GMC1000 bracket statics (2026-10-18 20:01 UTC)

Keohane3 n_ref20000/GMC2000 and Keohane4 n_ref20000/GMC1000 original20-pc 32768-cell .002-Myr winds finished guard0/one Finished AMRVAC/empty stderr/nine VTUs in26714.557/26648.181 s. NEW non-overwriting `results/dense_gmc_wr_full_outer_n20000_gmc2000_vm_32768_002myr_20261018/n20000b2000/wind/` and corresponding GMC1000 tree passed independent exact-age/finite-GMC initial mass-pressure-density/stable outer/2000.322-km-s WR speed/1.000215e-5-Msun-yr flux. Corrected full and age-fixed full+zoom profiles were visually inspected: endpoint R10=.071173/.071113 pc, FWHM9.80/9.17 native cells, contrast37.55/40.00, local 10-90% ramps3.97/3.89 cells. Numerical shell gates pass but neither local ramp is resolved; the full inward precursor is retained. Do not repeat/re-pull or claim convergence, physical shock width, GRB wall or fit.

NEW `results/dense_gmc_radius_coverage_20261017/v19_full_outer_vm32768_002_0p001to10/` combines both dated age-fixed roots:12/20 quality-gated bins,306 accepted snapshots,50 >=5-cell local ramps overall. The .0398-.0631-pc bin has18 accepted/seven cases/zero resolved ramps; all smaller bins are empty. Selected negative-k analytic fit radii are model-dependent, not measured walls.

Freed K3/K4 now run DISTINCT matched n_ref20000/GMC1000 original20-pc 16384-cell **no-wind statics** under21600-s guards in `/tmp/van_marle_wr_full_inner_bracket_n20000_gmc1000_k3_16384_20261018_farm/` and K4 counterpart. K3 inner.0005 pc, K4 inner.00025 pc, common first width.0000625 pc; exact manifests `dense_gmc_inputs_wr_full_inner_bracket_n20000_gmc1000_vm_k3_16384_20261018/manifest.csv` and corresponding K4 manifest. Each generated base differs from its K1/K2 GMC2000 bracket control only in `n_bg_cm3`; no physics support/cooling/conduction change. Pinned Linux binary/source/runner and transferred exact input SHA, idle/46-62-GiB available memory/111-GiB disk/empty output, initial VTU/one rank/empty stderr passed. **Do not restart or launch wind before static gate:** require guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW pull. Only after host-measured >=20% runtime margin may matching .0015-Myr/seven-VTU winds run under28800-s guards. K1 wind, K2 bracket static and Mac guards remain active; failed8192 inward farms/evidence untouched. Last touched: two NEW validated wind/plot/inner-edge trees, v19 inventory, two generated input sets, README/root handoff/TODO; commands were remote guard/SHA/resource checks, rsync, independent validators, corrected plots/PNG inspection, inventory, generator/diff and guarded static launches. Remaining: active guard completions and sub-.0398-pc quality gap; no physics, Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Keohane1 bracket atmosphere gate and early wind (2026-10-18 19:34 UTC)

Keohane1 n_ref20000/GMC2000 16384-cell original20-pc inner0.0005/first0.0000625-pc no-wind static completed guard0/one Finished AMRVAC/empty stderr/two VTUs in7691.535 s. NEW non-overwriting `results/dense_gmc_wr_full_inner_bracket_n20000_gmc2000_vm_k1_16384_20261018/Keohane1/n20000b2000/atmosphere/` passed independent exact .1-Myr age,247 initial H II elements, finite-GMC initial mass-pressure-density, finite-positive and stable outer fields. Do not repeat/re-pull; the static is not a shell measurement.

Matching DISTINCT .0015-Myr/seven-VTU wind NOW RUNS under28800-s guard in `/tmp/van_marle_wr_full_inner_bracket_n20000_gmc2000_k1_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_bracket_n20000_gmc2000_vm_k1_16384_20261018/manifest.csv`. Static ratio7691.535/2783.987 times duration-scaled validated full-domain16384 GMC2000 wind13086.763*(.0015/.004) projects about13.6 ks, below23.04-ks 80%-guard ceiling. Pinned Linux binary/source/runner and exact input SHA, idle/46-GiB available RAM/110-GiB disk/empty wind output, first VTU/one rank/empty stderr passed. **Do not restart.** Require guard0/one marker/empty stderr/seven VTUs/exact .0015 Myr/finite-GMC initial and stable outer/WR2000-km-s and1e-5-Msun-yr flux before NEW pull, corrected full and age-fixed full+zoom local 10/50/90-rise inspection, and inventory refresh. K2 bracket static, K3/K4 winds and Mac guards remain active; failed8192 inward farms/evidence remain untouched. Last touched: NEW validated static tree, README/root handoff/TODO; commands were remote guard/SHA/rank/resource checks, rsync, finite-GMC validator and guarded wind launch. Remaining: active guard completions and small-radius quality gap. No physics, Xcode, convergence, physical-width, GRB-wall or forced-fit change/claim. Older notes below are historical.

## Mac01 65536 static gate and early wind (2026-10-18 18:59 UTC)

Pauley404-01 n_ref20000/GMC2000 65536-cell inner.001/first.00003125/evolved outer2.5-pc no-wind atmosphere completed guard0/one Finished AMRVAC/empty stderr/two VTUs in19110.911 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_65536_001myr_20261018/Pauley404-01/n20000b2000/atmosphere/` passed independent exact .1-Myr age,494 initial H II elements, finite-GMC initial mass-pressure-density, finite-positive and stable outer fields using the20-pc pressure anchor. Do not repeat/re-pull; no shell measurement comes from this static.

Matching DISTINCT .001-Myr/nine-VTU wind NOW RUNS under36000-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_65536_001myr_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_mac_65536_001myr_20261018/manifest.csv`. Host-measured static ratio19110.911/4717.082 times the validated32768 .004-Myr wind duration-scaled22612.167/4 projects ~22900 s, under the28800-s 80%-guard ceiling. Shared pinned Lyra binary/source/runner and exact input SHA, idle/85%-free memory/719-GiB free disk/empty wind output, first VTU/one rank/empty stderr passed. **Do not restart.** Require guard0/one marker/empty stderr/nine VTUs/exact .001 Myr/finite-GMC initial and stable outer/WR2000-km-s and1e-5-Msun-yr flux with `--domain-max-pc 2.5 --atmosphere-outer-pc 20` before NEW non-overwriting pull, corrected full density and age-fixed full+zoom local 10/50/90-rise inspection, and inventory refresh. No convergence, physical shock-width, GRB-wall or forced-fit claim. Last touched: NEW validated static tree, README/root handoff/TODO; commands were remote guard/SHA/rank/resource checks, rsync, finite-GMC validator and guarded wind launch. Remaining: active guard completions and small-radius profile quality. Older notes below are historical.

## Mac02/03 finer inward statics (2026-10-18 18:08 UTC)

The Pauley404-02 n_ref20000/GMC1000 and Pauley404-03 n_ref20000/GMC2000 16384-cell inward/short-domain .0015-Myr winds have completed guard0/one marker/empty stderr/seven VTUs in10857.032/10874.582 s. NEW non-overwriting wind pulls under `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_16384_0015myr_20261018/` and the corresponding GMC2000 tree passed independent exact-age/finite-GMC initial/outer/2000-km-s WR speed/1e-5-Msun-yr flux checks with inner.0002/evolved outer2.5/pressure anchor20 pc. Corrected full and age-fixed full+zoom profiles were inspected in NEW plot and `results/dense_gmc_inner_edge_20261018/local_inner_outer_n20000b1000_mac16384_0015_agefix/` and corresponding GMC2000 diagnostics. First shell-gated snapshot .00075 Myr has R10=.041631/.041654 pc, FWHM5.68/6.00 native cells, local ramp2.85/3.08 cells. Endpoint R10=.062354/.062403 pc, FWHM12.04/12.82, contrast51.55/48.65, local ramp4.74/4.82 cells. No saved local ramp reaches the >=5-cell resolution criterion; do not infer convergence or physical shock width. Do not repeat/re-pull.

NEW `results/dense_gmc_radius_coverage_20261017/v18_inward_short_mac16384_0p001to10/` has12/20 quality-gated bins,298 accepted snapshots,50 >=5-cell local ramps overall. The .0398-.0631-pc bin has14 accepted/five cases/zero resolved ramps; all smaller bins empty. Selected negative-k analytic fit radii are not measured walls. Freed Mac02/03 now run DISTINCT same-physics 16384-cell **no-wind statics** with first native width halved to .0000125 pc, under43200-s guards in `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc1000_16384_f12_0015myr_20261018_mac_farm/` and corresponding GMC2000 farm. Exact manifests: `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_16384_f12_0015myr_20261018/manifest.csv` and corresponding GMC2000 manifest. Base diffs changed only stretch; shared pinned Lyra binary/source/Mac runner and exact input SHA, idle/resources/empty output/initial VTU/one rank/empty stderr passed. **Do not restart or launch wind before full static validation:** guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW non-overwriting pull. Their staged .0015-Myr/seven-VTU winds have guard36000; require measured host-specific >=20% margin first. Last touched: NEW wind/plot/age-fixed/v18 products and two generated input sets, README/root handoff/TODO; commands were remote guard/SHA/resource checks, rsync, validators, corrected plots, age-fixed PNG inspection, inventory, generator/controlled diff and guarded launches. Remaining: active guard gates and sub-.0398-pc quality gap; no physics or Xcode change. Older notes below are historical.

## K1/K2 inner-boundary bracket statics (2026-10-18 17:25 UTC)

Jonathan directed purposeful new work on the idle hosts. Keohane1 and Keohane2 now run DISTINCT n_ref20000/GMC2000, 16384-cell, original-20-pc no-wind statics under 21600-s guards. K1 uses inner0.0005 pc, K2 inner0.00025 pc; both use first native width0.0000625 pc. Exact manifests: `dense_gmc_inputs_wr_full_inner_bracket_n20000_gmc2000_vm_k1_16384_20261018/manifest.csv` and `dense_gmc_inputs_wr_full_inner_bracket_n20000_gmc2000_vm_k2_16384_20261018/manifest.csv`; remote farms: `/tmp/van_marle_wr_full_inner_bracket_n20000_gmc2000_k1_16384_20261018_farm/` and `/tmp/van_marle_wr_full_inner_bracket_n20000_gmc2000_k2_16384_20261018_farm/`. They vary inner boundary/derived stretch against a common pinned Linux binary and otherwise matched finite-GMC physics. Idle/resources, transferred-input checksums, empty output, initial VTU, one rank and empty stderr passed. **Do not restart, and do not disturb either failed 8192 inward static farm or its failure evidence.**

Require each static guard0/one Finished AMRVAC/empty stderr/two VTUs/exact0.1 Myr/H II>=10/finite-positive and finite-GMC initial mass-pressure-density/stable outer before NEW `rsync --ignore-existing` pull. Matching .0015-Myr/seven-VTU winds are staged only; launch conditionally after each host's measured >=20% margin under28800 s. Require exact wind age/WR2000-km-s and1e-5-Msun-yr flux/outer, then NEW corrected full and age-fixed full+zoom 10/50/90-rise profiles and inventory. Do not infer convergence, physical shock width or a GRB wall. Last touched: two generated input sets, manifests, README/root handoff/TODO; generator/diff/SSH/SHA/rsync preflights and guarded launches ran. Output: initial static VTUs only. Remaining: static gates, conditional winds and profile-quality gaps; no physics change.

## Mac02/03 16384 inward atmosphere gates and early winds (2026-10-18 14:56 UTC)

Pauley404-02 n_ref20000/GMC1000 and Pauley404-03 n_ref20000/GMC2000 inward/short-domain 16384-cell no-wind statics finished guard0/one Finished AMRVAC/empty stderr/two VTUs in13332.293/13331.468 s. NEW non-overwriting `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_16384_0015myr_20261018/Pauley404-02/n20000b1000/atmosphere/` and `results/dense_gmc_wr_local_inner_outer_n20000_gmc2000_mac_16384_0015myr_20261018/Pauley404-03/n20000b2000/atmosphere/` independently passed exact .1-Myr age,615 initial H II elements each, finite-GMC initial mass-pressure-density and stable outer fields with inner.0002/first.000025/evolved outer2.5/pressure anchor20 pc. Do not repeat/re-pull; these are atmosphere gates, not shell measurements.

Their DISTINCT matching .0015-Myr/seven-VTU winds now run under28800-s guards in the same respective farms, exact `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_16384_0015myr_20261018/manifest.csv` and `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc2000_mac_16384_0015myr_20261018/manifest.csv`. Host-measured static mesh ratios project ~11.0/11.4-ks winds from validated8192 same-physics .004-Myr cases after duration scaling, below the23.04-ks guard-margin ceiling. Shared pinned Lyra arm64 binary/source/Mac runner and exact input SHA, host idle/resources/empty wind output/initial VTU/one rank/empty stderr passed. **Do not restart.** Require guard0/one marker/empty stderr/seven VTUs/exact .0015 Myr/finite-GMC initial and outer/2000-km-s speed and1e-5-Msun-yr flux with `--domain-max-pc 2.5 --atmosphere-outer-pc 20`, then NEW non-overwriting pulls, corrected full and age-fixed inner-rise full+zoom PNG inspection, and 0.001-10-pc inventory refresh. Mac01 65536 static and K3/K4 32768 winds retain guards; K1/K2 idle pending Jonathan's direct retry decision. Last touched: two NEW validated static trees and README/root handoff/TODO; commands were guarded remote checks, rsync, independent validators and guarded wind launches. Remaining: active guards, small-radius shell/ramp quality and K1/K2 decision; no convergence, physical shock-width, GRB-wall, fit or physics/Xcode change.

## Mac01 32768 early profile and 65536 atmosphere gate (2026-10-18 13:40 UTC)

Pauley404-01 n_ref20000/GMC2000 32768-cell inner0.001/first0.0000625/outer2.5-pc 0.004-Myr wind completed guard0/one Finished AMRVAC/empty stderr/17 VTUs in22612.167 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_32768_20261018/Pauley404-01/n20000b2000/wind/` independently passed exact age, finite-GMC initial mass/pressure/density, stable outer with atmosphere-anchor20 pc, 2000.362-km/s speed and1.000222e-5-Msun-yr flux. Corrected `plot_wind_v1/` and age-fixed `results/dense_gmc_inner_edge_20261018/local_outer_control_n20000b2000_mac32768_agefix/` full+zoom profiles were inspected. At .0005 Myr R10=.032367 pc but FWHM3.24 cells fails the shell gate; first accepted .00125-Myr snapshot has R10=.054006 pc and local ramp2.87 cells. Endpoint R10=.108606 pc/FWHM26.51 cells/contrast25.58/ramp3.73 cells; matched16384 R10=.104678 pc differs3.75%. No convergence, physical shock-width, GRB-wall or forced-fit claim. Do not repeat/re-pull.

NEW `results/dense_gmc_radius_coverage_20261017/v17_outer_control_mac32768_0p001to10/` combines both dated age-fixed roots: 12/20 occupied quality-gated bins,290 accepted snapshots,50 resolved local ramps. The .0398-.0631-pc bin has six accepted/three cases/zero resolved ramps; all smaller bins remain empty. Freed Mac01 now runs DISTINCT same-physics 65536-cell short-domain **no-wind static** under28800-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_65536_001myr_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_mac_65536_001myr_20261018/manifest.csv`. Inner.001/first.00003125/outer2.5/atmosphere_outer20 pc; controlled base diff from32768 changes mesh/stretch and `max_blocks=16384` only. Shared Lyra binary/source/Mac runner/input SHA, idle/resources/empty output/first VTU/one rank/empty stderr passed. Measured fourfold mesh-runtime projection ~18868s is below80% of static guard. **Do not restart or launch matching wind before static gate:** require guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial/stable outer and NEW pull. Only after host-measured >=20% margin run conditional .001-Myr/nine-VTU wind under36000s and validate WR speed/flux/full+zoom rise. Mac02/03 statics and K3/K4 winds retain guards; K1/K2 idle awaiting direct retry decision. Last touched: NEW wind/plot/inner-edge/v17 products, generated65536 inputs, README/root handoff/TODO; commands were guard/SHA/resource checks, rsync, finite-GMC validator, corrected plotter, age-fixed rise/PNG inspection, inventory, generator/controlled diff and guarded static launch. Remaining: current guards, conditional wind, sub.0398-pc gap and K1/K2 decision.

## K3/K4 32768 atmosphere gates and early winds (2026-10-18 12:35 UTC)

Keohane3 n_ref20000/GMC2000 and Keohane4 n_ref20000/GMC1000 original20-pc 32768-cell no-wind atmospheres finished guard0/one Finished AMRVAC/empty stderr/two VTUs in 11316.064/11226.595 s. NEW non-overwriting `results/dense_gmc_wr_full_outer_n20000_gmc2000_vm_32768_002myr_20261018/n20000b2000/atmosphere/` and `results/dense_gmc_wr_full_outer_n20000_gmc1000_vm_32768_002myr_20261018/n20000b1000/atmosphere/` independently passed exact .1-Myr age, 244 initial H II elements each, finite-positive/finite-GMC initial mass-pressure-density and stable outer fields. Do not repeat/re-pull; these are atmosphere gates, not shell detections.

Matching DISTINCT .002-Myr/nine-VTU winds now run under36000-s guards in `/tmp/van_marle_wr_full_outer_n20000_gmc2000_32768_002myr_20261018_farm/` and `/tmp/van_marle_wr_full_outer_n20000_gmc1000_32768_002myr_20261018_farm/`, exact `dense_gmc_inputs_wr_full_outer_n20000_gmc2000_vm_32768_002myr_20261018/manifest.csv` and `dense_gmc_inputs_wr_full_outer_n20000_gmc1000_vm_32768_002myr_20261018/manifest.csv`. Static mesh-runtime ratios against validated 16384 cases project ~26.6-ks winds, below the 28.8-ks 80%-guard ceiling. Shared pinned Linux binary/source/runner/input SHA, host idle/resources/empty wind output and records, initial VTU/one rank/empty stderr passed. **Do not restart.** On completion require guard0/one marker/empty stderr/nine VTUs/exact .002 Myr/finite-GMC initial and outer/2000-km-s speed and1e-5-Msun-yr flux, NEW non-overwriting pull, corrected full profile and age-fixed inner-rise inspection, and inventory refresh. No convergence or physical shock-width claim.

Mac01 wind and Mac02/03 statics retain their guards. K1/K2 remain idle pending Jonathan's direct new-folder retry decision. Last touched: two NEW validated static result trees, README/root handoff/TODO. Commands: remote guard/SHA/resource checks, `rsync --ignore-existing`, independent validators and guarded wind launches. Remaining: wind/static gates, early-radius resolved profiles and K1/K2 decision; no physics or Xcode-licensing change.

## Inward short-domain winds and finer static gates (2026-10-18 11:12 UTC)

Pauley404-02 n_ref20000/GMC1000 and Pauley404-03 n_ref20000/GMC2000 8192-cell inner0.0002/first0.00005/evolved outer2.5-pc/atmosphere-anchor20-pc 0.004-Myr winds finished guard0/one Finished AMRVAC/empty stderr/17 VTUs. NEW non-overwriting `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_8192_20261018/Pauley404-02/n20000b1000/wind/` and `results/dense_gmc_wr_local_inner_outer_mac_8192_20261018/Pauley404-03/n20000b2000/wind/` independently passed exact-age/finite-GMC initial mass-pressure-density/stable outer/2000.82-km-s WR speed/1.000418e-5 and1.000417e-5-Msun-yr flux using `--domain-max-pc 2.5 --atmosphere-outer-pc 20`. Corrected plots and age-fixed `results/dense_gmc_inner_edge_20261018/local_inner_outer_n20000b1000_mac8192_agefix/` and `.../local_inner_outer_n20000b2000_mac8192_agefix/` full+zoom profiles were visually inspected. First numerical shell-gate pass is at0.00125 Myr/R10=0.054147/0.054180 pc, FWHM5.05/5.36 native cells, but local ramps only2.51/2.81 cells. At0.00325 Myr R10=0.095599/0.095636 pc, local ramps5.14/5.15 cells. Endpoint R10=0.108337/0.108352 pc, shell-inner n_H7.088e6/6.545e6 cm^-3, ramps4.05/3.90 cells. Pre-jump density is not cavity floor; local ramp is not physical shock thickness. Different GMC densities do not establish mesh convergence. Do not repeat/re-pull.

NEW `results/dense_gmc_radius_coverage_20261017/v16_inward_short_pair_0p001to10/` combines both dated age-fixed roots: 12/20 occupied quality-gated bins, 278 accepted snapshots,49 resolved local ramps. The 0.0398-0.0631-pc bin has four accepted snapshots from two cases but zero resolved ramps; the 0.0631-0.1-pc bin has38 accepted/six cases/four resolved ramps. All smaller bins remain empty. Selected negative-k GRB analytic radius intervals are model-dependent, not measured shell walls or a forced fit.

Freed Mac02/03 now run DISTINCT same-physics 16384-cell inward/short-domain **no-wind statics** under18000-s guards in `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc1000_16384_0015myr_20261018_mac_farm/` and `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc2000_16384_0015myr_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_16384_0015myr_20261018/manifest.csv` and `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc2000_mac_16384_0015myr_20261018/manifest.csv`. The bases differ from validated8192 only by mesh/stretch: inner0.0002/first0.000025/evolved outer2.5/pressure anchor20 pc. Shared pinned Lyra arm64 binary/source/Mac runner and exact new input SHA, host idle/CPU/memory/disk/empty output/initial VTU/one rank/empty stderr passed. **Do not restart or launch wind before static validation.** Each static requires guard0/one marker/empty stderr/two VTUs/exact0.1Myr/H II>=10/finite-GMC initial and stable outer with NEW `rsync --ignore-existing` pull. Only after a host-measured >=20% runtime guard margin may its matching 0.0015-Myr/seven-VTU wind run under28800 s; validate WR speed/flux/outer and NEW full+zoom profiles. Mac01 32768 short-domain wind and K3/K4 32768 original20-pc statics remain active; K1/K2 remain idle pending Jonathan's direct retry decision. No physics, Xcode licensing, convergence, physical shock-width, or GRB-wall change/claim.

Last touched: two NEW wind/plot/inner-edge trees, v16 inventory, two generated 16384 manifests/input sets, README/root handoff/TODO. Commands: remote guard/SHA/idle/resource checks, `rsync --ignore-existing`, independent validators, corrected plots and age-fixed rise/PNG inspection, generator/controlled base diff, guarded static launches, inventory. Remaining: active guard validation, conditional winds, K1/K2 retry decision, sub0.0398-pc quality gap.

## K3/K4 full-domain early profiles; 32768 static gates (2026-10-18 09:27 UTC)

Keohane3 n_ref20000/GMC2000 and Keohane4 n_ref20000/GMC1000 original-20-pc 16384-cell 0.004-Myr/17-VTU direct-WR winds finished guard0/one Finished AMRVAC/empty stderr in13086.763/13020.023 s. NEW non-overwriting `results/dense_gmc_wr_full_outer_n20000_gmc2000_vm_16384_20261018/n20000b2000/wind/` and `results/dense_gmc_wr_full_outer_n20000_gmc1000_vm_16384_20261018/n20000b1000/wind/` passed independent exact-age/finite-GMC initial mass-pressure-density/stable outer/2000.364-km-s/9.991332e-6 and9.991337e-6-Msun-yr-flux gates. Corrected `plot_wind_v1/` full profiles and NEW `results/dense_gmc_inner_edge_20261018/full_outer_n20000b2000_vm16384_agefix/` and `.../full_outer_n20000b1000_vm16384_agefix/` full+zoom profiles were visually inspected. At .004 Myr, R10=.104217/.104186 pc, FWHM12.28/11.39 native cells, contrast22.32/23.87, local 10-90% ramps4.50/4.28 cells, so shell gates pass but ramp resolution does not. K3 versus short-domain Mac01 matched16384 R10=.104678 pc differs0.44%; different evolved domain/stretch and unresolved ramps prohibit convergence or outer-boundary invariance claims. Do not repeat/re-pull.

Freed K3/K4 now run DISTINCT same-physics original20-pc 32768-cell no-wind statics under18000-s guards in `/tmp/van_marle_wr_full_outer_n20000_gmc2000_32768_002myr_20261018_farm/` and `/tmp/van_marle_wr_full_outer_n20000_gmc1000_32768_002myr_20261018_farm/`, exact NEW `dense_gmc_inputs_wr_full_outer_n20000_gmc2000_vm_32768_002myr_20261018/manifest.csv` and `dense_gmc_inputs_wr_full_outer_n20000_gmc1000_vm_32768_002myr_20261018/manifest.csv`. Inner.001/first.0000625/outer20 pc. Bases differ from validated16384 only by mesh/stretch and `max_blocks=8192`; pinned shared Linux binary/source/runner and exact inputs, idle/resources/empty output/first VTU/one rank/empty stderr passed. **Do not restart or launch wind before the static gate:** require guard0/one marker/empty stderr/two VTUs/exact.1Myr/H II>=10/finite-GMC initial and stable outer and NEW non-overwriting pull. Reassess host-measured >=20% margin before conditional matching .002-Myr/nine-VTU direct-WR wind under36000-s guard. This tests whether an early R10 near .058 pc can pass the native shell-width gate; it is not a promised result.

Keohane2 n_ref20000/GMC1000 original20-pc inward-boundary 8192 static also timed out under7200 s at about .09659 Myr: exit124, one initial VTU, zero Finished AMRVAC markers, empty stderr. Preserve its original `/tmp/van_marle_wr_full_inner_n20000_gmc1000_8192_20261018_farm/`; NEW failure evidence is separate at `results/failed_guards_20261018/Keohane2/n20000b1000_full_inner_7200_static/`. K1 and K2 are idle, both inward/full-domain statics unvalidated; no matching wind or automatic retry while Jonathan's identical-input new-folder10800-s retry decision is pending. NEW `results/dense_gmc_radius_coverage_20261017/v15_full_outer_pair_vm16384_0p001to10/` joins both dated age-fixed diagnostic roots: 11/20 bins, 254 accepted snapshots,43 resolved local ramps. Below.1 pc only .0631-.1-pc is occupied (22 snapshots/four cases/zero resolved ramps), smaller bins empty. Last touched: K2 failure evidence, K3/K4 NEW wind/plot/inner-edge trees, two generated pinned input sets, v15 inventory, README/root handoff/TODO. Commands: guard/SHA/resource checks, non-overwriting rsync, independent validators, corrected plotter/inner-rise/PNG inspection, inventory, controlled mesh diff and guarded launches. Remaining: Mac01/02/03 winds, K3/K4 static/conditional wind and K1/K2 decision; no physics change, physical shock-width, GRB-wall, convergence or fit claim.

## Mac02/03 inward short-domain statics validated; winds active (2026-10-18 05:00 EDT)

Pauley404-02 n_ref20000/GMC1000 and Pauley404-03 n_ref20000/GMC2000 8192-cell inward+short-domain no-wind statics finished guard0/one Finished AMRVAC/empty stderr/two VTUs in3391.825/3397.259s. NEW non-overwriting pulls under `results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_8192_20261018/Pauley404-02/n20000b1000/atmosphere/` and `results/dense_gmc_wr_local_inner_outer_mac_8192_20261018/Pauley404-03/n20000b2000/atmosphere/` independently passed exact .1-Myr age, 307 initial H II elements each, finite-GMC initial mass/pressure/density, finite-positive and stable outer fields, with inner.0002/first.00005/evolved outer2.5/pressure anchor20 pc. Do not repeat/re-pull.

Matching DISTINCT direct-WR .004-Myr/17-VTU winds now run on Mac02/03 under28800-s guards in `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc1000_8192_20261018_mac_farm/` and `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc2000_8192_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_8192_20261018/manifest.csv` and `dense_gmc_inputs_wr_local_inner_outer_mac_8192_20261018/manifest.csv`. Shared pinned Lyra arm64 binary/source/runner and exact input SHA, idle/resources/empty output, first VTU/one rank/empty stderr passed. Static-runtime scaling from the validated 8192 short-domain wind projects about16.3ks versus23.04ks 80%-guard ceiling. Require guard0/one marker/empty stderr/exact17 VTUs/.004Myr, finite-GMC initial and stable outer with `--domain-max-pc 2.5 --atmosphere-outer-pc 20`, WR speed and mass flux before NEW pulls and corrected full/zoom age-fixed inner-rise diagnostics. A mistyped first dispatch basename made only an inert `cloudmass_gmc_cloudmass_gmc_*_wind.dispatch.log` on each host and launched no AMRVAC; correct named jobs passed initial gates. Preserve these logs. K1 full-domain retry still requires Jonathan's decision; other guards continue. Last touched: NEW validated static trees and README/root handoff/TODO; commands were guard/SHA/resource checks, `rsync --ignore-existing`, independent static validation and guarded wind launches. Remaining: wind validation/profile and four other guards; no physics change, convergence or physical shock-width claim.

## K1 full-domain inward static guard failure (2026-10-18 08:15 UTC)

Keohane1 n_ref20000/GMC2000 8192-cell original20-pc inward-boundary no-wind static reached approximately .0963 Myr, then exited124 at its exact7200-s wall guard. There is one initial VTU, zero Finished AMRVAC markers and empty stderr: **not** a validated .1-Myr atmosphere. No matching wind or automatic retry. The remote `/tmp/van_marle_wr_full_inner_n20000_gmc2000_8192_20261018_farm/` remains intact. NEW non-overwriting run records and the initial VTU are preserved separately at `results/failed_guards_20261018/Keohane1/n20000b2000_full_inner_7200_static/`; do not use them as shell data. Jonathan was notified and asked whether an identical-input retry in a new folder with10800-s guard may run on affected K1/K2 hosts. K2's analogous static is still active; monitor its own guard, with no preemptive retry. Mac01/02/03 and K3/4 remain active. Last touched: failure evidence plus README/root handoff/TODO; commands were remote guard/marker/stderr/age/process checks and `rsync --ignore-existing`. Remaining: user decision and current guards; no physics change.

## Mac02/03 winds validated; paired inward short-domain statics active (2026-10-18 08:04 UTC)

Mac02 n_ref3000/GMC900 32768-cell .014-Myr/eight-VTU early wind finished guard0/one Finished AMRVAC/empty stderr in20164.451 s. NEW `results/dense_gmc_wr_early_n3000_gmc900_mac_32768_fixed_20261018/Pauley404-02/n03000b0900/wind/` passed independent exact-age/finite-GMC initial/outer/2000.272-km-s/1.000773e-5-Msun-yr flux checks. Corrected full-density and age-fixed full+zoom profiles were inspected: endpoint R10=.397441 pc, FWHM10.69 native cells, contrast75.31, local 10-90% ramp4.04 cells. Matched8192/16384 .014-Myr R10=.357827/.376072 pc; no convergence, resolved ramp or physical shock-width claim. Do not repeat/re-pull.

Mac03 n_ref1000/GMC50 8192-cell .27-Myr/15-VTU continuation finished guard0/one marker/empty stderr in25373.855 s. NEW `results/dense_gmc_wr_orthogonal_n1000_gmc50_mac_8192_027myr_20261017/Pauley404-03/n01000b0050/wind/` passed independent exact-age/finite-GMC initial/outer/2000.672-km-s/9.995214e-6-Msun-yr flux checks. Full+zoom inspected endpoint R10=8.529018 pc, FWHM8.10 cells, contrast132.75, local ramp3.59 cells; numerical shell gate passes, local ramp unresolved. Matched4096 R10=8.438229 pc but fails width gate. Do not repeat/re-pull or claim convergence.

Freed Mac03 now runs the previously staged n_ref20000/GMC2000 8192 inward/short-domain no-wind static under7200-s guard in `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc2000_8192_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_inner_outer_mac_8192_20261018/manifest.csv`. Freed Mac02 now runs a DISTINCT n_ref20000/GMC1000 8192 counterpart in `/private/tmp/van_marle_wr_local_inner_outer_n20000_gmc1000_8192_20261018_mac_farm/`, exact NEW `dense_gmc_inputs_wr_local_inner_outer_n20000_gmc1000_mac_8192_20261018/manifest.csv`. Both inner.0002/first.00005/outer2.5/atmosphere_outer20, with only GMC density different between bases. They use the SAME pinned Lyra arm64 binary/source/runner; previous guards, exact SHA, idle/resources/empty output, initial VTU/one rank/empty stderr passed. Do not restart or alter Xcode licensing. Require each static guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW non-overwriting pull; only then conditional matching .004-Myr/17-VTU wind after host-measured >=20% guard margin.

`inventory_shell_radius_coverage.py` now accepts repeatable `--additional-diagnostics` roots while preserving duplicate-snapshot rejection; four focused tests and `py_compile` passed. NEW `results/dense_gmc_radius_coverage_20261017/v13_mac02_32768_mac03_8192_0p001to10/` joins 20261017 and 20261018 age-fixed diagnostics without copying them: 11/20 occupied bins, 238 accepted snapshots, 43 >=5-cell local ramps. The .0631-.1-pc bin remains ten accepted/two cases/zero resolved ramps; smaller bins empty. Reproduce with `python inventory_shell_radius_coverage.py results/dense_gmc_inner_edge_20261017 results/dense_gmc_radius_coverage_20261017/NEW_DIR --additional-diagnostics results/dense_gmc_inner_edge_20261018 --min-radius-pc 0.001` using the root venv Python. Bin occupation is not a GRB wall or fit.

Last touched: NEW Mac02/03 wind, plot and inner-edge trees; Mac02 generated input set; inventory script/test/v13; README/root handoff/TODO. Commands: guard/marker/stderr/SHA/resource checks, `rsync --ignore-existing`, independent validators, corrected plots and inner-edge PNG inspection, generator/controlled diff, guarded static launches, focused tests and inventory. Remaining: seven guarded hosts, paired boundary/profile comparison and sub-.0631-pc quality gaps; K1 inward static is near its7200-s guard and must not auto-retry if it times out.

## Mac01 32768 short-domain atmosphere validated; matching wind guarded (2026-10-18 07:17 UTC)

Pauley404-01 n_ref20000/GMC2000 32768-cell inner.001/first.0000625/outer2.5-pc no-wind atmosphere finished guard0/one Finished AMRVAC/empty stderr/two VTUs in4717.082 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_32768_20261018/Pauley404-01/n20000b2000/atmosphere/` independently passed exact .1-Myr age, 247 initial H II cells, finite-positive/finite-GMC initial mass-pressure-density and stable outer with20-pc pressure anchor. Do not repeat/re-pull; this is not a wind shell.

Its matching .004-Myr/17-VTU direct-WR wind now runs under36000-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_32768_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_mac_32768_20261018/manifest.csv`. Measured static ratio4717.082/1192.122=3.96 against validated16384 projects ~22743-s wind from5748.974 s, under the80%-of-guard ceiling28800 s. Shared Lyra Mac binary/source/runner and exact base/wind/manifest SHA, idle/32-GiB RAM85% free/702-GiB disk/empty wind output/records and initial VTU/one rank/empty stderr passed. On completion require guard0/one marker/empty stderr/exact17 VTUs/.004 Myr/finite-GMC initial mass-pressure-density/stable outer with evolved2.5/atmosphere20, 2000-km-s and1e-5-Msun-yr flux. Pull only NEW, make corrected full density and age-fixed full+zoom inner-rise diagnostics, inspect inward precursor/local ramp and compare exact-age8192/16384; refresh inventory. Do not claim convergence or physical shock width.

Last touched: NEW validated Mac01 32768 static tree and README/root handoff/TODO. Commands: remote guard/marker/stderr/count/SHA/idle/resource checks, `rsync --ignore-existing`, independent static validator and guarded wind launch. Remaining: wind endpoint/profile and six other active host guards; no physics change.

## K2 GMC50 early profile validated; full-domain GMC1000 inward static guarded (2026-10-18 07:15 UTC)

Keohane2 n_ref1000/GMC50 16384-cell direct-WR .020-Myr wind finished guard0/one Finished AMRVAC/empty stderr/11 VTUs in16315.993 s. NEW non-overwriting `results/dense_gmc_wr_early_n1000_gmc50_vm_16384_20261018/n01000b0050/wind/` independently passed exact age, finite-GMC initial mass-pressure-density/stable outer, 2000.365-km-s wind and1.000429256e-5-Msun-yr flux. Corrected `results/dense_gmc_wr_early_n1000_gmc50_vm_16384_20261018/plot_wind_v1/` and age-fixed `results/dense_gmc_inner_edge_20261017/early_n01000b0050_vm16384_agefix/` full+zoom density profiles were visually inspected. At .020 Myr R10=.761824 pc, FWHM4.38 native cells, contrast186.25, post-jump n_H290928 cm^-3 and local 10-90% ramp2.45 cells. No saved age passes the FWHM>=5 shell-width gate or >=5-cell ramp gate. Matched 4096/8192 .020-Myr R10=.683124/.722580 pc; no convergence claim. NEW 0.001-10-pc `results/dense_gmc_radius_coverage_20261017/v12_gmc50_16384_0p001to10/` remains11/20 quality bins. Do not repeat/re-pull or count this as a quality shell.

Freed K2 now runs DISTINCT n_ref20000/GMC1000 8192-cell original20-pc-domain inward-boundary .1-Myr/two-VTU **no-wind static** under7200-s guard in `/tmp/van_marle_wr_full_inner_n20000_gmc1000_8192_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_n20000_gmc1000_vm_8192_20261018/manifest.csv`. Inner.0002/first.00005 pc isolates moving injection inward versus validated full-domain8192 GMC1000 inner.001; K1 separately tests GMC2000. Base changes only xprobmin/stretch, not physics. Common pinned Linux binary/source/runner and exact new input SHA, K2 idle/48-GiB memory/111-GiB disk/empty output/runtime projection and initial VTU/one rank/empty stderr passed. **Do not start wind before static validation:** require guard0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW non-overwriting pull. Then reassess K2-measured >=20% margin before conditional .004-Myr/17-VTU wind. Other six hosts remain guarded.

Last touched: NEW validated K2 wind/plot/inner-edge/inventory v12, generated full-inner GMC1000 inputs and README/root handoff/TODO. Commands: remote guard/marker/SHA/resource checks, `rsync --ignore-existing`, independent validator, corrected plotter/age-fixed inner-edge and PNG inspection, inventory, generator/controlled base diff, guarded static launch. Remaining: K2 static/conditional wind and six other guarded hosts, quality small-radius profile gap; no physics change.

## K1 GMC500 early profile validated; full-domain inward static guarded (2026-10-18 06:15 UTC)

Keohane1 n_ref10000/GMC500 8192-cell .020-Myr direct-WR wind finished guard0/one Finished AMRVAC/empty stderr/11 VTUs in16237.281 s. NEW non-overwriting `results/dense_gmc_wr_early_n10000_gmc500_vm_8192_20261018/n10000b0500/wind/` independently passed exact age, finite-GMC initial mass-pressure-density/stable outer, 2000.494-km/s wind and1.000510383e-5-Msun-yr flux. Corrected `results/dense_gmc_wr_early_n10000_gmc500_vm_8192_20261018/plot_wind_v1/` and age-fixed full+zoom `results/dense_gmc_inner_edge_20261017/early_n10000b0500_vm8192_agefix/` profiles were inspected. Endpoint R10=.349194 pc, FWHM17.86 native cells, contrast25.83, shell-inner n_H1.3035e6 cm^-3 and local ramp3.50 cells: shell gates pass, ramp remains unresolved. GMC1000/1500/3000 same-core/mesh/age R10=.348882/.348285/.345346 pc, with differing shell densities. NEW v11 0.001-10-pc inventory stays11/20 bins. Do not repeat/re-pull, fit radius, or claim convergence/physical shock width.

Freed K1 now runs a DISTINCT n_ref20000/GMC2000 8192-cell **original 20-pc domain** no-wind static under7200-s guard in `/tmp/van_marle_wr_full_inner_n20000_gmc2000_8192_20261018_farm/`, exact `dense_gmc_inputs_wr_full_inner_n20000_gmc2000_vm_8192_20261018/manifest.csv`. Inner boundary.0002 pc/first width.00005 pc tests inward injection at fixed outer20 pc against the validated full-domain8192 inner.001 case; it complements the Mac03 inward+short-outer pilot, still staged behind Mac03's separate active guard. The new base changes only inner boundary/stretch, not finite-GMC physics. Pinned common Linux binary/source/runner and exact input SHA, idle/resources/empty output/runtime projection and initial VTU/one rank/empty stderr passed. **Static first:** require guard0/one marker/empty stderr/two VTUs/exact.1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer, NEW non-overwriting pull; then reassess K1-measured >=20% margin before conditional .004-Myr/17-VTU wind. Other six hosts remain on their distinct guarded jobs.

Last touched: NEW validated K1 wind/plot/inner-edge/inventory v11 products, generated full-inner exact inputs and README/root handoff/TODO. Commands: guarded SSH/marker/SHA/resource checks, `rsync --ignore-existing`, independent validator, corrected plotter/age-fixed inner-edge and PNG inspection, inventory, generator/controlled base diff, guarded static launch. Remaining: static/conditional wind, other six host guards and smaller-radius resolved-ramp gap; no physics change.

## Mac01 16384 inner profile validated; 32768 short-domain static guarded (2026-10-18 05:54 UTC)

Mac01 n_ref20000/GMC2000 16384-cell inner0.001/first0.000125/outer2.5-pc direct-WR .004-Myr wind finished guard0/one Finished AMRVAC/empty stderr/17 VTUs in5748.974 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_16384_20261018/Pauley404-01/n20000b2000/wind/` independently passed exact age/finite-positive and finite-GMC initial mass-pressure-density/stable outer with `--domain-max-pc 2.5 --atmosphere-outer-pc 20`, 2000.363-km-s and9.991597e-6-Msun-yr mass flux. NEW corrected `results/dense_gmc_wr_local_outer_control_mac_16384_20261018/plot_wind_v1/` and age-fixed `results/dense_gmc_inner_edge_20261017/local_outer_control_n20000b2000_mac16384_agefix/` full/zoom density profiles were inspected: final R10=.104678 pc, FWHM13.99 native cells, contrast22.87, post-jump n_H6.732e6 cm^-3, local 10-90% ramp4.54 cells below the separate >=5-cell resolution gate. Matched8192 R10=.101010 pc differs3.63%; neither ramp nor radius is converged. Full inward precursor is retained; pre-jump density is not cavity floor, local ramp is not physical shock width. Do not repeat/re-pull.

Seven saved .002-.0035-Myr 16384 snapshots pass numerical shell gates at R10=.068805-.096498 pc, but their local ramps span only2.70-4.52 cells. NEW 0.001-10-pc `results/dense_gmc_radius_coverage_20261017/v10_outer_control_16384_0p001to10/` remains11/20 occupied bins; .0631-.1-pc has ten accepted snapshots from two mesh cases, zero resolved ramps; all smaller bins empty. No GRB wall, fit, shock thickness or convergence claim.

Freed Mac01 now runs the DISTINCT same-physics 32768-cell no-wind static under7200-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_32768_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_mac_32768_20261018/manifest.csv`. It keeps inner0.001/outer2.5/atmosphere pressure anchor20 pc and halves first width to0.0000625 pc; generated base differs from validated16384 only in domain_nx1/stretch and `max_blocks=8192` to permit 4096 eight-cell blocks. Its manifest records36000-s conditional wind guard. Shared Lyra binary SHA9b01f5e38b37c1436169b4b8f8d478058697f3db28e441bbeed6f70a7b529153, source SHA4b39192f46140b3419800bc65df0b71b0985dcc92ce250499bf0949e02e4383d, runner and exact input SHA matched non-overwriting transfer; Mac01 idle/32-GiB memory85% free/702-GiB disk/empty output, initial VTU/one rank/empty stderr passed. 4x measured16384 static runtime predicts4768 s <80% of7200; 4x wind predicts22996 s <80% of36000. **Do not launch wind before the full static gate:** require exit0/one marker/empty stderr/two VTUs/exact .1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW pull. Then reassess runtime/resource margin before matching .004-Myr/17-VTU wind, followed by exact WR-flux/outer validation and NEW full/zoom profiles. K3/K4 original20-pc winds and Mac02/Mac03/K1/K2 remain on distinct guards.

Last touched: NEW validated Mac01 16384 wind/plot/age-fixed inner-edge and v10 inventory, generated 32768 exact inputs and README/root handoff/TODO. Commands: guard/marker/stderr/count/SHA/resource checks, `rsync --ignore-existing`, independent validator, corrected plotter, inner-edge/PNG inspection, inventory, generator/controlled base diff and guarded static launch. Remaining: 32768 static/conditional wind and six other guarded winds, paired-profile comparison and fit-range gaps; no physics change.

## K3/K4 20-pc 16384 static gates passed; winds guarded (2026-10-18 05:47 UTC)

K3 n_ref20000/GMC2000 and K4 n_ref20000/GMC1000 original-20-pc 16384-cell no-wind atmospheres finished guard0/one Finished AMRVAC/empty stderr/two VTUs in2783.987/2747.395 s. NEW non-overwriting `results/dense_gmc_wr_full_outer_n20000_gmc2000_vm_16384_20261018/n20000b2000/atmosphere/` and `results/dense_gmc_wr_full_outer_n20000_gmc1000_vm_16384_20261018/n20000b1000/atmosphere/` independently passed exact .1-Myr age, 122 initial H II cells each, finite-positive/finite-GMC initial mass-pressure-density and stable outer fields. These are atmosphere gates, not shell detections. Do not repeat/re-pull.

Their matching distinct .004-Myr/17-VTU winds now run under28800-s guards in `/tmp/van_marle_wr_full_outer_n20000_gmc2000_16384_20261018_farm/` and `/tmp/van_marle_wr_full_outer_n20000_gmc1000_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_outer_n20000_gmc2000_vm_16384_20261018/manifest.csv` and `dense_gmc_inputs_wr_full_outer_n20000_gmc1000_vm_16384_20261018/manifest.csv`. Pinned common Linux binary/source/runner/input SHA, idle/48-64-GiB memory/111-GiB disk/empty wind output and host-measured >=20% runtime margin passed; initial VTU/one rank/empty stderr passed. Require exit0/one marker/empty stderr/exact17 VTUs/.004 Myr/finite-GMC initial and outer fields/2000-km-s and1e-5-Msun-yr flux, then NEW non-overwriting pulls, corrected plots and age-fixed full/zoom inner-edge diagnostics. Compare K3 with same-age Mac01 16384 short-domain and K4 with validated8192 GMC1000; no convergence, physical shock-width or GRB-wall claim. Mac01/Mac02/Mac03/K1/K2 remain on existing distinct guards.

Last touched: two NEW validated static trees and README/root handoff/TODO. Commands: remote guard/marker/stderr/count/SHA/resource checks, `rsync --ignore-existing`, independent finite-GMC static validators and guarded wind launches. Remaining: two matching winds and five other active guards, full-profile comparisons and log-radius inventory; no physics change.

## K3/K4 16384 early profiles validated; distinct 20-pc small-radius statics guarded (2026-10-18 04:58 UTC)

K3 n_ref5000/GMC125 and K4 n_ref5000/GMC1000 16384-cell .020-Myr/11-VTU winds finished guard0/one Finished AMRVAC/empty stderr in16553.820/16594.186 s. NEW non-overwriting `results/dense_gmc_wr_early_n5000_gmc125_vm_16384_20261017/n05000b0125/wind/` and `results/dense_gmc_wr_early_n5000_gmc1000_vm_16384_20261017/n05000b1000/wind/` independently passed exact-age/finite-positive/finite-GMC initial mass-pressure-density/stable outer/2000-km-s and1e-5-Msun-yr flux. NEW corrected plot and age-fixed `results/dense_gmc_inner_edge_20261018/early_n05000b0125_vm16384_agefix/` and `.../early_n05000b1000_vm16384_agefix/` full/zoom diagnostics were visually inspected. Endpoints R10=.415175/.417781 pc, FWHM5.11/11.01 native cells, contrast80.43/39.44, post-jump n_H1.665e6/8.007e5 cm^-3; both numerical shell gates pass. The local 10-90% ramps span only2.65/3.71 cells, against matched8192 R10=.393731/.396323 pc and ramps2.27/2.69 cells. The shallower inward precursor remains in the full profiles. No resolved ramp, physical shock width, or convergence claim; do not repeat/re-pull.

K3 now runs a DISTINCT n_ref20000/GMC2000 16384-cell **original 20-pc outer domain** no-wind static under7200-s guard in `/tmp/van_marle_wr_full_outer_n20000_gmc2000_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_outer_n20000_gmc2000_vm_16384_20261018/manifest.csv`. Inner0.001/first0.000125 pc matches Mac01's short-domain 16384 test; 20-pc evolved domain/stretch are the controlled difference. K4 independently runs n_ref20000/GMC1000 16384-cell original-domain static in `/tmp/van_marle_wr_full_outer_n20000_gmc1000_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_full_outer_n20000_gmc1000_vm_16384_20261018/manifest.csv`; its base differs from validated 8192 GMC1000 only by mesh/stretch. K3/K4 reuse the separately pinned common Linux binary SHA6220745f8bd78f536bcdeec7cda45762e1c032d3d20e383c8884044981350604, source SHAf77682de7f36cf94709c100a737d1142c56312b53a8fbb6ee2532dd740df0b35 and runner SHAdf2e62256431866eee2ae6cf663b5ff778b097edb918ccc8e05e8c4a16cc0f00, not the Lyra Mac build. Exact manifest/input SHA, idle/ample memory and disk/empty output, first VTU/one rank/empty stderr passed. Require each static guard0/one marker/empty stderr/exact two VTUs/0.1Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer and NEW non-overwriting pull; only then consider its matching .004-Myr/17-VTU wind under28800-s guard after a >=20% host-measured runtime margin. Original-domain profiles are needed to compare the short-domain Mac01 control, not to assert outer-boundary invariance from a single age. Mac01/Mac02/Mac03/K1/K2 guards remain active.

Last touched: NEW K3/K4 wind/plot/inner-edge trees, two generated manifests/input sets and README/root handoff/TODO. Commands: exact guarded SSH/marker/SHA/resource checks, `rsync --ignore-existing`, independent validator, corrected plotter, age-fixed inner-rise and PNG inspection, generator/controlled base diff, guarded static launches. Remaining: two statics/conditional winds, five other active guards and coverage inventory refresh; no physics change.

## Mac01 16384 atmosphere validated; matching wind guarded (2026-10-18 04:14 UTC)

Mac01's DISTINCT n_ref20000/GMC2000 16384-cell inner0.001/first0.000125/outer2.5-pc no-wind atmosphere finished guard0/one Finished AMRVAC/empty stderr/two VTUs in1192.122 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_16384_20261018/Pauley404-01/n20000b2000/atmosphere/` independently passed exact0.1-Myr age, 123 H II cells, finite-positive/finite-GMC initial mass-pressure-density and stable outer density/pressure using `--domain-max-pc 2.5 --atmosphere-outer-pc 20`. Shared Lyra binary/source and exact base/atmosphere SHA matched the pinned inputs. This is a static gate, not a shell result.

Its matching 0.004-Myr/17-VTU direct-WR wind now runs under28800-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_16384_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_mac_16384_20261018/manifest.csv`. Host-measured static mesh cost1192.122/310.741=3.84 times the validated8192 control, implying about5710 s from its1488.524-s wind; even a further3x penalty fits within80% of guard. Mac01 was idle with32-GiB RAM/702-GiB free disk; wind output/records empty, pinned binary/source/runner/base/wind SHA, initial wind VTU/one rank/empty stderr passed. On completion require guard0/one marker/empty stderr/17 VTUs/exact0.004 Myr/finite-GMC initial and stable outer fields/2000-km-s and1e-5-Msun-yr flux before NEW non-overwriting pull, corrected plot, age-fixed full/zoom inner-edge profiles, exact-age comparison with8192 and refreshed log-radius inventory. Do not equate more ramp cells with convergence or physical shock thickness. Mac03's inward pilot remains staged pending its separate GMC50 continuation.

Last touched: NEW validated 16384 static tree and README/root handoff/TODO; commands: guard/marker/stderr/count/SHA checks, `rsync --ignore-existing`, independent short-domain static validator, host runtime/resource/output checks and guarded wind launch. Remaining: wind quality/ramp, Mac03 prior guard/inward pilot and other active winds; no physics change.

## Mac01 outer-control wind validated; finer-mesh static guarded (2026-10-18 03:53 UTC)

The n_ref20000/GMC2000 8192-cell, inner0.001/outer2.5-pc control wind finished guard0/one Finished AMRVAC/empty stderr/17 VTUs in1488.524 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_8192_20261018/Pauley404-01/n20000b2000/wind/` independently passed exact0.004-Myr age, finite-positive and finite-GMC initial mass/pressure/density, stable outer fields with the 20-pc atmosphere pressure anchor, 2000.357-km/s wind and 1.000625e-5-Msun-yr flux. Corrected plot and age-fixed full/zoom inner-edge profiles were inspected in NEW `results/dense_gmc_inner_edge_20261018/local_outer_control_n20000b2000_mac8192_004myr_v1/`. The final R10 is0.101010 pc, FWHM6.96 native cells, contrast21.45, post-jump n_H6.532e6 cm^-3, but the local rise is only3.34 cells. At0.00325/0.0035/0.00375 Myr, quality-gated R10=0.088977/0.093080/0.097116 pc; none has a resolved >=5-cell local ramp. The full inward precursor is retained. The old 20-pc same-core/GMC 8192 case has R10=0.100515 pc at exactly0.004 Myr, a0.49% difference at this one age, not convergence or outer-boundary invariance.

NEW 0.001-10-pc inventory `results/dense_gmc_radius_coverage_20261017/v9_outer_control_0p001to10/` has11/20 occupied 0.2-dex bins. Only the0.0631-0.1-pc bin is newly occupied below0.1 pc: three accepted snapshots from this single case and zero resolved local ramps. Smaller bins remain empty. A DISTINCT 16384-cell resolution rung on free Mac01, same finite-GMC physics/inner0.001/outer2.5-pc geometry and0.004-Myr cadence with half first-cell width0.000125 pc, is now in guarded no-wind static under7200 s at `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_16384_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_mac_16384_20261018/manifest.csv`. The new base differs from the validated8192 control only in domain_nx1 and stretch ratio; base/runner/shared Lyra binary/source SHA matched after non-overwriting transfer, Mac01 idle/resources/output checks passed, and initial VTU/one rank/empty stderr passed. Require guard0/one marker/empty stderr/two VTUs/exact0.1 Myr/H II>=10/finite-GMC initial and stable outer validation plus NEW pull. Only then consider its matching guarded wind using host-measured >=20% runtime margin. Mac03 inward pilot remains staged, not launched, pending its prior active GMC50 continuation. No local-ramp, physical-shock-width, fit, GRB-wall or convergence claim.

Last touched: generated NEW 16384 input set, validated Mac01 wind/plots/inner-edge and v9 inventory, updated README/root handoff/TODO; commands: guard/marker/stderr/VTU checks, non-overwriting rsync, independent validator, corrected plotter and inner-edge measurement, PNG inspection, inventory, input diff/SHA/resources and guarded 16384 static launch. Remaining: static/conditional wind validation, Mac03 prior guard and inward pilot, and five other active winds.

## Mac01 outer-control static validated, wind active (2026-10-18 03:23 UTC)

The Mac01 n_ref20000/GMC2000 8192-cell outer-control static finished guard0/one marker/empty stderr/two VTUs in310.741 s. NEW non-overwriting `results/dense_gmc_wr_local_outer_control_mac_8192_20261018/Pauley404-01/n20000b2000/atmosphere/` independently passed exact0.1-Myr age, 61 initial H II elements, finite-positive fields, finite-GMC initial mass/pressure/density and stable outer density/pressure using `--domain-max-pc 2.5 --atmosphere-outer-pc 20`. It is not a swept-shell detection.

The distinct matching 0.004-Myr/17-VTU wind is now active under28800-s guard in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_8192_20261018_mac_farm/`, exact `dense_gmc_inputs_wr_local_outer_control_mac_8192_20261018/manifest.csv`. Same-core/GMC/inner/first-width Mac03 8192 wind on the old20-pc domain took7479.647 s for0.02 Myr, duration-scaled to~1496 s; even a 4x penalty stays below80% of the new guard. Mac01/Mac03 comparable statics took310.741/311.591 s. Shared Lyra binary/source/runner/input SHA, idle/empty wind output/resources and initial wind VTU/one rank/empty stderr passed. At completion require exit0/one marker/empty stderr/17 VTUs/exact0.004 Myr/finite-GMC initial and outer fields/2000-km-s/1e-5-Msun-yr flux before NEW plot/inner-rise/inventory products. No wind shell result yet. Mac03's inward pilot remains staged while its separate GMC50 continuation runs.

Last touched: NEW validated Mac01 static tree and README/root handoff/TODO. Commands: guarded log/exit/VTU checks, non-overwriting rsync, independent short-domain/static validator, pinned SHA/host resources/runtime projection and guarded wind launch. Remaining: wind endpoint and inner-rise quality, Mac03 prior guard/inward pilot and other active winds; no physics/other host change.

## Mac01 outer-control static running (2026-10-18 03:17 UTC)

Mac01's prior n_ref1000/GMC100 8192-cell 0.27-Myr wind finished guard0/one marker/empty stderr/15 VTUs, was pulled only to NEW `results/dense_gmc_wr_orthogonal_n1000_low_mac_8192_027myr_20261017/Pauley404-01/n01000b0100/wind/`, and independently passed exact age, finite-GMC initial mass/pressure/density, stable outer fields, 2000.645-km/s wind and 9.995214e-6-Msun-yr flux. NEW corrected plot and `results/dense_gmc_inner_edge_20261017/final_n01000b0100_mac8192_027myr_agefix_v1/` full/zoom profile were inspected. Endpoint R10=7.499922 pc, FWHM21.16 native cells, contrast52.90 and local rise8.84 cells; numerical shell and local-ramp gates pass. Matched 4096 R10=7.432725 pc/ramp4.71 cells does not establish convergence. Do not repeat or re-pull.

After Mac01 idle/memory/disk/empty-output checks, exact manifest and shared Lyra binary/source/runner/input SHA matches, its DISTINCT 8192-cell n_ref20000/GMC2000 outer-control **no-wind atmosphere** started in `/private/tmp/van_marle_wr_local_outer_control_n20000_gmc2000_8192_20261018_mac_farm/` under a 7200-s guard. Exact input is `dense_gmc_inputs_wr_local_outer_control_mac_8192_20261018/manifest.csv`; one rank, initial VTU and empty stderr were verified. A prior Mac03 static with identical n_ref/GMC/inner/first width at 20-pc outer took311.591 s, but the new short-domain host runtime remains to be measured. Require exit0/one marker/empty stderr/two VTUs/exact0.1 Myr/H II>=10/finite-GMC initial mass-pressure-density/stable outer with `--domain-max-pc 2.5 --atmosphere-outer-pc 20`, then NEW non-overwriting pull and Mac01-measured >=20% wind guard margin before any matching 0.004-Myr/17-VTU wind. Mac03's inward pilot is still staged and unlaunched; its prior GMC50 continuation and other distinct host winds are active. No physics/other job was changed.

Last touched: NEW Mac01 wind/plot/inner-edge products and README/root handoff/TODO; commands: guarded exit/log/SHA/VTU/resource checks, `rsync --ignore-existing`, independent validator, corrected plotter, inner-edge diagnostic/PNG inspection, shared-binary transfer/hash/dependency check and guarded static launch. Remaining: full Mac01 static gate/conditional wind, Mac03 prior guard and inward pilot, other active winds, coverage inventory refresh.

## Lyra shared Mac build and smoke (2026-10-18 03:06 UTC)

The opt-in local-boundary source now has one pinned arm64 Mac build on Lyra, preserved with SHA and build provenance in `builds/local_boundary_lyra_arm64_20261018/BUILD.md`. This **same compiled binary** is for Mac01 and Mac03; verify its SHA after transfer rather than rebuilding separately. Keohane1-4 use their separate common Linux binary. The two 2048-cell Lyra smoke geometries (outer-only control and inward/short-outer variant) each completed a guarded 10-year static and wind with exit0, one marker, empty stderr and two VTUs. Independent finite-GMC validation passed exact smoke age, positive fields, initial mass/pressure/density, stable outer fields, initial H II 59/242 cells, ~2000-km/s wind and ~1e-5-Msun/yr flux. Smoke inputs/results remain in `/private/tmp/van_marle_local_boundary_20261018_lyra/`; they are not quality-gated swept shells or a production runtime estimate.

At 03:06 UTC the two 8192-cell pilots below were staged and unlaunched; the newer Mac01 note above supersedes that status. Mac03 remains staged. Require the full static and >=20% host-measured wind-runtime gates stated below; do not substitute the 10-year smokes. No other active Mac or Keohane job was altered.

Last touched: preserved one Lyra-built arm64 executable/source and build provenance, generated two NEW 2048-cell smoke input sets and four guarded outputs, validated both static/wind pairs, updated README/root handoff/TODO and heartbeat. Commands: pinned AMRVAC `setup.pl -d=1`, serial `nice make -j1`, generator twice, guarded serial smokes, SHA/exit/log/stderr/VTU checks and four independent finite-GMC validator calls. Outputs: `builds/local_boundary_lyra_arm64_20261018/` and Lyra smoke trees; remaining uncertainty is 8192-cell host/static/runtime and inner-rise quality, not build initialization.

## Controlled inner/outer boundary pilot (2026-10-18 02:56 UTC)

Jonathan authorized moving both computational boundaries inward to resolve smaller radii. Two NEW n_ref=20000/GMC2000, 8192-cell, direct-WR cases have exact manifests in `dense_gmc_inputs_wr_local_outer_control_mac_8192_20261018/manifest.csv` (Mac01 static now running; no wind yet) and `dense_gmc_inputs_wr_local_inner_outer_mac_8192_20261018/manifest.csv` (Mac03 staged, unlaunched). Both end at 2.5 pc but retain the original 20-pc hydrostatic pressure reference through the opt-in `atmosphere_outer_pc=20` source/namelist setting; the computational inner limits are 0.001 and 0.0002 pc, respectively. The control retains the old 0.00025-pc first cell; the inward variant uses 0.00005 pc. Both require a 0.1-Myr/two-VTU no-wind static and, only after that passes, a 0.004-Myr/17-VTU wind at 0.00025-Myr cadence. This pair separates the short outer domain from the closer/finer injection boundary; the already validated 20-pc 8192-cell case is the third comparison. These short-domain simulations do not evolve the GMC edge at 15 pc, though their initial interior density, gravity, and pressure retain the finite-GMC model.

At the selected negative-`k` fit minimum 0.001225 pc, the old geometry has 0.90 cells from its inner boundary and the inward geometry has 20.43; at 0.1 pc their local cell widths are approximately 0.000255 and 0.0000859 pc. Predicted initial ionized front for the inward case is 0.01647 pc. Python atmosphere tables anchored at 20 pc differ in pressure by about 1.3e-6 relative at 0.001 pc due to the added inner mass/integration grid, and far less outward. Naively anchoring pressure at the new 2.5-pc outer edge instead would lower initial pressure at 0.1 pc by about 9.6%. These were input/analytic staging checks, not shell detections. `mod_usr_cloud_mass.t` now accepts the opt-in pressure-reference radius; old runs default to their computational outer boundary. `validate_cloud_mass.py`, the plotter, inner-edge diagnostic and inventory read exact manifest geometry; on short domains the shell search starts four first-cell widths beyond the inner boundary. The generator now permits bounded 0.001-0.27-Myr WR inputs and rejects impossible short-domain/first-width combinations or a short domain without an explicit pressure reference. Twelve focused tests and `py_compile` passed.

For each 8192-cell pilot host, validate its prior guard, use the pinned Lyra-built shared Mac binary above, hash-match binary/source/runner/inputs, and check idle/output/disk/memory. Do not alter Mac03 Xcode licensing. Require the host's static guard0/one marker/empty stderr/two VTUs/exact 0.1 Myr/H II>=10/finite-GMC initial mass-pressure-density/outer stability and pull into a NEW tree before its matching wind; check >=20% host-measured wind guard margin. For wind use `validate_cloud_mass.py --finite-gmc --edge-width-pc 0.5 --domain-max-pc 2.5 --atmosphere-outer-pc 20 --expected-mdot-msun-yr 1e-5` with each manifest's inner/n_bg, then NEW full/zoom inner-edge profile and log-radius inventory. Keep the full inward precursor, local ramp and shell-density quality flags. Do not claim convergence, physical shock thickness or a GRB wall from sub-0.1-pc raw rises. At the 02:56 staging milestone no 8192-cell job was launched; the newer Mac01 note above records its current static.

At 02:56 UTC: source, generator, validator, plotter, inner-edge diagnostic, inventory, focused tests, two NEW input trees, this README/root handoff/TODO and heartbeat. Commands: generator for both cases, controlled base diff, mesh/atmosphere numeric checks, `unittest`, `py_compile`, read-only Mac01/Mac03 process/disk checks. Outputs then: staged manifests/namelists only. The pinned Fortran build and Lyra smokes are now complete as documented above; remaining: guarded 8192 statics, conditional guarded winds, independent validation and full-profile comparison.

## Fit-driven small-radius priority (2026-10-18 02:41 UTC)

The source-linked 11 selected negative-`k` GRB fits in `Share_Folder/Reports/Bubble_Model_Comparisons/2026_10_15_negative_k_observed_radius_ranges_v1/` sample approximate minimized first-to-last blast-wave radii across 0.001225-0.719437 pc; eight end below 0.1 pc. The broader 15-fit table in `2026_10_15_GRB_powerlaw_radius_ranges_v2/` includes a positive-`k` case reaching 14.81 pc; that tail does not set the small-radius bubble priority. These are model-dependent analytic on-axis estimates, not measured walls or native off-axis trajectories. Thus the next free-host priority is resolved full density profiles at **smaller** inner-rise radii, especially 0.03-0.1 pc, not further 6-10-pc coverage. Preserve the already-running distinct jobs and their validation obligations.

`inventory_shell_radius_coverage.py --min-radius-pc 0.001` writes the NEW 0.001-10-pc, 0.2-dex inventory to `results/dense_gmc_radius_coverage_20261017/v8_fit_window_0p001to10/`; its original 0.1-pc default is unchanged. Of 187 numerically quality-gated saved snapshots, the smallest inner R10 is 0.100428 pc: zero pass below 0.1 pc, although 11 measured raw rises occur there and fail shell quality; none has a resolved >=5-cell local ramp. The 0.1-0.15849-pc bin has eight passing snapshots/four cases, zero resolved ramps. Bin occupation is not convergence.

The existing `n_ref=20000` early manifests use a 0.001-pc inner boundary and 0.00025-pc first cell; the running Mac02 `n_ref=3000/GMC900` 32768 case instead uses 0.01 pc. The fitted 0.001225-pc endpoint lies within the dense-case first cell and cannot be treated as an independently resolved shell. The earlier 16384-cell/0.006-0.008-Myr proposal is superseded by the controlled inward/short-domain pilot above. Validate the active Mac02 32768 wind and K3/K4 16384 early winds without disturbing them. Resolve the 0.03-0.1-pc range first, then assess 0.01-0.03 pc feasibility; do not claim 0.001-0.01-pc wall coverage without completed injection-boundary/resolution evidence or silently change physics.

Last touched: inventory script/test, this README, root handoff/TODO; commands: source-linked fit/report/manifest checks, focused unittest and NEW 0.01-10/v7 plus 0.001-10/v8 inventory generations. Outputs: new bin/snapshot CSVs; no AMRVAC case launched or physics changed. Remaining: finish seven active guards, validate all new outputs, then choose distinct small-radius mesh tests under host-specific runtime gates.

## K2 GMC50 16384 static passed, early wind running (2026-10-18 02:36 UTC)

Keohane2 n_ref1000/GMC50 16384-cell no-wind atmosphere finished guard0/one Finished AMRVAC/empty stderr/two VTUs in 206.758 s. NEW non-overwriting `results/dense_gmc_wr_early_n1000_gmc50_vm_16384_20261018/n01000b0050/atmosphere/` independently passed exact .1 Myr, 257 initial H II elements, finite-GMC initial mass/pressure/density and stable outer fields. Distinct .020-Myr/11-VTU early direct-WR wind now runs under 28800-s guard in `/tmp/van_marle_wr_early_n1000_gmc50_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_early_n1000_gmc50_vm_16384_20261018/manifest.csv`, after pinned SHA/idle/empty wind output/resources/initial VTU/one rank/empty-stderr checks. Validate age/WR flux/outer and inspect full density/inner ramp at .020 Myr against matched 4096 GMC50 short. No convergence or physical shock-width claim.

Current age-fixed inventory v6 has eight quality-gated snapshots from four cases in the 0.1-0.15849-pc inner-radius bin, only two within 0.09-0.11 pc; none has a >=5-cell resolved local ramp. Mostly n_ref20000 early snapshots. The running K2 wind is not yet in that inventory.

Last touched: NEW validated K2 static tree and README/root handoff/TODO; commands: guard/marker/VTU/SSH/SHA/resources, `rsync --ignore-existing`, independent atmosphere validator and guarded wind launch. Remaining: wind and other active guards.

## K2 GMC50 upper-radius continuation and early mesh (2026-10-18 02:24 UTC)

Keohane2 n_ref1000/GMC50 4096-cell .27-Myr direct-WR continuation finished guard0/one Finished AMRVAC/empty stderr/15 VTUs in 13555.348 s. NEW non-overwriting `results/dense_gmc_wr_orthogonal_n1000_gmc50_027myr_vm_4096_20261017/n01000b0050/wind/` passed independent exact age, finite-GMC initial mass/pressure/density, outer stability, 2000-km/s and 9.99046e-6-Msun-yr flux. Corrected plot and age-fixed full/zoom inner-rise profile inspected. Endpoint R10=8.438229 pc, shell-inner n_H5879 cm^-3, FWHM4.49 native cells, contrast117.59 and local ramp2.53 cells; fails shell-width and ramp gates. Only .096429-Myr/R10=3.142079-pc snapshot of 14 noninitial snapshots passes numerical shell gates; none has resolved ramp. Do not count the 8.44-pc endpoint as quality radius or physical shock thickness. NEW `results/dense_gmc_radius_coverage_20261017/v6/` counts 187 quality-gated snapshots/all ten bins, 35 resolved ramps.

Freed K2 now runs distinct n_ref1000/GMC50 16384-cell no-wind static under 7200-s guard in `/tmp/van_marle_wr_early_n1000_gmc50_16384_20261018_farm/`, exact `dense_gmc_inputs_wr_early_n1000_gmc50_vm_16384_20261018/manifest.csv`. Its base differs from validated 4096 GMC50 only in mesh and stretch; initial VTU/one rank/empty stderr, pinned Linux SHA, idle/empty output and resources passed. Require guard0/one marker/two VTUs/exact .1 Myr/H II>=10/mass-pressure/outer validation and NEW pull before matching .020-Myr/11-VTU wind; compare that with existing 4096 .020-Myr snapshot. Projected ~16086-s wind fits 28800-s guard. No convergence or physics change.

Last touched: NEW K2 wind/plots/inner-edge/inventory v6 and generated 16384 inputs, README/root handoff/TODO; commands: guard/SSH/SHA/resources, non-overwriting rsync, independent validator, corrected plotter/inner-edge/PNG inspection, generator/mesh diff, guarded static launch. Remaining: new static/conditional wind and six other active guards.

## Mac02 32768 static repaired, wind running (2026-10-18 02:17 UTC)

Jonathan authorized diagnosis of the held n_ref3000/GMC900 32768-cell .014-Myr early case. The original static exited128 with no output; a separately preserved `max_blocks=8192` test reached first DAT but failed at converter `mod_convert_files.f:897`: its atmosphere VTU name was 81 characters, beyond the pinned 80-character `filename` buffer. NEW `dense_gmc_inputs_wr_early_n3000_gmc900_mac_32768_fixed_20261018/manifest.csv` retains identical mesh/physics/ages/cadence, adds only `max_blocks=8192` for 4096 blocks, and shortens the case basename. Static finished guard0/one Finished AMRVAC/empty stderr/two VTUs in 530.315 s in `/private/tmp/van_marle_wr_early_n3000_gmc900_32768_fixed_20261018_mac_farm/`. NEW non-overwriting `results/dense_gmc_wr_early_n3000_gmc900_mac_32768_fixed_20261018/Pauley404-02/n03000b0900/atmosphere/` independently passed exact .1 Myr/199 H II/finite-GMC initial mass-pressure-density/outer. Matched .014-Myr/eight-VTU wind now runs under 28800-s guard after pinned SHA/idle/empty output/resources/initial VTU/one-rank checks. On completion validate WR flux/outer/exact age before NEW full and inner-edge profiles. `generate_dense_gmc_scan.py` now rejects >80-character VTU names before staging; focused rejection/short-name tests passed. Do not re-run failed farms, change physics, or claim convergence.

Last touched: generator/NEW input set/README/root handoff/TODO; commands: remote source and guard investigation, SHA/idle/resource checks, controlled base diff, `rsync --ignore-existing`, guarded static/wind launches, independent atmosphere validator, generator tests and `py_compile`. Products: NEW validated static tree and active wind. Remaining: wind endpoint/inner-profile validation.

## GMC500 static validated, early wind running (2026-10-18 01:39 UTC)

Keohane1 n_ref10000/GMC500 8192-cell no-wind atmosphere finished guard0/one Finished AMRVAC/empty stderr/two VTUs. NEW non-overwriting `results/dense_gmc_wr_early_n10000_gmc500_vm_8192_20261018/n10000b0500/atmosphere/` independently passed exact .1 Myr, 98 initial H II elements, finite-GMC initial mass/pressure and stable outer fields. Matching distinct .020-Myr/11-VTU direct-WR wind now runs under 28800-s guard in `/tmp/van_marle_wr_early_n10000_gmc500_8192_20261018_farm/`, exact `dense_gmc_inputs_wr_early_n10000_gmc500_vm_8192_20261018/manifest.csv`. Pinned Linux binary/source/runner/new input SHA, idle/empty wind output/disk/memory and initial VTU/one rank/empty-stderr gates passed. Require wind guard0/one marker/empty stderr/11 VTUs/exact .020 Myr/WR flux/outer fields before NEW plots and inner-edge profiles. Compare full radial density and shell density with GMC1000/1500/3000 at fixed n_ref/mesh; no radius fit, resolved-shock or late-WR claim.

Last touched: NEW validated static tree and README/root handoff/TODO; commands: guarded SSH/SHA/resource checks, `rsync --ignore-existing`, independent atmosphere validator and guarded wind launch. Remaining: wind and five other active guards plus Mac02 32768 mesh decision; no physics/full-run change.

## n10000 GMC1000 early validation and GMC500 bracket (2026-10-18 01:25 UTC)

Keohane1 n_ref10000/GMC1000 8192-cell .020-Myr/11-VTU direct-WR wind finished guard0/one Finished AMRVAC/empty stderr in 16211.112 s. NEW non-overwriting `results/dense_gmc_wr_early_n10000_gmc1000_vm_8192_20261017/n10000b1000/wind/` independently passed exact age, finite-GMC initial mass/pressure, outer stability, 2000-km/s and 1.00051e-5-Msun-yr flux. NEW corrected plots and `results/dense_gmc_inner_edge_20261017/early_n10000b1000_vm8192_agefix/` full/zoom profile inspected. At .020 Myr inner R10=.348882 pc, shell-inner n_H1.09434e6 cm^-3, FWHM20.85 native cells, contrast22.25 and local ramp3.22 cells. Seven ages .008-.020 Myr pass numerical shell gates, none has >=5-cell local ramp. Do not re-pull/repeat or treat the ramp as physical shock width. NEW `results/dense_gmc_radius_coverage_20261017/v5/`: 186 quality-gated snapshots in all ten 0.2-dex bins, 35 with resolved local ramps.

Freed K1 now runs a distinct n_ref10000/GMC500 8192-cell no-wind atmosphere under 7200-s guard in `/tmp/van_marle_wr_early_n10000_gmc500_8192_20261018_farm/`, exact host-corrected `dense_gmc_inputs_wr_early_n10000_gmc500_vm_8192_20261018/manifest.csv`. The new base differs from validated GMC1000 only in finite-GMC density, with core/mesh/support/gravity/cooling-off/conduction-off fixed. Pinned Linux binary/source/runner/input SHA, idle/empty output/disk/memory, initial VTU/one rank/empty-stderr checks passed. Require guard0/one marker/two VTUs/exact .1 Myr/H II>=10/initial mass-pressure/outer validation and NEW pull before matching .020-Myr/11-VTU high-cadence wind. Then compare full radial density, R10, shell-inner n_H and local ramp with GMC1000/1500/3000 at fixed core/mesh; do not force a radius law or claim convergence.

Last touched: generated host-corrected GMC500 inputs, NEW validated GMC1000 wind/plots/inner-edge/inventory v5 and README/root handoff/TODO; commands: guarded SSH/SHA/resource checks, non-overwriting rsync, finite-GMC validator, corrected plotter/inner-edge/visual inspection, generator/controlled diff, guarded static launch and inventory. Remaining: static then conditional GMC500 wind, five other guards and Mac02 held 32768 mesh decision; no physics/full-run change.

## GMC50 8192 short validation and age continuation (2026-10-18 00:54 UTC)

Pauley404-03 n_ref1000/GMC50 8192-cell .1-Myr/six-VTU direct-WR wind finished guard0/one Finished AMRVAC/empty stderr in 9395.473 s. NEW non-overwriting `results/dense_gmc_wr_orthogonal_n1000_gmc50_mac_8192_20261017/Pauley404-03/n01000b0050/wind/` passed independent exact age, finite-GMC initial mass/pressure, outer stability, 2000-km/s wind and 9.99521e-6-Msun-yr flux. NEW corrected plots and `results/dense_gmc_inner_edge_20261017/orth_n01000b0050_mac8192_agefix/` full/zoom profile inspected. At .1 Myr inner R10=3.442603 pc versus matched 4096 3.282278 pc (4.9% shift); shell-inner n_H15171 versus10426 cm^-3, FWHM6.38 versus5.08 native cells, local ramps2.95 versus2.86 cells. Numerical shell gates pass, but neither steep jump is resolved or converged. Do not repeat or re-pull.

Freed Mac03 now runs a distinct matched 8192-cell .27-Myr/15-VTU wind-only continuation under 36000-s guard in `/private/tmp/van_marle_wr_orthogonal_n1000_gmc50_8192_027myr_20261017_mac_farm/`, exact `dense_gmc_inputs_wr_orthogonal_n1000_gmc50_mac_8192_027myr_20261017/manifest.csv`. Base is byte-identical to validated short; pinned binary/source/runner/new input SHA, idle/empty output/disk/memory and initial VTU/one rank/empty-stderr gates passed. Measured short runtime x2.7 projects25368 s. On completion require guard0/one marker/empty stderr/15 VTUs/exact .27 Myr/finite-GMC initial/outer/WR flux, then NEW full density/inner-edge/quality comparison with K2 4096 GMC50 continuation. NEW `results/dense_gmc_radius_coverage_20261017/v4/` includes this short: 179 quality-gated snapshots across ten bins, only 35 with >=5-cell local ramps. Mac02 32768 static remains held after exit128. No physical shock-width, late-WR wall or fitted radius-law claim.

Last touched: generated continuation inputs, NEW non-overwriting wind/plots/inner-edge/inventory v4 products and README/root handoff/TODO; commands: SSH guard/SHA/resource checks, `rsync --ignore-existing`, finite-GMC validator, plotter/inner-edge diagnostic/PNG inspection, generator/base `cmp`, guarded launch and inventory. Remaining: this and five other guarded jobs, Mac02 mesh decision; no physics/full-run change.

## n5000 GMC1000 early profile and 16384 paired mesh (2026-10-18 00:19 UTC)

Keohane4 n_ref5000/GMC1000 8192-cell .020-Myr/11-VTU direct-WR wind finished guard0/one Finished AMRVAC/empty stderr in 4102.688 s. NEW non-overwriting `results/dense_gmc_wr_early_n5000_gmc1000_vm_8192_20261017/n05000b1000/wind/` independently passed exact age, finite-GMC initial mass/pressure, stable outer fields, 2000-km/s and 9.99531e-6-Msun-yr flux. NEW corrected and age-fixed full/zoom profiles inspected: at .020 Myr R10=.396323 pc, shell-inner n_H=807280 cm^-3, FWHM5.35 native cells, contrast36.66, local ramp2.69 cells. Only the final saved snapshot passes numerical shell gates; the rise remains underresolved. Matched K3 GMC125 8192 at .020 Myr has R10=.393731 pc and shell-inner n_H=1.2216e6, but fails FWHM floor. Similar inner radii do not imply similar shell-density profiles or convergence. NEW inventory `results/dense_gmc_radius_coverage_20261017/v3/` includes both n5000 cases: 177 quality-gated snapshots across ten bins, still only 35 with resolved local ramps.

Freed K4 now runs a distinct matched n_ref5000/GMC1000 16384-cell rung, exact host-corrected `dense_gmc_inputs_wr_early_n5000_gmc1000_vm_16384_20261017/manifest.csv`, farm `/tmp/van_marle_wr_early_n5000_gmc1000_16384_20261017_farm/`. Base differs only in mesh/stretch. Its 7200-s guarded no-wind static finished0/one marker/empty stderr/two VTUs, NEW non-overwriting pull to `results/dense_gmc_wr_early_n5000_gmc1000_vm_16384_20261017/n05000b1000/atmosphere/` independently passed exact .1 Myr/64 initial H II/mass-pressure/outer. Matching .020-Myr/11-VTU WR wind advances under 28800-s guard after pinned Linux SHA, idle/output/resources and initial VTU/one rank/empty-stderr checks; 8192 runtime x4 projects 16411 s. Compare full density, R10, shell density, native FWHM and local ramp with both 8192 GMC1000 and K3's independent GMC125 16384 case. No fitted law/physical shock width/late-WR claim.

Last touched: new generated/host-corrected 16384 inputs and README/root handoff/TODO; commands included controlled mesh diff, remote SHA/resource/guard checks, `rsync --ignore-existing`, independent static/wind validators, corrected plotter/inner-edge diagnostic and PNG inspection, guarded static/wind launches. Products: NEW validated 8192 wind/plots/inner and 16384 static trees, new wind active. Remaining: paired winds, other guards and held Mac02 32768 decision; no AMRVAC physics/full-run change.

## n5000 GMC125 early width gate and 16384 mesh (2026-10-18 00:08 UTC)

Keohane3 n_ref5000/GMC125 8192-cell .020-Myr/11-VTU direct-WR wind finished guard0/one Finished AMRVAC/empty stderr in 4119.839 s. NEW non-overwriting `results/dense_gmc_wr_early_n5000_gmc125_vm_8192_20261017/n05000b0125/wind/` independently passed exact age, finite-GMC initial mass/pressure, stable outer fields, 2000-km/s and 9.99524e-6-Msun-yr flux. NEW corrected plot and age-fixed full/zoom profile were inspected. At .020 Myr inner R10=.393731 pc, post-jump n_H=1.2216e6 cm^-3, FWHM3.46 native cells, local ramp2.27 cells. None of its early saved snapshots passes the >=5-cell shell-width gate, despite high density contrast; do not count these radii in the quality-gated coverage inventory or infer physical shock thickness.

Freed K3 now runs a DISTINCT matched n_ref5000/GMC125 16384-cell resolution rung, exact host-corrected `dense_gmc_inputs_wr_early_n5000_gmc125_vm_16384_20261017/manifest.csv`, farm `/tmp/van_marle_wr_early_n5000_gmc125_16384_20261017_farm/`. Base differs from 8192 only in mesh/stretch. Its guarded no-wind atmosphere finished0/one marker/empty stderr/two VTUs, was pulled NEW non-overwriting to `results/dense_gmc_wr_early_n5000_gmc125_vm_16384_20261017/n05000b0125/atmosphere/`, and independently passed exact .1 Myr/64 initial H II/initial mass-pressure/outer gates. Matching .020-Myr/11-VTU WR wind is active under 28800-s guard after pinned Linux binary/source/runner/input SHA, idle/empty-output/resources and initial VTU/one rank/empty-stderr checks. Projected 8192 runtime x4 is 16480 s, below 80% of the guard. Validate endpoint/flux/full profile and compare native width/ramp/R10 with 8192 before counting new radius snapshots or claiming convergence.

Last touched: new generated/host-corrected 16384 inputs and README/root handoff/TODO; commands included controlled mesh diff, remote pinned SHA/resources/guard checks, `rsync --ignore-existing`, independent static/wind validators, corrected plotter/inner-edge diagnostic and PNG inspection, guarded static/wind launches. Products: NEW validated 8192 wind/plot/inner and 16384 static trees; mesh wind active. Remaining: wind quality, other active guards and held Mac02 32768 decision; no AMRVAC physics/full-run change.

## GMC900 16384 early mesh and held 32768 gate (2026-10-17 23:50 UTC)

Pauley404-02 n_ref3000/GMC900 16384-cell .020-Myr/11-VTU direct-WR wind finished guard0/one Finished AMRVAC/empty stderr in 7314.934 s. NEW non-overwriting `results/dense_gmc_wr_early_n3000_gmc900_mac_16384_20261017/Pauley404-02/n03000b0900/wind/` passed independent exact-age, finite-GMC initial mass/pressure, outer stability, 2000-km/s and 1.00043e-5-Msun-yr flux checks. NEW corrected plot and age-fixed full/zoom density profiles were inspected. At .020 Myr inner R10=.496702 pc versus matched 8192 .469540 pc (5.8% shift), shell-inner n_H=473557 versus 480996 cm^-3, FWHM10.61 versus5.18 native cells, and local ramp3.74 versus2.65 native cells. The rise remains underresolved; no convergence or physical shock-width claim. Preserve the broad inward precursor. Do not rerun/re-pull this successful wind. NEW `results/dense_gmc_radius_coverage_20261017/v2/` includes this validated case: 176 quality-gated snapshots across all ten bins, still only 35 with resolved ramps.

A distinct 32768-cell .014-Myr comparison was generated in `dense_gmc_inputs_wr_early_n3000_gmc900_mac_32768_014myr_20261017/manifest.csv`; `generate_dense_gmc_scan.py` now permits this bounded early duration. The base differs from 16384 only by mesh/stretch, and the wind differs only by duration/output count and case name. Pinned Mac binary/source/runner and new input SHA, idle/empty-output/32-GB-memory/disk gates passed in `/private/tmp/van_marle_wr_early_n3000_gmc900_32768_014myr_20261017_mac_farm/`. Its guarded no-wind atmosphere exited **128 immediately**, with empty stdout/stderr, zero VTUs, no Finished AMRVAC marker and no crash report found. Cause is unconfirmed. Do not launch its wind, retry the failed static, or change block layout/solver build without a new decision; Mac02 is held after this failed gate.

Last touched: generator duration bound, new 32768 inputs and README/root handoff/TODO. Commands included `py_compile`, generator/controlled diff, remote pinned SHA/resource/guard checks, non-overwriting rsync, independent wind validator, corrected plotter, inner-edge diagnostic/PNG inspection and guarded static launch. Products: NEW validated 16384 wind/plots/inner tree; failed 32768 static records remain only in remote scratch. Remaining: diagnose/decide mesh ceiling, six other active guards, radius/profile convergence; no cooling/conduction/gravity/support/full-run change.

## Inner-radius log coverage inventory (2026-10-17 23:21 UTC)

`inventory_shell_radius_coverage.py` joins exact manifest core/GMC densities and base-file mesh size to age-corrected `measure_shell_inner_edge.py` per-snapshot CSVs. It counts only measured inner R10 radii with the existing H II/FWHM/contrast/width-ratio shell-quality flag, reports the separate >=5-cell local ramp resolution flag, and fails on duplicate diagnostic snapshots or conflicting manifests. Run with `/Users/jkeohane/GRBs/.venv/bin/python inventory_shell_radius_coverage.py results/dense_gmc_inner_edge_20261017 NEW_OUTPUT_DIR`; use a new output directory each time. Focused `python -m unittest test_inventory_shell_radius_coverage.py` passed.

NEW `results/dense_gmc_radius_coverage_20261017/v1/snapshot_inventory.csv` and `log_radius_bins.csv` inventory 25 age-fixed validated wind cases. All ten 0.2-dex bins from 0.1 to 10 pc contain a numerically quality-gated inner-rise snapshot (172 total), but only 35 have >=5-cell local ramps. Below 1.585 pc, no accepted snapshot has a resolved steep ramp. The 6.31-10-pc bin has four snapshots from two cases, one with a resolved ramp, and its closest representative is R10=7.432725 pc. This is radius-bin occupation, not even sampling in shell density or a converged physical profile law; no validated 10-pc wall is implied. Preserve each full precursor/profile and continue targeted mesh/density tests before parameterization.

Last touched: inventory script/test and README/root handoff/TODO; commands: focused unit test, NEW inventory generation and CSV/bin-count inspection. Outputs: NEW v1 snapshot/bin CSVs. Remaining: seven active guards and mesh/ramp/shell-density checks; no AMRVAC physics/full-run change.

## n5000 GMC1000 static and early wind (2026-10-17 23:04 UTC)

Keohane4 n_ref5000/GMC1000 8192-cell no-wind atmosphere finished guard0/one Finished AMRVAC/empty stderr/two VTUs. NEW non-overwriting `results/dense_gmc_wr_early_n5000_gmc1000_vm_8192_20261017/n05000b1000/atmosphere/` independently passed exact .1 Myr, 32 initial H II native elements, finite-GMC initial mass/pressure and stable outer fields. Matching distinct .02-Myr/11-VTU direct-WR wind now runs under 28800-s guard in `/tmp/van_marle_wr_early_n5000_gmc1000_8192_20261017_farm/`, exact `dense_gmc_inputs_wr_early_n5000_gmc1000_vm_8192_20261017/manifest.csv`; pinned Linux SHA/idle/empty-output/resources and initial VTU/one rank/empty-stderr checks passed. Require exact age/WR flux/outer and full inner-rise/shell density quality before comparing with K3 GMC125 at fixed core density/mesh.

Last touched: README/root handoff/TODO; commands included remote guard/marker/VTU/idle/SHA/resource checks, `rsync --ignore-existing`, independent atmosphere validator and guarded launch. Product: NEW validated static tree and active wind. Remaining: wind and six other guarded hosts; no physics/full-run change.

## n10000 early 8192 density profiles and n5000 next bracket (2026-10-17 23:02 UTC)

Keohane3/4 n_ref10000/GMC1500 and GMC3000 8192-cell .02-Myr/11-VTU early direct-WR winds finished guard0/one Finished AMRVAC/empty stderr. NEW non-overwriting `results/dense_gmc_wr_early_n10000_transition_vm_8192_20261017/<tag>/wind/` trees independently passed exact-age finite-GMC initial-mass-pressure/outer/2000-km-s/~1.00051e-5-Msun-yr-flux checks with 98 initial H II cells. NEW corrected plots and age-fixed full/zoom profiles inspected. At .020 Myr GMC1500 R10 .348285 pc, post-jump n_H900811 cm^-3, FWHM25.53 cells, contrast18.33, local ramp3.33 cells; GMC3000 R10 .345346 pc, post-jump n_H475894, FWHM49.14, contrast9.92, ramp2.99. Numerical shell gates first pass at .008/.006 Myr. Matched 4096 .020-Myr R10 .337752/.334970 differs ~3.1%; the steep rise remains underresolved, and a broad-topped density enhancement is not a physical thin-wall measurement. Runtimes16469.319/16694.052 s; no rerun/re-pull.

Freed K3 now runs a distinct n_ref5000/GMC125 8192-cell .02-Myr/11-VTU high-cadence wind in `/tmp/van_marle_wr_early_n5000_gmc125_8192_20261017_farm/`, exact host-corrected `dense_gmc_inputs_wr_early_n5000_gmc125_vm_8192_20261017/manifest.csv`. Its base is byte-identical to the validated 8192 static/short. Freed K4 runs a distinct n_ref5000/GMC1000 8192-cell no-wind static in `/tmp/van_marle_wr_early_n5000_gmc1000_8192_20261017_farm/`, exact host-corrected `dense_gmc_inputs_wr_early_n5000_gmc1000_vm_8192_20261017/manifest.csv`; base differs from validated 4096 only in mesh/stretch. Both launched after pinned Linux SHA, idle/empty-output/resources and initial VTU/one rank/empty-stderr checks. K4 needs guard0/one marker/two VTUs/exact .1Myr/H II>=10/initial mass-pressure/outer validation and NEW pull before its matching .02-Myr/11-VTU wind. Together these test early middle-radius profiles at fixed core density and mesh but distinct GMC densities; do not force a fit.

Last touched: generated two input sets/host-corrected manifests, README/root handoff/TODO; commands included guarded SSH/SHA/resource checks, non-overwriting rsync, independent validator, corrected plotter/age-fixed diagnostics/PNG inspection, generator/base `cmp` or mesh diff and guarded launches. Products: NEW validated K3/K4 early winds/plots/inner and two active distinct n5000 tests. Remaining: K4 static/conditional wind and five other guards; no physics/full-run change.

## GMC50 short profile and upper-radius continuation (2026-10-17 22:36 UTC)

Keohane2 n_ref1000/GMC50 4096-cell .1-Myr/six-VTU direct-WR wind finished guard0/one Finished AMRVAC/empty stderr. NEW non-overwriting `results/dense_gmc_wr_orthogonal_n1000_gmc50_vm_4096_20261017/n01000b0050/wind/` independently passed exact-age finite-GMC initial-mass-pressure/outer/2000-km-s/9.9904555e-6-Msun-yr-flux gates. NEW corrected plot and age-fixed full/zoom profile inspected: at .1 Myr R10 3.282278 pc, FWHM5.08 native cells, contrast206.88, post-jump n_H10426 cm^-3 and local steep ramp2.86 cells unresolved; four earlier saved ages fail the FWHM floor. Runtime5027.537 s. No physical shock-thickness/convergence or preconditioned late-WR claim; do not repeat/re-pull.

The distinct byte-base-identical 4096-cell .27-Myr/15-VTU continuation is now active on freed K2 in `/tmp/van_marle_wr_orthogonal_n1000_gmc50_027myr_20261017_farm/`, exact `dense_gmc_inputs_wr_orthogonal_n1000_gmc50_027myr_vm_4096_20261017/manifest.csv`. Short runtime x2.7 is below 80% of 36000-s guard. Pinned Linux binary/source/runner/input SHA, idle/empty-output/disk/memory and initial VTU/one rank/empty-stderr gates passed. Require exact endpoint, WR flux, outer stability and shell/ramp quality before counting an upper log-radius bin. Mac03 matched 8192 GMC50 short still runs independently.

Last touched: generated continuation inputs, README/root handoff/TODO; commands included independent validator, corrected plotter, age-fixed inner diagnostic/PNG inspection, generator/base `cmp`, guarded SSH/SHA/resource checks, `rsync --ignore-existing` and guarded launch. Products: NEW validated K2 short wind/plots/inner and active continuation. Remaining: endpoint/matched mesh and five other guarded jobs; no physics/full-run change.

## GMC2000 early mesh and GMC50 upper mesh (2026-10-17 22:11 UTC)

Pauley404-03 n_ref20000/GMC2000 8192-cell 0.02-Myr/11-VTU early direct-WR wind finished guard0/one Finished AMRVAC/empty stderr. NEW non-overwriting `results/dense_gmc_wr_early_n20000_gmc2000_mac_8192_20261017/Pauley404-03/n20000b2000/wind/` independently passed exact-age finite-GMC initial-mass-pressure/outer/2000-km-s/1.00051e-5-Msun-yr-flux gates. Corrected plot and age-fixed full/zoom density profile inspected. Numerical shell gates first pass at .004 Myr, R10 .100515 pc. At .020 Myr R10 .276616 pc, FWHM50.59 native cells, contrast7.98, post-jump n_H976835 cm^-3. Matched 4096 R10 .269841 and post-jump n_H970088 differ ~2.5% and ~0.7%, but the local ramp spans only2.83 versus2.94 cells. Narrowing physical width with mesh suggests a numerically sharp rise; neither physical shock thickness nor convergence is established. Runtime7479.647 s; do not repeat/re-pull.

For the upper-radius resolution bracket, new explicit `--orthogonal-wr-mac-n1000-upper` generator option stages n_ref1000/GMC50 on Mac03. Exact `dense_gmc_inputs_wr_orthogonal_n1000_gmc50_mac_8192_20261017/manifest.csv`; base differs from K2 4096 GMC50 only in mesh size/stretch. Guarded no-wind atmosphere finished0/one marker/empty stderr/two VTUs; NEW `results/dense_gmc_wr_orthogonal_n1000_gmc50_mac_8192_20261017/Pauley404-03/n01000b0050/atmosphere/` independently passed exact .1 Myr/128 initial H II/mass-pressure/outer. Matching .1-Myr/six-VTU direct-WR wind now runs in `/private/tmp/van_marle_wr_orthogonal_n1000_gmc50_8192_20261017_mac_farm/` under 28800-s guard after pinned SHA/idle/empty-output/32-GB-memory/disk and initial VTU/rank/empty-stderr gates. Compare full density/inner rise/shell density against K2 4096 GMC50 when both finish; .27 extension conditional on quality/runtime.

Last touched: generator option/new 8192 Mac inputs, README/root handoff/TODO; commands included guarded SSH/SHA/resource checks, generator `py_compile`/mesh diff, `rsync --ignore-existing`, independent validator, corrected plotter/inner diagnostic/PNG inspection and guarded static/wind launches. Products: NEW validated early 8192 wind/plots/inner and GMC50 static trees; GMC50 wind active. Remaining: validate it and six other guards; no cooling/conduction/gravity/support/full-run change.

## GMC900 early profile and 16384 resolution rung (2026-10-17 21:41 UTC)

Pauley404-02 n_ref3000/GMC900 8192-cell 0.02-Myr/11-VTU direct-WR wind finished guard 0/one Finished AMRVAC/empty stderr. NEW non-overwriting `results/dense_gmc_wr_early_n3000_gmc900_mac_8192_20261017/Pauley404-02/n03000b0900/wind/` independently passed finite-GMC exact-age/initial-mass-pressure/outer/2000-km-s/9.99533e-6-Msun-yr-flux gates. Corrected plot and age-fixed full/zoom density profile inspected. At .020 Myr R10=0.469540 pc, peak0.473525 pc, FWHM5.18 native cells, contrast46.81, post-jump n_H480996 cm^-3. Numerical shell gates pass only at this saved age; local 10-90% steep ramp2.65 cells is unresolved, and the shallower inward precursor remains visible. Runtime1883.821 s; do not re-pull/rerun.

To test the unresolved ramp without changing physics, a distinct matched 16384-cell case was generated in `dense_gmc_inputs_wr_early_n3000_gmc900_mac_16384_20261017/manifest.csv`. Its base differs from 8192 only in cell count and corresponding stretch ratio. The guarded no-wind static finished 0/one marker/empty stderr/two VTUs and NEW `results/dense_gmc_wr_early_n3000_gmc900_mac_16384_20261017/Pauley404-02/n03000b0900/atmosphere/` independently passed exact .1 Myr/99 initial H II/mass-pressure/outer. Matching .02-Myr/11-VTU wind now runs under 28800-s guard in `/private/tmp/van_marle_wr_early_n3000_gmc900_16384_20261017_mac_farm/` after pinned SHA/idle/empty-output/32-GB-memory/disk and initial VTU/rank/empty-stderr checks. Compare exact-age inner R10, full precursor, shell/jump density and ramp; do not infer physical shock thickness or convergence from width alone.

Last touched: generated 16384 inputs and updated README/root handoff/TODO; commands included SSH/SHA/resource/guard checks, mesh diff, `rsync --ignore-existing`, independent validator, corrected plotter and age-fixed inner diagnostic/PNG inspection, guarded static/wind launches. Products: NEW validated 8192 early wind/plot/inner tree and 16384 atmosphere tree; mesh wind in flight. Remaining: wind and other host validation; no gravity/support/cooling/conduction change.

## GMC50 static gate and matched wind (2026-10-17 21:14 UTC)

Keohane2 n_ref1000/GMC50 4096-cell no-wind atmosphere finished guard 0/one Finished AMRVAC/empty stderr/two VTUs. NEW non-overwriting `results/dense_gmc_wr_orthogonal_n1000_gmc50_vm_4096_20261017/n01000b0050/atmosphere/` independently passed exact 0.1 Myr, 64 initial H II elements, finite-GMC initial mass/pressure and stable outer fields. Matching distinct 0.1-Myr/six-VTU direct-WR wind now runs under 28800-s guard in `/tmp/van_marle_wr_orthogonal_n1000_gmc50_20261017_farm/`, exact `dense_gmc_inputs_wr_orthogonal_n1000_gmc50_vm_4096_20261017/manifest.csv`. Pinned binary/source/runner/base/wind SHA, idle/empty-output/disk/memory and initial VTU/rank/empty-stderr gates passed. Its full inner rise, shell density and numerical quality must be validated before any 0.27-Myr continuation; no upper-radius or thin-wall outcome is assumed.

Last touched: README/root handoff/TODO; commands included guarded SSH/SHA/resource checks, `rsync --ignore-existing`, finite-GMC validator, generator `py_compile`/help and guarded wind launch. Product: NEW validated GMC50 static tree; wind active. Remaining: wind gates, six other hosts and upper-radius coverage; no physics change or convergence claim.

## Upper radius and GMC900 age-mesh profiles (2026-10-17 21:09 UTC)

Keohane2 n_ref1000/GMC100 4096-cell .27-Myr direct-WR wind finished guard 0/one marker/empty stderr/15 VTUs. NEW non-overwriting `results/dense_gmc_wr_orthogonal_n1000_low_027myr_vm_4096_20261017/n01000b0100/wind/` independently passed exact age, finite-GMC initial mass-pressure, outer stability, 2000-km/s and 9.99046e-6-Msun-yr WR flux. Corrected plot and age-fixed inner profile: R10 7.432725 pc, local ramp4.71 native cells, peak7.469038 pc, FWHM10.74 cells, contrast50.35, post-jump n_H5035 cm^-3. Shell numerical gates pass but ramp is underresolved; no late-WR/GRB-wall claim. Runtime13680.080 s; do not repeat/re-pull.

Pauley404-02 n_ref3000/GMC900 8192-cell .27-Myr wind finished guard 0/one marker/empty stderr/15 VTUs. NEW non-overwriting `results/dense_gmc_wr_orthogonal_n3000_gmc900_mac_8192_027myr_20261017/Pauley404-02/n03000b0900/wind/` passed the same gates, including 9.99521e-6-Msun-yr flux. R10 4.368544 pc, ramp14.15 cells, peak5.151203 pc, FWHM386.76 cells, contrast3.22, post-jump n_H2051 cm^-3. NEW revalidation/age-fixed inner diagnostic for completed 4096 age profile: R10 4.283702 pc, ramp6.62 cells (~1.98% R10 difference). Full 8192 profile has broad precursor/plateau; two-mesh agreement alone does not establish convergence or a thin wall. Runtime25204.117 s; do not repeat/re-pull.

Freed Mac02 now runs a DISTINCT base-byte-identical n_ref3000/GMC900 8192-cell 0.02-Myr/11-VTU high-cadence wind under 28800-s guard in `/private/tmp/van_marle_wr_early_n3000_gmc900_8192_20261017_mac_farm/`, exact `dense_gmc_inputs_wr_early_n3000_gmc900_mac_8192_20261017/manifest.csv`. Pinned binary/source/runner/input SHA, idle/output/resources and initial VTU/rank/empty stderr passed; inspect per-snapshot inner rises/shell gates.

Freed K2 now runs a DISTINCT n_ref1000/GMC50 4096-cell no-wind atmosphere under 7200-s guard in `/tmp/van_marle_wr_orthogonal_n1000_gmc50_20261017_farm/`, exact `dense_gmc_inputs_wr_orthogonal_n1000_gmc50_vm_4096_20261017/manifest.csv`. Explicit `generate_dense_gmc_scan.py --orthogonal-wr-vm-n1000-upper` option changes only n_bg 100 to 50 relative to GMC100 base; no silent physics changes. Pinned Linux binary/source/runner/input SHA, idle/output/resources and initial VTU/rank/empty stderr passed. Require static guard0/one marker/two VTUs/exact .1Myr/H II>=10/initial mass-pressure/outer before matching .1Myr wind; a .27 continuation is conditional on short quality and runtime.

Last touched: generator option and new input sets, README/root handoff/TODO; commands included guard/SSH/SHA/resource checks, non-overwriting rsync, finite-GMC validator, corrected plots/age-fixed inner diagnostics and PNG inspection, controlled base diff and guarded launches. Products: NEW K2/Mac02 validated age profiles/plots/inner metrics and 4096 age comparison; two new jobs active. Remaining: static/wind quality, five other guards and upper-radius coverage; no fit or convergence claim.

## n_ref10000 GMC1000 mesh static gate (2026-10-17 20:51 UTC)

Keohane1 n_ref10000/GMC1000 8192-cell no-wind atmosphere finished guard 0/one Finished AMRVAC/empty stderr/two VTUs. NEW non-overwriting `results/dense_gmc_wr_early_n10000_gmc1000_vm_8192_20261017/n10000b1000/atmosphere/` independently passed exact 0.1 Myr, 98 initial H II elements, finite-GMC initial mass/pressure and stable outer fields. Matching distinct 0.02-Myr/11-VTU direct-WR wind now runs under 28800-s guard in `/tmp/van_marle_wr_early_n10000_gmc1000_8192_20261017_farm/`, exact host-corrected `dense_gmc_inputs_wr_early_n10000_gmc1000_vm_8192_20261017/manifest.csv`. Pinned Linux binary/source/runner/input SHA, idle/empty-output, CPU/memory/disk and initial VTU/rank/empty-stderr checks passed. On completion pull only NEW files; validate exact age/WR flux/outer and inspect full inner-rise/ramp profiles against GMC1500/3000. No convergence, late-WR-wall or physics-change claim.

Last touched: updated README/root handoff/TODO; commands included guarded SSH/SHA/resource checks, non-overwriting rsync, independent static validator and guarded wind launch. Products: NEW validated K1 static tree; early wind active. Remaining: validate wind and follow other six guards.

## n_ref20000 GMC1000 early profile and next bracket (2026-10-17 20:37 UTC)

Keohane1 n_ref20000/GMC1000 8192-cell 0.02-Myr/11-VTU direct-WR wind finished guard 0/one Finished AMRVAC/empty stderr. NEW non-overwriting `results/dense_gmc_wr_early_n20000_vm_8192_20261017/n20000b1000/wind/` independently passed finite-GMC exact age/initial mass-pressure/outer stability/2000-km-s/1.00051e-5-Msun-yr WR flux. NEW corrected plot and age-fixed inner full/zoom profiles were inspected. Inner R10 is 0.100428/0.177390/0.277546 pc at .004/.010/.020 Myr; shell numerical gates first pass at .004 Myr. At .020 Myr FWHM44.64 native cells, contrast8.96 and post-jump n_H 1.108e6 cm^-3, but local ramp only3.03 cells. The shallower inward precursor is retained. This supports provisional 0.1-pc radius coverage, not a resolved ramp, convergence or late-WR wall. Runtime16153.436 s; do not re-pull/rerun.

Freed K1 now runs a DISTINCT n_ref10000/GMC1000 8192-cell no-wind atmosphere in `/tmp/van_marle_wr_early_n10000_gmc1000_8192_20261017_farm/` under 7200-s guard, exact host-corrected `dense_gmc_inputs_wr_early_n10000_gmc1000_vm_8192_20261017/manifest.csv`. This brackets existing early GMC1500/3000 profiles. Base differs from validated 4096 GMC1000 only by mesh; pinned Linux binary/source/runner/input SHA, idle/output/resource and initial VTU/rank/empty stderr passed. Pull NEW and independently require guard0/one marker/two VTUs/exact .1Myr/H II>=10/initial mass-pressure/outer before matching 0.02-Myr/11-VTU wind under 28800-s guard. Compare inner R10/ramp and shell density, no convergence from width alone.

Last touched: generated/host-corrected K1 inputs and updated README/root handoff/TODO; commands included guard/SSH/SHA/resource checks, non-overwriting rsync, independent validator, corrected plotter/inner diagnostic/PNG inspection, mesh diff and guarded static launch. Products: NEW validated K1 early wind/plot/inner tree, new static active. Remaining: static gate, conditional wind and six other host guards; no gravity/support/cooling/conduction change.

## n_ref1000 mesh short and GMC2000 mesh static (2026-10-17 20:08 UTC)

Pauley404-01 n_ref1000/GMC100 8192-cell direct-WR 0.1-Myr wind finished guard 0/one marker/empty stderr/six VTUs. NEW non-overwriting `results/dense_gmc_wr_orthogonal_n1000_low_mac_8192_20261017/Pauley404-01/n01000b0100/wind/` independently passed finite-GMC exact-age/initial-mass-pressure/outer/2000-km-s/9.99521e-6-Msun-yr flux. Corrected NEW plot and age-fixed full/zoom profiles give inner R10 3.330476 pc, local ramp 4.40 native cells, peak 3.341455 pc, FWHM10.47 cells, contrast127.23 and post-jump n_H 12733 cm^-3. Compared with validated 4096 R10 3.193786 and ramp2.77, the ramp remains underresolved and radius is not converged. Runtime 9931.090 s; do not repeat/re-pull. A distinct base-byte-identical 8192-cell 0.27-Myr/15-VTU continuation now runs on freed Mac01 under 36000-s guard in `/private/tmp/van_marle_wr_orthogonal_n1000_low_8192_027myr_20261017_mac_farm/`, exact host-corrected `dense_gmc_inputs_wr_orthogonal_n1000_low_mac_8192_027myr_20261017/manifest.csv`. Short runtime x2.7 <=80% guard; pinned SHA/idle/output/resource and initial VTU/rank/empty stderr passed. Validate endpoint/WR flux/outer and compare full inner profiles to 4096 before using the upper-radius bin.

Pauley404-03 n_ref20000/GMC2000 8192-cell no-wind atmosphere finished guard 0/one marker/empty stderr/two VTUs. NEW pull to `results/dense_gmc_wr_early_n20000_gmc2000_mac_8192_20261017/Pauley404-03/n20000b2000/atmosphere/` passed exact .1Myr, 61 initial H II, mass/pressure and outer stability. Matching 0.02-Myr/11-VTU early WR wind now runs on Mac03 in `/private/tmp/van_marle_wr_early_n20000_gmc2000_8192_20261017_mac_farm/` under 28800-s guard with pinned SHA, idle/output/resource and initial rank/VTU/empty stderr checks. Compare all matched-age inner rise/ramp/shell density with 4096; no convergence from width alone.

Last touched: generated/host-corrected Mac01 age inputs, updated README/root handoff/TODO; commands included SSH/SHA/resource/guard checks, non-overwriting rsync, independent validator, corrected plotter/inner-edge diagnostic/PNG inspection, base `cmp` and guarded launches. Products: NEW Mac01 validated short and Mac03 validated static trees; two winds in flight. Remaining: validate winds and other five active guards; no physics change.

## GMC2000 early profile and matched mesh gate (2026-10-17 19:57 UTC)

Pauley404-03 n_ref20000/GMC2000 4096-cell 0.02-Myr/11-VTU direct-WR wind finished guard 0/one Finished AMRVAC/empty stderr. NEW non-overwriting `results/dense_gmc_wr_early_n20000_gmc2000_mac_4096_20261017/Pauley404-03/n20000b2000/wind/` independently passed finite-GMC exact age/initial mass-pressure/outer stability/2000-km-s/1.03923e-5-Msun-yr WR flux. NEW corrected plot and age-fixed inner-edge profiles were inspected. Numerical shell gates first pass at 0.008 Myr, inner R10 0.150341 pc; at 0.020 Myr R10 0.269841 pc, FWHM 26.09 native, contrast 7.52, post-jump n_H 970088 cm^-3, but the local steep ramp is only 2.94 native cells. Earlier 0.004-Myr R10 0.097533 pc fails FWHM gate. Retain full inward precursor; do not count unresolved ramps as converged shell structure or claim a late-WR wall. Runtime 1914.888 s. Do not repeat/re-pull.

Distinct matched 8192-cell GMC2000 inputs were generated in host-corrected `dense_gmc_inputs_wr_early_n20000_gmc2000_mac_8192_20261017/manifest.csv`, changing only mesh size/stretch from 4096. Freed Mac03 now runs the guarded 7200-s no-wind atmosphere in `/private/tmp/van_marle_wr_early_n20000_gmc2000_8192_20261017_mac_farm/`; pinned binary/source/runner/input SHA, idle/output/resources and initial VTU/rank/empty stderr passed. Pull NEW and independently validate two VTUs/exact 0.1 Myr/initial H II >=10/mass-pressure/outer before launching its matching 0.02-Myr/11-VTU wind. Compare exact-age inner R10/ramp, shell density and full profile with 4096; width alone is not convergence.

Last touched: generated and host-corrected 8192 inputs and updated README/root handoff/TODO; commands included guard/SSH/resource/SHA checks, non-overwriting rsync, independent validator, corrected plotter, inner-edge diagnostic and PNG inspection, mesh diff and guarded static launch. Products: NEW validated 4096 GMC2000 wind/plot/inner trees; 8192 static active. Remaining: validate static and conditional wind and follow other hosts; no physics changes.

## n_ref20000 GMC1000 age result and GMC2000 early test (2026-10-17 19:20 UTC)

Pauley404-03 n_ref20000/GMC1000 4096-cell 0.27-Myr direct-WR wind finished guard 0/one marker/empty stderr/15 VTUs. Non-overwriting pull to `results/dense_gmc_wr_orthogonal_n20000_low_027myr_mac_4096_20261017/Pauley404-03/n20000b1000/wind/` passed independent exact-age/finite-GMC initial mass-pressure/stable outer/2000-km-s/1.03922e-5-Msun-yr-flux validation. NEW corrected plot and age-fixed inner-rise profile: inner R10 2.041196 pc, local steep ramp 2.61 native cells, density-excess peak 2.052424 pc, FWHM 151.64 native cells, contrast 5.09 and post-jump n_H 15570 cm^-3 at 0.27 Myr. Shell numerical gates pass but the local rise remains underresolved; a broad profile is not a demonstrated thin late-WR/GRB wall. Runtime 25965.657 s. Do not repeat or re-pull.

To probe the 0.1/0.18-pc bins with independent GMC density, a distinct n_ref20000/GMC2000 4096-cell 0.02-Myr/11-VTU direct-WR wind was generated in host-corrected `dense_gmc_inputs_wr_early_n20000_gmc2000_mac_4096_20261017/manifest.csv`. Its base is byte-identical to the completed GMC2000 static/short; the saved atmosphere independently re-passed two VTUs/exact 0.1 Myr/30 initial H II/initial mass-pressure/outer validation. On freed Mac03 it now runs under a 28800-s guard in separate `/private/tmp/van_marle_wr_early_n20000_gmc2000_20261017_mac_farm/` after pinned arm64 binary/source/runner/new input SHA, idle/output/resource checks; initial VTU, one rank and empty stderr. Validate exact endpoint/WR flux/outer fields and inspect all saved full/zoom profiles before using any log-radius bin. Compare GMC1000/2000 at matched ages, preserving the broad inward precursor.

Last touched: generated and host-corrected new early input set, updated README/root handoff/TODO; commands included guard/SSH/rsync/finite-GMC/plot/inner-edge/PNG and CSV inspection, base diff, SHA/resource checks and guarded launch. Products: NEW validated age wind/plots/inner diagnostics; early wind active. Remaining: new early quality and six other guards; no physics change or convergence claim.

## n_ref10000 early 8192 static gate (2026-10-17 18:19 UTC)

Keohane3/4 GMC1500/GMC3000 8192-cell no-wind atmospheres finished guard 0/one marker/empty stderr/two VTUs. Non-overwriting pulls to `results/dense_gmc_wr_early_n10000_transition_vm_8192_20261017/<tag>/atmosphere/` independently passed exact 0.1 Myr, 98 initial H II elements, initial mass/pressure and stable outer fields. Matching 0.02-Myr/11-VTU direct-WR winds now run one per host in separate `/tmp/van_marle_wr_early_n10000_8192_20261017_farm/` checkouts under 28800-s guards. Exact `dense_gmc_inputs_wr_early_n10000_transition_vm_8192_20261017/manifest.csv`; pinned binary/source/runner/input SHA, idle/empty-wind-output and resource checks passed, followed by initial VTU/one rank/empty stderr. On completion require guard0/one marker/empty stderr/11 VTUs/exact 0.02 Myr/finite fields/WR flux/outer stability. Pull only NEW files, then compare each age's full density, inner R10, local ramp native cells and shell density with its 4096 match. No convergence or physical shock-thickness claim from width alone.

Last touched: updated README/root handoff/TODO; commands included guarded SSH/rsync/validator/SHA/resource checks and guarded wind launches. Products: NEW validated atmosphere trees, winds in flight. Remaining: validate 8192 winds and follow five other hosts; no physics change.

## n_ref10000 early 4096 results and 8192 mesh gate (2026-10-17 18:03 UTC)

Keohane3/4 n_ref10000/GMC1500 and GMC3000 4096-cell 0.02-Myr high-cadence direct-WR winds finished guard 0/one marker/empty stderr/11 VTUs. NEW non-overwriting pulls under `results/dense_gmc_wr_early_n10000_transition_vm_4096_20261017/<tag>/wind/` passed independent exact-age, finite-GMC initial mass/pressure, outer stability, 2000-km/s wind and ~1.0392e-5-Msun/yr inner-flux checks. Corrected plots and age-fixed full/zoom inner profiles were inspected. At 0.02 Myr, GMC1500/GMC3000 inner R10 is 0.337752/0.334970 pc, FWHM 13.34/25.37 native elements, contrast 16.98/9.35 and post-jump n_H ~9.01e5/4.67e5 cm^-3. Both pass shell gates but the local steep ramps span only 3.47/2.94 cells. At 0.008 Myr GMC3000 passes shell gates near R10 0.181271 pc, whereas GMC1500 first passes at 0.012 Myr near R10 0.236623 pc; these early ramps also remain underresolved. The full profile retains a shallower inward precursor. No convergence or physical shock-thickness claim.

To test the 0.1-0.3-pc radius/ramp sampling, matched distinct 8192-cell cases were generated in `dense_gmc_inputs_wr_early_n10000_transition_vm_8192_20261017/manifest.csv`; base diff from 4096 is mesh size/stretch only. Pinned binary/source/runner/input SHA and free-host/output/resources passed. Guarded 7200-s no-wind atmospheres now run one per K3/4 in separate `/tmp/van_marle_wr_early_n10000_8192_20261017_farm/` checkouts, with initial VTU, one rank and empty stderr. Validate two VTUs/exact 0.1 Myr/H II>=10/initial mass-pressure/outer before launching matching 0.02-Myr/11-VTU wind under 28800 s. Measured 4096 early runtimes were 4081/4060 s, allowing a mesh-scaled guard margin. Compare matched-age inner rise, shell density and full profile, not FWHM alone.

Last touched: generated 8192 input set, updated README/root handoff/TODO; commands included guard/SSH/rsync/validator/plotter/inner-edge/PNG and mesh/SHA/resource checks and static launches. Products: NEW validated 4096 early winds/plots/age-fixed diagnostics; 8192 static jobs in flight. Remaining: static validation then conditional winds, other five guards; no cooling/conduction/gravity/support change.

## n_ref1000 matched-mesh static gate (2026-10-17 17:17 UTC)

Pauley404-01's n_ref1000/GMC100 8192-cell no-wind atmosphere finished guard 0/one marker/empty stderr/two VTUs. A non-overwriting pull to `results/dense_gmc_wr_orthogonal_n1000_low_mac_8192_20261017/Pauley404-01/n01000b0100/atmosphere/` independently passed finite-GMC exact 0.1-Myr, 128 initial H II elements, initial mass/pressure and outer stability. The matching distinct 0.1-Myr/6-VTU WR wind now advances in `/private/tmp/van_marle_wr_orthogonal_n1000_low_8192_20261017_mac_farm/` under a 28800-s guard. Pinned arm64 binary/source/runner/input SHA, idle/output/resource checks passed; initial VTU/one rank/empty stderr verified. On completion compare the full density and inner-rise profile against the K2 4096-cell short (inner R10 3.193786 pc, local ramp only 2.77 cells). A wider native ramp alone is not convergence or a physical shock thickness.

Last touched: updated README/root handoff/TODO; commands included SSH guard/resource/SHA checks, `rsync --ignore-existing`, independent static validator and guarded wind launch. Product: NEW validated atmosphere tree, wind in flight. Remaining: validate/plot mesh wind and other active guards; no cooling/conduction/gravity/support change.

## Upper-radius and matched-mesh tests (2026-10-17 17:04 UTC)

Keohane2 n_ref1000/GMC100 4096-cell 0.1-Myr direct-WR short finished guard 0/one marker/empty stderr/six VTUs. It was pulled without overwrite to `results/dense_gmc_wr_orthogonal_n1000_low_vm_4096_20261017/n01000b0100/wind/` and independently passed finite-GMC exact-age, initial mass/pressure, outer stability, 2000-km/s and 9.99045e-6-Msun/yr WR-flux checks. NEW corrected plot and full/zoom inner profile were inspected: inner R10 3.193786 pc, local 10-90% ramp 2.77 native cells, density-excess peak 3.205977 pc, FWHM 5.50 native cells and contrast124.5. The shell barely clears the FWHM floor but the steep ramp is unresolved. Runtime 5148.572 s leaves 2.7x projection under 80% of the guard. A distinct base-byte-identical 0.27-Myr/15-VTU wind-only continuation now advances on K2 under a 36000-s guard in `/tmp/van_marle_wr_orthogonal_n1000_low_027myr_20261017_farm/`, exact `dense_gmc_inputs_wr_orthogonal_n1000_low_027myr_vm_4096_20261017/manifest.csv`. Pinned SHA/idle/output/resource and initial VTU/rank/empty-stderr checks passed. The longer profile may test the upper log-radius gap; it does not promise a quality 10-pc shell.

Pauley404-01 n_ref3000/GMC100 8192-cell 0.27-Myr direct-WR wind finished guard 0/one marker/empty stderr/15 VTUs. Non-overwriting pull to `results/dense_gmc_wr_orthogonal_n3000_gmc100_mac_8192_027myr_20261017/Pauley404-01/n03000b0100/wind/` independently passed the same fields/flux gates (9.99521e-6 Msun/yr). New corrected profiles give inner R10 6.486148 pc, local ramp 14.56 native cells, peak 6.532757 pc, FWHM24.01 cells and contrast64.49, with a shallower inward precursor distinct from the local steep jump. This is not a preconditioned late-WR/GRB wall. Freed Mac01 now runs a distinct n_ref1000/GMC100 8192-cell no-wind atmosphere for a matched-mesh check of K2's underresolved 4096 short. Exact host-corrected `dense_gmc_inputs_wr_orthogonal_n1000_low_mac_8192_20261017/manifest.csv`; separate `/private/tmp/van_marle_wr_orthogonal_n1000_low_8192_20261017_mac_farm/`. Pinned Mac arm64 binary/source/runner and input SHA, idle/output/resource checks passed; initial VTU/rank/empty stderr. Require static exit0/one marker/two VTUs/exact age/H II>=10/initial mass-pressure/outer stability before the matching 0.1-Myr WR wind.

Last touched: generated new input sets and host-corrected Mac manifest; updated README/root handoff/TODO. Commands: guarded SSH/status/resource/SHA checks, non-overwriting rsync, independent validator, corrected plotter/inner-rise diagnostics, visual inspection, base `cmp`, guarded launches. Products: NEW validated K2/Mac01 wind, plots and inner diagnostics; K2 continuation and Mac01 atmosphere active. Remaining: validate new and other in-flight guards; no cooling/conduction/gravity/support change, convergence or fitted radius law.

## n_ref10000 transition and early sampling (2026-10-17 16:49 UTC)

Keohane3/4 n_ref10000/GMC1500 and GMC3000 4096-cell direct-WR 0.1-Myr winds finished guard 0/one marker/empty stderr/six VTUs and were pulled without overwrite to `results/dense_gmc_wr_orthogonal_n10000_transition_vm_4096_20261017/<tag>/wind/`. Independent finite-GMC exact-age, initial mass/pressure, outer stability, 2000-km/s WR and ~1.0392e-5-Msun/yr flux checks passed. New corrected plots and age-fixed full/zoom density profiles were inspected. GMC1500 inner R10 is 1.193058 pc with local ramp 2.80 native cells; peak 1.203496 pc, FWHM 123.91 cells, contrast 5.34. GMC3000 inner R10 is 1.098615 pc, local ramp 2.93 cells; peak 1.108371 pc, FWHM 367.92 cells, contrast 2.23. GMC3000 fails contrast and FWHM/radius quality gates; neither ramp is adequately resolved. These are direct-WR enhancements, not a thin late-WR/GRB wall or a convergence demonstration. Measured ~20.35/20.21-ks short runtimes rule out 0.27-Myr VM continuations under the projected guard.

Freed K3/4 now each run a distinct 0.02-Myr WR wind saving 11 VTUs at 0.002-Myr cadence in `/tmp/van_marle_wr_early_n10000_transition_20261017_farm/`, exact `dense_gmc_inputs_wr_early_n10000_transition_vm_4096_20261017/manifest.csv`. Generated bases are byte-identical to those already static-validated and short-run-validated; only duration/output cadence differ. Pinned binary/source/runner/input SHA, idle host, empty output and resource gates passed. Initial VTU/one rank/empty stderr at launch. On completion check the full WR/outer gates and per-snapshot shell/inner-rise/ramp before using early radii, particularly for the GMC3000 contrast transition.

Last touched: generated new high-cadence input set, updated README/root handoff/TODO; commands included guarded SSH checks, non-overwriting rsync, independent validator, corrected plotter and inner-rise diagnostics, visual inspection, base `cmp`, SHA/resource checks and guarded launch. Products: NEW K3/4 validated wind, plots and inner profiles; high-cadence winds in flight. Remaining: validate early outputs and other hosts; no gravity/support/cooling/conduction change.

## Early-radius 8192 static gate (2026-10-17 16:04 UTC)

Keohane1 n_ref20000/GMC1000 8192-cell no-wind atmosphere completed guard 0/one marker/empty stderr/two VTUs. It was pulled without overwrite to `results/dense_gmc_wr_early_n20000_vm_8192_20261017/n20000b1000/atmosphere/` and independently passed finite-GMC exact 0.1-Myr, 61 initial H II elements, initial mass/pressure and outer stability. The matching distinct 0.02-Myr direct-WR case now advances under a 28800-s guard in `/tmp/van_marle_wr_early_n20000_8192_20261017_farm/`; it saves 11 VTUs at 0.002-Myr cadence and had an initial VTU, one rank and empty stderr after launch. Its input/pinned binary/source/runner hashes, idle-host, empty-output, disk and memory gates passed. Do not count 0.10/0.18-pc radius coverage until the wind passes exact-age/WR-flux/outer and per-snapshot shell/ramp gates.

Last touched: modified README/root handoff/TODO; commands were guarded SSH/resource/SHA checks, `rsync --ignore-existing`, independent validator and guarded wind launch. Output: NEW validated atmosphere tree; early wind in flight. Remaining: validate/plot/measure inner rise on completion and follow other hosts; no physical model change or convergence claim.

## GMC125 matched mesh and early-radius cadence (2026-10-17 15:52 UTC)

Keohane1's n_ref5000/GMC125 8192-cell direct-WR 0.1-Myr wind finished guard 0/one marker/empty stderr/six VTUs. Non-overwriting pull to `results/dense_gmc_wr_orthogonal_n5000_gmc125_vm_8192_20261017/n05000b0125/wind/` independently passed finite-GMC exact-age, initial mass/pressure, outer stability, 2000-km/s and 9.99521e-6-Msun/yr WR flux. Corrected NEW plots and age-corrected inner-edge diagnostics show inner R10 1.621163 pc vs the matched 4096 run's 1.500874 pc (~8.0% shift); local steep-jump ramps span only 3.45 and 2.72 native cells respectively. The 8192 density-excess peak is 1.628938 pc, FWHM 9.87 native cells and contrast 110.10. Despite shell FWHM quality passing, neither inner-ramp resolution nor radius convergence is established. Measured runtime 20308.143 s makes a 0.27-Myr VM continuation exceed the 28800-s projection; do not launch it or repeat this short.

For the missing small-radius bins, new exact `dense_gmc_inputs_wr_early_n20000_macmesh_vm_8192_20261017/manifest.csv` stages n_ref20000/GMC1000 on freed Keohane1. Its base differs from the completed Mac03 4096 short only in mesh (`domain_nx1` 8192 and the corresponding stretch ratio); gravity, support, cooling-off and conduction-off physics remain pinned. The generator's opt-in `--wind-save-interval-myr 0.002` produces 11 saves over a 0.02-Myr direct-WR wind without changing default cadence for other cases. SHA-matched pinned Linux binary/source/runner and inputs, idle/output/resource gates passed in separate `/tmp/van_marle_wr_early_n20000_8192_20261017_farm/`. A guarded 7200-s no-wind atmosphere currently advances there with one initial VTU, active rank and empty stderr. Require its exit0/one normal marker/two VTUs/exact 0.1 Myr, initial H II >=10, mass/pressure and outer stability before launching matching guarded 28800-s wind. Its early inner radii and ramp cells, not a density peak alone, determine whether 0.10/0.18-pc log bins are usable; no convergence or late-WR-wall claim.

Last touched: modified case generator/README/root handoff/TODO and generated the new high-cadence input set; commands were K1 SSH guard/SHA/resource checks, non-overwriting rsync, independent validator, corrected plotter and inner-edge diagnostic, input-base diff and guarded atmosphere launch. Products: NEW validated GMC125 mesh wind/plots/inner-edge diagnostics and active early-test atmosphere. Remaining: validate static then conditional early wind, follow K2/3/4 and Macs, assess quality-gated log-radius coverage.

## GMC1000 age endpoint and radius coverage (2026-10-17 15:36 UTC)

Keohane2's n_ref5000/GMC1000 4096-cell direct-WR 0.27-Myr wind finished with guard exit 0, exactly one Finished AMRVAC marker, empty stderr and 15 VTUs. Non-overwriting pull to `results/dense_gmc_wr_orthogonal_n5000_gmc1000_027myr_vm_4096_20261017/n05000b1000/wind/` passed independent finite-GMC exact-age, 16-initial-H-II, initial mass/pressure, outer stability, 2000-km/s WR and 9.99046e-6-Msun/yr flux validation. New corrected profile and inner-edge diagnostics give inner 10% radius 3.861819 pc, local 10-90% ramp 6.46 native cells, post-jump density 2205 cm^-3, density-excess peak 4.626915 pc, FWHM 186.60 cells and contrast 3.535. The full profile has a broad shallower precursor inward of the steep jump; numerical quality gates pass but this is not a demonstrated thin late-WR or GRB wall. AMRVAC time 13689.980 s. Do not re-pull or repeat.

`measure_shell_inner_edge.py` now converts Julian years from `read_vtu` to the case's 365-day-year Myr convention, matching `validate_cloud_mass.py`; a focused test covers the conversion. The earlier `results/dense_gmc_inner_edge_20261017/final_*/` CSVs without `_agefix` have snapshot ages low by 0.0684% and are superseded by NEW `_agefix` dirs for all four earlier cases plus GMC1000. Their density/radius metrics were not affected. Five corrected sources have 37 quality-gated measured snapshots: nearest inner radii for targets 0.32/0.56/1.0/1.8/3.2/5.6 pc are 0.271/0.587/0.899/1.774/3.164/5.456 pc. The 0.10, 0.18 and 10 pc targets remain unfilled; early local ramps often fail the separate >=5-cell sampling check. Do not fit a smooth radius law or claim convergence from this inventory.

To probe the upper gap without changing physics, a distinct opt-in n_ref1000/GMC100 4096-cell direct-WR case was generated in `dense_gmc_inputs_wr_orthogonal_n1000_low_vm_4096_20261017/manifest.csv` and hash-matched to the pinned Keohane2 Linux binary/source/runner. Its guarded no-wind atmosphere exited 0 with one marker, empty stderr and two VTUs; non-overwriting pull to `results/dense_gmc_wr_orthogonal_n1000_low_vm_4096_20261017/n01000b0100/atmosphere/` independently passed exact 0.1 Myr, 64 initial H II cells, initial mass/pressure and outer stability. Matching 0.1-Myr direct-WR wind now advances in separate `/tmp/van_marle_wr_orthogonal_n1000_low_20261017_farm/` under a 28800-s guard, with one initial VTU, one rank and empty stderr. Validate wind and inspect its full density/inner-rise profile before considering a duration extension. No 4.77-Myr full, cooling, conduction, gravity/support change or duplicate physics case.

Last touched: modified generator, inner-edge diagnostic/test and this README/root handoff/TODO; generated new input set and NEW non-overwriting GMC1000 wind/plots/age-corrected diagnostics and n_ref1000 static atmosphere. Commands: guarded SSH/hash/resource checks, rsync, independent validator, corrected plotter/inner-edge script and four unit tests. Remaining: follow seven active guarded hosts, validate n_ref1000 wind and new completions, assess endpoint gaps and ramp resolution.

## Provisional inner bubble radius (2026-10-17 14:33 UTC)

Use the inner side of the dominant swept-shell density jump as the working
bubble-radius coordinate, with the older density-excess peak retained only as
a comparison. `plot_dense_gmc_scan.py::inner_rise` selects the strongest
positive native density gradient on the inner side of the selected shell,
then brackets its contiguous local rise where the gradient exceeds 5% of
that maximum. In *linear* `n_H`, the first 10% crossing is `inner_radius_pc`;
the 50% and 90% crossings and their 10-90% separation report location and
local jump width. `prejump_nh_cm3` is the density immediately before this
steep jump, **not** the cavity floor. `shell_inner_nh_cm3` is the level just
after it. The full saved profile retains any shallower inward precursor;
the 10-90% width does not include that precursor. Ambiguous jumps are
flagged rather than assigned an inner radius.

`measure_shell_inner_edge.py` independently revalidates an already-completed
wind and writes every noninitial snapshot's inner-edge CSV plus a full/zoom
profile PNG into a NEW directory. The corrected plotter now reports the
inner edge alongside the old peak in new outputs, without modifying old
results. Diagnostic products are under
`results/dense_gmc_inner_edge_20261017/final_*/`; earlier same-day
non-`final_` directories are exploratory and superseded. Tests in
`test_measure_shell_inner_edge.py` cover a broad precursor, later crest,
missing jump and unordered radius.

At 0.1 Myr, matched n_ref3000/GMC900 4096/8192 inner radii are
1.843885/1.978934 pc (7.3% difference), versus 1.862348/2.203016 pc
for peak radii (18.3%). The local 10-90% jump widths are 0.010640/0.012822
pc, sampled by 3.93/9.28 native cells; the 4096 ramp is not adequately
sampled. The n_ref20000/GMC1000 4096 inner radius is 0.878057 pc at
0.1 Myr, but its ramp has only 2.73 native cells. The n_ref3000/GMC150
0.27-Myr inner radius is 5.872812 pc, with a distinct shallower precursor
visible inward of the big jump. These results support the definition but
**do not establish convergence or a physical shock thickness**. Keep
`inner_ramp_resolved` separate from the established shell-FWHM quality gate;
test more matched profiles and any candidate log-radius fit before claiming
a stable radius law.

Last touched: modified `plot_dense_gmc_scan.py`, added
`measure_shell_inner_edge.py` and its focused tests, updated README/root
handoff/TODO and the quiet heartbeat objective. Commands: `unittest`,
`py_compile`, finite-GMC revalidation/diagnostics on four completed wind
trees, corrected one-case plot, CSV and PNG inspection. Regenerated only
new diagnostic directories, no AMRVAC inputs or jobs. Remaining: expand
cross-resolution checks and catalog radius/age/profile quality across the
validated grid before a fit.

## Log-radius coverage objective (2026-10-17 14:21 UTC)

Target a validated set of direct-WR density profiles spanning roughly 0.1-10 pc,
with useful coverage near logarithmic centers 0.10, 0.18, 0.32, 0.56, 1.0,
1.8, 3.2, 5.6 and 10 pc. Age, core density, GMC density and mesh remain
explicit coordinates; snapshots at different ages are not interchangeable
realizations of one ambient parameter. Record the full radial density profile,
shell density and inner rise/ramp as well as a radius. The density-excess
maximum is only a provisional radius proxy: the validated n_ref3000/GMC900
4096/8192 short pair shifts its peak by 18.29% while physical FWHM changes
1.90%, so test a reproducible rising-edge definition and matched-resolution
profiles before fitting a radius law.

Saved validated WR snapshots already sample a provisional peak-radius sequence
of 0.286, 0.442, 0.593, 0.740 and 0.885 pc at 0.02-0.10 Myr for
n_ref20000/GMC1000; the 0.02-Myr snapshot has native FWHM 23.1 cells,
contrast 8.42 and FWHM/radius 0.061. Validated n_ref3000/GMC150 snapshots
reach a provisional 5.945 pc by 0.27 Myr. These are *not* a validated
log-spaced fit: apply the shell-quality and initial-atmosphere gates to every
candidate snapshot and inspect the rise/profile. The open endpoint gaps are
below about 0.29 pc and above about 6 pc. A distinct high-cadence early-time
mesh test could address the former; a new low-density finite-GMC bracket could
test the latter. Stage either only after checking existing products, unique
physics/mesh, host capacity, and the same static-first/run-validation gates.
The 0.1 and 10 pc endpoints may not yield quality shells within this
0.27-Myr WR-only phase; do not force a fit or alter cooling, conduction,
gravity, or support to make them appear.

Last touched: updated this README and root handoff/TODO; commands included
read-only saved-VTU native-shell analysis and host/resource checks. No input
files, AMRVAC jobs, or output products were created in this planning step.
Remaining from this planning step was the rising-edge definition; the
provisional implementation and its first tests are documented above.
Inventory the validated snapshots against the log targets, then stage gap
tests on freed hosts if warranted.

## n_ref3000 GMC900 mesh sensitivity (2026-10-17 14:00 UTC)

Pauley404-02's 8192-cell 0.1-Myr direct-WR wind finished guard 0/one marker/empty stderr/six VTUs, was pulled without overwrite to `results/dense_gmc_wr_orthogonal_n3000_gmc900_mac_8192_20261017/Pauley404-02/n03000b0900/wind/`, and independently passed exact age, finite-GMC initial mass/pressure, stable outer fields, 2000-km/s wind and 9.99521e-6-Msun/yr inner flux. New corrected host plots were inspected: peak 2.203016 pc, FWHM 156.16 native elements (0.22222 pc), contrast 7.641, 49 initial H II elements. Matched 4096 short had peak 1.862348 pc, FWHM 80.34 elements (0.21808 pc), contrast 7.215. The density-maximum peak shifts 18.29% while physical FWHM differs only 1.90%; both show a broad-topped enhancement. The peak-radius metric is not converged and must not be the only shell-radius definition for parameterization. Runtime 9340.929 s. Do not re-pull or rerun.

A distinct wind-only 0.27-Myr 8192-cell GMC900 continuation was generated in `dense_gmc_inputs_wr_orthogonal_n3000_gmc900_mac_8192_027myr_20261017/manifest.csv`, with cloud/mesh base byte-identical to this validated short. Short runtime times 2.7 leaves >20% margin on the 36000-s guard. Pinned Mac binary/source/runner/input SHA, free-host, empty-output and resource gates passed. Mac02 now runs it in separate `/private/tmp/van_marle_wr_orthogonal_n3000_gmc900_8192_027myr_20261017_mac_farm/` with initial VTU, one rank and empty stderr. Validate 15 VTUs/exact 0.27 Myr, WR flux and outer stability, then compare exact-age 4096/8192 full profiles and candidate radius definitions. This is not a late-WR/GRB-wall or convergence proof.

## n_ref20000 GMC1000 short profile and age test (2026-10-17 12:00 UTC)

Pauley404-03 n_ref20000/GMC1000 4096-cell direct-WR 0.1-Myr wind finished guard 0/one marker/empty stderr/six VTUs, was pulled without overwrite to `results/dense_gmc_wr_orthogonal_n20000_low_mac_4096_20261017/Pauley404-03/n20000b1000/wind/`, and independently passed exact-age, finite-GMC initial mass/pressure, stable outer fields, 2000-km/s wind and 1.03922e-5-Msun/yr inner flux. Corrected new `Pauley404-03/plots_n20000b1000_wind_v1/` was inspected: peak 0.885262 pc, FWHM 116.84 native elements, contrast 4.799, width/radius 0.168. The validated GMC2000 short peak/FWHM/contrast were 0.857513 pc/183.84/3.24, width/radius 0.268. GMC1000 clears numeric shell gates, but its narrow spike has a broad outer shoulder and is not a proven preconditioned late-WR or GRB wall. Runtime 9603.280 s. Do not re-pull or repeat either short.

A distinct wind-only 0.27-Myr GMC1000 continuation was generated in `dense_gmc_inputs_wr_orthogonal_n20000_low_027myr_mac_4096_20261017/manifest.csv`. Its base is byte-identical to the validated short. Measured short time times 2.7 is below 80% of the 36000-s guard; pinned binary/source/runner/input SHA, idle/output and resource checks passed. It now advances on Mac03 in separate `/private/tmp/van_marle_wr_orthogonal_n20000_low_027myr_20261017_mac_farm/` with initial VTU, one rank and empty stderr. Validate 15 VTUs/exact 0.27 Myr/WR flux/outer stability and inspect whether the peak remains sharp before using this profile in any parameterization.

## n_ref5000 age-dependent GMC contrast (2026-10-17 11:32 UTC)

Keohane2 n_ref5000/GMC1500 4096-cell direct-WR 0.27-Myr continuation finished guard 0/one marker/empty stderr/15 VTUs, was pulled without overwrite to `results/dense_gmc_wr_orthogonal_transition_027myr_vm_4096_20261017/n05000b1500/wind/`, and independently passed exact-age/finite-GMC/initial mass-pressure/stable outer-field/2000-km/s/9.99046e-6-Msun/yr WR-flux checks. New corrected plots in `results/dense_gmc_wr_orthogonal_transition_027myr_vm_4096_20261017/plots_n05000b1500_wind_v1/` were inspected: peak 4.649628 pc, FWHM 194.48 native elements, contrast 2.256 and FWHM/radius 0.159. The broad plateau fails the >=3 contrast gate although the matched 0.1-Myr case passed. Runtime 13699.441 s. This is not a confirmed thin late-WR shell; do not re-pull or rerun.

To bracket the age-dependent contrast transition between validated n_ref5000/GMC500 (0.27-Myr contrast 8.43) and GMC1500, a distinct GMC1000 0.27-Myr wind-only case was generated in `dense_gmc_inputs_wr_orthogonal_n5000_gmc1000_027myr_vm_4096_20261017/manifest.csv`. Its cloud/mesh base is byte-identical to the validated Mac02 GMC1000 0.1-Myr short, whose measured runtime plus VM scaling clears the 36000-s guard margin. Pinned Linux binary/source/runner/input SHA, empty-output, idle-host and resource gates passed in separate Keohane2 `/tmp/van_marle_wr_orthogonal_n5000_gmc1000_027myr_20261017_farm/`. Its guarded 0.27-Myr WR wind now advances with an initial VTU, one rank and empty stderr. On completion validate 15 VTUs, exact 0.27 Myr, WR flux and outer stability; plot corrected native profile into a NEW directory. Do not conflate this direct-WR age test with a preconditioned late-WR/GRB wall.

## n_ref3000/GMC900 age endpoint and mesh comparison (2026-10-17 11:19 UTC)

Pauley404-02's 4096-cell n_ref3000/GMC900 direct-WR 0.27-Myr continuation finished guard 0/one marker/empty stderr/15 VTUs, was pulled without overwrite to `results/dense_gmc_wr_orthogonal_n3000_gmc900_027myr_mac_4096_20261017/Pauley404-02/n03000b0900/wind/`, and independently passed exact-age, finite-positive, initial mass/pressure, stable outer-field, 2000-km/s and 9.99046e-6-Msun/yr WR-flux checks. New corrected plots in `Pauley404-02/plots_n03000b0900_wind_v1/` were inspected: peak 5.012420 pc, FWHM 185.51 native elements, contrast 3.281, FWHM/radius 0.145. Numerical gates pass, but the enhancement is a broad plateau; no thin late-WR-wall inference. Runtime 6577.090 s. Do not repeat or re-pull.

Because the validated n_ref3000/GMC600/900/1200 short-age radii are nonmonotonic, a distinct matched GMC900 8192-cell mesh test was generated in `dense_gmc_inputs_wr_orthogonal_n3000_gmc900_mac_8192_20261017/manifest.csv`. Its base changes only mesh settings from the validated 4096 short. Pinned Mac binary/source/runner and input SHA matched after staging in separate `/private/tmp/van_marle_wr_orthogonal_n3000_gmc900_8192_20261017_mac_farm/`. On freed Mac02 the guarded no-wind atmosphere completed exit 0/one marker/empty stderr/two VTUs, was pulled non-overwriting to `results/dense_gmc_wr_orthogonal_n3000_gmc900_mac_8192_20261017/Pauley404-02/n03000b0900/atmosphere/`, and independently passed exact 0.1 Myr, 49 initial H II elements, initial mass/pressure and outer stability. The matching guarded 0.1-Myr direct-WR wind now advances on Mac02 with initial VTU, one rank and empty stderr. Compare exact-age radius, profile and native width with 4096, not width alone.

## n_ref10000 GMC bracket endpoints and transition tests (2026-10-17 11:00 UTC)

Keohane3/4 n_ref10000/GMC500 and GMC2000 4096-cell direct-WR 0.1-Myr winds finished with guard exit 0, one normal marker, empty stderr and six VTUs. Non-overwriting pulls to `results/dense_gmc_wr_orthogonal_4096_20261016/n10000b0500/wind/` and `n10000b2000/wind/` passed independent exact-age, finite-GMC, initial mass/pressure, outer-field, 2000-km/s wind and 1.03921e-5-Msun/yr inner-flux checks. Corrected NEW plot dirs `plots_n10000b0500_wind_v1/` and `plots_n10000b2000_wind_v1/` were inspected: peak/FWHM/contrast 1.247487 pc/36.21 native elements/16.89 and 1.172728 pc/191.49/3.67. The GMC500 shell is sharp; the GMC2000 profile is a broad plateau with FWHM/radius 0.249, barely inside the numeric limit and not evidence of a thin wall. Runtimes 20394.688/20303.994 s rule out 0.27-Myr continuation under the 28800-s projected guard.

To map the profile transition, new distinct n_ref10000/GMC1500 on Keohane3 and GMC3000 on Keohane4 were generated in `dense_gmc_inputs_wr_orthogonal_n10000_transition_vm_4096_20261017/manifest.csv`. Each changes only GMC density from a matched validated base. Pinned binary/source/runner and new input SHA matched after staging in separate `/tmp/van_marle_wr_orthogonal_n10000_transition_20261017_farm/` trees. Both guarded no-wind atmospheres exited 0/one marker/empty stderr/two VTUs and were pulled without overwrite to separate `results/dense_gmc_wr_orthogonal_n10000_transition_vm_4096_20261017/<tag>/atmosphere/` trees. Independent finite-GMC validation passed exact 0.1 Myr, 49 initial H II elements, initial mass/pressure and outer stability. Matching guarded 0.1-Myr WR winds now advance one per host, each with initial VTU, one rank and empty stderr. Validate six VTUs/WR flux/outer fields, plot corrected native profiles to NEW dirs and compare exact-age GMC500/1000/1500/2000/3000 before any fit.

## n_ref5000/GMC125 age endpoint and mesh check (2026-10-17 09:57 UTC)

Keohane1's 4096-cell direct-WR 0.27-Myr continuation finished with guard exit 0, one normal marker, empty stderr and 15 VTUs. It was pulled without overwrite to `results/dense_gmc_wr_orthogonal_wide_027myr_vm_4096_20261017/n05000b0125/wind/` and independently passed exact-age, finite-GMC, initial mass/pressure, stable outer-field, 2000-km/s wind and 9.99046e-6-Msun/yr inner-flux checks. Corrected new plots in `results/dense_gmc_wr_orthogonal_wide_027myr_vm_4096_20261017/plots_n05000b0125_wind_v1/` were inspected: peak 5.091322 pc, FWHM 22.06 native elements, contrast 50.05 and FWHM/radius 0.0172. Runtime was 13759.639 s. This narrow direct-WR feature does not establish a preconditioned late-WR/GRB wall.

A distinct matched n_ref5000/GMC125 8192-cell mesh test was generated in `dense_gmc_inputs_wr_orthogonal_n5000_gmc125_vm_8192_20261017/manifest.csv`. Its base differs from the validated 4096-cell short only in mesh settings; pinned Linux binary/source/runner and input hashes matched after staging in separate `/tmp/van_marle_wr_orthogonal_n5000_gmc125_8192_20261017_farm/`. The guarded no-wind atmosphere exited 0 with one marker, empty stderr and two VTUs. It was pulled without overwrite to `results/dense_gmc_wr_orthogonal_n5000_gmc125_vm_8192_20261017/n05000b0125/atmosphere/` and independently passed exact 0.1 Myr, finite-GMC initial mass/pressure, 32 H II elements and outer stability. The matching 28800-s 0.1-Myr WR wind now advances on Keohane1 with an initial VTU, one rank and empty stderr. The matched 4096-cell short FWHM was only 5.67 native elements; compare exact-age radius and profile as well as width. A wider measured shell alone is not convergence.

## n_ref3000 mesh and GMC900 short endpoints (2026-10-17 09:27 UTC)

Pauley404-01's n_ref3000/GMC100 8192-cell 0.1-Myr direct-WR wind completed normally, was pulled without overwrite to `results/dense_gmc_wr_orthogonal_n3000_gmc100_mac_8192_20261017/Pauley404-01/n03000b0100/wind/`, and passed six-VTU/exact-age/finite-GMC/initial-mass-pressure/outer-field/2000-km/s/9.99521e-6-Msun/yr-flux checks. The corrected new plot gives peak 2.007851 pc, FWHM 7.87 native elements and contrast 224.95 with 49 initial H II elements. The 4096 peak was 1.846081 pc and FWHM 4.45 elements: 8192 clears the width gate but moves radius 8.76%, so the shell is not demonstrated converged. Runtime 9396.498 s.

Pauley404-02's n_ref3000/GMC900 4096-cell short WR wind passed the same independent six-VTU checks after non-overwriting pull to `results/dense_gmc_wr_orthogonal_n3000_transition_mac_4096_20261017/Pauley404-02/n03000b0900/wind/`. Corrected new plots show peak 1.862348 pc, FWHM 80.34 native elements, contrast 7.215, FWHM/radius 0.117; visually the enhancement is distinct but broader than low-GMC cases. Runtime 2401.499 s. At 0.1 Myr the GMC600/900/1200 peaks do not form a monotonic sequence, so a simple radius fit needs physical and mesh scrutiny.

Both validated short bases are byte-identical to newly staged 0.27-Myr wind-only inputs in `dense_gmc_inputs_wr_orthogonal_n3000_gmc100_mac_8192_027myr_20261017/` and `dense_gmc_inputs_wr_orthogonal_n3000_gmc900_mac_027myr_20261017/`. Their measured 2.7x time projections clear the 36000-s guards with >20% margin. Separate guarded continuations now advance on Mac01 and Mac02 in `/private/tmp/van_marle_wr_orthogonal_n3000_gmc100_8192_027myr_20261017_mac_farm/` and `/private/tmp/van_marle_wr_orthogonal_n3000_gmc900_027myr_20261017_mac_farm/`, each with initial VTU, one rank and empty stderr. Require 15 VTUs/exact 0.27 Myr, WR flux, outer stability and profile inspection before interpretation.

## n_ref10000 age endpoint and n_ref20000 GMC bracket (2026-10-17 09:14 UTC)

Pauley404-03's n_ref10000/GMC1000 direct-WR 0.27-Myr continuation finished with guard exit 0, one normal marker, empty stderr and 15 VTUs. It was pulled without overwrite to `results/dense_gmc_wr_only_027myr_mac_4096_20261016/Pauley404-03/n10000b1000/wind/` and independently passed finite-GMC/exact-age/initial-mass-pressure/outer-field/2000-km/s/1.03921e-5-Msun/yr-flux validation. The new corrected `Pauley404-03/plots_n10000b1000_wind_v1/` profile was inspected: peak 4.159690 pc, FWHM 222.16 native elements, contrast 3.438, FWHM/radius 0.221 and 49 initial H II elements. Numerical gates pass, but the enhancement is a broad plateau, not proof of a thin preconditioned late-WR wall. Runtime 25960.265 s.

The freed Mac03 now tests a distinct n_ref20000/GMC1000 case from `dense_gmc_inputs_wr_orthogonal_n20000_low_mac_4096_20261017/manifest.csv`. Its base differs from the matched GMC2000 case only in GMC density, testing whether lower ambient density yields a sharper small-radius feature. The guarded no-wind atmosphere passed independent two-VTU/0.1-Myr finite-GMC validation after non-overwriting pull to `results/dense_gmc_wr_orthogonal_n20000_low_mac_4096_20261017/Pauley404-03/n20000b1000/atmosphere/`: 30 initial H II elements, initial mass/pressure and stable outer fields. The matching guarded 0.1-Myr direct-WR wind advances in `/private/tmp/van_marle_wr_orthogonal_n20000_low_20261017_mac_farm/` with initial VTU, one rank and empty stderr. Validate six VTUs/WR flux/outer stability and compare GMC1000/2000 profiles at exact age before interpreting shell quality.

## n_ref3000 GMC1200 age gate and GMC900 bracket (2026-10-17 08:37 UTC)

Pauley404-02's n_ref3000/GMC1200 direct-WR 0.27-Myr continuation finished normally, was pulled non-overwriting to `results/dense_gmc_wr_orthogonal_n3000_gmc1200_027myr_mac_4096_20261017/Pauley404-02/n03000b1200/wind/`, and passed independent 15-VTU/exact-age/finite-GMC/initial-mass-pressure/outer-field/2000-km/s/9.99046e-6-Msun/yr-flux validation. New corrected plots under that host's `plots_n03000b1200_wind_v1/` were inspected. Peak 4.949735 pc, FWHM 263.42 native elements, contrast 2.386 and FWHM/radius 0.208: the 0.27-Myr profile fails contrast >=3, unlike its 0.1-Myr precursor. Runtime 6454.623 s. This is not a confirmed sharp shell.

An opt-in n_ref3000/GMC900 bracket was generated at `dense_gmc_inputs_wr_orthogonal_n3000_transition_mac_4096_20261017/manifest.csv` by varying only GMC density from the matched base. On freed Mac02 its guarded static atmosphere passed and was pulled to `results/dense_gmc_wr_orthogonal_n3000_transition_mac_4096_20261017/Pauley404-02/n03000b0900/atmosphere/`: two VTUs/exact 0.1 Myr, 24 initial H II elements, initial mass/pressure and stable outer fields. The matching guarded 0.1-Myr WR wind advances in separate `/private/tmp/van_marle_wr_orthogonal_n3000_transition_20261017_mac_farm/` with one rank, initial VTU and empty stderr. Validate six VTUs/WR flux/outer fields, then compare GMC600/900/1200 native profiles and shell quality at matched age. Direct WR is not a preconditioned late-WR/GRB-wall or convergence result.

## n_ref5000 GMC1500 transition (2026-10-17 07:42 UTC)

Keohane2's n_ref5000/GMC1500 0.1-Myr direct-WR wind finished normally
(exit 0, one marker, empty stderr, six VTUs), was pulled without overwrite
to `results/dense_gmc_wr_orthogonal_transition_vm_4096_20261017/n05000b1500/wind/`
and independently passed finite-GMC/exact-age/initial mass-pressure,
2000-km/s WR speed, 9.99047e-6 Msun/yr inner flux and stable outer fields.
Corrected new CSV/PNG inspection gives density-excess peak 1.453954 pc,
FWHM 123.01 native elements, contrast 4.33 and FWHM/radius 0.216. This
passes the stated short-shell gates but is visibly broadening; the GMC2000
case failed sharp-shell gates. Measured AMRVAC runtime was 5098.332 s.

A distinct wind-only 0.27-Myr continuation in
`dense_gmc_inputs_wr_orthogonal_transition_027myr_vm_4096_20261017/`
uses a cloud/mesh base byte-identical to the validated short. Its 2.7x
runtime projection leaves >20% of the 36000-s guard. Pinned input,
binary, source and runner hashes, free-host, empty-output and resource
checks passed; it now advances on Keohane2 in separate
`/tmp/van_marle_wr_orthogonal_transition_027myr_20261017_farm/` with an
initial VTU, one rank and empty stderr. Validate 15 VTUs/exact 0.27 Myr,
WR flux, outer fields and profile shape at completion. This is a direct-WR
temporal test, not a late-WR/GRB wall or convergence claim.

## n_ref3000 wide-GMC Mac results (2026-10-17 06:46 UTC)

Pauley404-01/02 n_ref3000/GMC100 and GMC1200 0.1-Myr direct-WR winds
finished normally (guard 0, one marker, empty stderr, six VTUs), were
pulled without overwrite to separate
`results/dense_gmc_wr_orthogonal_n3000_wide_mac_4096_20261017/<host>/<tag>/wind/`
trees, and passed independent exact-age/finite-GMC/initial mass-pressure,
2000-km/s wind, 1e-5 Msun/yr flux and outer-field validation. Corrected
one-case CSV/PNGs were inspected. GMC100 peaks at 1.846081 pc with 4.45
native FWHM elements and contrast 153.65: it fails the >=5-element width
gate. GMC1200 peaks at 2.116557 pc with 105.78 elements and contrast 4.97;
its width/radius is 0.141, so it passes the stated short-shell gates.
Measured AMRVAC runtimes were 2403.361 and 2400.427 s. Neither profile
is a preconditioned late-WR or GRB wall.

Mac01 now tests GMC100 at 8192 cells from
`dense_gmc_inputs_wr_orthogonal_n3000_gmc100_mac_8192_20261017/` in
`/private/tmp/van_marle_wr_orthogonal_n3000_gmc100_8192_20261017_mac_farm/`.
Only mesh parameters changed from the matched 4096 base. Its guarded
no-wind atmosphere exited 0/one marker/empty stderr, was pulled
non-overwriting to `results/dense_gmc_wr_orthogonal_n3000_gmc100_mac_8192_20261017/Pauley404-01/n03000b0100/atmosphere/`
and passed independent two-VTU/0.1-Myr validation: 49 initial H II
elements, initial mass/pressure and outer stability. Matching guarded
0.1-Myr 8192-cell WR wind now advances on Mac01. Mac02 runs GMC1200 0.27-Myr
wind-only continuation from
`dense_gmc_inputs_wr_orthogonal_n3000_gmc1200_027myr_mac_4096_20261017/`
in `/private/tmp/van_marle_wr_orthogonal_n3000_gmc1200_027myr_20261017_mac_farm/`.
Its cloud/mesh base is byte-identical to the passed 0.1-Myr case and its
2.7x measured-runtime projection leaves >20% of the 36000-s guard.
Both new winds had pinned binary/source/runner/input hashes, one active
rank, initial VTU and empty stderr at launch. They are distinct mesh and
temporal questions, not a convergence or late-WR claim.

## WR shell-quality transitions (2026-10-17 06:02 UTC)

Keohane1/2 n_ref5000/GMC125 and GMC2000 0.1-Myr direct-WR winds
finished normally with exit 0, one marker, empty stderr and six VTUs.
Non-overwriting pulls to
`results/dense_gmc_wr_orthogonal_wide_vm_4096_20261017/<tag>/wind/`
passed independent finite-GMC/exact-age/initial mass-pressure/outer-field,
2000-km/s WR and ~9.9904e-6 Msun/yr inner-flux validation. Corrected
new one-case CSV/PNGs were visually inspected. Peaks 1.510442/1.408091 pc,
native FWHM 5.67/193.16 elements and contrasts 82.87/2.84 show a narrow
GMC125 shell but broad low-contrast GMC2000 enhancement. GMC2000 fails
both contrast>=3 and width/radius<=0.25 gates; it is not a confirmed sharp
shell. Measured short times 5090.408/5120.007 s. Keohane1's validated
GMC125 base was byte-matched to a distinct wind-only 0.27-Myr input in
`dense_gmc_inputs_wr_orthogonal_wide_027myr_vm_4096_20261017/` and its
guarded 36000-s continuation now advances in separate
`/tmp/van_marle_wr_orthogonal_wide_027myr_20261017_farm/`.

Keohane2 tests the sharp-shell transition between the passed GMC1000
and failed GMC2000 cases at n_ref5000/GMC1500. The new opt-in
`--orthogonal-wr-vm-n5000-transition` input set in
`dense_gmc_inputs_wr_orthogonal_transition_vm_4096_20261017/` changes
only `n_bg_cm3` from the matched cloud/mesh base. Its guarded no-wind
atmosphere finished normally, was pulled without overwrite to
`results/dense_gmc_wr_orthogonal_transition_vm_4096_20261017/n05000b1500/atmosphere/`
and independently passed two-VTU/0.1-Myr initial mass/pressure, 16 H II
elements and outer stability checks. Its distinct 0.1-Myr direct-WR wind
now advances under a 28800-s guard in separate
`/tmp/van_marle_wr_orthogonal_transition_20261017_farm/`.

Pauley404-01/02 n_ref3000/GMC150 and GMC600 0.27-Myr direct-WR
continuations finished normally, were pulled without overwrite into
`results/dense_gmc_wr_orthogonal_n3000_027myr_mac_4096_20261017/<host>/<tag>/wind/`,
passed independent 15-VTU/exact-age/inner-WR-flux/outer-field checks and
were plotted in new one-case dirs. Visually inspected peaks 5.944745 and
5.154883 pc have FWHM 19.13/111.37 elements and contrasts 37.25/5.53;
measured AMRVAC times were 6483.533/6452.958 s. These are direct-WR
temporal profiles, not preconditioned late-WR or GRB walls.

Freed Macs now test n_ref3000/GMC100 and GMC1200 to bound the narrow
and broad sides of the shell-quality regime. The new opt-in
`--orthogonal-wr-mac-n3000-wide` input set is in
`dense_gmc_inputs_wr_orthogonal_n3000_wide_mac_4096_20261017/`; base
diffs from matching GMC150/600 cases change only `n_bg_cm3`. Both new
guarded atmospheres finished normally, were pulled non-overwriting to
`results/dense_gmc_wr_orthogonal_n3000_wide_mac_4096_20261017/<host>/<tag>/atmosphere/`
and passed independent two-VTU/0.1-Myr, 24-H-II-element initial
mass/pressure and outer-field checks. Their distinct 0.1-Myr direct-WR
winds now advance one per Mac under 28800-s guards in
`/private/tmp/van_marle_wr_orthogonal_n3000_wide_20261017_mac_farm/`.
Pauley404-03 and Keohane3/4 retain their previously launched distinct
jobs; no duplicate, full-lifetime, cooling or conduction case was run.

## Dense GMC brackets cleared (2026-10-17 05:10 UTC)

Keohane3/4 n_ref10000/GMC500 and GMC2000 no-wind atmospheres in
`/tmp/van_marle_wr_orthogonal_20261016_farm/` finished with guarded exit 0,
one normal marker, empty stderr and two VTUs. Non-overwriting pulls to
`results/dense_gmc_wr_orthogonal_4096_20261016/<tag>/atmosphere/` passed
independent finite-GMC validation at 0.1 Myr: 49 initial H II elements,
initial cloud masses 2.610e5/1.001e6 Msun, pressure/density and outer-field
checks. Density drift was 1.76%/1.74% and maximum speed 0.573/0.567 km/s.
After pinned input hashes, no-output and idle-host checks, matching distinct
0.1-Myr direct-WR winds started under 28800-s guards, one per host. Initial
VTUs, empty stderr and one rank were checked. Next: six-VTU endpoint,
inner WR mass flux and native shell-quality validation. Neither run is a
preconditioned late-WR or GRB-wall calibration.

## Dense direct-WR VM shorts (2026-10-17 04:56 UTC)

Keohane3/4 n_ref10000/GMC1000 and n_ref20000/GMC2000 0.1-Myr
direct-WR winds finished with guarded exit 0, one normal marker, empty
stderr and six VTUs. Non-overwriting pulls to
`results/dense_gmc_wr_only_4096_20261016/<tag>/wind/` passed independent
finite-GMC validation: exact endpoint, initial mass/pressure, stable outer
fields, 2000-km/s wind and ~1.0392e-5 Msun/yr inner flux. Corrected
one-case CSV/PNGs in new `plots_<tag>_wind_v1/` directories were visually
inspected. Peaks are 1.228502/0.857513 pc, native FWHM 71.59/183.84
elements and contrasts 8.82/3.24. The n20000 width/radius is 0.268 and
fails the <=0.25 sharp-shell gate; do not call it a confirmed sharp wall.
Measured VM times 20676.586/20367.929 s project beyond the 28800-s guard
for 0.27 Myr, so no dense continuation was launched.

On the freed hosts, distinct n_ref10000/GMC500 and GMC2000 guarded
no-wind atmospheres are now active in
`/tmp/van_marle_wr_orthogonal_20261016_farm/`. Their staged bases match
the manifest hashes and pinned binary/source/runner; no prior output or
run record existed. Each had an initial VTU, empty stderr and one rank.
Validate two VTUs, exact 0.1-Myr endpoint, initial H II sampling,
mass/pressure and outer stability before considering its matching wind.
The existing direct-WR short profiles do not establish preconditioned
late-WR/GRB walls or convergence.

## VM continuations and wide GMC brackets (2026-10-17 04:31 UTC)

Keohane1/2 direct-WR 0.27-Myr n_ref3000/GMC300 and n_ref5000/GMC500
continuations finished with guarded exit 0, one normal marker, empty stderr
and 15 VTUs. Non-overwriting pulls to
`results/dense_gmc_wr_only_027myr_4096_20261016/<tag>/wind/` passed
independent finite-GMC validation including exact 0.27-Myr age, initial
mass/pressure, 2000-km/s wind, ~9.99046e-6 Msun/yr flux and outer
stability. Corrected one-case CSV/PNGs in new `plots_<tag>_wind_v1/` dirs
were inspected. Peaks 5.511574/4.725719 pc, native FWHM 45.94/92.55
elements and contrasts 14.29/8.43 match the validated Mac continuations
at reported precision. VM AMRVAC times 13703.497/13646.443 s versus Mac
6553.829/6490.870 s, about 2.1 times longer. This is a platform metric
comparison, not bitwise identity or mesh convergence.

On freed Keohane1/2, distinct n_ref5000/GMC125 and GMC2000 no-wind
atmospheres in `/tmp/van_marle_wr_orthogonal_wide_20261017_farm/`
finished with exit 0, one marker, empty stderr and two VTUs. Separate
`rsync --ignore-existing` pulls to
`results/dense_gmc_wr_orthogonal_wide_vm_4096_20261017/<tag>/atmosphere/`
passed independent static finite-GMC validation: 16 initial H II elements,
cloud excess masses 7.219e4/9.973e5 Msun, density drift 0.306%/1.035%,
maximum speed <0.077 km/s and stable outer pressure/density. The matching
distinct 0.1-Myr direct-WR winds now advance under 28800-s guards, one
per host, with initial VTU, empty stderr, rank CPU and resource checks.
Next: validate their six-VTU endpoints and shell quality. The dense GMC2000
case may give only a broad enhancement; do not label one a confirmed wall
without native width/contrast checks. Cooling/conduction and 4.77-Myr
fulls remain off/held; staged VM GMC250/1000 duplicates remain held.

## n_ref3000 direct-WR brackets and continuation (2026-10-17 04:11 UTC)

Pauley404-01/02 n_ref3000/GMC150 and GMC600 0.1-Myr direct-WR winds
finished with guarded exit 0, one AMRVAC marker, empty stderr and six VTUs.
Non-overwriting pulls into
`results/dense_gmc_wr_orthogonal_n3000_mac_4096_20261017/<host>/<tag>/wind/`
passed independent `validate_cloud_mass.py --finite-gmc
--expected-mdot-msun-yr 1e-5`: exact age, all finite-positive fields,
initial mass/pressure, stable outer fields, ~2000-km/s wind and measured
inner flux 9.99044e-6/9.99045e-6 Msun/yr. Corrected one-case CSV/PNGs in
each host's new `plots_<tag>_wind_v1/` were inspected. At exact 0.1 Myr
the density-excess peaks are 1.851499/1.875933 pc, native FWHM
5.65/44.03 elements, contrast 119.96/14.65, fractional width
0.0083/0.0638, and 24 initial H II elements. Both pass the short-shell
gates, though GMC150 is only just over the five-element width threshold.
As at n_ref5000, GMC density changes radial profile width more than peak
radius. These are not preconditioned late-WR or GRB walls.

Measured AMRVAC times were 2410.386/2401.069 s; 2.7 times each is far
below 80% of the 36000-s continuation guard. A distinct temporal test
was generated with `generate_dense_gmc_scan.py --wr-only
--orthogonal-wr-mac-n3000 --wind-only --wr-duration-myr 0.27 --cells 4096
--suffix _wrorthn3000_0274096`, with exact inputs in
`dense_gmc_inputs_wr_orthogonal_n3000_027myr_mac_4096_20261017/manifest.csv`.
Both new bases are byte-identical to the corresponding validated short
cloud/mesh inputs. Hash-matched pinned arm64 executable/source/runner and
new inputs were staged in separate, initially empty
`/private/tmp/van_marle_wr_orthogonal_n3000_027myr_20261017_mac_farm/`
trees. After idle/output checks, guarded 0.27-Myr winds were launched one
per Mac; both began with one VTU, empty stderr, 100% CPU and ample disk/memory.
Next: require 15 VTUs and independent exact-endpoint/WR-flux/outer-field
validation, then compare matched-age profile evolution. No cooling,
conduction, 4.77-Myr full or duplicate case was launched.

## Direct-WR orthogonal brackets (2026-10-17 03:18 UTC)

Pauley404-01/02 n_ref5000/GMC250 and GMC1000 0.1-Myr direct-WR winds
finished with guard exit 0, one normal AMRVAC marker, empty stderr and six
VTUs each. Separate `rsync --ignore-existing` pulls into
`results/dense_gmc_wr_orthogonal_mac_4096_20261017/<host>/<tag>/wind/`
passed independent `validate_cloud_mass.py --finite-gmc
--expected-mdot-msun-yr 1e-5`: exact endpoint, 16 initial H II elements,
finite-positive fields, initial mass/pressure, 2000-km/s injection, measured
inner flux 9.99044e-6/9.99052e-6 Msun/yr, and stable outer fields. New
one-case corrected CSV/PNGs are in each host's `plots_<tag>_wind_v1/`.
Density-excess peaks are 1.518183/1.492417 pc, native FWHM 9.36/63.35
elements, contrasts 51.73/8.10, and fractional widths 0.016/0.109;
both meet the short-shell quality gates. The density profile PNGs were
inspected. The strong width change despite a small peak-radius shift is
important for a radius-plus-profile model; these are direct-WR 0.1-Myr
snapshots, not preconditioned late-WR or GRB walls.

Once each Mac was free, its distinct n_ref3000/GMC150 or GMC600 no-wind
atmosphere in `/private/tmp/van_marle_wr_orthogonal_n3000_20261017_mac_farm/`
completed with exit 0, one marker, empty stderr and two VTUs. Non-overwriting
pulls to `results/dense_gmc_wr_orthogonal_n3000_mac_4096_20261017/<host>/<tag>/atmosphere/`
passed independent finite-GMC validation: 24 initial H II elements,
0.316%/0.435% density drift, and outer stability. Both matching 0.1-Myr
direct-WR winds were launched under 28800-s guards after idle/output checks.
Remaining: validate their six-VTU endpoints and shell profiles, and follow
the advancing Keohane1-4 and Mac03 jobs. Do not launch held duplicate VM
GMC250/1000 cases or infer convergence from these short tests.

## Mac ambient-density brackets (2026-10-17 UTC)

Jonathan approved purposeful experiments on idle Pauley404-01/02. The existing
`n_ref=5000 cm^-3` GMC-background brackets at 250 and 1000 cm^-3 were copied
byte-for-byte into `dense_gmc_inputs_wr_orthogonal_mac_4096_20261017/`, whose
manifest assigns the first to Mac01 and the second to Mac02. Their previously
staged Keohane1/2 copies are **held to avoid duplicate cases**. The only base
parameter changed from the matched 5000/500 case is `n_bg_cm3`; pinned
arm64 binary and source hashes were verified unchanged.

The separate 7200-s no-wind atmosphere guards exited 0 with one AMRVAC finish
marker, empty stderr and two VTUs each. Non-overwriting pulls into
`results/dense_gmc_wr_orthogonal_mac_4096_20261017/<host>/<tag>/atmosphere/`
passed independent finite-GMC validation at 0.1 Myr: 16 initial H II elements
each, density drift 0.305%/0.653%, maximum speed <0.077 km/s, and cloud excess
mass 1.338e5/5.037e5 Msun. With hosts idle and outputs absent, matching
0.1-Myr direct-WR winds were launched under 28800-s guards in
`/private/tmp/van_marle_wr_orthogonal_20261017_mac_farm/`, one per Mac. Initial
rank ~100% CPU, empty stderr, one saved VTU, and disk checks passed. On
completion pull/validate six VTUs and the 1e-5 Msun/yr WR flux into distinct
`wind/` trees; compare native shell metrics at fixed core density and wind.
No late-WR, convergence, or GRB-wall claim follows from these short tests.

Last touched 2026-10-17 UTC: copied six pinned input files and added the Mac
host manifest; ran SHA-256/input-diff and idle/disk checks, guarded static
checks, non-overwriting rsync, and independent `validate_cloud_mass.py`
validation; launched two guarded winds. Remaining: complete/validate winds,
compare GMC-density effect, and keep the Keohane duplicate copies held.

The next **unlaunched** Mac pair is staged in
`dense_gmc_inputs_wr_orthogonal_n3000_mac_4096_20261017/`: n_ref3000 with
GMC150 on Mac01 and GMC600 on Mac02. `generate_dense_gmc_scan.py
--wr-only --orthogonal-wr-mac-n3000 --cells 4096` generated these files;
comparison with the validated 3000/300 base confirms that only `n_bg_cm3`
changes. Binary, source, runner and inputs are hash-matched in separate
`/private/tmp/van_marle_wr_orthogonal_n3000_20261017_mac_farm/` trees, with
empty outputs. Launch each no-wind atmosphere only after its host's active
5000-density wind finishes and passes validation; launch its wind only after
the new atmosphere passes the static/initial H II gates. These are a second
core-density anchor, not an automatic retry or production fit.

Keohane1/2's next **unlaunched** pair is separately staged in
`dense_gmc_inputs_wr_orthogonal_wide_vm_4096_20261017/`: n_ref5000 with
GMC125 and GMC2000 cm^-3. The opt-in generator flag
`--wr-only --orthogonal-wr-vm-n5000-wide --cells 4096` produced 0.1-Myr
atmosphere/wind inputs; diffs against the 5000/500 base show only `n_bg_cm3`
changes. Inputs, pinned Linux binary/source and guarded runner are SHA-matched
on Keohane1/2 in empty `/tmp/van_marle_wr_orthogonal_wide_20261017_farm/`
trees. This widens the ambient-density lever arm without repeating the Mac
250/1000 cases. When each VM's current 0.27-Myr continuation finishes and
validates, launch its new static atmosphere if the host is idle; only a
validated two-VTU static profile clears the matching short WR wind. The
2000 cm^-3 case may fail shell contrast, which would be a useful bound rather
than a calibrated shell radius.

## Parameterized radius experiment (2026-10-16)

Mac continuation and third short milestone (2026-10-17 UTC): Pauley404-01/02
direct-WR 0.27-Myr cases completed with guarded exit 0, one normal marker,
empty stderr, and 15 VTUs. Non-overwriting pulls into separate
`results/dense_gmc_wr_only_027myr_mac_4096_20261016/<host>/<tag>/wind/`
trees passed independent finite-GMC validation, including 2000-km/s injection,
1e-5 Msun/yr mass flux, initial/outer fields, and exact endpoint. Corrected
one-case CSV/PNGs are in each host's `plots_<tag>_wind_v1/`. At 0.27 Myr,
n3000/300 has peak 5.511574 pc, native FWHM 45.94 elements, contrast 14.29;
n5000/500 has 4.725719 pc, 92.55 elements, contrast 8.43. Both remain within
the 20-pc domain and pass the four short-shell gates, though the n5000 profile
has a broadened plateau. AMRVAC times were 6553.829/6490.870 s. These are
direct WR into an initial cloud, not preconditioned late-WR bubbles.
Pauley404-03 n10000/1000 direct-WR 0.1-Myr case also finished normally and
passed the same independent six-VTU validation. Its peak is 1.228502 pc,
FWHM 71.59 elements, contrast 8.82, with 49 initial H II elements; plot in
`results/dense_gmc_wr_only_mac_4096_20261016/Pauley404-03/plots_n10000b1000_wind_v1/`.
Its AMRVAC time was 9583.918 s; 2.7 times that is below 80% of the 36000-s
guard. A distinct 0.27-Myr continuation was launched on the now-idle Mac03
under that guard; rank, empty stderr and disk were checked. Mac01/02 are idle
after their completed continuations; no unvalidated duplicate or filler was
started. Three quality-passing, same-age Mac direct-WR short cases support a
separate exploratory fit at
`results/dense_gmc_parameterization_20261016/wr_direct_0p1myr_provisional_mac_v1/`:
R_pc = 1.51579 (n_ref / 5313.29 cm^-3)^(-0.34652), valid only n_ref
3000-10000 cm^-3 and R 1.2285-1.8705 pc; maximum leave-one-out error is
7.27%. The PNG was visually inspected. This is not a late-WR or GRB-wall
calibration and must not be mixed with the early-MS family.

VM short-run milestone (2026-10-17 UTC): Keohane1/2 n3000/300 and n5000/500
0.1-Myr direct-WR winds completed with guarded exit 0, one normal AMRVAC
marker, empty stderr and six VTUs. Separate non-overwriting pulls to
`results/dense_gmc_wr_only_4096_20261016/<tag>/wind/` passed independent
finite-GMC validation including 2000-km/s injection and 1e-5 Msun/yr
mass-loss (measured 9.99045e-6/9.99049e-6). Corrected one-case CSV/PNGs are
in `plots_n03000b0300_wind_v1/` and `plots_n05000b0500_wind_v1/` under that
VM results root. Both density profiles show sharp, boundary-clear shells.
VM peaks, FWHM widths, contrasts, and initial H II element counts match the
Mac01/02 values below exactly at the reported precision: 1.870496/1.515602
pc, 15.019/21.701 elements, 45.864/22.796 contrast, 24/16 H II elements.
The VTU files are not byte-identical, so this is a metric-level platform
comparison, not bitwise identity or mesh convergence. Measured AMRVAC times
were 5071.016/5084.882 s, versus Mac 2401.768/2396.729 s, about 2.11x
faster on these Macs. With 2.7x VM runtime projections below 80% of the
36000-s guard and hosts idle, distinct 0.27-Myr wind-only continuations
were launched on Keohane1/2 in `/tmp/van_marle_wr_only_027myr_20261016_farm/`.
At that milestone Keohane3/4 and Mac03 short winds, and Mac01/02 continuations, were advancing; see the newer Mac update above.
Remaining: validate those runs, assess same-age platform profiles at more
densities, and keep WR-only separate from physically preconditioned late WR.

Mac short-run milestone (2026-10-16): Pauley404-01 n3000/300 and
Pauley404-02 n5000/500 direct-WR 0.1-Myr winds finished with guarded exit 0,
one normal AMRVAC marker, empty stderr, and six VTUs. Separate non-overwriting
pulls and independent finite-GMC validation passed initial mass/pressure,
outer density/pressure, 2000-km/s WR injection, and inner mass flux
9.99045e-6/9.99049e-6 Msun/yr against 1e-5. Corrected CSV/PNGs are in
`results/dense_gmc_wr_only_mac_4096_20261016/Pauley404-01/plots_n03000b0300_wind_v1/`
and the corresponding `Pauley404-02/plots_n05000b0500_wind_v1/` directory.
Peaks are 1.870496/1.515602 pc, FWHM 15.019/21.701 native elements,
and contrasts 45.864/22.796; both pass the four short-shell quality gates.
Their measured AMRVAC times are 2401.768/2396.729 s. After confirming host
idle state and a 2.7x runtime projection below 80% of the 36000-s guard,
the distinct 0.27-Myr continuations were launched on Pauley404-01/02 in
`/private/tmp/van_marle_wr_only_027myr_20261016_mac_farm/`, one per host.
Matched early-MS peaks at 0.1 Myr are 1.181042/0.952368 pc; the direct-WR
shortcut is not equivalent to a physically preconditioned late-WR bubble.
At that milestone Pauley404-03 and all four VM short winds remained advancing; see the newer VM update above. Remaining: validate
continuations and other shorts, then compare matched Mac/VM profiles and times.

Weekend continuation is staged; Pauley404-01/02/03 and Keohane1/2 have launched so far. `generate_dense_gmc_scan.py
--wr-only --wr-duration-myr 0.27 --wind-only` generated
`dense_gmc_inputs_wr_only_027myr_4096_20261016/`: four direct-WR wind-only
cases covering the 0.27-Myr WR interval with 15 VTUs and a 36,000-s guard.
Their base files are byte-identical to validated 0.1-Myr bases. Separate
scratch with the same pinned binary/source is on all four Keohane hosts
and three Pauley hosts. Require the matched short wind to pass, inspect
its shell/profile, and project measured runtime x2.7 with >=20% guard
margin before launching a host. `--wr-only --orthogonal-wr` generated
`dense_gmc_inputs_wr_orthogonal_4096_20261016/`: n_ref5000/GMC250,1000
and n_ref10000/GMC500,2000 cases, each with a 0.1-Myr no-wind atmosphere
and WR wind. Inputs are staged on the four Keohane hosts in separate
`/tmp/van_marle_wr_orthogonal_20261016_farm/` trees, but no jobs were
launched. Their only base-file change from the matched 1:10 cases is
`n_bg_cm3`; each atmosphere must pass before its wind. These are bounded
experiments for a second density parameter, not a production calibration.
After the final validated products are assembled, publish/share the
reproducible package for Ansh from the correct project destination; no
push or share of this still-running campaign has happened yet.

`fit_dense_gmc_radius_family.py` reads corrected native `shell_metrics.csv`
files, requires a common mesh tag, fixed wind age/cloud geometry and a
fixed GMC-to-core density ratio, then screens shells for H II sampling,
native FWHM, contrast and fractional width. Its first deliberately
provisional early-MS product is
`results/dense_gmc_parameterization_20261016/ms_0p1myr_provisional_v2/`:
screened points CSV, coefficients/inverse formula/limits JSON, and a
visually inspected PNG. Three of six 4096-cell cases pass. The fitted
exponent is -0.3350, with 0.9596 pc at n_ref=5313 cm^-3, over only
n_ref=3000-10000 cm^-3 (R=0.786-1.181 pc). Leave-one-out errors reach
9.5%; this is **not** a calibrated GRB wall or late-WR result, and mesh
convergence is not established. Since all these cases enforce
n_GMC=0.1*n_ref, no independent GMC-density coefficient is identifiable.
Next experiment after the active WR-only checks: vary GMC density at fixed
core density, preserving wind and geometry, with separate no-wind
atmosphere validation before each wind. A preconditioned WR bubble and
resolution tests remain necessary before fitting the observed GRB scale.

Command for the current exploratory product (use a new output path on rerun):

```bash
/Users/jkeohane/GRBs/.venv/bin/python fit_dense_gmc_radius_family.py OUTPUT \
  results/dense_gmc_4096_20261015/plots_wind_low4096_v2/shell_metrics.csv \
  results/dense_gmc_4096_20261015/plots_wind_dense4096_v1/shell_metrics.csv \
  results/dense_gmc_intermediate4096_20261016/plots_wind_intermediate_all_v1/shell_metrics.csv \
  --label 'Three-phase wind: early MS' --mesh-tag c4096
```

Last touched: added fit script, ran it to distinct v1/v2 exploratory
products (v2 requires mesh tag), visually checked the plot, and recorded
quality/reproducibility limits. Remaining: validated WR-only products,
independent ambient-density scan, preconditioned WR comparison, mesh check.

## WR-only shortcut and platform test (2026-10-16)

`generate_dense_gmc_scan.py --wr-only --cells 4096 --suffix _wr4096`
created `dense_gmc_inputs_wr_only_4096_20261016/` with four distinct
0.1-Myr cases and no staged full runs. The base files are byte-identical
to matched n3000/5000/10000/20000 three-phase short controls. New
`wind_phase_age_offset_myr` defaults to zero and is 4.5 only for the
WR-wind stage, selecting the existing 2000-km/s WR phase and its mass-loss
rate at t=0 while leaving the finite-GMC profile, fixed enclosed-mass
field, ionization prescription, cooling-off, and conduction-off settings
unchanged. This is a WR wind directly into the initial cloud, **not**
a WR wind entering an MS/RSG-shaped cavity; compare short-age profiles
as a shortcut diagnostic, not as evidence of physical equivalence.

Pinned AMRVAC v3.1 `244c677f` builds use source SHA-256
`f77682de7f36cf94709c100a737d1142c56312b53a8fbb6ee2532dd740df0b35`.
VM binary SHA-256 is `6220745f8bd78f536bcdeec7cda45762e1c032d3d20e383c8884044981350604`;
Mac arm64 binary SHA-256 is `f9db83bc52e1a987b4441dd6884bd64667708f1f2054009d5b54f30ab4838a3f`.
VM scratch: `/tmp/van_marle_wr_only_20261016_farm/` on each Keohane host;
Mac scratch: `/private/tmp/van_marle_wr_only_20261016_mac_farm/` on each
Pauley host. `run_cloud_mass_case_mac.py` supplies a separate serial,
process-group-guarded launcher because macOS lacks GNU `timeout`.
Pauley404-03 uses the Mac01-built binary because local Xcode licensing
prevents a build; no system configuration was changed.

Last touched: all four VM no-wind atmospheres and all three Mac no-wind
atmospheres passed independent two-VTU, 0.1-Myr finite-GMC validation;
their separate non-overwriting results are in
`results/dense_gmc_wr_only_4096_20261016/<tag>/atmosphere/` and
`results/dense_gmc_wr_only_mac_4096_20261016/<host>/<tag>/atmosphere/`.
All four VM WR winds and all three Mac WR winds are active under 28,800-s
guards, one per host. Commands included `py_compile`, generator/base-file `cmp`, pinned
`make`, SHA-256 checks, guarded launches, `rsync --ignore-existing`, and
`validate_cloud_mass.py`. Its new opt-in `--expected-mdot-msun-yr` gate
uses three distinct innermost saved samples; a prior MS wind passed at
`1e-6` (measured `9.9909e-7`), and the WR checks must pass at `1e-5`.
The quiet heartbeat was updated/reactivated for this separate campaign.
Remaining: validate all winds including WR mass flux; compare matched-age
profiles and measured runtimes. No full, cooling, or conduction case
was started, and no convergence or late-WR-wall result is claimed.

## Finite-GMC dense-core scan (2026-10-16, short checks complete; fulls held)

Last touched 2026-10-16: Keohane4's n20000/2000 4096-cell wind completed
with guarded exit 0, one normal marker, empty stderr, six VTUs, exact
0.1-Myr endpoint, and no active rank. A non-overwriting pull into
`results/dense_gmc_intermediate4096_20261016/n20000b2000/wind/` passed
independent `validate_cloud_mass.py --finite-gmc` saved-field, initial
mass/pressure, inner 2000-km/s wind, and outer density/pressure checks.
The new two-case CSV/PNGs in `plots_wind_intermediate_all_v1/` were visually
checked. The n20000 peak is 0.50980 pc, FWHM 246.81 native elements, and
contrast 2.07, with 30 initial H II elements. Its broad profile is not a
confirmed sharp swept shell. At matched 0.1 Myr the 4096-cell sequence
n5000/n10000/n20000/n30000 peaks at 0.952/0.786/0.510/0.325 pc, but
the n20000/n30000 features are broad, and no radius law or convergence is
claimed. At that scan's completion the Keohane hosts were idle; the newer
WR-only shortcut runs are listed above. Commands: remote guard/resource check, `rsync --ignore-existing`,
validator, corrected plotter, CSV/PNG inspection. Remaining: choose a
full-lifetime mesh/runtime and physical model; no 4.77-Myr full, cooling,
or conduction case was launched. The quiet heartbeat is paused.

Current short-run state: all four 2048-cell and all four 4096-cell winds
passed independent validation. `plot_dense_gmc_scan.py`
now removes duplicate AMRVAC block-boundary vertices before using a local
cell width; the current products are `results/dense_gmc_20261015/plots_wind_all2048_v2/`
and `results/dense_gmc_4096_20261015/plots_wind_low4096_v2/` plus
`results/dense_gmc_4096_20261015/plots_wind_dense4096_v1/`.
The earlier v1 products are preserved but superseded. Ordered 2048
density-excess peaks are 1.765/1.108/0.907/0.416 pc; native FWHM counts
are 3.82/6.10/43.63/225.22. The earlier 6.16 reported for n10000 was
the contrast, not the width. At 4096, the low-density cases peak at
1.7653/1.1810 pc with FWHM 4.86/14.51 elements. The first still fails
the five-element gate; the second shifts 6.6% in peak radius. Neither
pair establishes convergence. The n30000 enhancement is broad and only
1.31 times its initial local density, not a confirmed sharp shell.
The 4096 dense cases peak at 0.7857/0.3254 pc with FWHM 98.70/488.88
native elements and contrast 4.94/1.21. Relative to 2048, their peak
radii shift 13.4%/21.7%. Numeric width does not make the broad n30000
feature a confirmed sharp swept shell.

The two low-density cases have a further **mesh-only** 8192-cell short
rung in `dense_gmc_inputs_8192_20261015/`. Its first-cell width is
0.001 pc; all wind, gravity, cloud, ionization, and cooling/conduction
settings are unchanged. Hash-matched executable/source and separate
inputs are staged on Keohane1/2 in each host's
`/tmp/van_marle_dense_gmc_8192_20261015_farm/`. Both guarded no-wind
atmospheres completed normally, passed independent finite-GMC validation
(128/49 initial H II elements, <0.17% density drift, <0.05 km/s speed),
and were pulled non-overwriting to separate
`results/dense_gmc_8192_20261015/<tag>/atmosphere/` trees. Distinct
0.1-Myr winds finished under 28,800-s guards, one per host, with exit 0,
one normal marker, empty stderr, and six finite-positive VTUs. Both were
pulled non-overwriting to separate `<tag>/wind/` trees and passed the
independent 0.1-Myr, inner-wind, and outer-boundary checks. Corrected
CSV/PNGs are in `results/dense_gmc_8192_20261015/plots_wind_low8192_v1/`.
Keohane3/4 finished their distinct 4096 dense short winds: exit 0, one normal marker,
empty stderr, six finite-positive VTUs, exact 0.1 Myr, expected inner wind,
and unchanged outer pressure/density. Their non-overwriting pulls and
independent validator passes are in separate `<tag>/wind/` result trees.
The 4.77-Myr fulls remain held for runtime/mesh decisions; no cooling or
conduction was enabled.

At matched 0.1 Myr, n1000 2048/4096/8192 shell peaks are
1.76502/1.76531/1.76411 pc, with native FWHM 3.82/4.86/9.74 elements
and contrasts 60.54/92.95/95.84. Only 8192 clears the five-element
width gate. n3000 peaks are 1.10773/1.18104/1.20202 pc, with FWHM
6.10/14.51/30.74 elements and contrasts 25.83/23.68/22.56. Its
4096-to-8192 peak moves 1.78%; neither a converged radius nor a WR
wall is established by these main-sequence short tests. Visually checked
profiles retain narrow peaks and clear domain margin. Keohane1/2 are
idle; no filler or full-lifetime run was launched.

To bracket the transition between the peaked n10000 profile and broad
n30000 enhancement, `generate_dense_gmc_scan.py --intermediate` optionally
stages n5000/500 and n20000/2000 cases; the four-case default is unchanged.
Distinct 4096-cell inputs are in `dense_gmc_inputs_intermediate4096_20261016/`.
Their only physical parameter changes from the neighboring cases are
the core/GMC densities; n5000 uses the same 0.01-pc inner boundary and
0.002-pc first width as the low-density 4096 checks, while n20000 uses
0.001/0.0005 pc as the dense checks. Identical hash-matched executable/source
are staged on Keohane3/4 under
`/tmp/van_marle_dense_gmc_intermediate4096_20261016_farm/`.
Both guarded no-wind atmospheres finished with exit 0, one normal marker,
empty stderr, and two finite-positive VTUs at 0.1 Myr. Independent
validation passed, including 16/30 initial H II elements, 0.38%/1.68%
maximum density drift, and <0.56 km/s maximum speed. They were pulled
non-overwriting to separate
`results/dense_gmc_intermediate4096_20261016/<tag>/atmosphere/` trees.
Distinct guarded 0.1-Myr winds started, one per Keohane3/4. Keohane3's
n5000/500 case finished with exit 0, one normal marker, empty stderr,
and six finite-positive VTUs at 0.1 Myr. It was pulled non-overwriting
to `results/dense_gmc_intermediate4096_20261016/n05000b0500/wind/`
and passed independent full-field, inner-wind, and outer-boundary
validation. One-case CSV/PNGs are in `plots_wind_n05000_v1/`. Native
density-excess peak is 0.95237 pc, FWHM 22.78 elements, contrast 12.41,
with 16 initial H II elements and clear domain margin. This is an early
main-sequence shell, not a WR wall or converged calibration. Keohane4's
n20000 completion and broad profile are documented above. Full-stage
files were generated for reproducibility but were neither staged on hosts
nor launched.

`generate_dense_gmc_scan.py` staged a new four-case, 20-pc/2048-cell
campaign in `dense_gmc_inputs_20261015/`; one case is assigned to each
Keohane VM. It keeps the 40-Msun MS/RSG/WR wind and illustrative photon
history below, but varies both the core density parameter at 1 pc and the
surrounding GMC density: 1000/100, 3000/300, 10000/1000, and 30000/3000
`cm^-3`. The smooth core has `r_flat=0.2 pc`, `p=1.8`, and a 2-pc tapered
edge; the GMC tapers at 15 pc to `n_H=10 cm^-3`. The two denser meshes begin
at 0.001 pc to sample their initial H II zones; the other two begin at
0.01 pc. The initial dust-free front spans 11-32 native elements. The
enclosed initial gas masses through 20 pc are about 5.7e4, 1.6e5, 5.1e5,
and 1.5e6 Msun, respectively.

The optional `finite_gmc_enabled` path in `mod_usr_cloud_mass.t` uses the
full gas density, rather than only its excess above an infinite background,
for the **initial** enclosed-mass gravitational field and hydrostatic
effective-support pressure. The field remains fixed while the gas moves.
This is still single-fluid 1D HD with a sharp photon-budget front, not dust
radiative transfer or evolved self-gravity. Cooling and conduction remain
off. The old cloud-mass inputs retain the original behavior by default.

The new executable SHA-256 is
`f2b3b521f245cc7d6cbfa7201407ee6685ab0b4dcd67f8f17a4bfc01a2beee9e`
and the modified source SHA-256 is
`8fccfc7cdba957bb302c5cac0957c88eb82d2f9f2ca39f2e4eecf90746adf8fb`.
Each host uses `/tmp/van_marle_dense_gmc_20261015_farm/` with distinct
case prefixes. All four 0.1-Myr no-wind atmospheres finished normally and
passed independent saved-field, density, initial pressure/mass, endpoint,
outer-boundary, and drift checks. Their maximum density drifts were 1.2%,
1.1%, 5.0%, and 4.4%; peak speeds were below 1 km/s. Four separate 0.1-Myr
wind cases were launched under 28,800-s guards. Static products were pulled
non-destructively to `results/dense_gmc_20261015/<tag>/atmosphere/`.

All four 2048-cell winds finished with guarded exit 0, one normal marker,
empty stderr, six finite-positive VTUs, and the 0.1-Myr endpoint. They
independently passed density, initial mass/pressure, 2000-km/s inner wind,
and outer-boundary checks. Combined CSV/two PNGs are in
`results/dense_gmc_20261015/plots_wind_all2048_v1/` (now superseded by v2); the first two also
have separate one-case products. In core/GMC density order, the 0.1-Myr
density-excess peak radii are 1.765, 1.108, 0.907, and 0.416 pc. Native
corrected FWHM widths are 3.82, 6.10, 43.63, and 225.22 cells. The first fails the
>=5-cell gate. The n30000b3000 feature is broad and only 1.31 times the
initial local density; its numeric FWHM pass is **not** evidence of a
well-defined swept shell or a WR wall. These are main-sequence-era 0.1-Myr
snapshots, not final bubble sizes.

The generator staged a distinct `dense_gmc_inputs_4096_20261015/` resolution
check (`--cells 4096 --case n01000b0100 --case n03000b0300 --suffix _c4096`).
A second non-overwriting `dense_gmc_inputs_4096_dense_20261015/` manifest
holds the n10000b1000/n30000b3000 checks with the same `_c4096` suffix.
Only the mesh changed: twice the cells and half the first-cell width,
with unchanged wind, gravity, cloud, ionization,
cooling-off, and conduction-off parameters. On Keohane1/2 the hash-matched
executable is in `/tmp/van_marle_dense_gmc_4096_20261015_farm/`; both
4096-cell no-wind atmospheres passed independent 0.1-Myr validation, with
0.32% density drift and <0.1 km/s peak speed. Their guarded 0.1-Myr winds
subsequently finished and passed independent validation. The Keohane3/4 hash-matched 4096 checks use the same
scratch-tree name on their own hosts; their no-wind atmospheres also passed
independent 0.1-Myr validation (1.76%/1.71% density drift, <0.6 km/s peak
speed), and their guarded 0.1-Myr winds subsequently completed and passed
independent finite-GMC validation. All 4096 atmosphere
products were pulled non-destructively to
`results/dense_gmc_4096_20261015/<tag>/atmosphere/`. No 4096 full was
launched. The ~20- and ~80-minute measured 2048 short runtimes project
beyond the 36,000-s full guard for every case, so full lifetimes remain held.

For each newly completed wind, pull to a distinct `<tag>/wind/` tree with
`rsync --ignore-existing`, then run `validate_cloud_mass.py` with
`--edge-width-pc 0.5 --domain-max-pc 20 --inner-pc <manifest value>
--n-bg <manifest value> --finite-gmc` and require six finite-positive VTUs,
exact 0.1 Myr, normal exit/marker, empty stderr, phase-appropriate inner
wind, and unchanged outer density/pressure. `plot_dense_gmc_scan.py` makes
new CSV/PNG products only for validated cases. Require initial H II >=10
cells and native shell FWHM >=5 cells; inspect whether the density-excess
peak is a physical shell and not an ionization or boundary artifact. Check
measured wall time and domain clearance before any 4.77-Myr full. The
generated `full` inputs are **staged, not launch clearance**; the 0.001-pc
inner meshes may be too slow for useful full runs. Never silently alter
physics or claim convergence from this four-point ladder.

This is a separate 1D spherical experiment. The original 10-year hydro-only
smoke, the 2000 cm^-3 4.77-Myr evolving-ionization pair, and the denser
matched sweep all ran and passed numerical validation. These are
**exploratory**, not a calibrated
photoionized, self-gravitating, cooling-cloud calculation. Do not use the
earlier 1.5 pc inner boundary: it exceeds the illustrative 0.86 pc initial
Strömgren radius at `n_H=1000 cm^-3`.

## Intended physics

- Use the 40 Msun wind phases in van Marle et al. (2012), Table 1: main
  sequence 0-4.3 Myr (`1e-6 Msun/yr`, `2000 km/s`), red supergiant
  4.3-4.5 Myr (`5e-5`, `15`), Wolf-Rayet 4.5-4.77 Myr (`1e-5`, `2000`).
  Stop before the supernova; do not add the 25 Msun star.
- The two new cases use the same wind and sharp-front photon-budget prescription;
  one has no gravity and the other has a static analytic acceleration chosen to
  balance the initial pressure profile. `n_H` denotes hydrogen nuclei, not H2.
- This is **not** self-gravity or the desired `G(M_star+M_gas(<r))/r^2` source.
  It omits the star's gravity and does not recompute gravitational mass after
  the wind rearranges gas. The photon luminosities are illustrative, not a
  verified stellar evolution track. The ionization algorithm is not radiative
  transfer and ignores dust. No CLOUDY cooling or thermal conduction is active.
- A future physically calibrated case still needs an agreed density/core scale,
  photon history, gravity source, molecular heating/cooling, and resolution tests.
  Do not interpret the near-identical gravity/no-gravity curves as convergence.

## Evolving-front finite-core pilot (2026-10-14)

`mod_usr_evolving.t` with `evolving_base.par` is a **serial**, 256-cell,
non-AMR, stretched 1D spherical run over 0.1-40 pc. The initial profile adapts
the Gaussian-core / inverse-square-envelope form used by Franco, Garcia-Segura
& Kurtz (2005): `n_H=2000 exp[-(r/1 pc)^2] cm^-3` to 1 pc, then
`(2000/e)(r/1 pc)^-2 cm^-3` to the 2 pc cloud edge. The exterior is held at
the edge density, about 184 cm^-3. The initial pressure is
`P=rho (0.72 km/s)^2`, representing **effective** cold-gas support, not a
literal single-temperature molecular equation of state. The gravity case
uses the matching fixed inward acceleration to 2 pc and zero beyond it.

The initial dust-free Strömgren integral over this actual density profile gives
0.627 pc for illustrative `Q_H=2e49 s^-1` and
`alpha_B=2.6e-13 cm^3 s^-1`; ionized cells start at 10,000 K. After each
hydro step the code balances old ionized atoms plus injected photons against
new ionized atoms and case-B recombinations in radial shells, moves a single
sharp front, and applies an ionized-pressure floor. The **illustrative**
photon history is `2e49 s^-1` in MS and WR, zero in RSG. Neutral, moderately
hot dense gas relaxes toward its effective support pressure on a local
recombination time. Shocked wind gas is not radiatively cooled. The source
has no ionization-advection tracer or dust opacity.

Both 4.77-Myr runs used the paper's 40 Msun MS (0-4.3 Myr), RSG
(4.3-4.5 Myr), and WR (4.5-4.77 Myr) wind rates/speeds. The built executable
was pinned AMRVAC v3.1 `244c677f` plus source SHA-256
`ca35e389b5a90f1d3c6c8cb33e7b5cc0e75506878077b1ffad1e8489ba94bfe8`.
The host scratch directory was
`/tmp/van_marle_ionized_core_evolving_20261014/` on Keohane1; the matching
gravity/no-gravity inputs and all small output files are here under
`results/evolving_20261014/`, with separate prefixes. No stopped BoOST run
or failed 2D van Marle case was relaunched.

Validation: the no-wind gravity atmosphere retained its core density within
0.22% for 0.1 Myr. Both 0.1-Myr wind pilots had six finite-positive VTUs,
correct 0.627 pc initial ionized zone, and unchanged outer boundary. Both
full runs completed normally with empty stderr, 49 finite-positive VTUs each,
and a verified 4.77-Myr endpoint. The saved inner flow confirms 15 km/s in
RSG at 4.4 Myr and 2000 km/s in WR at 4.6 Myr. The front reached the 2 pc
initial cloud edge by about 0.1 Myr, receded from about 23 pc to 21 pc in the
zero-photon RSG phase, and returned to about 24.9 pc by 4.77 Myr. At the
endpoint the density disturbance reaches about 26.4 pc, with the 30-40 pc
exterior unchanged. The two front tracks differ by less than 0.008 pc at
matched logged ages; this only says the prescribed gravity is dynamically
weak in this pilot. **The 2000 cm^-3 cloud does not remain a cold neutral
core into the WR phase.** Wind and photoheating act together in these two
runs; a radiation-only control is still needed to apportion the clearing.

Revalidate and regenerate the diagnostic PNGs with:

```bash
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/validate_evolving.py AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/results/evolving_20261014 ion_gravity_4p77myr 4.77
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/validate_evolving.py AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/results/evolving_20261014 ion_nogravity_4p77myr 4.77
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/plot_evolving.py AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/results/evolving_20261014 AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/results/evolving_20261014/plots
```

The two generated figures are `plots/front_history.png` and
`plots/density_profiles.png`. References: van Marle et al. (2012),
doi:10.1051/0004-6361/201219180; Franco et al. (2005),
arXiv:astro-ph/0508467. The density-profile **form** comes from the latter,
not the numerical core parameters used in its paper.

## Denser-media sweep (2026-10-14)

`generate_density_sweep.py` creates distinct gravity/no-gravity input files
in `density_inputs_20261014/`. It changes only central `n0_cm3` and, for
refinement tests, `domain_nx1` and the geometric stretch ratio in the matching
`evolving_base_512.par`, `_1024.par`, or `_2048.par`. The 40 Msun wind,
photon history, fixed 0.1-40 pc boundaries, 2 pc profile transition, support
speed, cooling/conduction switches, and source executable are unchanged.
Runs use isolated Keohane1 scratch
`/tmp/van_marle_density_sweep_20261014/`; validated outputs are transferred
non-destructively to `results/density_sweep_20261014/`.

All paired 0.1-Myr checks at 4,000/6,000/8,000/10,000 cm^-3 on 256 and
512 cells, 4,000/10,000/20,000 on 1,024 cells, and 20,000 on 2,048 cells
have six finite-positive VTUs, normal completion, empty stderr, correct
initial density/front, and unchanged 40 pc boundary. The analytic initial
fronts are 0.360/0.272/0.225/0.196/0.138 pc, respectively. Gravity-branch
fronts at 0.1 Myr (pc) show the grid effect:

| `n0` (cm^-3) | 256 cells | 512 cells | 1,024 cells | 2,048 cells |
| ---: | ---: | ---: | ---: | ---: |
| 4,000 | 1.375 | 1.419 | 1.427 | - |
| 6,000 | 1.111 | 1.186 | - | - |
| 8,000 | 0.946 | 1.020 | - | - |
| 10,000 | 0.849 | 0.916 | 0.968 | - |
| 20,000 | - | - | 0.702 | 0.716 |

The eight 512-cell full-lifetime gravity/no-gravity cases at 4,000-10,000
completed normally with empty stderr and 49 finite-positive VTUs each,
including the exact 4.77-Myr endpoint and saved 15/2,000 km/s inner RSG/WR
speeds. The static-gravity WR endpoint front radii are 21.649, 19.734,
18.500, and 17.550 pc in increasing density order; no-gravity differences
are less than 0.003 pc. All cross the initial 2 pc cloud edge within
0.14-0.23 Myr. During the zero-photon RSG phase, the simplified front
algorithm recombines to the 0.1 pc inner boundary, then rapidly reionizes
on WR onset. These are **ionization-front** radii, not automatically the
wind termination shock or swept shell radius. The WR density and thermal
pressure profiles show the outer shell at tens of parsecs.

The canonical, phase-aware 512-cell products are in
`results/density_sweep_20261014/plots_phase_aware/`: full front history,
late-phase zoom, WR density and thermal-pressure profiles, 0.1-Myr grid
check, and `front_summary_phase_aware_r512.csv`. The earlier
`plots/front_summary_r512.csv` is retained for provenance, but its single
sample exactly at the 4.5-Myr phase switch is ambiguous; use the phase-aware
CSV. Generate a new distinct plot directory when rerunning
`plot_density_sweep.py`; it refuses to overwrite existing products.

A separate matched 1,024-cell full pair at 10,000 also completed normally,
with 49 finite-positive VTUs each, 4.77-Myr endpoint, empty stderr, and
inner RSG/WR speeds present within 0.15 pc. Its first attempt was
deliberately stopped when a 7,200-s guard proved too short; five partial
VTUs and logs are preserved under
`results/density_sweep_20261014/incomplete_r1024_guard/` and are **not**
the validated fulls. The clean pair ran with identical inputs and binary
in isolated Keohane1
`/tmp/van_marle_density_sweep_20261014_r1024_longguard/` under 18,000-s
guards. `compare_10k_resolution.py` linearly interpolates the differently
sampled front logs to the 49 matched VTU ages, excluding exact wind-switch
ages; shell peaks use each native radial grid, and 10 pc thermal pressures
are linearly interpolated in radius. Its CSV and two PNGs are in
`results/density_sweep_20261014/plots_resolution_10k/`. At 4.77 Myr,
512-to-1,024-cell gravity-case front radius changes 17.550 to 17.758 pc,
native shell peak 18.175 to 18.390 pc, and 10 pc thermal pressure changes
by about 3%. The maximum matched-age front and shell-peak differences are
0.246 and 0.266 pc. This supports the qualitative density trend but does
**not** establish convergence from one grid pair. At 10 pc the 10,000 cm^-3
fine-grid gravity case changes from initially about 920 to 0.0073 cm^-3
by WR end: the wind plus photoheating evacuate gas strongly in this model,
but their individual contributions are not separated. The 20,000 run
remains short-only.

At 20,000 cm^-3 the initial Strömgren front lies just 0.038 pc beyond the
fixed 0.1 pc wind boundary: about four 1,024-cell or nine 2,048-cell
innermost widths. Higher densities would require a smaller injection radius
and a redesigned grid, not blind continuation of this sequence. Moreover,
the initial 0.1-2 pc gas mass is about 970-4,840 Msun over the 4,000-20,000
range. This model keeps the same prescribed gravity when density increases;
it does **not** include the growing cloud self-gravity or a self-consistent
core atmosphere. The flat exterior also scales as `n0/(4e)`. Thus these are
controlled density and resolution tests, not predictions for a molecular
core or proof of convergence.

## Separate 0.01 pc inner-boundary density series (2026-10-14)

`generate_inner_density_sweep.py` writes collision-checked inputs under
`density_inputs_inner0p01_20261014/`. The two matching base files change
**only** `xprobmin1` from 0.1 to 0.01 pc relative to the 1,024/2,048-cell
files above. This is a separate geometry, not another rung on the same
convergence ladder. The pinned executable, 40 Msun wind, illustrative
photon rates, effective support speed, 2 pc core profile and 40 pc outer
boundary are unchanged. Cooling, conduction, dust, stellar gravity and
self-gravity remain absent. The `hd_gravity` branch uses the same prescribed
radial field at every `n0`: `g=-2 c_eff^2 r/(1 pc)^2` inside 1 pc,
`g=-2 c_eff^2/r` from 1-2 pc, and zero outside. This field was chosen to
balance the **initial** pressure profile `P=rho c_eff^2`; it is not an extra
pressure term and is not recomputed from the gas or stellar mass.

The initial dust-free front radii are 0.1167, 0.0733, and 0.0463 pc at
20,000, 40,000, and 80,000 cm^-3. All ten 0.1-Myr gravity/no-gravity
short cases completed normally with empty stderr and passed six-VTU,
finite-positive, exact-endpoint, initial-front, and outer-density checks:
20k/40k at 1,024 and 2,048 cells, and 80k at 2,048 cells. On the 2,048-cell
prescribed-field branch the 0.1-Myr sharp ionization fronts are 0.959,
0.752, and 0.591 pc; native density-shell peaks are 0.975, 0.763, and
0.606 pc. At 20k, changing the inner boundary from 0.1 to 0.01 pc moves
the 2,048-cell 0.1-Myr front from 0.716 to 0.959 pc. Within the new
geometry, 1,024-to-2,048-cell front changes are still about 6-7% at
20k/40k. Neither comparison establishes convergence. The 80k initial H II
zone has only about ten hot saved radial cells on the 2,048-cell grid, so
80k is short-only pending a stronger resolution/physics decision.

The 0.01-2 pc initial gas mass is approximately 4,846/9,693/19,386 Msun
across 20k/40k/80k. The prescribed field corresponds to only about
241 Msun enclosed at 1 pc, while the 40k profile actually contains about
3,295 Msun there. Consequently these are **controlled numerical density
tests**, not a self-gravitating cold-core model. The generated short
CSV/PNGs are in `results/density_inner0p01_20261014/plots_short/`.

Four 1,024-cell 4.77-Myr 20k/40k prescribed-field/no-field full controls
completed normally in isolated Keohane1 scratch
`/tmp/van_marle_density_inner0p01_20261014/` under 36,000-s guards.
They were pulled non-destructively into the same local results tree and
passed `validate_evolving.py --inner-radius-pc 0.01` for all 196 saved
VTUs: finite-positive fields, 49 strictly increasing saves per case,
exact 4.77-Myr endpoints, initial density/front, unchanged outer density,
and 15/2000 km/s RSG/WR injection speeds. All four had `run.exit=0`, one
`Finished AMRVAC` marker, and empty stderr. The executable SHA-256 was
`3e4b905eb8e91d3b7c12d6f5676ccb0a438214a827ac6b3f28728c7bd3066ec9`.

At the WR endpoint the last logged **ionization** fronts for fixed `g(r)`
are 16.041 pc (20k) and 13.331 pc (40k); no-field controls are 16.042
and 13.348 pc. The native saved density-shell peaks are 16.729 and
14.113 pc with fixed `g(r)`, versus 16.729 and 14.156 pc without it.
These are different observables. During 4.3-4.5 Myr, `Q_H=0` in the
illustrative RSG prescription, so the sharp ionization-front diagnostic
falls to the 0.01 pc inner boundary; this is **not** collapse of the
swept-up shell. The clarified front/density/pressure PNGs and four-row
CSV are in `results/density_inner0p01_20261014/plots_full_field_labeled/`.
The first render remains separately in `plots_full/` and was not overwritten.

The near-agreement of fixed-field and no-field endpoints does not validate
the field as realistic gravity. The 20k/40k short-grid changes remain 6-7%,
the 80k case remains short-only, and this model still omits cooling, dust,
stellar gravity, and gas self-gravity. No convergence or physical cold-core
pressure claim follows from these exploratory controls.

### Density-shell radius versus central density

`plot_shell_radius_vs_density.py` reads the validated endpoint VTUs and
plots the **native density-shell peak**, not the sharp ionization front.
For the 4.77-Myr WR endpoint it searches 2-35 pc and shows the 4k-10k
series (0.1 pc inner radius, 512 cells) separately from the 20k-40k
series (0.01 pc inner radius, 1024 cells). A 10k, 1024-cell check is an
unconnected marker. With the fixed prescribed field, the WR peak radii
are 22.131, 20.303, 19.047, 18.175, 16.729, and 14.113 pc at central
densities 4k, 6k, 8k, 10k, 20k, and 40k cm^-3. The right panel uses only
the separate 0.01 pc, 2048-cell 0.1-Myr short series, searching 0.2-2 pc:
0.975, 0.763, and 0.606 pc at 20k, 40k, and 80k cm^-3. Both panels
include no-field controls. The 80k run has no WR endpoint.

The 20-row provenance CSV and visually checked PNG are in
`results/density_inner0p01_20261014/plots_shell_vs_density_20261014_v2/`.
The first render in `plots_shell_vs_density_20261014/` was preserved;
both CSVs have identical SHA-256. Recreate the final plot in a **new**
output directory with:

```bash
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/plot_shell_radius_vs_density.py AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/results/density_sweep_20261014 AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/results/density_inner0p01_20261014 <new-output-dir>
```

The two WR series have different inner boundaries and mesh sizes; do not
fit a single scaling law through their gap or call them a convergence
sequence. The shell peak is one radius diagnostic, not a resolved shell
width or outer edge. The fixed field is not self-gravity, and cooling,
dust, and a physical ionizing history remain absent.

### Finite-cloud mass-gravity test campaign (2026-10-14)

`mod_usr_cloud_mass.t` is a separate 1D source; it does not replace the
earlier prescribed-field results. Its initial hydrogen-nuclei profile is a
flattened power law with a smooth finite-cloud taper:

`n_H(r) = n_bg + max[0, n_ref ((1+(1pc/r_flat)^2)/(1+(r/r_flat)^2))^(p/2)-n_bg]
           * [1-tanh((r-R_cloud)/w)]/2`.

The *slope* `p=1.8` is motivated by the mean `1.8 +/- 0.4` in the 31
massive-star-forming envelopes modeled by
[Mueller et al. 2002](https://arxiv.org/abs/astro-ph/0207322); an independent
sample found mean inner `p=1.6`
([Beuther et al. 2002](https://arxiv.org/abs/astro-ph/0110370)).
The chosen `r_flat=0.2 pc`, `R_cloud=2 pc`, taper width `w=0.5 pc`,
`n_bg=10 cm^-3`, and density normalization `n_ref=300/600/1000/3000 cm^-3`
are **test assumptions**, not measurements of the target cloud. `n_ref` is
the untapered-law normalization at 1 pc; the taper makes the actual value
slightly lower. The smooth edge belongs to the cloud, not an infinite
`r^-p` atmosphere.

The model tabulates
`M_enc(r) = 40 Msun + 4 pi integral[0.01 pc,r] (rho-rho_bg) s^2 ds`,
`g(r) = -G M_enc(r)/r^2`, and
`P_0(r) = P_ext + integral[r,R_out] rho(s) |g(s)| ds`, with
`P_ext = rho_bg (0.72 km/s)^2`. Only interior cloud excess mass contributes
to the fixed field; the uniform large-scale background's self-gravity and
gas inside the 0.01 pc injection boundary are excluded. Shell theorem is
respected. There is no extra gravitational-pressure force: HD evolves `P`
and applies `rho*g`. The initial `P_0` is **effective support** (including
unmodeled turbulence), not a claim that molecular gas has that thermal
temperature. The potential remains fixed after wind sweeping, so this is
not evolving self-gravity. Photon rates remain illustrative; dust, CLOUDY
cooling, conduction, and detailed radiation transfer remain absent.

`generate_cloud_mass_cases.py` writes a four-density, three-stage manifest
(`atmosphere` then 0.1-Myr `wind` then 4.77-Myr `full`). Each independent
serial case is assigned to Keohane1/2/3/4, respectively. All four hosts
compiled the same source against pinned AMRVAC `244c677f`, yielding identical
executable SHA-256 `45ea86b45462e9e76b40515b5babc03ac32f51b9a9886967b88c7f32f817e114`.
The first 0.2-pc-edge atmosphere diagnostic is preserved under
`results/cloud_mass_20261014/`; it completed but failed the 0.1-Myr
equilibrium gate with 16-27% density drift near the edge. A distinct
0.5-pc-edge branch is in `results/cloud_mass_wideedge_20261014/`.
Its four no-wind 0.1-Myr controls have normal exits, two finite-positive
VTUs each, exact endpoint, independent initial density/pressure checks,
and maximum density drifts of 9.2/7.3/7.4/3.9%, with peak speeds below
0.31 km/s. That residual drift is a systematic baseline for later shell
interpretation; it is not perfect hydrostatic equilibrium. The four short
wind/photoionization cases then completed normally on the four VMs with
six finite-positive VTUs each, exact 0.1-Myr endpoints, empty stderr,
independently checked initial profiles/pressure/mass, and unchanged outer
boundary. Canonical products are in
`results/cloud_mass_wideedge_20261014/plots_wind_v5/` (CSV and three PNGs;
the earlier render is preserved). The CSV identifies both the untapered
`n_ref` and the actual initial central/1-pc densities.
The native 0.1-Myr shell-excess peaks for `n_ref=300/600/1000/3000` are
3.229/2.326/1.798/1.013 pc. The first has ~36 elements across its
excess FWHM; the others have only ~3.7/3.1/2.9. The 3000 case also has
only **five** elements inside its initial Strömgren radius. Hollow markers
flag these limitations. This is an exploratory trend, not a converged
wall-radius calibration; **do not run the 3000 case to 4.77 Myr on this
grid**.

`generate_cloud_variants.py` sets up one-factor 0.1-Myr checks at
`n_ref=1000`: cloud edge at 1 or 3 pc, slope `p=1.6` instead of 1.8,
and zero stellar mass in `g` (gas cloud only). The 1 pc / 0.25 pc edge
failed its no-wind check with 23% drift; its separately named 0.5 pc edge
passed with 8.7%. The 3 pc and `p=1.6` no-wind checks passed with 4.3%
and 7.5% drift. The gas-only no-wind case drifted 12.8%, above the
predeclared 12% atmosphere gate, so its wind case is held. A separate
`n_ref=1500` no-wind case passed with 6.2% drift; it has ten initial H II
elements, marginal for a full run. The three passing variant winds and
the 1500 wind short completed normally and passed six-VTU, 0.1-Myr,
initial-profile, and boundary validation. The four cloud-shape controls
at fixed `n_ref=1000` have a separate CSV and PNG in
`results/cloud_variants_20261014/plots_wind_v1/`, generated by
`plot_cloud_variants.py`; it subtracts each variant's own initial profile.
The 1 pc cloud moves the measured short shell to 2.40 pc versus 1.80 pc
for the baseline, whereas the 3 pc edge and `p=1.6` controls have short
peaks at 1.78 and 1.88 pc. Only the 1 pc shell has at least five
elements across its excess FWHM; the others are marked as exploratory.

For the 4.77-Myr comparison, a separate 0.01-80 pc / 2048-cell mesh in
`cloud_mass_base_2048_80pc.par` preserves the old innermost cell width
(`~0.00846 pc`) while moving the outer boundary away. Its four-case
`n_ref=300/600/1000/1500` manifest is in
`cloud_mass_inputs_80pc_20261014/` and staged on four VMs. This changes
the outer hydrostatic-pressure integral as well as the outer boundary.
All four fresh no-wind 0.1-Myr checkpoints completed normally and passed
independent atmosphere/boundary validation, with maximum density drift
9.2/7.7/7.7/6.2% for `n_ref=300/600/1000/1500`. Their four matching
0.1-Myr wind cases completed normally on Keohane1/2/3/4, were pulled
non-destructively to `results/cloud_mass_80pc_20261014/nref####/wind/`,
and passed six finite-positive VTUs, 0.1-Myr endpoint, initial
density/mass/pressure, and outer density **and pressure** gates. The
standard CSV and three PNGs are in
`results/cloud_mass_80pc_20261014/plots_wind_v3/` (earlier renders
preserved). Shell-excess peaks
are 3.208/2.340/1.811/1.476 pc, with FWHM widths of 48/3.8/3.2/3.1
radial elements. Only the `n_ref=300` short case is adequately sampled on
this mesh. Its guarded 4.77-Myr full finished normally on Keohane1 on
2026-10-15 (exit 0, one completion marker, empty stderr, 49 VTUs), was
pulled non-destructively to `results/cloud_mass_80pc_20261014/nref0300/full/`,
and passed full-field/endpoint, initial-profile, outer-density/pressure,
and RSG/WR phase validation. The saved RSG inner active-cell speed is
16.2 km/s versus the 15 km/s prescribed ghost-cell speed; the validator
uses a documented 10% RSG tolerance and retains 5% for WR. Standard
single-case CSV and three PNGs are in `plots_full_nref0300_v1/`.
At 4.77 Myr, the native shell-excess peak is 57.687 pc and its FWHM is
0.318 pc, only 3.97 radial elements. This **fails** the >=5-element
full-shell gate even though the initial H II region spans 118 elements.
The CSV/plot is one point, not a shell-radius-versus-density relation or
convergence result. Do not duplicate the full or promote it to a calibrated
GRB CSM profile.
For a side-by-side radius-versus-density view of this same 80-pc branch,
`plot_cloud_mass_density_overview.py` reads the existing validated 2048/
4096-cell 0.1-Myr CSVs and the sole 4.77-Myr full CSV. The final two-panel
PNG and eight-row provenance CSV are in
`results/cloud_mass_80pc_20261014/plots_density_overview_20261015_v2/`.
Hollow points fail the five-cell shell or ten-cell initial-H II gate.
The two epochs have separate panels and y-scales; the late panel contains
only nref300, so it is not a density relation or fit. The initial `n_ref`
is the untapered density parameter at 1 pc, not central density.
The denser 2048-cell fulls are **held**. The 3000 short-only point is
not on this ladder.

`cloud_mass_base_4096_80pc.par` and
`cloud_mass_inputs_4096_80pc_20261014/` define a separate, same-physics
resolution test of `n_ref=600/1000/1500` on Keohane2/3/4. It halves the
inner cell width to ~0.004 pc while preserving the 0.01-80 pc radial
domain. The model executable and base input hashes match across the
three hosts. Their unique `r4096` atmosphere cases completed normally
on 2026-10-14 in `/tmp/van_marle_cloud_mass_4096_80pc_20261014_farm/`,
were pulled non-destructively, and passed the 12%/1 km/s stability and
independent numerical gates. Their matching 0.1-Myr wind checks completed
normally with six VTUs each and were pulled non-destructively to distinct
`results/cloud_mass_4096_80pc_20261014/nref####/wind/` trees.
`validate_cloud_mass.py` passed finite-positive fields, exact endpoint,
initial density/mass/support pressure, and outer density and pressure.
New CSV/three PNGs in `plots_wind_v1/` give native shell peaks
2.214/1.766/1.494 pc and shell-FWHM widths 3.72/3.32/3.22 radial
elements at `n_ref=600/1000/1500`, respectively. Initial H II zones
span 55/32/22 elements. The shell widths still fail the predeclared
five-element gate. Matched 2048-cell shell peaks were
2.340/1.811/1.476 pc and widths 3.78/3.17/3.14 elements. The 4096-cell study tests shell
measurement, **not** convergence by itself. Its measured short-run rate
projects a full 4.77-Myr serial case beyond the 36,000-s guard; do not
launch the staged 4096 full inputs overnight merely because a short
case passes. Review runtime and mesh strategy first.

`validate_cloud_mass.py` checks every saved VTU, initial density and support
pressure against an independent radial integration, run exit/marker/stderr,
endpoint, and outer boundary. After a complete short or full stage,
`plot_cloud_mass_products.py` runs this validation and writes a native
density-excess shell-radius-vs-density CSV/PNG, radial density diagnostics,
and initial density/enclosed-mass/`g`/pressure plots to a **new** directory.
Its shell radius is the maximum positive density excess above the initial
profile in 0.2-35 pc (short) or 2 pc to 5 pc inside the outer boundary
(full), not an ionization front, wind termination shock, or fitted CSM
wall. The CSV also records shell excess FWHM, width in grid elements,
contrast to the initial profile, and peak pressure. No inversion to a GRB/afterglow
density law is licensed before full-stage checks, profile sensitivity, and
resolution tests. For a sole completed full, use
`python plot_cloud_mass_products.py cloud_mass_inputs_80pc_20261014/manifest.csv results/cloud_mass_80pc_20261014 full NEW_OUTPUT --case cloudmass_nref0300_full`;
the explicit selection creates an isolated one-point product without
inventing the held full cases.

### Previous four-VM farm plan (fulfilled for the new short tests)

Jonathan wants the next approved batch farmed across **all four** Keohane
VMs rather than concentrated on Keohane1. The original read-only checks at
2026-10-14 15:22 UTC found Keohane1/2/3/4 reachable, with 16/16/16/24
logical CPUs, about 46/46/46/62 GiB available memory, at least 111 GiB
free disk each, and no AMRVAC, MPI, or user Python jobs. Each has the
pinned AMRVAC checkout at `244c677f`, `gfortran`, and `make`. This is a
snapshot, **not** ongoing launch clearance; capacity and competing jobs
were rechecked before the new farm. The new binary was built and hash-matched
on all four hosts as documented above.

The new finite-cloud matrix above is distinct from the older 80k dense-core
branch. Assign independent serial 1D cases one each to Keohane1/2/3/4.
Queue remaining cases under measured CPU/memory/disk limits; do not
oversubscribe or duplicate a case merely to occupy a host. Verify the
same pinned source, model build hash, and case-input hash on every host.
Use unique per-case scratch/output prefixes and guarded exits; require
`run.exit=0`, a normal AMRVAC completion marker, empty stderr, all saved
finite-positive fields, the intended endpoint, and phase/boundary checks
before a non-overwriting pull into distinct local result directories.
The old 80k short run is under-resolved and is not part of this new matrix.

## Read-only scale check

`preflight.py` uses an illustrative `Q_H=2e49 s^-1`, `n_H=1000 cm^-3`,
`alpha_B=2.6e-13 cm^3 s^-1`, and a **hypothetical** 2 pc core. It prints
the dust-free, uniform-density Strömgren radius, recombination time, cloud
mass, escape speed, and a classical pressure-driven H II crossing time.
The crossing time assumes 10 km/s ionized-gas sound speed and ignores dust,
wind, gravity, and cloud stratification; it is a warning scale, not a
simulation result or a prediction for the requested model.

## Completed numerical smoke (2026-10-14)

`mod_usr.t` and `smoke.par` were compiled against pinned AMRVAC v3.1
`244c677f` on Keohane1 and run serially in the isolated
`/tmp/van_marle_ionized_core_smoke_20261014/` directory. The 256-cell 1D
spherical box spans 0.03-4 pc. It starts at uniform `n_H=1000 cm^-3` with
10,000 K inside the dust-free Strömgren radius and 20 K molecular gas outside;
the inner boundary injects the paper's 40 Msun wind. The outer boundary is
held at the molecular state. The single-fluid HD code has a fixed ionized-gas
mean particle mass; the molecular temperature is converted to an equivalent
pressure using `mu=2.33`. No cooling, conduction, radiation transport,
recombination update, or gravity is active. The 10-year limit is much shorter
than the ~122-year uniform-gas recombination time; this test is only an
initial-state and hydro-boundary check, **not** a 4.77-Myr wind calculation.

The run produced saves at 0 and 10 years, a normal `Finished AMRVAC` marker,
and empty stderr. `validate_smoke.py` checked both saved ages, all finite
positive density and pressure values, the initial hot/cold pressures, and
the unchanged outer ambient density. Small results are copied non-destructively
to `results/smoke_20261014/`; the input files remain here. Revalidate with:

```bash
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/validate_smoke.py AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/results/smoke_20261014
```

Source hashes: `mod_usr.t` `46e99e489d51e112511dd086bdb417364b98fc927b8ba0e82f222325634204f1`;
`smoke.par` `7ba05b8bd6fdc795083636c17ef7f56777e01008f44c0bf49af1a7bf0347813c`.

```bash
/Users/jkeohane/GRBs/.venv/bin/python AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d/preflight.py
```

For any next scientific run: determine whether the intended cloud needs a
higher density, a different finite-core radius, stellar-plus-gas gravity, and
a phase-dependent ionizing track. Add physically appropriate cooling and
dust/radiation treatment before treating the bubble scale as a prediction.
Require a normal AMRVAC completion marker, finite-positive output, phase
checks, and resolution/outer-boundary tests; an MPI-abort exit code alone is
not a completion gate.

### Last touched (2026-10-16, n5000 intermediate wind)

Checked guarded completion, pulled n5000 wind with `rsync --ignore-existing`,
ran independent six-VTU `validate_cloud_mass.py --finite-gmc`, generated
one-case CSV/two PNGs in new `plots_wind_n05000_v1/`, and inspected the
density profile. No full, cooling, or conduction run. Remaining: n20000
wind, then short-age scan comparison; no convergence claim.

### Last touched (2026-10-16, 8192 winds)

Pulled the two completed 8192 short winds with `rsync --ignore-existing`,
ran independent `validate_cloud_mass.py --finite-gmc` on all six saved
VTUs, regenerated corrected CSV/two PNGs with `plot_dense_gmc_scan.py`
in new `plots_wind_low8192_v1/`, and inspected both PNGs. Compared
exact-age 2048/4096/8192 peaks, native widths, contrasts, and domain
clearance. No convergence claim or full run. Remaining: finish and
validate the two intermediate 4096 winds; full lifetimes held.

### Last touched (2026-10-16, intermediate staging)

Modified `generate_dense_gmc_scan.py` to opt in to two intermediate-density
short cases; generated their separate 4096 manifest and parameter files.
Checked pinned binary/source/input hashes, remote CPU/memory/disk, pulled
and independently validated both intermediate no-wind atmospheres, then
started their guarded short winds on Keohane3/4. The prior dense 4096
winds were pulled with `rsync --ignore-existing`, independently validated,
and plotted to a new `plots_wind_dense4096_v1/` CSV/PNG directory; their
2048-to-4096 radius shifts prevent a convergence claim. Commands included
`py_compile`, generator, par diff, remote hash/capacity checks, runner,
validator, plotter, and PNG inspection. Remaining: finish intermediate
winds and compare exact-age profiles; fulls held.

### Last touched (2026-10-15)

Finite-GMC update: modified `plot_dense_gmc_scan.py` to collapse duplicate
AMRVAC block vertices before measuring shell width, then regenerated
validated CSV/PNGs in distinct 2048/4096 `v2` plot directories; v1 remains
but is superseded. Generated two mesh-only 8192 short cases, diffed base
parameters against 4096, checked executable/source hashes, ran and pulled
both guarded no-wind atmospheres, and validated each at two finite-positive
VTUs/0.1 Myr. Distinct guarded 8192 winds now advance on Keohane1/2;
4096 dense winds advance on Keohane3/4. Commands included the generator,
`py_compile`, synthetic duplicate-coordinate check, remote guarded runner,
`rsync --ignore-existing`, validator, and plotter. Updated this README,
root handoff/TODO, and the quiet heartbeat prompt. Remaining: validate
four advancing winds and compare matched-age native profiles. No full
lifetime, cooling, or conduction run launched; no convergence claim.

Earlier 80-pc campaign last-touched note:

Modified `validate_cloud_mass.py`, `plot_cloud_mass_products.py`,
`plot_cloud_mass_density_overview.py`, this README, and root handoff/TODO.
Checked Keohane1 guard/log/VTUs; pulled the sole
completed 80-pc full with `rsync --ignore-existing`; ran the full validator
and the explicitly selected one-case plot command above. Inspected all three
PNGs. Regenerated the separate-age shell-radius/density overview from the
three validated product CSVs to a new `v2/` output directory and visually
checked its PNG. The final shell fails the five-element resolution gate; dense fulls
remain held for a mesh/runtime and physics decision. No new AMRVAC run was
launched. William's Git log was not updated from Lyra.
