#!/usr/bin/env python3
"""Check a run observation CSV against the local Dylan/thesis row-count audit."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from thesis_reproduction_data import normalize_event_name


DEFAULT_AUDITS = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "nmap_dataset_check_same_model_20260428"
    / "nmap_same_model_check.csv",
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "nmap_dataset_check_20260428"
    / "nmap_dataset_check.csv",
)


def count_included_rows(path: Path) -> int:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return 0
        include_col = next((name for name in reader.fieldnames if name.lower() == "include"), None)
        count = 0
        for row in reader:
            if include_col is not None:
                try:
                    if float(row.get(include_col, "1")) <= 0:
                        continue
                except Exception:
                    pass
            count += 1
    return count


def load_reference_counts(event: str, audit_paths: tuple[Path, ...]) -> dict[str, int]:
    normalized = normalize_event_name(event)
    for path in audit_paths:
        if not path.exists():
            continue
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                if normalize_event_name(row.get("event", "")) != normalized:
                    continue
                refs: dict[str, int] = {}
                for key in ("raw_grb_data_rows", "curated_obs_rows"):
                    value = row.get(key)
                    if value in {None, ""}:
                        continue
                    try:
                        refs[key] = int(round(float(value)))
                    except Exception:
                        pass
                return refs
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--obs", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=("warn", "fail"),
        default="warn",
        help="Warn or exit nonzero when the row count does not match an audit count.",
    )
    args = parser.parse_args()

    current = count_included_rows(args.obs)
    refs = load_reference_counts(args.event, DEFAULT_AUDITS)
    if not refs:
        msg = f"OBS_ROW_AUDIT unavailable event={args.event} obs_rows={current}"
        if args.mode == "fail":
            raise SystemExit(msg)
        print(f"WARNING: {msg}")
        return

    matches = [name for name, value in refs.items() if value == current]
    if matches:
        print(f"OBS_ROW_AUDIT ok event={args.event} obs_rows={current} matches={','.join(matches)}")
        return

    ref_text = ", ".join(f"{name}={value}" for name, value in refs.items())
    msg = f"OBS_ROW_AUDIT mismatch event={args.event} obs_rows={current} audit: {ref_text}"
    if args.mode == "fail":
        raise SystemExit(msg)
    print(f"WARNING: {msg}")


if __name__ == "__main__":
    main()
