# Purpose: Compile the current user module against unchanged official AMRVAC 3.2 and verify that no core source was edited.
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
BASE=Path('/tmp/skynet-v32-qdvc32bu/amrvac')
DEST=HERE/'user_module_only_build'
DEST.mkdir(exist_ok=True)
TEMP=Path(tempfile.mkdtemp(prefix='user-only-amrvac-'))
SOURCE=TEMP/'source'
PROBLEM=TEMP/'problem'
SOURCE.mkdir()
PROBLEM.mkdir()
expected='e7bff9c949d901aa75316418cb394cfbdee537b06e431a149461879c4fd15135'

def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()

assert digest(BASE/'src/amr/mod_refine.t')==expected,'Baseline refinement source is not official v3.2'
for name in ('src','arch','lib'):
    shutil.copytree(BASE/name,SOURCE/name)
shutil.copy2(BASE/'setup.pl',SOURCE/'setup.pl')
template=SOURCE/'lib/1d1_default/mod_refine.t'
if template.exists():
    assert digest(template)==expected
assert 'positivity_fallback' not in (SOURCE/'lib/1d1_default/mod_refine.f').read_text()
original={str(p.relative_to(SOURCE)):digest(p) for name in ('src','arch') for p in (SOURCE/name).rglob('*') if p.is_file()}
for name in ('mod_usr.t','amrvac.h'):
    shutil.copy2(HERE.parent/name,PROBLEM/name)
    shutil.copy2(HERE.parent/name,DEST/name)
flags='-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'
env=dict(os.environ,AMRVAC_DIR=str(SOURCE),OMP_NUM_THREADS='1')
with (DEST/'build.log').open('w') as stream:
    stream.write('# Purpose: Build transcript for a user-module-only fix with untouched AMRVAC 3.2 core.\n')
    stream.flush()
    for command in (['perl',str(SOURCE/'setup.pl'),'-d=1'],['make','hdr','F90=mpifort','F90FLAGS='+flags],
                    ['make','-j4','F90=mpifort','F90FLAGS='+flags]):
        print('BUILD',command,flush=True)
        subprocess.run(command,cwd=PROBLEM,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
assert original=={str(p.relative_to(SOURCE)):digest(p) for name in ('src','arch') for p in (SOURCE/name).rglob('*') if p.is_file()}
shutil.copy2(PROBLEM/'amrvac',DEST/'amrvac')
report={'purpose':'Prove the delivered user module compiles with unmodified AMRVAC 3.2 core sources.',
        'passed':True,'source_commit':'c45d84650ed3379eb22dcfa6fb927a45734e5d8c',
        'core_source_files_unchanged':len(original),'mod_refine_sha256':expected,
        'flags':flags,'temporary_build':str(TEMP),'executable':str(DEST/'amrvac'),
        'executable_sha256':digest(DEST/'amrvac'),'user_module_sha256':digest(DEST/'mod_usr.t'),
        'reused_official_compiled_library':True}
(DEST/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print('UNMODIFIED CORE BUILD PASSED',DEST/'amrvac',flush=True)
