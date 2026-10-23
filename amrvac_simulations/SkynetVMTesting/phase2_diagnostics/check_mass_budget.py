# Purpose: Independently compare native-snapshot gas-mass changes against the prescribed wind mass injected during each completed test.
import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from plot_dat_folder import read_snapshot
PC = 3.0857e18
MSUN = 1.98892e33  # AMRVAC 3.2 mod_constants, not a different solar-mass convention.


def native_path(text):
    if os.name == 'nt' and text.startswith('/mnt/c/'):
        return Path('C:/'+text[7:])
    return Path(text)


def mass(path, par):
    data=read_snapshot(path, par)
    if data['invalid_cells']:
        raise RuntimeError('Invalid gas state: '+str(path))
    return math.fsum(c[2]*(4*math.pi/3)*PC**3*(c[1]**3-c[0]**3) for c in data['cells'])/MSUN


def wind_mass(start,end):
    total=0.
    for low,high,rate in [(0,4.3e6,1e-6),(4.3e6,4.5e6,5e-5),(4.5e6,4.77e6,1e-5)]:
        total+=max(0.,min(end,high)-max(start,low))*rate
    return total


rows=[]
for report_path in sorted(HERE.glob('*/results.json')):
    report=json.loads(report_path.read_text())
    if 'cancellation_note' in report:
        continue
    for case in report['cases']:
        if not case.get('passed'):
            continue
        folder=report_path.parent/case['case']
        par=folder/'run.par'
        source=native_path(report['checkpoint'])
        final=sorted((folder/'output').glob('test*.dat'))[-1]
        initial_mass=mass(source,par)
        final_mass=mass(final,par)
        start=report.get('start_age_years',4.3e6)
        end=case['last_saved_age_years']
        injected=wind_mass(start,end)
        change=final_mass-initial_mass
        row={'batch':report_path.parent.name,'case':case['case'],
             'initial_mass_Msun':initial_mass,'final_mass_Msun':final_mass,
             'mass_change_Msun':change,'wind_injected_Msun':injected,
             'relative_mass_difference':(change-injected)/injected}
        rows.append(row)
        print(row['batch'],case['case'],'delta M=',change,'expected=',injected,
              'relative difference=',row['relative_mass_difference'])
(HERE/'mass_budget.json').write_text(json.dumps({
    'purpose':'Independent volume-integrated mass-budget comparison for completed candidate tests.',
    'interpretation':'Difference includes numerical inner-boundary flux error and any outer-boundary flux, not just refinement error.',
    'cases':rows},indent=2)+'\n')
