# Purpose: Compare identical fixed-work WR continuations at 1, 2, 4, and 8 MPI ranks without altering conduction or cooling.
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
BUILD=HERE/'positive_amr_flux_candidate'
sys.path.insert(0,str(HERE.parent))
from plot_dat_folder import read_snapshot
parser=argparse.ArgumentParser()
parser.add_argument('checkpoint',type=Path)
args=parser.parse_args()
checkpoint=args.checkpoint.resolve(strict=True)
initial=read_snapshot(checkpoint)
rows=[]
for ranks in (1,2,4,8):
    label='wr_rank_benchmark_'+str(ranks)
    command=[sys.executable,str(HERE/'run_tests.py'),'--executable',str(BUILD/'amrvac'),
             '--source-dir',str(BUILD),'--checkpoint',str(checkpoint),
             '--start-age-years',str(initial['age_years']),'--cases','both','--ghost-copy',
             '--ranks',str(ranks),'--courant','0.1','--steps','1000','--save-years','10000',
             '--label',label,'--timeout','300']
    print('BENCHMARK RANKS',ranks,flush=True)
    subprocess.run(command,check=True)
    report_path=sorted(HERE.glob('*_'+label+'/results.json'))[-1]
    report=json.loads(report_path.read_text())
    row=dict(report['cases'][0],ranks=ranks,report=str(report_path))
    rows.append(row)
    (HERE/'wr_rank_benchmark.json').write_text(json.dumps({
        'purpose':'Fixed-work WR rank comparison with identical physics and starting gas state.',
        'checkpoint':str(checkpoint),'cases':rows},indent=2)+'\n')
    if not row.get('passed'):
        raise RuntimeError('A benchmark failed; inspect its log before continuing')
print('FASTEST INTEGRATION RANK COUNT',min(rows,key=lambda r:r['timeloop_seconds'])['ranks'],flush=True)
