# Purpose: Launch the four production runs in a persistent WSL background session
# and inspect their progress without tying their lifetime to this chat's shell.
import argparse
import os
import signal
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PID_FILE = HERE / 'campaign_pid.txt'
LOG_FILE = HERE / 'campaign.log'
CASES = ['tc_off_rc_off', 'tc_on_rc_off', 'tc_off_rc_on', 'tc_on_rc_on']


def active_pid():
    if not PID_FILE.exists():
        return None
    for line in PID_FILE.read_text().splitlines():
        if line.startswith('pid='):
            pid = int(line.split('=', 1)[1])
            try:
                cmdline = Path(f'/proc/{pid}/cmdline').read_bytes()
            except FileNotFoundError:
                return None
            if b'manage.py' in cmdline and b'run' in cmdline:
                return pid
    return None


def start(ranks):
    pid = active_pid()
    if pid:
        raise SystemExit(f'Campaign already running: PID {pid}')
    if LOG_FILE.exists():
        raise SystemExit('campaign.log already exists; inspect it before launching another campaign')
    subprocess.run([sys.executable, str(HERE / 'manage.py'), 'validate'], check=True)
    for case in CASES:
        folder = HERE / case
        if (folder / 'run.log').exists() or list((folder / 'output').glob('test*.dat')):
            raise SystemExit(f'{case}: production output exists; refusing to overwrite it')
    with LOG_FILE.open('x') as log:
        log.write('# Purpose: Persistent supervisor log for four sequential 4.77 Myr production runs.\n')
        log.flush()
        process = subprocess.Popen(
            [sys.executable, '-u', str(HERE / 'manage.py'), 'run', '--ranks', str(ranks)],
            cwd=HERE, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True,
            env={**os.environ, 'OMP_NUM_THREADS': '1'})
    PID_FILE.write_text('# Purpose: Identify the persistent production campaign supervisor.\n'
                       f'pid={process.pid}\nMPI_ranks_per_run={ranks}\n'
                       'order='+','.join(CASES)+'\n')
    print(f'Launched persistent campaign: PID {process.pid}; {ranks} ranks per run.', flush=True)


def status():
    pid = active_pid()
    print(f'Supervisor PID: {pid if pid else "not running"}')
    if LOG_FILE.exists():
        print('\nCampaign log:')
        print('\n'.join(LOG_FILE.read_text(errors='replace').splitlines()[-12:]))
    for case in CASES:
        log = HERE / case / 'run.log'
        print(f'\n{case}:')
        if not log.exists():
            print('Queued (not started)')
            continue
        lines = log.read_text(errors='replace').splitlines()
        print('\n'.join(lines[-8:]))
    if pid:
        descendants = [pid]
        for parent in descendants:
            try:
                children = Path(f'/proc/{parent}/task/{parent}/children').read_text()
                descendants.extend(int(child) for child in children.split())
            except FileNotFoundError:
                pass
        subprocess.run(['ps', '-p', ','.join(map(str, descendants)),
                        '-o', 'pid,ppid,stat,etime,pcpu,args', '--forest'], check=True)


def stop():
    pid = active_pid()
    if not pid:
        print('Campaign supervisor is not running.')
        return
    # start_new_session=True gave this supervisor its own process group.
    # Verify the group before stopping it so unrelated jobs are excluded.
    if os.getpgid(pid) != pid:
        raise SystemExit('Unexpected process group; refusing to signal unrelated processes')
    os.killpg(pid, signal.SIGTERM)
    with LOG_FILE.open('a') as log:
        log.write('\n# Campaign stopped: hydro-only run contains nonfinite conserved quantities; retained for diagnosis.\n')
    print(f'Sent SIGTERM to campaign process group {pid}; logs and outputs preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'status', 'stop'])
    parser.add_argument('--ranks', type=int, default=4)
    args = parser.parse_args()
    if args.ranks < 1:
        parser.error('MPI rank count must be positive')
    if args.action == 'start':
        start(args.ranks)
    elif args.action == 'stop':
        stop()
    else:
        status()
