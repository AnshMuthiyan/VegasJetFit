#!/usr/bin/env python3
"""Stage a filtered live-sheet snapshot beside one campaign's durable files."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


EVENT_RE = re.compile(r"^\d{6}[A-Z]?$")


def campaign_events(campaign: Path) -> list[str]:
    records = campaign / "event_decision_records.json"
    if records.is_file():
        payload = json.loads(records.read_text())
        events = payload.get("events", {})
        if isinstance(events, dict):
            return list(events)
    for name in ("dispatch_manifest.csv", "dynamic_event_queue.csv"):
        path = campaign / name
        if path.is_file():
            with path.open(newline="") as handle:
                events = [row.get("event", "").strip() for row in csv.DictReader(handle)]
            events = [event for event in events if event]
            if events:
                return events
    return sorted(path.name for path in campaign.iterdir() if path.is_dir() and EVENT_RE.fullmatch(path.name))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--events", help="Optional comma-separated event IDs when a new campaign has no local manifest yet.")
    parser.add_argument("--columns", default="M,N,O,Q,S,T,V,W,X")
    parser.add_argument("--out-name", default="tracking_sheet_notes.json")
    args = parser.parse_args()

    source = json.loads(args.snapshot.read_text())
    source_events = source.get("events", {})
    selected_columns = [column.strip().upper() for column in args.columns.split(",") if column.strip()]
    selected = {}
    events = [event.strip() for event in args.events.split(",") if event.strip()] if args.events else campaign_events(args.campaign)
    for event in events:
        entry = source_events.get(event)
        if not isinstance(entry, dict):
            continue
        notes = entry.get("notes", {})
        retained = {
            label: text
            for label, text in notes.items()
            if any(label.startswith(f"{column}:") for column in selected_columns)
        }
        selected[event] = {
            "tracking_row": entry.get("tracking_row"),
            "notes": retained,
        }
    payload = {
        "schema_version": 1,
        "tracking_sheet": source.get("tracking_sheet"),
        "tracking_sheet_url": source.get("tracking_sheet_url"),
        "snapshot_utc": source.get("snapshot_utc"),
        "source_snapshot": str(args.snapshot),
        "selected_columns": selected_columns,
        "events": selected,
    }
    out = args.campaign / args.out_name
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"WROTE {out} ({len(selected)} events)")


if __name__ == "__main__":
    main()
