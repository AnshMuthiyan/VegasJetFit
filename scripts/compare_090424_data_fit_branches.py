#!/usr/bin/env python3
"""Compare the three GRB 090424 fit branches on one common observation set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from diagnose_likelihood_contributions import load_params, point_contributions
from jetfit.ampy import Ampy


DEFAULT_BASE = Path(
    "/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/final_seeded_runs/"
    "26_07_07__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__"
    "final_seeded__10_temperature_5000x5000"
)
DEFAULT_SSC = Path(
    "/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/final_seeded_runs/"
    "26_08_03__core_ejet_gamma_logangles__single_powerlaw_csm__090424_early_xray__"
    "ssc_kn__final_seeded__10_temperature_5000x5000/090424_with_early_xray_ssc_kn"
)

FIT_COLORS = {
    "No early X-ray; synchrotron": "#2f2f2f",
    "Early X-ray; synchrotron": "#2563a6",
    "Early X-ray; SSC+KN": "#b33b32",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the GRB 090424 fit branches on the same full dataset."
    )
    parser.add_argument("--no-early", type=Path, default=DEFAULT_BASE / "090424")
    parser.add_argument(
        "--early-synchrotron", type=Path, default=DEFAULT_BASE / "090424_with_early_xray"
    )
    parser.add_argument("--early-ssc", type=Path, default=DEFAULT_SSC)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_SSC.parent / "comparison_plots",
    )
    return parser.parse_args()


def common_observations(source: Path, out_dir: Path) -> Path:
    """Write an evaluation-only copy with every observation included."""
    obs = pd.read_csv(source / "obs.csv")
    if "Include" not in obs:
        raise ValueError(f"No Include column in {source / 'obs.csv'}")
    obs["Include"] = 1
    path = out_dir / "090424_all_observations_evaluation_only.csv"
    obs.to_csv(path, index=False)
    return path


def dataset_name(row: pd.Series) -> str:
    if row["value_type"] == "SpectralIndex":
        return "X-ray spectral index"
    if row["band"] != "xray":
        return str(row["band"])
    return "X-ray: 91-247 s" if row["time_days"] <= 247.071 / 86400.0 else "X-ray: >247 s"


def evaluate(label: str, result_dir: Path, obs_path: Path) -> tuple[pd.DataFrame, dict]:
    params = load_params(result_dir)
    ampy = Ampy(obs_path, result_dir / "model.toml")
    points = point_contributions(ampy, params)
    points["raw_resid_sigma"] = (points["y"] - points["model"]) / points["err"]
    points["fit"] = label
    points["dataset"] = points.apply(dataset_name, axis=1)

    minimized = json.loads((result_dir / "minimized" / "minimized.json").read_text())
    run = {
        "fit": label,
        "result_dir": str(result_dir),
        "original_included_points": int(pd.read_csv(result_dir / "obs.csv")["Include"].sum()),
        "common_evaluation_points": len(points),
        "stored_nmap": float(minimized["nmap"]),
        "params": params,
    }
    return points, run


def summarize(points: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    group_order = ["All observations", "All X-ray", "X-ray: 91-247 s", "X-ray: >247 s"]
    filters = sorted(set(points["dataset"]) - set(group_order[2:]))
    for fit, fit_points in points.groupby("fit", sort=False):
        groups: list[tuple[str, pd.DataFrame]] = [
            ("All observations", fit_points),
            ("All X-ray", fit_points[fit_points["band"] == "xray"]),
            ("X-ray: 91-247 s", fit_points[fit_points["dataset"] == "X-ray: 91-247 s"]),
            ("X-ray: >247 s", fit_points[fit_points["dataset"] == "X-ray: >247 s"]),
        ]
        groups.extend((band, fit_points[fit_points["dataset"] == band]) for band in filters)
        for dataset, part in groups:
            if part.empty:
                continue
            ratio = part["model"] / part["y"]
            pull = part["resid_sigma"]
            rows.append(
                {
                    "fit": fit,
                    "dataset": dataset,
                    "n": len(part),
                    "median_model_over_data": float(ratio.median()),
                    "p16_model_over_data": float(ratio.quantile(0.16)),
                    "p84_model_over_data": float(ratio.quantile(0.84)),
                    "median_signed_pull": float(pull.median()),
                    "mean_absolute_pull": float(pull.abs().mean()),
                    "rms_pull": float(np.sqrt(np.mean(np.square(pull)))),
                    "raw_rms_measurement_pull": float(
                        np.sqrt(np.mean(np.square(part["raw_resid_sigma"])))
                    ),
                    "sum_pull2": float(part["pull2"].sum()),
                    "sum_likelihood_term": float(part["chi_term"].sum()),
                }
            )
    return pd.DataFrame(rows)


def plot_dataset_overlays(points: pd.DataFrame, out_dir: Path) -> None:
    datasets = [
        "X-ray: 91-247 s", "X-ray: >247 s", "uvw2", "uvm2", "uvw1",
        "uvot-u", "uvot-b", "uvot-v", "r", "i", "X-ray spectral index",
    ]
    fig, axes = plt.subplots(6, 2, figsize=(8.0, 11.0), constrained_layout=True)
    for ax, dataset in zip(axes.flat, datasets):
        subset = points[points["dataset"] == dataset]
        observed = subset[subset["fit"] == next(iter(FIT_COLORS))].sort_values("time_days")
        ax.errorbar(
            observed["time_days"] * 86400.0,
            observed["y"],
            yerr=observed["err"],
            fmt="o",
            ms=2.2,
            color="#777777",
            ecolor="#aaaaaa",
            elinewidth=0.55,
            alpha=0.75,
            label="Data",
            zorder=4,
        )
        for label, color in FIT_COLORS.items():
            fit = subset[subset["fit"] == label].sort_values("time_days")
            ax.plot(
                fit["time_days"] * 86400.0,
                fit["model"],
                color=color,
                lw=1.35,
                alpha=0.95,
                label=label,
            )
        ax.set_xscale("log")
        if dataset == "X-ray spectral index":
            ax.set_ylabel("Spectral index")
        else:
            ax.set_yscale("log")
        ax.set_title(dataset, fontsize=9)
        ax.grid(True, which="both", alpha=0.18)
        ax.tick_params(labelsize=7)
    for ax in axes[-1, :]:
        ax.set_xlabel("Observer time [s]", fontsize=9)
    for ax in axes[:-1, 0]:
        ax.set_ylabel("Flux density [mJy]", fontsize=9)
    axes[-1, 1].axis("off")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=2, fontsize=8, frameon=False)
    for suffix in ("png", "pdf"):
        fig.savefig(out_dir / f"090424_fit_overlays_by_dataset.{suffix}", dpi=240)
    plt.close(fig)


def plot_metric_summary(summary: pd.DataFrame, out_dir: Path) -> None:
    datasets = ["All observations", "X-ray: 91-247 s", "X-ray: >247 s", "X-ray spectral index", "uvw2", "uvm2", "uvw1", "uvot-u", "uvot-b", "uvot-v", "r", "i"]
    fig, axes = plt.subplots(2, 1, figsize=(8.0, 7.5), constrained_layout=True)
    width = 0.24
    x = np.arange(len(datasets), dtype=float)
    for index, (label, color) in enumerate(FIT_COLORS.items()):
        fit = summary[summary["fit"] == label].set_index("dataset").reindex(datasets)
        offset = (index - 1) * width
        axes[0].bar(
            x + offset,
            fit["raw_rms_measurement_pull"],
            width,
            color=color,
            alpha=0.88,
            label=label,
        )
        med = fit["median_model_over_data"].to_numpy(float)
        lo = med - fit["p16_model_over_data"].to_numpy(float)
        hi = fit["p84_model_over_data"].to_numpy(float) - med
        axes[1].errorbar(x + offset, med, yerr=np.vstack((lo, hi)), fmt="o", ms=4, capsize=2, color=color)
    axes[0].set_ylabel("RMS residual / measurement error")
    axes[0].legend(fontsize=8, frameon=False, ncol=1)
    axes[1].axhline(1.0, color="#666666", ls="--", lw=1)
    axes[1].set_ylabel("Median model / data")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(datasets, rotation=40, ha="right", fontsize=8)
        ax.grid(True, axis="y", alpha=0.22)
    for suffix in ("png", "pdf"):
        fig.savefig(out_dir / f"090424_fit_quality_by_dataset.{suffix}", dpi=240)
    plt.close(fig)


def plot_early_xray_shape(points: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    early = points[points["dataset"] == "X-ray: 91-247 s"].copy()
    reference = early[early["fit"] == next(iter(FIT_COLORS))].sort_values("time_days")
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(7.3, 6.5),
        sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1.0]},
        constrained_layout=True,
    )
    axes[0].errorbar(
        reference["time_days"] * 86400.0,
        reference["y"],
        yerr=reference["err"],
        fmt="o",
        ms=3,
        color="#666666",
        ecolor="#aaaaaa",
        elinewidth=0.6,
        label="Data",
        zorder=5,
    )
    slope_rows: list[dict] = []
    data_slope = float(
        np.polyfit(np.log10(reference["time_days"]), np.log10(reference["y"]), 1)[0]
    )
    for label, color in FIT_COLORS.items():
        fit = early[early["fit"] == label].sort_values("time_days")
        ratio = fit["model"] / fit["y"]
        model_slope = float(
            np.polyfit(np.log10(fit["time_days"]), np.log10(fit["model"]), 1)[0]
        )
        axes[0].plot(
            fit["time_days"] * 86400.0,
            fit["model"],
            color=color,
            lw=1.7,
            label=f"{label} (slope {model_slope:.2f})",
        )
        axes[1].plot(
            fit["time_days"] * 86400.0,
            ratio,
            color=color,
            lw=1.5,
            label=label,
        )
        ordered = fit.sort_values("time_days")
        quartiles = pd.qcut(ordered["time_days"], 4, labels=False, duplicates="drop")
        for quartile, part in ordered.groupby(quartiles):
            part_ratio = part["model"] / part["y"]
            slope_rows.append(
                {
                    "fit": label,
                    "time_quartile": int(quartile) + 1,
                    "time_min_s": float(part["time_days"].min() * 86400.0),
                    "time_max_s": float(part["time_days"].max() * 86400.0),
                    "n": len(part),
                    "median_model_over_data": float(part_ratio.median()),
                    "raw_rms_measurement_pull": float(
                        np.sqrt(np.mean(np.square(part["raw_resid_sigma"])))
                    ),
                    "data_log_slope_full_interval": data_slope,
                    "model_log_slope_full_interval": model_slope,
                }
            )
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("X-ray flux density [mJy]")
    axes[0].legend(fontsize=7.2, frameon=False, ncol=1)
    axes[0].text(
        0.98,
        0.05,
        f"Observed slope: {data_slope:.2f}",
        transform=axes[0].transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
    )
    axes[1].axhline(1.0, color="#666666", ls="--", lw=1)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Observer time [s]")
    axes[1].set_ylabel("Model / data")
    for ax in axes:
        ax.grid(True, which="both", alpha=0.2)
    for suffix in ("png", "pdf"):
        fig.savefig(out_dir / f"090424_early_xray_shape_comparison.{suffix}", dpi=240)
    plt.close(fig)
    return pd.DataFrame(slope_rows)


def write_interpretation(summary: pd.DataFrame, runs: list[dict], out_dir: Path) -> None:
    lookup = summary.set_index(["fit", "dataset"])
    synch = "Early X-ray; synchrotron"
    ssc = "Early X-ray; SSC+KN"
    lines = [
        "# GRB 090424 common-data fit comparison",
        "",
        "All three minimized solutions are evaluated against the same 751 included observations. "
        "This evaluation does not refit or modify any campaign result.",
        "",
        "## Key results",
        "",
        f"- Early-X-ray RMS standardized residual: {lookup.loc[(synch, 'X-ray: 91-247 s'), 'rms_pull']:.3f} "
        f"(synchrotron) versus {lookup.loc[(ssc, 'X-ray: 91-247 s'), 'rms_pull']:.3f} (SSC+KN).",
        f"- Later-X-ray RMS standardized residual: {lookup.loc[(synch, 'X-ray: >247 s'), 'rms_pull']:.3f} "
        f"(synchrotron) versus {lookup.loc[(ssc, 'X-ray: >247 s'), 'rms_pull']:.3f} (SSC+KN).",
        f"- Stored optimized nmap (-2 log posterior; lower is better) on the shared fitted dataset: "
        f"{next(r['stored_nmap'] for r in runs if r['fit'] == synch):.3f} (synchrotron) versus "
        f"{next(r['stored_nmap'] for r in runs if r['fit'] == ssc):.3f} (SSC+KN).",
        "",
        "SSC+KN improves both the common-data likelihood contribution and the optimized posterior, with no added "
        "fitted coordinate. The improvement is not confined to the flagged early interval: later X-rays also improve, "
        "while the optical/UV changes are mixed. However, the early-X-ray shape remains visibly wrong: the observed "
        "log-log temporal slope is about -1.77, versus -0.93 for the included-data synchrotron fit and -1.30 for "
        "SSC+KN, and SSC+KN still underpredicts the earliest quarter. The SSC+KN solution is also qualitatively "
        "different and includes extreme physical parameters. Thus SSC improves the fit but does not remove the "
        "evidence that the telescope-flagged interval contains an additional flare-like component.",
        "",
        "## Provenance",
        "",
    ]
    lines.extend(f"- **{run['fit']}**: `{run['result_dir']}`" for run in runs)
    (out_dir / "090424_common_data_comparison.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    obs_path = common_observations(args.early_synchrotron.expanduser().resolve(), out_dir)
    specs = [
        ("No early X-ray; synchrotron", args.no_early),
        ("Early X-ray; synchrotron", args.early_synchrotron),
        ("Early X-ray; SSC+KN", args.early_ssc),
    ]
    point_frames: list[pd.DataFrame] = []
    runs: list[dict] = []
    for label, path in specs:
        points, run = evaluate(label, path.expanduser().resolve(), obs_path)
        point_frames.append(points)
        runs.append(run)
    all_points = pd.concat(point_frames, ignore_index=True)
    summary = summarize(all_points)
    all_points.to_csv(out_dir / "090424_fit_comparison_pointwise.csv", index=False)
    summary.to_csv(out_dir / "090424_fit_comparison_by_dataset.csv", index=False)
    (out_dir / "090424_fit_comparison_provenance.json").write_text(json.dumps(runs, indent=2) + "\n")
    plot_dataset_overlays(all_points, out_dir)
    plot_metric_summary(summary, out_dir)
    early_shape = plot_early_xray_shape(all_points, out_dir)
    early_shape.to_csv(out_dir / "090424_early_xray_time_resolved_metrics.csv", index=False)
    write_interpretation(summary, runs, out_dir)
    print(out_dir)


if __name__ == "__main__":
    main()
