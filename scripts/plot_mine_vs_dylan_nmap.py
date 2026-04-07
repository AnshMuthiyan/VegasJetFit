#!/usr/bin/env python3
"""Compare local short-run nMAP values against Dylan/Ansh runs available on disk."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt


DYLAN_RUNS = {
    "130612A": Path(
        "/Users/jkeohane/GRBs/VegasJetFit/Ansh_Run/Share_for_Ansh_20260220T045317Z/results/130612A_powerlaw_tophat_theta1p0_thesis_short/best_fit.json"
    ),
    # This downloaded bundle is unlabeled on disk; event inferred from z=0.151 and dL28=0.229.
    "221009A": Path(
        "/Users/jkeohane/GRBs/VegasJetFit/Ansh_Run/drive-download-20260213T180906Z-3-001/best_fit.json"
    ),
}


def load_json(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def count_data_rows(csv_path: Path) -> int:
    with csv_path.open(newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def find_obs_csv(resources_root: Path, event: str) -> Path:
    event_dir = resources_root / event
    csvs = sorted(p for p in event_dir.glob("*.csv") if p.name != "parameters.csv")
    preferred = [p for p in csvs if event in p.stem]
    return preferred[0] if preferred else csvs[0]


def mine_best_fit(results_root: Path, event: str) -> Path:
    return results_root / f"{event}_powerlaw_tophat_theta1p0_thesis_short" / "best_fit.json"


def collect_rows(results_root: Path, resources_root: Path) -> list[dict]:
    rows = []
    for event, dylan_path in DYLAN_RUNS.items():
        my_path = mine_best_fit(results_root, event)
        if not my_path.exists() or not dylan_path.exists():
            continue
        mine = load_json(my_path)
        dylan = load_json(dylan_path)
        n_rows = count_data_rows(find_obs_csv(resources_root, event))
        rows.append(
            {
                "event": event,
                "mine_nmap": float(mine["nmap"]),
                "dylan_nmap": float(dylan["nmap"]),
                "mine_nmap_per_row": float(mine["nmap"]) / n_rows,
                "dylan_nmap_per_row": float(dylan["nmap"]) / n_rows,
                "n_rows": n_rows,
            }
        )
    return rows


def identity_bounds(rows: list[dict], xkey: str, ykey: str) -> tuple[float, float]:
    vals = [row[xkey] for row in rows] + [row[ykey] for row in rows]
    lo = min(vals)
    hi = max(vals)
    pad = 0.08 * max(hi - lo, 1e-6)
    return lo - pad, hi + pad


def make_plot(rows: list[dict], xkey: str, ykey: str, xlabel: str, ylabel: str, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 7.6))
    for idx, row in enumerate(rows):
        ax.scatter(row[xkey], row[ykey], s=56, color="#1c7ed6")
        dx = 5 if idx % 2 == 0 else -28
        dy = 6 if idx % 2 == 0 else -12
        ax.annotate(row["event"], (row[xkey], row[ykey]), xytext=(dx, dy), textcoords="offset points", fontsize=9)

    lo, hi = identity_bounds(rows, xkey, ykey)
    ax.plot([lo, hi], [lo, hi], "--", color="0.45", lw=1)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.25)
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

    rows = collect_rows(results_root, resources_root)
    if not rows:
        raise SystemExit("No common Dylan/local runs found.")

    make_plot(
        rows,
        "dylan_nmap",
        "mine_nmap",
        "Dylan/Ansh nMAP",
        "Jonathan nMAP",
        "nMAP Comparison: Jonathan vs Dylan/Ansh",
        out_dir / "nmap_mine_vs_dylan.pdf",
    )
    make_plot(
        rows,
        "dylan_nmap_per_row",
        "mine_nmap_per_row",
        "Dylan/Ansh nMAP / N_rows",
        "Jonathan nMAP / N_rows",
        "Normalized nMAP Comparison: Jonathan vs Dylan/Ansh",
        out_dir / "nmap_per_row_mine_vs_dylan.pdf",
    )

    print(f"Saved plots to: {out_dir}")


if __name__ == "__main__":
    main()
