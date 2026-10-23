# Purpose: Independently validate every saved diagnostic snapshot and summarize completed local phase-switch experiments.
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from plot_dat_folder import read_snapshot, scalar


def main():
    summary = {'purpose': 'Local phase-2 diagnostic outcomes and independent checkpoint validation.',
               'cases': [], 'deliberately_stopped_batches': []}
    for report_path in sorted(HERE.glob('*/results.json')):
        report = json.loads(report_path.read_text())
        if 'cancellation_note' in report:
            summary['deliberately_stopped_batches'].append(report_path.parent.name)
            continue
        for original in report['cases']:
            folder = report_path.parent/original['case']
            row = dict(original, batch=report_path.parent.name, ranks=report['ranks'])
            row.pop('log', None)
            snapshots = sorted((folder/'output').glob('test*.dat'))
            invalid, minimum_p, maximum_t = 0, float('inf'), 0
            for snapshot in snapshots:
                data = read_snapshot(snapshot, folder/'run.par')
                invalid += data['invalid_cells']
                minimum_p = min(minimum_p, *(cell[4] for cell in data['cells']))
                maximum_t = max(maximum_t, *(cell[5] for cell in data['cells']))
            row.update(saved_snapshots_checked=len(snapshots), invalid_saved_cells=invalid,
                       minimum_saved_pressure_cgs=minimum_p if snapshots else None,
                       maximum_saved_temperature_K=maximum_t if snapshots else None)
            row.setdefault('passed', False)
            log=(folder/'run.log').read_text(errors='replace')
            par=(folder/'run.par').read_text()
            tc=scalar(par,'hd_thermal_conduction')=='.true.'
            rc=scalar(par,'hd_radiative_cooling')=='.true.'
            row['physics_flags_match']=(('Spitzer HD par:' in log)==tc and
                                        ('Cooling Tfix enabled: T' in log)==rc)
            row['refinement_parent_copy_events']=log.count('AMR parent-copy fallback')
            row['passed']=row['passed'] and row['physics_flags_match']
            guard = folder/'output/test_guard.csv'
            if guard.exists():
                records = list(csv.DictReader(guard.read_text().splitlines()[1:]))
                if records:
                    row['max_recorded_rescue_evaluations'] = max(float(r['rescue_events']) for r in records)
                    row['max_recorded_rescue_energy_erg'] = max(float(r['evaluation_energy_erg']) for r in records)
                    row['last_recorded_audit_age_yr'] = float(records[-1]['age_yr'])
            tc_guard=folder/'output/test_tc_floor.csv'
            if tc_guard.exists():
                records=list(csv.DictReader(tc_guard.read_text().splitlines()[1:]))
                if records:
                    row['tc_floor_events']=max(float(r['tc_floor_events']) for r in records)
                    row['tc_floor_evaluation_energy_erg']=max(float(r['tc_floor_evaluation_energy_erg']) for r in records)
                    row['tc_floor_worst_cell_fraction']=max(float(r['worst_cell_fraction']) for r in records)
                    row['tc_floor_audit_final_age_yr']=float(records[-1]['age_yr'])
                    row['tc_floor_audit_covers_final_state']=abs(row['tc_floor_audit_final_age_yr']-
                        row.get('last_saved_age_years',float('inf')))<1e-3
            summary['cases'].append(row)
    (HERE/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    for row in summary['cases']:
        print(row['batch'], row['case'], 'completed=', row['completed'],
              'saved_age=', row.get('last_saved_age_years'),
              'rescues=', row.get('max_recorded_rescue_evaluations'))


if __name__ == '__main__':
    main()
