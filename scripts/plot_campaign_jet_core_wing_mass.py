#!/usr/bin/env python3
"""Summarize core and wing contributions to structured-jet mass."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    args = parser.parse_args()
    campaign = args.campaign.expanduser().resolve()

    rows = []
    for run in sorted(path for path in campaign.iterdir() if path.is_dir() and path.name != "trash"):
        path = run / "jet_energy_posterior.npz"
        if not path.is_file():
            continue
        with np.load(path) as data:
            total = np.asarray(data["M_j_msun"], dtype=float)
            core = np.asarray(data["M_j_core_msun"], dtype=float)
            wings = np.asarray(data["M_j_wings_msun"], dtype=float)
            fraction = np.asarray(data["M_j_core_fraction"], dtype=float)
            energy_fraction = np.asarray(data["E_j_core_fraction"], dtype=float)
        good = (
            np.isfinite(total) & (total > 0)
            & np.isfinite(core) & (core >= 0)
            & np.isfinite(wings) & (wings >= 0)
            & np.isfinite(fraction)
            & np.isfinite(energy_fraction)
        )
        total, core, wings = total[good], core[good], wings[good]
        fraction, energy_fraction = fraction[good], energy_fraction[good]
        fq16, fq50, fq84 = np.quantile(fraction, [0.16, 0.5, 0.84])
        eq16, eq50, eq84 = np.quantile(energy_fraction, [0.16, 0.5, 0.84])
        rows.append(
            {
                "event": run.name,
                "n_samples": int(total.size),
                "total_mass_median_msun": float(np.median(total)),
                "core_mass_median_msun": float(np.median(core)),
                "wing_mass_median_msun": float(np.median(wings)),
                "core_fraction_q16": float(fq16),
                "core_fraction_median": float(fq50),
                "core_fraction_q84": float(fq84),
                "wing_fraction_median": float(1.0 - fq50),
                "core_energy_fraction_q16": float(eq16),
                "core_energy_fraction_median": float(eq50),
                "core_energy_fraction_q84": float(eq84),
                "mass_to_energy_core_fraction_ratio": float(fq50 / eq50),
                "median_total_over_core": float(np.median(total / np.clip(core, 1e-300, None))),
            }
        )

    rows.sort(key=lambda row: float(row["core_fraction_median"]))
    events = [str(row["event"]) for row in rows]
    median = np.asarray([row["core_fraction_median"] for row in rows], dtype=float)
    q16 = np.asarray([row["core_fraction_q16"] for row in rows], dtype=float)
    q84 = np.asarray([row["core_fraction_q84"] for row in rows], dtype=float)
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(9.2, 6.7))
    ax.barh(y, median, color="#146c94", alpha=0.88, label="core mass fraction")
    ax.barh(y, 1.0 - median, left=median, color="#e58f2a", alpha=0.76, label="wing mass fraction")
    ax.errorbar(
        median,
        y,
        xerr=np.vstack([median - q16, q84 - median]),
        fmt="none",
        ecolor="black",
        elinewidth=1.0,
        capsize=2.5,
        zorder=4,
    )
    ax.set_yticks(y, [f"GRB {event}" for event in events])
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel(r"Fraction of inferred $M_j$")
    ax.set_title(r"Core vs Wing Contribution to the Jet-Mass Proxy")
    ax.grid(axis="x", alpha=0.22)
    ax.legend(loc="lower right", frameon=True)
    for yi, value in zip(y, median):
        ax.text(
            max(0.015, value - 0.015),
            yi,
            f"{100.0 * value:.0f}%",
            ha="right" if value > 0.1 else "left",
            va="center",
            color="white" if value > 0.1 else "black",
            fontsize=8,
            fontweight="bold",
        )
    fig.text(
        0.995,
        0.008,
        r"core: $\theta\leq\theta_c$; wings: $\theta_c<\theta\leq\pi/2$",
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(campaign / "jet_mass_core_wing_fraction.pdf", bbox_inches="tight", pad_inches=0.04)
    fig.savefig(campaign / "jet_mass_core_wing_fraction.png", dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    with (campaign / "jet_mass_core_wing_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {campaign / 'jet_mass_core_wing_fraction.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
