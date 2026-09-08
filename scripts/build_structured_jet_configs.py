#!/usr/bin/env python3
"""Build structured-jet configs seeded from finished theta_c-free runs.

This preserves the existing medium model, prior boxes, nuisance terms, and
initial sigmas from the source configs, while recentering free parameters on a
finished minimized result and swapping the Python model wrapper to the
structured-jet campaign class.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

from build_thesis_reproduction_model_toml import _load_toml, _write_toml
from build_thetacfree_powerlaw_configs import (
    CONFIG_SECTION_ORDER,
    _entry_name,
    load_minimized_sections,
    render_name,
    resolve_results_dir,
    seed_prior_entry,
    valid_minimized_payload,
    write_audit_csv,
)
from thesis_reproduction_data import normalize_event_name


def _fixed_numeric_entry(name: str, value: float) -> dict[str, Any]:
    return {
        "name": name,
        "scale": "linear",
        "value": float(value),
    }


def _existing_seed_value(entry: dict[str, Any]) -> Any:
    if "value" in entry:
        return entry.get("value")
    prior = entry.get("prior")
    if isinstance(prior, dict):
        return prior.get("initial_guess", "")
    return ""


def _upsert_fixed_entries(
    entries: list[dict[str, Any]],
    fixed_values: dict[str, float],
    audits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in entries:
        name = _entry_name(entry)
        if name is None or name not in fixed_values:
            out.append(entry)
            continue

        seen.add(name)
        out.append(_fixed_numeric_entry(name, fixed_values[name]))
        audits.append(
            {
                "section": "model",
                "name": name,
                "old_initial_guess": _existing_seed_value(entry),
                "new_initial_guess": fixed_values[name],
                "seed_linear_value": fixed_values[name],
            }
        )

    for name, value in fixed_values.items():
        if name in seen:
            continue
        out.append(_fixed_numeric_entry(name, value))
        audits.append(
            {
                "section": "model",
                "name": name,
                "old_initial_guess": "",
                "new_initial_guess": value,
                "seed_linear_value": value,
            }
        )

    return out


def build_config(
    *,
    source: dict[str, Any],
    seeded_sections: dict[str, dict[str, float]],
    model_name: str,
    fixed_model_values: dict[str, float],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = copy.deepcopy(source)
    config["name"] = model_name
    audits: list[dict[str, Any]] = []

    for section in CONFIG_SECTION_ORDER:
        entries = config.get(section, [])
        if not isinstance(entries, list):
            continue

        new_entries: list[dict[str, Any]] = []
        seeded_values = seeded_sections.get(section, {})

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            updated, audit = seed_prior_entry(
                section=section,
                entry=entry,
                seeded_values=seeded_values,
            )
            new_entries.append(updated)
            if audit is not None:
                audits.append(audit)

        if section == "model":
            new_entries = _upsert_fixed_entries(new_entries, fixed_model_values, audits)

        config[section] = new_entries

    return config, audits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vegas-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="VegasJetFit root.",
    )
    parser.add_argument(
        "--source-config-dir",
        type=Path,
        required=True,
        help="Directory containing the current source configs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write the structured-jet configs into.",
    )
    parser.add_argument(
        "--source-run-tag",
        required=True,
        help="Finished source run tag used for minimized seed files.",
    )
    parser.add_argument(
        "--results-name-template",
        required=True,
        help="Template used to locate the finished source results.",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "jetfit" / "results",
        help="Local results root.",
    )
    parser.add_argument("--drive-root", type=Path, help="Optional synced Drive root fallback.")
    parser.add_argument(
        "--owner-subdir",
        default="jkeohane",
        help="Owner subdirectory under the synced Drive root.",
    )
    parser.add_argument("--events", nargs="+", required=True, help="Event list to build.")
    parser.add_argument("--audit-csv", type=Path, help="Optional audit CSV output.")
    parser.add_argument(
        "--model-name",
        required=True,
        help="Top-level model name to write into the output TOMLs.",
    )
    parser.add_argument("--fixed-k-e", type=float, default=2.0, help="Fixed structured-jet k_e.")
    parser.add_argument("--fixed-k-g", type=float, default=2.0, help="Fixed structured-jet k_g.")
    parser.add_argument(
        "--fixed-s",
        type=float,
        default=4.0,
        help="Compatibility-only structured-jet s value recorded in the TOMLs.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_audits: list[dict[str, Any]] = []
    fixed_model_values = {
        "k_e": float(args.fixed_k_e),
        "k_g": float(args.fixed_k_g),
        "s": float(args.fixed_s),
    }

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
        config, audits = build_config(
            source=source,
            seeded_sections=seeded_sections,
            model_name=args.model_name,
            fixed_model_values=fixed_model_values,
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
