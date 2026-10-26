#!/usr/bin/env python3
"""Serial-per-host guarded full-track queue and independent saved-field checks."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,pathlib,re,shutil,signal,struct,subprocess,time
from concurrent.futures import ThreadPoolExecutor
HERE=pathlib.Path(__file__).resolve().parent
PC=3.085677581e18; YEAR=365*86400.; KB=1.380649e-16; MP=1.6726219e-24
TIME_MYR=PC/1e7/YEAR/1e6

def digest(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def read_vtu(p):
 raw=pathlib.Path(p).read_bytes();app=raw.index(b'<AppendedData');base=raw.index(b'_',app)+1
 header=raw[:app].decode('ascii');age=float(re.search(r'Name="TIME"[^>]*>\s*([^<]+)',header).group(1))*TIME_MYR
 points=[]
 for piece in re.finditer(r'<Piece\b[^>]*>(.*?)</Piece>',header,re.S):
  body=piece.group(1)
  def array(pattern):
   m=re.search(pattern,body,re.S)
   if m is None:raise ValueError('VTU missing array '+pattern)
   offset=base+int(m.group(1));n=struct.unpack_from('<I',raw,offset)[0]
   if n%4:raise ValueError('VTU array is not float32')
   return struct.unpack_from('<'+str(n//4)+'f',raw,offset+4)
  xyz=array(r'<Points>\s*<DataArray[^>]*offset="\s*(\d+)"');rho=array(r'<DataArray[^>]*Name="rho"[^>]*offset="\s*(\d+)"')
  v=array(r'<DataArray[^>]*Name="v1"[^>]*offset="\s*(\d+)"');p=array(r'<DataArray[^>]*Name="p"[^>]*offset="\s*(\d+)"')
  for i in range(len(rho)):points.append((xyz[3*i],rho[i],v[i],p[i]))
 if not points:raise ValueError('No saved points')
 for r,rho,v,p in points:
  if not all(math.isfinite(x) for x in (r,rho,v,p)) or rho<=0 or p<=0:raise ValueError('Nonfinite/nonpositive saved fields')
 return age,points

def check(root,row,stage,expected_age,expected_count):
 case=row['case']+'_'+stage;root=pathlib.Path(root)
 if (root/(case+'.run.exit')).read_text().strip()!='0':raise ValueError('Nonzero guarded exit')
 log=(root/(case+'.run.log')).read_text()
 if log.count('Finished AMRVAC')!=1 or (root/(case+'.run.err')).stat().st_size:raise ValueError('Finish/stderr gate failed')
 matches=re.findall(r'EXTERNAL_PRESSURE\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)',log)
 if len(matches)!=1:raise ValueError('Missing/duplicate boundary-pressure initialization')
 pk,pressure=map(float,matches[0])
 expected_pk=float(row['external_pressure_over_k_K_cm3'])
 if not math.isclose(pk,expected_pk,rel_tol=1e-8) or not math.isclose(pressure,pk*KB,rel_tol=1e-8):raise ValueError('Boundary pressure does not match manifest')
 files=sorted((root/'output').glob(case+'[0-9][0-9][0-9][0-9].vtu'))
 if len(files)!=expected_count:raise ValueError(f'Expected {expected_count} VTUs, got {len(files)}')
 ages=[];phase_samples={};initial=None;drift=0.;endpoints=None
 for f in files:
  age,points=read_vtu(f);ages.append(age)
  if initial is None:
   initial=points
   outer=max(points,key=lambda p:p[0]);actual_pk=outer[3]*1e-11/KB
   if not math.isclose(actual_pk,expected_pk,rel_tol=.015):raise ValueError(f'Initial outer P/k {actual_pk} != {expected_pk}')
   nref=float(row['n_ref_cm3_at_1pc'])
   for r,rho,v,p in points:
    if .08<r<1.5:
     core=nref*((1+(.2**-2))/(1+(r/.2)**2))**.9
     taper=.5*(1-math.tanh((r-2)/.5));ambient=10+990*.5*(1-math.tanh(r-15))
     expected=ambient+max(0,core-ambient)*taper
     if not math.isclose(rho*1e-25/(1.4*MP),expected,rel_tol=.025):raise ValueError('Initial density differs from analytic finite-GMC model')
  if stage=='static':
   for x,y in zip(points,initial):
    if .05<x[0]<14:drift=max(drift,abs(x[1]/y[1]-1))
  if stage=='full':
   mass=int(row['star_mass_msun']);which=None
   if mass==25:
    if abs(age-6.4)<1e-5:which=('MS',1500.)
    if abs(age-6.6)<1e-5:which=('RSG',15.)
   else:
    if abs(age-4.2)<1e-5:which=('MS',2000.)
    if abs(age-4.4)<1e-5:which=('RSG',15.)
    if abs(age-4.6)<1e-5:which=('WR',2000.)
   if which:
    inner=[x[2]*100 for x in points if x[0]<.04]
    phase_samples[which[0]]={'saved_age_myr':age,'injected_speed_kms':which[1],'evolved_inner_speeds_kms':inner}
  endpoints=points
 if not math.isclose(ages[0],0,abs_tol=1e-9) or not math.isclose(ages[-1],expected_age,abs_tol=2e-6) or not all(b>a for a,b in zip(ages,ages[1:])):raise ValueError('Saved age sequence failed')
 if stage=='static' and drift>.02:raise ValueError(f'Static core drift exceeds 2% survey gate: {drift}')
 if stage=='full' and len(phase_samples)!=(2 if int(row['star_mass_msun'])==25 else 3):raise ValueError('Incomplete saved phase coverage')
 if stage=='full':
  track=re.findall(r'^ TRACK\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)',log,re.M)
  seen=set()
  for age,mdot,speed in track:
   age,mdot,speed=map(float,(age,mdot,speed));mass=int(row['star_mass_msun'])
   boundaries=(6.5,7.) if mass==25 else (4.3,4.5,4.77)
   if any(abs(age-t)<1e-7 for t in boundaries):continue
   if mass==25:phase,em,ev=('MS',2e-7,1500.) if age<6.5 else ('RSG',1e-5,15.)
   elif age<4.3:phase,em,ev='MS',1e-6,2000.
   elif age<4.5:phase,em,ev='RSG',5e-5,15.
   else:phase,em,ev='WR',1e-5,2000.
   if not math.isclose(mdot,em,rel_tol=1e-7) or not math.isclose(speed,ev,rel_tol=1e-7):raise ValueError('Injected wind track mismatch')
   seen.add(phase)
  if seen!=set(phase_samples):raise ValueError('Missing injected phase diagnostics')
 result={'case':row['case'],'stage':stage,'saved_vtus':len(files),'endpoint_myr':ages[-1],'external_pressure_over_k_K_cm3':expected_pk,'max_static_density_drift':drift,'phase_samples':phase_samples,'status':'PASS','files_sha256':{str(f.relative_to(root)):digest(f) for f in files}}
 (root/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

def run_stage(case_root,row,stage,guard):
 prefix=row['case']+'_'+stage
 for suffix in ('run.log','run.err','run.exit'):
  if (case_root/(prefix+'.'+suffix)).exists():raise RuntimeError('Refusing duplicate/overwrite')
 env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
 with (case_root/(prefix+'.run.log')).open('x') as log,(case_root/(prefix+'.run.err')).open('x') as err:
  p=subprocess.Popen([str(HERE/'amrvac'),'-i',str(HERE/'inputs'/row['base_file']),str(HERE/'inputs'/row[stage+'_file'])],cwd=case_root,stdout=log,stderr=err,env=env,start_new_session=True)
  try:rc=p.wait(timeout=guard)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   rc=124
 (case_root/(prefix+'.run.exit')).write_text(str(rc)+'\n')
 if rc:raise RuntimeError(f'{stage} exited {rc}; no retry')

def queue(host):
 rows=[r for r in csv.DictReader((HERE/'manifest.csv').open()) if r['host']==host]
 pins=json.loads((HERE/'build_pins.json').read_text())
 for name,sha in pins.items():
  if digest(HERE/name)!=sha:raise RuntimeError('Transferred SHA mismatch: '+name)
 commands=subprocess.check_output(['ps','-axo','comm='],text=True).splitlines()
 if any(pathlib.Path(x.strip()).name=='amrvac' for x in commands):raise RuntimeError('Host already has an AMRVAC process before queue launch')
 with (HERE/'queue.started').open('x') as f:f.write(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+'\n')
 output=HERE/'runs';output.mkdir(exist_ok=True)
 def work(row):
  root=output/row['case']
  if root.exists():raise RuntimeError('Case already claimed: '+str(root))
  root.mkdir();(root/'output').mkdir();(root/'manifest_row.json').write_text(json.dumps(row,indent=2)+'\n')
  try:
   run_stage(root,row,'static',7200)
   check(root,row,'static',.01,2)
   run_stage(root,row,'smoke',1800)
   check(root,row,'smoke',.0001,2)
   run_stage(root,row,'full',int(row['guard_seconds']))
   check(root,row,'full',float(row['endpoint_myr']),int(row['expected_vtus']))
   (root/'COMPLETE.json').write_text(json.dumps({'completed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'VALIDATED_FULL_TRACK'})+'\n')
   print('COMPLETE',row['case'],flush=True)
  except Exception as exc:
   (root/'FAILED.json').write_text(json.dumps({'error':str(exc),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})+'\n')
   print('FAILED',row['case'],str(exc),flush=True)
 with ThreadPoolExecutor(max_workers=min(4,max(1,(os.cpu_count() or 2)//2))) as pool:
  list(pool.map(work,rows))
 # A failed independent case is preserved; later independent cases are still useful.
 (HERE/'queue.finished').write_text(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('host');a=p.parse_args();queue(a.host)
