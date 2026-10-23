# Purpose: Save and stop only an explicitly named local diagnostic MPI job, recording the deliberate stop separately from numerical failures.
import argparse
import json
import os
from pathlib import Path
import signal
import time

parser=argparse.ArgumentParser()
parser.add_argument('folder',type=Path)
parser.add_argument('--reason',required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parent
folder=args.folder.resolve(strict=True)
folder.relative_to(root)
if not (folder/'run.par').is_file():
    raise RuntimeError('Not a diagnostic case directory')
launchers=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if (proc/'comm').read_text().strip()=='mpirun' and (proc/'cwd').resolve()==folder:
            launchers.append(int(proc.name))
    except (FileNotFoundError,PermissionError,ProcessLookupError):
        pass
if not launchers:
    raise RuntimeError('No MPI launcher belongs to this exact diagnostic directory')
marker=folder/'savenow'
marker.write_text('! Purpose: Request a native checkpoint before deliberately stopping this diagnostic.\n')
deadline=time.monotonic()+40
while marker.exists() and time.monotonic()<deadline:
    time.sleep(.2)
if marker.exists():
    raise RuntimeError('Checkpoint request not acknowledged; refusing to terminate')
print('CHECKPOINT SAVED; stopping diagnostic launchers',launchers,flush=True)
for pid in launchers:
    os.killpg(os.getpgid(pid),signal.SIGTERM)
report=folder.parent/'results.json'
deadline=time.monotonic()+40
while time.monotonic()<deadline:
    try:
        data=json.loads(report.read_text())
        if any(r['case']==folder.name for r in data['cases']):
            data['cancellation_note']=args.reason
            report.write_text(json.dumps(data,indent=2)+'\n')
            break
    except (FileNotFoundError,json.JSONDecodeError):
        pass
    time.sleep(.2)
else:
    raise RuntimeError('Simulation stopped, but diagnostic report was not written yet')
print('DELIBERATE STOP RECORDED',report,flush=True)
