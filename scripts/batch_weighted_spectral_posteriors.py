#!/usr/bin/env python3
"""Retired batch helper for Dylan-style weighted spectral plots.

The standard pipeline should use ``frequencies.pdf`` and should not regenerate
``spectral_plot.pdf`` or ``spectral_plot.png``. This script now requires an
explicit opt-in flag before writing those retired products.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.ampy import Ampy
from scripts.generate_postfit_products import display_run_label, infer_event
from scripts.plot.visualize import FrequencyPlotter


def _load_postfit_params(run_dir: Path) -> tuple[dict[str, Any], str]:
    minimized = run_dir / "minimized" / "minimized.json"
    if minimized.exists():
        payload = json.loads(minimized.read_text())
        params = payload.get("params", payload)
        if isinstance(params, dict) and isinstance(params.get("model"), dict):
            return params, "minimized/minimized.json"
    best = run_dir / "best_fit.json"
    if best.exists():
        params = json.loads(best.read_text())
        if isinstance(params, dict) and isinstance(params.get("model"), dict):
            return params, "best_fit.json"
    raise FileNotFoundError("missing minimized/minimized.json and best_fit.json")


def _read_model_name(model_toml: Path) -> str:
    with model_toml.open("rb") as handle:
        payload = tomllib.load(handle)
    name = payload.get("name")
    if not name:
        raise ValueError(f"missing model name in {model_toml}")
    return str(name)


def _spectral_model_kw(model_name: str) -> dict[str, Any]:
    """Force the canonical EATS-weighted break path where the model supports it."""
    if model_name in {
        "powerlawVegasDylanSpectrumModel",
        "PowerlawJetVegasDylanSpectrumModel",
    }:
        return {"break_frequency_mode": "eats_weighted"}
    return {}


def _flatten_chain(chain: np.ndarray, lnprob: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    c = np.asarray(chain)
    lp = np.asarray(lnprob)
    if c.ndim == 4:
        c = c[:, 0, :, :]
    if lp.ndim == 3:
        lp = lp[:, 0, :]
    flat_chain = c.reshape((-1, c.shape[-1]))
    flat_lnprob = lp.reshape((-1,))
    return flat_chain, flat_lnprob


def _plot_one(run_dir: Path, nsamps: int) -> None:
    obs_csv = run_dir / "obs.csv"
    model_toml = run_dir / "model.toml"
    chain_npz = run_dir / "chain.npz"

    if not (obs_csv.exists() and model_toml.exists() and chain_npz.exists()):
        raise FileNotFoundError("missing one of obs.csv/model.toml/chain.npz")

    event = infer_event(run_dir, None)
    params, source = _load_postfit_params(run_dir)
    if "model" not in params:
        raise ValueError("postfit params missing model section")
    model_name = _read_model_name(model_toml)
    model_kw = _spectral_model_kw(model_name)

    os.environ["JETFIT_PLOT_EVENT_TITLE"] = f"GRB {event}"
    os.environ["JETFIT_PLOT_RUN_LABEL"] = (
        f"GRB {event} | {display_run_label(run_dir, event)} | {source}"
    )

    ampy = Ampy(str(obs_csv), str(model_toml), model_kw=model_kw)
    with np.load(chain_npz) as data:
        flat_chain, flat_lnprob = _flatten_chain(data["chain"], data["lnprob"])

    fp = FrequencyPlotter(
        flat_chain,
        flat_lnprob,
        ampy.mcmc.params,
        ampy.mcmc.models.afg_model,
        ampy.mcmc.models.afg_kw,
    )

    epoch = ampy.obs.epoch(mask=ampy.obs.flux_loc)
    times = np.geomspace(epoch.min() / 2.0, epoch.max() * 2.0, num=200)

    # Posterior distribution overlay + best curve + observed data.
    fp.plot_dist(times, best=params, nsamps=nsamps)
    fp.plot_data(ampy.obs)
    fp.plot_indices(ampy.obs, best=params, times=times)
    fp.axes[1].set_xlim(times.min(), times.max())

    out_pdf = run_dir / "spectral_plot.pdf"
    out_png = run_dir / "spectral_plot.png"
    fp.fig.savefig(out_pdf)
    fp.fig.savefig(out_png, dpi=220)
    plt.close(fp.fig)


def _plot_one_report(run_dir: Path, nsamps: int) -> dict[str, str]:
    try:
        _plot_one(run_dir, nsamps=nsamps)
        return {"run_dir": str(run_dir), "status": "ok"}
    except Exception as exc:
        return {"run_dir": str(run_dir), "status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def _iter_run_dirs(root: Path, include_text: str | None) -> list[Path]:
    runs: list[Path] = []
    for model_toml in root.rglob("model.toml"):
        run_dir = model_toml.parent
        if include_text and include_text not in str(run_dir):
            continue
        runs.append(run_dir)
    return sorted(set(runs))


def _ok_dirs_from_log(log_path: Path) -> set[str]:
    if not log_path.exists():
        return set()

    ok: set[str] = set()
    current: str | None = None
    for line in log_path.read_text(errors="ignore").splitlines():
        if line.startswith("[") and "/VegasGRBruns/Fits/" in line:
            current = line.split("] ", 1)[1]
        elif "status=ok" in line and current:
            ok.add(str(Path(current).resolve()))
            current = None
        elif "status=failed" in line:
            current = None
    return ok


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--fits-root",
        type=Path,
        default=Path(
            "/Users/jkeohane/Library/CloudStorage/GoogleDrive-jwkeohane@gmail.com/.shortcut-targets-by-id/1d7HnZ0yxuhMv2vPzbGBL9NNSDX9BjeDp/VegasGRBruns/Fits"
        ),
    )
    p.add_argument(
        "--include",
        default="spectrum_dylan_smoothed",
        help="Only process run directories whose absolute path contains this string (empty to disable).",
    )
    p.add_argument("--nsamps", type=int, default=70, help="Posterior samples per run for cloud overlays.")
    p.add_argument("--workers", type=int, default=1, help="Number of run directories to process in parallel.")
    p.add_argument("--limit", type=int, default=0, help="Optional cap on number of runs (0=all).")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--write-retired-products",
        action="store_true",
        help=(
            "Actually write retired spectral_plot.pdf/.png products. Standard "
            "pipelines should not pass this flag; use frequencies.pdf instead."
        ),
    )
    p.add_argument(
        "--skip-ok-log",
        type=Path,
        default=None,
        help="Skip run directories that already have status=ok in a previous batch log.",
    )
    p.add_argument(
        "--log-json",
        type=Path,
        default=None,
        help="Optional JSON report path for success/failure summary.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.write_retired_products:
        print(
            "SKIP: spectral_plot.pdf and spectral_plot.png are retired "
            "standard products. Use frequencies.pdf instead. Pass "
            "--write-retired-products only for an explicit one-off diagnostic."
        )
        return 0

    root = args.fits_root.expanduser().resolve()
    include_text = args.include or None

    run_dirs = _iter_run_dirs(root, include_text)
    run_dirs = [r for r in run_dirs if (r / "chain.npz").exists()]
    if args.skip_ok_log:
        ok_dirs = _ok_dirs_from_log(args.skip_ok_log.expanduser().resolve())
        run_dirs = [r for r in run_dirs if str(r.resolve()) not in ok_dirs]
    if args.limit > 0:
        run_dirs = run_dirs[: args.limit]

    results: dict[str, list[dict[str, str]]] = {"ok": [], "failed": []}
    workers = max(1, int(args.workers))
    print(f"found_runs={len(run_dirs)} nsamps={args.nsamps} workers={workers} include={include_text!r}")

    if args.dry_run:
        for i, run_dir in enumerate(run_dirs, start=1):
            print(f"[{i}/{len(run_dirs)}] {run_dir}")
    elif workers == 1:
        for i, run_dir in enumerate(run_dirs, start=1):
            print(f"[{i}/{len(run_dirs)}] {run_dir}", flush=True)
            row = _plot_one_report(run_dir, args.nsamps)
            results[row["status"]].append(row)
            if row["status"] == "ok":
                print("  status=ok", flush=True)
            else:
                print(f"  status=failed error={row['error']}", flush=True)
    else:
        future_to_index = {}
        with ProcessPoolExecutor(max_workers=min(workers, len(run_dirs) or 1)) as pool:
            for i, run_dir in enumerate(run_dirs, start=1):
                print(f"[{i}/{len(run_dirs)}] queued {run_dir}", flush=True)
                future = pool.submit(_plot_one_report, run_dir, args.nsamps)
                future_to_index[future] = i
            for future in as_completed(future_to_index):
                row = future.result()
                results[row["status"]].append(row)
                prefix = f"[done {len(results['ok']) + len(results['failed'])}/{len(run_dirs)}]"
                if row["status"] == "ok":
                    print(f"{prefix} status=ok {row['run_dir']}", flush=True)
                else:
                    print(f"{prefix} status=failed error={row['error']} {row['run_dir']}", flush=True)

    print(f"done ok={len(results['ok'])} failed={len(results['failed'])}")
    if args.log_json:
        args.log_json.parent.mkdir(parents=True, exist_ok=True)
        args.log_json.write_text(json.dumps(results, indent=2))
        print(f"wrote_log={args.log_json}")
    return 0 if not results["failed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
