#!/usr/bin/env python3
"""Plot campaign-level histograms of core jet posterior quantities."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np


QUANTITIES = {
    "mass": {
        "array_key": "M_j_core_msun",
        "output_stem": "jet_mass_posterior_histogram",
        "value_name": "core_mass",
        "unit_name": "msun",
        "xlabel": r"$\log_{10}(M_{j,\mathrm{core}}/M_\odot)$",
        "title": "Two-Sided Core Jet-Mass Posterior Distributions",
        "note": (
            r"$M_{j,\mathrm{core}}=2\int_0^{\theta_c}"
            r"[(dE/d\Omega)/(\Gamma_0(\theta)c^2)]\,d\Omega$"
        ),
    },
    "energy": {
        "array_key": "E_j_core_52",
        "output_stem": "jet_core_energy_posterior_histogram",
        "value_name": "core_energy",
        "unit_name": "e52",
        "xlabel": r"$\log_{10}(E_{j,\mathrm{core}}/10^{52}\,\mathrm{erg})$",
        "title": "Two-Sided Core Jet-Energy Posterior Distributions",
        "note": (
            r"$E_{j,\mathrm{core}}=2\int_0^{\theta_c}"
            r"(dE/d\Omega)\,d\Omega$"
        ),
    },
    "gamma": {
        "array_key": "Gamma_0_core_avg",
        "output_stem": "gamma0_core_average_posterior_histogram",
        "value_name": "gamma0_core_average",
        "unit_name": "dimensionless",
        "xlabel": r"$\log_{10}\langle\Gamma_0\rangle_{\mathrm{core}}$",
        "title": "Core-Averaged Initial Lorentz-Factor Posterior Distributions",
        "note": (
            r"$\langle\Gamma_0\rangle_{\mathrm{core}}="
            r"\int_0^{\theta_c}\Gamma_0(\theta)\sin\theta\,d\theta/"
            r"(1-\cos\theta_c)$"
        ),
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--bins", type=int, default=64)
    parser.add_argument("--quantity", choices=sorted(QUANTITIES), default="mass")
    parser.add_argument("--output-stem")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    campaign = args.campaign.expanduser().resolve()
    quantity = QUANTITIES[args.quantity]
    output_stem = args.output_stem or quantity["output_stem"]
    runs = sorted(
        path for path in campaign.iterdir()
        if path.is_dir() and path.name != "trash"
        and (path / "jet_energy_posterior.npz").is_file()
    )
    if not runs:
        raise SystemExit(f"No jet_energy_posterior.npz files found under {campaign}")

    samples: dict[str, np.ndarray] = {}
    summary_rows: list[dict[str, float | int | str]] = []
    for run in runs:
        with np.load(run / "jet_energy_posterior.npz") as data:
            values = np.asarray(data[quantity["array_key"]], dtype=float)
        values = values[np.isfinite(values) & (values > 0.0)]
        if values.size == 0:
            continue
        log_values = np.log10(values)
        samples[run.name] = log_values
        q16, q50, q84 = np.quantile(values, [0.16, 0.5, 0.84])
        value_name = quantity["value_name"]
        unit_name = quantity["unit_name"]
        summary_rows.append(
            {
                "event": run.name,
                "n_samples": int(values.size),
                f"{value_name}_median_{unit_name}": float(q50),
                f"{value_name}_q16_{unit_name}": float(q16),
                f"{value_name}_q84_{unit_name}": float(q84),
                f"{value_name}_median_log10": float(np.log10(q50)),
            }
        )

    if not samples:
        raise SystemExit(
            f"No finite positive {quantity['array_key']} samples found under {campaign}"
        )

    all_log_values = np.concatenate(list(samples.values()))
    lo, hi = np.quantile(all_log_values, [0.0005, 0.9995])
    pad = 0.04 * (hi - lo)
    edges = np.linspace(lo - pad, hi + pad, args.bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])

    colors = plt.get_cmap("turbo")(np.linspace(0.03, 0.97, len(samples)))
    fig, ax = plt.subplots(figsize=(11.2, 6.5))
    histogram_rows: list[dict[str, float | str]] = []
    for (event, values), color in zip(samples.items(), colors):
        density, _ = np.histogram(values, bins=edges, density=True)
        ax.stairs(density, edges, color=color, lw=1.7, label=f"GRB {event}")
        median = float(np.median(values))
        ax.axvline(median, color=color, lw=0.9, alpha=0.72)
        for center, value in zip(centers, density):
            histogram_rows.append(
                {
                    "event": event,
                    f"log10_{quantity['value_name']}_bin_center": float(center),
                    "density": float(value),
                }
            )

    ax.set_xlabel(quantity["xlabel"], fontsize=13)
    ax.set_ylabel("Posterior probability density", fontsize=13)
    ax.set_title(quantity["title"], fontsize=15, pad=10)
    ax.grid(axis="y", alpha=0.22)
    ax.tick_params(labelsize=11)
    ax.legend(
        ncol=3,
        fontsize=9,
        loc="upper left",
        frameon=True,
        columnspacing=1.2,
        handlelength=2.2,
    )
    fig.text(
        0.995,
        0.008,
        quantity["note"],
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))

    stem = campaign / output_stem
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    with (campaign / f"{output_stem}_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)
    with (campaign / f"{output_stem}_data.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=histogram_rows[0].keys())
        writer.writeheader()
        writer.writerows(histogram_rows)

    print(f"Wrote {stem.with_suffix('.pdf')}")
    print(f"Wrote {stem.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
