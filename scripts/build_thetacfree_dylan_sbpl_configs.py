#!/usr/bin/env python3
"""Build theta_c-free SBPL configs seeded from a finished fixed-theta campaign.

This keeps the current Dylan SBPL config family intact:
- preserve all existing priors, bounds, and initial sigmas from the source config
- recenter all existing fitted parameters on a finished minimized result
- thaw theta_c using the shared jetsim prior box

The intended source configs are the current fixed-theta SBPL configs such as
`dylan_sbpl_configs_init5pct_active/*.toml`, and the intended seed results are
the matching finished minimized outputs from the fixed-theta SBPL campaign.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from build_thesis_reproduction_model_toml import _load_toml, _write_toml
from build_thetacfree_powerlaw_configs import (
    build_config,
    load_minimized_sections,
    render_name,
    resolve_results_dir,
    theta_c_prior_for_event,
    valid_minimized_payload,
    write_audit_csv,
)
from thesis_reproduction_data import normalize_event_name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vegas-dir", type=Path, default=Path(__file__).resolve().parents[1], help="VegasJetFit root.")
    parser.add_argument("--source-config-dir", type=Path, required=True, help="Directory containing the current fixed-theta SBPL configs.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to write the theta_c-free SBPL configs into.")
    parser.add_argument("--source-run-tag", required=True, help="Finished fixed-theta SBPL run tag used for seed minimized.json files.")
    parser.add_argument(
        "--results-name-template",
        default="{event}_{run_tag}",
        help="Template used to locate the finished fixed-theta SBPL results.",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "jetfit" / "results",
        help="Local results root.",
    )
    parser.add_argument("--drive-root", type=Path, help="Optional synced Drive root fallback.")
    parser.add_argument("--owner-subdir", default="jkeohane", help="Owner subdirectory under the synced Drive root.")
    parser.add_argument("--events", nargs="+", required=True, help="Event list to build.")
    parser.add_argument("--audit-csv", type=Path, help="Optional audit CSV output.")
    parser.add_argument(
        "--theta-c-initial-sigma",
        type=float,
        default=0.05,
        help="Initial sigma used for the thawed theta_c prior.",
    )
    parser.add_argument(
        "--theta-c-lower-floor",
        type=float,
        default=1e-3,
        help="Practical positivity floor applied to theta_c lower bounds.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_audits: list[dict[str, object]] = []

    for raw_event in args.events:
        event = normalize_event_name(raw_event)
        source_path = args.source_config_dir / f"{event}.toml"
        if not source_path.exists():
            raise SystemExit(f"Missing source config for {event}: {source_path}")

        results_name = render_name(args.results_name_template, event, args.source_run_tag)
        results_dir = resolve_results_dir(
            event=event,
            results_name=results_name,
            results_root=args.results_root,
            drive_root=args.drive_root,
            owner_subdir=args.owner_subdir,
        )
        minimized_path = results_dir / "minimized" / "minimized.json"
        if not valid_minimized_payload(minimized_path):
            raise SystemExit(f"Missing or invalid minimized seed for {event}: {minimized_path}")

        source = _load_toml(source_path)
        seeded_sections = load_minimized_sections(minimized_path)
        theta_c_prior = theta_c_prior_for_event(
            vegas_dir=args.vegas_dir,
            event=event,
            lower_floor=args.theta_c_lower_floor,
        )
        config, audits = build_config(
            source=source,
            seeded_sections=seeded_sections,
            theta_c_prior=theta_c_prior,
            theta_c_initial_sigma=args.theta_c_initial_sigma,
        )

        output_path = args.output_dir / f"{event}.toml"
        _write_toml(output_path, config)
        print(f"WROTE {event}: {output_path}")

        for audit in audits:
            audit["event"] = event
            all_audits.append(audit)

    if args.audit_csv is not None:
        write_audit_csv(args.audit_csv, all_audits)
        print(f"AUDIT {args.audit_csv}")


if __name__ == "__main__":
    main()
