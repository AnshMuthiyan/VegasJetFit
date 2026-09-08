#!/usr/bin/env python3
"""Create honest retrospective decision records for a final-final campaign."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path


TRACKING_ROWS = {
    "050525A": 2, "050922C": 3, "080319B": 4, "080413B": 5,
    "090424": 6, "090618": 7, "111228A": 8, "130612A": 9,
    "131030A": 10, "140506A": 11, "160131A": 12, "171010A": 13,
    "210905A": 14, "220101A": 15, "221009A": 16,
}

EVENT_CONDITIONS = {
    "090424": "The retained data configuration includes the early UVOT points approved for this final-final analysis.",
    "130612A": "The source family was retained despite mild numerical light-curve and cooling-frequency wiggles; its post-fit ladder is the evidence gate for any refinement.",
    "131030A": "The approved data configuration retains the early feature judged suitable for fitting rather than excluding it as an unmodelled flare.",
    "140506A": "This event was run at the campaign's moderate resolution because prior products showed mild numerical instability.",
    "160131A": "The posterior-cloud source is the physically selected k < -4 solution family from the preceding focused minimization.",
    "210905A": "The posterior-cloud source is the physically preferred low-p solution family after the focused re-minimization described in the tracking sheet.",
    "220101A": "The approved data configuration includes the corrected HST filters and the additional early X-ray data.",
    "221009A": "The configuration enforces the dedicated Milky-Way extinction treatment: fixed E(B-V)_MW=1.3021 mag and the fitted R_V^MW prior.",
}


def text(value: object) -> str:
    return str(value).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--campaign-metadata", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mirror-out", type=Path)
    parser.add_argument("--snapshot-utc", default=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    args = parser.parse_args()

    metadata = json.loads(args.campaign_metadata.read_text())
    with args.manifest.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    events = [text(row["event"]) for row in rows]
    missing_rows = [event for event in events if event not in TRACKING_ROWS]
    if missing_rows:
        raise SystemExit(f"No tracking-row mapping for: {', '.join(missing_rows)}")

    sampler = text(metadata["sampler"])
    resolution = text(metadata["resolution"])
    purpose = text(metadata["purpose"])
    records: dict[str, dict[str, object]] = {}
    for row in rows:
        event = text(row["event"])
        host = text(row["host"])
        workers = text(row["workers"])
        condition = EVENT_CONDITIONS.get(event)
        notes: dict[str, str] = {
            "Retroactive provenance": (
                "This standard decision record was backfilled on 2026-07-22 from the "
                "July 16 campaign metadata and dispatch manifest. It documents the "
                "actual common protocol; it is not presented as a contemporaneous "
                "verbatim tracking-sheet entry."
            ),
        }
        if condition:
            notes["Known event-specific condition"] = condition
        records[event] = {
            "tracking_row": TRACKING_ROWS[event],
            "decision_summary": (
                "Retroactive standard record for the accepted final-final solution "
                "family: full correlated posterior-cloud initialization, expanded "
                "agreed priors, and thawed structured-jet shape s."
            ),
            "pre_dispatch_decision": (
                "Initialize from the accepted correlated cold-chain posterior cloud from the "
                "July 7 final-seeded source campaign recorded in the campaign metadata. "
                "The newly free s coordinate starts in a compact cloud near 4, but is sampled "
                "under its stated broad prior. The source cloud is an initializer only, not an "
                "additional likelihood or prior. "
                f"Use {sampler}."
            ),
            "refinement_basis": (
                f"This run implements the campaign purpose: {purpose} The moderate "
                "production grid is the reference calculation for a subsequent fixed-solution "
                "VegasAfterglow resolution ladder; any finer continuation must be selected from "
                "that event-specific evidence rather than a generic grid rule."
            ),
            "selected_refinement": (
                f"Production VegasAfterglow controls: {resolution}. Manifest allocation: "
                f"{host}, {workers} workers."
            ),
            "postfit_protocol": (
                "On Lyra, minimize the completed chain, generate the complete publication-ready "
                "post-fit suite, run and validate the fixed-minimized-solution numerical-resolution "
                "ladder, publish the event, and refresh the partial campaign meeting book. "
                "Use the new event ladder and tracking-sheet review to decide whether a finer "
                "cloud-seeded continuation is warranted."
            ),
            "tracking_sheet_notes": notes,
        }

    payload = {
        "schema_version": 1,
        "record_type": "retroactive_standard_finalfinal_decision_records",
        "tracking_sheet": "GRB_Tracking / Sheet1",
        "tracking_sheet_url": "https://docs.google.com/spreadsheets/d/1pbgOMIJx_C9crSOtti6BJvAbXvTsWJv0fZXESgRCPf8",
        "snapshot_utc": args.snapshot_utc,
        "campaign_metadata_source": str(args.campaign_metadata),
        "dispatch_manifest_source": str(args.manifest),
        "events": records,
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    for path in (args.out, args.mirror_out):
        if path is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded)
        print(f"WROTE {path} ({len(records)} events)")


if __name__ == "__main__":
    main()
