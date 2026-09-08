#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from jetfit.ampy import model_factory


def _load_model_name(model_toml: Path) -> str:
    data = tomllib.loads(model_toml.read_text())
    model_name = data.get("name")
    if not model_name:
        raise ValueError(f"Missing top-level model name in {model_toml}")
    return str(model_name)


def _load_best_model_kwargs(run_dir: Path) -> dict:
    best = json.loads((run_dir / "best_fit.json").read_text())
    kwargs = dict(best.get("model", {}))
    if not kwargs:
        raise ValueError(f"Missing model best-fit parameters in {run_dir / 'best_fit.json'}")
    return kwargs


def _load_times_days(run_dir: Path, ngrid: int) -> np.ndarray:
    obs_csv = run_dir / "obs.csv"
    if obs_csv.exists():
        obs = np.genfromtxt(obs_csv, delimiter=",", names=True, dtype=None, encoding=None)
        if "time" in obs.dtype.names:
            times = np.asarray(obs["time"], dtype=float)
            times = times[np.isfinite(times) & (times > 0.0)]
            if times.size > 2:
                tmin = float(np.nanmin(times))
                tmax = float(np.nanmax(times))
                if tmax > tmin:
                    return np.logspace(math.log10(tmin), math.log10(tmax), ngrid)
    # Safe fallback window for GRB fitting products
    return np.logspace(-2.0, 3.0, ngrid)


def _eval_mode(model_name: str, kwargs: dict, times: np.ndarray, mode: str) -> dict[str, np.ndarray]:
    model_cls = model_factory(model_name)
    kw = dict(kwargs)
    kw["break_frequency_mode"] = mode
    model = model_cls(**kw)
    return {
        "nu_a": np.asarray(model.nu_a(times), dtype=float),
        "nu_m": np.asarray(model.nu_m(times), dtype=float),
        "nu_c": np.asarray(model.nu_c(times), dtype=float),
    }


def _safe_ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    out = np.full_like(num, np.nan, dtype=float)
    m = np.isfinite(num) & np.isfinite(den) & (num > 0.0) & (den > 0.0)
    out[m] = num[m] / den[m]
    return out


def make_plot(run_dir: Path, ngrid: int = 240) -> tuple[Path, Path, Path]:
    model_toml = run_dir / "model.toml"
    if not model_toml.exists():
        raise FileNotFoundError(f"Missing model.toml in {run_dir}")

    model_name = _load_model_name(model_toml)
    kwargs = _load_best_model_kwargs(run_dir)
    times = _load_times_days(run_dir, ngrid)

    local = _eval_mode(model_name, kwargs, times, "local_trace")
    eats = _eval_mode(model_name, kwargs, times, "eats_weighted")

    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(9.5, 8.0), sharex=True, gridspec_kw={"height_ratios": [3.0, 1.2]}
    )

    styles = {"local_trace": ("--", 0.95), "eats_weighted": ("-", 0.95)}
    colors = {"nu_a": "tab:green", "nu_m": "tab:blue", "nu_c": "tab:orange"}

    for key in ("nu_a", "nu_m", "nu_c"):
        ax.loglog(times, local[key], styles["local_trace"][0], color=colors[key], alpha=styles["local_trace"][1], label=f"{key} local_trace")
        ax.loglog(times, eats[key], styles["eats_weighted"][0], color=colors[key], alpha=styles["eats_weighted"][1], label=f"{key} eats_weighted")

    ax.set_ylabel("Break Frequency (Hz)")
    ax.set_title(f"{run_dir.name} spectral breaks: local_trace vs eats_weighted")
    ax.grid(True, which="both", alpha=0.2)
    ax.legend(ncol=2, fontsize=9)

    for key in ("nu_a", "nu_m", "nu_c"):
        ratio = _safe_ratio(eats[key], local[key])
        axr.semilogx(times, ratio, color=colors[key], lw=1.8, label=f"{key} ratio")
    axr.axhline(1.0, color="k", lw=1.0, alpha=0.6)
    axr.set_ylabel("weighted/local")
    axr.set_xlabel("Observer Time (days)")
    axr.set_yscale("log")
    axr.grid(True, which="both", alpha=0.2)
    axr.legend(ncol=3, fontsize=9)

    out_png = run_dir / "spectral_break_mode_comparison.png"
    out_pdf = run_dir / "spectral_break_mode_comparison.pdf"
    out_csv = run_dir / "spectral_break_mode_comparison.csv"

    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    fig.savefig(out_pdf)
    plt.close(fig)

    table = np.column_stack(
        [
            times,
            local["nu_a"],
            local["nu_m"],
            local["nu_c"],
            eats["nu_a"],
            eats["nu_m"],
            eats["nu_c"],
            _safe_ratio(eats["nu_a"], local["nu_a"]),
            _safe_ratio(eats["nu_m"], local["nu_m"]),
            _safe_ratio(eats["nu_c"], local["nu_c"]),
        ]
    )
    header = (
        "time_days,nu_a_local,nu_m_local,nu_c_local,"
        "nu_a_eats,nu_m_eats,nu_c_eats,"
        "ratio_nu_a,ratio_nu_m,ratio_nu_c"
    )
    np.savetxt(out_csv, table, delimiter=",", header=header, comments="")
    return out_png, out_pdf, out_csv


def main() -> None:
    p = argparse.ArgumentParser(description="Compare break-frequency modes for a run directory.")
    p.add_argument("run_dir", type=Path, help="Run directory containing model.toml and obs.csv")
    p.add_argument("--ngrid", type=int, default=240)
    args = p.parse_args()

    png, pdf, csv = make_plot(args.run_dir, args.ngrid)
    print(f"Wrote: {png}")
    print(f"Wrote: {pdf}")
    print(f"Wrote: {csv}")


if __name__ == "__main__":
    main()
