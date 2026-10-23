#!/usr/bin/env python3
"""Plot the validated 0.001--10 pc shell-radius inventory for the meeting book."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bins_csv", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()

    with args.bins_csv.open(newline="", encoding="ascii") as stream:
        rows = list(csv.DictReader(stream))
    left = np.array([float(row["radius_lo_pc"]) for row in rows])
    right = np.array([float(row["radius_hi_pc"]) for row in rows])
    accepted = np.array([int(row["snapshot_count"]) for row in rows])
    resolved = np.array([int(row["ramp_resolved_count"]) for row in rows])
    center = np.sqrt(left * right)

    fig, ax = plt.subplots(figsize=(9, 3.8), constrained_layout=True)
    ax.axvspan(0.001, 0.0251188643, color="#f6e5e2", label="No accepted shell below 0.0251 pc")
    ax.bar(center, accepted, width=right - left, color="#356b79", alpha=0.85,
           label="Quality-gated snapshots")
    ax.bar(center, resolved, width=right - left, color="#d07143", alpha=0.95,
           label="Local 10--90% ramp >=5 cells")
    ax.axvline(0.001225, color="#333333", linestyle=":", linewidth=1.5)
    ax.axvline(0.719437, color="#333333", linestyle="--", linewidth=1.5)
    ax.text(0.001225 * 1.08, max(accepted) * 0.92, "analytic first radius",
            rotation=90, va="top", fontsize=8)
    ax.text(0.719437 * 1.08, max(accepted) * 0.92, "analytic last radius",
            rotation=90, va="top", fontsize=8)
    ax.set(xscale="log", xlim=(0.001, 10), ylim=(0, max(accepted) * 1.14),
           xlabel="Shell inner 10% radius (pc)", ylabel="Snapshot count",
           title="Quality-gated numerical shell-radius coverage")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    if args.output_png.exists():
        raise FileExistsError(args.output_png)
    fig.savefig(args.output_png, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
