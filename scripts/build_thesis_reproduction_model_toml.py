#!/usr/bin/env python3
"""Build thesis-centered PL or SBPL TOMLs for the wide top-hat reproduction workflow."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any
import tomllib

from thesis_reproduction_data import THESIS, normalize_event_name


SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")

SOURCE_MODEL_ALIASES = {
    "dL28": "dl28",
    "dL": "dl28",
    "dl": "dl28",
    "eps_B": "eps_b",
    "n0t": "nt",
    "n017": "n017",
    "sni": "sn",
}

PL_PARAM_SPECS = [
    ("E52", "model", "E52", "log"),
    ("lf0", "model", "lf0", "log"),
    ("n017", "model", "n017", "log"),
    ("eps_e", "model", "eps_e", "log"),
    ("eps_b", "model", "eps_b", "log"),
    ("p", "model", "p", "linear"),
    ("k", "model", "k", "linear"),
]

SBPL_PARAM_SPECS = [
    ("E52", "model", "E52", "log"),
    ("lf0", "model", "lf0", "log"),
    ("nt", "model", "nt", "linear"),
    ("rt", "model", "rt", "linear"),
    ("eps_e", "model", "eps_e", "log"),
    ("eps_b", "model", "eps_B", "log"),
    ("p", "model", "p", "linear"),
    ("kpre", "model", "k1", "linear"),
    ("kpost", "model", "k2", "linear"),
    ("sn", "model", "sn", "linear"),
]

POSITIVE_LINEAR_LOWER_BOUNDS = {
    "ebv_source_frame": 0.0,
    "slop": 0.0,
    "p": 2.0,
}

LOG_UPPER_BOUNDS = {
    "eps_e": 0.0,
    "eps_b": 0.0,
    "eps_B": 0.0,
}

MIN_SIGMA_FALLBACKS = {
    "E52": 0.10,
    "lf0": 0.10,
    "n017": 0.10,
    "nt": 0.10,
    "rt": 0.05,
    "eps_e": 0.10,
    "eps_b": 0.10,
    "eps_B": 0.10,
    "p": 0.01,
    "k": 0.05,
    "k1": 0.05,
    "k2": 0.05,
    "sn": 0.05,
    "ebv_source_frame": 0.01,
    "slop": 0.01,
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


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _entry_name(entry: dict[str, Any]) -> str | None:
    value = entry.get("name")
    return value if isinstance(value, str) else None


def _canonical_model_name(name: str) -> str:
    return SOURCE_MODEL_ALIASES.get(name, name)


def _source_section_map(source: dict[str, Any], section: str) -> dict[str, dict[str, Any]]:
    entries = source.get(section, [])
    if not isinstance(entries, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = _entry_name(entry)
        if name is None:
            continue
        key = _canonical_model_name(name) if section == "model" else name
        mapped[key] = entry
    return mapped


def _fixed_entry(name: str, scale: str, value: float) -> dict[str, Any]:
    return {
        "name": name,
        "scale": scale,
        "value": float(value),
    }


def _clone_entry(entry: dict[str, Any], *, new_name: str | None = None) -> dict[str, Any]:
    out = copy.deepcopy(entry)
    if new_name is not None:
        out["name"] = new_name
    return out


def _fallback_prior_from_source(
    source_entry: dict[str, Any] | None,
    *,
    center: float,
    scale: str,
    initial_sigma_scale: float,
) -> dict[str, Any]:
    if source_entry is not None:
        prior = source_entry.get("prior")
        if isinstance(prior, dict) and "lower" in prior and "upper" in prior:
            out = {
                "type": "uniform",
                "lower": float(prior["lower"]),
                "upper": float(prior["upper"]),
                "initial_guess": float(center),
            }
            initial_sigma = prior.get("initial_sigma")
            if isinstance(initial_sigma, (float, int)):
                out["initial_sigma"] = max(float(initial_sigma) * initial_sigma_scale, 1e-6)
            return out

    width = 0.5 if scale == "linear" else 0.3
    return {
        "type": "uniform",
        "lower": float(center - width),
        "upper": float(center + width),
        "initial_guess": float(center),
        "initial_sigma": max(float(width / 2.0) * initial_sigma_scale, 1e-6),
    }


def _source_prior_entry(
    source_entry: dict[str, Any] | None,
    *,
    center: float,
    scale: str,
    param_name: str,
    initial_sigma_scale: float,
) -> dict[str, Any]:
    prior = None
    if source_entry is not None:
        candidate = source_entry.get("prior")
        if isinstance(candidate, dict) and "lower" in candidate and "upper" in candidate:
            prior = candidate

    if prior is None:
        prior_out = _fallback_prior_from_source(
            source_entry,
            center=center,
            scale=scale,
            initial_sigma_scale=initial_sigma_scale,
        )
    else:
        source_center = prior.get("initial_guess", center)
        prior_out = {
            "type": prior.get("type", "uniform"),
            "lower": float(prior["lower"]),
            "upper": float(prior["upper"]),
            "initial_guess": float(source_center),
        }
        source_sigma = prior.get("initial_sigma")
        if isinstance(source_sigma, (float, int)):
            prior_out["initial_sigma"] = max(float(source_sigma) * initial_sigma_scale, 1e-6)

    lower_bound = POSITIVE_LINEAR_LOWER_BOUNDS.get(param_name)
    if lower_bound is not None:
        prior_out["lower"] = max(float(prior_out["lower"]), lower_bound)

    upper_bound = LOG_UPPER_BOUNDS.get(param_name)
    if upper_bound is not None:
        prior_out["upper"] = min(float(prior_out["upper"]), upper_bound)

    prior_out["initial_guess"] = min(
        max(float(prior_out["initial_guess"]), float(prior_out["lower"])),
        float(prior_out["upper"]),
    )
    return prior_out


def _build_uniform_prior(
    thesis_interval: tuple[float, float, float],
    *,
    sigma_multiple: float,
    scale: str,
    source_entry: dict[str, Any] | None,
    param_name: str,
    initial_sigma_scale: float,
) -> dict[str, Any]:
    center, lower_68, upper_68 = thesis_interval
    sigma_minus = max(0.0, float(center) - float(lower_68))
    sigma_plus = max(0.0, float(upper_68) - float(center))

    if sigma_minus == 0.0 and sigma_plus == 0.0:
        sigma_minus = sigma_plus = MIN_SIGMA_FALLBACKS.get(param_name, 0.05)

    prior = _source_prior_entry(
        source_entry,
        center=float(center),
        scale=scale,
        param_name=param_name,
        initial_sigma_scale=initial_sigma_scale,
    )
    if "initial_sigma" not in prior:
        initial_sigma = max((sigma_minus + sigma_plus) / 2.0, 1e-3)
        prior["initial_sigma"] = max(float(initial_sigma) * initial_sigma_scale, 1e-6)
    return prior


def _thesis_prior_entry(
    output_name: str,
    scale: str,
    thesis_interval: tuple[float, float, float],
    *,
    sigma_multiple: float,
    source_entry: dict[str, Any] | None,
    param_name: str,
    initial_sigma_scale: float,
) -> dict[str, Any]:
    return {
        "name": output_name,
        "scale": scale,
        "prior": _build_uniform_prior(
            thesis_interval,
            sigma_multiple=sigma_multiple,
            scale=scale,
            source_entry=source_entry,
            param_name=param_name,
            initial_sigma_scale=initial_sigma_scale,
        ),
    }


def _copy_non_model_sections(
    source: dict[str, Any],
    thesis: dict[str, Any],
    *,
    sigma_multiple: float,
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
            if name == "ebv_source_frame" and "ebv_source_frame" in thesis:
                new_extinction.append(
                    _thesis_prior_entry(
                        "ebv_source_frame",
                        "linear",
                        thesis["ebv_source_frame"],
                        sigma_multiple=sigma_multiple,
                        source_entry=entry,
                        param_name="ebv_source_frame",
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
        single_slop = len(slop_entries) == 1 and "slop" in thesis
        for entry in slop_entries:
            if not isinstance(entry, dict):
                continue
            name = _entry_name(entry)
            if single_slop and name == "slop":
                new_slop.append(
                    _thesis_prior_entry(
                        "slop",
                        "linear",
                        thesis["slop"],
                        sigma_multiple=sigma_multiple,
                        source_entry=entry,
                        param_name="slop",
                        initial_sigma_scale=initial_sigma_scale,
                    )
                )
            else:
                new_slop.append(copy.deepcopy(entry))
        if new_slop:
            out["slop"] = new_slop

    return out


def _resolve_fixed_from_source(
    source_model: dict[str, dict[str, Any]],
    name: str,
    fallback: float | None = None,
) -> float:
    entry = source_model.get(name)
    if entry is not None and "value" in entry:
        return float(entry["value"])
    if fallback is None:
        raise ValueError(f"Missing fixed source value for {name}")
    return float(fallback)


def build_config(
    source: dict[str, Any],
    *,
    event: str,
    sigma_multiple: float,
    initial_sigma_scale: float,
    theta_c: float,
    theta_v: float,
    pl_model_name: str,
    sbpl_model_name: str,
) -> dict[str, Any]:
    thesis = THESIS[event]
    kind = thesis["model"]
    source_model = _source_section_map(source, "model")

    if kind == "PL":
        config: dict[str, Any] = {"name": pl_model_name}
        model_entries: list[dict[str, Any]] = []
        for thesis_key, _, output_name, scale in PL_PARAM_SPECS:
            source_entry = source_model.get(output_name)
            if thesis_key in thesis:
                model_entries.append(
                    _thesis_prior_entry(
                        output_name,
                        scale,
                        thesis[thesis_key],
                        sigma_multiple=sigma_multiple,
                        source_entry=source_entry,
                        param_name=output_name,
                        initial_sigma_scale=initial_sigma_scale,
                    )
                )
            elif source_entry is not None:
                model_entries.append(_clone_entry(source_entry, new_name=output_name))
            else:
                raise ValueError(f"Missing thesis and source prior for {event}:{output_name}")

        model_entries.append(_fixed_entry("hmf", "linear", 0.7))
        model_entries.append(_fixed_entry("z", "linear", _resolve_fixed_from_source(source_model, "z")))
        model_entries.append(_fixed_entry("dl28", "linear", _resolve_fixed_from_source(source_model, "dl28")))
        model_entries.append(_fixed_entry("theta_c", "linear", theta_c))
        model_entries.append(_fixed_entry("theta_v", "linear", theta_v))
        config["model"] = model_entries
    elif kind == "SBPL":
        config = {"name": sbpl_model_name}
        model_entries = []
        for thesis_key, _, output_name, scale in SBPL_PARAM_SPECS:
            source_lookup = output_name
            if output_name == "eps_B":
                source_lookup = "eps_b"
            source_entry = source_model.get(source_lookup)
            if thesis_key in thesis:
                model_entries.append(
                    _thesis_prior_entry(
                        output_name,
                        scale,
                        thesis[thesis_key],
                        sigma_multiple=sigma_multiple,
                        source_entry=source_entry,
                        param_name=output_name,
                        initial_sigma_scale=initial_sigma_scale,
                    )
                )
            elif source_entry is not None:
                model_entries.append(_clone_entry(source_entry, new_name=output_name))
            else:
                raise ValueError(f"Missing thesis and source prior for {event}:{output_name}")

        model_entries.append(_fixed_entry("z", "linear", _resolve_fixed_from_source(source_model, "z")))
        model_entries.append(_fixed_entry("dl28", "linear", _resolve_fixed_from_source(source_model, "dl28")))
        model_entries.append(_fixed_entry("theta_c", "linear", theta_c))
        model_entries.append(_fixed_entry("theta_v", "linear", theta_v))
        config["model"] = model_entries
    else:
        raise ValueError(f"Unsupported thesis model kind for {event}: {kind}")

    config.update(
        _copy_non_model_sections(
            source,
            thesis,
            sigma_multiple=sigma_multiple,
            initial_sigma_scale=initial_sigma_scale,
        )
    )
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="GRB event name.")
    parser.add_argument("--input", required=True, type=Path, help="Source event parameters TOML.")
    parser.add_argument("--output", required=True, type=Path, help="Output thesis-centered TOML.")
    parser.add_argument("--sigma-multiple", type=float, default=5.0, help="Width multiplier for 68% thesis intervals.")
    parser.add_argument(
        "--initial-sigma-scale",
        type=float,
        default=1.0,
        help="Scale factor applied to Dylan thesis sigma when setting initial_sigma.",
    )
    parser.add_argument("--theta-c", type=float, default=1.0, help="Fixed top-hat opening angle in radians.")
    parser.add_argument("--theta-v", type=float, default=0.0, help="Fixed observing angle in radians.")
    parser.add_argument(
        "--pl-model-name",
        default="powerlawVegasDylanSpectrumModel",
        help="Model class name to use for PL events.",
    )
    parser.add_argument(
        "--sbpl-model-name",
        default="VegasAfterglowModel",
        help="Model class name to use for SBPL events.",
    )
    args = parser.parse_args()

    event = normalize_event_name(args.event)
    if event not in THESIS:
        raise SystemExit(f"No thesis prior data found for event: {event}")

    source = _load_toml(args.input)
    config = build_config(
        source,
        event=event,
        sigma_multiple=args.sigma_multiple,
        initial_sigma_scale=args.initial_sigma_scale,
        theta_c=args.theta_c,
        theta_v=args.theta_v,
        pl_model_name=args.pl_model_name,
        sbpl_model_name=args.sbpl_model_name,
    )
    _write_toml(args.output, config)

    print(f"Wrote thesis reproduction config: {args.output}")
    print(f"  event:      {event}")
    print(f"  thesis:     {THESIS[event]['model']}")
    print(f"  model_name: {config['name']}")
    print(f"  theta_c:    {args.theta_c}")
    print(f"  theta_v:    {args.theta_v}")
    print(f"  sigma_mult: {args.sigma_multiple}")
    print(f"  init_sigma: {args.initial_sigma_scale}x thesis sigma")


if __name__ == "__main__":
    main()
