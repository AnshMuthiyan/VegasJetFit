#!/usr/bin/env python3
"""Check the curated May 1 AMRVAC snapshot bundle and its source manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUALITY = ROOT / "tables" / "allP_run_quality_table.csv"
MANIFEST = ROOT / "selected_vtu_manifest.csv"
FIELDNAMES = (
    "run_id", "p", "n", "chosen_snapshot", "bundle_file",
    "campaign_source", "bytes", "sha256",
)
ARCHIVE = "_archive_pre_innerfix_20260503T174140Z"


def expected_rows() -> list[dict[str, str]]:
    with QUALITY.open(newline="") as handle:
        quality_rows = list(csv.DictReader(handle))
    if len(quality_rows) != 12:
        raise ValueError(f"Expected 12 May 1 quality rows, found {len(quality_rows)}")

    rows = []
    for item in quality_rows:
        run_id = item["run_id"]
        snapshot = item["chosen_snapshot"]
        if not run_id.startswith(("p4_n", "p5_n", "p6_n")) or not snapshot.endswith(".vtu"):
            raise ValueError(f"Unexpected run/snapshot: {run_id}, {snapshot}")
        bundle_file = Path("selected_vtu") / f"{run_id}__{snapshot}"
        path = ROOT / bundle_file
        data = path.read_bytes()
        if not data.startswith(b'<?xml version="1.0"?>') or b"<VTKFile " not in data[:256]:
            raise ValueError(f"Not a VTK XML file: {path}")
        prefix = "" if run_id.startswith("p4_") else f"{ARCHIVE}/"
        source = f"{prefix}pressure_{run_id}/output/Ostar_1D/{snapshot}"
        rows.append({
            "run_id": run_id,
            "p": item["p"],
            "n": item["n"],
            "chosen_snapshot": snapshot,
            "bundle_file": bundle_file.as_posix(),
            "campaign_source": source,
            "bytes": str(len(data)),
            "sha256": hashlib.sha256(data).hexdigest(),
        })

    if len({row["run_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate run_id in quality table")
    bundled = {p.name for p in (ROOT / "selected_vtu").glob("*.vtu")}
    expected = {Path(row["bundle_file"]).name for row in rows}
    if bundled != expected:
        raise ValueError(f"Snapshot file set mismatch: missing={expected - bundled}, extra={bundled - expected}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    rows = expected_rows()

    if args.write_manifest:
        with MANIFEST.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        with MANIFEST.open(newline="") as handle:
            recorded = list(csv.DictReader(handle))
        if recorded != rows:
            raise SystemExit("Manifest differs from selected files or quality table")
    print(f"Verified {len(rows)} selected VTU snapshots: {MANIFEST}")


if __name__ == "__main__":
    main()
