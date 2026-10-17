# Purpose: Re-audit completed native snapshots and summarize all repair experiments.
from pathlib import Path
import argparse
import csv
import math
import audit_native

ROOT=Path(__file__).resolve().parent.parent


def result(folder):
    path=folder/'result.txt'
    if not path.exists():
        interrupted=any(folder.name.startswith(marker.name.removesuffix('_STOPPED.txt')+'_')
                        for marker in folder.parent.glob('*_STOPPED.txt'))
        return {'name':folder.name,'passed':'INTERRUPTED' if interrupted else 'PENDING'}
    info={}
    for line in path.read_text().splitlines():
        if line.startswith('#') or '=' not in line: continue
        key,value=line.split('=',1)
        info[key]=value
    if info.get('passed')=='True':
        rows=[audit_native.audit(path) for path in sorted((folder/'output').glob('test*.dat'))]
        if not rows: raise RuntimeError('No native evidence in '+str(folder))
        with (folder/'native_audit.csv').open('w',newline='') as stream:
            stream.write('# Purpose: Independent native-cell positivity and physics audit.\n')
            writer=csv.DictWriter(stream,fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)
        info.update({key:rows[-1][key] for key in ['disturbed_radius_pc','shell_mass_g',
            'total_energy_erg','thermal_energy_erg','max_temperature_K']})
        info['min_temperature_K']=min(row['min_temperature_K'] for row in rows)
        if not math.isclose(rows[-1]['age_yr'],float(info['years']),rel_tol=1e-10):
            raise RuntimeError('Final age mismatch in '+str(folder))
    par=(folder/'run.par').read_text()
    import re
    info['courantpar']=re.search(r'courantpar=(\S+)',par).group(1)
    info['flux_scheme']=re.search(r'flux_scheme=(\S+)',par).group(1)
    match=re.search(r'qstretch_baselevel\(1\)=(\S+)',par)
    info['qstretch']=match.group(1) if match else 'auto'
    return info


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--require-complete',action='store_true')
    parser.add_argument('--require-selected',action='store_true')
    args=parser.parse_args()
    folders=sorted((ROOT/'validation').iterdir())
    rows=[result(folder) for folder in folders if folder.is_dir()]
    columns=['name','case','years','passed','wall_seconds','ranks','courantpar','flux_scheme','qstretch','rescue_events',
        'final_evaluation_fraction','worst_cell_fraction','min_temperature_K',
        'disturbed_radius_pc','shell_mass_g','total_energy_erg','thermal_energy_erg','max_temperature_K']
    with (ROOT/'validation_summary.csv').open('w',newline='') as stream:
        stream.write('# Purpose: Re-audited repair, physics, and accelerated-phase validation results.\n')
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row['name'],row.get('passed'),row.get('rescue_events',''),row.get('disturbed_radius_pc',''))
    pending=[row for row in rows if row.get('passed')=='PENDING']
    failed=[row for row in rows if row.get('passed')=='False']
    print('Passed:',sum(row.get('passed')=='True' for row in rows),'Pending:',len(pending),'Failed:',len(failed))
    if args.require_complete and (pending or failed or len(rows)<15): raise SystemExit(1)
    if args.require_selected:
        cases=['tc_off_rc_off','tc_on_rc_off','tc_off_rc_on','tc_on_rc_on']
        required=['tvdlf_physics_1000yr_'+case for case in cases]
        required += ['tvdlf_phase_150yr_'+phase+'_'+case for phase in ['MS_RSG','RSG_WR'] for case in cases]
        index={row['name']:row for row in rows}
        for name in required:
            row=index.get(name,{})
            if row.get('passed')!='True' or float(row.get('rescue_events','nan'))!=0:
                raise SystemExit('Selected setup is not yet validated without rescue: '+name)
            if row['flux_scheme']!="20*'tvdlf'" or row['courantpar']!='0.1d0' or row['qstretch']!='1.03d0':
                raise SystemExit('Selected test uses inconsistent numerical parameters: '+name)
            folder=ROOT/'validation'/name
            if (folder/'mod_usr.t').read_bytes()!=(ROOT/'mod_usr.t').read_bytes():
                raise SystemExit('Selected test source differs from current source: '+name)
            transcript=(folder/'run.log').read_text()
            tc=row['case'].startswith('tc_on_')
            rc=row['case'].endswith('_rc_on')
            if ('Spitzer HD par:' in transcript)!=tc or ('Cooling Tfix enabled: T' in transcript)!=rc:
                raise SystemExit('Runtime physics activation mismatch: '+name)
        print('SELECTED SETUP PASSED: all four 1000-year cases and all eight transition tests; zero rescues.')
