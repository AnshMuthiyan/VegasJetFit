#!/usr/bin/env python3
"""Build Campaign A configs by thawing theta_v in recent structured-jet runs.

This starts from completed result `model.toml` files so all current priors,
seed centers, nuisance terms, and fixed jet parameters are preserved. The only
intentional change is converting `theta_v` from a fixed value to a free prior.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

from build_thesis_reproduction_model_toml import _load_toml, _write_toml


def render_name(template: str, event: str, run_tag: str) -> str:
    out = template.replace("{event}", event)
    out = out.replace("{run_tag}", run_tag)
    return out


def find_model_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    model = config.get("model", [])
    if not isinstance(model, list):
        raise SystemExit("Config missing [[model]] list.")
    return model


def find_named_entry(entries: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name") == name:
            return entry
    return None


def thaw_theta_v(config: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(config)
    entries = find_model_entries(out)
    theta_c = find_named_entry(entries, "theta_c")
    theta_v = find_named_entry(entries, "theta_v")
    if theta_v is None:
        raise SystemExit("Config missing theta_v entry.")
    if theta_c is None:
        raise SystemExit("Config missing theta_c entry.")

    theta_c_prior = theta_c.get("prior", {})
    if not isinstance(theta_c_prior, dict):
        raise SystemExit("theta_c entry missing prior block.")

    upper = float(theta_c_prior.get("upper", 1.0))
    sigma = float(theta_c_prior.get("initial_sigma", 0.05))
    current_value = theta_v.get("value", 0.0)
    try:
        initial_guess = float(current_value)
    except Exception:
        initial_guess = 0.0

    theta_v.pop("value", None)
    theta_v["scale"] = "linear"
    theta_v["prior"] = {
        "type": "uniform",
        "lower": 0.0,
        "upper": upper,
        "initial_guess": initial_guess,
        "initial_sigma": sigma,
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "jetfit" / "results",
        help="Local JetFit results root.",
    )
    parser.add_argument(
        "--source-run-tag",
        required=True,
        help="Run tag whose result model.toml files will be used as the source.",
    )
    parser.add_argument(
        "--results-name-template",
        default="{event}_{run_tag}",
        help="Template used to locate source result directories.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where thawed configs will be written.",
    )
    parser.add_argument(
        "--events",
        nargs="+",
        required=True,
        help="Event names to build.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for event in args.events:
        results_name = render_name(args.results_name_template, event, args.source_run_tag)
        source_model = args.results_root / results_name / "model.toml"
        if not source_model.exists():
            raise SystemExit(f"Missing source model TOML: {source_model}")

        config = _load_toml(source_model)
        thawed = thaw_theta_v(config)
        output_path = args.output_dir / f"{event}.toml"
        _write_toml(output_path, thawed)
        print(f"WROTE {event}: {output_path}")


if __name__ == "__main__":
    main()
