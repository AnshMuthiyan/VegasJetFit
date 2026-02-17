#!/usr/bin/env python3
"""
Build a bubble-model TOML that is apples-to-apples with a powerlaw TOML.

Rules:
- Keep BubbleVegas model name.
- In [model], replace any bubble entry whose name also exists in powerlaw
  with the powerlaw definition (shared priors/values).
- Keep bubble-only medium entries (e.g., nt, nism, rt) from bubble template.
- Copy extinction/offsets/host/slop categories from powerlaw so nuisance
  settings match across runs.
"""

from __future__ import annotations

import argparse
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


def _entry_name(entry: dict[str, Any]) -> str | None:
    name = entry.get("name")
    return name if isinstance(name, str) else None


def _by_name(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = _entry_name(entry)
        if name is not None:
            out[name] = entry
    return out


def build_synced_bubble(powerlaw: dict[str, Any], bubble: dict[str, Any]) -> dict[str, Any]:
    synced: dict[str, Any] = {}
    synced["name"] = bubble.get("name", "BubbleVegasModel")

    powerlaw_model = powerlaw.get("model", [])
    bubble_model = bubble.get("model", [])
    powerlaw_model_by_name = _by_name(powerlaw_model)

    merged_model: list[dict[str, Any]] = []
    for entry in bubble_model:
        name = _entry_name(entry)
        if name is not None and name in powerlaw_model_by_name:
            merged_model.append(powerlaw_model_by_name[name])
        else:
            merged_model.append(entry)
    synced["model"] = merged_model

    for section in ("extinction", "offsets", "host", "slop"):
        if section in powerlaw:
            synced[section] = powerlaw[section]
        elif section in bubble:
            synced[section] = bubble[section]

    return synced


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync bubble TOML against powerlaw TOML")
    parser.add_argument("--powerlaw", required=True, help="Path to powerlaw model TOML")
    parser.add_argument("--bubble", required=True, help="Path to bubble model TOML")
    parser.add_argument("--output", required=True, help="Output path for synced bubble TOML")
    args = parser.parse_args()

    powerlaw_path = Path(args.powerlaw)
    bubble_path = Path(args.bubble)
    output_path = Path(args.output)

    powerlaw_data = tomllib.loads(powerlaw_path.read_text())
    bubble_data = tomllib.loads(bubble_path.read_text())

    synced = build_synced_bubble(powerlaw_data, bubble_data)
    _write_toml(output_path, synced)

    shared = sorted(set(_by_name(powerlaw_data.get("model", [])).keys()) &
                    set(_by_name(bubble_data.get("model", [])).keys()))
    print(f"Wrote synced bubble config: {output_path}")
    print(f"Shared model params synced from powerlaw: {', '.join(shared)}")


if __name__ == "__main__":
    main()
