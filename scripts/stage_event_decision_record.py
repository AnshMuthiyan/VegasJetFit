#!/usr/bin/env python3
"""Copy one approved campaign decision record into a run directory."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.records.read_text())
    events = payload.get("events")
    if not isinstance(events, dict) or not isinstance(events.get(args.event), dict):
        raise SystemExit(f"No decision record for {args.event} in {args.records}")

    record = dict(events[args.event])
    record.update({
        "schema_version": int(payload.get("schema_version", 1)),
        "event": args.event,
        "campaign_record_source": str(args.records),
        "staged_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"STAGED {args.out}")


if __name__ == "__main__":
    main()
