#!/usr/bin/env python3
"""Plot Dylan thesis values against local short-run results for shared parameters."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt


THESIS = {
    "050525A": {
        "model": "PL",
        "E52": (0.53, 0.39, 1.19),
        "n017": (-0.31, -0.43, -0.14),
        "eps_e": (-0.51, -0.86, -0.41),
        "eps_b": (-0.53, -2.02, -0.25),
        "p": (2.22, 2.17, 2.28),
        "k": (2.93, 2.82, 2.97),
        "ebv_source_frame": (0.04, 0.03, 0.05),
        "slop": (0.09, 0.08, 0.10),
    },
    "050922C": {
        "model": "PL",
        "E52": (0.61, 0.24, 0.93),
        "n017": (-0.85, -3.77, 3.13),
        "eps_e": (-0.71, -1.04, -0.33),
        "eps_b": (-1.47, -2.66, -0.62),
        "p": (2.06, 2.04, 2.08),
        "k": (-3.55, -5.02, -2.35),
        "ebv_source_frame": (0.02, 0.01, 0.03),
        "slop": (0.02, 0.02, 0.02),
    },
    "080319B": {
        "model": "SBPL",
        "E52": (2.37, 2.15, 2.61),
        "lf0": (2.43, 2.09, 2.83),
        "eps_e": (-0.72, -0.96, -0.49),
        "eps_b": (-3.35, -4.03, -2.64),
        "p": (2.48, 2.47, 2.49),
        "kpre": (2.33, 2.32, 2.34),
        "kpost": (1.18, 1.12, 1.24),
        "ebv_source_frame": (0.01, 0.01, 0.02),
        "slop": (0.03, 0.03, 0.03),
    },
    "080413B": {
        "model": "SBPL",
        "E52": (0.65, 0.28, 1.16),
        "lf0": (2.18, 2.18, 2.18),
        "eps_e": (-0.25, -0.36, -0.11),
        "eps_b": (-0.85, -1.28, -0.51),
        "p": (2.37, 2.34, 2.40),
        "kpre": (2.51, 2.38, 2.62),
        "kpost": (0.45, 0.29, 0.58),
        "ebv_source_frame": (0.01, 0.00, 0.02),
        "slop": (0.02, 0.02, 0.02),
    },
    "090424": {
        "model": "PL",
        "E52": (0.56, 0.45, 1.02),
        "lf0": (1.83, 1.72, 2.33),
        "n017": (-1.23, -1.58, -0.73),
        "eps_e": (-0.26, -0.36, -0.11),
        "eps_b": (-1.15, -1.93, -0.59),
        "p": (2.07, 2.05, 2.11),
        "k": (2.08, 2.01, 2.11),
        "ebv_source_frame": (0.09, 0.07, 0.12),
    },
    "090618": {
        "model": "PL",
        "E52": (0.67, 0.45, 0.83),
        "n017": (-3.01, -5.22, 0.32),
        "eps_e": (-0.57, -0.71, -0.35),
        "eps_b": (-2.03, -2.71, -1.61),
        "p": (2.29, 2.26, 2.31),
        "k": (-6.52, -8.07, -5.20),
        "ebv_source_frame": (0.00, 0.00, 0.00),
        "slop": (0.02, 0.02, 0.02),
    },
    "111228A": {
        "model": "PL",
        "E52": (0.95, 0.64, 1.90),
        "lf0": (2.47, 1.96, 3.42),
        "n017": (-1.31, -1.46, -1.13),
        "eps_e": (-0.14, -0.20, -0.09),
        "eps_b": (-0.62, -0.78, -0.49),
        "p": (2.02, 2.02, 2.02),
        "k": (1.11, 1.07, 1.14),
        "ebv_source_frame": (0.11, 0.11, 0.11),
        "slop": (0.02, 0.02, 0.02),
    },
    "130612A": {
        "model": "PL",
        "E52": (2.47, 1.16, 3.53),
        "n017": (1.67, -1.29, 4.57),
        "eps_e": (-3.22, -4.25, -1.96),
        "eps_b": (-2.31, -3.96, -0.76),
        "p": (2.03, 2.01, 2.06),
        "k": (-1.02, -2.30, 0.18),
        "ebv_source_frame": (0.16, 0.12, 0.20),
        "slop": (0.03, 0.02, 0.04),
    },
    "131030A": {
        "model": "PL",
        "E52": (3.47, 2.94, 3.84),
        "n017": (-0.84, -3.76, 1.00),
        "eps_e": (-2.52, -2.87, -2.06),
        "eps_b": (-4.78, -5.66, -3.39),
        "p": (2.31, 2.25, 2.35),
        "k": (-0.97, -1.29, -0.61),
        "ebv_source_frame": (0.01, 0.00, 0.02),
        "slop": (0.03, 0.02, 0.03),
    },
    "140506A": {
        "model": "PL",
        "E52": (2.57, 2.20, 3.03),
        "n017": (-3.11, -5.02, -1.06),
        "eps_e": (-1.69, -2.14, -1.38),
        "eps_b": (-5.08, -5.71, -4.30),
        "p": (2.31, 2.26, 2.36),
        "k": (-2.43, -2.92, -1.95),
        "ebv_source_frame": (0.25, 0.23, 0.27),
        "slop": (0.05, 0.04, 0.06),
    },
    "160131A": {
        "model": "PL",
        "E52": (1.58, 1.31, 1.80),
        "n017": (0.73, 0.20, 1.32),
        "eps_e": (-1.42, -1.64, -1.16),
        "eps_b": (-1.00, -1.75, -0.33),
        "p": (2.08, 2.07, 2.09),
        "k": (1.72, 1.67, 1.77),
        "ebv_source_frame": (0.00, 0.00, 0.00),
        "slop": (0.02, 0.02, 0.02),
    },
    "171010A": {
        "model": "PL",
        "E52": (2.77, 1.41, 3.70),
        "n017": (0.50, -1.34, 1.99),
        "eps_e": (-1.50, -2.30, -0.71),
        "eps_b": (-3.62, -5.25, -1.56),
        "p": (2.60, 2.48, 2.71),
        "k": (1.84, 1.48, 2.24),
        "ebv_source_frame": (0.03, 0.01, 0.08),
        "slop": (0.01, 0.00, 0.02),
    },
    "210905A": {
        "model": "PL",
        "E52": (3.78, 3.55, 3.94),
        "n017": (-4.16, -6.86, -2.12),
        "eps_e": (-1.73, -1.89, -1.53),
        "eps_b": (-5.51, -5.86, -4.94),
        "p": (2.44, 2.40, 2.47),
        "k": (-8.00, -9.40, -6.33),
        "ebv_source_frame": (0.04, 0.02, 0.06),
        "slop": (0.06, 0.05, 0.07),
    },
    "220101A": {
        "model": "PL",
        "E52": (3.57, 3.13, 3.88),
        "n017": (-2.24, -3.98, -0.87),
        "eps_e": (-0.53, -0.90, -0.26),
        "eps_b": (-4.74, -5.62, -3.47),
        "p": (2.54, 2.50, 2.58),
        "k": (0.15, -0.15, 0.41),
        "ebv_source_frame": (0.02, 0.01, 0.04),
        "slop": (0.07, 0.06, 0.08),
    },
    "221009A": {
        "model": "PL",
        "E52": (2.75, 2.24, 3.28),
        "n017": (-0.12, -1.01, 0.76),
        "eps_e": (-0.77, -1.29, -0.26),
        "eps_b": (-2.40, -3.96, -0.85),
        "p": (2.36, 2.35, 2.37),
        "k": (2.19, 2.16, 2.22),
        "ebv_source_frame": (0.18, 0.16, 0.20),
        "slop": (0.03, 0.03, 0.03),
    },
}


GENERIC_PARAMS = {
    "E52": "log10 E52",
    "lf0": "log10 Gamma0",
    "n017": "log10 n0,17",
    "eps_e": "log10 eps_e",
    "eps_b": "log10 eps_B",
    "p": "p",
    "ebv_source_frame": "E(B-V) source frame",
    "slop": "sigma_slop",
}


def load_summary(summary_csv: Path) -> dict[str, tuple[float, float, float]]:
    values: dict[str, tuple[float, float, float]] = {}
    with summary_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row[""]
            values[name] = (
                float(row["mean"]),
                float(row["hdi_3%"]),
                float(row["hdi_97%"]),
            )
    return values


def collect_short_results(results_root: Path) -> dict[str, dict[str, tuple[float, float, float]]]:
    collected = {}
    for summary_csv in sorted(
        results_root.glob("*_powerlaw_tophat_theta1p0_thesis_short/summary.csv")
    ):
        event = summary_csv.parent.name.split("_powerlaw_tophat_", 1)[0]
        collected[event] = load_summary(summary_csv)
    return collected


def add_identity_line(ax: plt.Axes, points: list[float]) -> None:
    lower = min(points)
    upper = max(points)
    pad = 0.08 * max(upper - lower, 1e-6)
    ax.plot([lower - pad, upper + pad], [lower - pad, upper + pad], "--", color="0.4", lw=1)
    ax.set_xlim(lower - pad, upper + pad)
    ax.set_ylim(lower - pad, upper + pad)


def plot_generic(
    short_results: dict[str, dict[str, tuple[float, float, float]]],
    param: str,
    label: str,
    out_pdf: Path,
    out_png: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 8.2))
    all_points: list[float] = []
    pl_done = False
    sbpl_done = False

    for idx, event in enumerate(sorted(short_results)):
        thesis_event = THESIS.get(event)
        if thesis_event is None or param not in thesis_event or param not in short_results[event]:
            continue

        tx, tx_lo, tx_hi = thesis_event[param]
        uy, uy_lo, uy_hi = short_results[event][param]
        all_points.extend([tx, uy, tx_lo, tx_hi, uy_lo, uy_hi])
        xerr = [[tx - tx_lo], [tx_hi - tx]]
        yerr = [[uy - uy_lo], [uy_hi - uy]]

        if thesis_event["model"] == "PL":
            marker = "o"
            color = "#1c7ed6"
            ecolor = "#a5d8ff"
            legend = "PL thesis fit" if not pl_done else None
            pl_done = True
        else:
            marker = "^"
            color = "#e67700"
            ecolor = "#ffd8a8"
            legend = "SBPL thesis fit" if not sbpl_done else None
            sbpl_done = True

        ax.errorbar(
            tx,
            uy,
            xerr=xerr,
            yerr=yerr,
            fmt=marker,
            ms=6,
            color=color,
            ecolor=ecolor,
            elinewidth=1.2,
            capsize=2,
            label=legend,
        )
        dx = 5 if idx % 2 == 0 else -38
        dy = 5 if idx % 3 == 0 else -12
        ax.annotate(event, (tx, uy), xytext=(dx, dy), textcoords="offset points", fontsize=8)

    add_identity_line(ax, all_points)
    ax.set_title(f"{label} Comparison: Dylan Thesis vs Jonathan Short Runs")
    ax.set_xlabel(f"Dylan thesis {label}")
    ax.set_ylabel(f"Jonathan short-run {label}")
    ax.grid(alpha=0.25)
    if pl_done or sbpl_done:
        ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_pdf)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def plot_p(short_results: dict[str, dict[str, tuple[float, float, float]]], out_pdf: Path, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 8.2))
    all_points: list[float] = []

    for idx, event in enumerate(sorted(short_results)):
        if event not in THESIS or "p" not in THESIS[event] or "p" not in short_results[event]:
            continue
        tx, tx_lo, tx_hi = THESIS[event]["p"]
        uy, uy_lo, uy_hi = short_results[event]["p"]
        all_points.extend([tx, uy, tx_lo, tx_hi, uy_lo, uy_hi])
        xerr = [[tx - tx_lo], [tx_hi - tx]]
        yerr = [[uy - uy_lo], [uy_hi - uy]]
        ax.errorbar(
            tx,
            uy,
            xerr=xerr,
            yerr=yerr,
            fmt="o",
            ms=6,
            color="#0b7285",
            ecolor="#74c0fc",
            elinewidth=1.2,
            capsize=2,
        )
        dx = 5 if idx % 2 == 0 else -38
        dy = 5 if idx % 3 == 0 else -12
        ax.annotate(event, (tx, uy), xytext=(dx, dy), textcoords="offset points", fontsize=8)

    add_identity_line(ax, all_points)
    ax.set_title("Electron Index Comparison: Dylan Thesis vs Jonathan Short Runs")
    ax.set_xlabel("Dylan thesis p")
    ax.set_ylabel("Jonathan short-run p")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_pdf)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def plot_k(short_results: dict[str, dict[str, tuple[float, float, float]]], out_pdf: Path, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 8.4))
    all_points: list[float] = []
    pl_done = False
    sbpl_done = False

    for idx, event in enumerate(sorted(short_results)):
        if event not in THESIS or "k" not in short_results[event]:
            continue

        uy, uy_lo, uy_hi = short_results[event]["k"]
        yerr = [[uy - uy_lo], [uy_hi - uy]]

        if "k" in THESIS[event]:
            tx, tx_lo, tx_hi = THESIS[event]["k"]
            all_points.extend([tx, uy, tx_lo, tx_hi, uy_lo, uy_hi])
            xerr = [[tx - tx_lo], [tx_hi - tx]]
            ax.errorbar(
                tx,
                uy,
                xerr=xerr,
                yerr=yerr,
                fmt="o",
                ms=6,
                color="#1c7ed6",
                ecolor="#a5d8ff",
                elinewidth=1.2,
                capsize=2,
                label="Single-k thesis fit" if not pl_done else None,
            )
            dx = 5 if idx % 2 == 0 else -35
            dy = 5 if idx % 3 == 0 else -12
            ax.annotate(event, (tx, uy), xytext=(dx, dy), textcoords="offset points", fontsize=8)
            pl_done = True
            continue

        for suffix, color, ecolor, yoffset in (
            ("kpre", "#e67700", "#ffd8a8", 10),
            ("kpost", "#d9480f", "#ffc9c9", -14),
        ):
            tx, tx_lo, tx_hi = THESIS[event][suffix]
            all_points.extend([tx, uy, tx_lo, tx_hi, uy_lo, uy_hi])
            xerr = [[tx - tx_lo], [tx_hi - tx]]
            ax.errorbar(
                tx,
                uy,
                xerr=xerr,
                yerr=yerr,
                fmt="^",
                ms=6,
                color=color,
                ecolor=ecolor,
                elinewidth=1.1,
                capsize=2,
                label="Broken-k thesis fit" if not sbpl_done else None,
            )
            label = f"{event}-{suffix[1:]}"
            ax.annotate(label, (tx, uy), xytext=(6, yoffset), textcoords="offset points", fontsize=8)
            sbpl_done = True

    add_identity_line(ax, all_points)
    ax.set_title("Density Index Comparison: Dylan Thesis vs Jonathan Short Runs")
    ax.set_xlabel("Dylan thesis k")
    ax.set_ylabel("Jonathan short-run k")
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_pdf)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-root",
        default="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results",
        help="Directory containing local thesis_short result directories.",
    )
    parser.add_argument(
        "--out-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/logs/thesis_short_compare",
        help="Output directory for comparison plots.",
    )
    args = parser.parse_args()

    results_root = Path(args.results_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    short_results = collect_short_results(results_root)
    if not short_results:
        raise SystemExit(f"No short-run summaries found under {results_root}")

    plot_p(
        short_results,
        out_dir / "p_compare_thesis_vs_short.pdf",
        out_dir / "p_compare_thesis_vs_short.png",
    )
    plot_k(
        short_results,
        out_dir / "k_compare_thesis_vs_short.pdf",
        out_dir / "k_compare_thesis_vs_short.png",
    )
    for param, label in GENERIC_PARAMS.items():
        if param == "p":
            continue
        plot_generic(
            short_results,
            param,
            label,
            out_dir / f"{param}_compare_thesis_vs_short.pdf",
            out_dir / f"{param}_compare_thesis_vs_short.png",
        )

    print(f"Saved plots to: {out_dir}")


if __name__ == "__main__":
    main()
