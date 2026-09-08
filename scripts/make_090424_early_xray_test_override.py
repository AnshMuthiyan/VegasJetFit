#!/usr/bin/env python3
"""Create the controlled GRB 090424 early-X-ray inclusion test data file."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path("/Users/jkeohane/GRBs/VegasJetFit")
SOURCE = ROOT / "obs_overrides/090424_early_uvoir_included_no_early_xray.csv"
DESTINATION = ROOT / "obs_overrides/090424_early_uvoir_included_with_early_xray.csv"
EXPECTED_CHANGED = 144


def main() -> None:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise ValueError(f"Missing CSV header: {SOURCE}")

    changed = []
    for row in rows:
        if row.get("Filter", "").strip().lower() != "xray":
            continue
        if row.get("Include", "").strip() != "0":
            continue
        time_seconds = float(row["Time"])
        if 91.1323 <= time_seconds <= 247.071:
            row["Include"] = "1"
            changed.append(time_seconds)

    if len(changed) != EXPECTED_CHANGED:
        raise ValueError(
            f"Expected {EXPECTED_CHANGED} early X-ray points, changed {len(changed)} instead."
        )

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with DESTINATION.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote={DESTINATION}")
    print(f"early_xray_points_enabled={len(changed)}")
    print(f"early_xray_time_seconds={min(changed):.4f},{max(changed):.4f}")


if __name__ == "__main__":
    main()
