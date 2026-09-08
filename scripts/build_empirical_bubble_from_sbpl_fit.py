#!/usr/bin/env python3
"""
Build an empirical-bubble TOML seeded from a finished SBPL fit.

The source SBPL config carries the event-specific priors, offsets, extinction,
and data-side nuisance setup. This builder converts the runtime model to the
empirical-bubble Dylan-spectrum wrapper, preserves the relevant prior boxes,
maps the fitted SBPL center into the empirical-bubble parameterization, and
derives an initial ``nism`` seed from the late-time density implied by the
finished SBPL model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import tomllib
from pathlib import Path
from typing import Any

import numpy as np

from jetfit.models.vegasafterglow import VegasAfterglowModel


SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")
TINY = 1e-300


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


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _extract_sections(payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    sections: dict[str, dict[str, float]] = {section: {} for section in SECTION_ORDER}

    if "params" in payload and isinstance(payload["params"], dict):
        source = payload["params"]
    else:
        source = payload

    for section in SECTION_ORDER:
        values = source.get(section, {})
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if isinstance(value, (int, float)):
                sections[section][str(key)] = float(value)

    return sections


def _load_obs_bounds_days(path: Path) -> tuple[float, float]:
    times: list[float] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("Time")
            if raw in (None, ""):
                continue
            time = float(raw)
            unit = str(row.get("TimeUnits", "s")).strip().lower()
            if unit == "s":
                time /= 86400.0
            times.append(time)
    if not times:
        raise ValueError(f"no observation times found in {path}")
    return min(times), max(times)


def _interp_radius_at_tmax_days(model: VegasAfterglowModel, tmin_days: float, tmax_days: float) -> float:
    details = model.vegas_model.details(float(tmin_days * 86400.0 * 0.8), float(tmax_days * 86400.0 * 1.2))
    t_obs = np.asarray(details.fwd.t_obs[0, 0, :], dtype=float) / 86400.0
    radius = np.asarray(details.fwd.r[0, 0, :], dtype=float)

    mask = np.isfinite(t_obs) & np.isfinite(radius) & (t_obs > 0.0) & (radius > 0.0)
    t_obs = t_obs[mask]
    radius = radius[mask]
    if t_obs.size == 0:
        raise ValueError("VegasAfterglow details() returned no valid forward-shock trajectory")

    order = np.argsort(t_obs)
    t_obs = t_obs[order]
    radius = radius[order]
    return float(np.interp(tmax_days, t_obs, radius))


def _sbpl_density_log10_at_radius(seed_model: dict[str, float], radius_cm: float) -> float:
    nt_log = float(seed_model["nt"])
    rt_log = float(seed_model["rt"])
    k1 = float(seed_model["k1"])
    k2 = float(seed_model["k2"])
    sn = float(seed_model["sn"])

    n_t = 10.0 ** nt_log
    r_t = 10.0 ** rt_log
    x = max(radius_cm / max(r_t, TINY), 1e-30)

    density = n_t * (2.0 ** (1.0 / sn)) * (x ** (k1 * sn) + x ** (k2 * sn)) ** (-(1.0 / sn))
    return math.log10(max(float(density), TINY))


def _derive_nism_guess(seed_model: dict[str, float], obs_csv: Path) -> float:
    vegas_model = VegasAfterglowModel(
        E52=float(seed_model["E52"]),
        lf0=float(seed_model["lf0"]),
        theta_c=float(seed_model["theta_c"]),
        theta_v=float(seed_model["theta_v"]),
        eps_e=float(seed_model["eps_e"]),
        eps_B=float(seed_model["eps_B"]),
        p=float(seed_model["p"]),
        z=float(seed_model["z"]),
        dl28=float(seed_model["dl28"]),
        nt=float(seed_model["nt"]),
        rt=float(seed_model["rt"]),
        k1=float(seed_model["k1"]),
        k2=float(seed_model["k2"]),
        sn=float(seed_model["sn"]),
    )

    tmin_days, tmax_days = _load_obs_bounds_days(obs_csv)
    outer_radius = _interp_radius_at_tmax_days(vegas_model, tmin_days, tmax_days)
    return _sbpl_density_log10_at_radius(seed_model, outer_radius)


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


def _convert_model_entry(
    entry: dict[str, Any],
    section_values: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    name = entry.get("name")
    if not isinstance(name, str):
        return entry

    if name in {"k1", "k2", "sn"}:
        return None

    new_entry = json.loads(json.dumps(entry))
    if name == "eps_B":
        new_entry["name"] = "eps_b"
        name = "eps_b"

    if name in {"nt", "rt"}:
        new_entry["scale"] = "log"

    if "value" in new_entry:
        return new_entry

    prior = new_entry.get("prior")
    if not isinstance(prior, dict):
        return new_entry

    seed_name = "eps_B" if name == "eps_b" else name
    seed_value = section_values["model"].get(seed_name)
    if seed_value is None:
        seed_value = section_values["extinction"].get(seed_name)
    if seed_value is None:
        seed_value = section_values["offsets"].get(seed_name)
    if seed_value is None:
        seed_value = section_values["host"].get(seed_name)
    if seed_value is None:
        seed_value = section_values["slop"].get(seed_name)

    if seed_value is None:
        return new_entry

    if name in {"nt", "rt"}:
        guess = float(seed_value)
        lower = prior.get("lower")
        upper = prior.get("upper")
        if isinstance(lower, (int, float)):
            guess = max(float(lower), guess)
        if isinstance(upper, (int, float)):
            guess = min(float(upper), guess)
    else:
        guess = _scaled_guess(new_entry, float(seed_value))
        if guess is None:
            return new_entry

    prior["initial_guess"] = guess
    return new_entry


def _make_nism_entry(source_nt_entry: dict[str, Any], nism_guess_log10: float) -> dict[str, Any]:
    prior = {
        "type": "uniform",
        "lower": -6.0,
        "upper": 6.0,
        "initial_guess": max(-6.0, min(6.0, float(nism_guess_log10))),
        "initial_sigma": 0.25,
    }

    source_prior = source_nt_entry.get("prior")
    if isinstance(source_prior, dict):
        sigma = source_prior.get("initial_sigma")
        if isinstance(sigma, (int, float)):
            prior["initial_sigma"] = max(0.1, float(sigma))

    return {
        "name": "nism",
        "scale": "log",
        "prior": prior,
    }


def build_seeded_config(
    *,
    input_config: Path,
    fit_json: Path,
    obs_csv: Path,
    output: Path,
    model_name: str,
) -> None:
    config = tomllib.loads(input_config.read_text())
    section_values = _extract_sections(_load_payload(fit_json))

    model_values = section_values["model"]
    required = {"E52", "lf0", "nt", "rt", "eps_e", "eps_B", "p", "k1", "k2", "sn", "z", "dl28", "theta_c", "theta_v"}
    missing = sorted(required - set(model_values))
    if missing:
        raise ValueError(f"fit json missing required model values: {', '.join(missing)}")

    nism_guess_log10 = _derive_nism_guess(model_values, obs_csv)

    new_config: dict[str, Any] = {"name": model_name}
    for section in SECTION_ORDER:
        entries = config.get(section, [])
        if not isinstance(entries, list):
            continue

        converted_entries: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if section == "model":
                converted = _convert_model_entry(entry, section_values)
                if converted is None:
                    continue
                converted_entries.append(converted)
            else:
                converted_entries.append(entry)

        if section == "model":
            names = [entry.get("name") for entry in converted_entries if isinstance(entry.get("name"), str)]
            if "nism" not in names:
                nt_entry = next((entry for entry in converted_entries if entry.get("name") == "nt"), None)
                insert_at = names.index("nt") + 1 if "nt" in names else len(converted_entries)
                source_nt_entry = nt_entry if isinstance(nt_entry, dict) else {"prior": {"initial_sigma": 0.25}}
                converted_entries.insert(insert_at, _make_nism_entry(source_nt_entry, nism_guess_log10))

        new_config[section] = converted_entries

    _write_toml(output, new_config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an empirical-bubble TOML from a finished SBPL fit.")
    parser.add_argument("--input-config", required=True, help="Existing SBPL TOML to clone priors/offsets from.")
    parser.add_argument("--fit-json", required=True, help="Finished SBPL minimized.json or best_fit.json.")
    parser.add_argument("--obs-csv", required=True, help="Observation CSV used to derive the late-time outer-density seed.")
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
        fit_json=Path(args.fit_json).expanduser().resolve(),
        obs_csv=Path(args.obs_csv).expanduser().resolve(),
        output=Path(args.output).expanduser().resolve(),
        model_name=str(args.model_name),
    )


if __name__ == "__main__":
    main()
