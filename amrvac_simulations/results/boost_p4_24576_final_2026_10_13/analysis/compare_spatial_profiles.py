#!/usr/bin/env python3
"""Compare matched-age 1D controls at two spatial resolutions."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
GRBS = ROOT.parents[1]
sys.path.insert(0, str(GRBS / "VegasJetFit_wind_bubble_handoff/amrvac_simulations/analysis"))
from plot_dense_cooling_run import read_vtu  # noqa: E402


CASES = ("p4_n22", "p4_n23", "p4_n24")


def load(run: Path) -> list[tuple[float, np.ndarray]]:
    if (run / "run.exit").read_text().strip() != "0":
        raise ValueError(f"{run}: failed run")
    if "Finished AMRVAC in" not in (run / "run.stdout").read_text():
        raise ValueError(f"{run}: normal completion marker missing")
    data = [read_vtu(path) for path in sorted((run / "output").glob("test*.vtu"))]
    if len(data) != 54 or not np.isclose(data[-1][0], 5.24, atol=0.001):
        raise ValueError(f"{run}: incomplete 5.24-Myr sequence")
    return data


def differences(coarse: np.ndarray, fine: np.ndarray) -> dict[str, float]:
    radius = np.linspace(0.25, 30.0, 1800)
    values: dict[str, float] = {}
    for name, column in (("rho", 1), ("p", 3)):
        a = np.interp(radius, coarse[:, 0], np.log10(coarse[:, column]))
        b = np.interp(radius, fine[:, 0], np.log10(fine[:, column]))
        delta = np.abs(b - a)
        values[f"mean_abs_log10{name}"] = float(delta.mean())
        values[f"p95_abs_log10{name}"] = float(np.percentile(delta, 95))
        values[f"max_abs_log10{name}"] = float(delta.max())
    return values


def plot_final(
    case: str,
    variant: str,
    coarse: np.ndarray,
    fine: np.ndarray,
    coarse_cells: int,
    fine_cells: int,
    domain_scale: int,
    out: Path,
) -> None:
    stem = f"{case}_{variant}_{coarse_cells}_vs_{fine_cells}"
    if domain_scale != 1:
        stem += f"_domain{domain_scale}x"
    png = out / f"{stem}.png"
    pdf = out / f"{stem}.pdf"
    if png.exists() or pdf.exists():
        return
    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True, layout="constrained")
    for profile, label, color in (
        (coarse, f"{coarse_cells} base cells", "#ac4237"),
        (fine, f"{fine_cells} base cells", "#166995"),
    ):
        interior = profile[1:-1]
        for ax, column in zip(axes, (1, 3, 2)):
            value = interior[:, column] / 1e5 if column == 2 else interior[:, column]
            ax.plot(interior[:, 0], value, label=label, color=color, lw=1.5)
    axes[0].set_ylabel(r"Mass density [g cm$^{-3}$]")
    axes[1].set_ylabel(r"Thermal pressure [dyn cm$^{-2}$]")
    axes[2].set_ylabel("Radial velocity [km/s]")
    axes[2].set_xlabel("Radius [pc]")
    axes[0].set_yscale("log")
    axes[1].set_yscale("log")
    axes[0].legend()
    for ax in axes:
        ax.set_xlim(0, coarse[-1, 0])
        ax.grid(alpha=0.2)
    fig.suptitle(f"BoOST {case} {variant} at 5.24 Myr: spatial-grid check")
    fig.savefig(png, dpi=200)
    fig.savefig(pdf)
    plt.close(fig)


def run_directory(case: str, variant: str, cells: int, domain_scale: int, platform: str) -> Path:
    suffix = (
        f"_domain{domain_scale}x_{cells}"
        if domain_scale != 1
        else ("" if cells == 192 else f"_{cells}")
    )
    prefix = "results_mac_full" if platform == "mac" else "results_full"
    return ROOT / f"{prefix}{suffix}" / f"{case}_{variant}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coarse-cells", type=int, choices=(192, 384, 768, 1536, 3072, 6144, 12288), default=192)
    parser.add_argument("--fine-cells", type=int, choices=(384, 768, 1536, 3072, 6144, 12288, 24576), default=384)
    parser.add_argument("--variant", choices=("hydro", "cooling", "conduction"), default="hydro")
    parser.add_argument("--domain-scale", type=int, choices=(1, 2, 4), default=1)
    parser.add_argument("--platform", choices=("vm", "mac"), default="vm")
    parser.add_argument("--output", type=Path, help="write a distinct comparison CSV")
    args = parser.parse_args()
    if args.fine_cells != 2 * args.coarse_cells:
        parser.error("the fine grid must have twice as many base cells")
    if args.domain_scale == 2 and (args.coarse_cells, args.fine_cells) != (384, 768):
        parser.error("wide-domain comparison requires 384 and 768 base cells")
    if args.domain_scale == 4 and (args.coarse_cells, args.fine_cells) not in ((1536, 3072), (3072, 6144), (6144, 12288), (12288, 24576)):
        parser.error("4x-domain comparison requires adjacent 1536-to-24576 base-cell rungs")

    rows: list[dict[str, float | str]] = []
    plot_dir = ROOT / ("spatial_comparison_mac_plots" if args.platform == "mac" else "spatial_comparison_plots")
    plot_dir.mkdir(exist_ok=True)
    for case in CASES:
        coarse_run = run_directory(case, args.variant, args.coarse_cells, args.domain_scale, args.platform)
        fine_run = run_directory(case, args.variant, args.fine_cells, args.domain_scale, args.platform)
        if not (coarse_run / "run.exit").exists() or not (fine_run / "run.exit").exists():
            print(f"{case}: waiting for complete {args.coarse_cells}/{args.fine_cells} {args.variant} pair")
            continue
        coarse = load(coarse_run)
        fine = load(fine_run)
        for (age_coarse, profile_coarse), (age_fine, profile_fine) in zip(coarse, fine):
            if not np.isclose(age_coarse, age_fine, atol=0.001):
                raise ValueError(f"{case}: saved ages differ: {age_coarse}, {age_fine}")
            rows.append({"case": case, "age_Myr": age_coarse, **differences(profile_coarse, profile_fine)})
        plot_final(
            case, args.variant, coarse[-1][1], fine[-1][1],
            args.coarse_cells, args.fine_cells, args.domain_scale, plot_dir,
        )
        print(f"{case}: compared {len(coarse)} matched {args.variant} ages")
    if rows:
        if (args.coarse_cells, args.fine_cells, args.variant, args.domain_scale, args.platform) == (192, 384, "hydro", 1, "vm"):
            out = ROOT / "spatial_comparison.csv"
        else:
            platform_tag = "mac_" if args.platform == "mac" else ""
            out = ROOT / (
                f"spatial_comparison_{platform_tag}{args.variant}_{args.coarse_cells}vs{args.fine_cells}"
                f"_domain{args.domain_scale}x.csv"
            )
        out = args.output or out
        with out.open("x" if args.output else "w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} spatial-grid comparisons to {out}")


if __name__ == "__main__":
    main()
