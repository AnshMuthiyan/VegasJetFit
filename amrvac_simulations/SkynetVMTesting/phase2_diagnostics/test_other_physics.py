# Purpose: Validate the candidate across the other three physics combinations using each case's own checkpoint and a full RSG-to-WR transition.
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parent
BUILD = HERE/'positive_amr_audited_candidate'
sys.path.insert(0, str(BUNDLE))
from plot_dat_folder import read_snapshot

rows = []
for case, switch in [('tc_off_rc_off','neither'), ('tc_on_rc_off','conduction_only'),
                     ('tc_off_rc_on','cooling_only')]:
    checkpoint = max((BUNDLE/case).glob('test*.dat'), key=lambda p: read_snapshot(p)['age_years'])
    command = [sys.executable, str(HERE/'run_tests.py'), '--executable',str(BUILD/'amrvac'),
               '--source-dir',str(BUILD), '--checkpoint',str(checkpoint),
               '--cases',switch,'--ghost-copy','--ranks','1','--start-age-years','4300000',
               '--years','201000','--save-years','10000','--courant','0.1',
               '--timeout','7200','--label','exact_matrix_'+case]
    print('MATRIX CASE',case,'CHECKPOINT',checkpoint,flush=True)
    with (HERE/('exact_matrix_'+case+'.log')).open('w') as stream:
        stream.write('# Purpose: Physics-matrix runner transcript for '+case+'.\n')
        stream.flush()
        code = subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
    reports = sorted(HERE.glob('*_exact_matrix_'+case+'/results.json'))
    report = json.loads(reports[-1].read_text()) if reports else None
    row = {'case':case,'runner_returncode':code,'report':str(reports[-1]) if reports else None,
           'passed':bool(report and all(r.get('passed',False) for r in report['cases']))}
    rows.append(row)
    (HERE/'exact_matrix_results.json').write_text(json.dumps({'purpose':'Audited prescribed-flux own-checkpoint RSG and WR transition tests for the three additional physics cases.',
                                                       'cases':rows},indent=2)+'\n')
    print(json.dumps(row),flush=True)
    if not row['passed']:
        print('STOPPING MATRIX FOR DIAGNOSIS',flush=True)
        break
