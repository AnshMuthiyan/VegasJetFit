#!/usr/bin/env python3
"""Compare validated 0.1-Myr cloud-shape controls at fixed n_ref."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_cloud_mass_products import shell_measure
from validate_cloud_mass import MASS_PER_H, RHO_UNIT, profile_nh, validate
from validate_smoke import read_vtu


CASES = (
    ("baseline", "cloud_mass_wideedge_20261014/nref1000/wind",
     "cloudmass_nref1000_wind", 2.0, 0.5, 1.8),
    ("core1pcw05", "cloud_variants_20261014/core1pcw05/wind",
     "cloudmass_core1pcw05_nref1000_wind", 1.0, 0.5, 1.8),
    ("core3pc", "cloud_variants_20261014/core3pc/wind",
     "cloudmass_core3pc_nref1000_wind", 3.0, 0.75, 1.8),
    ("slope16", "cloud_variants_20261014/slope16/wind",
     "cloudmass_slope16_nref1000_wind", 2.0, 0.5, 1.6),
)


def make_products(results: Path, output: Path) -> None:
    rows = []
    profiles = []
    for label, subdir, prefix, cloud_pc, width, slope in CASES:
        root = results / subdir
        check = validate(root, prefix, 1000.0, 0.1, 6, False,
                         width, cloud_pc, slope)
        data = read_vtu(root / f"{prefix}0005.vtu")[1]
        shell = shell_measure(data, 1000.0, width, "wind", 40.0,
                              cloud_pc, slope)
        rows.append({"variant": label, **check, **shell})
        profiles.append((label, data, cloud_pc, width, slope, shell["shell_peak_pc"]))
    output.mkdir(parents=True, exist_ok=False)
    with (output / "shell_radius_by_cloud_shape.csv").open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)

    fig, (ax, radius_ax) = plt.subplots(1, 2, figsize=(11, 4.6),
                                        constrained_layout=True)
    colors = ("#a33445", "#2b6f7b", "#cd7c28", "#483c87")
    for (label, data, cloud_pc, width, slope, shell), row, color in zip(
            profiles, rows, colors, strict=True):
        order = np.argsort(data[:, 0])
        r = data[order, 0]
        nh = data[order, 1] * RHO_UNIT / MASS_PER_H
        ax.plot(r, nh, color=color, label=label)
        ax.plot(r, profile_nh(r, 1000.0, width, cloud_pc, slope),
                color=color, linestyle=":", linewidth=1.0, alpha=0.6)
        ax.axvline(shell, color=color, linestyle="--", linewidth=0.8)
        unresolved = (row["initial_front_elements"] < 10 or
                      row["shell_width_elements"] < 5)
        radius_ax.scatter(label, shell, color="white" if unresolved else color,
                          edgecolor=color, s=65, linewidth=1.6)
    ax.set(xlim=(0, 8), yscale="log", xlabel="Radius (pc)",
           ylabel=r"$n_H$ (cm$^{-3}$)",
           title="Saved density; dotted initial, dashed shell")
    ax.legend(frameon=False, fontsize=8)
    radius_ax.set(ylabel="Native density-excess shell peak (pc)",
                  title=r"$n_{ref}=1000$ cm$^{-3}$, 0.1 Myr")
    radius_ax.tick_params(axis="x", labelrotation=25)
    for panel in (ax, radius_ax):
        panel.grid(alpha=0.2)
    fig.savefig(output / "shell_radius_by_cloud_shape.png", dpi=180)
    plt.close(fig)
    print(f"Validated {len(rows)} cloud shapes; wrote {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    make_products(args.results, args.output)
