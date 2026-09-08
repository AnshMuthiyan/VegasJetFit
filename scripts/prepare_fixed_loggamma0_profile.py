#!/usr/bin/env python3
"""Prepare projected posterior-cloud inputs for a fixed-log10(Gamma0) profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tomllib
from pathlib import Path

import numpy as np

SECTIONS = ("model", "extinction", "offsets", "host", "slop")
PARAMETER = "Gamma_0_core_avg"


def fitted_names(path: Path) -> list[str]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    return [
        str(entry["name"])
        for section in SECTIONS
        for entry in config.get(section, [])
        if isinstance(entry, dict) and isinstance(entry.get("prior"), dict)
    ]


def fix_loggamma_block(text: str, loggamma: float) -> str:
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.strip() == "[[model]]"]
    for start in starts:
        end = next((i for i in starts if i > start), len(lines))
        block = "".join(lines[start:end])
        if f"name = '{PARAMETER}'" not in block:
            continue
        replacement = (
            "[[model]]\n"
            f"name = '{PARAMETER}'\n"
            "scale = 'log'\n"
            f"value = {loggamma:.1f}\n\n"
        )
        return "".join(lines[:start]) + replacement + "".join(lines[end:])
    raise ValueError(f"Could not find {PARAMETER!r} model block.")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def label(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value).replace(".", "p")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-results", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--obs-out", type=Path, required=True)
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--event", default="080413B")
    parser.add_argument("--loggammas", nargs="+", type=float, required=True)
    args = parser.parse_args()

    source = args.source_results.expanduser().resolve()
    source_model = source / "model.toml"
    source_obs = source / "obs.csv"
    source_chain = source / "chain.npz"
    source_best = source / "best_fit.json"
    for required in (source_model, source_obs, source_chain, source_best):
        if not required.is_file():
            raise FileNotFoundError(required)

    args.results_root.mkdir(parents=True, exist_ok=True)
    args.config_dir.mkdir(parents=True, exist_ok=True)
    args.obs_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_obs, args.obs_out)

    names = fitted_names(source_model)
    gamma_index = names.index(PARAMETER)
    projected_names = names[:gamma_index] + names[gamma_index + 1 :]
    with np.load(source_chain, allow_pickle=False) as payload:
        chain = np.asarray(payload["chain"], dtype=float)
        lnprob = np.asarray(payload["lnprob"], dtype=float)
        betas = np.asarray(payload["betas"], dtype=float) if "betas" in payload else None
    if chain.shape[-1] != len(names):
        raise ValueError(f"Source chain dimension {chain.shape[-1]} != {len(names)} fitted parameters.")
    projected_chain = np.delete(chain, gamma_index, axis=-1)
    source_best_payload = json.loads(source_best.read_text())

    prepared: list[dict[str, object]] = []
    model_text = source_model.read_text()
    for value in args.loggammas:
        value_label = label(value)
        run_name = f"{args.event}_loggamma0_{value_label}_{args.run_tag}"
        config_path = args.config_dir / f"{args.event}_loggamma0_{value_label}.toml"
        config_path.write_text(fix_loggamma_block(model_text, value))
        if fitted_names(config_path) != projected_names:
            raise ValueError(f"Projected parameter order mismatch for {config_path}.")

        run_dir = args.results_root / run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_path, run_dir / "model.toml")
        shutil.copy2(args.obs_out, run_dir / "obs.csv")
        best = json.loads(json.dumps(source_best_payload))
        best["model"][PARAMETER] = 10.0**value
        best["profile_seed_source_nmap"] = best.pop("nmap", None)
        best["profile_fixed_log10_gamma0"] = value
        (run_dir / "best_fit.json").write_text(json.dumps(best, indent=2) + "\n")
        chain_payload = {"chain": projected_chain, "lnprob": lnprob}
        if betas is not None:
            chain_payload["betas"] = betas
        np.savez_compressed(run_dir / "chain.npz", **chain_payload)
        prepared.append(
            {
                "log10_gamma0": value,
                "gamma0": 10.0**value,
                "run_name": run_name,
                "config": str(config_path),
                "result_dir": str(run_dir),
            }
        )

    provenance = {
        "event": args.event,
        "purpose": "Profile likelihood in fixed log10(Gamma_0_core_avg)",
        "method": "Project the authoritative posterior cloud by removing Gamma_0, then multistart-minimize every remaining fitted parameter at each fixed Gamma_0.",
        "source_results": str(source),
        "source_model_sha256": sha256(source_model),
        "source_obs_sha256": sha256(source_obs),
        "source_chain_sha256": sha256(source_chain),
        "fixed_parameter": PARAMETER,
        "fixed_scale": "log10",
        "projected_parameter_names": projected_names,
        "runs": prepared,
    }
    provenance_path = args.config_dir / "profile_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    print(provenance_path)


if __name__ == "__main__":
    main()
