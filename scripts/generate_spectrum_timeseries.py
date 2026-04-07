#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from jetfit.ampy import Ampy
from scripts.plot import visualize


def _load_plot_params(results_dir: Path) -> dict:
    minimized = results_dir / "minimized" / "minimized.json"
    if minimized.exists():
        payload = json.loads(minimized.read_text())
        params = payload.get("params")
        if isinstance(params, dict) and isinstance(params.get("model"), dict):
            return params

    best_fit = results_dir / "best_fit.json"
    if best_fit.exists():
        payload = json.loads(best_fit.read_text())
        if isinstance(payload, dict) and isinstance(payload.get("model"), dict):
            return payload

    raise FileNotFoundError(
        f"Could not find usable minimized/best-fit parameters in {results_dir}"
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Generate spectrum_timeseries.pdf for a results directory.")
    parser.add_argument("--results", required=True, help="Results directory containing model.toml, obs.csv, and best_fit/minimized output.")
    parser.add_argument("--output", default=None, help="Optional explicit PDF output path. Defaults to <results>/spectrum_timeseries.pdf")
    parser.add_argument("--ncurves", type=int, default=10, help="Number of time slices to plot.")
    parser.add_argument("--nfreq", type=int, default=400, help="Number of frequency samples per spectrum.")
    return parser.parse_args()


def main():
    args = parse_args()
    results_dir = Path(args.results).expanduser().resolve()
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    obs_path = results_dir / "obs.csv"
    params_path = results_dir / "model.toml"
    if not obs_path.exists():
        raise FileNotFoundError(f"Observation CSV not found: {obs_path}")
    if not params_path.exists():
        raise FileNotFoundError(f"Model TOML not found: {params_path}")

    event = results_dir.name.split("_")[0]
    os.environ.setdefault("JETFIT_PLOT_RUN_LABEL", f"GRB {event} | {results_dir.name}")

    ampy = Ampy(obs_path, params_path)
    params = _load_plot_params(results_dir)
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output is not None
        else results_dir / "spectrum_timeseries.pdf"
    )

    visualize.plot_spectrum_timeseries_ampy(
        ampy,
        params=params,
        output_path=output_path,
        ncurves=args.ncurves,
        nfreq=args.nfreq,
    )
    print(output_path)


if __name__ == "__main__":
    main()
