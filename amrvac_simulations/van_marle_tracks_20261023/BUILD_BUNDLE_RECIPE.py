from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import csv,hashlib,io,json,os,re,shutil,subprocess,sys,tarfile,contextlib
ROOT=Path('/Users/jkeohane/GRBs');SRC=ROOT/'AMRVAC_Bubble_Models/van_marle_40_ionized_core_1d'
DEST=ROOT/'VegasJetFit_wind_bubble_handoff/amrvac_simulations/van_marle_tracks_20261023'
FULL=DEST/'full_evolution_40Msun_4p77Myr'
sys.path.insert(0,str(SRC));from validate_evolving import validate
sys.path.insert(0,str(ROOT/'AMRVAC_Bubble_Models/van_marle_full_track_grid_20261023'));from grid_runtime import read_vtu
MP=1.6726219e-24

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build(spec):
 os.environ['MPLCONFIGDIR']='/private/tmp/van_marle_publish_mpl_20261023'
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import numpy as np
 family,prefix=spec;run=SRC/'results'/family;target=FULL/family/prefix;target.mkdir(parents=True)
 m=re.search(r'_n(\d+)',prefix);n=int(m.group(1)) if m else 2000
 inner=.01 if 'inner0p01' in family or 'cloud_mass_80pc' in family else .1
 outer=80 if 'cloud_mass_80pc' in family else 40
 log=io.StringIO()
 if prefix.startswith('ion_'):
  with contextlib.redirect_stdout(log):validate(run,prefix,4.77,prefix,n,inner)
 else:
  p=subprocess.run([sys.executable,str(SRC/'validate_cloud_mass.py'),str(run),prefix,'300','4.77','49','--edge-width-pc','.5','--n-bg','10','--inner-pc','.01','--domain-max-pc','80'],capture_output=True,text=True,check=True);log.write(p.stdout)
 (target/'VALIDATION.txt').write_text(log.getvalue())
 files=sorted(p for p in run.glob(prefix+'*') if p.is_file() and p.suffix in ('.vtu','.dat','.log','.err','.exit','.sha256','.json','.csv'))
 vtus=sorted(p for p in files if re.fullmatch(re.escape(prefix)+r'\d{4}\.vtu',p.name));dats=[p for p in files if p.suffix=='.dat'];assert len(vtus)==49 and len(dats)==49
 archive=target/(prefix+'_all_saves.tar.gz')
 with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
  for p in files:tar.add(p,arcname=prefix+'/'+p.name,recursive=False)
 manifests=[{'filename':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
 with (target/'RAW_FILES_SHA256.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(manifests[0]));w.writeheader();w.writerows(manifests)
 plots=target/'density_profiles';plots.mkdir()
 samples=[];allmin=1e99;allmax=0
 for p in vtus:
  age,points=read_vtu(p);a=np.array(points);mask=(a[:,0]>=inner)&(a[:,0]<=outer);a=a[mask];a=a[np.argsort(a[:,0],kind='stable')];nh=a[:,1]*1e-25/(1.4*MP)
  samples.append((p,age,a[:,0],nh));allmin=min(allmin,float(nh.min()));allmax=max(allmax,float(nh.max()))
 for p,age,r,nh in samples:
  fig,ax=plt.subplots(figsize=(7.2,4.4),layout='constrained');ax.loglog(r,nh,lw=1.2,color='#155e75');ax.set(xlim=(inner,outer),ylim=(allmin*.65,allmax*1.5),xlabel='Radius (pc)',ylabel=r'Hydrogen-nucleus density $n_H$ (cm$^{-3}$)',title=f'40 solar masses: {age:.4f} Myr | '+('MS' if age<4.3-1e-6 else 'RSG' if age<4.5-1e-6 else 'WR'))
  ax.text(.02,.02,prefix,transform=ax.transAxes,fontsize=7);ax.grid(alpha=.18,which='both');fig.savefig(plots/(p.stem+'.png'),dpi=130);plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
 for index in (0,1,42,44,46,48):
  _,age,r,nh=samples[index];ax.loglog(r,nh,lw=1.2,label=f'{age:.2f} Myr')
 ax.set(xlim=(inner,outer),xlabel='Radius (pc)',ylabel=r'$n_H$ (cm$^{-3}$)',title='40-solar-mass full MS/RSG/WR evolution');ax.legend(ncol=2,fontsize=8);ax.grid(alpha=.18,which='both');fig.savefig(target/'phase_density_overview.png',dpi=150);plt.close(fig)
 summary={'case':prefix,'family':family,'star_mass_msun':40,'n_input_cm3':n if prefix.startswith('ion_') else 300,'density_convention':'central n0' if prefix.startswith('ion_') else 'n_ref at 1pc','inner_pc':inner,'outer_pc':outer,'endpoint_myr':samples[-1][1],'saved_vtus':49,'saved_dat':49,'density_pngs':49,'archive':str(archive.relative_to(DEST)),'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'gravity':'none' if 'nogravity' in prefix else 'prescribed initial profile','status':'PHASE_COMPLETE_EXPLORATORY'}
 (target/'CASE.json').write_text(json.dumps(summary,indent=2)+'\n')
 return summary

def main():
 DEST.mkdir();FULL.mkdir()
 specs=[]
 for family in ('evolving_20261014','density_sweep_20261014','density_inner0p01_20261014','cloud_mass_80pc_20261014/nref0300/full'):
  for p in sorted((SRC/'results'/family).glob('*0048.vtu')):
   prefix=p.name[:-8]
   if '4p77myr' in prefix or prefix=='cloudmass_nref0300_full':specs.append((family,prefix))
 assert len(specs)==17,(len(specs),specs)
 with ProcessPoolExecutor(max_workers=4) as pool:
  rows=[]
  for row in pool.map(build,specs):rows.append(row);print('PACKAGED',row['case'],flush=True)
 with (FULL/'CASE_INDEX.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 refs=FULL/'reference_sources';refs.mkdir()
 for pattern in ('*.t','*.py','*.par'):
  for p in SRC.glob(pattern):shutil.copy2(p,refs/p.name)
 for d in ('density_inputs_20261014','density_inputs_inner0p01_20261014','cloud_mass_inputs_80pc_20261014'):
  shutil.copytree(SRC/d,refs/d)
 shutil.copy2(SRC/'README.md',FULL/'MODEL_NOTES_ASOF_20261023.md')
 # Complete newer 25-Msun records, including all seven static+wind stages.
 src25=ROOT/'AMRVAC_Bubble_Models/van_marle_25_finite_gmc_1d';test25=DEST/'short_tests_25Msun_1500yr';test25.mkdir()
 for host in sorted((src25/'results/direct_ms_pilots_20261021').iterdir()):
  target=test25/host.name;target.mkdir()
  with tarfile.open(target/(host.name+'_all_static_and_wind_saves.tar.gz'),'w:gz') as tar:
   for parent,tag in [(host,'wind'),(src25/'results/static_pilots_20261021'/host.name,'static')]:
    tar.add(parent,arcname=tag)
  shutil.copytree(src25/'results/direct_ms_diagnostics_20261021'/host.name,target/'density_profiles')
 shutil.copy2(src25/'results/direct_ms_diagnostics_20261021/campaign_endpoint_summary_20261021.csv',test25/'CASE_INDEX.csv')
 shutil.copy2(src25/'README.md',test25/'MODEL_NOTES.md')
 # The 40-Msun companion completed after the October20 handoff.
 test40=DEST/'short_tests_40Msun_1500yr';test40.mkdir()
 raw=SRC/'results/dense_gmc_wr_local_inner_outer_n20000_gmc2000_mac_20480_f12_0015myr_20261021_mac02'
 with tarfile.open(test40/'GMC2000_20480_all_wind_saves.tar.gz','w:gz') as tar:tar.add(raw,arcname=raw.name)
 for d in ('dense_gmc_plots_20261021','dense_gmc_inner_edge_20261021','dense_gmc_comparisons_20261021'):
  shutil.copytree(SRC/'results'/d,test40/d)
 print('DONE:',len(rows),'phase-complete 40-Msun runs,',sum(r['saved_vtus'] for r in rows))
if __name__=='__main__':main()
