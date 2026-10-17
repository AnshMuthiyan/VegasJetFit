# Purpose: Build isolated AMRVAC v3.1 executables, create candidate inputs,
# run controlled stability experiments, and retain reproducible run evidence.
from pathlib import Path
import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get('AMRVAC_DIR','/home/anshm/amrvac'))
FLAGS = ['-cpp', '-ffree-form', '-fimplicit-none', '-O2', '-g',
         '-fcheck=bounds', '-fbacktrace']
YEAR_CODE = 3.1536e7 / 3.0857e11

def command(argv, cwd, log):
    with log.open('w') as f:
        f.write('# Purpose: Build/run transcript for '+log.stem+'\n')
        f.flush()
        result = subprocess.run(argv, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text(errors='replace')[-8000:], flush=True)
        raise RuntimeError(f'{argv[0]} failed: {result.returncode}')

def build():
    lib = HERE/'library'
    problem = HERE/'build'
    lib.mkdir(exist_ok=True)
    problem.mkdir(exist_ok=True)
    (lib/'amrvac.h').write_text('/* Purpose: Default one-dimensional HD build; no compile-time overrides. */\n')
    shutil.copy2(lib/'amrvac.h', problem/'amrvac.h')
    command(['make','-j4','-f',str(SOURCE/'arch/lib.make'),
             'AMRVAC_DIR='+str(SOURCE),'ARCH=default','NDIM=1',
             'F90FLAGS='+' '.join(FLAGS)],lib,HERE/'library_build.log')
    for name, src in [('mod_usr', HERE/'mod_usr.t'),('amrvac',SOURCE/'src/amrvac.t')]:
        dest=problem/(name+'.f')
        with dest.open('w') as f:
            f.write('! Purpose: Generated one-dimensional Fortran for the isolated wind tests.\n')
            f.flush()
            subprocess.run([str(SOURCE/'src/vacpp.pl'),'-d=1',str(src)],cwd=problem,stdout=f,check=True)
        command(['mpif90',*FLAGS,'-I'+str(lib),'-c',str(dest),'-o',name+'.o'],problem,HERE/(name+'_compile.log'))
    command(['mpif90',*FLAGS,'mod_usr.o','amrvac.o','-L'+str(lib),'-lamrvac','-o','amrvac'],problem,HERE/'link.log')
    print('Build complete',flush=True)

BASE = '''! Purpose: {purpose}; constant WR wind in n_total=1e4 cm^-3, 100 K gas.
! Both physical transport terms and Tfix remain enabled in every candidate.
&filelist
 base_filename='output/test'
 saveprim=.true.
 autoconvert=.true.
 convert_type='vtuBmpi'
 nwauxio=1
/
&savelist
 itsave(1,1)=0
 itsave(1,2)=0
 ditsave_log=1000
 dtsave_dat={save:.17e}
/
&stoplist
 time_max={stop:.17e}
 final_dt_reduction=.true.
 dtmin=1.d-14
/
&methodlist
 ! SSPRK3 provides ps2 geometry needed by spherical AMR+STS in v3.1.
 time_stepper='threestep'
 flux_scheme=20*'{flux}'
 limiter=20*'minmod'
 loglimit(1)=.true.
 loglimit(3)=.true.
 check_small_values=.true.
 fix_small_values=.true.
 small_values_method='replace'
 small_temperature=0.d0
 small_pressure=1.d-14
 small_density=1.d-14
/
&boundlist
 typeboundary_min1='special','special','special'
 typeboundary_max1='special','special','special'
/
&meshlist
 refine_criterion=3
 refine_max_level={level}
 w_refine_weight(1)=0.7d0
 w_refine_weight(2)=0.d0
 w_refine_weight(3)=0.d0
 w_refine_weight(4)=0.3d0
 refine_threshold=20*0.05d0
 derefine_ratio=20*0.1d0
 domain_nx1={nx}
 block_nx1=8
 xprobmin1={xmin}
 ! Leave room for the forward shock at one million years.
 xprobmax1=20.d0
 {stretch}
/
&paramlist
 typecourant='maxsum'
 courantpar={cfl}
 slowsteps=50
/
&hd_list
 hd_energy=.true.
 hd_gamma=1.6666666666666667d0
 hd_radiative_cooling=.true.
 hd_thermal_conduction=.true.
/
&tc_list
 tc_saturate=.true.
/
&sts_list
 sts_method=1
 sts_dtpar={sts}
 sts_ncycles=1000
 sourcetype_sts=2
/
&rc_list
 coolcurve='SPEX_DM'
 coolmethod='exact'
 Tfix=.true.
/
&usr_list
 ! This is total particle density; the code derives rho using the HD EOS.
 ambient_particles_cm3=1.d4
 ambient_temperature_k=100.d0
 wind_mdot_msunyr=1.d-5
 wind_velocity_kms=2000.d0
 wind_temperature_k=1.d4
/
'''

CASES = {
 'a_uniform_tfix': dict(purpose='Tfix-only control with the original uniform grid',xmin='0.01d0',flux='tvdlf',cfl='0.2d0',sts='0.8d0',level=4,nx=192,stretch=''),
 'b_uniform_hll': dict(purpose='Test HLL flux with a safe 0.2 pc inner boundary',xmin='0.2d0',flux='hll',cfl='0.2d0',sts='0.8d0',level=4,nx=192,stretch=''),
 'c_stretched_tvdlf': dict(purpose='Test logarithmic radial grid to control dr/r',xmin='0.01d0',flux='tvdlf',cfl='0.2d0',sts='0.8d0',level=2,nx=128,stretch="stretch_dim(1)='uni'"),
 'd_stretched_hll': dict(purpose='Test logarithmic grid with HLL flux',xmin='0.05d0',flux='hll',cfl='0.2d0',sts='0.4d0',level=2,nx=128,stretch="stretch_dim(1)='uni'"),
 'e_small_dt': dict(purpose='Test a smaller CFL and conduction timestep',xmin='0.2d0',flux='tvdlf',cfl='0.05d0',sts='0.2d0',level=4,nx=192,stretch=''),
 'f_production_1myr': dict(purpose='Production 1 Myr run with AMR level 3 and HLL flux',xmin='0.2d0',flux='hll',cfl='0.2d0',sts='0.8d0',level=3,nx=192,stretch=''),
}

def prepare(name, years):
    cfg=CASES[name]
    folder=HERE/name
    folder.mkdir(exist_ok=True)
    (folder/'output').mkdir(exist_ok=True)
    source=(HERE/'mod_usr.t').read_text()
    (folder/'mod_usr.t').write_text(source)
    par=BASE.format(**cfg,stop=years*YEAR_CODE,save=max(years/4,1)*YEAR_CODE)
    (folder/'run.par').write_text(par)
    return folder

def run(name, years, timeout, ranks):
    if not (HERE/'build/amrvac').is_file():
        raise RuntimeError('Build must finish before launching experiments')
    folder=prepare(name,years)
    env=os.environ.copy()
    env['OMP_NUM_THREADS']='1'
    start=time.monotonic()
    log=folder/'run.log'
    print(f'Start {name}: {years:g} yr, {ranks} MPI ranks',flush=True)
    with log.open('w') as f:
        f.write(f'# Purpose: Stability evidence for {name}, target {years:g} years.\n')
        f.flush()
        try:
            result=subprocess.run(['mpirun','-np',str(ranks),str(HERE/'build/amrvac'),'-i','run.par'],cwd=folder,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
            status=result.returncode
        except subprocess.TimeoutExpired:
            status='timeout'
    output=log.read_text(errors='replace')
    evidence={'purpose':'Machine-readable result of this numerical experiment','case':name,'target_years':years,'returncode':status,'finished':status==0 and 'Finished AMRVAC' in output,'wall_seconds':time.monotonic()-start}
    (folder/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence),flush=True)
    print(output[-1800:],flush=True)
    return evidence

def inspect():
    print('SOURCE_COMMIT',subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip())
    for name,words in [('src/mod_input_output.t',['stretch_dim','qstretch_baselevel']),('src/hd/mod_hd_phys.t',['hd_eaux','hd_internal_e','namelist /hd_list/']),('src/mod_geometry.t',['stretch','surface','volume'])]:
        path=SOURCE/name
        if path.exists():
            lines=path.read_text().splitlines()
            for i,line in enumerate(lines):
                if any(w in line for w in words):
                    print(f'{name}:{i+1}: {line}')
    print('CPU_COUNT',os.cpu_count())
    print(subprocess.check_output(['free','-h'],text=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['inspect','build','screen','run','prepare'])
    ap.add_argument('--case',choices=CASES,default='d_stretched_hll')
    ap.add_argument('--years',type=float,default=1000)
    ap.add_argument('--timeout',type=float,default=600)
    ap.add_argument('--ranks',type=int,default=2)
    args=ap.parse_args()
    if args.action=='inspect': inspect()
    elif args.action=='build': build()
    elif args.action=='prepare': prepare(args.case,args.years)
    elif args.action=='run': run(args.case,args.years,args.timeout,args.ranks)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda name:run(name,args.years,args.timeout,args.ranks),CASES))
        (HERE/'screen_results.json').write_text(json.dumps({'purpose':'Comparative candidate stability results','results':results},indent=2)+'\n')
