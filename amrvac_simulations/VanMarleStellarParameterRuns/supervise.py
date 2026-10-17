# Purpose: Run four independent production cases concurrently and stop the entire
# campaign if a numerical log becomes nonfinite or any simulation fails.
import argparse
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
CASES=['tc_off_rc_off','tc_on_rc_off','tc_off_rc_on','tc_on_rc_on']


def fail(reason):
    print('CAMPAIGN STOPPED: '+reason,flush=True)
    (HERE/'campaign_failed.txt').write_text('# Purpose: Preserve the reason for automatic campaign shutdown.\n'+reason+'\n')
    # The launcher creates this session/group specifically for this campaign.
    if os.getpgrp()!=os.getpid(): raise RuntimeError('Unexpected campaign process group')
    os.killpg(os.getpgrp(),signal.SIGTERM)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--ranks',type=int,default=1)
    args=parser.parse_args()
    if os.getpgrp()!=os.getpid():
        raise SystemExit('Start with launch_campaign.py start --parallel so shutdown is isolated')
    processes={case:subprocess.Popen([sys.executable,'-u',str(HERE/'manage.py'),
        'run','--case',case,'--ranks',str(args.ranks)],cwd=HERE,stdin=subprocess.DEVNULL)
        for case in CASES}
    completed=set()
    while len(completed)<len(CASES):
        for case,process in processes.items():
            log=HERE/case/'output/test.log'
            if log.exists():
                with log.open('rb') as stream:
                    stream.seek(max(0,log.stat().st_size-4096))
                    tail=stream.read().decode(errors='replace')
                if re.search(r'\b(?:NaN|Infinity)\b',tail,re.I):
                    fail(case+' logged a nonfinite numerical value')
            code=process.poll()
            if code is not None and case not in completed:
                if code!=0: fail(case+f' exited with code {code}; inspect its run.log')
                completed.add(case)
                print(case+' completed successfully.',flush=True)
        time.sleep(10)
    (HERE/'run_results.txt').write_text('# Purpose: Completion status of all four production simulations.\n'+
        '\n'.join(case+': PASS' for case in CASES)+'\n')
    print('All four production runs completed.',flush=True)
