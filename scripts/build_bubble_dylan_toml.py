#!/usr/bin/env python3
"""
Build a Dylan-smoothed bubble-model TOML from a control top-hat power-law TOML.

The shared jet/microphysics/extinction settings come from the supplied power-law
control config. Bubble-only medium parameters can optionally be seeded from an
older bubble fit, and ``rt`` is then overridden with a physically motivated
seed placed just inside the earliest sampled radius of the control run.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import tomllib
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jetfit.core.input import Observation
from jetfit.models.powerlawVegas import powerlawVegasModel
from jetfit.models.powerlawJetVegasDylanSpectrum import PowerlawJetVegasDylanSpectrumModel
from jetfit.models.powerlawVegasDylanSpectrum import powerlawVegasDylanSpectrumModel


SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")
MODEL_NAME_MAP = {
    "powerlawVegasModel": powerlawVegasModel,
    "powerlawVegasDylanSpectrumModel": powerlawVegasDylanSpectrumModel,
    "PowerlawJetVegasDylanSpectrumModel": PowerlawJetVegasDylanSpectrumModel,
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


def _by_name(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = _entry_name(entry)
        if name is not None:
            out[name] = entry
    return out


def _load_fit_model(path: Path | None) -> dict[str, float]:
    if path is None or not path.exists():
        return {}

    payload = json.loads(path.read_text())
    if isinstance(payload.get("model"), dict):
        model = payload["model"]
    else:
        params = payload.get("params", {})
        model = params.get("model", {}) if isinstance(params, dict) else {}

    out: dict[str, float] = {}
    for key, value in model.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _set_initial_guess(entry: dict[str, Any], value: float) -> None:
    prior = entry.get("prior")
    if not isinstance(prior, dict):
        return

    if entry.get("scale") == "log":
        if value <= 0.0:
            return
        guess = math.log10(value)
    else:
        guess = float(value)

    lower = prior.get("lower")
    upper = prior.get("upper")
    if isinstance(lower, (int, float)):
        guess = max(float(lower), guess)
    if isinstance(upper, (int, float)):
        guess = min(float(upper), guess)

    prior["initial_guess"] = guess


def _value_from_entry(entry: dict[str, Any]) -> float:
    if "value" in entry:
        return float(entry["value"])

    prior = entry.get("prior")
    if not isinstance(prior, dict):
        raise ValueError(f"Entry has neither fixed value nor prior: {entry}")

    if "initial_guess" in prior:
        guess = float(prior["initial_guess"])
    else:
        lower = prior.get("lower")
        upper = prior.get("upper")
        if isinstance(lower, (int, float)) and isinstance(upper, (int, float)):
            guess = 0.5 * (float(lower) + float(upper))
        else:
            raise ValueError(f"Entry is missing an initial guess and finite bounds: {entry}")

    if entry.get("scale") == "log":
        return 10.0 ** guess
    return guess


def _instantiate_control_model(powerlaw: dict[str, Any]) -> powerlawVegasModel:
    model_name = str(powerlaw.get("name", "powerlawVegasDylanSpectrumModel"))
    model_cls = MODEL_NAME_MAP.get(model_name)
    if model_cls is None:
        raise ValueError(f"Unsupported control model for radius seeding: {model_name}")

    kwargs: dict[str, float] = {}
    for entry in powerlaw.get("model", []):
        if not isinstance(entry, dict):
            continue
        name = _entry_name(entry)
        if name is None:
            continue
        kwargs[name] = _value_from_entry(entry)

    return model_cls(**kwargs)


def _sampled_rt_seed(powerlaw: dict[str, Any], obs_path: Path, factor: float) -> float:
    obs = Observation.from_csv(obs_path)
    times = np.asarray(obs.times(), dtype=float)
    times = times[np.isfinite(times)]
    if times.size == 0:
        raise ValueError(f"No valid observation times found in {obs_path}")

    model = _instantiate_control_model(powerlaw)
    radii = np.asarray(model.radii(np.array([times.min()])), dtype=float)
    radius = float(radii[0])
    if not np.isfinite(radius) or radius <= 0.0:
        raise ValueError(f"Invalid control-model radius seed from {obs_path}: {radius}")

    return factor * radius


def _derived_bubble_medium_seed(
    powerlaw: dict[str, Any],
    obs_path: Path,
    *,
    rt_seed_cm: float,
) -> dict[str, float]:
    """
    Derive nt/nism seeds from the current top-hat power-law fit.

    When no older bubble fit exists, use the power-law control profile
    n(r) = n017 * (r / 1e17 cm)^(-k) to seed:
      - nt   at the seeded termination-shock radius rt
      - nism at the latest sampled control radius
    """
    obs = Observation.from_csv(obs_path)
    times = np.asarray(obs.times(), dtype=float)
    times = times[np.isfinite(times)]
    if times.size == 0:
        return {}

    model = _instantiate_control_model(powerlaw)
    if not hasattr(model, "n017") or not hasattr(model, "k"):
        return {}

    radii = np.asarray(model.radii(np.array([times.min(), times.max()])), dtype=float)
    if radii.size == 0 or not np.all(np.isfinite(radii)):
        return {}

    ref_radius = float(getattr(model, "ref_radius", 1.0e17))
    n017 = float(getattr(model, "n017"))
    k = float(getattr(model, "k"))
    outer_radius = max(float(np.nanmax(radii)), float(rt_seed_cm) * 1.25)

    def n_at(radius_cm: float) -> float:
        radius_safe = max(float(radius_cm), 1.0)
        value = n017 * (radius_safe / ref_radius) ** (-k)
        return max(float(value), 1.0e-300)

    return {
        "nt": n_at(rt_seed_cm),
        "nism": n_at(outer_radius),
    }


def _set_rt_seed(entry: dict[str, Any], radius_seed: float, sigma_scale: float) -> None:
    _set_initial_guess(entry, radius_seed)
    prior = entry.get("prior")
    if not isinstance(prior, dict):
        return

    sigma = prior.get("initial_sigma")
    if isinstance(sigma, (int, float)):
        prior["initial_sigma"] = abs(float(sigma)) * sigma_scale


def build_bubble_config(
    powerlaw: dict[str, Any],
    bubble_template: dict[str, Any],
    *,
    control_seed: dict[str, float],
    bubble_seed: dict[str, float],
    obs_path: Path,
    rt_factor: float,
    rt_sigma_scale: float,
    model_name: str,
) -> dict[str, Any]:
    powerlaw_copy = copy.deepcopy(powerlaw)
    powerlaw_model_by_name = _by_name(powerlaw_copy.get("model", []))
    bubble_model_by_name = _by_name(bubble_template.get("model", []))

    for name, value in control_seed.items():
        entry = powerlaw_model_by_name.get(name)
        if entry is not None:
            _set_initial_guess(entry, value)

    synced: dict[str, Any] = {"name": model_name}
    merged_model: list[dict[str, Any]] = []

    for entry in bubble_template.get("model", []):
        name = _entry_name(entry)
        if name is not None and name in powerlaw_model_by_name:
            merged_entry = copy.deepcopy(powerlaw_model_by_name[name])
        else:
            merged_entry = copy.deepcopy(entry)
            if name is not None and name in bubble_seed:
                _set_initial_guess(merged_entry, bubble_seed[name])
        merged_model.append(merged_entry)

    rt_entry = _by_name(merged_model).get("rt")
    if rt_entry is None:
        raise ValueError("Bubble template is missing the rt parameter.")

    radius_seed = _sampled_rt_seed(powerlaw_copy, obs_path, rt_factor)
    derived_bubble_seed = _derived_bubble_medium_seed(
        powerlaw_copy,
        obs_path,
        rt_seed_cm=radius_seed,
    )

    merged_model_by_name = _by_name(merged_model)
    for param_name in ("nt", "nism"):
        if param_name in bubble_seed:
            continue
        entry = merged_model_by_name.get(param_name)
        if entry is None or param_name not in derived_bubble_seed:
            continue
        _set_initial_guess(entry, derived_bubble_seed[param_name])

    _set_rt_seed(rt_entry, radius_seed, rt_sigma_scale)

    synced["model"] = merged_model

    for section in ("extinction", "offsets", "host", "slop"):
        if section in powerlaw_copy:
            synced[section] = copy.deepcopy(powerlaw_copy[section])
        elif section in bubble_template:
            synced[section] = copy.deepcopy(bubble_template[section])

    return synced


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Dylan-smoothed bubble TOML.")
    parser.add_argument("--powerlaw", required=True, help="Control top-hat powerlaw TOML.")
    parser.add_argument("--bubble-template", required=True, help="Bubble template TOML.")
    parser.add_argument("--output", required=True, help="Output TOML path.")
    parser.add_argument("--obs", required=True, help="Observation CSV used to seed rt.")
    parser.add_argument("--seed-best-fit", type=Path, default=None, help="Best-fit or minimized JSON for shared control params.")
    parser.add_argument("--bubble-seed", type=Path, default=None, help="Optional old bubble best-fit/minimized JSON for nt/nism seeds.")
    parser.add_argument("--rt-factor", type=float, default=0.9, help="Seed rt at factor * earliest sampled radius.")
    parser.add_argument("--rt-sigma-scale", type=float, default=0.05, help="Scale factor applied to template rt initial_sigma.")
    parser.add_argument("--model-name", default="BubbleVegasDylanSpectrumModel", help="Model name to write.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    powerlaw_path = Path(args.powerlaw)
    bubble_template_path = Path(args.bubble_template)
    output_path = Path(args.output)
    obs_path = Path(args.obs)

    powerlaw = tomllib.loads(powerlaw_path.read_text())
    bubble_template = tomllib.loads(bubble_template_path.read_text())
    control_seed = _load_fit_model(args.seed_best_fit)
    bubble_seed = _load_fit_model(args.bubble_seed)

    config = build_bubble_config(
        powerlaw,
        bubble_template,
        control_seed=control_seed,
        bubble_seed=bubble_seed,
        obs_path=obs_path,
        rt_factor=args.rt_factor,
        rt_sigma_scale=args.rt_sigma_scale,
        model_name=args.model_name,
    )
    _write_toml(output_path, config)

    rt_entry = _by_name(config["model"])["rt"]
    rt_prior = rt_entry.get("prior", {})
    print(f"Wrote Dylan bubble config: {output_path}")
    print(f"  powerlaw:     {powerlaw_path}")
    print(f"  bubble seed:  {args.bubble_seed if args.bubble_seed else 'none'}")
    print(f"  control seed: {args.seed_best_fit if args.seed_best_fit else 'none'}")
    print(f"  obs:          {obs_path}")
    print(f"  model:        {config['name']}")
    print(f"  rt guess:     {rt_prior.get('initial_guess')}")
    print(f"  rt sigma:     {rt_prior.get('initial_sigma')}")


if __name__ == "__main__":
    main()
