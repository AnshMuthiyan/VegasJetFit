# Purpose: Checkpoint and suspend live runs; resume individual cases without reinitializing them.
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

from validation_tools.audit_native import audit

ROOT = Path(__file__).resolve().parent
CASES = ('tc_off_rc_off', 'tc_on_rc_off', 'tc_off_rc_on', 'tc_on_rc_on')
MANIFEST = ROOT / 'pause_state.json'


def identity(pid):
    proc = Path('/proc') / str(pid)
    args = (proc / 'cmdline').read_bytes().split(b'\0')
    if not args[0] or Path(os.fsdecode(args[0])).resolve() != (ROOT / 'build/amrvac').resolve():
        raise RuntimeError(f'PID {pid} is not this campaign executable')
    stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'start_ticks': stat[19], 'state': stat[0],
            'case': (proc / 'cwd').resolve().name}


def processes():
    found = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            item = identity(int(entry.name))
            if item['case'] in CASES:
                if item['case'] in found:
                    raise RuntimeError('Multiple production ranks found; refuse partial MPI suspension')
                found[item['case']] = item
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        except RuntimeError as exc:
            if 'not this campaign executable' not in str(exc):
                raise
    return found


def write_state(state):
    temporary = MANIFEST.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(MANIFEST)


def pause():
    live = processes()
    if set(live) != set(CASES):
        raise RuntimeError('Expected one live production process per case; found ' + str(live))
    if any(item['state'] in ('T', 't') for item in live.values()):
        raise RuntimeError('Some cases are already paused; use status before another pause')
    before = {case: set((ROOT / case / 'output').glob('test*.dat')) for case in CASES}
    for case in CASES:
        marker = ROOT / case / 'savenow'
        with marker.open('x') as stream:
            stream.write('# Purpose: Request an AMRVAC restart checkpoint before user-requested pause.\n')
    pending = set(CASES)
    state = {'purpose': 'Validated restart checkpoints and exact suspended process identities.',
             'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'cases': {}}
    deadline = time.monotonic() + 60
    while pending and time.monotonic() < deadline:
        for case in tuple(pending):
            new_files = set((ROOT / case / 'output').glob('test*.dat')) - before[case]
            # AMRVAC deletes savenow only after synchronous snapshot and log output finish.
            if (ROOT / case / 'savenow').exists() or not new_files:
                continue
            current = identity(live[case]['pid'])
            if current['start_ticks'] != live[case]['start_ticks']:
                raise RuntimeError('Process identity changed')
            os.kill(current['pid'], signal.SIGSTOP)
            checkpoint = max(new_files, key=lambda p: p.stat().st_mtime_ns)
            # Persist the recovery path immediately, even if the subsequent audit fails.
            state['cases'][case] = {**current, 'state': 'paused',
                                    'checkpoint': str(checkpoint.relative_to(ROOT))}
            write_state(state)
            row = audit(checkpoint)
            state['cases'][case]['checkpoint_age_yr'] = row['age_yr']
            state['cases'][case]['iteration'] = row['iteration']
            write_state(state)
            print(f"PAUSED {case}: checkpoint {row['age_yr']:.6f} yr, PID {current['pid']}", flush=True)
            pending.remove(case)
        if pending:
            time.sleep(0.05)
    if pending:
        # Freeze remaining processes rather than continuing against the user's request.
        for case in pending:
            current = identity(live[case]['pid'])
            os.kill(current['pid'], signal.SIGSTOP)
            state['cases'][case] = {**current, 'state': 'paused', 'checkpoint_error': 'Save request timed out'}
        write_state(state)
        raise RuntimeError('All ranks suspended, but checkpoint requests timed out: ' + str(pending))


def resume(case):
    state = json.loads(MANIFEST.read_text())
    if state['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
        raise RuntimeError('WSL restarted; use the saved disk checkpoint rather than resuming a stale PID')
    selected = CASES if case == 'all' else (case,)
    for name in selected:
        saved = state['cases'][name]
        current = identity(saved['pid'])
        if current['start_ticks'] != saved['start_ticks'] or current['case'] != name:
            raise RuntimeError('Process identity changed; refusing to signal it')
        if current['state'] not in ('T', 't'):
            print(name + ' is already running', flush=True)
            continue
        os.kill(saved['pid'], signal.SIGCONT)
        saved['state'] = 'running'
        write_state(state)
        print('RESUMED ' + name, flush=True)


def status():
    live = processes()
    state = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'cases': {}}
    for case in CASES:
        item = live.get(case)
        label = 'paused' if item and item['state'] in ('T', 't') else 'running' if item else 'not running'
        saved = state['cases'].get(case, {})
        print(case, label, 'checkpoint age [yr]:', saved.get('checkpoint_age_yr', 'unknown'), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['pause', 'resume', 'status'])
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    args = parser.parse_args()
    if args.action == 'pause': pause()
    elif args.action == 'resume': resume(args.case)
    else: status()
