#!/usr/bin/env python3
"""Plot minimized core ejecta mass against the requested core solid angle."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import zipfile

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.mcmc.parameters import Parameters
from scripts.generate_postfit_products import derive_jet_energy_posterior


def is_campaign_event_dir(path: Path) -> bool:
    """Return true for canonical event folders, not side-by-side comparisons."""
    name = path.name
    return (
        path.is_dir()
        and name != "trash"
        and not name.startswith((".", "_"))
        and "_no_" not in name
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument(
        "--output-stem",
        default="minimized_core_mass_vs_solid_angle",
    )
    return parser.parse_args()


def load_derived_posterior(run: Path, params: Parameters) -> dict[str, np.ndarray]:
    """Load derived samples, regenerating only when an older product lacks them."""
    saved = run / "jet_energy_posterior.npz"
    if saved.is_file():
        try:
            with np.load(saved) as data:
                return {
                    key: np.asarray(data[key], dtype=float)
                    for key in data.files
                    if np.issubdtype(np.asarray(data[key]).dtype, np.number)
                }
        except (OSError, ValueError, zipfile.BadZipFile):
            # A Drive placeholder or incomplete archive is recoverable from chain.npz.
            pass
    with np.load(run / "chain.npz") as data:
        chain = np.asarray(data["chain"], dtype=float)
    posterior = chain[chain.shape[0] // 2 :].reshape(-1, chain.shape[-1])
    derived, _ = derive_jet_energy_posterior(posterior, params, params.model)
    return derived


def load_minimized_point(run: Path) -> dict[str, float | str]:
    minimized_path = run / "minimized" / "minimized.json"
    payload = json.loads(minimized_path.read_text())
    if not payload.get("success", True):
        raise ValueError(f"Minimizer did not report success for {run.name}")

    params = Parameters.from_toml(run / "model.toml")
    x = np.asarray(payload["x"], dtype=float)
    if x.size != len(params.fitting):
        raise ValueError(
            f"Minimized vector length mismatch for {run.name}: "
            f"{x.size} != {len(params.fitting)}"
        )

    derived, _ = derive_jet_energy_posterior(
        x.reshape(1, -1),
        params,
        params.model,
    )
    theta_c = float(np.asarray(derived["theta_c"])[0])
    mass = float(np.asarray(derived["M_j_core_msun"])[0])
    energy = float(np.asarray(derived["E_j_core_52"])[0])
    gamma = float(np.asarray(derived["Gamma_0_core_avg"])[0])
    solid_angle = 2.0 * np.pi * theta_c**2
    exact_solid_angle = 4.0 * np.pi * (1.0 - np.cos(theta_c))

    posterior = load_derived_posterior(run, params)
    posterior_theta_c = np.asarray(posterior["theta_c"], dtype=float)
    posterior_mass = np.asarray(posterior["M_j_core_msun"], dtype=float)
    posterior_energy = np.asarray(posterior["E_j_core_52"], dtype=float)
    posterior_solid_angle = 2.0 * np.pi * posterior_theta_c**2
    valid = (
        np.isfinite(posterior_solid_angle)
        & np.isfinite(posterior_mass)
        & (posterior_solid_angle > 0.0)
        & (posterior_mass > 0.0)
    )
    posterior_solid_angle = posterior_solid_angle[valid]
    posterior_mass = posterior_mass[valid]
    posterior_mass_per_solid_angle = posterior_mass / posterior_solid_angle
    if posterior_mass.size == 0:
        raise ValueError(f"No finite posterior core-mass samples for {run.name}")
    omega_q16, omega_q50, omega_q84 = np.quantile(
        posterior_solid_angle, [0.16, 0.5, 0.84]
    )
    mass_q16, mass_q50, mass_q84 = np.quantile(
        posterior_mass, [0.16, 0.5, 0.84]
    )
    energy_valid = np.isfinite(posterior_energy) & (posterior_energy > 0.0)
    energy_q16, energy_q50, energy_q84 = np.quantile(
        posterior_energy[energy_valid], [0.16, 0.5, 0.84]
    )
    mass_per_sr_q16, mass_per_sr_q50, mass_per_sr_q84 = np.quantile(
        posterior_mass_per_solid_angle, [0.16, 0.5, 0.84]
    )

    if not all(
        np.isfinite(value) and value > 0.0
        for value in (theta_c, mass, energy, gamma, solid_angle)
    ):
        raise ValueError(f"Non-finite minimized derived value for {run.name}")

    return {
        "event": run.name,
        "nmap": float(payload["nmap"]),
        "theta_c_rad": theta_c,
        "solid_angle_2pi_theta_c_sq_sr": solid_angle,
        "exact_two_sided_core_solid_angle_sr": exact_solid_angle,
        "solid_angle_approx_over_exact": solid_angle / exact_solid_angle,
        "M_j_core_msun": mass,
        "E_j_core_52": energy,
        "Gamma_0_core_avg": gamma,
        "M_j_core_msun_per_sr": mass / solid_angle,
        "posterior_n_samples": int(posterior_mass.size),
        "solid_angle_posterior_q16_sr": float(omega_q16),
        "solid_angle_posterior_median_sr": float(omega_q50),
        "solid_angle_posterior_q84_sr": float(omega_q84),
        "M_j_core_posterior_q16_msun": float(mass_q16),
        "M_j_core_posterior_median_msun": float(mass_q50),
        "M_j_core_posterior_q84_msun": float(mass_q84),
        "E_j_core_posterior_q16_52": float(energy_q16),
        "E_j_core_posterior_median_52": float(energy_q50),
        "E_j_core_posterior_q84_52": float(energy_q84),
        "M_j_core_per_sr_posterior_q16_msun_per_sr": float(mass_per_sr_q16),
        "M_j_core_per_sr_posterior_median_msun_per_sr": float(mass_per_sr_q50),
        "M_j_core_per_sr_posterior_q84_msun_per_sr": float(mass_per_sr_q84),
    }


def annotate_events(ax, rows, x, y, colors, extra_offsets=None) -> None:
    """Add stable collision-conscious event labels."""
    offsets = ((7, 7), (7, -13), (-7, 7), (-7, -13))
    event_offsets = {
        "090618": (7, 7),
        "111228A": (7, -13),
        "220101A": (7, 7),
    }
    if extra_offsets:
        event_offsets.update(extra_offsets)
    for index, (row, x_value, y_value, color) in enumerate(zip(rows, x, y, colors)):
        dx, dy = event_offsets.get(row["event"], offsets[index % len(offsets)])
        ax.annotate(
            f"GRB {row['event']}",
            (x_value, y_value),
            xytext=(dx, dy),
            textcoords="offset points",
            ha="left" if dx > 0 else "right",
            va="bottom" if dy > 0 else "top",
            fontsize=8.5,
            color=color,
            fontweight="semibold",
            zorder=4,
        )


def draw_interval_bars(
    ax,
    rows,
    x,
    y,
    colors,
    y16_key: str,
    y84_key: str,
) -> None:
    """Draw exact marginal posterior intervals around minimized coordinates."""
    for row, x_value, y_value, color in zip(rows, x, y, colors):
        x16 = float(row["solid_angle_posterior_q16_sr"])
        x84 = float(row["solid_angle_posterior_q84_sr"])
        y16 = float(row[y16_key])
        y84 = float(row[y84_key])
        ax.hlines(y_value, x16, x84, color=color, lw=1.15, alpha=0.58, zorder=2)
        ax.vlines(x_value, y16, y84, color=color, lw=1.15, alpha=0.58, zorder=2)
        ax.plot(
            [x16, x84], [y_value, y_value], linestyle="none", marker="|",
            markersize=7, markeredgewidth=1.0, color=color, alpha=0.68, zorder=2,
        )
        ax.plot(
            [x_value, x_value], [y16, y84], linestyle="none", marker="_",
            markersize=7, markeredgewidth=1.0, color=color, alpha=0.68, zorder=2,
        )


def draw_mass_energy_interval_bars(ax, rows, energy, mass, colors) -> None:
    """Draw posterior intervals around minimized core energy/mass coordinates."""
    for row, x_value, y_value, color in zip(rows, energy, mass, colors):
        x16 = float(row["E_j_core_posterior_q16_52"])
        x84 = float(row["E_j_core_posterior_q84_52"])
        y16 = float(row["M_j_core_posterior_q16_msun"])
        y84 = float(row["M_j_core_posterior_q84_msun"])
        ax.hlines(y_value, x16, x84, color=color, lw=1.15, alpha=0.58, zorder=2)
        ax.vlines(x_value, y16, y84, color=color, lw=1.15, alpha=0.58, zorder=2)
        ax.plot([x16, x84], [y_value, y_value], linestyle="none", marker="|",
                markersize=7, markeredgewidth=1.0, color=color, alpha=0.68, zorder=2)
        ax.plot([x_value, x_value], [y16, y84], linestyle="none", marker="_",
                markersize=7, markeredgewidth=1.0, color=color, alpha=0.68, zorder=2)


def main() -> int:
    args = parse_args()
    campaign = args.campaign.expanduser().resolve()
    runs = sorted(
        path
        for path in campaign.iterdir()
        if is_campaign_event_dir(path)
        and (path / "minimized" / "minimized.json").is_file()
        and (path / "model.toml").is_file()
    )
    if not runs:
        raise SystemExit(f"No minimized runs found under {campaign}")

    rows = []
    skipped: list[dict[str, str]] = []
    for run in runs:
        try:
            rows.append(load_minimized_point(run))
        except ValueError as exc:
            if "Minimizer did not report success" not in str(exc):
                raise
            skipped.append({"event": run.name, "reason": str(exc)})
            print(f"WARNING: skipping {run.name} from minimized comparisons: {exc}")
    if not rows:
        raise SystemExit(f"No successful minimized runs found under {campaign}")
    x = np.asarray([row["solid_angle_2pi_theta_c_sq_sr"] for row in rows])
    y = np.asarray([row["M_j_core_msun"] for row in rows])
    colors = plt.get_cmap("turbo")(np.linspace(0.03, 0.97, len(rows)))

    fig, ax = plt.subplots(figsize=(9.2, 6.7))
    draw_interval_bars(
        ax, rows, x, y, colors,
        "M_j_core_posterior_q16_msun",
        "M_j_core_posterior_q84_msun",
    )
    ax.scatter(
        x,
        y,
        c=colors,
        s=72,
        edgecolor="black",
        linewidth=0.65,
        zorder=3,
    )

    annotate_events(ax, rows, x, y, colors)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(
        r"Core solid angle approximation, $2\pi\theta_c^2$ [sr]",
        fontsize=12.5,
    )
    ax.set_ylabel(
        r"Minimized two-sided core ejecta mass, $M_{j,\mathrm{core}}/M_\odot$",
        fontsize=12.5,
    )
    ax.set_title(
        "Minimized Core Ejecta Mass versus Core Solid Angle",
        fontsize=14.5,
        pad=10,
    )
    ax.grid(which="major", alpha=0.24)
    ax.grid(which="minor", alpha=0.09)
    ax.tick_params(labelsize=10.5)
    ax.margins(x=0.08, y=0.12)
    fig.text(
        0.995,
        0.008,
        r"Solid angle uses the requested two-sided small-angle approximation "
        r"$2\pi\theta_c^2$; bars span posterior 16th-84th percentiles and may "
        r"detach when the minimum lies outside the central interval.",
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))

    stem = campaign / args.output_stem
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    y_per_sr = np.asarray([row["M_j_core_msun_per_sr"] for row in rows])
    fig, ax = plt.subplots(figsize=(9.2, 6.7))
    draw_interval_bars(
        ax, rows, x, y_per_sr, colors,
        "M_j_core_per_sr_posterior_q16_msun_per_sr",
        "M_j_core_per_sr_posterior_q84_msun_per_sr",
    )
    ax.scatter(
        x, y_per_sr, c=colors, s=72, edgecolor="black",
        linewidth=0.65, zorder=3,
    )
    annotate_events(
        ax,
        rows,
        x,
        y_per_sr,
        colors,
        extra_offsets={
            "050525A": (-7, 17),
            "050922C": (7, -22),
            "090424": (-7, 9),
            "111228A": (7, 8),
            "140506A": (-7, -4),
            "160131A": (7, -15),
            "171010A": (-7, -20),
            "210905A": (-7, 14),
        },
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(
        r"Core solid angle approximation, $2\pi\theta_c^2$ [sr]",
        fontsize=12.5,
    )
    ax.set_ylabel(
        r"Minimized core ejecta mass per solid angle "
        r"$M_{j,\mathrm{core}}/(2\pi\theta_c^2)$ "
        r"[$M_\odot\,\mathrm{sr}^{-1}$]",
        fontsize=12.5,
    )
    ax.set_title(
        "Minimized Core Ejecta Mass per Solid Angle versus Core Solid Angle",
        fontsize=14.5,
        pad=10,
    )
    ax.grid(which="major", alpha=0.24)
    ax.grid(which="minor", alpha=0.09)
    ax.tick_params(labelsize=10.5)
    ax.margins(x=0.08, y=0.12)
    fig.text(
        0.995,
        0.008,
        r"Both coordinates use each sample's own $2\pi\theta_c^2$; bars span "
        r"posterior 16th-84th percentiles.",
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    per_sr_stem = campaign / "minimized_core_mass_per_solid_angle_vs_solid_angle"
    fig.savefig(per_sr_stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(
        per_sr_stem.with_suffix(".png"),
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.04,
    )
    plt.close(fig)

    energy = np.asarray([row["E_j_core_52"] for row in rows])
    fig, ax = plt.subplots(figsize=(9.2, 6.7))
    draw_mass_energy_interval_bars(ax, rows, energy, y, colors)
    ax.scatter(
        energy, y, c=colors, s=72, edgecolor="black", linewidth=0.65, zorder=3,
    )
    annotate_events(
        ax,
        rows,
        energy,
        y,
        colors,
        extra_offsets={
            "050525A": (-8, 12),
            "050922C": (8, -18),
            "080319B": (-18, 16),
            "080413B": (-8, -22),
            "090424": (-8, -22),
            "090618": (8, -22),
            "111228A": (8, -18),
            "130612A": (8, 14),
            "131030A": (-8, 16),
            "140506A": (-8, -20),
            "160131A": (-8, 16),
            "171010A": (8, -24),
            "210905A": (-8, 16),
            "220101A": (8, -20),
            "221009A": (-8, -16),
        },
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(
        r"Minimized two-sided core jet energy, $E_{j,\mathrm{core}}/10^{52}\,\mathrm{erg}$",
        fontsize=12.5,
    )
    ax.set_ylabel(
        r"Minimized two-sided core ejecta mass, $M_{j,\mathrm{core}}/M_\odot$",
        fontsize=12.5,
    )
    ax.set_title(
        "Minimized Core Ejecta Mass versus Core Jet Energy",
        fontsize=14.5,
        pad=10,
    )
    ax.grid(which="major", alpha=0.24)
    ax.grid(which="minor", alpha=0.09)
    ax.tick_params(labelsize=10.5)
    ax.margins(x=0.08, y=0.12)
    fig.text(
        0.995,
        0.008,
        r"Bars span posterior 16th-84th percentiles in each coordinate and may "
        r"detach when the minimized point lies outside the central interval.",
        ha="right",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    mass_energy_stem = campaign / "minimized_core_mass_vs_core_energy"
    fig.savefig(mass_energy_stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(
        mass_energy_stem.with_suffix(".png"), dpi=220, bbox_inches="tight", pad_inches=0.04,
    )
    plt.close(fig)

    with stem.with_suffix(".csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    if skipped:
        skipped_path = campaign / "minimized_comparison_skipped_runs.csv"
        with skipped_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("event", "reason"))
            writer.writeheader()
            writer.writerows(skipped)
        print(f"Wrote {skipped_path}")

    print(f"Wrote {stem.with_suffix('.pdf')}")
    print(f"Wrote {stem.with_suffix('.png')}")
    print(f"Wrote {stem.with_suffix('.csv')}")
    print(f"Wrote {per_sr_stem.with_suffix('.pdf')}")
    print(f"Wrote {per_sr_stem.with_suffix('.png')}")
    print(f"Wrote {mass_energy_stem.with_suffix('.pdf')}")
    print(f"Wrote {mass_energy_stem.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
