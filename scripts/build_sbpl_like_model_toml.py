#!/usr/bin/env python3
"""Build a StratifiedFireballModel TOML from an existing single-k event config."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
import tomllib


MODEL_ORDER = (
    "E52",
    "lf0",
    "n0t",
    "rt",
    "eps_e",
    "eps_b",
    "p",
    "k1",
    "k2",
    "sni",
    "hmf",
    "tj",
    "sj",
    "sji",
    "z",
    "dL28",
)

MODEL_NAME_MAP = {
    "dL28": "dL28",
    "dl28": "dL28",
    "eps_B": "eps_b",
    "eps_b": "eps_b",
    "n017": "n0t",
    "n0t": "n0t",
    "k": "k1",
}

PRIOR_KEY_ORDER = (
    "type",
    "lower",
    "upper",
    "mu",
    "sigma",
    "initial_guess",
    "initial_sigma",
)

# These parameters are stored in the model/best-fit JSON as linear physical
# values, but the SBPL TOMLs in this repo fit them on a linear-in-log10 basis
# (e.g. rt prior 15..20 means log10(cm), not cm).
LOG10_LINEAR_INITIAL_GUESS_NAMES = {"n0t", "rt"}


def canonical_name(name: str) -> str:
    return MODEL_NAME_MAP.get(name, name)


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_best_fit(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    model = payload.get("model", {})
    if not isinstance(model, dict):
        return {}
    return {canonical_name(str(k)): float(v) for k, v in model.items()}


def clone_block(block: dict[str, Any], *, new_name: str | None = None) -> dict[str, Any]:
    out = dict(block)
    if new_name is not None:
        out["name"] = new_name
    if "prior" in block:
        out["prior"] = dict(block["prior"])
    return out


def set_initial_guess(block: dict[str, Any], value: float) -> None:
    if "value" in block:
        return
    prior = block.setdefault("prior", {})
    if block.get("name") in LOG10_LINEAR_INITIAL_GUESS_NAMES:
        if value <= 0:
            return
        prior["initial_guess"] = math.log10(value)
    elif block.get("scale") == "log":
        if value <= 0:
            return
        prior["initial_guess"] = math.log10(value)
    else:
        prior["initial_guess"] = value


def make_block(
    name: str,
    *,
    scale: str,
    lower: float,
    upper: float,
    initial_guess: float | None = None,
    initial_sigma: float | None = None,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "name": name,
        "scale": scale,
        "prior": {
            "type": "uniform",
            "lower": lower,
            "upper": upper,
        },
    }
    if initial_guess is not None:
        block["prior"]["initial_guess"] = initial_guess
    if initial_sigma is not None:
        block["prior"]["initial_sigma"] = initial_sigma
    return block


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    return repr(value)


def emit_table_array(lines: list[str], section: str, blocks: list[dict[str, Any]]) -> None:
    for block in blocks:
        lines.append(f"[[{section}]]")
        top_keys = []
        if "name" in block:
            top_keys.append("name")
        if "scale" in block:
            top_keys.append("scale")
        if "value" in block:
            top_keys.append("value")
        for key in block:
            if key not in top_keys and key != "prior":
                top_keys.append(key)
        for key in top_keys:
            lines.append(f"{key} = {format_value(block[key])}")
        prior = block.get("prior")
        if prior:
            lines.append("")
            lines.append(f"[{section}.prior]")
            for key in PRIOR_KEY_ORDER:
                if key in prior:
                    lines.append(f"{key} = {format_value(prior[key])}")
            for key, value in prior.items():
                if key not in PRIOR_KEY_ORDER:
                    lines.append(f"{key} = {format_value(value)}")
        lines.append("")


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Source event parameters TOML.")
    parser.add_argument("--output", required=True, type=Path, help="Output StratifiedFireballModel TOML.")
    parser.add_argument(
        "--seed-best-fit",
        type=Path,
        default=None,
        help="Optional best_fit.json used to seed initial guesses.",
    )
    parser.add_argument("--k2-initial", type=float, default=1.0)
    parser.add_argument("--k2-lower", type=float, default=-3.0)
    parser.add_argument("--k2-upper", type=float, default=3.0)
    parser.add_argument("--k1-initial", type=float, default=0.0)
    parser.add_argument("--k1-lower", type=float, default=-10.0)
    parser.add_argument("--k1-upper", type=float, default=3.0)
    parser.add_argument("--rt-initial", type=float, default=17.0)
    parser.add_argument("--rt-lower", type=float, default=15.0)
    parser.add_argument("--rt-upper", type=float, default=20.0)
    parser.add_argument("--sni-initial", type=float, default=-0.5)
    parser.add_argument("--sni-lower", type=float, default=-1.0)
    parser.add_argument("--sni-upper", type=float, default=-0.1)
    parser.add_argument(
        "--initial-sigma-scale",
        type=float,
        default=1.0,
        help="Multiply all existing prior.initial_sigma values by this factor.",
    )
    return parser.parse_args()


def main() -> int:
    args = build_args()
    source = load_toml(args.source)
    best_fit = load_best_fit(args.seed_best_fit)

    model_blocks = source.get("model", [])
    if not isinstance(model_blocks, list):
        raise SystemExit(f"Expected [[model]] array in {args.source}")

    source_by_name: dict[str, dict[str, Any]] = {}
    for block in model_blocks:
        if not isinstance(block, dict) or "name" not in block:
            continue
        source_by_name[canonical_name(str(block["name"]))] = block

    out_models: list[dict[str, Any]] = []

    for wanted in MODEL_ORDER:
        if wanted == "rt":
            source_block = source_by_name.get("rt")
            if source_block is not None:
                block = clone_block(source_block, new_name="rt")
            else:
                block = make_block(
                    "rt",
                    scale="log",
                    lower=args.rt_lower,
                    upper=args.rt_upper,
                    initial_guess=args.rt_initial,
                    initial_sigma=0.5,
                )
            # StratifiedFireballModel expects rt to be sampled in log10 space.
            block["scale"] = "log"
            out_models.append(block)
            continue

        if wanted == "k2":
            source_block = source_by_name.get("k2")
            if source_block is not None:
                block = clone_block(source_block, new_name="k2")
            else:
                block = make_block(
                    "k2",
                    scale="linear",
                    lower=args.k2_lower,
                    upper=args.k2_upper,
                    initial_guess=args.k2_initial,
                    initial_sigma=0.5,
                )
            out_models.append(block)
            continue

        if wanted == "k1":
            source_block = source_by_name.get("k1")
            if source_block is not None:
                block = clone_block(source_block, new_name="k1")
                block.pop("value", None)
                prior = block.setdefault("prior", {})
                prior["type"] = "uniform"
                prior["lower"] = args.k1_lower
                prior["upper"] = args.k1_upper
                if "initial_sigma" not in prior:
                    prior["initial_sigma"] = 0.25
            else:
                block = make_block(
                    "k1",
                    scale="linear",
                    lower=args.k1_lower,
                    upper=args.k1_upper,
                    initial_guess=args.k1_initial,
                    initial_sigma=0.25,
                )
            out_models.append(block)
            continue

        if wanted == "sni":
            source_block = source_by_name.get("sni")
            if source_block is not None:
                block = clone_block(source_block, new_name="sni")
            else:
                block = make_block(
                    "sni",
                    scale="linear",
                    lower=args.sni_lower,
                    upper=args.sni_upper,
                    initial_guess=args.sni_initial,
                    initial_sigma=0.2,
                )
            out_models.append(block)
            continue

        source_block = source_by_name.get(wanted)
        if source_block is None and wanted == "hmf":
            out_models.append({"name": "hmf", "scale": "linear", "value": 0.7})
            continue
        if source_block is None:
            continue
        block = clone_block(source_block, new_name=wanted)
        if wanted == "n0t":
            # StratifiedFireballModel expects n0t to be sampled in log10 space.
            block["scale"] = "log"
        out_models.append(block)

    if not any(block["name"] == "n0t" for block in out_models):
        raise SystemExit(f"Source file does not provide n017/n0t: {args.source}")
    if not any(block["name"] == "k1" for block in out_models):
        raise SystemExit(f"Source file does not provide k/k1: {args.source}")

    for block in out_models:
        name = block["name"]
        if name not in best_fit:
            continue
        set_initial_guess(block, best_fit[name])

    if "k1" in best_fit:
        for block in out_models:
            if block["name"] == "k1":
                set_initial_guess(block, best_fit["k1"])
            elif block["name"] == "k2" and "prior" in block and "initial_guess" not in block["prior"]:
                block["prior"]["initial_guess"] = args.k2_initial

    if args.initial_sigma_scale <= 0:
        raise SystemExit("--initial-sigma-scale must be > 0")
    if args.initial_sigma_scale != 1.0:
        for block in out_models:
            prior = block.get("prior")
            if not isinstance(prior, dict):
                continue
            sigma = prior.get("initial_sigma")
            if isinstance(sigma, (int, float)):
                prior["initial_sigma"] = float(sigma) * args.initial_sigma_scale

    lines = [
        "# Generated smoothly broken power-law style configuration",
        "# Source: " + str(args.source),
    ]
    if args.seed_best_fit is not None:
        lines.append("# Seed best fit: " + str(args.seed_best_fit))
    lines.extend(
        [
            f"name = {format_value('StratifiedFireballModel')}",
            "",
        ]
    )

    emit_table_array(lines, "model", out_models)

    for section in ("extinction", "offsets", "hosts", "slop"):
        blocks = source.get(section, [])
        if isinstance(blocks, list) and blocks:
            emit_table_array(lines, section, blocks)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote SBPL-like config: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
