#!/usr/bin/env python3
"""Build a correlated parallel-tempered seed cloud from a finished cold chain."""
from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import numpy as np

SECTIONS = ("model", "extinction", "offsets", "host", "slop")


def fitted_names(path: Path) -> list[str]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    return [
        str(entry["name"])
        for section in SECTIONS
        for entry in config.get(section, [])
        if isinstance(entry, dict) and isinstance(entry.get("prior"), dict)
    ]


def uniform_bounds(path: Path, name: str) -> tuple[float, float]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    for section in SECTIONS:
        for entry in config.get(section, []):
            if not isinstance(entry, dict) or entry.get("name") != name:
                continue
            prior = entry.get("prior")
            if not isinstance(prior, dict) or prior.get("type") != "uniform":
                raise ValueError(f"{name} must have a uniform target prior for ridge expansion.")
            return float(prior["lower"]), float(prior["upper"])
    raise ValueError(f"Target model has no fitted parameter named {name!r}.")


def apply_boundary_ridge_expansion(
    positions: np.ndarray,
    target_names: list[str],
    target_model: Path,
    *,
    parameter: str,
    coupled_parameter: str,
    coupled_factor: float,
    max_shift: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Spread hot ensembles along a bounded, user-specified degeneracy ridge.

    Temperature zero remains an exact posterior-cloud draw. Higher-temperature
    ensembles receive progressively broader positive shifts in ``parameter``
    and ``coupled_factor * shift`` in ``coupled_parameter``. Every realized
    shift is truncated against both target priors.
    """
    if parameter == coupled_parameter:
        raise ValueError("Ridge parameters must be distinct.")
    if coupled_factor == 0.0:
        raise ValueError("--ridge-coupled-factor must be nonzero.")
    if max_shift <= 0.0:
        raise ValueError("--ridge-max-shift must be positive.")

    parameter_index = target_names.index(parameter)
    coupled_index = target_names.index(coupled_parameter)
    _, parameter_upper = uniform_bounds(target_model, parameter)
    coupled_lower, coupled_upper = uniform_bounds(target_model, coupled_parameter)
    ntemps, nwalkers, _ = positions.shape
    deltas = np.zeros((ntemps, nwalkers), dtype=float)

    for temperature in range(1, ntemps):
        temperature_fraction = temperature / max(ntemps - 1, 1)
        caps = np.full(nwalkers, max_shift * temperature_fraction, dtype=float)
        parameter_values = positions[temperature, :, parameter_index]
        coupled_values = positions[temperature, :, coupled_index]
        caps = np.minimum(caps, parameter_upper - parameter_values)
        if coupled_factor > 0.0:
            caps = np.minimum(caps, (coupled_upper - coupled_values) / coupled_factor)
        else:
            caps = np.minimum(caps, (coupled_values - coupled_lower) / -coupled_factor)
        caps = np.maximum(caps, 0.0)
        delta = rng.uniform(0.0, 1.0, size=nwalkers) * caps
        positions[temperature, :, parameter_index] += delta
        positions[temperature, :, coupled_index] += coupled_factor * delta
        deltas[temperature] = delta

    return deltas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-results", type=Path, required=True)
    parser.add_argument("--target-model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ntemps", type=int, required=True)
    parser.add_argument("--nwalkers", type=int, required=True)
    parser.add_argument(
        "--new-parameter",
        default="s",
        help="Parameter absent from the source and newly initialized in the target; pass an empty string when source and target parameter sets are identical.",
    )
    parser.add_argument("--new-center", type=float, default=4.0)
    parser.add_argument("--new-sigma", type=float, default=0.4)
    parser.add_argument("--new-lower", type=float, default=2.0)
    parser.add_argument("--new-upper", type=float, default=10.0)
    parser.add_argument(
        "--ridge-parameter",
        default="",
        help="Optional fitted coordinate shifted positively in hotter ensembles; temperature zero is unchanged.",
    )
    parser.add_argument(
        "--ridge-coupled-parameter",
        default="",
        help="Second fitted coordinate shifted with --ridge-parameter to follow a known degeneracy.",
    )
    parser.add_argument(
        "--ridge-coupled-factor",
        type=float,
        default=-1.0,
        help="Change in the coupled coordinate per unit positive ridge shift.",
    )
    parser.add_argument(
        "--ridge-max-shift",
        type=float,
        default=0.0,
        help="Maximum ridge shift at the hottest temperature; intermediate temperatures scale linearly.",
    )
    parser.add_argument("--seed", type=int, default=90424)
    args = parser.parse_args()

    source = args.source_results.resolve()
    source_names = fitted_names(source / "model.toml")
    target_names = fitted_names(args.target_model.resolve())
    new_parameter = args.new_parameter or None
    if new_parameter is None:
        if target_names != source_names:
            raise ValueError("Without --new-parameter, source and target fitted parameters must match exactly.")
    else:
        shared = [name for name in target_names if name != new_parameter]
        if new_parameter not in target_names or shared != source_names:
            raise ValueError("Target parameters must equal source parameters plus the new parameter.")

    with np.load(source / "chain.npz", allow_pickle=False) as data:
        chain = np.asarray(data["chain"], dtype=float)
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if chain.ndim != 3 or chain.shape[-1] != len(source_names):
        raise ValueError(f"Unexpected source chain shape {chain.shape}.")
    samples = chain.reshape(-1, chain.shape[-1])
    samples = samples[np.isfinite(samples).all(axis=1)]
    total = args.ntemps * args.nwalkers
    if samples.shape[0] < total:
        raise ValueError(f"Need {total} finite source samples; found {samples.shape[0]}.")

    rng = np.random.default_rng(args.seed)
    chosen = samples[rng.choice(samples.shape[0], size=total, replace=False)]
    positions = np.empty((args.ntemps, args.nwalkers, len(target_names)), dtype=float)
    for index, name in enumerate(target_names):
        if name == new_parameter:
            values = np.clip(
                rng.normal(args.new_center, args.new_sigma, size=total),
                args.new_lower,
                args.new_upper,
            )
        else:
            values = chosen[:, source_names.index(name)]
        positions[:, :, index] = values.reshape(args.ntemps, args.nwalkers)

    ridge_args = (
        bool(args.ridge_parameter),
        bool(args.ridge_coupled_parameter),
        args.ridge_max_shift > 0.0,
    )
    if any(ridge_args) and not all(ridge_args):
        raise ValueError(
            "Ridge expansion requires --ridge-parameter, --ridge-coupled-parameter, "
            "and a positive --ridge-max-shift."
        )
    ridge_deltas = np.zeros((args.ntemps, args.nwalkers), dtype=float)
    if all(ridge_args):
        ridge_deltas = apply_boundary_ridge_expansion(
            positions,
            target_names,
            args.target_model.resolve(),
            parameter=args.ridge_parameter,
            coupled_parameter=args.ridge_coupled_parameter,
            coupled_factor=args.ridge_coupled_factor,
            max_shift=args.ridge_max_shift,
            rng=rng,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        positions=positions,
        parameter_names=np.asarray(target_names),
        source_results=np.asarray(str(source)),
        source_samples=int(samples.shape[0]),
        rng_seed=int(args.seed),
        ridge_parameter=np.asarray(args.ridge_parameter),
        ridge_coupled_parameter=np.asarray(args.ridge_coupled_parameter),
        ridge_coupled_factor=float(args.ridge_coupled_factor),
        ridge_max_shift=float(args.ridge_max_shift),
        ridge_deltas=ridge_deltas,
    )
    print(f"wrote={args.out} shape={positions.shape} source_samples={samples.shape[0]}")
    if all(ridge_args):
        realized = [
            f"T{temperature}:max={ridge_deltas[temperature].max():.6g}"
            for temperature in range(args.ntemps)
        ]
        print("ridge=" + ",".join(realized))


if __name__ == "__main__":
    main()
