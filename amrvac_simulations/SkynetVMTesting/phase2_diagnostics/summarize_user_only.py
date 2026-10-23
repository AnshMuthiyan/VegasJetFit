# Purpose: Record completed validation of the delivered user-module/parameter-only setup without claiming full stellar-lifetime coverage.
import hashlib
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
build=json.loads((HERE/'user_module_only_build/build.json').read_text())
current=hashlib.sha256((HERE.parent/'mod_usr.t').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
assert build['user_module_sha256']==current
expected={'old_failure_regression','tc_off_rc_off','tc_off_rc_on','tc_on_rc_off','tc_on_rc_on'}
completed=[]
for path in sorted(HERE.glob('*_user_only_checks/results.json')):
    report=json.loads(path.read_text())
    if report['build']['user_module_sha256']!=current:
        continue
    if {r['case'] for r in report['cases']}==expected and all(r['passed'] for r in report['cases']):
        completed.append((path,report))
assert completed,'Final-source five-case checks are not complete'
path,report=completed[-1]
for row in report['cases']:
    audit=path.parent/row['case']/'output/test_tc_floor.csv'
    if audit.exists():
        records=list(csv.DictReader(audit.read_text().splitlines()[1:]))
        row['last_tc_floor_record']=records[-1]
result={'purpose':'Document successful short validation on unmodified AMRVAC 3.2 and the remaining full-duration uncertainty.',
        'passed_short_checks':True,'build':build,'report':str(path.relative_to(HERE)),
        'cases':report['cases'],
        'delivered_inputs':'../mod_usr.t and the four ../tc_*/run.par files; no engine patch required.',
        'initial_condition_change':'Fresh 25 Msun analytic MS free wind inside 0.03 pc; unchanged 100 K, 1e4 total-particle/cm3 ambient outside.',
        'limits':['Fresh 25 Msun tests cover the first 1000 years only, not 7 Myr.',
                  'The old-failure regression uses the historical 40 Msun gas checkpoint reset to 4.3 Myr; it tests the numerical failure, not a physical 25 Msun RSG bubble.',
                  'Runtime overhead has not been measured separately. User-hook checks still have a cost.']}
(HERE/'user_only_validation.json').write_text(json.dumps(result,indent=2)+'\n')
status=json.loads((HERE/'WORK_STATUS.json').read_text())
status.update(purpose='Track the delivered solution using unmodified AMRVAC core and user-module/parameter changes only.',
              status='User-module-only build and short checks complete.',active_jobs=[],
              best_current_build='user_module_only_build',final_validation='user_only_validation.json',
              delivered_package='Parent SkynetVMTesting mod_usr.t and four case run.par files.',
              future_optional_validation='Complete 25 Msun evolution and RSG switch through 7 Myr.')
(HERE/'WORK_STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
print('FINAL USER-ONLY VALIDATION PASSED',path)
for row in report['cases']:
    print(row['case'],row['last_saved_age_years'],'invalid saved cells:',row['invalid_saved_cells'])
