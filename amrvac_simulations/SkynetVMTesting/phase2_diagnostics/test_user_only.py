# Purpose: Check fresh 25 Msun starts and reproduce the old refinement failure using only user-module hooks on unmodified AMRVAC 3.2.
import argparse
import csv
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from plot_dat_folder import read_snapshot
from run_tests import set_value,YEAR_CODE

parser=argparse.ArgumentParser()
parser.add_argument('--fresh-steps',type=int)
parser.add_argument('--fresh-years',type=float,default=100)
parser.add_argument('--courant',type=float)
parser.add_argument('--cases',nargs='+')
parser.add_argument('--phase-years',type=float,default=1000)
parser.add_argument('--ranks',type=int,default=4)
parser.add_argument('--timeout',type=float,default=180)
args=parser.parse_args()
BUILD=HERE/'user_module_only_build'
assert (ROOT/'mod_usr.t').read_bytes()==(BUILD/'mod_usr.t').read_bytes()
archive=HERE/(time.strftime('%Y%m%d_%H%M%S')+'_user_only_checks')
archive.mkdir()
# Fresh starts probe 10000 possible snapshots. Keep these filesystem probes
# on Linux rather than the slower Windows-mounted validation directory.
batch=Path(tempfile.mkdtemp(prefix='user-only-checks-'))
for name in ('mod_usr.t','amrvac.h','stellar_evolution.dat','stellar_evolution_25Msun.dat'):
    shutil.copy2(ROOT/name,batch/name)
    shutil.copy2(ROOT/name,archive/name)
cases=[('old_failure_regression',True)]
cases += [(name,False) for name in ('tc_off_rc_off','tc_off_rc_on','tc_on_rc_off','tc_on_rc_on')]
if args.cases:
    cases=[c for c in cases if c[0] in args.cases]
report={'purpose':'Finite-state and conservative user-refinement validation on stock AMRVAC 3.2; fresh checks are startup tests, not full 7-Myr evolution.',
        'build':json.loads((BUILD/'build.json').read_text()),'cases':[]}
report['native_work_directory']=str(batch)
for name,regression in cases:
    folder=batch/name
    folder.mkdir()
    (folder/'output').mkdir()
    source_case='tc_on_rc_on' if regression else name
    text=(ROOT/source_case/'run.par').read_text()
    settings=[('base_filename',"'output/test'",'filelist'),('autoconvert','.false.','filelist'),
              ('it_max',str(args.fresh_steps if not regression and args.fresh_steps else 1000000000),'stoplist'),
              ('itsave(1,2)','1000000000','savelist')]
    if regression:
        checkpoint=ROOT/'tc_on_rc_on/test0011.dat'
        shutil.copy2(checkpoint,folder/checkpoint.name)
        settings += [('restart_from_file',repr(checkpoint.name),'filelist'),
                     ('reset_time','.true.','stoplist'),('reset_it','.true.','stoplist'),
                     ('time_init',f'{4.3e6*YEAR_CODE:.17e}','stoplist'),
                     ('time_max',f'{(4.3e6+args.phase_years)*YEAR_CODE:.17e}','stoplist'),
                     ('stellar_param_file',"'../stellar_evolution.dat'",'usr_list'),
                     ('dtsave_dat',f'{250*YEAR_CODE:.17e}','savelist')]
    else:
        settings += [('time_max',f'{args.fresh_years*YEAR_CODE:.17e}','stoplist'),
                     ('dtsave_dat',f'{25*YEAR_CODE:.17e}','savelist')]
    if args.courant is not None:
        settings.append(('courantpar',repr(args.courant),'paramlist'))
    for key,value,section in settings:
        text=set_value(text,key,value,section)
    (folder/'run.par').write_text('! Purpose: Stock-core user-module-only diagnostic: '+name+'.\n'+text)
    start=time.monotonic()
    env=dict(os.environ,OMP_NUM_THREADS='1')
    with (folder/'run.log').open('w') as stream:
        stream.write('# Purpose: User-module-only AMRVAC stability-check transcript.\n')
        stream.flush()
        process=subprocess.Popen(['mpirun','--bind-to','none','--oversubscribe','-np',str(args.ranks),
                                  str(BUILD/'amrvac'),'-i','run.par'],cwd=folder,env=env,
                                  stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            process.wait(timeout=15)
            code='timeout'
    log=(folder/'run.log').read_text(errors='replace')
    row={'case':name,'returncode':code,'wall_seconds':time.monotonic()-start,'passed':False}
    snapshots=[read_snapshot(p,folder/'run.par') for p in sorted((folder/'output').glob('*.dat'))]
    if snapshots:
        final=max(snapshots,key=lambda s:s['iteration'])
        tc=source_case.split('_')[1]=='on'
        rc=source_case.split('_')[3]=='on'
        row.update(last_saved_age_years=final['age_years'],last_iteration=final['iteration'],
                   invalid_saved_cells=sum(s['invalid_cells'] for s in snapshots),snapshots_checked=len(snapshots),
                   physics_flags_match=(('Spitzer HD par:' in log)==tc and ('Cooling Tfix enabled: T' in log)==rc))
        target_ok=math.isclose(final['age_years'],4.3e6+args.phase_years,abs_tol=1e-5) if regression else (final['iteration']==args.fresh_steps if args.fresh_steps else math.isclose(final['age_years'],args.fresh_years,abs_tol=1e-5))
        row['passed']=code==0 and 'Finished AMRVAC' in log and 'User-module conservative refinement: T' in log and target_ok and row['invalid_saved_cells']==0 and row['physics_flags_match']
    audit=folder/'output/test_guard.csv'
    if audit.exists():
        records=list(csv.DictReader(audit.read_text().splitlines()[1:]))
        row['last_guard_record']=records[-1]
    report['cases'].append(row)
    shutil.copytree(folder,archive/name)
    (archive/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(row),flush=True)
    if not row['passed']:
        print(log[-6000:],flush=True)
        raise SystemExit(1)
print('ALL USER-ONLY CHECKS PASSED',archive,flush=True)
