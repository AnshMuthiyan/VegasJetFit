#!/usr/bin/env python3
"""
Build an empirical-bubble TOML seeded from a finished simple-bubble fit.

This keeps the original prior boxes and initial sigma values from the source
config, swaps the runtime model to the empirical-bubble Dylan-spectrum wrapper,
and rewrites initial guesses from a best_fit.json payload.
"""

from __future__ import annotations

import argparse
import json
import math
import tomllib
from pathlib import Path
from typing import Any


SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")


def _fmt_value(value: Any) -> str:
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    return repr(value)


def _write_toml(path: Path, data: dict[str, Any]) -> None:
    lines: list[str] = []
    if "name" in data:
        lines.append(f"name = {_fmt_value(data['name'])}")
        lines.append("")

    for section in SECTION_ORDER:
        entries = data.get(section, [])
        if not entries:
            continue

        for entry in entries:
            lines.append(f"[[{section}]]")
            for key, value in entry.items():
                if key == "prior":
                    continue
                lines.append(f"{key} = {_fmt_value(value)}")

            prior = entry.get("prior")
            if isinstance(prior, dict):
                lines.append("")
                lines.append(f"[{section}.prior]")
                for p_key, p_value in prior.items():
                    lines.append(f"{p_key} = {_fmt_value(p_value)}")

            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n")


def _flatten_best_fit(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text())
    flat: dict[str, float] = {}

    for section in SECTION_ORDER:
        values = payload.get(section, {})
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if isinstance(value, (int, float)):
                flat[str(key)] = float(value)

    for key, value in payload.items():
        if isinstance(value, (int, float)):
            flat[str(key)] = float(value)

    return flat


def _scaled_guess(entry: dict[str, Any], value: float) -> float | None:
    scale = str(entry.get("scale", "linear")).lower()
    if scale == "log":
        if value <= 0.0:
            return None
        guess = math.log10(value)
    else:
        guess = float(value)

    prior = entry.get("prior")
    if isinstance(prior, dict):
        lower = prior.get("lower")
        upper = prior.get("upper")
        if isinstance(lower, (int, float)):
            guess = max(float(lower), guess)
        if isinstance(upper, (int, float)):
            guess = min(float(upper), guess)

    return guess


def build_seeded_config(
    *,
    input_config: Path,
    best_fit: Path,
    output: Path,
    model_name: str,
) -> None:
    config = tomllib.loads(input_config.read_text())
    flat = _flatten_best_fit(best_fit)

    config["name"] = model_name

    for section in SECTION_ORDER:
        entries = config.get(section, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if "value" in entry:
                continue
            prior = entry.get("prior")
            if not isinstance(prior, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or name not in flat:
                continue
            guess = _scaled_guess(entry, flat[name])
            if guess is None:
                continue
            prior["initial_guess"] = guess

    _write_toml(output, config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an empirical-bubble TOML from a finished bubble fit.")
    parser.add_argument("--input-config", required=True, help="Existing bubble TOML to clone priors/sigmas from.")
    parser.add_argument("--best-fit", required=True, help="best_fit.json used for seed centers.")
    parser.add_argument("--output", required=True, help="Output empirical-bubble TOML path.")
    parser.add_argument(
        "--model-name",
        default="EmpiricalBubbleVegasDylanSpectrumModel",
        help="Model name to write into the TOML.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_seeded_config(
        input_config=Path(args.input_config).expanduser().resolve(),
        best_fit=Path(args.best_fit).expanduser().resolve(),
        output=Path(args.output).expanduser().resolve(),
        model_name=str(args.model_name),
    )


if __name__ == "__main__":
    main()
