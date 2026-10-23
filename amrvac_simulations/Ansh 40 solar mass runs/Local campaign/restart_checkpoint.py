# Purpose: Verify saved pause checkpoints and independently restart cases after their original processes exit.
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys

from pause_runs import CASES, MANIFEST, ROOT, processes
from validation_tools.audit_native import YEAR_CODE, audit


def prepare(case, verify=False):
    saved = json.loads(MANIFEST.read_text())['cases'][case]
    checkpoint = (ROOT / saved['checkpoint']).resolve()
    initial = audit(checkpoint)
    fingerprint = 'mod_usr.t SHA256: ' + hashlib.sha256((ROOT/'mod_usr.t').read_bytes()).hexdigest()
    if fingerprint not in (ROOT/'build_info.txt').read_text():
        raise RuntimeError('Executable/source fingerprint mismatch')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    folder = ROOT / ('restart_checks' if verify else 'restarted_runs') / (case + '_' + stamp)
    folder.mkdir(parents=True)
    (folder/'output').mkdir()
    original = ROOT/case
    for filename in ('mod_usr.t', 'stellar_evolution.dat'):
        shutil.copy2(original/filename, folder/filename)
    # A relative path avoids AMRVAC's command-line path parsing limitations.
    # AMRVAC parses the trailing four-digit snapshot number from this filename.
    shutil.copy2(checkpoint, folder/checkpoint.name)
    par = (original/'run.par').read_text()
    if verify:
        end_code = (initial['age_yr'] + 0.25) * YEAR_CODE
        par = re.sub(r'time_max=\S+', f'time_max={end_code:.17e}', par)
    (folder/'run.par').write_text('! Purpose: ' + ('Short isolated restart verification.' if verify else
        'Continue this case from its saved pause checkpoint with separate output files.') + '\n' + par)
    (folder/'restart_info.json').write_text(json.dumps({'purpose': 'Checkpoint origin and preserved physical start age.',
        'case': case, 'checkpoint': str(checkpoint.relative_to(ROOT)),
        'checkpoint_local_name': checkpoint.name, 'age_yr': initial['age_yr'],
        'verification_only': verify}, indent=2) + '\n')
    return folder


def worker(folder):
    folder = folder.resolve()
    if folder.parent not in (ROOT/'restart_checks', ROOT/'restarted_runs'):
        raise RuntimeError('Unexpected restart directory')
    info = json.loads((folder/'restart_info.json').read_text())
    command = ['mpirun', '--bind-to', 'none', '-np', '1', str(ROOT/'build/amrvac'),
               '-i', 'run.par', '-if', info['checkpoint_local_name']]
    with (folder/'run.log').open('x') as stream:
        stream.write('# Purpose: Independent checkpoint restart transcript.\n')
        stream.flush()
        process = subprocess.Popen(command, cwd=folder, stdout=stream, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, env={**os.environ, 'OMP_NUM_THREADS': '1'})
        while True:
            try:
                code = process.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                log = folder/'output/test.log'
                if log.exists():
                    with log.open('rb') as numerical:
                        numerical.seek(max(0, log.stat().st_size-4096))
                        bad = re.search(rb'\b(?:NaN|Infinity)\b', numerical.read(), re.I)
                    if bad:
                        process.terminate()
                        raise RuntimeError('Restart numerical log contains NaN/Infinity')
    if code:
        raise RuntimeError(f'AMRVAC exited with code {code}; inspect {folder}/run.log')
    transcript = (folder/'run.log').read_text(errors='replace')
    if 'Finished AMRVAC' not in transcript:
        raise RuntimeError('Missing completion marker')
    rows = [audit(path) for path in sorted((folder/'output').glob('test*.dat'))]
    target = float(re.search(r'time_max=(\S+)', (folder/'run.par').read_text()).group(1))/YEAR_CODE
    if not rows or not math.isclose(rows[-1]['age_yr'], target, rel_tol=1e-10):
        raise RuntimeError('Restart did not reach its target age')
    info = json.loads((folder/'restart_info.json').read_text())
    case = info['case']
    if ('Spitzer HD par:' in transcript) != (case.split('_')[1]=='on'):
        raise RuntimeError('Conduction activation mismatch')
    if ('Cooling Tfix enabled: T' in transcript) != (case.split('_')[3]=='on'):
        raise RuntimeError('Cooling activation mismatch')
    (folder/'restart_result.json').write_text(json.dumps({'purpose': 'Independent restart completion audit.',
        'passed': True, 'start_age_yr': info['age_yr'], 'end_age_yr': rows[-1]['age_yr'],
        'snapshots_audited': len(rows)}, indent=2)+'\n')
    print(f"PASS {case}: {info['age_yr']:.6f} -> {rows[-1]['age_yr']:.6f} yr", flush=True)


def start(case):
    if case in processes():
        raise RuntimeError('An original process for this case still exists; use pause_runs.py resume instead')
    # Refuse a duplicate independently restarted case too.
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        try:
            cwd = (proc/'cwd').resolve()
            if cwd.parent == ROOT/'restarted_runs' and cwd.name.startswith(case+'_'):
                raise RuntimeError('A restarted process for this case already exists')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    folder = prepare(case)
    with (folder/'supervisor.log').open('x') as stream:
        stream.write('# Purpose: Persistent independent checkpoint-restart supervisor.\n')
        stream.flush()
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_worker',
            '--folder', str(folder)], cwd=folder, stdout=stream, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
    (folder/'supervisor_pid.txt').write_text('# Purpose: Identify this independent restart worker.\n'+str(child.pid)+'\n')
    print('Restart launched:', folder, 'supervisor PID:', child.pid, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['verify', 'start', '_worker'])
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--folder', type=Path)
    args = parser.parse_args()
    if args.action == '_worker':
        if args.folder is None: parser.error('Worker requires --folder')
        worker(args.folder)
    elif args.action == 'verify':
        for case in CASES if args.case=='all' else (args.case,):
            worker(prepare(case, verify=True))
    else:
        if args.case=='all': parser.error('Select one case to restart independently')
        start(args.case)
