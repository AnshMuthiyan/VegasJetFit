#!/usr/bin/env python3
"""Plot fit-quality summaries for thesis_short runs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt


def count_data_rows(csv_path: Path) -> int:
    with csv_path.open(newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def find_obs_csv(resources_root: Path, event: str) -> Path | None:
    event_dir = resources_root / event
    if not event_dir.is_dir():
        return None
    csvs = sorted(p for p in event_dir.glob("*.csv") if p.name != "parameters.csv")
    if not csvs:
        return None
    preferred = [p for p in csvs if event in p.stem]
    return preferred[0] if preferred else csvs[0]


def collect_fit_quality(results_root: Path, resources_root: Path) -> list[dict]:
    rows = []
    for result_dir in sorted(results_root.glob("*_powerlaw_tophat_theta1p0_thesis_short")):
        best_fit = result_dir / "best_fit.json"
        if not best_fit.exists():
            continue
        event = result_dir.name.split("_powerlaw_tophat_", 1)[0]
        with best_fit.open() as handle:
            payload = json.load(handle)
        nmap = payload.get("nmap")
        if nmap is None:
            continue
        obs_csv = find_obs_csv(resources_root, event)
        n_data = count_data_rows(obs_csv) if obs_csv is not None else None
        rows.append(
            {
                "event": event,
                "nmap": float(nmap),
                "n_data": n_data,
                "nmap_per_row": (float(nmap) / n_data) if n_data else None,
            }
        )
    return rows


def plot_metric(rows: list[dict], key: str, ylabel: str, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    xs = list(range(len(rows)))
    ys = [row[key] for row in rows]

    ax.scatter(xs, ys, s=42, color="#1c7ed6")
    ax.plot(xs, ys, color="#74c0fc", alpha=0.6, lw=1)

    for x, row in zip(xs, rows):
        ax.annotate(row["event"], (x, row[key]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8, rotation=45)

    ax.set_xticks(xs)
    ax.set_xticklabels([row["event"] for row in rows], rotation=45, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path)
    fig.savefig(out_path.with_suffix(".png"), dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-root",
        default="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results",
    )
    parser.add_argument(
        "--resources-root",
        default="/Users/jkeohane/GRBs/VegasJetFit/jetfit/resources/grbs",
    )
    parser.add_argument(
        "--out-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/logs/thesis_short_compare",
    )
    args = parser.parse_args()

    results_root = Path(args.results_root)
    resources_root = Path(args.resources_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = collect_fit_quality(results_root, resources_root)
    if not rows:
        raise SystemExit("No thesis_short fit-quality data found.")

    plot_metric(
        rows,
        "nmap",
        "nMAP = -2 max(log posterior)",
        "Short-Run Goodness Metric by GRB",
        out_dir / "nmap_short_runs.pdf",
    )

    rows_norm = [row for row in rows if row["nmap_per_row"] is not None]
    plot_metric(
        rows_norm,
        "nmap_per_row",
        "nMAP / N_rows",
        "Short-Run Goodness Metric per Data Row by GRB",
        out_dir / "nmap_per_row_short_runs.pdf",
    )

    print(f"Saved plots to: {out_dir}")


if __name__ == "__main__":
    main()
