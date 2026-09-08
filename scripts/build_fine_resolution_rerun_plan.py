#!/usr/bin/env python3
"""Rank finer-resolution final-final reruns from measured campaign data."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path


FINE_RESOLUTION_ID = "fine"
MODERATE_RESOLUTION_ID = "campaign_moderate"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_launch_time(value: str) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def priority(delta: float) -> str:
    if delta >= 0.03:
        return "highest"
    if delta >= 0.01:
        return "high"
    if delta >= 0.005:
        return "moderate"
    return "low"


def build_rows(
    results_root: Path,
    manifest_path: Path,
    local_results_root: Path,
    continuation_burn: int,
    standard_burn: int,
    production: int,
) -> list[dict[str, object]]:
    manifest = {row["event"]: row for row in read_csv(manifest_path)}
    rows: list[dict[str, object]] = []

    for event_dir in sorted(path for path in results_root.iterdir() if path.is_dir()):
        event = event_dir.name
        levels = {row["resolution_id"]: row for row in read_csv(event_dir / "resolution_summary.csv")}
        moderate = levels[MODERATE_RESOLUTION_ID]
        fine = levels[FINE_RESOLUTION_ID]
        manifest_row = manifest[event]
        result_dir = local_results_root / f"{event}_{manifest_row['run_tag']}"
        chain_path = result_dir / "chain.npz"
        launch = parse_launch_time(manifest_row["launched_utc"])
        if not launch or not chain_path.is_file():
            raise RuntimeError(f"Missing launch time or completed chain for {event}")
        completed = datetime.fromtimestamp(chain_path.stat().st_mtime, tz=timezone.utc)
        moderate_hours = (completed - launch).total_seconds() / 3600.0
        cost_multiplier = float(fine["runtime_seconds"]) / float(moderate["runtime_seconds"])
        fine_same_protocol = moderate_hours * cost_multiplier
        continuation_fraction = (continuation_burn + production) / (standard_burn + production)
        rows.append(
            {
                "event": event,
                "priority": priority(float(moderate["max_abs_log10_flux_delta"])),
                "moderate_max_abs_log10_flux_delta": float(moderate["max_abs_log10_flux_delta"]),
                "moderate_mcmc_wall_hours": moderate_hours,
                "fine_to_moderate_model_cost_multiplier": cost_multiplier,
                "fine_same_protocol_wall_hours": fine_same_protocol,
                "fine_continuation_500burn_wall_hours": fine_same_protocol * continuation_fraction,
                "host": manifest_row["host"],
                "run_tag": manifest_row["run_tag"],
                "resolution": "fine=(0.20 phi/deg, 0.75 theta/deg, 20 time/log10 decade)",
            }
        )

    rows.sort(key=lambda row: float(row["moderate_max_abs_log10_flux_delta"]), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["priority_rank"] = rank
    return rows


def write_csv(rows: list[dict[str, object]], output: Path) -> None:
    fields = list(rows[0])
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, object]], output: Path, continuation_burn: int) -> None:
    lines = [
        "# Fine-Resolution Final-Final Rerun Priority",
        "",
        "This table is sorted by the observed moderate-resolution maximum absolute "
        "log-flux difference from the extreme-fine fixed-parameter reference. It uses "
        "the next coupled refinement, `(phi, theta, time) = (0.20, 0.75, 20)`, not a "
        "new likelihood or a changed posterior seed.",
        "",
        "The moderate MCMC wall clock is measured from the final-final manifest launch "
        "timestamp through `chain.npz` completion. The fine estimate multiplies that "
        "event's measured wall clock by the event's measured fixed-model fine/moderate "
        "runtime ratio. The continuation column assumes a conservative 500-step burn-in "
        f"with the complete existing posterior cloud, followed by the same 5,000-step production ({continuation_burn}+5000 versus 1000+5000).",
        "",
        "| Rank | Event | Priority | Moderate max delta (dex) | Measured moderate wall (h) | Fine/moderate cost | Fine, same 1000+5000 (h) | Fine, cloud continuation (h) | Original host |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {priority_rank} | {event} | {priority} | {moderate_max_abs_log10_flux_delta:.4f} | "
            "{moderate_mcmc_wall_hours:.1f} | {fine_to_moderate_model_cost_multiplier:.2f}x | "
            "{fine_same_protocol_wall_hours:.1f} | {fine_continuation_500burn_wall_hours:.1f} | {host} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Not Yet Rankable",
            "",
            "`220101A` and `090618` remain blocked behind their current final-seeded runs; "
            "`111228A` is held for scientific review; `140506A` and `080413B` have not "
            "completed their moderate final-final MCMCs. They need a completed, validated "
            "moderate result and fixed-parameter ladder before this evidence-based ranking "
            "can be extended to them.",
        ]
    )
    output.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--local-results-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--continuation-burn", type=int, default=500)
    parser.add_argument("--standard-burn", type=int, default=1000)
    parser.add_argument("--production", type=int, default=5000)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(
        args.results_root,
        args.manifest,
        args.local_results_root,
        args.continuation_burn,
        args.standard_burn,
        args.production,
    )
    write_csv(rows, args.output_dir / "fine_resolution_rerun_priority.csv")
    write_markdown(rows, args.output_dir / "FINE_RESOLUTION_RERUN_PRIORITY.md", args.continuation_burn)
    print(f"WROTE {args.output_dir}")


if __name__ == "__main__":
    main()
