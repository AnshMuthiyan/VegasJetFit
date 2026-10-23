#!/usr/bin/env python3
"""Artificial-age source transition checks; these are not evolved bubbles."""
import csv,hashlib,json,math,os,pathlib,re,subprocess,time
from grid_runtime import read_vtu,KB
HERE=pathlib.Path(__file__).resolve().parent
rows=list(csv.DictReader((HERE/'manifest.csv').open()))
root=HERE/'phase_preflight_v5';root.mkdir(exist_ok=True)
records=[]
for mass,offset,end,expected in [(25,6.49995,.0001,15),(25,6.9999,.0001,15),(40,4.29995,.0001,15),(40,4.49995,.0001,2000),(40,4.7699,.0001,2000)]:
 row=next(r for r in rows if int(r['star_mass_msun'])==mass)
 case=f'phase_m{mass}_a{str(offset).replace(".","p")}'
 d=root/case;d.mkdir(exist_ok=True);(d/'output').mkdir(exist_ok=True)
 base=HERE/'inputs'/row['base_file']
 par=(HERE/'inputs'/row['smoke_file']).read_text()
 par=par.replace(row['case']+'_smoke',case)
 par=par.replace('wind_phase_age_offset_myr = 0.0d0',f'wind_phase_age_offset_myr = {offset:.12f}d0')
 par=re.sub(r'dtsave_dat\s*=.*',f'dtsave_dat = {end*102.20121568819214/4:.17e}',par)
 (d/'stage.par').write_text(par)
 start=time.monotonic()
 if (d/'run.log').exists():
  assert (d/'run.log').read_text().count('Finished AMRVAC')==1 and not (d/'run.err').stat().st_size
  class Finished:returncode=0
  p=Finished()
 else:
  with (d/'run.log').open('x') as log,(d/'run.err').open('x') as err:
   p=subprocess.run([str(HERE/'amrvac'),'-i',str(base),str(d/'stage.par')],cwd=d,stdin=subprocess.DEVNULL,stdout=log,stderr=err,timeout=300,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
 assert p.returncode==0 and (d/'run.err').stat().st_size==0,(case,p.returncode)
 assert (d/'run.log').read_text().count('Finished AMRVAC')==1
 fs=sorted((d/'output').glob('*.vtu'));assert len(fs)==5,(case,len(fs))
 age,points=read_vtu(fs[-1]);speeds=[x[2]*100 for x in points if x[0]<.04]
 assert math.isclose(age,end,abs_tol=1e-9)
 track=re.findall(r'^ TRACK\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)',(d/'run.log').read_text(),re.M)
 assert track,(case,'missing injected track diagnostics')
 ta,tm,tv=map(float,track[-1]);assert math.isclose(tv,expected,rel_tol=1e-7),(case,tv,expected)
 if offset in (6.49995,4.29995,4.49995):assert ta>=offset+.00005-1e-9,(case,ta,offset)
 assert math.isclose(tm,5e-5 if mass==40 and expected==15 else 1e-5,rel_tol=1e-7)
 records.append({'case':case,'offset_myr':offset,'end_elapsed_myr':age,'expected_endpoint_wind_kms':expected,'runtime_seconds':time.monotonic()-start,'status':'PASS'})
 print('PASS',case,expected,flush=True)
# Explicit pressure isolation: same density and mass, four-pressure initial states.
for row in [r for r in rows if r['case'].startswith('m25_n3000_')]:
 case='pressure_'+row['case'];d=root/case;d.mkdir(exist_ok=True);(d/'output').mkdir(exist_ok=True)
 par=(HERE/'inputs'/row['static_file']).read_text().replace(row['case']+'_static',case)
 par=re.sub(r'time_max\s*=.*','time_max = 0.0d0',par);(d/'stage.par').write_text(par)
 with (d/'run.log').open('x') as log,(d/'run.err').open('x') as err:
  p=subprocess.run([str(HERE/'amrvac'),'-i',str(HERE/'inputs'/row['base_file']),str(d/'stage.par')],cwd=d,stdout=log,stderr=err,timeout=120)
 assert p.returncode==0 and not (d/'run.err').stat().st_size
 fs=sorted((d/'output').glob('*.vtu'));_,points=read_vtu(fs[0]);actual=max(points,key=lambda p:p[0])[3]*1e-11/KB;expected=float(row['external_pressure_over_k_K_cm3'])
 assert math.isclose(actual,expected,rel_tol=.015),(actual,expected)
 records.append({'case':case,'expected_pressure_over_k':expected,'actual_pressure_over_k':actual,'status':'PASS'})
 print('PASS',case,'P/k='+str(actual),flush=True)
(HERE/'preflight_results.json').write_text(json.dumps(records,indent=2)+'\n')
