#!/usr/bin/env python3
"""Prepare matched full-temperature clouds for the long 090424 dust comparison."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np


VARIANTS = ("ccm", "trotter")
SHORT_TAG = "090424_{variant}_bandpass_verified_5temp_25x100_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def section_by_name(config: dict, section: str) -> dict:
    return {entry["name"]: entry for entry in config.get(section, [])}


def validate_matched_configs(configs: dict[str, dict]) -> None:
    left, right = (configs[name] for name in VARIANTS)
    if left.get("name") != right.get("name"):
        raise ValueError("CCM and Trotter use different emission models.")
    for section in ("model", "offsets", "host", "slop"):
        if section_by_name(left, section) != section_by_name(right, section):
            raise ValueError(f"CCM and Trotter differ outside extinction: {section}")
    expected_models = {"ccm": "ccm89", "trotter": "trotter2011"}
    for variant, expected in expected_models.items():
        selected = configs[variant].get("source_extinction_model")
        if selected != expected:
            raise ValueError(
                f"{variant} config selects {selected!r}; expected {expected!r}."
            )


def validate_uniform_bounds(
    positions: np.ndarray, parameter_names: list[str], config: dict
) -> None:
    entries = []
    for section in ("model", "extinction", "offsets", "host", "slop"):
        entries.extend(config.get(section, []))
    by_name = {entry["name"]: entry for entry in entries}
    for index, name in enumerate(parameter_names):
        prior = by_name[name].get("prior", {})
        if prior.get("type") != "uniform":
            continue
        values = positions[..., index]
        lower = float(prior["lower"])
        upper = float(prior["upper"])
        if np.any(values < lower) or np.any(values > upper):
            raise ValueError(f"{name} has terminal walkers outside [{lower}, {upper}].")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config_root = root / "run_configs" / "bandpass_integration"
    result_root = root / "jetfit" / "results"

    configs = {}
    obs_hashes = set()
    records = {}
    for variant in VARIANTS:
        config_dir = config_root / f"090424_{variant}"
        model_path = config_dir / "model.toml"
        with model_path.open("rb") as handle:
            configs[variant] = tomllib.load(handle)
        obs_hashes.add(sha256(config_dir / "obs.csv"))

    validate_matched_configs(configs)
    if len(obs_hashes) != 1:
        raise ValueError("CCM and Trotter observation files are not identical.")

    for variant in VARIANTS:
        config_dir = config_root / f"090424_{variant}"
        source = result_root / SHORT_TAG.format(variant=variant)
        state_path = source / "pt_resume_state.npz"
        seed_metadata = config_dir / "initial_positions.npz"
        with np.load(state_path, allow_pickle=False) as state:
            positions = np.asarray(state["last_pos"], dtype=float)
            phase = str(np.asarray(state["phase"]).item())
            completed = int(state["completed_iterations"])
            target = int(state["target_iterations"])
        with np.load(seed_metadata, allow_pickle=False) as seed:
            parameter_names = [str(name) for name in seed["parameter_names"]]

        expected = (5, 100, len(parameter_names))
        if positions.shape != expected:
            raise ValueError(f"{variant} terminal cloud {positions.shape} != {expected}.")
        if phase != "production" or completed < target:
            raise ValueError(
                f"{variant} source is incomplete: phase={phase}, {completed}/{target}."
            )
        if not np.isfinite(positions).all():
            raise ValueError(f"{variant} terminal cloud contains non-finite values.")
        validate_uniform_bounds(positions, parameter_names, configs[variant])

        output = config_dir / "initial_positions_long.npz"
        np.savez(
            output,
            positions=positions,
            parameter_names=np.asarray(parameter_names),
        )
        records[variant] = {
            "source_result": str(source.relative_to(root)),
            "source_checkpoint_sha256": sha256(state_path),
            "seed_path": str(output.relative_to(root)),
            "seed_sha256": sha256(output),
            "seed_shape": list(positions.shape),
            "parameter_count": len(parameter_names),
        }

    manifest = {
        "event": "090424",
        "purpose": "Long controlled comparison of CCM and Trotter host extinction",
        "controlled_inputs": {
            "observations_sha256": obs_hashes.pop(),
            "data": "all reviewed UV/optical/IR data; early X-ray flare excluded",
            "emission_model": configs["ccm"]["name"],
            "bandpass_integration": "verified photon-counting",
            "bandpass_nodes": 16,
            "vegas_grid": {"phi": 0.15, "theta": 0.5, "time": 15.0},
            "sampler": {
                "temperatures": 5,
                "walkers": 100,
                "burn": 100,
                "production": 800,
                "workers": 8,
                "checkpoint_interval": 50,
            },
        },
        "intentional_difference": (
            "Host extinction prescription and its required fitted coordinates: "
            "CCM uses E(B-V); Trotter uses A_V, c2, c4, and correlated dust-prior coordinates."
        ),
        "variants": records,
    }
    manifest_path = config_root / "090424_extinction_long_comparison.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
