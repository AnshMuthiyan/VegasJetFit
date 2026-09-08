#!/usr/bin/env python3
"""Plot campaign-level posterior comparisons for shared physical parameters."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys
import zlib

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.mcmc.parameters import Parameters


MANIFEST_NAME = "physical_parameter_histograms_manifest.csv"
MANIFEST_FIELDS = (
    "parameter",
    "output_stem",
    "plotted_scale",
    "n_events",
    "samples_per_event",
)
DENSITY_K_SCATTER_STEM = "density_n017_vs_csm_slope_k_posterior_scatter"


def is_campaign_event_dir(path: Path) -> bool:
    """Return true for canonical event folders, not side-by-side comparisons."""
    name = path.name
    return (
        path.is_dir()
        and name != "trash"
        and not name.startswith((".", "_"))
        and "_no_" not in name
    )


@dataclass(frozen=True)
class ParameterSpec:
    key: str
    output_stem: str
    xlabel: str
    title: str
    source: str = "chain"
    transform: str = "identity"
    note: str = ""


PARAMETERS = (
    ParameterSpec(
        "E_j_core_52",
        "jet_core_energy_posterior_histogram",
        r"$\log_{10}(E_{j,\mathrm{core}}/10^{52}\,\mathrm{erg})$",
        "Two-Sided Core Jet-Energy Posterior Distributions",
        source="derived",
        transform="log10",
        note=r"$E_{j,\mathrm{core}}=2\int_0^{\theta_c}(dE/d\Omega)\,d\Omega$",
    ),
    ParameterSpec(
        "Gamma_0_core_avg",
        "gamma0_core_average_posterior_histogram",
        r"$\log_{10}\langle\Gamma_0\rangle_{\mathrm{core}}$",
        "Core-Averaged Initial Lorentz-Factor Posterior Distributions",
        source="derived",
        transform="log10",
        note=(
            r"$\langle\Gamma_0\rangle_{\mathrm{core}}="
            r"\int_0^{\theta_c}\Gamma_0(\theta)\sin\theta\,d\theta/"
            r"(1-\cos\theta_c)$"
        ),
    ),
    ParameterSpec(
        "M_j_core_msun",
        "jet_mass_posterior_histogram",
        r"$\log_{10}(M_{j,\mathrm{core}}/M_\odot)$",
        "Two-Sided Core Jet-Mass Posterior Distributions",
        source="derived",
        transform="log10",
        note=(
            r"$M_{j,\mathrm{core}}=2\int_0^{\theta_c}"
            r"[(dE/d\Omega)/(\Gamma_0(\theta)c^2)]\,d\Omega$"
        ),
    ),
    ParameterSpec(
        "E_j_core_52_per_sr",
        "jet_core_energy_per_solid_angle_posterior_histogram",
        r"$\log_{10}[\langle dE_j/d\Omega\rangle_{\mathrm{core}}/"
        r"(10^{52}\,\mathrm{erg\,sr^{-1}})]$",
        "Average Core Jet Energy per Solid Angle",
        source="derived_ratio",
        transform="log10",
        note=(
            r"$\langle dE_j/d\Omega\rangle_{\mathrm{core}}"
            r"=E_{j,\mathrm{core}}/(2\pi\theta_c^2)$"
        ),
    ),
    ParameterSpec(
        "M_j_core_msun_per_sr",
        "jet_core_mass_per_solid_angle_posterior_histogram",
        r"$\log_{10}[\langle dM_j/d\Omega\rangle_{\mathrm{core}}/"
        r"(M_\odot\,\mathrm{sr^{-1}})]$",
        "Average Core Ejecta Mass per Solid Angle",
        source="derived_ratio",
        transform="log10",
        note=(
            r"$\langle dM_j/d\Omega\rangle_{\mathrm{core}}"
            r"=M_{j,\mathrm{core}}/(2\pi\theta_c^2)$"
        ),
    ),
    ParameterSpec(
        "n017",
        "density_n017_posterior_histogram",
        r"$\log_{10}(n_{0,17})$",
        "Density Normalization Posterior Distributions",
    ),
    ParameterSpec(
        "eps_e",
        "epsilon_e_posterior_histogram",
        r"$\log_{10}(\epsilon_e)$",
        "Electron Energy-Fraction Posterior Distributions",
    ),
    ParameterSpec(
        "eps_b",
        "epsilon_b_posterior_histogram",
        r"$\log_{10}(\epsilon_B)$",
        "Magnetic Energy-Fraction Posterior Distributions",
    ),
    ParameterSpec(
        "p",
        "electron_index_p_posterior_histogram",
        r"$p$",
        "Electron Power-Law Index Posterior Distributions",
    ),
    ParameterSpec(
        "k",
        "csm_slope_k_posterior_histogram",
        r"$k$",
        "CSM Density-Slope Posterior Distributions",
        note=r"$n(r)\propto r^{-k}$",
    ),
    ParameterSpec(
        "theta_c",
        "core_angle_posterior_histogram",
        r"$\log_{10}(\theta_c/\mathrm{rad})$",
        "Jet Core-Angle Posterior Distributions",
        transform="log10_fit",
    ),
    ParameterSpec(
        "theta_v",
        "viewing_angle_posterior_histogram",
        r"$\log_{10}(\theta_v/\mathrm{rad})$",
        "Viewing-Angle Posterior Distributions",
        transform="log10_fit",
    ),
    ParameterSpec(
        "ebv_source_frame",
        "host_reddening_posterior_histogram",
        r"$E(B-V)_{\mathrm{source}}$ [mag]",
        "Source-Frame Reddening Posterior Distributions",
    ),
    ParameterSpec(
        "nt",
        "sbpl_density_nt_posterior_histogram",
        r"$\log_{10}(n_t/\mathrm{cm}^{-3})$",
        "SBPL Transition-Density Posterior Distributions",
    ),
    ParameterSpec(
        "rt",
        "sbpl_transition_radius_posterior_histogram",
        r"$\log_{10}(r_t/\mathrm{cm})$",
        "SBPL Transition-Radius Posterior Distributions",
    ),
    ParameterSpec(
        "k1",
        "sbpl_inner_slope_k1_posterior_histogram",
        r"$k_1$",
        "SBPL Inner Density-Slope Posterior Distributions",
    ),
    ParameterSpec(
        "k2",
        "sbpl_outer_slope_k2_posterior_histogram",
        r"$k_2$",
        "SBPL Outer Density-Slope Posterior Distributions",
    ),
    ParameterSpec(
        "sn",
        "sbpl_smoothing_sn_posterior_histogram",
        r"$s_n$",
        "SBPL Density-Smoothing Posterior Distributions",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--bins", type=int, default=64)
    parser.add_argument(
        "--parameter",
        action="append",
        choices=[spec.key for spec in PARAMETERS],
        help="Generate only this parameter; repeat to select several.",
    )
    parser.add_argument(
        "--scatter-samples-per-event",
        type=int,
        default=5000,
        help="Maximum posterior draws per event to write/plot in the density-k scatter.",
    )
    parser.add_argument(
        "--skip-density-k-scatter",
        action="store_true",
        help="Do not generate the density-normalization versus k scatter product.",
    )
    parser.add_argument(
        "--only-density-k-scatter",
        action="store_true",
        help="Generate only the density-normalization versus k scatter product.",
    )
    return parser.parse_args()


def campaign_runs(campaign: Path) -> list[Path]:
    return sorted(
        path
        for path in campaign.iterdir()
        if is_campaign_event_dir(path)
        and (path / "chain.npz").is_file()
        and (path / "model.toml").is_file()
    )


def load_values(run: Path, spec: ParameterSpec) -> np.ndarray:
    if spec.source == "derived_ratio":
        numerator_key = {
            "E_j_core_52_per_sr": "E_j_core_52",
            "M_j_core_msun_per_sr": "M_j_core_msun",
        }[spec.key]
        with np.load(run / "jet_energy_posterior.npz") as data:
            numerator = np.asarray(data[numerator_key], dtype=float)
            theta_c = np.asarray(data["theta_c"], dtype=float)
        values = numerator / (2.0 * np.pi * theta_c**2)
    elif spec.source == "derived":
        with np.load(run / "jet_energy_posterior.npz") as data:
            values = np.asarray(data[spec.key], dtype=float)
    else:
        params = Parameters.from_toml(run / "model.toml").fitting
        names = [param.name for param in params]
        aliases = {
            "eps_b": ("eps_b", "eps_B"),
        }
        source_key = next(
            (name for name in aliases.get(spec.key, (spec.key,)) if name in names),
            None,
        )
        if source_key is None:
            raise KeyError(f"{spec.key} is not fitted by {run.name}")
        with np.load(run / "chain.npz") as data:
            chain = np.asarray(data["chain"], dtype=float)
        values = chain[..., names.index(source_key)].reshape(-1)

    values = values[np.isfinite(values)]
    if spec.transform == "log10":
        values = values[values > 0.0]
        values = np.log10(values)
    if values.size == 0:
        raise ValueError(f"No finite posterior samples for {spec.key} in {run.name}")
    return values


def fitted_parameter_names(run: Path) -> list[str]:
    return [param.name for param in Parameters.from_toml(run / "model.toml").fitting]


def resolve_fit_key(names: list[str], key: str) -> str:
    aliases = {
        "eps_b": ("eps_b", "eps_B"),
    }
    source_key = next((name for name in aliases.get(key, (key,)) if name in names), None)
    if source_key is None:
        raise KeyError(f"{key} is not fitted")
    return source_key


def load_chain_pair(run: Path, x_key: str, y_key: str) -> tuple[np.ndarray, np.ndarray]:
    names = fitted_parameter_names(run)
    x_source = resolve_fit_key(names, x_key)
    y_source = resolve_fit_key(names, y_key)
    with np.load(run / "chain.npz") as data:
        chain = np.asarray(data["chain"], dtype=float)
    x = chain[..., names.index(x_source)].reshape(-1)
    y = chain[..., names.index(y_source)].reshape(-1)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size == 0:
        raise ValueError(f"No finite paired posterior samples for {x_key},{y_key} in {run.name}")
    return x, y


def shared_edges(samples: dict[str, np.ndarray], bins: int) -> np.ndarray:
    values = np.concatenate(list(samples.values()))
    lo, hi = np.quantile(values, [0.0005, 0.9995])
    if not np.isfinite(lo) or not np.isfinite(hi):
        raise ValueError("Non-finite histogram range")
    if hi <= lo:
        pad = max(abs(lo) * 0.05, 0.05)
    else:
        pad = 0.04 * (hi - lo)
    return np.linspace(lo - pad, hi + pad, bins + 1)


def plot_parameter(
    campaign: Path,
    runs: list[Path],
    spec: ParameterSpec,
    bins: int,
) -> dict[str, str | int]:
    samples: dict[str, np.ndarray] = {}
    for run in runs:
        try:
            samples[run.name] = load_values(run, spec)
        except KeyError:
            continue
    if not samples:
        raise ValueError(f"No campaign runs fit {spec.key}")
    edges = shared_edges(samples, bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    colors = plt.get_cmap("turbo")(np.linspace(0.03, 0.97, len(samples)))

    fig, ax = plt.subplots(figsize=(11.2, 6.5))
    summary_rows: list[dict[str, float | int | str]] = []
    histogram_rows: list[dict[str, float | str]] = []
    for (event, values), color in zip(samples.items(), colors):
        density, _ = np.histogram(values, bins=edges, density=True)
        ax.stairs(density, edges, color=color, lw=1.7, label=f"GRB {event}")
        median = float(np.median(values))
        ax.axvline(median, color=color, lw=0.9, alpha=0.72)
        q16, q84 = np.quantile(values, [0.16, 0.84])
        summary_rows.append(
            {
                "event": event,
                "parameter": spec.key,
                "plotted_scale": spec.transform,
                "n_samples": int(values.size),
                "q16": float(q16),
                "median": median,
                "q84": float(q84),
            }
        )
        for center, density_value in zip(centers, density):
            histogram_rows.append(
                {
                    "event": event,
                    "parameter": spec.key,
                    "bin_center": float(center),
                    "density": float(density_value),
                }
            )

    ax.set_xlabel(spec.xlabel, fontsize=13)
    ax.set_ylabel("Posterior probability density", fontsize=13)
    ax.set_title(spec.title, fontsize=15, pad=10)
    ax.grid(axis="y", alpha=0.22)
    ax.tick_params(labelsize=11)
    ax.legend(
        ncol=3,
        fontsize=9,
        loc="upper left",
        frameon=True,
        columnspacing=1.2,
        handlelength=2.2,
    )
    if spec.note:
        fig.text(0.995, 0.008, spec.note, ha="right", va="bottom", fontsize=8)
    fig.tight_layout(rect=(0, 0.035 if spec.note else 0, 1, 1))

    stem = campaign / spec.output_stem
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    with (campaign / f"{spec.output_stem}_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)
    with (campaign / f"{spec.output_stem}_data.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=histogram_rows[0].keys())
        writer.writeheader()
        writer.writerows(histogram_rows)

    return {
        "parameter": spec.key,
        "output_stem": spec.output_stem,
        "plotted_scale": spec.transform,
        "n_events": len(samples),
        "samples_per_event": ",".join(
            f"{event}:{values.size}" for event, values in samples.items()
        ),
    }


def sample_indices(event: str, n_values: int, max_samples: int) -> np.ndarray:
    if n_values <= max_samples:
        return np.arange(n_values, dtype=int)
    seed = zlib.crc32(event.encode("utf-8")) ^ 0x20260707
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n_values, size=max_samples, replace=False))


def padded_limits(values: np.ndarray) -> tuple[float, float]:
    lo, hi = np.quantile(values, [0.001, 0.999])
    if not np.isfinite(lo) or not np.isfinite(hi):
        raise ValueError("Non-finite scatter range")
    if hi <= lo:
        pad = max(abs(lo) * 0.05, 0.05)
    else:
        pad = 0.05 * (hi - lo)
    return float(lo - pad), float(hi + pad)


def plot_density_k_scatter(
    campaign: Path,
    runs: list[Path],
    max_samples_per_event: int,
) -> dict[str, str | int]:
    if max_samples_per_event <= 0:
        raise ValueError("--scatter-samples-per-event must be positive")

    paired_samples: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for run in runs:
        try:
            paired_samples[run.name] = load_chain_pair(run, "n017", "k")
        except KeyError:
            continue
    if not paired_samples:
        raise ValueError("No campaign runs fit both n017 and k")

    colors = plt.get_cmap("turbo")(np.linspace(0.03, 0.97, len(paired_samples)))
    fig, ax = plt.subplots(figsize=(11.2, 7.0))
    summary_rows: list[dict[str, float | int | str]] = []
    scatter_rows: list[dict[str, float | int | str]] = []
    plotted_x: list[np.ndarray] = []
    plotted_y: list[np.ndarray] = []

    for (event, (density_values, k_values)), color in zip(paired_samples.items(), colors):
        indices = sample_indices(event, density_values.size, max_samples_per_event)
        density_subset = density_values[indices]
        k_subset = k_values[indices]
        plotted_x.append(density_subset)
        plotted_y.append(k_subset)

        ax.scatter(
            density_subset,
            k_subset,
            s=5,
            alpha=0.16,
            color=color,
            edgecolors="none",
            label=f"GRB {event}",
        )
        density_median = float(np.median(density_values))
        k_median = float(np.median(k_values))
        density_q16, density_q84 = np.quantile(density_values, [0.16, 0.84])
        k_q16, k_q84 = np.quantile(k_values, [0.16, 0.84])
        ax.errorbar(
            [density_median],
            [k_median],
            xerr=np.asarray([[density_median - density_q16], [density_q84 - density_median]]),
            yerr=np.asarray([[k_median - k_q16], [k_q84 - k_median]]),
            fmt="o",
            markersize=6.2,
            markerfacecolor=color,
            markeredgecolor="black",
            markeredgewidth=0.65,
            ecolor=color,
            elinewidth=1.25,
            capsize=3.0,
            capthick=1.05,
            alpha=0.92,
            zorder=5,
        )
        if density_values.size > 1 and np.std(density_values) > 0.0 and np.std(k_values) > 0.0:
            pearson_r = float(np.corrcoef(density_values, k_values)[0, 1])
        else:
            pearson_r = float("nan")
        summary_rows.append(
            {
                "event": event,
                "n_full_samples": int(density_values.size),
                "n_plotted_samples": int(indices.size),
                "density_n017_q16": float(density_q16),
                "density_n017_median": density_median,
                "density_n017_q84": float(density_q84),
                "k_q16": float(k_q16),
                "k_median": k_median,
                "k_q84": float(k_q84),
                "pearson_r": pearson_r,
            }
        )
        for index, density_value, k_value in zip(indices, density_subset, k_subset):
            scatter_rows.append(
                {
                    "event": event,
                    "posterior_index": int(index),
                    "density_n017_log10": float(density_value),
                    "k": float(k_value),
                }
            )

    ax.set_xlabel(r"$\log_{10}(n_{0,17})$", fontsize=13)
    ax.set_ylabel(r"$k$", fontsize=13)
    ax.set_title("Density Normalization vs. CSM Slope Posterior Samples", fontsize=15, pad=10)
    ax.grid(alpha=0.22)
    ax.tick_params(labelsize=11)
    ax.set_xlim(*padded_limits(np.concatenate(plotted_x)))
    ax.set_ylim(*padded_limits(np.concatenate(plotted_y)))
    ax.legend(
        ncol=3,
        fontsize=9,
        loc="upper left",
        frameon=True,
        columnspacing=1.2,
        handlelength=1.0,
    )
    fig.text(
        0.995,
        0.008,
        r"$n(r)=n_{0,17}(r/10^{17}\,\mathrm{cm})^{-k}$; circles mark medians, "
        r"bars span posterior 16th-84th percentiles",
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))

    stem = campaign / DENSITY_K_SCATTER_STEM
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    with (campaign / f"{DENSITY_K_SCATTER_STEM}_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)
    with (campaign / f"{DENSITY_K_SCATTER_STEM}_data.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=scatter_rows[0].keys())
        writer.writeheader()
        writer.writerows(scatter_rows)

    return {
        "parameter": "n017,k",
        "output_stem": DENSITY_K_SCATTER_STEM,
        "plotted_scale": "identity,identity",
        "n_events": len(paired_samples),
        "samples_per_event": ",".join(
            f"{event}:{min(values[0].size, max_samples_per_event)}/{values[0].size}"
            for event, values in paired_samples.items()
        ),
    }


def write_manifest(campaign: Path, rows: list[dict[str, str | int]], *, preserve_existing: bool) -> Path:
    manifest = campaign / MANIFEST_NAME
    final_rows: list[dict[str, str | int]] = []
    new_stems = {str(row["output_stem"]) for row in rows}
    if preserve_existing and manifest.is_file():
        with manifest.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("output_stem") not in new_stems:
                    final_rows.append(row)
    final_rows.extend(rows)
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(final_rows)
    return manifest


def main() -> int:
    args = parse_args()
    campaign = args.campaign.expanduser().resolve()
    runs = campaign_runs(campaign)
    if not runs:
        raise SystemExit(f"No completed runs found under {campaign}")

    selected = set(args.parameter or ())
    manifest_rows = []
    specs = []
    if not args.only_density_k_scatter:
        specs = [spec for spec in PARAMETERS if not selected or spec.key in selected]
        for spec in specs:
            try:
                manifest_rows.append(plot_parameter(campaign, runs, spec, args.bins))
            except ValueError as exc:
                if "No campaign runs fit" not in str(exc):
                    raise
                print(f"Skipping {spec.key}: {exc}")
    should_plot_density_k = (
        not args.skip_density_k_scatter
        and (
            args.only_density_k_scatter
            or not selected
            or {"n017", "k"}.issubset(selected)
        )
    )
    if should_plot_density_k:
        try:
            manifest_rows.append(
                plot_density_k_scatter(campaign, runs, args.scatter_samples_per_event)
            )
        except ValueError as exc:
            if "No campaign runs fit" not in str(exc):
                raise
            print(f"Skipping n017,k scatter: {exc}")
    if not manifest_rows:
        raise SystemExit("No requested campaign products could be generated")
    manifest = write_manifest(
        campaign,
        manifest_rows,
        preserve_existing=args.only_density_k_scatter,
    )

    print(f"Wrote {len(manifest_rows)} campaign product families for {len(runs)} events")
    print(f"Wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
