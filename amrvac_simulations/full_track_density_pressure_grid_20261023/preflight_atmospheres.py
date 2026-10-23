#!/usr/bin/env python3
"""Independent initial-state/static gates at opposite corners of the grid."""
import csv,json,pathlib
from grid_runtime import HERE,run_stage,check
rows=list(csv.DictReader((HERE/'manifest.csv').open()))
out=HERE/'atmosphere_preflight_final';out.mkdir()
records=[]
for case in ('m25_n3000_pk1000000','m40_n30000_pk1000000000'):
 row=next(r for r in rows if r['case']==case);d=out/case;d.mkdir();(d/'output').mkdir()
 run_stage(d,row,'static',7200);records.append(check(d,row,'static',.01,2))
 run_stage(d,row,'smoke',1800);records.append(check(d,row,'smoke',.0001,2))
 print('PASS',case,'static and wind smoke',flush=True)
(HERE/'atmosphere_preflight_results.json').write_text(json.dumps(records,indent=2)+'\n')
