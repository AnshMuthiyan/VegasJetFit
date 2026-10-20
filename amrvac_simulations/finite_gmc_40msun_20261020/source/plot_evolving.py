#!/usr/bin/env python3
"""Plot the exploratory 40 Msun finite-core run pair."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from preflight import MP_G
from validate_smoke import RHO_UNIT, read_vtu


def front_log(path: Path) -> tuple[np.ndarray, np.ndarray]:
    log = path.read_text(encoding="utf-8")
    rows = re.findall(r"^ FRONT\s+\d+\s+(\S+)\s+(\S+)", log, re.M)
    if not rows:
        raise ValueError(f"no front history in {path}")
    return np.asarray(rows, dtype=float).T


def density_profile(path: Path) -> tuple[np.ndarray, np.ndarray]:
    _, data = read_vtu(path)
    order = np.argsort(data[:, 0])
    radius = data[order, 0]
    nh = data[order, 1] * RHO_UNIT / (1.4 * MP_G)
    unique, inverse = np.unique(radius, return_inverse=True)
    counts = np.bincount(inverse)
    return unique, np.bincount(inverse, weights=nh) / counts


def plot(root: Path, output: Path) -> None:
    gravity = "ion_gravity_4p77myr"
    no_gravity = "ion_nogravity_4p77myr"
    for prefix in (gravity, no_gravity):
        if not (root / f"{prefix}0048.vtu").exists():
            raise ValueError(f"missing complete endpoint for {prefix}")
    output.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 4.7), constrained_layout=True)
    for prefix, label, color in (
        (gravity, "Static cloud gravity", "#0c6b79"),
        (no_gravity, "No gravity", "#bd5a27"),
    ):
        age, front = front_log(root / f"{prefix}.run.log")
        ax.plot(age, front, label=label, color=color, lw=1.8)
    ax.axhline(2.0, color="#585858", linestyle="--", lw=1, label="Initial cloud edge")
    ax.axvline(4.3, color="#59697a", linestyle=":", lw=1)
    ax.axvline(4.5, color="#59697a", linestyle=":", lw=1)
    ax.set(xlabel="Stellar age (Myr)", ylabel="Sharp-front radius (pc)",
           title="Illustrative ionization front in a finite core")
    ax.set_xlim(0, 4.77)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.22)
    ax.legend(frameon=False, loc="upper left")
    fig.savefig(output / "front_history.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.7), constrained_layout=True)
    for index, label, color in (
        (0, "Initial", "#464646"),
        (1, "0.1 Myr", "#2b8cbe"),
        (42, "4.2 Myr (MS)", "#6d9f35"),
        (44, "4.4 Myr (RSG)", "#d27b22"),
        (48, "4.77 Myr (WR)", "#ad3040"),
    ):
        radius, nh = density_profile(root / f"{gravity}{index:04d}.vtu")
        ax.plot(radius, nh, label=label, color=color, lw=1.45,
                linestyle="--" if index == 0 else "-")
    ax.axvline(2.0, color="#585858", linestyle=":", lw=1)
    ax.set(xlabel="Radius (pc)", ylabel=r"Hydrogen nuclei density (cm$^{-3}$)",
           title="Three-phase wind against the initial finite core")
    ax.set_xlim(0, 35)
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1e6)
    ax.grid(alpha=0.22, which="both")
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(output / "density_profiles.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plot(args.root, args.output)


if __name__ == "__main__":
    main()
