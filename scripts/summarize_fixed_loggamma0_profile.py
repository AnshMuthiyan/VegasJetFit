#!/usr/bin/env python3
"""Summarize completed fixed-log10(Gamma0) profile-likelihood minimizations."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--loggammas", nargs="+", type=float, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    for loggamma in args.loggammas:
        label = str(int(loggamma)) if loggamma.is_integer() else str(loggamma).replace(".", "p")
        run_name = f"080413B_loggamma0_{label}_{args.run_tag}"
        path = args.results_root / run_name / "minimized" / "minimized.json"
        if not path.is_file():
            rows.append({"log10_gamma0": loggamma, "gamma0": 10.0**loggamma, "nmap": None, "status": "pending", "run_name": run_name})
            continue
        payload = json.loads(path.read_text())
        nmap = float(payload["nmap"])
        rows.append(
            {
                "log10_gamma0": loggamma,
                "gamma0": 10.0**loggamma,
                "nmap": nmap,
                "status": "complete" if math.isfinite(nmap) else "invalid",
                "run_name": run_name,
                "success": payload.get("success"),
                "optimizer": payload.get("scipy_method"),
            }
        )

    finite = [row["nmap"] for row in rows if isinstance(row.get("nmap"), float) and math.isfinite(row["nmap"])]
    best = min(finite) if finite else None
    for row in rows:
        row["delta_nmap"] = row["nmap"] - best if best is not None and isinstance(row.get("nmap"), float) else None

    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / "080413B_fixed_loggamma0_profile.csv"
    fields = ["log10_gamma0", "gamma0", "nmap", "delta_nmap", "status", "success", "optimizer", "run_name"]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    complete = [row for row in rows if row.get("delta_nmap") is not None]
    if complete:
        x = [row["log10_gamma0"] for row in complete]
        y = [row["delta_nmap"] for row in complete]
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        ax.plot(x, y, marker="o", color="#255f85", linewidth=2)
        ax.axhline(0.0, color="0.35", linewidth=1, linestyle="--")
        ax.axvline(5.0, color="#b33b32", linewidth=1.5, linestyle=":", label="Previous upper prior bound")
        ax.set_xlabel(r"Fixed $\log_{10}(\Gamma_0)$")
        ax.set_ylabel(r"$\Delta N_{\rm MAP}$ (smaller is better)")
        ax.set_xticks(args.loggammas)
        ax.grid(alpha=0.25)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(args.out_dir / "080413B_fixed_loggamma0_profile.png", dpi=220)
        fig.savefig(args.out_dir / "080413B_fixed_loggamma0_profile.pdf")
        plt.close(fig)
    print(csv_path)


if __name__ == "__main__":
    main()
