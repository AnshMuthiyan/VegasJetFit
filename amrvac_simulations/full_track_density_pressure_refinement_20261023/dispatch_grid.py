#!/usr/bin/env python3
"""One-time exact-SHA midpoint dispatch alongside the existing healthy grid."""
from pathlib import Path
import csv,datetime,hashlib,json,shlex,subprocess
HERE=Path(__file__).resolve().parent
rows=list(csv.DictReader((HERE/'manifest.csv').open()))
assert len(rows)==46 and not (HERE/'dispatch_records.json').exists(),'Refinement already dispatched'
for arch in ('arm64','linux_x86_64'):
 for name,count in (('preflight_results.json',9),('atmosphere_preflight_results.json',4)):
  r=json.loads((HERE/'builds'/arch/name).read_text());assert len(r)==count and all(x['status']=='PASS' for x in r)
 assert (HERE/'builds'/arch/'mod_usr.t').read_bytes()==(HERE/'mod_usr.t').read_bytes()
records=[]
for host in dict.fromkeys(r['host'] for r in rows):
 arch='arm64' if host.startswith('pauley') else 'linux_x86_64'
 farm=('/private/tmp/' if arch=='arm64' else '/tmp/')+'van_marle_full_grid_refinement_20261023_farm'
 original_farm=('/private/tmp/' if arch=='arm64' else '/tmp/')+'van_marle_full_grid_20261023_farm'
 old_workers=0 if host=='pauley404-03' else 4
 new_workers=sum(r['host']==host for r in rows)
 ssh=['ssh','-n','-x','-o','ForwardX11=no','-o','BatchMode=yes','-o','ConnectTimeout=10',host]
 pre='''import os,pathlib,shutil,subprocess,json
farm=pathlib.Path(FARM)
assert not farm.exists(),'farm exists; refuse duplicate'
cores=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 0)
assert cores>=OLD+NEW+1,'insufficient CPU capacity'
assert shutil.disk_usage(farm.parent).free>5*2**30,'insufficient free disk'
processes=subprocess.check_output(['ps','-axo','command='],text=True).splitlines()
amrvac=[p for p in processes if pathlib.Path(p.strip().split()[0]).name=='amrvac']
assert len(amrvac)==OLD,'unexpected AMRVAC process count'
assert all(p.startswith(ORIGINAL+'/amrvac ') for p in amrvac),'unexpected AMRVAC source farm'
farm.mkdir();print(json.dumps({'available_logical_cores':cores,'existing_amrvac':len(amrvac),'new_cases':NEW,'free_disk_GiB':round(shutil.disk_usage(farm).free/2**30,1)}))
'''.replace('FARM',repr(farm)).replace('ORIGINAL',repr(original_farm)).replace('OLD',str(old_workers)).replace('NEW',str(new_workers))
 py='/opt/homebrew/bin/python3' if arch=='arm64' else 'python3'
 resource=subprocess.check_output(ssh+[py+' -c '+shlex.quote(pre)],text=True).strip()
 files={p.name:p for p in (HERE/'mod_usr.t',HERE/'grid_runtime.py',HERE/'manifest.csv',HERE/'design.json',HERE/'README.md')}
 files['amrvac']=HERE/'builds'/arch/'amrvac'
 files.update({'inputs/'+p.name:p for p in sorted((HERE/'inputs').glob('*.par'))})
 pins={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files.items()}
 pinfile=HERE/'builds'/arch/('pins_'+host+'.json');pinfile.write_text(json.dumps(pins,indent=2)+'\n')
 subprocess.run(['rsync','-a','--ignore-existing','-e','ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=10',*[str(files[n]) for n in files if not n.startswith('inputs/')],str(HERE/'inputs'),host+':'+farm+'/'],check=True)
 subprocess.run(['rsync','-a','--ignore-existing','-e','ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=10',str(pinfile),host+':'+farm+'/build_pins.json'],check=True)
 launch='''import hashlib,json,pathlib,subprocess
farm=pathlib.Path(FARM)
pins=json.loads((farm/'build_pins.json').read_text())
for name,digest in pins.items():assert hashlib.sha256((farm/name).read_bytes()).hexdigest()==digest,name
(farm/'amrvac').chmod(0o755)
assert not (farm/'queue.pid').exists(),'queue already claimed'
with (farm/'queue.pid').open('x') as pidfile,(farm/'queue.log').open('x') as log:
 p=subprocess.Popen([PY,str(farm/'grid_runtime.py'),HOST],cwd=farm,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 pidfile.write(str(p.pid)+'\\n')
print('PID',p.pid)
'''.replace('FARM',repr(farm)).replace('PY',repr(py)).replace('HOST',repr(host))
 launched=subprocess.check_output(ssh+[py+' -c '+shlex.quote(launch)],text=True).strip()
 record={'host':host,'farm':farm,'arch':arch,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':[r['case'] for r in rows if r['host']==host],'launch':launched,'resources':json.loads(resource),'pins_file':str(pinfile.relative_to(HERE))}
 records.append(record);(HERE/'dispatch_records.json').write_text(json.dumps(records,indent=2)+'\n')
 print(host,launched,new_workers,'distinct one-core midpoint cases; static/smoke gates precede full evolution',flush=True)
