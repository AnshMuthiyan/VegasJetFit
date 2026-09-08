#!/usr/bin/env python3
"""Compare per-walker observed-shell mass and mean number-density posteriors."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--bins", default=56, type=int)
    return parser.parse_args()


def read_samples(path: Path, column: str) -> np.ndarray:
    with path.open(newline="", encoding="utf-8") as handle:
        values = np.asarray([float(row[column]) for row in csv.DictReader(handle)], dtype=float)
    return np.log10(values[np.isfinite(values) & (values > 0.0)])


def edges_for(samples: dict[str, np.ndarray], bins: int) -> np.ndarray:
    values = np.concatenate(list(samples.values()))
    lo, hi = np.quantile(values, [0.0005, 0.9995])
    span = max(float(hi - lo), 0.2)
    return np.linspace(lo - 0.04 * span, hi + 0.04 * span, bins + 1)


def main() -> int:
    args = parse_args()
    campaign = args.campaign.expanduser().resolve()
    runs = sorted(path for path in campaign.iterdir() if path.is_dir() and (path / "density_shell_mass_walkers.csv").is_file())
    mass: dict[str, np.ndarray] = {}
    density: dict[str, np.ndarray] = {}
    summary: list[dict[str, float | int | str]] = []
    for run in runs:
        source = run / "density_shell_mass_walkers.csv"
        try:
            log_mass = read_samples(source, "shell_mass_msun")
            log_density = read_samples(source, "mean_number_density_cm3")
        except (KeyError, OSError, ValueError):
            continue
        count = min(log_mass.size, log_density.size)
        if count == 0:
            continue
        mass[run.name] = log_mass
        density[run.name] = log_density
        summary.append({
            "event": run.name,
            "walker_count": int(count),
            "shell_mass_msun_q16": float(np.quantile(10.0 ** log_mass, 0.16)),
            "shell_mass_msun_median": float(np.median(10.0 ** log_mass)),
            "shell_mass_msun_q84": float(np.quantile(10.0 ** log_mass, 0.84)),
            "mean_number_density_cm3_q16": float(np.quantile(10.0 ** log_density, 0.16)),
            "mean_number_density_cm3_median": float(np.median(10.0 ** log_density)),
            "mean_number_density_cm3_q84": float(np.quantile(10.0 ** log_density, 0.84)),
        })
    if not mass:
        raise SystemExit(f"No usable density_shell_mass_walkers.csv products in {campaign}")

    mass_edges = edges_for(mass, args.bins)
    density_edges = edges_for(density, args.bins)
    colors = plt.get_cmap("turbo")(np.linspace(0.03, 0.97, len(mass)))
    fig, axes = plt.subplots(2, 1, figsize=(11.0, 8.2), constrained_layout=True)
    data_rows: list[dict[str, float | str]] = []
    for (event, values), color in zip(mass.items(), colors, strict=True):
        hist, _ = np.histogram(values, bins=mass_edges, density=True)
        axes[0].stairs(hist, mass_edges, color=color, lw=1.6, label=f"GRB {event}")
        axes[0].axvline(np.median(values), color=color, lw=0.8, alpha=0.65)
        data_rows.extend({"event": event, "quantity": "shell_mass_msun", "log10_bin_center": float(center), "posterior_density": float(value)} for center, value in zip(0.5 * (mass_edges[:-1] + mass_edges[1:]), hist, strict=True))
    for (event, values), color in zip(density.items(), colors, strict=True):
        hist, _ = np.histogram(values, bins=density_edges, density=True)
        axes[1].stairs(hist, density_edges, color=color, lw=1.6)
        axes[1].axvline(np.median(values), color=color, lw=0.8, alpha=0.65)
        data_rows.extend({"event": event, "quantity": "mean_number_density_cm3", "log10_bin_center": float(center), "posterior_density": float(value)} for center, value in zip(0.5 * (density_edges[:-1] + density_edges[1:]), hist, strict=True))
    axes[0].set_xlabel(r"$\log_{10}(M_{\rm shell}/M_\odot)$")
    axes[0].set_ylabel("Posterior density")
    axes[0].set_title("Observed-shell mass posterior")
    axes[1].set_xlabel(r"$\log_{10}\langle n_{\rm H}\rangle$ [atoms cm$^{-3}$]")
    axes[1].set_ylabel("Posterior density")
    axes[1].set_title("Observed-shell mean hydrogen number-density posterior")
    for axis in axes:
        axis.grid(axis="y", alpha=0.25)
    axes[0].legend(ncol=3, fontsize=8, loc="best")
    fig.suptitle("Observed Density-Shell Posterior Comparison", fontsize=15)

    output = campaign / "histograms"
    output.mkdir(parents=True, exist_ok=True)
    stem = output / "density_shell_mass_density_comparison_histograms"
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    with stem.with_name(stem.name + "_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)
    with stem.with_name(stem.name + "_data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=data_rows[0].keys())
        writer.writeheader()
        writer.writerows(data_rows)
    print(f"Wrote {stem.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
