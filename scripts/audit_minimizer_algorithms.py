#!/usr/bin/env python3
"""Summarize observed minimizer algorithm outcomes from local results."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def iter_json_rows(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def classify_row(row: dict[str, Any]) -> tuple[str, str]:
    method = str(
        row.get("scipy_method")
        or row.get("primary_scipy_method")
        or row.get("optimizer_backend")
        or "unknown"
    )
    message = str(row.get("message") or "")
    success = bool(row.get("success"))
    seed_preserved = bool(row.get("seed_preserved")) or method == "seed_preserved"

    if seed_preserved:
        return method, "seed_preserved"
    if success:
        return method, "success"
    if "exception" in message.lower():
        return method, "exception"
    return method, "explicit_failure"


def audit_json_files(root: Path) -> tuple[list[dict[str, str]], dict[str, Counter]]:
    rows_out: list[dict[str, str]] = []
    counts: dict[str, Counter] = defaultdict(Counter)
    for path in sorted(root.rglob("minimized*.json")):
        for row in iter_json_rows(path):
            method, outcome = classify_row(row)
            counts[method][outcome] += 1
            rows_out.append(
                {
                    "source": str(path),
                    "method": method,
                    "outcome": outcome,
                    "success": str(bool(row.get("success"))),
                    "message": str(row.get("message") or "")[:240],
                }
            )
    return rows_out, counts


def write_outputs(rows: list[dict[str, str]], counts: dict[str, Counter], out_csv: Path, out_md: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "method", "outcome", "success", "message"])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Minimizer Algorithm Outcome Tracker",
        "",
        "This file is generated from local `minimized*.json` products. It records explicit optimizer outcomes only; hung jobs that were killed before writing JSON must be added as manual notes.",
        "",
        "## Summary",
        "",
        "| Method | Success | Seed Preserved | Explicit Failure | Exception | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in sorted(counts):
        c = counts[method]
        total = sum(c.values())
        lines.append(
            f"| `{method}` | {c['success']} | {c['seed_preserved']} | {c['explicit_failure']} | {c['exception']} | {total} |"
        )

    lines.extend(
        [
            "",
            "## Manual Hang Notes",
            "",
            "- `Powell` has at least one confirmed hang/stall case: `080319B_sbpl_structjet_thetav_thetacfree_unseeded_2000x2000_v1` on Lyra ran for roughly 21 hours serially with no log output and no files in `minimized/`; it was killed on 2026-05-27.",
            "- Operational rule: when a minimizer appears hung, cycle to a different first-choice algorithm instead of restarting the same method. Keep the previous method only as a fallback if there is a reason to test it.",
            "",
            "## CSV Detail",
            "",
            f"Detailed row-level audit: `{out_csv}`",
            "",
        ]
    )
    out_md.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/Users/jkeohane/GRBs/VegasJetFit/jetfit/results"))
    parser.add_argument("--out-csv", type=Path, default=Path("/Users/jkeohane/GRBs/VegasJetFit/reports/minimizer_algorithm_outcomes.csv"))
    parser.add_argument("--out-md", type=Path, default=Path("/Users/jkeohane/GRBs/VegasJetFit/reports/minimizer_algorithm_outcomes.md"))
    args = parser.parse_args()

    rows, counts = audit_json_files(args.root.expanduser().resolve())
    write_outputs(rows, counts, args.out_csv.expanduser().resolve(), args.out_md.expanduser().resolve())
    print(f"rows={len(rows)}")
    for method in sorted(counts):
        print(method, dict(counts[method]))
    print(f"wrote={args.out_md}")
    print(f"wrote={args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
