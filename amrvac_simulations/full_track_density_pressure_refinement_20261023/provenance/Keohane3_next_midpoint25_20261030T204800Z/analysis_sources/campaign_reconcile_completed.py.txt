#!/usr/bin/env python3
"""Use the native parent analysis with this campaign's frozen rows/checker.

No dispatch, network operations or overwrite of completed analysis products.
"""
import argparse
import csv
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PARENT = next(p for p in [HERE.parent/'van_marle_full_track_grid_20261023',
    HERE.parent/'full_track_density_pressure_grid_20261023'] if p.is_dir())
sys.path.insert(0, str(PARENT))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host_result_root', type=Path)
    args = parser.parse_args()
    engine = module('native_full_track_analysis', PARENT/'reconcile_completed.py')
    runtime = module('frozen_refinement_runtime', HERE/'grid_runtime.py')
    # Queue policies differ, but the independent scientific checker is identical.
    assert inspect.getsource(runtime.check) == inspect.getsource(engine.grid_runtime.check)
    engine.grid_runtime = runtime
    design = json.loads((HERE/'design.json').read_text())
    rows = {r['case']:r for r in csv.DictReader((HERE/'manifest.csv').open())}
    context = dict(campaign=HERE.name, parent_analysis_sha256=sha(PARENT/'reconcile_completed.py'),
        wrapper_sha256=sha(Path(__file__)), frozen_runtime_sha256=sha(HERE/'grid_runtime.py'),
        manifest_sha256=sha(HERE/'manifest.csv'), design_sha256=sha(HERE/'design.json'),
        checker_identical_to_parent=True)
    results = []
    for case in sorted(args.host_result_root.resolve().glob('m*_n*_pk*')):
        results.append(engine.reconcile(case, rows[case.name], design))
        engine.write_json(case/'independent_validation/campaign_validation_context.json', context)
        print(case.name, 'independent gates and diagnostics PASS', flush=True)
    engine.write_json(args.host_result_root/'reconciliation_summary.json', results)
    print(json.dumps(dict(cases=len(results), status='PASS', density_pngs=sum(r['density_pngs'] for r in results))))


if __name__ == '__main__':
    main()
