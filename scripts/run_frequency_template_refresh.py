#!/usr/bin/env python3
"""Regenerate template-style frequencies.pdf for one or more run directories."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_postfit_products import load_postfit_params, regenerate_frequency_plot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--posterior-curves', type=int, default=100)
    parser.add_argument('--time-samples', type=int, default=200)
    args = parser.parse_args()

    os.environ['JETFIT_FREQUENCY_POSTERIOR_CURVES'] = str(args.posterior_curves)
    os.environ['JETFIT_FREQUENCY_TIME_SAMPLES'] = str(args.time_samples)
    os.environ.pop('JETFIT_FREQUENCY_FAST_INDICES', None)

    for raw_run in args.runs:
        run = raw_run.expanduser().resolve()
        if not run.exists():
            print(f'MISSING run={run}', flush=True)
            continue
        batch = time.strftime('frequency_template_refresh_%Y%m%dT%H%M%S')
        trash = run / 'trash' / batch
        trash.mkdir(parents=True, exist_ok=True)
        freq = run / 'frequencies.pdf'
        if freq.exists():
            shutil.copy2(freq, trash / 'frequencies.pdf')
        print(f'START run={run}', flush=True)
        params, source, _ = load_postfit_params(run)
        regenerate_frequency_plot(run, params, source)
        print(f'DONE run={run} output={freq}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
