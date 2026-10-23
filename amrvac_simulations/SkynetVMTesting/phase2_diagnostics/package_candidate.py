# Purpose: Assemble the validated numerical fix and four checkpoint-based phase-2 inputs for AMRVAC 3.2 on the VM.
from pathlib import Path
import json
import shutil
from run_tests import set_value, YEAR_CODE

HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parent
BUILD = HERE/'positive_amr_audited_candidate'
DEST = BUNDLE/'ConservativeAMRRestart'
DEST.mkdir(exist_ok=True)
for name in ('mod_usr.t', 'amrvac.h', 'patched_mod_refine.t', 'build.json'):
    shutil.copy2(BUILD/name, DEST/name)
for name in ('stellar_evolution.dat',):
    shutil.copy2(BUNDLE/name, DEST/name)
shutil.copy2(HERE/'install_positive_amr.py', DEST/'install_positive_amr.py')
settings = [('ghost_copy','.true.','boundlist'),
            ('prolongprimitive','.false.','meshlist'),('coarsenprimitive','.false.','meshlist'),
            ('reset_time','.true.','stoplist'),('reset_it','.true.','stoplist'),('it_init','0','stoplist'),
            ('time_init',f'{4.3e6*YEAR_CODE:.17e}','stoplist'),
            ('time_max',f'{4.77e6*YEAR_CODE:.17e}','stoplist'),
            ('it_max','1000000000','stoplist'),('wall_time_max','1.d99','stoplist'),
            ('courantpar','0.1d0','paramlist'),('sts_dtpar','0.1d0','sts_list'),
            ('dtsave_dat',f'{10000*YEAR_CODE:.17e}','savelist')]
checkpoints = {}
for name in ('tc_off_rc_off','tc_off_rc_on','tc_on_rc_off','tc_on_rc_on'):
    case = DEST/name
    case.mkdir(exist_ok=True)
    text = (BUNDLE/name/'run.par').read_text()
    import re
    checkpoint = re.search(r"restart_from_file\s*=\s*'([^']+)'",text).group(1)
    shutil.copy2(BUNDLE/name/checkpoint,case/checkpoint)
    for key,value,section in settings:
        text = set_value(text,key,value,section)
    text = text.replace('! Resume the saved mesh, conserved variables, and stellar age.',
                        '! Resume saved gas; deliberately reset the stellar clock to 4.3 Myr.')
    text = text.replace("! Retain the checkpoint's stellar age and iteration counter.",
                        '! Reset age for this phase-2 experiment; disable both resets on later resumes.')
    (case/'run.par').write_text('! Purpose: Conservative AMR phase-2 restart; retain this case physics and evolve stellar age 4.3 to 4.77 Myr.\n'+text)
    checkpoints[name] = checkpoint
shutil.copy2(HERE/'wrapup_validation.json',DEST/'validation_status.json')
shutil.copy2(HERE/'clean_install_verification.json',DEST/'clean_install_verification.json')
(DEST/'checkpoint_manifest.json').write_text(json.dumps({
    'purpose':'Identify original saved gas states packaged for the four phase-2 experiments.',
    'checkpoints':checkpoints,
    'stellar_clock_reset_years':4300000,
    'warning':'Resetting stellar age does not evolve the original approximately 1-Myr gas through the omitted MS interval.'},indent=2)+'\n')
print(DEST)
