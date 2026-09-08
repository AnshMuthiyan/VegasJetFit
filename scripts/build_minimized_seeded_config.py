#!/usr/bin/env python3
"""Build a config seeded at minimized values with width set by prior range."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_thesis_reproduction_model_toml import _load_toml, _write_toml

SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")
RESULT_KEY_ALIASES = {
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


def _entry_name(entry: dict[str, Any]) -> str | None:
    name = entry.get("name")
    return name if isinstance(name, str) else None


def _candidate_result_keys(section: str, name: str) -> list[str]:
    aliases = RESULT_KEY_ALIASES.get(section, {})
    keys = [name]
    for result_key, canonical in aliases.items():
        if canonical == name:
            keys.append(result_key)
    return keys


def _load_minimized_sections(path: Path) -> dict[str, dict[str, float]]:
    payload = json.loads(path.read_text())
    params = payload.get("params", {})
    if not isinstance(params, dict):
        raise ValueError(f"Expected params dict in minimized payload: {path}")

    out: dict[str, dict[str, float]] = {}
    for section in SECTION_ORDER:
        values = params.get(section, {})
        if not isinstance(values, dict):
            continue
        out[section] = {
            str(key): float(value)
            for key, value in values.items()
            if isinstance(value, (int, float)) and math.isfinite(float(value))
        }
    return out


def _linear_to_fit_space(value: float, scale: str) -> float | None:
    if not math.isfinite(value):
        return None
    if scale == "log":
        if value <= 0.0:
            return None
        return math.log10(value)
    return float(value)


def _bounded_seed(
    *,
    entry: dict[str, Any],
    section: str,
    minimized_sections: dict[str, dict[str, float]],
    seed_fraction: float,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    out = copy.deepcopy(entry)
    prior = out.get("prior")
    name = _entry_name(out)
    if name is None or not isinstance(prior, dict):
        return out, None
    if "lower" not in prior or "upper" not in prior:
        return out, None

    section_values = minimized_sections.get(section, {})
    seed_value = None
    for result_name in _candidate_result_keys(section, name):
        if result_name in section_values:
            seed_value = section_values[result_name]
            break
    if seed_value is None:
        return out, None

    fit_value = _linear_to_fit_space(seed_value, str(out.get("scale", "linear")))
    if fit_value is None:
        return out, None

    lower = float(prior["lower"])
    upper = float(prior["upper"])
    if not (math.isfinite(lower) and math.isfinite(upper) and upper > lower):
        return out, None

    fit_value = min(max(float(fit_value), lower), upper)
    initial_sigma = max(float(seed_fraction) * (upper - lower), 1e-12)

    old_guess = prior.get("initial_guess", "")
    old_sigma = prior.get("initial_sigma", "")
    prior["initial_guess"] = fit_value
    prior["initial_sigma"] = initial_sigma

    return out, {
        "section": section,
        "name": name,
        "scale": out.get("scale", ""),
        "seed_linear_value": seed_value,
        "initial_guess": fit_value,
        "initial_sigma": initial_sigma,
        "lower": lower,
        "upper": upper,
        "old_initial_guess": old_guess,
        "old_initial_sigma": old_sigma,
    }


def build_config(
    source_config: dict[str, Any],
    minimized_sections: dict[str, dict[str, float]],
    seed_fraction: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = copy.deepcopy(source_config)
    audits: list[dict[str, Any]] = []

    for section in SECTION_ORDER:
        entries = config.get(section)
        if not isinstance(entries, list):
            continue

        new_entries: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            updated, audit = _bounded_seed(
                entry=entry,
                section=section,
                minimized_sections=minimized_sections,
                seed_fraction=seed_fraction,
            )
            new_entries.append(updated)
            if audit is not None:
                audits.append(audit)
        config[section] = new_entries

    return config, audits


def write_audit(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "section",
        "name",
        "scale",
        "seed_linear_value",
        "initial_guess",
        "initial_sigma",
        "lower",
        "upper",
        "old_initial_guess",
        "old_initial_sigma",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--minimized-json", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--audit-csv", type=Path)
    parser.add_argument(
        "--seed-fraction",
        type=float,
        default=0.10,
        help="One-sided initial_sigma as a fraction of upper-lower for bounded priors.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.seed_fraction <= 0.0:
        raise SystemExit("--seed-fraction must be > 0")

    source = _load_toml(args.source_config)
    minimized = _load_minimized_sections(args.minimized_json)
    config, audits = build_config(source, minimized, args.seed_fraction)

    _write_toml(args.output_config, config)
    if args.audit_csv is not None:
        write_audit(args.audit_csv, audits)

    print(f"WROTE {args.output_config}")
    print(f"SEEDED_BOUNDED_PRIORS {len(audits)}")
    if args.audit_csv is not None:
        print(f"AUDIT {args.audit_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
