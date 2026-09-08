#!/usr/bin/env python3
"""Build wide top-hat SBPL configs seeded at Dylan thesis medians."""

from __future__ import annotations

import argparse
import copy
import csv
from pathlib import Path
from typing import Any

from build_thesis_reproduction_model_toml import _load_toml, _write_toml
from thesis_reproduction_data import THESIS, normalize_event_name

DEFAULT_EVENTS = ("080319B", "080413B")
SEED_MAP = {
    "E52": "E52",
    "lf0": "lf0",
    "nt": "nt",
    "rt": "rt",
    "eps_e": "eps_e",
    "eps_B": "eps_b",
    "p": "p",
    "k1": "kpre",
    "k2": "kpost",
    "sn": "sn",
}
EXT_SEED_MAP = {"ebv_source_frame": "ebv_source_frame"}
SLOP_SEED_MAP = {"slop": "slop"}


def parse_args() -> argparse.Namespace:
    root = Path("/Users/jkeohane/GRBs")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", nargs="+", default=list(DEFAULT_EVENTS))
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=root / "VegasJetFit" / "sbpl_unseeded_tophat_configs_active",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "VegasJetFit" / "sbpl_tophat_theta1p0_dylanthesis_seeded_configs_active",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=root / "VegasJetFit" / "sbpl_tophat_theta1p0_dylanthesis_seeded_configs_v1",
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=root
        / "VegasJetFit"
        / "reports"
        / "sbpl_tophat_theta1p0_dylanthesis_seeded"
        / "seed_audit.csv",
    )
    parser.add_argument("--initial-sigma-fraction", type=float, default=0.05)
    return parser.parse_args()


def _ensure_prior_contains_seed(prior: dict[str, Any], seed: float) -> tuple[float, float, bool]:
    lower = float(prior["lower"])
    upper = float(prior["upper"])
    expanded = False
    if seed < lower:
        lower = seed
        expanded = True
    if seed > upper:
        upper = seed
        expanded = True
    prior["lower"] = lower
    prior["upper"] = upper
    return lower, upper, expanded


def add_seed(
    entry: dict[str, Any],
    thesis_key: str,
    thesis: dict[str, Any],
    event: str,
    rows: list[dict[str, Any]],
    section: str,
    initial_sigma_fraction: float,
) -> None:
    prior = entry.get("prior")
    if not isinstance(prior, dict):
        raise ValueError(f"{event} {section}.{entry.get('name')} has no prior")
    median = float(thesis[thesis_key][0])
    lower, upper, expanded = _ensure_prior_contains_seed(prior, median)
    sigma = max(initial_sigma_fraction * (upper - lower), 1e-8)
    prior["initial_guess"] = median
    prior["initial_sigma"] = sigma
    rows.append(
        {
            "event": event,
            "section": section,
            "parameter": entry["name"],
            "thesis_key": thesis_key,
            "thesis_median": median,
            "prior_lower": lower,
            "prior_upper": upper,
            "initial_guess": median,
            "initial_sigma": sigma,
            "prior_expanded_to_include_seed": expanded,
        }
    )


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.snapshot_dir.mkdir(parents=True, exist_ok=True)
    args.audit_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for raw_event in args.events:
        event = normalize_event_name(raw_event)
        thesis = THESIS[event]
        if thesis["model"] != "SBPL":
            raise ValueError(f"{event} thesis model is not SBPL")
        data = copy.deepcopy(_load_toml(args.source_dir / f"{event}.toml"))

        for entry in data.get("model", []):
            name = entry.get("name")
            if name in SEED_MAP:
                add_seed(
                    entry,
                    SEED_MAP[name],
                    thesis,
                    event,
                    rows,
                    "model",
                    args.initial_sigma_fraction,
                )
            if name == "theta_c":
                entry.pop("prior", None)
                entry["value"] = 1.0
            if name == "theta_v":
                entry.pop("prior", None)
                entry["value"] = 0.0

        for entry in data.get("extinction", []):
            name = entry.get("name")
            if name in EXT_SEED_MAP:
                add_seed(
                    entry,
                    EXT_SEED_MAP[name],
                    thesis,
                    event,
                    rows,
                    "extinction",
                    args.initial_sigma_fraction,
                )

        for entry in data.get("slop", []):
            name = entry.get("name")
            if name in SLOP_SEED_MAP:
                add_seed(
                    entry,
                    SLOP_SEED_MAP[name],
                    thesis,
                    event,
                    rows,
                    "slop",
                    args.initial_sigma_fraction,
                )

        for dest in (args.output_dir / f"{event}.toml", args.snapshot_dir / f"{event}.toml"):
            _write_toml(dest, data)

    fieldnames = [
        "event",
        "section",
        "parameter",
        "thesis_key",
        "thesis_median",
        "prior_lower",
        "prior_upper",
        "initial_guess",
        "initial_sigma",
        "prior_expanded_to_include_seed",
    ]
    with args.audit_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {args.output_dir}")
    print(f"wrote {args.snapshot_dir}")
    print(f"wrote {args.audit_csv}")


if __name__ == "__main__":
    main()
