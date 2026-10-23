#!/usr/bin/env python3
"""Read-only compact process and artifact status for the six grid farms."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,json,shlex,subprocess
HERE=Path(__file__).resolve().parent
CODE='''import pathlib,json,re,subprocess
farm=pathlib.Path(FARM)
rows=[]
for d in sorted((farm/'runs').glob('*')):
 case=d.name;status='STATIC'
 for stage in ('smoke','full'):
  if (d/(case+'_'+stage+'.run.log')).exists():status=stage.upper()
 if (d/'FAILED.json').exists():status='FAILED'
 if (d/'COMPLETE.json').exists():status='VALIDATED_FULL_TRACK'
 stage='full' if list((d/'output').glob(case+'_full*.vtu')) else ('smoke' if list((d/'output').glob(case+'_smoke*.vtu')) else 'static')
 files=sorted((d/'output').glob(case+'_'+stage+'*.vtu'));age=None
 if files:
  with files[-1].open('rb') as f:head=f.read(64000)
  m=re.search(rb'Name="TIME"[^>]*>\\s*([^<]+)',head)
  if m:age=float(m.group(1))*3.085677581e18/1e7/(365*86400)/1e6
 live_age=age
 log=d/(case+'_'+stage+'.run.log')
 if log.exists():
  with log.open('rb') as f:f.seek(max(0,log.stat().st_size-32000));tail=f.read().decode(errors='replace')
  for line in tail.splitlines():
   if line.startswith(' FRONT '):
    try:live_age=float(line.split()[2])
    except (ValueError,IndexError):pass
 err=d/(case+'_'+stage+'.run.err')
 r={'case':case,'status':status,'latest_stage':stage,'saved_vtus':len(files),'saved_age_myr':age,'live_age_myr':live_age,'stderr_bytes':err.stat().st_size if err.exists() else None}
 if status=='FAILED':r['error']=json.loads((d/'FAILED.json').read_text())
 rows.append(r)
processes=[line.strip() for line in subprocess.check_output(['ps','-axo','pid,pcpu,etime,comm'],text=True).splitlines() if pathlib.Path(line.split()[-1]).name=='amrvac']
print(json.dumps({'farm':str(farm),'cases':rows,'amrvac_processes':processes,'queue_finished':(farm/'queue.finished').exists()}))
'''
def get(r):
 py='/opt/homebrew/bin/python3' if r['arch']=='arm64' else 'python3'
 command=py+' -c '+shlex.quote(CODE.replace('FARM',repr(r['farm'])))
 p=subprocess.run(['ssh','-n','-x','-o','ForwardX11=no','-o','BatchMode=yes','-o','ConnectTimeout=10',r['host'],command],capture_output=True,text=True,timeout=30)
 return {'host':r['host'],**(json.loads(p.stdout) if p.returncode==0 else {'status':'UNKNOWN','error':p.stderr.strip()})}
if __name__=='__main__':
 records=json.loads((HERE/'dispatch_records.json').read_text())
 with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(get,records))
 print(json.dumps({'queried_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hosts':results},indent=2))
