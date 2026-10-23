# 25-Msun finite-GMC 1D campaign

## Campaign reconciled (2026-10-21 22:38 UTC)

All seven 0.1-Myr statics and all seven matching 0.0015-Myr direct-MS
winds are validated and pulled. There is no pending 25-Msun stage and no
authorization here for additional runs. Do not rerun, restart or re-pull
any completed stage. The dated dispatch notes below are historical records;
their earlier pending/held/conditional-launch instructions are superseded.

The final three winds passed guard exit 0, exactly one `Finished AMRVAC`,
empty run stderr and dispatch logs, seven exact `0000`--`0006` VTUs,
binary/source/runner/manifest/base/wind SHA pins and original dispatch
checksum records. NEW non-overwriting full-farm pulls matched remote
`rsync -rcni` dry-runs and every remote file SHA (27 files on Keohane1,
26 each on Keohane2 and Pauley404-03). Independent validation passed
25-Msun finite-GMC initial density/mass/pressure, stable evolved outer
2.5 pc with pressure anchor 20 pc, the 1500-km/s wind and
2e-7-Msun/yr flux. All seven saved ages match 0--0.0015 Myr at
0.00025-Myr spacing to within 1e-9 Myr; the final saved age is
0.0014999999654379042 Myr. NEW full/inner density and velocity figures
were visually inspected.

| Final reconciled host | GMC background (cm^-3) | Cells | Runtime (s) | Maximum speed (km/s) | Inner flux (Msun/yr) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Keohane1 | 1000 | 20480 | 18496.063 | 1500.5355 | 1.9976690e-7 |
| Keohane2 | 2000 | 20480 | 18503.879 | 1500.5376 | 1.9976720e-7 |
| Pauley404-03 | 1000 | 4096 | 30337.733 | 1500.5554 | 2.0002390e-7 |

The earlier Mac01/02 and Keohane3/4 validated products were retained without
new pulls. The seven-host inventory is
`results/direct_ms_diagnostics_20261021/campaign_endpoint_summary_20261021.csv`.
For each host/case, the unchanged remote farm mirror is in
`results/direct_ms_pilots_20261021/<host>/<case>/wind/`; each new mirror has
`validation.csv` and `endpoint_provenance.json`. NEW figures and snapshot
CSVs are in `results/direct_ms_diagnostics_20261021/<host>/<case>/`.

Validation must specify `edge_width=0.5` (CLI `--edge-width-pc 0.5`),
`--star-mass-msun 25 --finite-gmc --n-bg <1000|2000> --inner-pc 0.0002
--domain-max-pc 2.5 --atmosphere-outer-pc 20 --expected-wind-speed-kms 1500
--expected-mdot-msun-yr 2e-7`. The independent `validate_cloud_mass.py`
expects a flat directory: create a temporary symlink view in local scratch
combining the farm's run records with its `output/` files, then write its
CSV into the farm mirror. Do not alter the raw remote or local files.
Use `ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=10`
for direct probes; omit `-n` from rsync's SSH transport because rsync needs
stdin. Keep Matplotlib caches in local non-Drive scratch.

The 506/747 potential-front cell counts are mesh diagnostics with ionization
off. These remain short unpreconditioned MS winds, not a natural 7-Myr
MS/RSG evolution, a WR phase, resolved physical shock widths, converged
profiles or established GRB walls. No physics, guard, Xcode or network
configuration changed; the separate 40-Msun endpoint belongs to its monitor.

Monitor shutdown completed at 2026-10-21 22:41 UTC. App
`automation_update` confirmed `monitor-25-msun-finite-gmc-statics` PAUSED
after the chat's permission profile changed to full access. A fresh
read-only stored-TOML check verified PAUSED with the existing hourly
schedule, name, prompt and dedicated `AMRVAC monitoring` target
`01a15e82-7f3a-7a02-bbb0-8a91839c5849` preserved. Earlier
`MCP tool call requires approval, but approval policy is never` errors
are historical and resolved. There is no pending 25-Msun science or
administrative stage. If a stale heartbeat arrives, do no SSH, pulls
or launches. The separate 40-Msun monitor was not modified.

Historical monitor routing update 2026-10-21 12:50 UTC: the existing monitor was changed to hourly in this dedicated thread. Earlier15-minute/main-thread instructions are superseded.

## Historical: approved held wind launched (2026-10-21 12:22 UTC)

Jonathan authorized both held winds with "Let's run it" and confirmed
"Yes", explaining that machine availability, rather than paid computer
time, limits the work. Keohane1's 25-Msun GMC1000 20,480-cell direct-MS
wind launched ONCE at 08:18 EDT under 60,000 s in NEW
`/tmp/van_marle_m25_n20000b1000_c20480f31_ms_wind_20261021_farm/`.
Static exit0/one finish/empty stderr/two VTUs, static source/base pins,
exact manifest verifier, six remote SHA, idle/46-GiB available RAM/zero
swap/110-GiB disk/empty-output gates passed. Estimate45,880.279 s is below
the48,000-s planning ceiling. Runner706560 / AMRVAC706563; first VTU,
one rank/~100% CPU, advancing steps and empty stderr/dispatch passed.
Keohane2 and Mac03 winds retain original54,000-s guards. The existing
hourly25 monitor now follows all three; no validated endpoint yet.
The separate authorized40-Msun GMC2000 wind runs on freed Pauley404-02
under64,800 s; NEVER launch its original Mac03 staged copy. Older held
instructions and launch snapshots below are historical and superseded.

Last touched: this README,40 README/new dispatch JSON, root handoff/TODO
and both existing monitors. Commands: SHA/input/static verification,
quiet SSH resources, NEW rsync, guarded launch and first-VTU/process/
stderr checks. Outputs: NEW remote K1 farm/initial VTU; endpoint gates,
NEW pulls and diagnostics remain pending. No physics change.

Historical status (2026-10-21 07:12 EDT): all seven statics passed and were NEW-pulled
and independently validated. Pauley404-01/02 and Keohane3/4 direct-MS winds
also passed independent endpoint checks and have NEW pulls and profile
diagnostics. Keohane2's wind remains guarded; Keohane1's wind is held for
Jonathan's guard decision. Pauley404-03's matching wind is guarded under
54,000 s after its independent static and host-margin gates. The static pilots
change central stellar gravity from 40 to 25 Msun in the working 1D
finite-GMC model. They keep the same core/cloud density, support, geometry,
cooling-off/conduction-off switches, and no-wind/no-ionization static stage
as the pinned 40-Msun controls. Those static stages are not wind results.

The published 25-Msun model in van Marle et al. (2012), Table 1
(DOI 10.1051/0004-6361/201219180), has a 6.5-Myr MS phase with
2e-7 Msun/yr at 1500 km/s, a 0.5-Myr RSG phase with 1e-5 Msun/yr at
15 km/s, and **no WR phase** before its 7.0-Myr endpoint. It also omits
photoionization. A hypothetical stripped-star WR case and an ionized
25-Msun case require separate, explicit assumptions; neither is implied
by these static inputs. The existing two-star 2D setup failed at the first
advancing timestep and must not be used as a validated production route.

`generate_static_pilots.py` creates seven distinct, non-overwriting inputs
under `input_sets/static_pilots_20261020_v2/`: two GMC backgrounds across a
4096--20480-cell mesh ladder, one case per Keohane/Pauley host. Every case
uses an inner boundary of 0.0002 pc, evolved outer radius 2.5 pc, and
hydrostatic pressure anchor at 20 pc. The Linux first width is 0.00003125
pc; the Mac first width is 0.0000125 pc. This is an exploratory mesh ladder,
not a fixed-first-width convergence comparison. The copied
40-Msun photon parameters are dormant because ionization is OFF. Only
the star mass, mesh size/stretch, and output filename change from the
pinned 40-Msun source templates; the manifest records source and output
SHA-256 values. No existing inputs, results, or guards are overwritten.
The earlier `static_pilots_20261020/` draft is unlaunched and superseded;
do not dispatch it.

## Static pilot assignments and gates

The exact dispatch inputs are in `input_sets/static_pilots_20261020_v2/`.
Farm names below are relative to `/tmp/` on Keohane hosts or `/private/tmp/`
on Pauley hosts. Each farm was new and empty before transfer. The manifest,
binary, source, runner, base, and static input hashes matched independently
after transfer. All seven produced the initial VTU with one AMRVAC process
and empty stderr. All seven 0.1-Myr endpoints subsequently passed and were
pulled and validated, as recorded below and in the campaign inventory.

| Host | GMC background (cm^-3) | Cells | First width (pc) | Farm |
| --- | ---: | ---: | ---: | --- |
| Keohane1 | 1000 | 20480 | 0.00003125 | `van_marle_m25_n20000b1000_c20480f31_static_20261020_farm/` |
| Keohane2 | 2000 | 20480 | 0.00003125 | `van_marle_m25_n20000b2000_c20480f31_static_20261020_farm/` |
| Keohane3 | 1000 | 16384 | 0.00003125 | `van_marle_m25_n20000b1000_c16384f31_static_20261020_farm/` |
| Keohane4 | 2000 | 16384 | 0.00003125 | `van_marle_m25_n20000b2000_c16384f31_static_20261020_farm/` |
| Pauley404-01 | 1000 | 8192 | 0.0000125 | `van_marle_m25_n20000b1000_c8192f12_static_20261020_mac_farm/` |
| Pauley404-02 | 2000 | 8192 | 0.0000125 | `van_marle_m25_n20000b2000_c8192f12_static_20261020_mac_farm/` |
| Pauley404-03 | 1000 | 4096 | 0.0000125 | `van_marle_m25_n20000b1000_c4096f12_static_20261020_mac_farm/` |

The four Keohane hosts use the same newly built short-domain-capable Linux
binary, SHA-256 `d07e444f0b3c1528d36525d3ea0fdff255af9721760be40bfbc7d32337f8bab2`;
its source is SHA-256 `4b39192f46140b3419800bc65df0b71b0985dcc92ce250499bf0949e02e4383d`.
Build provenance and a passed 10-year/two-VTU guarded static smoke are in
`builds/linux_local_boundary_20261020/BUILD.md` and
`results/static_smoke_20261020/Keohane1/`. The smoke is not a 0.1-Myr
atmosphere result. All three Pauley hosts use the pinned arm64 binary
SHA-256 `9b01f5e38b37c1436169b4b8f8d478058697f3db28e441bbeed6f70a7b529153`
with the same source SHA; Pauley404-03 uses Homebrew Python via the existing
LAN jump, without changing its Xcode or Tailscale state.

Prior host static measurements on the 40-Msun f31 16,384-cell controls were
15,433, 21,988, 15,546, and 21,695 s on Keohane1--4. Scaling the first
two by 20,480/16,384 gives 19,291 and 27,485 s; the other two remain at
their measured mesh size. A conservative further 1.5x allowance keeps each
projection below 43,200 s (80% of the 54,000-s guard). Mac02/03 measured
16,384-cell f12 statics near 27,000 s; the 8192/4096 pilots were projected
below the same ceiling. These are guard estimates, not measured 25-Msun
runtimes. Never extend a guard or repeat a failed case automatically.

Before each launch, check the host is idle and has adequate memory/disk,
verify binary/source/runner/input checksums, establish a host-measured
runtime projection with at least 20% guard margin, and require an empty
output directory. After completion, require guard exit 0, one normal
AMRVAC finish, empty stderr, two exact VTUs, 0.1-Myr age, finite-positive
fields, and the 25-Msun finite-GMC initial/outer stability validation.
Pull into NEW result trees only. No matching wind may launch until its own
static gate, exact direct-MS input gate, and host-specific runtime margin pass.
For a no-ionization static, the validator's initial H II cell count is only
a potential-front mesh diagnostic; it is not ionized gas evolved by the run.

## Direct-MS wind inputs and source gate

`generate_direct_ms_pilots.py` creates seven matching
0.0015-Myr/seven-VTU direct-MS wind namelists in
`input_sets/direct_ms_0015myr_20261020/`. The independent
`verify_direct_ms_pilots.py` passed all seven exact base/static SHA matches,
phase offset 0, ionization-off switch, cadence, and controlled differences
from the pinned wind template. All seven winds are complete and validated.
These are
**unpreconditioned early-MS pilots**
in the same static finite-GMC gas, not a 6.5-Myr MS evolution, an RSG shell,
or a WR bubble. Only the MS rate and speed are borrowed from van Marle et al.

`mod_usr_25_track.t` and the distinct arm64 executable are pinned in
`builds/arm64_25_track_20261020/BUILD.md`. The isolated Lyra build completed,
and a NEW 2048-cell, 10-year/two-VTU direct-MS/no-ionization smoke exited its
600-s guard normally with one finish marker and empty stderr. The NEW
`results/direct_ms_smoke_20261020/Lyra/validation.csv` independently passed
the exact 25-Msun finite-GMC/short-domain geometry and measured inner wind
speed 1500.352 km/s and mass flux 2.000105e-7 Msun/yr. The exact x86-64
source was subsequently built on a freed Keohane host; its pinned source,
binary and host-measured projections are in
`builds/linux_25_track_20261021/BUILD.md`. All four Linux wind endpoints
subsequently passed. Every host required its own completed static
gate, NEW pull, and measured >=20%
guard margin before its matching wind started. The separate authorized
40-Msun GMC2000 endpoint remains owned by its own monitor.

## Mac01/02 static gates and wind preflight (2026-10-21 00:35 EDT)

Pauley404-01 (GMC1000) and Pauley404-02 (GMC2000) 8192-cell static guards
finished with exit 0, one `Finished AMRVAC` marker, empty stderr and exactly
two VTUs in 11315.833 and 11175.113 s, respectively. NEW non-overwriting
farm mirrors are under `results/static_pilots_20261021/<host>/<case>/atmosphere/`;
checksum dry-runs matched their remote sources. The independent validator
passed exact 0.099999998-Myr age, 25-Msun finite-GMC initial mass/density/
pressure, evolved outer 2.5 pc with pressure anchor 20 pc, and stable outer
fields. Maximum density drift is 0.002408/0.002406 and maximum speed is
0.15168/0.15162 km/s. The 969 potential-front cells are a mesh calculation,
not an evolved H II region, because ionization is off.

For the matching direct-MS winds, host-measured 40-Msun static/wind runtime
ratios give Mac01 `11315.833 * 5654.522 / 4709.179 = 13587.427 s` and
Mac02 `11175.113 * 21985.413 / 27155.067 = 9047.648 s`. A further 1.5x
allowance gives 20381.141 and 13571.471 s, both below 34560 s (80% of the
explicit 43200-s wind guard). This is a scheduling projection across wind
physics, not a measured 25-Msun wind duration. Both hosts were idle, with
700/675 GiB free disk and no swap activity. Their NEW wind farms have empty
outputs and transferred arm64 binary, 25-track source, runner, manifest and
case-input SHA-256 matching the pinned local files. The final validated
wind results are recorded below.

At 00:35 EDT, the matching Mac01 GMC1000 and Mac02 GMC2000 direct-MS winds
launched once in NEW farms
`/private/tmp/van_marle_m25_n20000b1000_c8192f12_ms_wind_20261021_mac_farm/`
and
`/private/tmp/van_marle_m25_n20000b2000_c8192f12_ms_wind_20261021_mac_farm/`.
Each had an explicit 43200-s guard. Both passed the post-launch pinned
binary/source/base/wind SHA check, initial VTU, one AMRVAC process and empty
stderr/dispatch log. Their final gates and diagnostics are below. No shell
claim follows from the initial VTU. Mac03 advances slowly, and its static
guard must not be restarted or changed.

## Mac01/02 validated direct-MS endpoints (2026-10-21 03:00 EDT)

Pauley404-01/02 winds finished in 8438.730/8368.617 s with guard exit 0,
exactly one `Finished AMRVAC` marker, empty stderr and dispatch logs, and
seven exact `0000`--`0006` VTUs. Remote binary/source/runner/manifest/base/
wind SHA matched both their dispatch records and the pinned inputs. NEW
non-overwriting full-farm pulls are under
`results/direct_ms_pilots_20261021/<host>/<case>/wind/`; remote/local
checksum dry-runs showed no differences. Independent `validate_cloud_mass.py`
passed exact 0.001499999965-Myr age, 25-Msun finite-GMC initial mass/density/
pressure, evolved outer 2.5 pc/pressure anchor 20 pc, stable outer fields,
and 1500.555/1500.557-km/s maximum speeds with inner mass flux
2.000342e-7 Msun/yr in both cases. The validator's 969 potential-front cells
do not mean ionization was evolved. Each pull has `validation.csv`.

NEW `plot_direct_ms_profiles.py` reads only validated seven-VTU pulls and
writes non-overwriting full/inner density and velocity profiles plus a
snapshot CSV under `results/direct_ms_diagnostics_20261021/<host>/<case>/`.
Both figures were visually inspected. A narrow outward-moving density peak
is visible over these 1.5 kyr, but no shell-quality, physical-width,
termination-shock, convergence, or GRB-wall inference has been made. These
are short unpreconditioned MS winds with ionization disabled.

## Keohane3/4 static gates and guarded direct-MS winds (2026-10-21 02:54 EDT)

Keohane3 GMC1000 and Keohane4 GMC2000 16,384-cell statics finished in
19281.796/19176.233 s with guard exit 0, one finish, empty stderr and two
VTUs. NEW non-overwriting full-farm pulls at
`results/static_pilots_20261021/<host>/<case>/atmosphere/` passed remote/local
checksum dry-runs and independent exact 0.099999998-Myr 25-Msun finite-GMC
initial mass/density/pressure and stable evolved-outer/pressure-anchor
validation. Density drift is 0.0020141/0.0020131, speed at most
0.345418/0.345323 km/s; 500 potential-front cells are a mesh diagnostic,
not an evolved H II region. Each pull has `validation.csv`.

The exact 25-track Linux x86-64 source and executable were built on freed
Keohane3 in an isolated directory; build commands and SHA-256 are in
`builds/linux_25_track_20261021/BUILD.md`. Prior same-host 40-Msun
static/wind runtime ratios applied to the just-measured 25-Msun statics,
with an additional 1.5 allowance, projected 36945.370/26406.733 s for
Keohane3/4 winds, both below 43200 s (80% of their explicit 54000-s guards).
These estimates cross wind physics and are not measured 25-Msun wind times.
After pinned binary/source/runner/manifest/base/wind SHA, idle/resource and
empty-output preflight, the distinct matching winds launched once into NEW
`/tmp/van_marle_m25_n20000b{1000,2000}_c16384f31_ms_wind_20261021_farm/`
on Keohane3/4. Each has first VTU, one AMRVAC rank and empty stderr.
The transferred Linux runner was made executable before either dispatch;
its SHA did not change. Do not restart. On completion require guard 0,
one finish, empty stderr, seven exact VTUs, exact 0.0015-Myr age, independent
finite-GMC initial/outer/1500-km/s/2e-7-Msun-yr validation, then a NEW pull
and diagnostics. Pauley404-03's original static remains guarded; Mac03 is
particularly slow. No failed AMRVAC case is automatically retried.

## Keohane1/2 20,480-cell static gates and wind preflight (2026-10-21 04:11 EDT)

Keohane1 GMC1000 and Keohane2 GMC2000 0.1-Myr statics completed in
23924.339/23926.525 s. Each passed guard exit 0, exactly one normal finish,
empty run stderr and dispatch log, and exact `0000`/`0001` VTUs. Their binary,
source, runner, manifest, base and static SHA-256 match the pinned files.
NEW non-overwriting full-farm pulls at
`results/static_pilots_20261021/<host>/<case>/atmosphere/` passed remote/local
checksum dry-runs. Independent validation passed exact 0.099999998-Myr age,
finite-positive 25-Msun finite-GMC initial mass/density/pressure and stable
evolved outer 2.5 pc with pressure anchor 20 pc. Maximum density drift is
0.0020141/0.0020131 and maximum speed is 0.345548/0.345166 km/s. The
506 potential-front cells are only a mesh calculation: ionization is off.

For the staged direct-MS winds, use prior same-host measured 40-Msun
static/wind ratios, with an additional 1.5 runtime allowance. Keohane1's
15433.040-s static and 19730.874-s wind give
`23924.339 * 19730.874 / 15433.040 * 1.5 = 45880.279 s`, above the
43200-s 80%-of-54000-s safety ceiling. Its wind remains **HELD** pending
Jonathan's explicit guard decision; do not change the guard or launch it
silently. Keohane2's measured 10509.521-s static and 10078.430-s wind give
`23926.525 * 10078.430 / 10509.521 * 1.5 = 34417.621 s`, below that
ceiling. These are scheduling estimates across wind physics/meshes, not
measured 25-Msun wind durations. Keohane2 was idle with 46 GiB memory
available, zero swap use and 111 GiB disk free. A NEW matching wind farm
`/tmp/van_marle_m25_n20000b2000_c20480f31_ms_wind_20261021_farm/`
had an empty output directory and matching pinned x86-64 binary, 25-track
source, runner, manifest, base and wind SHA-256. The runner was made
executable without changing its hash. The matching wind launched once under
an explicit 54,000-s guard at 04:12 EDT; its first VTU, one AMRVAC rank,
empty stderr/dispatch log and post-launch binary/base/wind SHA passed.
It is not yet a validated endpoint. Keohane3/4 guarded winds and
Pauley404-03 static remain untouched.

## Keohane3/4 wind endpoints and Pauley404-03 static (2026-10-21 07:07 EDT)

Keohane3 GMC1000 and Keohane4 GMC2000 16,384-cell direct-MS winds finished
in 14773.173/14712.560 s. Both passed guard exit 0, exactly one normal
finish, empty run stderr and dispatch log, seven exact `0000`--`0006` VTUs,
and pinned binary/source/runner/manifest/base/wind SHA-256. NEW
non-overwriting full-farm pulls under
`results/direct_ms_pilots_20261021/Keohane{3,4}/<case>/wind/` matched the
remote checksums. Independent `validate_cloud_mass.py` passed exact
0.001499999965-Myr age, finite-positive 25-Msun finite-GMC initial fields,
stable evolved outer 2.5 pc/pressure anchor 20 pc, speeds
1500.536/1500.538 km/s and fluxes 1.997661e-7/1.997652e-7 Msun/yr.
NEW full-domain and inner-0.2-pc density/velocity profiles and snapshot CSVs
in `results/direct_ms_diagnostics_20261021/Keohane{3,4}/` were visually
checked. They remain short unpreconditioned MS pilots, not RSG/WR bubbles,
physical shell-width measurements, convergence tests or GRB walls.

Pauley404-03 GMC1000 4096-cell no-wind/no-ionization static finished in
35145.846 s. It passed guard exit 0, one finish, empty run stderr and
dispatch log, exact `0000`/`0001` VTUs and pinned arm64 binary/source/
runner/manifest/base/static SHA-256. Its NEW non-overwriting full-farm pull
at `results/static_pilots_20261021/Pauley404-03/<case>/atmosphere/` matched
the remote checksum dry-run. Independent validation passed exact
0.099999998-Myr age, finite-positive 25-Msun finite-GMC initial fields,
stable evolved outer 2.5 pc/pressure anchor 20 pc, maximum density drift
0.00241095 and maximum speed 0.151536 km/s. The 747 potential-front cells
are only a mesh diagnostic because ionization is off.

For its matching staged direct-MS wind, Pauley404-03's prior same-host
40-Msun 16,384-cell static/wind durations were 27072.209/22013.375 s.
Applying that measured ratio to this host's completed 25-Msun static and
a further 1.5 allowance gives
`35145.846 * 22013.375 / 27072.209 * 1.5 = 42867.504 s`.
That is below 43200 s (80% of the proposed explicit 54000-s guard), but
only by 332.496 s; it is a cross-physics/cross-mesh scheduling estimate,
not a measured 25-Msun wind duration. Before launch require the matching
25-track arm64 binary/source/runner/manifest/base/wind SHA, idle/resources,
and a NEW empty-output farm. Do not change Xcode/Tailscale or retry a failed
AMRVAC case automatically. The separate 40-Msun GMC2000 wind remains HELD.

The exact staged direct-MS manifest verifier passed all seven cases again.
Pauley404-03 was idle with 32 GiB RAM, 0.25 MiB used swap and 515 GiB free
disk. A NEW empty-output farm at
`/private/tmp/van_marle_m25_n20000b1000_c4096f12_ms_wind_20261021_mac_farm/`
received only its matching 25-track arm64 binary/source, Mac runner,
manifest, base and wind namelist. All transferred SHA-256 values match the
pinned local files. The wind launched once at 07:12 EDT under an explicit
54,000-s guard using Homebrew Python. First VTU, one AMRVAC process, empty
stderr/dispatch log and post-launch binary/source/base/wind SHA passed.
It is not a validated endpoint; require guard exit 0, one finish, empty
stderr, seven exact VTUs, exact 0.0015-Myr/finite-GMC initial and outer,
1500-km/s/2e-7-Msun-per-year checks, then a NEW pull and diagnostics.

Last touched (2026-10-21 22:38 UTC): final K1/K2/Mac03 NEW result mirrors,
validation/provenance JSON, three profile figures/snapshot CSVs, seven-host
endpoint inventory, this README and root handoff/TODO. Commands: exact
input verifier, read-only SSH exit/marker/SHA checks, non-overwriting rsync
and checksum dry-runs, independent validator through temporary flat views,
strict snapshot-age checks, profile plotting and visual inspection. All
seven statics/winds reconciled; no simulation restarted. Monitor shutdown
resolved at22:41 UTC via app view/update and read-only persisted-state
verification; this README and root handoff/TODO updated, no science
products regenerated or SSH performed in the shutdown turn. Remaining:
separate 40-Msun reconciliation and the scientific limitations stated above.
