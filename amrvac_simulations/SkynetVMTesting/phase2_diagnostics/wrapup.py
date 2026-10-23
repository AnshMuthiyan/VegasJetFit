# Purpose: Audit saved final-source diagnostic states and record the exact validation limits at wrap-up.
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from plot_dat_folder import read_snapshot

rows = []
for batch, case in [('20261020_103817_audited_rsg_full','both'),
                    ('20261020_103525_audited_full_wr','both'),
                    ('20261020_155102_exact_matrix_tc_off_rc_off','neither')]:
    folder = HERE/batch/case
    report = json.loads((folder.parent/'results.json').read_text())
    paths = sorted((folder/'output').glob('test*.dat'))
    snapshots = [read_snapshot(p, folder/'run.par') for p in paths]
    assert snapshots and not sum(s['invalid_cells'] for s in snapshots)
    row = {'batch':batch, 'case':case, 'start_age_years':report['start_age_years'],
           'latest_saved_age_years':max(s['age_years'] for s in snapshots),
           'latest_checkpoint':str(max(zip(paths,snapshots),key=lambda x:x[1]['age_years'])[0].relative_to(HERE)),
           'snapshots_checked':len(snapshots), 'invalid_saved_cells':0,
           'minimum_saved_pressure_cgs':min(c[4] for s in snapshots for c in s['cells']),
           'courant':report['courant'],
           'target_completed':report['cases'][0]['completed'],
           'deliberate_stop':report.get('cancellation_note')}
    audit = folder/'output/test_tc_floor.csv'
    if audit.exists():
        records = list(csv.DictReader(audit.read_text().splitlines()[1:]))
        row['tc_floor_last_record'] = records[-1]
    rows.append(row)
result = {'purpose':'Record successful stability checks and unfinished full-duration coverage without treating deliberate stops as numerical failures.',
          'status':'Stable over sustained phase-switch tests; diagnostic jobs checkpointed and stopped at user request.',
          'source_commit':'c45d84650ed3379eb22dcfa6fb927a45734e5d8c',
          'final_source_checks':rows,
          'earlier_matrix':'Other three physics combinations completed 201000 years through the WR switch with the same AMR fix, before the subsequent prescribed-wind-flux correction and TC observer.',
          'remaining_limit':'Full 4.77-Myr endpoint and full four-case matrix with the final source have not been completed. Saved-state checks do not inspect every intermediate substep.',
          'clean_install_report':'clean_install_verification.json',
          'restart_caveat':'Original approximately 1-Myr gas is reused with stellar clock reset to 4.3 Myr; omitted MS evolution is not reconstructed.'}
clean = json.loads((HERE/'clean_install_verification.json').read_text())
assert clean['passed']
smoke = max(HERE.glob('*_clean_install_smoke'))
smoke_report = json.loads((smoke/'results.json').read_text())
assert all(c['passed'] for c in smoke_report['cases'])
reference = HERE/'20261020_103351_tc_audit_equivalence/both/output/test0000.dat'
actual = next((smoke/'both/output').glob('test*.dat'))
assert read_snapshot(reference)['cells'] == read_snapshot(actual)['cells']
result['clean_build_and_restart'] = {'passed':True,'steps':1000,
    'physics_flags_match':True,'matches_previous_decoded_cells_exactly':True,
    'report':str((smoke/'results.json').relative_to(HERE))}
(HERE/'wrapup_validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
status = json.loads((HERE/'WORK_STATUS.json').read_text())
status.update(purpose='Preserve the completed local stability investigation and exact validation limits.',
              active_jobs=[],next_steps=[],status='Wrapped up at user request; diagnostics checkpointed and stopped.',
              final_validation='wrapup_validation.json',
              delivered_package='../ConservativeAMRRestart',
              temporary_power_request='Released; normal automatic sleep restored.',
              future_optional_validation='Complete final-source four-case matrix and remaining WR interval to 4.77 Myr.')
(HERE/'WORK_STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(rows,indent=2))
