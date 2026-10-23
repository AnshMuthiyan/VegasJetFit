# Purpose: Verify that the portable AMR installer and audited problem compile against a clean official AMRVAC 3.2 source tree.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
OFFICIAL=REPO/'.cache/amrvac-v3.2-validation'
BUILD=HERE/'positive_amr_audited_candidate'
TEMP=Path(tempfile.mkdtemp(prefix='clean-amr-install-'))
SOURCE=TEMP/'source'
PROBLEM=TEMP/'problem'
SOURCE.mkdir()
PROBLEM.mkdir()
for name in ('src','arch','lib'):
    shutil.copytree(OFFICIAL/name,SOURCE/name)
shutil.copy2(OFFICIAL/'setup.pl',SOURCE/'setup.pl')
for path in SOURCE.rglob('*'):
    if path.is_file() and (path.suffix in ('.t','.pl','.make','.defs','.h','.f','.py','.sh')
                           or path.name in ('makefile','Makefile')):
        path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
        if path.suffix in ('.pl','.sh'):
            path.chmod(0o755)
for name in ('mod_usr.t','amrvac.h'):
    shutil.copy2(BUILD/name,PROBLEM/name)
FLAGS='-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'
env=dict(os.environ,AMRVAC_DIR=str(SOURCE),OMP_NUM_THREADS='1')
start=time.monotonic()
with (HERE/'clean_install_build.log').open('w') as stream:
    stream.write('# Purpose: Clean-source installation and compilation verification transcript.\n')
    stream.flush()
    commands=[[sys.executable,str(HERE/'install_positive_amr.py'),'--amrvac-dir',str(SOURCE),
               '--patch-dir',str(BUILD)],['perl',str(SOURCE/'setup.pl'),'-d=1'],
              ['make','hdr','F90=mpifort','F90FLAGS='+FLAGS],
              ['make','-j1','F90=mpifort','F90FLAGS='+FLAGS]]
    for command in commands:
        print('CLEAN INSTALL',command,flush=True)
        subprocess.run(command,cwd=PROBLEM,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
report={'purpose':'Verify clean-source installation and full AMRVAC 3.2 compilation of the portable numerical fix.',
        'passed':True,'source_commit':'c45d84650ed3379eb22dcfa6fb927a45734e5d8c',
        'flags':FLAGS,'build_seconds':time.monotonic()-start,'temporary_build':str(TEMP),
        'executable':str(PROBLEM/'amrvac'),
        'executable_sha256':hashlib.sha256((PROBLEM/'amrvac').read_bytes()).hexdigest()}
(HERE/'clean_install_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('CLEAN INSTALL BUILD PASSED',PROBLEM/'amrvac',flush=True)
