# Purpose: Verify corrected two-file recovery output naming and preserved checkpoint state using a real stock-AMRVAC restart.
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
parser=argparse.ArgumentParser()
parser.add_argument('--geometry',action='store_true',help='Check the test0050.dat geometry-recovery overlay and a separate output directory.')
args=parser.parse_args()
output_dir='recovery40_geometry' if args.geometry else 'recovery40'
overlay_name='resume_40Msun_geometry.par' if args.geometry else 'resume_40Msun.par'
checkpoint_path='recovery40/test0050.dat' if args.geometry else 'output/test0043.dat'
sys.path.insert(0,str(ROOT))
from plot_dat_folder import read_snapshot
from run_tests import set_value

temporary=Path(tempfile.mkdtemp(prefix='recovery-prefix-check-'))
case=temporary/'production'
case.mkdir()
(case/'output').mkdir()
(case/output_dir).mkdir()
shutil.copy2(ROOT/'stellar_evolution.dat',temporary/'stellar_evolution.dat')
checkpoint=ROOT/'tc_on_rc_on/test0011.dat'
initial=read_snapshot(checkpoint)
(case/checkpoint_path).parent.mkdir(exist_ok=True)
shutil.copy2(checkpoint,case/checkpoint_path)
primary=(ROOT/'ConservativeAMRRestart/tc_on_rc_on/run.par').read_text()
primary=set_value(primary,'base_filename',repr(output_dir+'/test'),'filelist')
(case/'run_recovery40.par').write_text(primary)
overlay=(ROOT/overlay_name).read_text()
assert not any(line.strip().startswith('base_filename=') for line in overlay.splitlines())
# Only the diagnostic iteration limit differs from the delivered recovery overlay.
overlay=set_value(overlay,'it_max',str(initial['iteration']+10),'stoplist')
(temporary/overlay_name).write_text(overlay)
executable=HERE/'user_module_only_build/amrvac'
with (case/'check.log').open('w') as stream:
    stream.write('# Purpose: Ten-iteration stock-AMRVAC restart exercising the corrected recovery parameter combination.\n')
    stream.flush()
    completed=subprocess.run(['mpirun','--bind-to','none','-np','1',str(executable),
                              '-i','run_recovery40.par','../'+overlay_name],
                             cwd=case,env=dict(os.environ,OMP_NUM_THREADS='1'),
                             stdout=stream,stderr=subprocess.STDOUT,timeout=60)
log=(case/'check.log').read_text()
assert completed.returncode==0,log[-6000:]
assert 'User-module conservative refinement: T' in log
assert 'Finished AMRVAC' in log
outputs=sorted((case/output_dir).glob('test*.dat'))
assert outputs,'Expected native output under recovery40, not a concatenated path'
states=[read_snapshot(p,case/'run_recovery40.par') for p in outputs]
final=max(states,key=lambda s:s['iteration'])
assert final['iteration']==initial['iteration']+10
assert initial['age_years']<final['age_years']<initial['age_years']+10
assert not any(s['invalid_cells'] for s in states)
evidence=HERE/('geometry_recovery_verification' if args.geometry else 'recovery_prefix_verification')
evidence.mkdir(exist_ok=True)
for name in ('check.log','run_recovery40.par'):
    shutil.copy2(case/name,evidence/name)
shutil.copy2(temporary/overlay_name,evidence/overlay_name)
report={'purpose':'Verify stock-AMRVAC concatenation workaround with two actual input files and native restart/output.',
        'passed':True,'iterations_advanced':10,'initial_age_years':initial['age_years'],
        'final_age_years':final['age_years'],'invalid_saved_cells':0,
        'output_prefix':output_dir+'/test','output_files':[p.name for p in outputs],
        'core_source_modified':False,
        'scope':'Uses a local reference checkpoint renamed for the fixture; actual VM '+checkpoint_path+' has not been inspected locally.'}
(evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
