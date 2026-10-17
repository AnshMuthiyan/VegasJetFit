# Purpose: Compare numerical repairs in isolated copies beyond the 142-year failure.
# Production inputs, outputs, and the failed original campaign remain untouched.
from pathlib import Path
import argparse
import concurrent.futures
import csv
import datetime
import math
import os
import re
import shutil
import subprocess
import time
import sys

# Direct script execution must also find the campaign's management module.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import manage
import audit_native

ROOT=manage.HERE
RANKS=4
SWITCH_YEAR=100


def run_test(name, case, years, edits, phase_test=None):
    folder=ROOT/'validation'/name
    if folder.exists():
        raise RuntimeError(f'{folder} exists; choose a new test name')
    folder.mkdir(parents=True)
    (folder/'output').mkdir()
    shutil.copy2(ROOT/'mod_usr.t',folder/'mod_usr.t')
    shutil.copy2(ROOT/'stellar_evolution.dat',folder/'stellar_evolution.dat')
    par=(ROOT/case/'run.par').read_text()
    par=re.sub(r'time_max=\S+',f'time_max={years*manage.YEAR_CODE:.17e}',par)
    par=re.sub(r'dtsave_dat=\S+',f'dtsave_dat={years/4*manage.YEAR_CODE:.17e}',par)
    par=par.replace('ditsave_log=10000','ditsave_log=1000')
    for key,value in edits.items():
        par,count=re.subn(r'(?m)^(\s*)'+re.escape(key)+r'=\S+',r'\g<1>'+key+'='+value,par)
        if count==0 and key=='qstretch_baselevel(1)':
            par=par.replace('&meshlist\n','&meshlist\n qstretch_baselevel(1)='+value+'\n')
        elif count!=1: raise RuntimeError(f'Expected one {key}; found {count}')
    if phase_test:
        rows=(ROOT/'stellar_evolution.dat').read_text().splitlines()
        data=[line.split() for line in rows if line.strip() and not line.startswith('#')]
        ends=[SWITCH_YEAR,SWITCH_YEAR+200000,SWITCH_YEAR+470000] if phase_test=='MS_RSG' else [0,SWITCH_YEAR,SWITCH_YEAR+270000]
        contents=['# Purpose: Accelerated '+phase_test+' transition test only; production ages are unchanged.',
                  '# Same screenshot Mdot and speeds; shortened phase ages exercise the source switch.']
        contents += [' '.join([str(end),*row[1:]]) for end,row in zip(ends,data)]
        (folder/'stellar_evolution.dat').write_text('\n'.join(contents)+'\n')
    (folder/'run.par').write_text('! Purpose: Isolated stability test '+name+'.\n'+par)
    start=time.monotonic()
    print('Starting '+name,flush=True)
    with (folder/'run.log').open('w') as stream:
        stream.write('# Purpose: Stability and energy-rescue evidence for '+name+'.\n')
        stream.flush()
        try:
            result=subprocess.run(['mpirun','--bind-to','none','-np',str(RANKS),str(ROOT/'build/amrvac'),'-i','run.par'],
                cwd=folder,env={**os.environ,'OMP_NUM_THREADS':'1'},stdout=stream,
                stderr=subprocess.STDOUT,timeout=max(3000,years*3))
            code=result.returncode
        except subprocess.TimeoutExpired:
            code='timeout'
    text=(folder/'run.log').read_text(errors='replace')
    passed=code==0 and 'Finished AMRVAC' in text
    log=folder/'output/test.log'
    if log.exists() and re.search(r'\b(?:NaN|Infinity)\b',log.read_text(),re.I): passed=False
    report={'name':name,'case':case,'years':years,'passed':passed,'code':code,
            'wall_seconds':round(time.monotonic()-start,2),'ranks':RANKS,
            'courantpar':re.search(r'courantpar=(\S+)',par).group(1)}
    if passed:
        try:
            snapshots=[audit_native.audit(path) for path in sorted((folder/'output').glob('test*.dat'))]
            if not snapshots: raise ValueError('No native snapshots')
            with (folder/'native_audit.csv').open('w',newline='') as stream:
                stream.write('# Purpose: Independent native-cell finite/positivity audit.\n')
                writer=csv.DictWriter(stream,fieldnames=snapshots[0])
                writer.writeheader()
                writer.writerows(snapshots)
            report['min_temperature_K']=min(row['min_temperature_K'] for row in snapshots)
            report['disturbed_radius_pc']=snapshots[-1]['disturbed_radius_pc']
            if not math.isclose(snapshots[-1]['age_yr'],years,rel_tol=1e-10):
                raise ValueError('Native final age does not match requested duration')
        except (ValueError,AssertionError,KeyError) as exc:
            passed=False
            report['passed']=False
            report['native_audit_error']=str(exc)
    audit=folder/'output/test_guard.csv'
    if audit.exists():
        lines=[line for line in audit.read_text().splitlines() if not line.startswith('#')]
        records=list(csv.DictReader(lines))
        if records:
            report['final_evaluation_fraction']=float(records[-1]['evaluation_fraction'])
            report['worst_cell_fraction']=max(float(row['worst_cell_fraction']) for row in records)
            report['rescue_events']=float(records[-1]['rescue_events'])
    (folder/'result.txt').write_text('# Purpose: Summary of isolated stability test.\n'+
        '\n'.join(f'{key}={value}' for key,value in report.items())+'\n')
    print(report,flush=True)
    if not passed: print(text[-2800:],flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('suite',choices=['compare','physics','transitions','mesh','numerics'])
    parser.add_argument('--years',type=float,default=1000)
    parser.add_argument('--tag',default=datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    parser.add_argument('--xmin',default='0.01d0')
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--skip-hydro',action='store_true')
    parser.add_argument('--ranks',type=int,default=4)
    parser.add_argument('--courant')
    parser.add_argument('--switch-year',type=float,default=100)
    parser.add_argument('--qstretch')
    parser.add_argument('--flux')
    args=parser.parse_args()
    RANKS=args.ranks
    SWITCH_YEAR=args.switch_year
    if args.suite=='compare':
        specs=[('representable','tc_off_rc_off',args.years,{},None),
               ('absolute_floor','tc_off_rc_off',args.years,{'guard_ulps':'0.d0','small_pressure':'1.d-8'},None),
               ('smaller_cfl','tc_off_rc_off',args.years,{'courantpar':'0.1d0'},None),
               ('larger_inner','tc_off_rc_off',args.years,{'xprobmin1':'0.05d0'},None)]
    elif args.suite=='physics':
        specs=[(case,case,args.years,{'xprobmin1':args.xmin},None) for case in manage.CASES
               if not (args.skip_hydro and case=='tc_off_rc_off')]
    elif args.suite=='transitions':
        specs=[(phase+'_'+case,case,args.years,{'xprobmin1':args.xmin},phase)
               for case in ['tc_off_rc_on','tc_off_rc_off','tc_on_rc_on','tc_on_rc_off']
               for phase in ['MS_RSG','RSG_WR']]
    elif args.suite=='mesh':
        specs=[('gentler_stretch','tc_off_rc_off',args.years,
                {'qstretch_baselevel(1)':'1.03d0','courantpar':'0.1d0'},None)]
    else:
        base={'qstretch_baselevel(1)':'1.03d0','courantpar':'0.1d0'}
        specs=[('linear_density','tc_off_rc_on',args.years,{**base,'loglimit(1)':'.false.'},'RSG_WR'),
               ('linear_primitives','tc_off_rc_on',args.years,
                {**base,'loglimit(1)':'.false.','loglimit(3)':'.false.'},'RSG_WR'),
               ('tvdlf','tc_off_rc_on',args.years,{**base,'flux_scheme':"20*'tvdlf'"},'RSG_WR'),
               ('cfl005','tc_off_rc_on',args.years,{**base,'courantpar':'0.05d0'},'RSG_WR'),
               ('cfl0025','tc_off_rc_on',args.years,{**base,'courantpar':'0.025d0'},'RSG_WR')]
    if args.courant:
        specs=[(name,case,years,{**edits,'courantpar':args.courant},phase)
               for name,case,years,edits,phase in specs]
    if args.qstretch:
        specs=[(name,case,years,{**edits,'qstretch_baselevel(1)':args.qstretch},phase)
               for name,case,years,edits,phase in specs]
    if args.flux:
        specs=[(name,case,years,{**edits,'flux_scheme':"20*'"+args.flux+"'"},phase)
               for name,case,years,edits,phase in specs]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(run_test,args.tag+'_'+name,case,years,edits,phase)
                 for name,case,years,edits,phase in specs]
        results=[future.result() for future in futures]
    print('PASS COUNT',sum(row['passed'] for row in results),'/',len(results),flush=True)
    if not all(row['passed'] for row in results): raise SystemExit(1)
