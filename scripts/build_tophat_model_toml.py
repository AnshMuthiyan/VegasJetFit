#!/usr/bin/env python3
"""
Build an event-specific top-hat model TOML.

This is meant for apples-to-apples comparisons where:
- event-specific fixed values (e.g., redshift, luminosity distance) are
  inherited from the event's existing parameters.toml
- jet half-opening angle is fixed to theta_c (default: 1.0 rad)
- viewing angle is fixed to theta_v (default: 0.0 rad)

Input may be an existing FireballModel or powerlaw-style parameter file.
New top-hat configs default to Dylan's smoothed Vegas spectrum; pass
``--model-name powerlawVegasModel`` only for an intentional legacy-standard
spectrum comparison.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

import tomllib


SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")

# Keep only fields supported by powerlawVegasModel.__init__
KEEP_MODEL_NAMES = {
    "E52",
    "lf0",
    "n017",
    "eps_e",
    "eps_b",
    "p",
    "k",
    "hmf",
    "z",
    "dl28",
    "theta_c",
    "theta_v",
}

RENAME_MODEL_NAMES = {
    "dL28": "dl28",
    "dL": "dl28",
    "dl": "dl28",
    "E": "E52",
    "rho0": "n017",
    "X": "hmf",
    "eps_B": "eps_b",
    "k1": "k",
    "n0t": "n017",
}

BEST_FIT_NAME_MAP = {
    "dL28": "dl28",
    "dL": "dl28",
    "dl": "dl28",
    "rho0": "n017",
    "eps_B": "eps_b",
}

REQUIRED_MODEL_NAMES = {
    "E52",
    "lf0",
    "n017",
    "eps_e",
    "eps_b",
    "p",
    "k",
    "z",
    "dl28",
}

# Defaults used to backfill missing parameters from legacy model files.
# These match the standard powerlaw priors used in this repo.
DEFAULT_REQUIRED_ENTRIES: dict[str, dict[str, Any]] = {
    "E52": {
        "name": "E52",
        "scale": "log",
        "prior": {"type": "uniform", "lower": -2.0, "upper": 4.0},
    },
    "lf0": {
        "name": "lf0",
        "scale": "log",
        "prior": {"type": "uniform", "lower": 1.69, "upper": 3.0},
    },
    "n017": {
        "name": "n017",
        "scale": "log",
        "prior": {"type": "uniform", "lower": -6.0, "upper": 6.0},
    },
    "eps_e": {
        "name": "eps_e",
        "scale": "log",
        "prior": {"type": "uniform", "lower": -6.0, "upper": 0.0},
    },
    "eps_b": {
        "name": "eps_b",
        "scale": "log",
        "prior": {"type": "uniform", "lower": -6.0, "upper": 0.0},
    },
    "p": {
        "name": "p",
        "scale": "linear",
        "prior": {"type": "uniform", "lower": 2.0, "upper": 3.0},
    },
    "k": {
        "name": "k",
        "scale": "linear",
        "prior": {"type": "uniform", "lower": -10.0, "upper": 3.0},
    },
}

EXPECTED_SCALES = {
    "E52": "log",
    "lf0": "log",
    "n017": "log",
    "eps_e": "log",
    "eps_b": "log",
    "p": "linear",
    "k": "linear",
    "z": "linear",
    "dl28": "linear",
}


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


def _find_model_entry(model_entries: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for entry in model_entries:
        if _entry_name(entry) == name:
            return entry
    return None


def _canonical_bestfit_name(name: str) -> str:
    return BEST_FIT_NAME_MAP.get(name, name)


def _load_best_fit(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    payload = json.loads(path.read_text())
    model = payload.get("model")
    if not isinstance(model, dict) or not model:
        params = payload.get("params", {})
        if isinstance(params, dict):
            model = params.get("model", {})
        else:
            model = {}
    if not isinstance(model, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in model.items():
        try:
            out[_canonical_bestfit_name(str(key))] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _set_initial_guess_from_bestfit(entry: dict[str, Any], value: float) -> None:
    if "prior" not in entry or "value" in entry:
        return
    prior = entry.get("prior")
    if not isinstance(prior, dict):
        return
    if entry.get("scale") == "log":
        if value <= 0.0:
            return
        prior["initial_guess"] = math.log10(value)
    else:
        prior["initial_guess"] = value


def _set_fixed_value(model_entries: list[dict[str, Any]], name: str, value: float) -> None:
    entry = _find_model_entry(model_entries, name)
    if entry is None:
        entry = {"name": name, "scale": "linear"}
        model_entries.append(entry)

    entry["value"] = float(value)
    entry.pop("prior", None)


def _normalize_required_entries(
    model_entries: list[dict[str, Any]],
    *,
    k_lower: float,
    k_upper: float,
) -> list[str]:
    """Backfill missing required params and normalize key scales/priors.

    Returns names that were auto-added.
    """
    added: list[str] = []

    for name, default_entry in DEFAULT_REQUIRED_ENTRIES.items():
        entry = _find_model_entry(model_entries, name)
        if entry is None:
            model_entries.append(copy.deepcopy(default_entry))
            added.append(name)
            continue

        # Keep model scales consistent with powerlawVegasModel conventions.
        expected_scale = EXPECTED_SCALES.get(name)
        if expected_scale is not None:
            entry["scale"] = expected_scale

        # k and n017 must be fit parameters (never fixed) for this workflow.
        if name in {"k", "n017"}:
            entry.pop("value", None)
            if "prior" not in entry:
                entry["prior"] = copy.deepcopy(default_entry["prior"])

        # Always enforce the k prior bounds for apples-to-apples comparisons.
        if name == "k":
            prior = entry.setdefault("prior", {})
            prior["type"] = "uniform"
            prior["lower"] = float(k_lower)
            prior["upper"] = float(k_upper)

        # If a required physics parameter is present but missing prior/value,
        # recover with the repo's standard prior.
        if name in {"E52", "lf0", "eps_e", "eps_b", "p"}:
            if "prior" not in entry and "value" not in entry:
                entry["prior"] = copy.deepcopy(default_entry["prior"])

    return added


def build_tophat_config(
    source: dict[str, Any],
    theta_c: float,
    theta_v: float,
    k_lower: float = -10.0,
    k_upper: float = 3.0,
    seed_best_fit: dict[str, float] | None = None,
    model_name: str = "powerlawVegasDylanSpectrumModel",
) -> dict[str, Any]:
    out: dict[str, Any] = {"name": model_name}

    raw_model = source.get("model", [])
    if not isinstance(raw_model, list):
        raise ValueError("Input TOML has no valid [[model]] section.")

    filtered_model: list[dict[str, Any]] = []
    seen: set[str] = set()
    dropped: list[str] = []

    for entry in raw_model:
        if not isinstance(entry, dict):
            continue

        name = _entry_name(entry)
        if name is None:
            continue

        renamed = RENAME_MODEL_NAMES.get(name, name)
        if renamed not in KEEP_MODEL_NAMES:
            dropped.append(name)
            continue
        if renamed in seen:
            continue

        new_entry = copy.deepcopy(entry)
        new_entry["name"] = renamed
        filtered_model.append(new_entry)
        seen.add(renamed)

    added = _normalize_required_entries(
        filtered_model,
        k_lower=k_lower,
        k_upper=k_upper,
    )

    # recompute seen after normalization/additions
    seen = {_entry_name(e) for e in filtered_model if _entry_name(e) is not None}

    missing = sorted(REQUIRED_MODEL_NAMES - set(seen))
    if missing:
        raise ValueError(
            "Input model is missing required parameters for a power-law Vegas model: "
            + ", ".join(missing)
        )

    # Force top-hat parameters to fixed values
    _set_fixed_value(filtered_model, "theta_c", theta_c)
    _set_fixed_value(filtered_model, "theta_v", theta_v)

    if seed_best_fit:
        for entry in filtered_model:
            name = _entry_name(entry)
            if name is None:
                continue
            if name in seed_best_fit:
                _set_initial_guess_from_bestfit(entry, seed_best_fit[name])

    out["model"] = filtered_model

    # Keep nuisance/systematics sections untouched.
    for section in ("extinction", "offsets", "host", "slop"):
        if section in source:
            out[section] = copy.deepcopy(source[section])

    if dropped:
        print("Dropped unsupported model parameters:", ", ".join(dropped))
    if added:
        print("Added missing model parameters from defaults:", ", ".join(added))

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build top-hat theta_c TOML from event parameters TOML")
    parser.add_argument("--input", required=True, help="Input event parameter TOML")
    parser.add_argument("--output", required=True, help="Output top-hat TOML")
    parser.add_argument("--theta-c", type=float, default=1.0, help="Fixed theta_c in radians (default: 1.0)")
    parser.add_argument("--theta-v", type=float, default=0.0, help="Fixed theta_v in radians (default: 0.0)")
    parser.add_argument("--k-lower", type=float, default=-10.0, help="Lower prior bound for k (default: -10.0)")
    parser.add_argument("--k-upper", type=float, default=3.0, help="Upper prior bound for k (default: 3.0)")
    parser.add_argument("--seed-best-fit", type=Path, default=None, help="Optional best_fit.json to seed initial guesses")
    parser.add_argument(
        "--model-name",
        default="powerlawVegasDylanSpectrumModel",
        help=(
            "Model name to write into the output TOML "
            "(default: Dylan-smoothed powerlawVegasDylanSpectrumModel)"
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    source = tomllib.loads(input_path.read_text())
    if args.k_lower >= args.k_upper:
        raise SystemExit(f"--k-lower must be < --k-upper (got {args.k_lower} >= {args.k_upper})")

    seed_best_fit = _load_best_fit(args.seed_best_fit)

    out = build_tophat_config(
        source,
        theta_c=args.theta_c,
        theta_v=args.theta_v,
        k_lower=args.k_lower,
        k_upper=args.k_upper,
        seed_best_fit=seed_best_fit,
        model_name=args.model_name,
    )
    _write_toml(output_path, out)

    print(f"Wrote top-hat config: {output_path}")
    print(f"  source:  {input_path}")
    print(f"  model:   {out.get('name')}")
    print(f"  theta_c: {args.theta_c}")
    print(f"  theta_v: {args.theta_v}")
    print(f"  k_prior: [{args.k_lower}, {args.k_upper}]")
    if args.seed_best_fit is not None:
        print(f"  seed:    {args.seed_best_fit}")


if __name__ == "__main__":
    main()
