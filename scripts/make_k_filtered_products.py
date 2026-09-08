#!/usr/bin/env python3
"""Create posterior-slice products for a finished run filtered by CSM slope k."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.mcmc.parameters import Parameters
from scripts.generate_postfit_products import (
    derive_jet_energy_posterior,
    summarize_derived_samples,
    write_jet_energy_summary,
)
from scripts.plot import diagnose


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path, help="Finished run directory containing chain.npz.")
    parser.add_argument("--out", required=True, type=Path, help="Output subfolder for filtered products.")
    parser.add_argument("--event", default=None, help="Event label for plot annotations.")
    parser.add_argument("--k-max", type=float, default=-4.0, help="Keep samples with k < this value.")
    parser.add_argument("--max-plot-samples", type=int, default=50000, help="Maximum samples for corner plots.")
    parser.add_argument("--seed", type=int, default=160131, help="Random seed used only for plot thinning.")
    return parser.parse_args()


def infer_model_name(model_toml: Path) -> str:
    for line in model_toml.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("name") and "=" in stripped:
            return stripped.split("=", 1)[1].strip().strip("'\"")
    raise ValueError(f"Could not infer model name from {model_toml}")


def finite_summary(values: np.ndarray) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {
            "n_samples": 0,
            "mean": float("nan"),
            "sd": float("nan"),
            "q02_5": float("nan"),
            "q16": float("nan"),
            "median": float("nan"),
            "q84": float("nan"),
            "q97_5": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }
    qs = np.quantile(arr, [0.025, 0.16, 0.5, 0.84, 0.975])
    return {
        "n_samples": int(arr.size),
        "mean": float(np.mean(arr)),
        "sd": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
        "q02_5": float(qs[0]),
        "q16": float(qs[1]),
        "median": float(qs[2]),
        "q84": float(qs[3]),
        "q97_5": float(qs[4]),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def write_parameter_summary(out: Path, names: list[str], samples: np.ndarray) -> None:
    fields = ["parameter", "n_samples", "mean", "sd", "q02_5", "q16", "median", "q84", "q97_5", "min", "max"]
    with (out / "posterior_summary_k_lt_minus4.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, name in enumerate(names):
            row = {"parameter": name, **finite_summary(samples[:, index])}
            writer.writerow(row)


def write_histogram_data(out: Path, names: list[str], samples: np.ndarray, bins: int = 80) -> None:
    with (out / "posterior_histograms_data.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["parameter", "bin_left", "bin_right", "count"])
        writer.writeheader()
        for index, name in enumerate(names):
            arr = samples[:, index]
            arr = arr[np.isfinite(arr)]
            if arr.size == 0:
                continue
            counts, edges = np.histogram(arr, bins=bins)
            for count, left, right in zip(counts, edges[:-1], edges[1:]):
                writer.writerow(
                    {
                        "parameter": name,
                        "bin_left": float(left),
                        "bin_right": float(right),
                        "count": int(count),
                    }
                )


def plot_histograms(out: Path, names: list[str], samples: np.ndarray, event: str, k_max: float) -> None:
    ncols = 4
    nrows = int(np.ceil(len(names) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, max(8, 2.2 * nrows)), constrained_layout=True)
    axes = np.asarray(axes).reshape(-1)
    for ax, name, values in zip(axes, names, samples.T):
        arr = values[np.isfinite(values)]
        ax.hist(arr, bins=60, color="#2f6f8f", alpha=0.86)
        ax.axvline(np.median(arr), color="#c7432f", lw=1.4)
        ax.set_title(name, fontsize=9)
        ax.tick_params(labelsize=7)
    for ax in axes[len(names):]:
        ax.axis("off")
    fig.suptitle(f"GRB {event}: posterior samples with k < {k_max:g}", fontsize=14)
    fig.savefig(out / "posterior_histograms.pdf", dpi=300)
    fig.savefig(out / "posterior_histograms.png", dpi=220)
    plt.close(fig)


def thin_for_plot(samples: np.ndarray, max_samples: int, seed: int) -> np.ndarray:
    if samples.shape[0] <= max_samples:
        return samples
    rng = np.random.default_rng(seed)
    idx = rng.choice(samples.shape[0], size=max_samples, replace=False)
    return samples[np.sort(idx)]


def write_readme(out: Path, manifest: dict[str, object]) -> None:
    lines = [
        "# 160131A k < -4 posterior-slice products",
        "",
        "These products were made from the finished 26_06_29 k[-10,3] 10-temperature run, using only posterior samples whose fitted single-power-law CSM slope satisfies `k < -4`.",
        "",
        "The filter is applied to the linear fitted `k` coordinate in `chain.npz`; no refit or re-minimization was performed.",
        "",
        "Key files:",
        "",
        "- `selected_parameter_samples.npz`: flattened selected posterior samples and parameter names.",
        "- `posterior_summary_k_lt_minus4.csv`: quantiles and moments for fitted parameters in the selected subset.",
        "- `posterior_histograms.pdf/.png`: one-dimensional histograms for all fitted parameters in the selected subset.",
        "- `corner_core.pdf/.png`, `corner_csm.pdf/.png`: reduced posterior corner plots for the selected subset.",
        "- `jet_energy_posterior.npz`, `jet_energy_summary.csv`, `corner_energy.pdf/.png`, `corner_jet_mass.pdf/.png`: derived core-energy/core-mass products recomputed from the selected subset.",
        "- `selection_manifest.json`: machine-readable provenance and sample counts.",
        "",
        "Selection summary:",
        "",
        f"- total finite posterior samples: {manifest['n_total']}",
        f"- selected samples: {manifest['n_selected']}",
        f"- selected fraction: {manifest['selected_fraction']:.6f}",
        f"- k quantiles in selected subset: {manifest['selected_k_quantiles']}",
        "",
    ]
    out.joinpath("README.md").write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    results = args.results.expanduser().resolve()
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    params = Parameters.from_toml(results / "model.toml")
    fitting = params.fitting
    names = [param.name for param in fitting]
    if "k" not in names:
        raise KeyError(f"Run has no fitted k parameter: {results}")
    k_index = names.index("k")

    with np.load(results / "chain.npz") as data:
        chain = np.asarray(data["chain"], dtype=float)
        lnprob = np.asarray(data["lnprob"], dtype=float) if "lnprob" in data.files else None
        betas = np.asarray(data["betas"], dtype=float) if "betas" in data.files else None

    flat_chain = chain.reshape(-1, chain.shape[-1])
    flat_lnprob = None if lnprob is None else lnprob.reshape(-1)
    k_values = flat_chain[:, k_index]
    finite_mask = np.isfinite(k_values)
    selected_mask = finite_mask & (k_values < args.k_max)
    selected = flat_chain[selected_mask]
    if selected.shape[0] < 2:
        raise ValueError(f"Only {selected.shape[0]} samples satisfy k < {args.k_max}")
    selected_lnprob = None if flat_lnprob is None else flat_lnprob[selected_mask]

    event = args.event or results.name.split("_", 1)[0]
    model_name = infer_model_name(results / "model.toml")
    selected_k = selected[:, k_index]
    manifest = {
        "event": event,
        "source_results": str(results),
        "source_chain": str(results / "chain.npz"),
        "filter": f"k < {args.k_max:g}",
        "k_coordinate": "linear fitted parameter",
        "k_index": k_index,
        "n_total": int(finite_mask.sum()),
        "n_selected": int(selected.shape[0]),
        "selected_fraction": float(selected.shape[0] / max(int(finite_mask.sum()), 1)),
        "selected_k_quantiles": {
            "min": float(np.min(selected_k)),
            "q16": float(np.quantile(selected_k, 0.16)),
            "median": float(np.median(selected_k)),
            "q84": float(np.quantile(selected_k, 0.84)),
            "max": float(np.max(selected_k)),
        },
        "model_name": model_name,
        "max_plot_samples": int(args.max_plot_samples),
        "plot_seed": int(args.seed),
    }
    (out / "selection_manifest.json").write_text(json.dumps(manifest, indent=2))

    np.savez_compressed(
        out / "selected_parameter_samples.npz",
        samples=selected.astype(np.float32),
        lnprob=np.asarray([] if selected_lnprob is None else selected_lnprob, dtype=np.float32),
        betas=np.asarray([] if betas is None else betas, dtype=np.float32),
        parameter_names=np.asarray(names),
        k_max=np.asarray(args.k_max, dtype=float),
    )
    write_parameter_summary(out, names, selected)
    write_histogram_data(out, names, selected)
    plot_histograms(out, names, selected, event, args.k_max)

    for name in ("model.toml", "obs.csv", "best_fit.json", "mcmc_settings.toml"):
        src = results / name
        if src.exists():
            shutil.copy2(src, out / name)
    minimized = results / "minimized" / "minimized.json"
    if minimized.exists():
        (out / "minimized").mkdir(exist_ok=True)
        shutil.copy2(minimized, out / "minimized" / "minimized.json")

    derived, jet_type = derive_jet_energy_posterior(selected, params, model_name)
    rows = summarize_derived_samples(derived, jet_type)
    np.savez_compressed(
        out / "jet_energy_posterior.npz",
        jet_profile=np.asarray(jet_type),
        **{key: np.asarray(value, dtype=np.float32) for key, value in derived.items()},
    )
    write_jet_energy_summary(out, rows)

    plot_samples = thin_for_plot(selected, args.max_plot_samples, args.seed)
    plot_derived = {}
    plot_indices = None
    if selected.shape[0] > plot_samples.shape[0]:
        # Preserve row correspondence between thinned chain and derived arrays.
        rng = np.random.default_rng(args.seed)
        plot_indices = np.sort(rng.choice(selected.shape[0], size=plot_samples.shape[0], replace=False))
        plot_samples = selected[plot_indices]
    if plot_indices is None:
        plot_derived = {key: value for key, value in derived.items()}
    else:
        plot_derived = {key: np.asarray(value)[plot_indices] for key, value in derived.items()}

    os.environ["JETFIT_PLOT_RUN_LABEL"] = f"GRB {event} | k < {args.k_max:g} posterior slice"
    diagnose.plot_reduced_corners(plot_samples, fitting, derived=plot_derived, out_dir=out)
    diagnose.plot_energy_corner(plot_derived, out_dir=out)
    diagnose.plot_jet_mass_corner(plot_derived, out_dir=out)

    write_readme(out, manifest)
    print(
        "k_filtered_products_ok "
        f"out={out} selected={manifest['n_selected']} total={manifest['n_total']} "
        f"fraction={manifest['selected_fraction']:.6f}"
    )


if __name__ == "__main__":
    main()
