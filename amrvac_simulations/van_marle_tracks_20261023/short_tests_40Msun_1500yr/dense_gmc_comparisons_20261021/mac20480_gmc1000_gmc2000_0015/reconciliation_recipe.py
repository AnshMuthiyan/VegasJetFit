import csv
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

root = Path('/Users/jkeohane/GRBs/AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d')
dispatch_path = root / 'dispatch_records/20261021_gmc2000_mac02.json'
dispatch = json.loads(dispatch_path.read_text())
manifest = Path(dispatch['source_manifest'])
case = dispatch['case']
assert dispatch['host'] == 'Pauley404-02' and dispatch['guard_seconds'] == 64800
row = next(r for r in csv.DictReader(manifest.open()) if r['case'] == case)
assert row['host'] == 'Pauley404-03' and row['guard_seconds'] == '43200'
assert float(row['endpoint_myr']) == 0.0015 and int(row['expected_vtus']) == 7
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == dispatch['sha256']['manifest.csv']
for name in (row['base_file'], case + '.par'):
    assert hashlib.sha256((manifest.parent / name).read_bytes()).hexdigest() == dispatch['sha256'][name]

destination = root / 'results/dense_gmc_wr_local_inner_outer_n20000_gmc2000_mac_20480_f12_0015myr_20261021_mac02/Pauley404-02/n20000b2000/wind'
plots = root / 'results/dense_gmc_plots_20261021/reconciled_n20000b2000_mac02_20480_0015'
inner = root / 'results/dense_gmc_inner_edge_20261021/reconciled_n20000b2000_mac02_20480_0015_agefix'
comparison = root / 'results/dense_gmc_comparisons_20261021/mac20480_gmc1000_gmc2000_0015'
for p in (destination, plots, inner, comparison):
    assert not p.exists(), f'Refusing overwrite or duplicate pull: {p}'

expected = dict(dispatch['sha256'])
expected[dispatch_path.name] = hashlib.sha256(dispatch_path.read_bytes()).hexdigest()
remote_script = r'''
import pathlib,json,sys,hashlib,re,datetime
root=pathlib.Path(sys.argv[1]);case=sys.argv[2];expected=json.loads(sys.argv[3])
sha={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in expected}
assert sha==expected,(sha,expected)
record=json.loads((root/'20261021_gmc2000_mac02.json').read_text())
assert record['host']=='Pauley404-02' and record['guard_seconds']==64800
assert (root/(case+'.run.exit')).read_text().strip()=='0'
log=(root/(case+'.run.log')).read_text()
assert log.count('Finished AMRVAC')==1
assert (root/(case+'.run.err')).stat().st_size==0
assert (root/(case+'.dispatch.log')).stat().st_size==0
paths=sorted(p.name for p in (root/'output').glob('*.vtu'))
assert paths==[case+str(i).zfill(4)+'.vtu' for i in range(7)],paths
pins={}
for line in (root/(case+'.run.sha256')).read_text().splitlines():
 h,p=line.split(maxsplit=1);pins[str(pathlib.Path(p.lstrip('*')))]=h
assert all(sha[p]==h for p,h in pins.items()),pins
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
print(json.dumps({'status':'PASS','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'guard_exit':0,'finish_markers':1,'stderr_bytes':0,'dispatch_bytes':0,'saved_vtus':7,'runtime_s':float(re.search(r'Finished AMRVAC in\s*:\s*([\d.]+)',log).group(1)),'source_pins':sha,'dispatch_pins':pins,'files_sha256':files},sort_keys=True))
'''
ssh = ['ssh', '-x', '-o', 'ForwardX11=no', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10']
command = shlex.join(['/opt/homebrew/bin/python3', '-c', remote_script, dispatch['farm'], case, json.dumps(expected)])
gate = json.loads(subprocess.check_output([ssh[0], '-n', *ssh[1:], 'pauley404-02', command], text=True, timeout=90))
assert gate['runtime_s'] < dispatch['guard_seconds']
destination.mkdir(parents=True, exist_ok=False)
source = 'pauley404-02:' + dispatch['farm'] + '/'
subprocess.run(['rsync', '-a', '--ignore-existing', '-e', shlex.join(ssh), source, str(destination) + '/'], check=True, timeout=180)
dry_run = subprocess.check_output(['rsync', '-rcni', '-e', shlex.join(ssh), source, str(destination) + '/'], text=True, timeout=180)
assert not dry_run.strip(), dry_run
actual = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in destination.rglob('*') if p.is_file()}
assert actual == gate['files_sha256']

os.environ['MPLCONFIGDIR'] = '/private/tmp/amrvac40_mplconfig_20261021'
Path(os.environ['MPLCONFIGDIR']).mkdir(exist_ok=True)
sys.path.insert(0, str(root))
from validate_cloud_mass import validate, RHO_UNIT, MASS_PER_H
from validate_smoke import read_vtu
from plot_dense_gmc_scan import unique_radial_samples
from measure_shell_inner_edge import analyze, case_age_myr
import matplotlib.pyplot as plt

with tempfile.TemporaryDirectory(prefix='amrvac40_mac02_endpoint_', dir='/private/tmp') as temp:
    view = Path(temp)
    for parent in (destination, destination / 'output'):
        for p in parent.iterdir():
            if p.is_file():
                (view / p.name).symlink_to(p)
    validated = validate(view, case, 20000, 0.0015, 7, False, edge_width=0.5,
                         star_mass_msun=40, domain_max_pc=2.5, inner_pc=0.0002,
                         n_bg=2000, finite_gmc=True, atmosphere_outer_pc=20,
                         expected_wind_speed_kms=2000, expected_mdot_msun_yr=1e-5)
    ages = [case_age_myr(read_vtu(view / f'{case}{i:04d}.vtu')[0]) for i in range(7)]
    assert np.allclose(ages, np.linspace(0, 0.0015, 7), rtol=0, atol=1e-9), ages
    analyze(manifest, case, view, inner)

with (destination / 'validation.csv').open('x', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(validated))
    writer.writeheader()
    writer.writerow(validated)

profiles = []
for i in range(7):
    age, raw = read_vtu(destination / 'output' / f'{case}{i:04d}.vtu')
    data = unique_radial_samples(raw)
    profiles.append((case_age_myr(age), data[:, 0], data[:, 1] * RHO_UNIT / MASS_PER_H))
metrics = list(csv.DictReader((inner / 'inner_shell_metrics.csv').open()))
last = metrics[-1]
plots.mkdir(parents=True, exist_ok=False)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
colors = plt.cm.viridis(np.linspace(0.05, 0.9, 7))
for (age, radius, density), color in zip(profiles, colors):
    for ax in axes:
        ax.plot(radius, density, color=color, lw=1.15, label=f'{age * 1000:.2f} kyr')
for ax in axes:
    ax.set(yscale='log', xlabel='Radius (pc)')
    ax.grid(alpha=0.2)
axes[0].set(xscale='log', xlim=(0.0002, 2.5), ylabel=r'$n_{\rm H}$ (cm$^{-3}$)', title='Full evolved domain')
axes[1].set(xlim=(0, 0.09), title='Bubble, inward precursor and swept shell')
axes[1].legend(frameon=False, fontsize=8, ncol=2, loc='lower right')
fig.suptitle('40-Msun direct WR | GMC 2000 cm$^{-3}$ | Pauley404-02 | 20480 cells')
fig.savefig(plots / 'full_density_evolution.png', dpi=180)
plt.close(fig)

reference_inner = root / 'results/dense_gmc_inner_edge_20261020/meeting_n20000b1000_mac20480_0015_agefix/inner_shell_metrics.csv'
reference_metrics = list(csv.DictReader(reference_inner.open()))
reference_root = root / 'results/dense_gmc_wr_local_inner_outer_n20000_gmc1000_mac_20480_f12_0015myr_20261019/Pauley404-02/n20000b1000/wind'
reference_case = 'cloudmass_gmc_n20000b1000_in02oc25m20f12e15_wind'
reference_vtu = reference_root / 'output' / f'{reference_case}0006.vtu'
if not reference_vtu.exists():
    reference_vtu = reference_root / f'{reference_case}0006.vtu'
reference_age, reference_raw = read_vtu(reference_vtu)
reference_data = unique_radial_samples(reference_raw)
assert abs(case_age_myr(reference_age) - ages[-1]) < 1e-9
assert np.array_equal(reference_data[:, 0], profiles[-1][1]), 'Comparison grids differ; do not interpolate silently'
comparison.mkdir(parents=True, exist_ok=False)
fields = ['inner_radius_pc', 'shell_peak_pc', 'shell_fwhm_pc', 'shell_fwhm_cells',
          'shell_contrast', 'inner_ramp_pc', 'inner_ramp_cells', 'shell_inner_nh_cm3']
comparison_rows = []
for current in metrics:
    ref = next(r for r in reference_metrics if abs(float(r['age_myr']) - float(current['age_myr'])) < 1e-10)
    record = {'age_myr': current['age_myr'], 'gmc1000_shell_quality': ref['shell_quality_pass'],
              'gmc2000_shell_quality': current['shell_quality_pass'],
              'gmc1000_ramp_resolved': ref['inner_ramp_resolved'],
              'gmc2000_ramp_resolved': current['inner_ramp_resolved']}
    for field in fields:
        record['gmc1000_' + field] = ref[field]
        record['gmc2000_' + field] = current[field]
        record[field + '_relative_change'] = float(current[field]) / float(ref[field]) - 1
    comparison_rows.append(record)
with (comparison / 'matched_age_metrics.csv').open('x', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(comparison_rows[0]))
    writer.writeheader()
    writer.writerows(comparison_rows)
ref_final = reference_metrics[-1]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
for ax in axes:
    for radius, density, metric, label, color in (
        (reference_data[:, 0], reference_data[:, 1] * RHO_UNIT / MASS_PER_H, ref_final, 'GMC 1000 cm$^{-3}$', '#315f9b'),
        (profiles[-1][1], profiles[-1][2], last, 'GMC 2000 cm$^{-3}$', '#b24538')):
        ax.plot(radius, density, label=label, color=color, lw=1.4)
        ax.axvline(float(metric['inner_radius_pc']), color=color, ls='--', alpha=0.7)
    ax.set(yscale='log', xlabel='Radius (pc)')
    ax.grid(alpha=0.2)
axes[0].set(xlim=(0, 0.09), ylabel=r'$n_{\rm H}$ (cm$^{-3}$)', title='Full bubble and swept shell')
axes[1].set(xlim=(0.0625, 0.065), title='Inner rise; dashed lines mark R10')
axes[1].legend(frameon=False, fontsize=9, loc='lower right')
fig.suptitle('Matched 1.500-kyr endpoints | 40-Msun direct WR | 20480 cells | identical native radius grid')
fig.savefig(comparison / 'matched_endpoint_density.png', dpi=180)
plt.close(fig)

def clean(value):
    if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list): return [clean(v) for v in value]
    return None if isinstance(value, float) and not math.isfinite(value) else value

gate.update(local_checked_at_utc=datetime.now(timezone.utc).isoformat(), remote_host=dispatch['host'],
            remote_farm=dispatch['farm'], local_tree=str(destination), local_files_match_remote=True,
            checksum_dry_run='rsync -rcni; empty output; SSH transport without -n',
            snapshot_ages_myr=ages, validation=validated, dispatch_record=str(dispatch_path),
            manifest_preserved=True, original_manifest_host=row['host'],
            validator_input_view='temporary flat symlinks to unchanged farm records and output snapshots',
            scripts_sha256={name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                            for name in ('validate_cloud_mass.py', 'measure_shell_inner_edge.py', 'plot_dense_gmc_scan.py')},
            comparison_reference_csv=str(reference_inner),
            comparison_reference_csv_sha256=hashlib.sha256(reference_inner.read_bytes()).hexdigest(),
            comparison_reference_vtu_sha256=hashlib.sha256(reference_vtu.read_bytes()).hexdigest(),
            comparison_interpolation='None; both endpoint native radius grids are byte-identical as arrays',
            scientific_limits='Direct-WR pilot; no convergence, physical shock-width, termination-shock or GRB-wall inference')
with (destination / 'endpoint_provenance.json').open('x') as stream:
    json.dump(clean(gate), stream, indent=2, sort_keys=True, allow_nan=False)
    stream.write('\n')
print(json.dumps(clean({'status': 'PASS', 'runtime_s': gate['runtime_s'], 'matched_raw_files': len(actual),
                        'validation': validated, 'endpoint_inner_metrics': last,
                        'matched_endpoint': comparison_rows[-1], 'destination': str(destination),
                        'plots': str(plots), 'inner': str(inner), 'comparison': str(comparison)}), indent=2))
