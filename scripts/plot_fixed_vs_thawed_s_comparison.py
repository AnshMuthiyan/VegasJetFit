#!/usr/bin/env python3
"""Compare a fixed-s posterior with a corresponding thawed-s posterior."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.mcmc.parameters import Parameters
from scripts.generate_postfit_products import derive_jet_energy_posterior


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-results", required=True, type=Path)
    parser.add_argument("--thawed-results", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--event", required=True)
    return parser.parse_args()


def posterior_half(path: Path) -> tuple[np.ndarray, Parameters]:
    params = Parameters.from_toml(path / "model.toml")
    with np.load(path / "chain.npz") as data:
        chain = np.asarray(data["chain"], dtype=float)
    return chain[chain.shape[0] // 2 :].reshape(-1, chain.shape[-1]), params


def fitted_samples(chain: np.ndarray, params: Parameters, name: str) -> np.ndarray:
    names = [param.name for param in params.fitting]
    index = names.index(name)
    values = chain[:, index]
    return values[np.isfinite(values)]


def derived_posterior(
    path: Path,
    chain: np.ndarray,
    params: Parameters,
) -> dict[str, np.ndarray]:
    """Load saved derived samples or reproduce them from the immutable chain."""
    saved = path / "jet_energy_posterior.npz"
    if saved.is_file():
        with np.load(saved) as data:
            derived = {}
            for key in data.files:
                values = np.asarray(data[key])
                if np.issubdtype(values.dtype, np.number):
                    derived[key] = values.astype(float)
            return derived
    derived, _ = derive_jet_energy_posterior(chain, params, params.model)
    return derived


def derived_samples(derived: dict[str, np.ndarray], key: str, logarithmic: bool) -> np.ndarray:
    values = np.asarray(derived[key], dtype=float)
    values = values[np.isfinite(values)]
    if logarithmic:
        values = values[values > 0.0]
        values = np.log10(values)
    return values


def energy_mass_samples(derived: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Return aligned log-energy and log-mass posterior draws."""
    energy = np.asarray(derived["E_j_core_52"], dtype=float)
    mass = np.asarray(derived["M_j_core_msun"], dtype=float)
    valid = np.isfinite(energy) & np.isfinite(mass) & (energy > 0.0) & (mass > 0.0)
    return np.log10(energy[valid]), np.log10(mass[valid])


def summarize(values: np.ndarray) -> tuple[float, float, float]:
    q16, q50, q84 = np.quantile(values, [0.16, 0.5, 0.84])
    return float(q16), float(q50), float(q84)


def main() -> int:
    args = parse_args()
    fixed = args.fixed_results.expanduser().resolve()
    thawed = args.thawed_results.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    fixed_chain, fixed_params = posterior_half(fixed)
    thawed_chain, thawed_params = posterior_half(thawed)
    fixed_derived = derived_posterior(fixed, fixed_chain, fixed_params)
    thawed_derived = derived_posterior(thawed, thawed_chain, thawed_params)
    specs = (
        ("E_j_core_52", r"$\log_{10}(E_{j,\mathrm{core}}/10^{52}\,\mathrm{erg})$", "derived", True),
        ("Gamma_0_core_avg", r"$\log_{10}\langle\Gamma_0\rangle_{\mathrm{core}}$", "derived", True),
        ("M_j_core_msun", r"$\log_{10}(M_{j,\mathrm{core}}/M_\odot)$", "derived", True),
        ("n017", r"$\log_{10}(n_{0,17})$", "fitted", False),
        ("eps_e", r"$\log_{10}(\epsilon_e)$", "fitted", False),
        ("eps_b", r"$\log_{10}(\epsilon_B)$", "fitted", False),
        ("p", r"$p$", "fitted", False),
        ("k", r"$k$", "fitted", False),
        ("theta_c", r"$\log_{10}(\theta_c/\mathrm{rad})$", "fitted", False),
        ("theta_v", r"$\log_{10}(\theta_v/\mathrm{rad})$", "fitted", False),
        ("ebv_source_frame", r"$E(B-V)_{\mathrm{source}}$ [mag]", "fitted", False),
        ("s", r"$s$", "fitted", False),
    )
    rows = []
    panels = []
    fixed_names = [param.name for param in fixed_params.fitting]
    thawed_names = [param.name for param in thawed_params.fitting]
    for key, label, source, logarithmic in specs:
        fixed_value = None
        if source == "derived":
            fixed_values = derived_samples(fixed_derived, key, logarithmic)
            thawed_values = derived_samples(thawed_derived, key, logarithmic)
        elif key == "s":
            fixed_value = 4.0
            if key not in thawed_names:
                continue
            fixed_values = np.empty(0, dtype=float)
            thawed_values = fitted_samples(thawed_chain, thawed_params, key)
        else:
            if key not in fixed_names or key not in thawed_names:
                continue
            fixed_values = fitted_samples(fixed_chain, fixed_params, key)
            thawed_values = fitted_samples(thawed_chain, thawed_params, key)
        if thawed_values.size == 0 or (key != "s" and fixed_values.size == 0):
            continue
        panels.append((key, label, fixed_values, thawed_values, fixed_value))
        thawed_q16, thawed_q50, thawed_q84 = summarize(thawed_values)
        if key == "s":
            fixed_q16 = fixed_q50 = fixed_q84 = fixed_value
        else:
            fixed_q16, fixed_q50, fixed_q84 = summarize(fixed_values)
        rows.append({
            "parameter": key,
            "fixed_s_q16": fixed_q16,
            "fixed_s_median": fixed_q50,
            "fixed_s_q84": fixed_q84,
            "thawed_s_q16": thawed_q16,
            "thawed_s_median": thawed_q50,
            "thawed_s_q84": thawed_q84,
        })

    figure, axes = plt.subplots(3, 4, figsize=(15.2, 9.4))
    for axis, (key, label, fixed_values, thawed_values, fixed_value) in zip(axes.flat, panels):
        combined = thawed_values if key == "s" else np.concatenate((fixed_values, thawed_values))
        lo, hi = np.quantile(combined, [0.002, 0.998])
        pad = max((hi - lo) * 0.08, 1e-5)
        bins = np.linspace(lo - pad, hi + pad, 48)
        if key != "s":
            axis.hist(fixed_values, bins=bins, density=True, histtype="step", lw=1.55,
                      color="#2558c5", label="fixed $s=4$")
        else:
            axis.axvline(fixed_value, color="#2558c5", lw=1.55, label="fixed $s=4$")
        axis.hist(thawed_values, bins=bins, density=True, histtype="step", lw=1.55,
                  color="#c64037", label="thawed $s$")
        axis.set_xlabel(label, fontsize=10)
        axis.set_yticks([])
        axis.grid(alpha=0.18)
    for axis in axes.flat[len(panels):]:
        axis.set_visible(False)
    axes.flat[0].legend(frameon=False, fontsize=9, loc="best")
    figure.suptitle(f"GRB {args.event}: Fixed-$s$ versus Thawed-$s$ Posterior Comparison", fontsize=15)
    figure.tight_layout(rect=(0, 0, 1, 0.96))

    stem = output_dir / "fixed_s_vs_thawed_s_posterior_comparison"
    figure.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    figure.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    plt.close(figure)
    with stem.with_suffix(".csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    fixed_energy, fixed_mass = energy_mass_samples(fixed_derived)
    thawed_energy, thawed_mass = energy_mass_samples(thawed_derived)
    rng = np.random.default_rng(90424)
    figure, axis = plt.subplots(figsize=(8.3, 6.8))
    for energy, mass, color, label in (
        (fixed_energy, fixed_mass, "#2558c5", "fixed $s=4$"),
        (thawed_energy, thawed_mass, "#c64037", "thawed $s$"),
    ):
        take = min(15000, energy.size)
        indices = rng.choice(energy.size, size=take, replace=False)
        axis.scatter(energy[indices], mass[indices], s=3.0, alpha=0.10,
                     color=color, edgecolors="none", label=label)
    axis.set_xlabel(r"$\log_{10}(E_{j,\mathrm{core}}/10^{52}\,\mathrm{erg})$", fontsize=12)
    axis.set_ylabel(r"$\log_{10}(M_{j,\mathrm{core}}/M_\odot)$", fontsize=12)
    axis.set_title(f"GRB {args.event}: Core Mass versus Core Energy", fontsize=14)
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    figure.tight_layout()
    mass_energy_stem = output_dir / "fixed_s_vs_thawed_s_core_mass_vs_energy"
    figure.savefig(mass_energy_stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    figure.savefig(mass_energy_stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
