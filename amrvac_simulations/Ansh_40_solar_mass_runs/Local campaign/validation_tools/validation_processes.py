# Purpose: Inspect CPU affinity and stop only explicitly selected repair-test processes.
from pathlib import Path
import argparse
import os
import signal

ROOT=Path(__file__).resolve().parent.parent


def argv(pid):
    try:
        return Path(f'/proc/{pid}/cmdline').read_bytes().decode().rstrip('\0').split('\0')
    except (FileNotFoundError,ProcessLookupError):
        return []


def main(action,tag):
    allowed=os.sched_getaffinity(0)
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        pid=int(entry.name)
        args=argv(pid)
        if not args: continue
        if action in ('status','rebalance') and args[0]==str(ROOT/'build/amrvac'):
            try:
                cwd=Path(f'/proc/{pid}/cwd').resolve()
                if not cwd.is_relative_to(ROOT/'validation'): continue
                before=os.sched_getaffinity(pid)
                print('PID',pid,'case',cwd.name,'CPU affinity',sorted(before),flush=True)
                if action=='rebalance':
                    for task in Path(f'/proc/{pid}/task').iterdir():
                        try: os.sched_setaffinity(int(task.name),allowed)
                        except ProcessLookupError: pass
                    print('Enabled CPUs',sorted(allowed),flush=True)
            except (FileNotFoundError,ProcessLookupError): pass
        controllers={str(ROOT/'validation_tools/repair_tests.py'), str(ROOT/'repair_tests.py')}
        if action=='stop' and controllers.intersection(args) and '--tag' in args:
            if args[args.index('--tag')+1]!=tag: continue
            # Freeze this controller before collecting children so no queued test starts.
            os.kill(pid,signal.SIGSTOP)
            descendants=[pid]
            for parent in descendants:
                try:
                    for task in Path(f'/proc/{parent}/task').iterdir():
                        descendants.extend(child for child in map(int,(task/'children').read_text().split())
                                           if child not in descendants)
                except FileNotFoundError: pass
            for target in reversed(descendants):
                try: os.kill(target,signal.SIGTERM)
                except ProcessLookupError: pass
            try: os.kill(pid,signal.SIGCONT)
            except ProcessLookupError: pass
            (ROOT/'validation'/(tag+'_STOPPED.txt')).write_text(
                '# Purpose: Record stopping superseded reference tests; all evidence retained.\n'
                f'controller_pid={pid}\ntag={tag}\n')
            print('Stopped reference suite',tag,'PIDs',descendants,flush=True)
        elif action=='stop' and (args[0]==str(ROOT/'build/amrvac') or
                (Path(args[0]).name in ('mpirun','orterun') and str(ROOT/'build/amrvac') in args)):
            try:
                cwd=Path(f'/proc/{pid}/cwd').resolve()
                if cwd.parent==ROOT/'validation' and cwd.name.startswith(tag+'_'):
                    os.kill(pid,signal.SIGTERM)
                    print('Stopped remaining worker',pid,cwd.name,flush=True)
            except (FileNotFoundError,ProcessLookupError): pass


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['status','rebalance','stop'])
    parser.add_argument('--tag')
    args=parser.parse_args()
    if args.action=='stop' and not args.tag: parser.error('stop requires an exact test tag')
    main(args.action,args.tag)
