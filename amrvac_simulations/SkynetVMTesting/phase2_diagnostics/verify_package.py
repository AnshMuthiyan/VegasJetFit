# Purpose: Verify portable source hashes, physics switches, reset settings and original checkpoint copies before delivery.
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from plot_dat_folder import read_snapshot, scalar

package=HERE.parent/'ConservativeAMRRestart'
info=json.loads((package/'build.json').read_text())
assert hashlib.sha256((package/'patched_mod_refine.t').read_bytes().replace(b'\r\n',b'\n')).hexdigest()==info['patched_source_sha256']
for name in ('mod_usr.t','amrvac.h'):
    assert (package/name).read_bytes()==(HERE/'positive_amr_audited_candidate'/name).read_bytes()
manifest=json.loads((package/'checkpoint_manifest.json').read_text())
rows=[]
for case,checkpoint in manifest['checkpoints'].items():
    folder=package/case
    text=(folder/'run.par').read_text()
    tc,rc=case.split('_')[1],case.split('_')[3]
    assert scalar(text,'hd_thermal_conduction')==('.true.' if tc=='on' else '.false.')
    assert scalar(text,'hd_radiative_cooling')==('.true.' if rc=='on' else '.false.')
    for key,value in [('ghost_copy','.true.'),('prolongprimitive','.false.'),
                      ('coarsenprimitive','.false.'),('reset_time','.true.'),('reset_it','.true.')]:
        assert scalar(text,key)==value,(case,key)
    assert (folder/checkpoint).read_bytes()==(HERE.parent/case/checkpoint).read_bytes()
    data=read_snapshot(folder/checkpoint,folder/'run.par')
    assert data['invalid_cells']==0
    rows.append({'case':case,'checkpoint':checkpoint,'original_gas_age_years':data['age_years'],
                 'checkpoint_sha256':hashlib.sha256((folder/checkpoint).read_bytes()).hexdigest()})
report={'purpose':'Verify delivered source identity, per-case physics, restart configuration and unchanged valid checkpoints.',
        'passed':True,'cases':rows}
(package/'package_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
