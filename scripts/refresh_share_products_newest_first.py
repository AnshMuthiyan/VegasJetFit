#!/usr/bin/env python3
"""Refresh Share_Folder postfit products newest-first, preserving old products in trash."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHARE_FITS = Path('/Users/jkeohane/GRBs/Share_Folder/Fits')
PYTHON = Path('/Users/jkeohane/GRBs/.venv/bin/python')
POSTFIT = PROJECT_ROOT / 'scripts' / 'generate_postfit_products.py'

PRODUCT_NAMES = {
    'ampy_comparison.csv', 'ampy_comparison.pdf', 'ampy_comparison.png',
    'ampy_comparison_missing_reference.md',
    'ampy_comparison_symmetric.pdf', 'ampy_comparison_symmetric.png',
    'ampy_comparison_log_ratio.pdf', 'ampy_comparison_log_ratio.png',
    'corner_prior.pdf', 'corner_prior.png', 'corner.pdf', 'corner.png',
    'corner_core.pdf', 'corner_csm.pdf', 'corner_energy.pdf', 'corner_jet_mass.pdf',
    'corner_np.pdf', 'corner_host.pdf',
    'frequencies.pdf',
    'gamma_jetbreak_crossings.csv', 'gamma_jetbreak_two_panel.pdf', 'gamma_jetbreak_two_panel.png',
    'index_dist.pdf', 'k_profile.pdf', 'n0_profile.pdf', 'n_profile.pdf',
    'jet_energy_posterior.npz', 'jet_energy_summary.csv',
    'light_curve.pdf', 'light_curve.png', 'light_curve_two_panel.pdf', 'light_curve_two_panel.png',
    'light_curve_spread_out_100_walkers.pdf', 'light_curve_spread_out_100_walkers.png',
    'light_curve_spread_out_factors.csv', 'light_curve_spread_out_shaded_posterior.pdf',
    'light_curve_spread_out_shaded_posterior.png', 'light_curve_spread_out_spread_metadata.json',
    # Obsolete, but kept here so refreshes move old copies to trash before
    # regenerating the current swept-mass/Gamma diagnostics.
    'mass_profile.csv', 'mass_profile.pdf', 'mass_profile.png',
    'mass_swept_ejecta_crossings.csv', 'mass_swept_ejecta_radius.pdf', 'mass_swept_ejecta_radius.png',
    'mass_swept_ejecta_time.pdf', 'mass_swept_ejecta_time.png',
    'mass_swept_ejecta_two_panel.pdf', 'mass_swept_ejecta_two_panel.png',
    'spectral_breaks_eats_weighted.csv', 'spectral_plot.pdf', 'spectral_plot.png',
    'spectral_plot_legacy_before_eats_weighted.pdf', 'spectrum_timeseries.pdf',
    'summary.csv', 'trace.pdf', 'trace.png',
}
PRODUCT_PREFIXES = (
    'trace_', 'index_dist_',
)
FIT_TIME_NAMES = (
    'chain.npz', 'best_fit.json', 'run.log', 'pt_resume_state.npz',
)


def is_run_dir(path: Path) -> bool:
    return (path / 'chain.npz').exists() and (path / 'model.toml').exists()


def iter_run_dirs(root: Path):
    for chain in root.rglob('chain.npz'):
        if 'trash' in chain.parts:
            continue
        run_dir = chain.parent
        if is_run_dir(run_dir):
            yield run_dir


def newest_relevant_mtime(run_dir: Path) -> float:
    times = []
    for name in FIT_TIME_NAMES:
        path = run_dir / name
        if path.exists():
            times.append(path.stat().st_mtime)
    minimized = run_dir / 'minimized' / 'minimized.json'
    if minimized.exists():
        times.append(minimized.stat().st_mtime)
    return max(times) if times else run_dir.stat().st_mtime


def product_paths(run_dir: Path) -> list[Path]:
    out = []
    for child in run_dir.iterdir():
        if child.is_dir():
            continue
        if child.name in PRODUCT_NAMES or any(child.name.startswith(prefix) for prefix in PRODUCT_PREFIXES):
            out.append(child)
    return sorted(out)


def move_products_to_trash(run_dir: Path, batch_name: str) -> int:
    products = product_paths(run_dir)
    if not products:
        (run_dir / 'trash').mkdir(exist_ok=True)
        return 0
    trash_dir = run_dir / 'trash' / batch_name
    trash_dir.mkdir(parents=True, exist_ok=True)
    for src in products:
        dst = trash_dir / src.name
        if dst.exists():
            stem = dst.stem
            suffix = dst.suffix
            i = 1
            while True:
                candidate = trash_dir / f'{stem}_{i}{suffix}'
                if not candidate.exists():
                    dst = candidate
                    break
                i += 1
        shutil.move(str(src), str(dst))
    return len(products)


def run_postfit(run_dir: Path, log_dir: Path) -> int:
    env = os.environ.copy()
    env['PYTHONPATH'] = f'{PROJECT_ROOT}:{env.get("PYTHONPATH", "")}'
    log_path = log_dir / f'{int(time.time())}_{run_dir.name}_postfit.log'
    cmd = [str(PYTHON), str(POSTFIT), '--results', str(run_dir)]
    with log_path.open('w') as log:
        log.write('COMMAND: ' + ' '.join(cmd) + '\n')
        log.write(f'RUN_DIR: {run_dir}\n\n')
        log.flush()
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=SHARE_FITS)
    parser.add_argument('--limit', type=int, default=None, help='Refresh only the first N newest runs.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--continue-on-failure', action='store_true', default=True)
    args = parser.parse_args()

    batch_name = time.strftime('products_refresh_%Y%m%dT%H%M%S')
    log_dir = PROJECT_ROOT / 'scripts' / 'runtime_logs' / batch_name
    log_dir.mkdir(parents=True, exist_ok=True)

    runs = sorted(set(iter_run_dirs(args.root)), key=newest_relevant_mtime, reverse=True)
    if args.limit is not None:
        runs = runs[:args.limit]

    manifest = log_dir / 'ordered_runs.tsv'
    with manifest.open('w') as handle:
        handle.write('rank\tmtime\trun_dir\n')
        for i, run_dir in enumerate(runs, 1):
            handle.write(f'{i}\t{newest_relevant_mtime(run_dir):.0f}\t{run_dir}\n')

    print(f'batch={batch_name}', flush=True)
    print(f'run_count={len(runs)}', flush=True)
    print(f'manifest={manifest}', flush=True)

    failures = []
    for i, run_dir in enumerate(runs, 1):
        print(f'[{i}/{len(runs)}] START {run_dir}', flush=True)
        if args.dry_run:
            print(f'[{i}/{len(runs)}] DRY products={len(product_paths(run_dir))}', flush=True)
            continue
        moved = move_products_to_trash(run_dir, batch_name)
        print(f'[{i}/{len(runs)}] moved_products={moved}', flush=True)
        code = run_postfit(run_dir, log_dir)
        status = 'OK' if code == 0 else f'FAIL code={code}'
        print(f'[{i}/{len(runs)}] {status} {run_dir}', flush=True)
        if code != 0:
            failures.append((run_dir, code))
            if not args.continue_on_failure:
                break

    failure_path = log_dir / 'failures.tsv'
    with failure_path.open('w') as handle:
        handle.write('code\trun_dir\n')
        for run_dir, code in failures:
            handle.write(f'{code}\t{run_dir}\n')
    print(f'SUMMARY ok={len(runs)-len(failures)} failed={len(failures)} total={len(runs)}', flush=True)
    print(f'failures={failure_path}', flush=True)
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
