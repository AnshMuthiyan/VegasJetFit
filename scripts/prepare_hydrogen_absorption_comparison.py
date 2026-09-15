#!/usr/bin/env python3
"""Prepare matched posterior-cloud tests of IGM and host H I absorption."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import toml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jetfit.core.bandpass import get_bandpass
from jetfit.mcmc.parameters import (
    Parameters,
    add_hydrogen_absorption_toml_comments,
    add_source_extinction_toml_comments,
    source_extinction_model_from_config,
)


VARIANTS = {
    "none": ("none", "none"),
    "igm": ("inoue2014", "none"),
    "igm_host": ("inoue2014", "trotter2011"),
}
MCMC_SMOKE = """# Finite-model and sampler smoke test.\n\n[sampler]\nname = 'parallel_tempered'\nnum_walkers = 100\nburn_length = 2\nrun_length = 3\nntemps = 5\nworkers = 8\ncheckpoint_interval = 1\n"""
MCMC_DIAGNOSTIC = """# Short controlled absorption comparison for the meeting.\n\n[sampler]\nname = 'parallel_tempered'\nnum_walkers = 100\nburn_length = 25\nrun_length = 100\nntemps = 5\nworkers = 8\ncheckpoint_interval = 10\n"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fitted_names(model_path: Path) -> list[str]:
    params = Parameters.from_toml(model_path)
    return [str(parameter.name) for parameter in params.fitting]


def known_redshift(config: dict) -> float:
    redshifts = [
        entry for entry in config.get("model", [])
        if entry.get("name") == "z" and "value" in entry
    ]
    if len(redshifts) != 1:
        raise ValueError("Expected exactly one fixed source redshift z.")
    redshift = float(redshifts[0]["value"])
    if not np.isfinite(redshift) or redshift < 0.0:
        raise ValueError("Source redshift must be finite and non-negative.")
    return redshift


def host_nhi_parameter(lower: float, upper: float) -> dict:
    center = min(max(21.0, lower + 0.25), upper - 0.25)
    return {
        "name": "nhi_host",
        "scale": "log",
        "prior": {
            "type": "uniform",
            "lower": float(lower),
            "upper": float(upper),
            "initial_guess": center,
            "initial_sigma": 0.5,
        },
    }


def target_config(
    source: dict,
    variant: str,
    nhi_lower: float,
    nhi_upper: float,
) -> dict:
    config = copy.deepcopy(source)
    config["source_extinction_model"] = source_extinction_model_from_config(
        config
    )
    igm_model, host_model = VARIANTS[variant]
    config["igm_absorption_model"] = igm_model
    config["host_hi_absorption_model"] = host_model
    config.pop("absorption", None)
    if host_model != "none":
        config["absorption"] = [host_nhi_parameter(nhi_lower, nhi_upper)]
    return config


def render_config(config: dict) -> str:
    rendered = toml.dumps(config)
    rendered = add_source_extinction_toml_comments(rendered)
    return add_hydrogen_absorption_toml_comments(rendered)


def load_source_samples(source: Path, source_names: list[str]) -> np.ndarray:
    with np.load(source / "chain.npz", allow_pickle=False) as archive:
        chain = np.asarray(archive["chain"], dtype=float)
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if chain.ndim != 3 or chain.shape[-1] != len(source_names):
        raise ValueError(f"Unexpected source chain shape {chain.shape}.")
    samples = chain.reshape(-1, chain.shape[-1])
    return samples[np.isfinite(samples).all(axis=1)]


def included_band_inventory(obs_path: Path) -> list[dict]:
    with obs_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    included = [
        row for row in rows
        if str(row.get("Include", "")).strip().lower() in {"1", "true", "yes"}
        and row.get("ValueType") == "Spectral Flux"
    ]
    counts = Counter(row.get("Filter", "") for row in included)
    return [
        {
            "filter": band,
            "included_rows": count,
            "response_treatment": (
                "verified_full_response"
                if get_bandpass(band) is not None
                else "central_wavelength_approximation"
            ),
        }
        for band, count in sorted(counts.items(), key=lambda item: item[0].lower())
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--source-results", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--ntemps", type=int, default=5)
    parser.add_argument("--nwalkers", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--nhi-lower", type=float, default=18.0)
    parser.add_argument("--nhi-upper", type=float, default=23.5)
    args = parser.parse_args()

    if args.nhi_upper <= args.nhi_lower:
        raise ValueError("The host N_HI upper bound must exceed the lower bound.")
    source = args.source_results.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    event_root = output_root / args.event
    source_model = source / "model.toml"
    source_obs = source / "obs.csv"
    source_config = toml.load(source_model)
    redshift = known_redshift(source_config)
    source_names = fitted_names(source_model)
    samples = load_source_samples(source, source_names)
    total = args.ntemps * args.nwalkers
    if samples.shape[0] < total:
        raise ValueError(f"Need {total} source samples; found {samples.shape[0]}.")

    rng = np.random.default_rng(args.seed)
    selected_indices = rng.choice(samples.shape[0], size=total, replace=False)
    selected = samples[selected_indices]
    host_nhi = np.clip(
        rng.normal(21.0, 0.5, size=total),
        args.nhi_lower,
        args.nhi_upper,
    )
    variants = {}

    for variant in VARIANTS:
        variant_root = event_root / variant
        variant_root.mkdir(parents=True, exist_ok=True)
        config = target_config(
            source_config, variant, args.nhi_lower, args.nhi_upper
        )
        model_path = variant_root / "model.toml"
        model_path.write_text(render_config(config), encoding="utf-8")
        shutil.copy2(source_obs, variant_root / "obs.csv")
        target_names = fitted_names(model_path)
        shared_names = [name for name in target_names if name != "nhi_host"]
        if shared_names != source_names:
            raise ValueError(
                f"{variant} changed source parameter order: "
                f"{shared_names} != {source_names}"
            )

        positions = np.empty(
            (args.ntemps, args.nwalkers, len(target_names)), dtype=float
        )
        for index, name in enumerate(target_names):
            values = (
                host_nhi if name == "nhi_host"
                else selected[:, source_names.index(name)]
            )
            positions[:, :, index] = values.reshape(
                args.ntemps, args.nwalkers
            )
        seed_path = variant_root / "initial_positions.npz"
        np.savez_compressed(
            seed_path,
            positions=positions,
            parameter_names=np.asarray(target_names),
            source_results=np.asarray(str(source)),
            source_sample_indices=selected_indices,
            rng_seed=int(args.seed),
        )
        variants[variant] = {
            "igm_absorption_model": VARIANTS[variant][0],
            "host_hi_absorption_model": VARIANTS[variant][1],
            "model_sha256": sha256(model_path),
            "obs_sha256": sha256(variant_root / "obs.csv"),
            "seed_sha256": sha256(seed_path),
            "seed_shape": list(positions.shape),
            "fitted_parameters": target_names,
        }

    (output_root / "mcmc_smoke_5temp_2x3.toml").write_text(MCMC_SMOKE)
    (output_root / "mcmc_diagnostic_5temp_25x100.toml").write_text(
        MCMC_DIAGNOSTIC
    )
    provenance = {
        "event": args.event,
        "source_redshift": redshift,
        "purpose": (
            "Controlled posterior-cloud comparison separating mean IGM "
            "attenuation from optional fitted host neutral-hydrogen absorption."
        ),
        "source_results": str(source),
        "source_model_sha256": sha256(source_model),
        "source_chain_sha256": sha256(source / "chain.npz"),
        "source_obs_sha256": sha256(source_obs),
        "source_finite_samples": int(samples.shape[0]),
        "selected_source_sample_indices_sha256": hashlib.sha256(
            np.asarray(selected_indices, dtype=np.int64).tobytes()
        ).hexdigest(),
        "matched_cloud": (
            "All variants use the same 500 draws from the authoritative "
            "correlated cold posterior; only the host model adds log10(N_HI)."
        ),
        "host_nhi_log10_prior": [args.nhi_lower, args.nhi_upper],
        "filter_inventory": included_band_inventory(source_obs),
        "variants": variants,
    }
    provenance_path = event_root / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"event={args.event} z={redshift} source_samples={samples.shape[0]}")
    for variant, record in variants.items():
        print(
            f"{variant}: seed_shape={record['seed_shape']} "
            f"parameters={len(record['fitted_parameters'])}"
        )
    print(f"provenance={provenance_path}")


if __name__ == "__main__":
    main()
