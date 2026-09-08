#!/usr/bin/env python3
"""Build theta_c-free PL configs seeded from a finished fixed-theta campaign.

This keeps the current power-law Dylan-smoothed config family intact:
- preserve all existing priors, bounds, and initial sigmas from the source config
- recenter all existing fitted parameters on a finished minimized result
- thaw theta_c using the shared jetsim prior box

The intended source configs are the current fixed-theta wide-jet configs such as
`thesis_reproduction_configs_dylanphyspriors_init5pct_active/*.toml`, and the
intended seed results are the matching finished minimized outputs from the
fixed-theta campaign.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from pathlib import Path
from typing import Any

from build_thesis_reproduction_model_toml import _load_toml, _write_toml
from thesis_reproduction_data import normalize_event_name


RESULT_SECTION_ORDER = ("model", "extinction", "host", "offsets", "slop")
CONFIG_SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")

SECTION_KEY_ALIASES = {
    "model": {
        "dL28": "dl28",
        "dL": "dl28",
        "dl": "dl28",
        "eps_B": "eps_b",
    },
    "extinction": {},
    "offsets": {},
    "host": {},
    "slop": {},
}

DEFAULT_THETA_C_PRIOR = {
    "type": "uniform",
    "lower": 0.0,
    "upper": 1.0,
}


def _entry_name(entry: dict[str, Any]) -> str | None:
    value = entry.get("name")
    return value if isinstance(value, str) else None


def _canonical_key(section: str, name: str) -> str:
    return SECTION_KEY_ALIASES.get(section, {}).get(name, name)


def load_minimized_sections(path: Path) -> dict[str, dict[str, float]]:
    payload = json.loads(path.read_text())
    params = payload.get("params", {})
    if not isinstance(params, dict):
        raise ValueError(f"Expected params dict in minimized payload: {path}")

    out: dict[str, dict[str, float]] = {}
    for section in RESULT_SECTION_ORDER:
        values = params.get(section, {})
        if not isinstance(values, dict):
            continue
        mapped: dict[str, float] = {}
        for raw_key, raw_value in values.items():
            if not isinstance(raw_value, (int, float)):
                continue
            mapped[_canonical_key(section, str(raw_key))] = float(raw_value)
        out[section] = mapped
    return out


def valid_minimized_payload(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return False
    success = payload.get("success")
    nmap = payload.get("nmap")
    return success is True and isinstance(nmap, (int, float)) and math.isfinite(float(nmap))


def convert_linear_to_fit(value: float, scale: str) -> float | None:
    if not math.isfinite(value):
        return None
    if scale == "log":
        if value <= 0.0:
            return None
        return float(math.log10(value))
    return float(value)


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def interiorize(value: float, lower: float, upper: float, sigma: float) -> float:
    """Move a seed slightly off a hard boundary when possible."""
    margin = max(float(sigma), 1e-6)
    inner_lower = lower + margin
    inner_upper = upper - margin
    if inner_lower <= inner_upper:
        return clamp(value, inner_lower, inner_upper)
    return clamp(value, lower, upper)


def theta_c_prior_for_event(
    *,
    vegas_dir: Path,
    event: str,
    lower_floor: float,
) -> dict[str, float | str]:
    jetsim_path = vegas_dir / "jetfit" / "resources" / "jetsim" / event / "jetsim.toml"
    if jetsim_path.exists():
        jetsim = _load_toml(jetsim_path)
        for entry in jetsim.get("model", []):
            if not isinstance(entry, dict):
                continue
            if _entry_name(entry) != "theta_c":
                continue
            prior = entry.get("prior")
            if isinstance(prior, dict) and "lower" in prior and "upper" in prior:
                out = copy.deepcopy(prior)
                out["lower"] = max(float(out["lower"]), lower_floor)
                out["upper"] = float(out["upper"])
                return out

    out = copy.deepcopy(DEFAULT_THETA_C_PRIOR)
    out["lower"] = max(float(out["lower"]), lower_floor)
    out["upper"] = float(out["upper"])
    return out


def resolve_results_dir(
    *,
    event: str,
    results_name: str,
    results_root: Path,
    drive_root: Path | None,
    owner_subdir: str,
) -> Path:
    local_dir = results_root / results_name
    local_required = (
        local_dir / "minimized" / "minimized.json",
        local_dir / "best_fit.json",
    )
    if all(path.exists() for path in local_required):
        return local_dir

    if drive_root is not None:
        share_dir = drive_root / event / owner_subdir / results_name
        share_required = (
            share_dir / "minimized" / "minimized.json",
            share_dir / "best_fit.json",
        )
        if all(path.exists() for path in share_required):
            return share_dir

    return local_dir


def render_name(template: str, event: str, run_tag: str) -> str:
    out = template.replace("{event}", event)
    out = out.replace("{run_tag}", run_tag)
    return out


def seed_prior_entry(
    *,
    section: str,
    entry: dict[str, Any],
    seeded_values: dict[str, float],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    out = copy.deepcopy(entry)
    prior = out.get("prior")
    name = _entry_name(out)
    if name is None or not isinstance(prior, dict):
        return out, None

    canonical = _canonical_key(section, name)
    if canonical not in seeded_values:
        return out, None

    fit_value = convert_linear_to_fit(seeded_values[canonical], str(out.get("scale", "linear")))
    if fit_value is None:
        return out, None

    lower = prior.get("lower")
    upper = prior.get("upper")
    old_guess = prior.get("initial_guess", "")
    if isinstance(lower, (int, float)) and isinstance(upper, (int, float)):
        fit_value = clamp(float(fit_value), float(lower), float(upper))

    prior["initial_guess"] = float(fit_value)
    audit = {
        "section": section,
        "name": name,
        "old_initial_guess": old_guess,
        "new_initial_guess": prior["initial_guess"],
        "seed_linear_value": seeded_values[canonical],
    }
    return out, audit


def thaw_theta_c_entry(
    *,
    current_entry: dict[str, Any],
    theta_c_seed: float,
    theta_c_prior: dict[str, float | str],
    theta_c_initial_sigma: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    lower = float(theta_c_prior["lower"])
    upper = float(theta_c_prior["upper"])
    initial_sigma = max(float(theta_c_initial_sigma), 1e-6)
    seed = interiorize(float(theta_c_seed), lower, upper, initial_sigma)

    out = {
        "name": "theta_c",
        "scale": "linear",
        "prior": {
            "type": theta_c_prior.get("type", "uniform"),
            "lower": lower,
            "upper": upper,
            "initial_guess": seed,
            "initial_sigma": initial_sigma,
        },
    }
    audit = {
        "section": "model",
        "name": "theta_c",
        "old_initial_guess": current_entry.get("value", ""),
        "new_initial_guess": seed,
        "seed_linear_value": theta_c_seed,
        "lower": lower,
        "upper": upper,
        "initial_sigma": initial_sigma,
    }
    return out, audit


def build_config(
    *,
    source: dict[str, Any],
    seeded_sections: dict[str, dict[str, float]],
    theta_c_prior: dict[str, float | str],
    theta_c_initial_sigma: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = copy.deepcopy(source)
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

            name = _entry_name(entry)
            if section == "model" and name == "theta_c":
                theta_c_seed = seeded_values.get("theta_c")
                if theta_c_seed is None:
                    theta_c_seed = float(entry.get("value", 1.0))
                thawed, audit = thaw_theta_c_entry(
                    current_entry=entry,
                    theta_c_seed=theta_c_seed,
                    theta_c_prior=theta_c_prior,
                    theta_c_initial_sigma=theta_c_initial_sigma,
                )
                new_entries.append(thawed)
                audits.append(audit)
                continue

            updated, audit = seed_prior_entry(
                section=section,
                entry=entry,
                seeded_values=seeded_values,
            )
            new_entries.append(updated)
            if audit is not None:
                audits.append(audit)

        config[section] = new_entries

    return config, audits


def write_audit_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "event",
        "section",
        "name",
        "old_initial_guess",
        "new_initial_guess",
        "seed_linear_value",
        "lower",
        "upper",
        "initial_sigma",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vegas-dir", type=Path, default=Path(__file__).resolve().parents[1], help="VegasJetFit root.")
    parser.add_argument("--source-config-dir", type=Path, required=True, help="Directory containing the current fixed-theta configs.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to write the theta_c-free configs into.")
    parser.add_argument("--source-run-tag", required=True, help="Finished fixed-theta run tag used for seed minimized.json files.")
    parser.add_argument(
        "--results-name-template",
        default="{event}_thesis_reproduction_{run_tag}",
        help="Template used to locate the finished fixed-theta results.",
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
    all_audits: list[dict[str, Any]] = []

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
