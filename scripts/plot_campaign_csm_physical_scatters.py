#!/usr/bin/env python3
"""Plot physical CSM-profile comparisons for a completed campaign."""

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
    parser.add_argument("--campaign", required=True, type=Path)
    return parser.parse_args()


def event_dirs(campaign: Path) -> list[Path]:
    return sorted(
        path
        for path in campaign.iterdir()
        if path.is_dir()
        and not path.name.startswith((".", "_"))
        and path.name != "trash"
        and (path / "chain.npz").is_file()
        and (path / "model.toml").is_file()
        and (path / "density_shell_mass_walkers.csv").is_file()
    )


def terminal_cold_chain(run: Path, parameters: Parameters) -> np.ndarray:
    with np.load(run / "chain.npz", allow_pickle=False) as data:
        chain = np.asarray(data["chain"], dtype=float)
    if chain.ndim == 4:
        terminal = chain[-1, 0]
    elif chain.ndim == 3:
        terminal = chain[-1]
    else:
        raise ValueError(f"Unexpected chain shape for {run.name}: {chain.shape}")
    if terminal.ndim != 2 or terminal.shape[1] != len(parameters.fitting):
        raise ValueError(f"Unexpected terminal chain shape for {run.name}: {terminal.shape}")
    return terminal


def quantiles(values: np.ndarray) -> tuple[float, float, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        raise ValueError("No finite values for posterior summary.")
    return tuple(float(value) for value in np.quantile(finite, [0.16, 0.50, 0.84]))


def errorbar(ax, x: np.ndarray, y: np.ndarray, *, color: np.ndarray, label: str) -> None:
    x16, x50, x84 = quantiles(x)
    y16, y50, y84 = quantiles(y)
    ax.errorbar(
        x50,
        y50,
        xerr=np.array([[x50 - x16], [x84 - x50]]),
        yerr=np.array([[y50 - y16], [y84 - y50]]),
        fmt="o",
        ms=6.5,
        color=color,
        ecolor=color,
        elinewidth=1.1,
        capsize=2.7,
        markeredgecolor="black",
        markeredgewidth=0.55,
        label=f"GRB {label}",
        zorder=3,
    )


def log_limits(values: list[np.ndarray], *, pad: float = 0.20) -> tuple[float, float]:
    merged = np.concatenate([np.asarray(value, dtype=float) for value in values])
    merged = merged[np.isfinite(merged) & (merged > 0.0)]
    lo, hi = np.log10(np.quantile(merged, [0.005, 0.995]))
    if hi <= lo:
        lo -= 0.5
        hi += 0.5
    return 10.0 ** (lo - pad), 10.0 ** (hi + pad)


def linear_limits(values: list[np.ndarray], *, pad: float = 0.08) -> tuple[float, float]:
    merged = np.concatenate([np.asarray(value, dtype=float) for value in values])
    merged = merged[np.isfinite(merged)]
    lo, hi = np.quantile(merged, [0.005, 0.995])
    span = max(float(hi - lo), 0.2)
    return float(lo - pad * span), float(hi + pad * span)


def set_log_square_aspect(ax) -> None:
    # Equal physical length per decade makes equal-unit comparisons honest even
    # when the two axes need different numerical limits.
    ax.set_aspect("equal", adjustable="box")
    ax.grid(which="major", alpha=0.24)
    ax.grid(which="minor", alpha=0.08)


def write_summary(path: Path, events: dict[str, dict[str, np.ndarray]]) -> None:
    fields = (
        "event",
        "n_samples",
        "n17_q16_cm3", "n17_median_cm3", "n17_q84_cm3",
        "profile_mean_nh_q16_cm3", "profile_mean_nh_median_cm3", "profile_mean_nh_q84_cm3",
        "theta_c_q16_rad", "theta_c_median_rad", "theta_c_q84_rad",
        "profile_radius_q16_cm", "profile_radius_median_cm", "profile_radius_q84_cm",
        "profile_inner_radius_median_cm", "profile_outer_radius_median_cm",
        "csm_shell_mass_q16_msun", "csm_shell_mass_median_msun", "csm_shell_mass_q84_msun",
        "jet_mass_q16_msun", "jet_mass_median_msun", "jet_mass_q84_msun",
        "k_q16", "k_median", "k_q84",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for event, values in events.items():
            row: dict[str, float | int | str] = {"event": event, "n_samples": int(values["n17"].size)}
            for key, prefix in (
                ("n17", "n17"),
                ("mean_nh", "profile_mean_nh"),
                ("theta_c", "theta_c"),
                ("profile_radius", "profile_radius"),
                ("csm_mass", "csm_shell_mass"),
                ("jet_mass", "jet_mass"),
                ("k", "k"),
            ):
                q16, q50, q84 = quantiles(values[key])
                suffix = "_cm3" if key in {"n17", "mean_nh"} else "_rad" if key == "theta_c" else "_cm" if key == "profile_radius" else "_msun" if "mass" in key else ""
                row[f"{prefix}_q16{suffix}"] = q16
                row[f"{prefix}_median{suffix}"] = q50
                row[f"{prefix}_q84{suffix}"] = q84
            row["profile_inner_radius_median_cm"] = quantiles(values["r_inner"])[1]
            row["profile_outer_radius_median_cm"] = quantiles(values["r_outer"])[1]
            writer.writerow(row)


def load_event(run: Path) -> dict[str, np.ndarray]:
    parameters = Parameters.from_toml(run / "model.toml")
    names = [parameter.name for parameter in parameters.fitting]
    if not {"n017", "k", "theta_c"}.issubset(names):
        raise ValueError(f"{run.name} does not fit n017, k, and theta_c.")
    terminal = terminal_cold_chain(run, parameters)
    derived, _ = derive_jet_energy_posterior(terminal, parameters, parameters.model)
    shell_rows = list(csv.DictReader((run / "density_shell_mass_walkers.csv").open(encoding="utf-8")))
    indices = np.asarray([int(row["walker_index"]) for row in shell_rows], dtype=int)
    valid = (indices >= 0) & (indices < terminal.shape[0])
    indices = indices[valid]
    if indices.size < 2:
        raise ValueError(f"{run.name} has too few matched terminal shell walkers.")
    n17 = 10.0 ** terminal[indices, names.index("n017")]
    k = terminal[indices, names.index("k")]
    theta_c = 10.0 ** terminal[indices, names.index("theta_c")]
    mean_nh = np.asarray([float(row["mean_number_density_cm3"]) for row in shell_rows], dtype=float)[valid]
    csm_mass = np.asarray([float(row["shell_mass_msun"]) for row in shell_rows], dtype=float)[valid]
    r_inner = np.asarray([float(row["r_inner_cm"]) for row in shell_rows], dtype=float)[valid]
    r_outer = np.asarray([float(row["r_outer_cm"]) for row in shell_rows], dtype=float)[valid]
    profile_radius = np.sqrt(r_inner * r_outer)
    jet_mass = np.asarray(derived["M_j_msun"], dtype=float)[indices]
    finite = (
        np.isfinite(n17) & (n17 > 0.0)
        & np.isfinite(mean_nh) & (mean_nh > 0.0)
        & np.isfinite(csm_mass) & (csm_mass > 0.0)
        & np.isfinite(jet_mass) & (jet_mass > 0.0)
        & np.isfinite(theta_c) & (theta_c > 0.0)
        & np.isfinite(r_inner) & (r_inner > 0.0)
        & np.isfinite(r_outer) & (r_outer > r_inner)
        & np.isfinite(profile_radius) & (profile_radius > 0.0)
        & np.isfinite(k)
    )
    if finite.sum() < 2:
        raise ValueError(f"{run.name} has too few finite matched physical samples.")
    return {
        "n17": n17[finite],
        "mean_nh": mean_nh[finite],
        "csm_mass": csm_mass[finite],
        "jet_mass": jet_mass[finite],
        "theta_c": theta_c[finite],
        "r_inner": r_inner[finite],
        "r_outer": r_outer[finite],
        "profile_radius": profile_radius[finite],
        "k": k[finite],
    }


def save(fig, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    campaign = args.campaign.expanduser().resolve()
    events: dict[str, dict[str, np.ndarray]] = {}
    for run in event_dirs(campaign):
        try:
            events[run.name] = load_event(run)
        except ValueError as exc:
            print(f"WARNING: skipping {run.name}: {exc}")
    if not events:
        raise SystemExit("No campaign events supplied matched CSM/jet samples.")

    output = campaign / "comparison_plots"
    output.mkdir(parents=True, exist_ok=True)
    colors = plt.get_cmap("turbo")(np.linspace(0.03, 0.97, len(events)))

    # 1. Same physical quantity and units on both axes: enforce identical
    # decade limits and a one-to-one reference line.
    fig, ax = plt.subplots(figsize=(8.4, 8.4))
    shared_limits = log_limits([values[key] for values in events.values() for key in ("n17", "mean_nh")])
    for (event, values), color in zip(events.items(), colors, strict=True):
        errorbar(ax, values["n17"], values["mean_nh"], color=color, label=event)
    ax.plot(shared_limits, shared_limits, color="0.35", lw=1.1, ls="--", label=r"$\langle n_H\rangle=n_{17}$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(shared_limits)
    ax.set_ylim(shared_limits)
    ax.set_xlabel(r"Density normalization, $n_{17}$ [atoms cm$^{-3}$]")
    ax.set_ylabel(r"Data-range profile average, $\langle n_H\rangle$ [atoms cm$^{-3}$]")
    ax.set_title("Profile-Averaged Density versus Density Normalization")
    set_log_square_aspect(ax)
    ax.legend(loc="upper left", fontsize=7.1, ncol=2, frameon=True)
    fig.tight_layout()
    save(fig, output / "csm_mean_density_vs_n017")

    # 2. Both masses are in solar masses.  Put the broader posterior-median
    # range horizontally while retaining equal lengths per logarithmic decade.
    csm_span = np.ptp([np.log10(quantiles(values["csm_mass"])[1]) for values in events.values()])
    jet_span = np.ptp([np.log10(quantiles(values["jet_mass"])[1]) for values in events.values()])
    horizontal_key, vertical_key = ("csm_mass", "jet_mass") if csm_span >= jet_span else ("jet_mass", "csm_mass")
    horizontal_label = r"Data-range CSM mass, $M_{\rm profile}/M_\odot$" if horizontal_key == "csm_mass" else r"Two-sided jet ejecta mass, $M_j/M_\odot$"
    vertical_label = r"Two-sided jet ejecta mass, $M_j/M_\odot$" if vertical_key == "jet_mass" else r"Data-range CSM mass, $M_{\rm profile}/M_\odot$"
    x_limits = log_limits([values[horizontal_key] for values in events.values()])
    y_limits = log_limits([values[vertical_key] for values in events.values()])
    fig, ax = plt.subplots(figsize=(10.5, 7.0))
    for (event, values), color in zip(events.items(), colors, strict=True):
        errorbar(ax, values[horizontal_key], values[vertical_key], color=color, label=event)
    diagonal = (max(x_limits[0], y_limits[0]), min(x_limits[1], y_limits[1]))
    if diagonal[0] < diagonal[1]:
        ax.plot(diagonal, diagonal, color="0.35", lw=1.1, ls="--", label=r"$M_j=M_{\rm shell}$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(x_limits)
    ax.set_ylim(y_limits)
    ax.set_xlabel(horizontal_label)
    ax.set_ylabel(vertical_label)
    ax.set_title("Jet Ejecta Mass versus Data-Range CSM Mass")
    set_log_square_aspect(ax)
    ax.legend(loc="upper left", fontsize=7.1, ncol=2, frameon=True)
    fig.tight_layout()
    save(fig, output / "jet_mass_vs_csm_shell_mass")

    # 3. Shared k axis makes the two physically distinct CSM diagnostics easy
    # to compare without conflating solar-mass and number-density units.
    k_limits = linear_limits([values["k"] for values in events.values()])
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 10.0), sharex=True, constrained_layout=True)
    for (event, values), color in zip(events.items(), colors, strict=True):
        errorbar(axes[0], values["k"], values["csm_mass"], color=color, label=event)
        errorbar(axes[1], values["k"], values["mean_nh"], color=color, label=event)
    axes[0].set_yscale("log")
    axes[1].set_yscale("log")
    axes[0].set_ylabel(r"Data-range CSM mass, $M_{\rm profile}/M_\odot$")
    axes[1].set_ylabel(r"Profile average, $\langle n_H\rangle$ [atoms cm$^{-3}$]")
    axes[1].set_xlabel(r"CSM density-profile slope, $k$")
    axes[0].set_title("Data-Range CSM Mass and Profile-Averaged Density versus CSM Slope")
    for axis in axes:
        axis.set_xlim(k_limits)
        axis.grid(which="major", alpha=0.24)
        axis.grid(which="minor", alpha=0.08)
    axes[0].legend(loc="upper left", fontsize=7.1, ncol=2, frameon=True)
    save(fig, output / "csm_shell_mass_density_vs_k")

    # 4. This is the proposed physical constraint diagnostic, not a fitting
    # prior.  The shaded range is therefore a visual reference only.
    fig, ax = plt.subplots(figsize=(9.2, 7.0))
    density_limits = log_limits([values["mean_nh"] for values in events.values()])
    theta_limits = log_limits([values["theta_c"] for values in events.values()])
    ax.axvspan(1.0e-6, 1.0e10, color="#6abf69", alpha=0.11, zorder=0, label=r"Proposed $\langle n_H\rangle$ range")
    ax.axvline(1.0e-6, color="#4b8c4a", lw=1.0, ls="--", zorder=1)
    ax.axvline(1.0e10, color="#4b8c4a", lw=1.0, ls="--", zorder=1)
    for (event, values), color in zip(events.items(), colors, strict=True):
        errorbar(ax, values["mean_nh"], values["theta_c"], color=color, label=event)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(density_limits)
    ax.set_ylim(theta_limits)
    ax.set_xlabel(r"Data-range profile average, $\langle n_H\rangle$ [atoms cm$^{-3}$]")
    ax.set_ylabel(r"Core angle, $\theta_c$ [rad]")
    ax.set_title("Core Angle versus Profile-Averaged CSM Density")
    ax.grid(which="major", alpha=0.24)
    ax.grid(which="minor", alpha=0.08)
    ax.legend(loc="best", fontsize=7.0, ncol=2, frameon=True)
    fig.tight_layout()
    save(fig, output / "theta_c_vs_profile_mean_density")

    # 5. The horizontal pale interval is the posterior-median radial span of
    # the data-range profile, while the point/error bars summarize its
    # geometric-mean radius and the theta_c posterior.
    fig, ax = plt.subplots(figsize=(9.2, 7.0))
    for (event, values), color in zip(events.items(), colors, strict=True):
        r_inner_mid = quantiles(values["r_inner"])[1]
        r_outer_mid = quantiles(values["r_outer"])[1]
        theta_mid = quantiles(values["theta_c"])[1]
        ax.hlines(theta_mid, r_inner_mid, r_outer_mid, color=color, lw=4.0, alpha=0.24, zorder=1)
        errorbar(ax, values["profile_radius"], values["theta_c"], color=color, label=event)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(log_limits([values["r_inner"] for values in events.values()] + [values["r_outer"] for values in events.values()]))
    ax.set_ylim(theta_limits)
    ax.set_xlabel(r"Data-range profile radius, $r$ [cm]")
    ax.set_ylabel(r"Core angle, $\theta_c$ [rad]")
    ax.set_title("Core Angle versus Data-Range Profile Radius")
    ax.grid(which="major", alpha=0.24)
    ax.grid(which="minor", alpha=0.08)
    ax.legend(loc="best", fontsize=7.0, ncol=2, frameon=True)
    fig.tight_layout()
    save(fig, output / "theta_c_vs_profile_radius")

    write_summary(output / "csm_physical_scatter_summary.csv", events)
    print(f"Wrote campaign CSM physical scatters for {len(events)} events to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
