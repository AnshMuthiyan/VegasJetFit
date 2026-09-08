#!/usr/bin/env python3
"""Safely regenerate 140506A-style frequencies.pdf for completed run dirs.

The existing frequencies.pdf remains in place until the new plot successfully
renders in a temporary output directory.
"""
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

from jetfit.ampy import Ampy
from scripts.generate_postfit_products import _load_chain_for_frequency_plot, load_postfit_params
from scripts.plot import visualize


def regenerate_one(run: Path, posterior_curves: int, time_samples: int) -> None:
    run = run.expanduser().resolve()
    params, source, _ = load_postfit_params(run)
    ampy = Ampy(run / 'obs.csv', run / 'model.toml')
    chain, log_prob = _load_chain_for_frequency_plot(run)

    tmp = run / f'.frequency_template_tmp_{int(time.time())}'
    tmp.mkdir(exist_ok=False)
    try:
        print(f'RENDER run={run} source={source}', flush=True)
        visualize.plot_frequencies(
            chain,
            log_prob,
            ampy.obs,
            ampy.mcmc.params,
            ampy.afterglow_model,
            model_kw=ampy.mcmc.models.afg_kw,
            best=params,
            out_dir=tmp,
            nsamps=posterior_curves,
            ntimes=time_samples,
            fast_indices=False,
        )
        new_pdf = tmp / 'frequencies.pdf'
        if not new_pdf.exists():
            raise FileNotFoundError(f'Expected output not written: {new_pdf}')
        batch = time.strftime('frequency_template_refresh_%Y%m%dT%H%M%S')
        trash = run / 'trash' / batch
        trash.mkdir(parents=True, exist_ok=True)
        old_pdf = run / 'frequencies.pdf'
        if old_pdf.exists():
            shutil.copy2(old_pdf, trash / 'frequencies.pdf')
        os.replace(new_pdf, old_pdf)
        print(f'DONE run={run} output={old_pdf}', flush=True)
    finally:
        for child in tmp.glob('*'):
            child.unlink()
        tmp.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--posterior-curves', type=int, default=100)
    parser.add_argument('--time-samples', type=int, default=200)
    args = parser.parse_args()
    for run in args.runs:
        regenerate_one(run, args.posterior_curves, args.time_samples)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
