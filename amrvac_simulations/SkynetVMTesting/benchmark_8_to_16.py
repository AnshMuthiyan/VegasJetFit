# Purpose: Benchmark every MPI rank count from 8 through 16 using identical saved states and fixed work.
import argparse
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
CASES = ('tc_off_rc_off', 'tc_on_rc_off', 'tc_off_rc_on', 'tc_on_rc_on')
YEAR_CODE = 3.1536e7 / 3.0857e11
COLUMNS = ('case', 'ranks', 'repeat', 'status', 'start_iteration', 'end_iteration',
           'steps', 'wall_seconds', 'timeloop_seconds', 'steps_per_second',
           'start_age_years', 'end_age_years', 'guard_events', 'error', 'folder')


def snapshot(path):
    """Inspect native v5 HD data, including every physical cell, without external packages."""
    data = path.read_bytes()
    if len(data) < 100:
        raise ValueError('Truncated checkpoint: ' + str(path))
    version, tree, blocks, nw, ndir, ndim, level, leaves, parents, iteration = struct.unpack_from('<10i', data)
    if (version, nw, ndir, ndim) != (5, 3, 1, 1):
        raise ValueError('Expected native v5 1D, three-variable HD checkpoint: ' + str(path))
    age = struct.unpack_from('<d', data, 40)[0]
    block_nx = struct.unpack_from('<i', data, 68)[0]
    if not math.isfinite(age) or age < 0 or leaves < 1 or iteration < 0:
        raise ValueError('Invalid checkpoint header')
    parameter_offset = 96 + 16 * nw + 16
    count = struct.unpack_from('<i', data, parameter_offset)[0]
    values = struct.unpack_from('<' + str(count) + 'd', data, parameter_offset + 4)
    names_offset = parameter_offset + 4 + 8 * count
    names = [data[names_offset+16*j:names_offset+16*(j+1)].decode().strip() for j in range(count)]
    gamma = dict(zip(names, values))['gamma']
    table = tree + 4 * (leaves + parents)
    offsets = struct.unpack_from('<' + str(leaves) + 'q', data, table + 8 * leaves)
    if table + 16 * leaves != blocks:
        raise ValueError('Invalid checkpoint block table')
    for offset in offsets:
        low, high = struct.unpack_from('<2i', data, offset)
        size = block_nx + low + high
        state = struct.unpack_from('<' + str(size * 3) + 'd', data, offset + 8)
        for j in range(low, low + block_nx):
            rho, momentum, energy = state[j], state[size+j], state[2*size+j]
            if not all(math.isfinite(x) for x in (rho, momentum, energy)) or rho <= 0:
                raise ValueError('Nonfinite cell or nonpositive density in ' + str(path))
            pressure = (gamma - 1) * (energy - 0.5 * momentum**2 / rho)
            if not math.isfinite(pressure) or pressure <= 0:
                raise ValueError('Nonpositive recovered pressure in ' + str(path))
    return {'iteration': iteration, 'age_code': age, 'age_years': age / YEAR_CODE,
            'blocks': leaves, 'sha256': hashlib.sha256(data).hexdigest()}


def parameter(text, key):
    match = re.search(r'(?mi)^\s*' + re.escape(key) + r'\s*=\s*([^!\n]+)', text)
    if not match:
        raise ValueError('Missing parameter: ' + key)
    return match.group(1).strip().strip("'\"")


def update_parameter(text, section, key, value):
    pattern = re.compile(r'(?ims)(^\s*&' + section + r'\s*\n)(.*?)(^\s*/\s*$)')
    match = pattern.search(text)
    if not match:
        raise ValueError('Missing namelist: ' + section)
    body = re.sub(r'(?mi)^\s*' + re.escape(key) + r'\s*=.*\n?', '', match.group(2))
    body += ' ' + key + '=' + value + '\n'
    return text[:match.start()] + match.group(1) + body + match.group(3) + text[match.end():]


def select_inputs(case, explicit, steps):
    folders = [ROOT / case, *sorted(ROOT.glob('production_*_' + case))]
    paths = [explicit.resolve()] if explicit else [p for folder in folders for p in
             [*folder.glob('test*.dat'), *folder.glob('output/test*.dat')]]
    if not paths:
        raise ValueError('No checkpoint found for ' + case)
    # Select by physical stellar age, not filesystem modification time.
    candidates = []
    for path in paths:
        try:
            info = snapshot(path)
        except (ValueError, KeyError, struct.error, OSError) as exc:
            if explicit:
                raise
            print('Skipping invalid checkpoint %s: %s' % (path, exc), flush=True)
            continue
        candidates.append((info['age_code'], info['iteration'], str(path), path, info))
    if not candidates:
        raise ValueError('No valid checkpoint found for ' + case)
    _, _, _, path, info = max(candidates)
    if info['iteration'] + steps > 9000000:
        raise ValueError('Reduce --steps to avoid AMRVAC iteration-counter rollover for ' + case)
    par_path = (path.parent.parent if path.parent.name == 'output' else path.parent) / 'run.par'
    if not par_path.exists():
        raise ValueError('Checkpoint requires its matching run.par: ' + str(par_path))
    text = par_path.read_text()
    for key, expected in [('hd_thermal_conduction', case.split('_')[1]),
                          ('hd_radiative_cooling', case.split('_')[3])]:
        if parameter(text, key).lower() != ('.true.' if expected == 'on' else '.false.'):
            raise ValueError('Physics mismatch for ' + case)
    if parameter(text, 'reset_time').lower() != '.false.':
        raise ValueError('Do not reset stellar age for a restart benchmark')
    history = (par_path.parent / parameter(text, 'stellar_param_file')).resolve()
    if not history.is_file():
        raise ValueError('Missing wind history: ' + str(history))
    return path, info, text, history


def busy_jobs():
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            args = (entry / 'cmdline').read_bytes().split(b'\0')
            state = (entry / 'stat').read_text().rsplit(')', 1)[1].split()[0]
            if args[0] and Path(os.fsdecode(args[0])).name == 'amrvac' and state not in ('T', 't', 'Z'):
                found.append(entry.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return found


def write_summary(batch, rows):
    with (batch / 'summary.csv').open('w', newline='') as stream:
        stream.write('# Purpose: Equal-work MPI scaling measurements; only PASS rows are comparable.\n')
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def stop_child(child):
    if child.poll() is None:
        if os.getpgid(child.pid) != child.pid:
            raise RuntimeError('Unexpected test process group; refusing to signal it')
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()


def execute(folder, row, executable, timeout, verbose):
    command = ['mpirun', '--use-hwthread-cpus', '--bind-to', 'none', '-np', str(row['ranks']),
               str(executable), '-i', 'run.par']
    started = time.monotonic()
    child = None
    try:
        with (folder / 'run.log').open('x') as stream:
            stream.write('# Purpose: Independent fixed-iteration MPI benchmark transcript.\n')
            stream.flush()
            child = subprocess.Popen(command, cwd=folder, stdin=subprocess.DEVNULL, stdout=stream,
                stderr=subprocess.STDOUT, start_new_session=True, env={**os.environ, 'OMP_NUM_THREADS': '1'})
            while child.poll() is None:
                if time.monotonic() - started > timeout:
                    raise TimeoutError('Test exceeded --timeout, including final output/shutdown')
                if verbose and time.monotonic() - started >= verbose[0]:
                    print('  Still running: %.0f seconds; log: %s' %
                          (time.monotonic() - started, folder / 'run.log'), flush=True)
                    verbose[0] += 30
                time.sleep(0.2)
        row['wall_seconds'] = time.monotonic() - started
        text = (folder / 'run.log').read_text(errors='replace')
        if child.returncode or 'Finished AMRVAC' not in text:
            raise RuntimeError('Missing successful AMRVAC completion; exit code ' + str(child.returncode))
        if ('Spitzer HD par:' in text) != (row['case'].split('_')[1] == 'on'):
            raise RuntimeError('Runtime conduction activation mismatch')
        if ('Cooling Tfix enabled: T' in text) != (row['case'].split('_')[3] == 'on'):
            raise RuntimeError('Runtime cooling activation mismatch')
        if re.search(r'\b(?:NaN|Infinity)\b', text, re.I):
            raise RuntimeError('Nonfinite value reported in transcript')
        outputs = [(snapshot(path), path) for path in (folder / 'output').glob('test*.dat')]
        if not outputs:
            raise RuntimeError('No final native checkpoint')
        final, _ = max(outputs, key=lambda item: item[0]['age_code'])
        row.update(end_iteration=final['iteration'], end_age_years=final['age_years'])
        if final['iteration'] != row['end_iteration_expected'] or final['age_years'] <= row['start_age_years']:
            raise RuntimeError('Wrong final iteration or stellar age')
        match = re.search(r'Total timeloop took\s*:\s*([\d.Ee+-]+)', text)
        row['timeloop_seconds'] = float(match.group(1)) if match else ''
        row['steps_per_second'] = row['steps'] / row['wall_seconds']
        guard = folder / 'output/test_guard.csv'
        if guard.exists():
            lines = [line for line in guard.read_text().splitlines() if line and not line.startswith('#')]
            row['guard_events'] = float(list(csv.DictReader(lines))[-1]['rescue_events'])
        row['status'] = 'PASS'
    except KeyboardInterrupt:
        row.update(status='INTERRUPTED', error='Stopped by user')
        raise
    except Exception as exc:
        row.update(status='FAIL', error=str(exc))
    finally:
        if child is not None:
            stop_child(child)
        row.setdefault('wall_seconds', time.monotonic() - started)
        row.pop('end_iteration_expected', None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--steps', type=int, default=50000)
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--min-ranks', type=int, default=8)
    parser.add_argument('--max-ranks', type=int, default=16)
    parser.add_argument('--timeout', type=float, default=600, help='External per-test timeout in seconds')
    parser.add_argument('--checkpoint', type=Path, help='Explicit checkpoint; requires one selected case')
    parser.add_argument('--executable', type=Path, default=ROOT / 'amrvac')
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks_8_16')
    parser.add_argument('--prepare-only', action='store_true', help='Write and inspect inputs without launching MPI')
    args = parser.parse_args()
    if args.steps < 1 or args.repeats < 1 or not 1 <= args.min_ranks <= args.max_ranks or args.timeout <= 0:
        parser.error('Steps, repeats, timeout, and rank counts must be positive and ordered')
    if args.checkpoint and args.case == 'all':
        parser.error('--checkpoint requires one case')
    executable = args.executable.resolve()
    selected = CASES if args.case == 'all' else (args.case,)
    prepared = {case: select_inputs(case, args.checkpoint, args.steps) for case in selected}
    if not args.prepare_only:
        if os.name != 'posix' or not executable.is_file() or not os.access(executable, os.X_OK):
            parser.error('Run on Linux with a compiled executable; use --prepare-only to inspect inputs elsewhere')
        if not shutil.which('mpirun'):
            parser.error('mpirun is not on PATH')
        allowed = len(os.sched_getaffinity(0))
        if args.max_ranks > allowed:
            parser.error('Requested %d ranks but only %d CPUs are available' % (args.max_ranks, allowed))
        busy = busy_jobs()
        if busy:
            parser.error('Stop/pause your other AMRVAC runs first for a fair benchmark; active PIDs: ' + ','.join(busy))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    batch = args.output.resolve() / stamp
    batch.mkdir(parents=True)
    metadata = {'purpose': 'Equal-work benchmark inputs and provenance; all tests run sequentially.',
                'steps_per_test': args.steps, 'rank_counts': list(range(args.min_ranks, args.max_ranks+1)),
                'repeats': args.repeats, 'executable': str(executable), 'checkpoints': {}}
    if executable.is_file():
        metadata['executable_sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
    shutil.copy2(ROOT / 'mod_usr.t', batch / 'mod_usr.t')
    jobs = []
    for case, (path, info, text, history) in prepared.items():
        case_folder = batch / case
        (case_folder / 'checkpoints').mkdir(parents=True)
        copied = case_folder / 'checkpoints' / path.name
        shutil.copy2(path, copied)
        if snapshot(copied)['sha256'] != info['sha256']:
            raise RuntimeError('Checkpoint changed during copying; stop the producer and retry')
        shutil.copy2(history, case_folder / 'stellar_evolution.dat')
        metadata['checkpoints'][case] = {'source': str(path), **info}
        for repeat in range(1, args.repeats+1):
            for ranks in range(args.min_ranks, args.max_ranks+1):
                folder = case_folder / ('cores_%02d_repeat_%02d' % (ranks, repeat))
                (folder / 'output').mkdir(parents=True)
                par = text
                for section, key, value in [('filelist','restart_from_file', "'../checkpoints/" + path.name + "'"),
                    ('filelist','base_filename', "'output/test'"), ('filelist','firstprocess','.false.'),
                    ('stoplist','it_max',str(info['iteration']+args.steps)),
                    ('stoplist','wall_time_max','1.d99'), ('stoplist','reset_time','.false.'),
                    ('stoplist','reset_it','.false.'), ('usr_list','stellar_param_file',"'../stellar_evolution.dat'")]:
                    par = update_parameter(par, section, key, value)
                par = '! Purpose: Fixed-work %d-rank benchmark for %s; production inputs are unchanged.\n' % (ranks, case) + par
                (folder / 'run.par').write_text(par)
                jobs.append((folder, {'case':case, 'ranks':ranks, 'repeat':repeat, 'status':'PREPARED',
                    'start_iteration':info['iteration'], 'end_iteration_expected':info['iteration']+args.steps,
                    'steps':args.steps, 'start_age_years':info['age_years'], 'folder':str(folder.relative_to(batch))}))
    (batch / 'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print('Results folder:', batch, flush=True)
    print('%d tests; %d steps each; rank counts %d through %d inclusive.' %
          (len(jobs),args.steps,args.min_ranks,args.max_ranks), flush=True)
    if args.prepare_only:
        print('Preparation only: no simulations were launched.', flush=True)
        return
    rows = []
    try:
        for index, (folder,row) in enumerate(jobs,1):
            print('[%d/%d] %s: %d ranks, repeat %d' %
                  (index,len(jobs),row['case'],row['ranks'],row['repeat']), flush=True)
            try:
                execute(folder,row,executable,args.timeout,[30])
            finally:
                rows.append(row)
                write_summary(batch,rows)
            print('  %s: %.3f s; %s' % (row['status'],row['wall_seconds'],row.get('error','')), flush=True)
    except KeyboardInterrupt:
        print('Benchmark stopped; completed results preserved in',batch,flush=True)
        return 130
    winners = []
    for case in selected:
        times = {}
        for ranks in range(args.min_ranks,args.max_ranks+1):
            group = [r for r in rows if r['case']==case and r['ranks']==ranks]
            if len(group)==args.repeats and all(r['status']=='PASS' for r in group):
                times[ranks] = statistics.median(r['wall_seconds'] for r in group)
        if times:
            best = min(times,key=times.get)
            winners.append('%s: fastest measured = %d ranks (median %.3f s)' % (case,best,times[best]))
    (batch / 'fastest.txt').write_text('# Purpose: Fastest successfully completed equal-work configurations.\n'+'\n'.join(winners)+'\n')
    print('\n'.join(winners),flush=True)
    print('Summary:',batch/'summary.csv',flush=True)
    return 1 if any(r['status']!='PASS' for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
