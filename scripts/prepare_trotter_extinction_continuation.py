#!/usr/bin/env python3
"""Prepare a Trotter-extinction config and posterior-cloud seed from a run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import toml

from jetfit.mcmc.trotter_extinction import TrotterDustPrior


SECTIONS = ("model", "extinction", "offsets", "host", "slop")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fitted_names(config):
    return [
        entry["name"]
        for section in SECTIONS
        for entry in config.get(section, [])
        if isinstance(entry.get("prior"), dict)
    ]


def uniform_parameter(name, lower, upper, initial_guess, initial_sigma):
    return {
        "name": name,
        "scale": "linear",
        "prior": {
            "type": "uniform",
            "lower": float(lower),
            "upper": float(upper),
            "initial_guess": float(initial_guess),
            "initial_sigma": float(initial_sigma),
        },
    }


def build_target_config(source_config, av_guess):
    config = dict(source_config)
    extinction = [
        entry
        for entry in config.get("extinction", [])
        if entry.get("name") != "ebv_source_frame"
    ]
    extinction[:0] = [
        uniform_parameter("av_source_frame", 0.0, 10.0, av_guess, max(0.05, 0.2 * av_guess)),
        uniform_parameter("c2", -1.0, 3.5, 1.0, 0.2),
        uniform_parameter("c4", 0.0, 2.0, 0.5, 0.25),
    ]
    prior = TrotterDustPrior()
    for name, (sigma_plus, sigma_minus) in prior.delta_sigmas.items():
        extinction.append(
            uniform_parameter(
                name,
                -5.0 * sigma_minus,
                5.0 * sigma_plus,
                0.0,
                min(sigma_plus, sigma_minus),
            )
        )
    config["extinction"] = extinction
    return config


def source_chain(path, expected_names):
    with np.load(path, allow_pickle=False) as archive:
        chain = np.asarray(archive["chain"], dtype=float)
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if chain.ndim != 3 or chain.shape[-1] != len(expected_names):
        raise ValueError(f"Unexpected source chain shape {chain.shape}")
    if chain.shape[1] != 100:
        raise ValueError(f"Expected the retained 100-walker cloud; found {chain.shape[1]} walkers")
    return chain


def draw_dust_seed(rng, prior, old_ebv):
    for _ in range(10_000):
        values = {
            "av_source_frame": float(np.clip(3.1 * old_ebv, 1.0e-6, 10.0)),
            "c2": float(np.clip(rng.normal(1.0, 0.20), -1.0, 3.5)),
            "c4": float(rng.uniform(0.0, 2.0)),
        }
        for name, (sigma_plus, sigma_minus) in prior.delta_sigmas.items():
            positive = rng.random() < sigma_plus / (sigma_plus + sigma_minus)
            sigma = sigma_plus if positive else sigma_minus
            sign = 1.0 if positive else -1.0
            values[name] = float(sign * abs(rng.normal(0.0, sigma)))
        if np.isfinite(prior.log_prior(values)):
            return values
    raise RuntimeError("Could not draw a physically valid Trotter dust seed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-results", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--ntemps", type=int, default=5)
    parser.add_argument("--seed", type=int, default=90424)
    args = parser.parse_args()

    source = args.source_results.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source_model = source / "model.toml"
    source_chain_path = source / "chain.npz"
    source_obs = source / "obs.csv"
    source_config = toml.load(source_model)
    source_names = fitted_names(source_config)
    chain = source_chain(source_chain_path, source_names)

    ebv_index = source_names.index("ebv_source_frame")
    av_guess = float(3.1 * np.nanmedian(chain[-1, :, ebv_index]))
    target_config = build_target_config(source_config, av_guess)
    target_model = output / "model.toml"
    target_model.write_text(toml.dumps(target_config), encoding="utf-8")
    target_names = fitted_names(target_config)

    if chain.shape[0] < args.ntemps:
        raise ValueError(f"Need at least {args.ntemps} source iterations")
    source_cloud = chain[-args.ntemps :, :, :]
    positions = np.empty((args.ntemps, 100, len(target_names)), dtype=float)
    rng = np.random.default_rng(args.seed)
    prior = TrotterDustPrior()
    dust_names = {"av_source_frame", "c2", "c4", *prior.delta_sigmas}

    for temperature in range(args.ntemps):
        for walker in range(100):
            source_row = source_cloud[temperature, walker]
            dust = draw_dust_seed(rng, prior, source_row[ebv_index])
            for index, name in enumerate(target_names):
                positions[temperature, walker, index] = (
                    dust[name] if name in dust_names else source_row[source_names.index(name)]
                )

    seed_path = output / "initial_positions.npz"
    np.savez_compressed(
        seed_path,
        positions=positions,
        parameter_names=np.asarray(target_names),
        source_results=np.asarray(str(source)),
        source_terminal_iterations=np.arange(chain.shape[0] - args.ntemps, chain.shape[0]),
        rng_seed=args.seed,
    )
    provenance = {
        "purpose": "Posterior-cloud continuation with Trotter source-frame extinction",
        "source_results": str(source),
        "source_model_sha256": sha256(source_model),
        "source_chain_sha256": sha256(source_chain_path),
        "source_obs_sha256": sha256(source_obs),
        "source_terminal_iterations": list(range(chain.shape[0] - args.ntemps, chain.shape[0])),
        "retained_walkers_per_temperature": 100,
        "target_model": str(target_model),
        "target_fitted_parameters": target_names,
        "dust_hyperparameters": "fixed at Trotter thesis Tables 3.2--3.5 peak values",
        "dust_hard_bounds": {"av_source_frame": [0, 10], "c2": [-1, 3.5], "bh_derived": [0, 10], "c4": [0, 2]},
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"model={target_model}")
    print(f"seed={seed_path} shape={positions.shape}")


if __name__ == "__main__":
    main()
