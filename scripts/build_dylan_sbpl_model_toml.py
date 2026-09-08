#!/usr/bin/env python3
"""Stage Dylan SBPL events onto top-hat VegasAfterglow with Dylan prior boxes."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

from build_thesis_reproduction_model_toml import _load_toml, _write_toml
from thesis_reproduction_data import THESIS, normalize_event_name


SCRIPT_DIR = Path(__file__).resolve().parent
VEGAS_DIR = SCRIPT_DIR.parent

SEED_SIGMA_FALLBACKS = {
    "E52": 0.10,
    "lf0": 0.10,
    "nt": 0.10,
    "rt": 0.05,
    "eps_e": 0.10,
    "eps_b": 0.10,
    "eps_B": 0.10,
    "p": 0.01,
    "k1": 0.05,
    "k2": 0.05,
    "sn": 0.05,
    "ebv_source_frame": 0.01,
    "slop": 0.01,
}

MODEL_SPECS = {
    "080413B": [
        ("E52", "E52", "E52", "E52", "log", None, "log10"),
        ("lf0", "lf0", "lf0", "lf0", "log", None, "log10"),
        ("n017", "n0t", "nt", "nt", "linear", None, "log10"),
        ("rt", "rt", "rt", "rt", "linear", None, "log10"),
        ("eps_e", "eps_e", "eps_e", "eps_e", "log", None, "log10"),
        ("eps_B", "eps_b", "eps_b", "eps_B", "log", None, "log10"),
        ("p", "p", "p", "p", "linear", None, None),
        ("k1", "k1", "kpre", "k1", "linear", None, None),
        ("k2", "k2", "kpost", "k2", "linear", None, None),
        ("sn", "sni", "sn", "sn", "linear", None, None),
    ],
    "080319B": [
        ("E52", "E52", "E52", "E52", "log", None, "log10"),
        ("lf0", "lf0", "lf0", "lf0", "log", None, "log10"),
        ("n0t", "n0t", "nt", "nt", "linear", None, "log10"),
        ("rt", "rt", "rt", "rt", "linear", None, "log10"),
        ("eps_e", "eps_e", "eps_e", "eps_e", "log", None, "log10"),
        ("eps_b", "eps_b", "eps_b", "eps_B", "log", None, "log10"),
        ("p", "p", "p", "p", "linear", None, None),
        ("k1", "k1", "kpre", "k1", "linear", None, None),
        ("k2", "k2", "kpost", "k2", "linear", None, None),
        ("sni", "sni", "sn", "sn", "linear", "reciprocal", "reciprocal"),
    ],
}

FIXED_MODEL_SPECS = {
    "080413B": [
        ("z", "z"),
        ("dl28", "dl28"),
    ],
    "080319B": [
        ("z", "z"),
        ("dL28", "dl28"),
    ],
}

DEFAULT_SEED_BEST_FIT = {
    "080319B": VEGAS_DIR / "jetfit" / "results" / "080319B_smoothbroken_thesis_short" / "best_fit.json",
    "080413B": VEGAS_DIR / "jetfit" / "results" / "080413B_smoothbroken_thesis_short" / "best_fit.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="GRB event name.")
    parser.add_argument("--input", required=True, type=Path, help="Path to Dylan source TOML.")
    parser.add_argument("--output", required=True, type=Path, help="Output TOML path.")
    parser.add_argument(
        "--seed-best-fit",
        type=Path,
        default=None,
        help="Optional Dylan best_fit.json used for seeded initial_guess centers.",
    )
    parser.add_argument(
        "--sigma-multiple",
        type=float,
        default=5.0,
        help="Retained for CLI compatibility. Hard priors come from Dylan's source TOML.",
    )
    parser.add_argument(
        "--initial-sigma-scale",
        type=float,
        default=0.05,
        help="Scale factor applied to Dylan source initial_sigma when setting initial_sigma.",
    )
    parser.add_argument(
        "--theta-c",
        type=float,
        default=1.0,
        help="Fixed top-hat opening angle in radians.",
    )
    parser.add_argument(
        "--theta-v",
        type=float,
        default=0.0,
        help="Fixed observing angle in radians.",
    )
    return parser.parse_args()


def _entry_name(entry: dict[str, Any]) -> str | None:
    value = entry.get("name")
    return value if isinstance(value, str) else None


def _section_map(source: dict[str, Any], section: str) -> dict[str, dict[str, Any]]:
    entries = source.get(section, [])
    if not isinstance(entries, list):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = _entry_name(entry)
        if name is None:
            continue
        out[name] = entry
    return out


def _interval_center_and_sigma(event: str, thesis_key: str, *, fallback_name: str) -> tuple[float, float]:
    interval = THESIS[event].get(thesis_key)
    if interval is None:
        raise ValueError(f"Missing thesis interval for {event}:{thesis_key}")

    center, lower_68, upper_68 = (float(value) for value in interval)
    sigma_minus = max(center - lower_68, 0.0)
    sigma_plus = max(upper_68 - center, 0.0)
    sigma = (sigma_minus + sigma_plus) / 2.0
    if sigma <= 0.0:
        sigma = SEED_SIGMA_FALLBACKS.get(fallback_name, 0.05)
    return center, sigma


def _load_best_fit(path: Path) -> dict[str, dict[str, float]]:
    payload = json.loads(path.read_text())
    out: dict[str, dict[str, float]] = {}
    for section in ("model", "extinction", "slop"):
        raw_section = payload.get(section, {})
        if not isinstance(raw_section, dict):
            out[section] = {}
            continue
        converted: dict[str, float] = {}
        for key, value in raw_section.items():
            if isinstance(value, (int, float)):
                converted[str(key)] = float(value)
        out[section] = converted
    return out


def _resolve_seed_best_fit_path(event: str, seed_best_fit: Path | None) -> Path:
    path = seed_best_fit if seed_best_fit is not None else DEFAULT_SEED_BEST_FIT.get(event)
    if path is None:
        raise ValueError(f"No default Dylan best-fit path configured for {event}")
    if not path.exists():
        raise FileNotFoundError(f"Dylan best-fit file not found for {event}: {path}")
    return path


def _transform_prior_box(prior: dict[str, Any], transform: str | None) -> dict[str, Any]:
    out = {"type": prior.get("type", "uniform")}
    if "lower" not in prior or "upper" not in prior:
        raise ValueError("Expected Dylan source prior to carry lower/upper bounds")

    lower = float(prior["lower"])
    upper = float(prior["upper"])
    if transform == "reciprocal":
        if lower == 0.0 or upper == 0.0:
            raise ValueError("Cannot transform prior containing zero with reciprocal mapping")
        transformed = (1.0 / upper, 1.0 / lower)
        lower = min(transformed)
        upper = max(transformed)

    out["lower"] = lower
    out["upper"] = upper
    return out


def _clamp_to_prior(center: float, prior: dict[str, Any]) -> float:
    lower = float(prior["lower"])
    upper = float(prior["upper"])
    return min(max(center, lower), upper)


def _transform_seed_value(value: float, transform: str | None) -> float:
    if transform == "log10":
        if value <= 0.0:
            raise ValueError("Cannot transform non-positive best-fit value with log10 mapping")
        return math.log10(value)
    if transform == "reciprocal":
        if value == 0.0:
            raise ValueError("Cannot transform zero with reciprocal mapping")
        return 1.0 / value
    return value


def _scaled_source_sigma(
    prior: dict[str, Any],
    *,
    event: str,
    thesis_key: str,
    output_name: str,
    initial_sigma_scale: float,
) -> float:
    source_sigma = prior.get("initial_sigma")
    if isinstance(source_sigma, (float, int)):
        return max(abs(float(source_sigma)) * initial_sigma_scale, 1e-6)

    _, sigma = _interval_center_and_sigma(event, thesis_key, fallback_name=output_name)
    return max(sigma * initial_sigma_scale, 1e-6)


def _build_seeded_entry(
    source_entry: dict[str, Any],
    *,
    event: str,
    seed_value: float,
    thesis_key: str,
    output_name: str,
    output_scale: str,
    initial_sigma_scale: float,
    prior_transform: str | None = None,
    seed_transform: str | None = None,
) -> dict[str, Any]:
    prior = source_entry.get("prior")
    if not isinstance(prior, dict):
        raise ValueError(f"Missing prior for source entry {source_entry.get('name')}")

    seeded_prior = _transform_prior_box(prior, prior_transform)
    center = _transform_seed_value(seed_value, seed_transform)
    seeded_prior["initial_guess"] = _clamp_to_prior(center, seeded_prior)
    seeded_prior["initial_sigma"] = _scaled_source_sigma(
        prior,
        event=event,
        thesis_key=thesis_key,
        output_name=output_name,
        initial_sigma_scale=initial_sigma_scale,
    )
    return {
        "name": output_name,
        "scale": output_scale,
        "prior": seeded_prior,
    }


def _copy_fixed_entry(source_entry: dict[str, Any], *, output_name: str) -> dict[str, Any]:
    if "value" not in source_entry:
        raise ValueError(f"Missing fixed value for source entry {source_entry.get('name')}")
    scale = source_entry.get("scale")
    if not isinstance(scale, str):
        raise ValueError(f"Missing scale for source entry {source_entry.get('name')}")
    return {
        "name": output_name,
        "scale": scale,
        "value": float(source_entry["value"]),
    }


def _fixed_entry(name: str, scale: str, value: float) -> dict[str, Any]:
    return {
        "name": name,
        "scale": scale,
        "value": float(value),
    }


def _copy_sections(
    source: dict[str, Any],
    *,
    best_fit: dict[str, dict[str, float]],
    event: str,
    initial_sigma_scale: float,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}

    for section in ("offsets", "host"):
        entries = source.get(section, [])
        if isinstance(entries, list) and entries:
            out[section] = copy.deepcopy(entries)

    extinction_entries = source.get("extinction", [])
    if isinstance(extinction_entries, list) and extinction_entries:
        new_extinction: list[dict[str, Any]] = []
        for entry in extinction_entries:
            if not isinstance(entry, dict):
                continue
            name = _entry_name(entry)
            if name == "ebv_source_frame":
                if name not in best_fit["extinction"]:
                    raise ValueError(f"Missing Dylan best-fit extinction value for {event}:{name}")
                new_extinction.append(
                    _build_seeded_entry(
                        entry,
                        seed_value=best_fit["extinction"][name],
                        event=event,
                        thesis_key="ebv_source_frame",
                        output_name="ebv_source_frame",
                        output_scale="linear",
                        initial_sigma_scale=initial_sigma_scale,
                    )
                )
            else:
                new_extinction.append(copy.deepcopy(entry))
        if new_extinction:
            out["extinction"] = new_extinction

    slop_entries = source.get("slop", [])
    if isinstance(slop_entries, list) and slop_entries:
        new_slop: list[dict[str, Any]] = []
        for entry in slop_entries:
            if not isinstance(entry, dict):
                continue
            name = _entry_name(entry)
            if name == "slop":
                if name not in best_fit["slop"]:
                    raise ValueError(f"Missing Dylan best-fit slop value for {event}:{name}")
                new_slop.append(
                    _build_seeded_entry(
                        entry,
                        seed_value=best_fit["slop"][name],
                        event=event,
                        thesis_key="slop",
                        output_name="slop",
                        output_scale="linear",
                        initial_sigma_scale=initial_sigma_scale,
                    )
                )
            else:
                new_slop.append(copy.deepcopy(entry))
        if new_slop:
            out["slop"] = new_slop

    return out


def build_config(
    source: dict[str, Any],
    *,
    event: str,
    best_fit: dict[str, dict[str, float]],
    initial_sigma_scale: float,
    theta_c: float,
    theta_v: float,
) -> dict[str, Any]:
    if event not in MODEL_SPECS:
        raise ValueError(f"Unsupported Dylan SBPL event: {event}")

    source_model = _section_map(source, "model")
    model_entries: list[dict[str, Any]] = []
    for (
        source_name,
        seed_name,
        thesis_key,
        output_name,
        output_scale,
        prior_transform,
        seed_transform,
    ) in MODEL_SPECS[event]:
        source_entry = source_model.get(source_name)
        if source_entry is None:
            raise ValueError(f"Missing Dylan source entry {source_name} for event {event}")
        if seed_name not in best_fit["model"]:
            raise ValueError(f"Missing Dylan best-fit model value for {event}:{seed_name}")
        model_entries.append(
            _build_seeded_entry(
                source_entry,
                event=event,
                seed_value=best_fit["model"][seed_name],
                thesis_key=thesis_key,
                output_name=output_name,
                output_scale=output_scale,
                initial_sigma_scale=initial_sigma_scale,
                prior_transform=prior_transform,
                seed_transform=seed_transform,
            )
        )

    for source_name, output_name in FIXED_MODEL_SPECS[event]:
        source_entry = source_model.get(source_name)
        if source_entry is None:
            raise ValueError(f"Missing Dylan fixed source entry {source_name} for event {event}")
        model_entries.append(_copy_fixed_entry(source_entry, output_name=output_name))

    model_entries.append(_fixed_entry("theta_c", "linear", theta_c))
    model_entries.append(_fixed_entry("theta_v", "linear", theta_v))

    config: dict[str, Any] = {
        "name": "VegasAfterglowModel",
        "model": model_entries,
    }
    config.update(
        _copy_sections(
            source,
            best_fit=best_fit,
            event=event,
            initial_sigma_scale=initial_sigma_scale,
        )
    )
    return config


def main() -> int:
    args = parse_args()
    if args.initial_sigma_scale <= 0:
        raise SystemExit("--initial-sigma-scale must be > 0")
    if args.sigma_multiple <= 0:
        raise SystemExit("--sigma-multiple must be > 0")

    event = normalize_event_name(args.event)
    if event not in THESIS:
        raise SystemExit(f"No thesis data for event: {event}")
    if THESIS[event].get("model") != "SBPL":
        raise SystemExit(f"Event is not marked as SBPL in thesis data: {event}")

    source = _load_toml(args.input)
    seed_best_fit_path = _resolve_seed_best_fit_path(event, args.seed_best_fit)
    best_fit = _load_best_fit(seed_best_fit_path)
    config = build_config(
        source,
        event=event,
        best_fit=best_fit,
        initial_sigma_scale=args.initial_sigma_scale,
        theta_c=args.theta_c,
        theta_v=args.theta_v,
    )
    _write_toml(args.output, config)

    print(f"Wrote Dylan SBPL config: {args.output}")
    print(f"  event:       {event}")
    print(f"  model_name:  {config['name']}")
    print(f"  seed_center: {seed_best_fit_path}")
    print("  hard_priors: Dylan source TOML")
    print(f"  init_sigma:  {args.initial_sigma_scale}x Dylan source initial_sigma")
    print(f"  theta_c:     {args.theta_c}")
    print(f"  theta_v:     {args.theta_v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
