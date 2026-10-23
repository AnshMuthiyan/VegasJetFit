# Purpose: Reproduce and isolate the phase-2 restart NaN using copied inputs and a shared original checkpoint.
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parent
sys.path.insert(0, str(BUNDLE))
from plot_dat_folder import read_snapshot

YEAR_CODE = 3.1536e7 / 3.0857e11


def set_value(text, key, value, section):
    pattern = r'(?mi)^\s*' + re.escape(key) + r'\s*=[^\n]*'
    if re.search(pattern, text):
        return re.sub(pattern, '\n ' + key + '=' + value, text)
    return re.sub(r'(?mi)^&' + section + r'\s*$',
                  '&' + section + '\n ' + key + '=' + value, text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', required=True, type=Path)
    parser.add_argument('--ranks', type=int, default=8)
    parser.add_argument('--years', type=float, default=500)
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--cases', nargs='+', default=['both', 'cooling_only', 'conduction_only'])
    parser.add_argument('--label', default='baseline')
    parser.add_argument('--ghost-copy', action='store_true')
    parser.add_argument('--primitive-prolong', action='store_true')
    parser.add_argument('--courant', type=float, default=0.02)
    parser.add_argument('--sts-dtpar', type=float, default=0.1)
    parser.add_argument('--save-years', type=float, default=50)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--start-age-years', type=float, default=4.3e6)
    parser.add_argument('--source-dir', type=Path)
    parser.add_argument('--steps', type=int, help='Stop after this many fixed-work benchmark iterations instead of the requested duration.')
    args = parser.parse_args()
    batch = HERE / (time.strftime('%Y%m%d_%H%M%S') + '_' + args.label)
    batch.mkdir()
    checkpoint = args.checkpoint.resolve() if args.checkpoint else BUNDLE / 'tc_on_rc_on/test0011.dat'
    original = (BUNDLE / 'tc_on_rc_on/run.par').read_text()
    history = BUNDLE / 'stellar_evolution.dat'
    for name in ['mod_usr.t', 'amrvac.h']:
        shutil.copy2((args.source_dir or BUNDLE)/name, batch/name)
    shutil.copy2(history, batch/history.name)
    state = read_snapshot(checkpoint)
    if state['invalid_cells']:
        raise RuntimeError('Source checkpoint contains invalid cells')
    report = {'purpose': 'Source-term isolation at a deliberately reset 4.3 Myr stellar age.',
              'checkpoint': str(checkpoint), 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
              'original_age_years': state['age_years'], 'executable': str(args.executable),
              'executable_sha256': hashlib.sha256(args.executable.read_bytes()).hexdigest(),
              'target_duration_years': args.years, 'ranks': args.ranks, 'cases': [],
              'start_age_years': args.start_age_years}
    report['fixed_steps']=args.steps
    report.update(ghost_copy=args.ghost_copy, primitive_prolong=args.primitive_prolong,
                  courant=args.courant, sts_dtpar=args.sts_dtpar)
    settings = {'both': (True, True), 'cooling_only': (False, True), 'conduction_only': (True, False),
                'neither': (False, False), 'both_ghost_copy': (True, True)}
    env = dict(os.environ, OMP_NUM_THREADS='1')
    for name in args.cases:
        tc, rc = settings[name]
        folder = batch/name
        folder.mkdir()
        (folder/'output').mkdir()
        shutil.copy2(checkpoint, folder/checkpoint.name)
        text = original
        values = [('restart_from_file', repr(checkpoint.name), 'filelist'),
                  ('base_filename', "'output/test'", 'filelist'),
                  ('reset_time', '.true.', 'stoplist'), ('time_init', f'{args.start_age_years*YEAR_CODE:.17e}', 'stoplist'),
                  ('reset_it', '.true.', 'stoplist'), ('it_init', '0', 'stoplist'),
                  ('time_max', f'{(args.start_age_years+args.years)*YEAR_CODE:.17e}', 'stoplist'),
                  ('it_max', str(args.steps or 8000000), 'stoplist'), ('wall_time_max', '1.d99', 'stoplist'),
                  ('courantpar', f'{args.courant:.17e}', 'paramlist'),
                  ('sts_dtpar', f'{args.sts_dtpar:.17e}', 'sts_list'),
                  ('hd_thermal_conduction', '.true.' if tc else '.false.', 'hd_list'),
                  ('hd_radiative_cooling', '.true.' if rc else '.false.', 'hd_list'),
                  ('stellar_param_file', "'../stellar_evolution.dat'", 'usr_list'),
                  ('dtsave_dat', f'{args.save_years*YEAR_CODE:.17e}', 'savelist')]
        if args.ghost_copy or name == 'both_ghost_copy':
            values.append(('ghost_copy', '.true.', 'boundlist'))
        if args.primitive_prolong:
            values.extend([('prolongprimitive', '.true.', 'meshlist'),
                           ('coarsenprimitive', '.false.', 'meshlist')])
        if args.steps:
            values.extend([('itsave(1,2)','1000000000','savelist'),
                           ('autoconvert','.false.','filelist')])
        for key, value, section in values:
            text = set_value(text, key, value, section)
        (folder/'run.par').write_text('! Purpose: Isolated phase-2 diagnostic: ' + name + '.\n' + text)
        command = ['mpirun', '--bind-to', 'none', '--oversubscribe', '-np', str(args.ranks),
                   str(args.executable), '-i', 'run.par']
        print('RUN', name, 'folder=', folder, flush=True)
        start = time.monotonic()
        with (folder/'run.log').open('w') as stream:
            stream.write('# Purpose: AMRVAC diagnostic transcript, including floating-point backtraces.\n')
            stream.flush()
            try:
                process = subprocess.Popen(command, cwd=folder, env=env, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                code = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                code = 'timeout'
        log = (folder/'run.log').read_text(errors='replace')
        row = {'case': name, 'returncode': code, 'wall_seconds': time.monotonic()-start,
               'completed': code == 0 and 'Finished AMRVAC' in log, 'log': str(folder/'run.log')}
        row['physics_flags_match'] = (('Spitzer HD par:' in log)==tc and
                                      ('Cooling Tfix enabled: T' in log)==rc)
        snapshots = sorted((folder/'output').glob('test*.dat'))
        if snapshots:
            final = read_snapshot(snapshots[-1], folder/'run.par')
            row.update(last_saved_age_years=final['age_years'], invalid_cells=final['invalid_cells'])
            finished_target = final['iteration']==args.steps if args.steps else math.isclose(
                final['age_years'], args.start_age_years+args.years, abs_tol=1e-5)
            row['passed'] = row['completed'] and row['physics_flags_match'] and not final['invalid_cells'] and finished_target
        loop_time=re.search(r'Total timeloop took\s*:\s*([0-9.Ee+-]+)',log)
        if loop_time:
            row['timeloop_seconds']=float(loop_time.group(1))
        report['cases'].append(row)
        (batch/'results.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(row), flush=True)
        if not row['completed']:
            print(log[-6500:], flush=True)
    print('REPORT', batch/'results.json', flush=True)


if __name__ == '__main__':
    main()
