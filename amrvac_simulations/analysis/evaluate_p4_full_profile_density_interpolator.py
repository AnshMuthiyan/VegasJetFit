#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_tight_density_profiles import final_file, read_plan, read_vtu
from evaluate_p4n22_7param_model import despike_log_profile

CAMPAIGN = Path(__file__).resolve().parent
PLOT_DIR = CAMPAIGN / "plots"
PLOT_DIR.mkdir(exist_ok=True)


@dataclass
class Profile:
    run_id: str
    n_rho_exp: float
    x: np.ndarray
    y: np.ndarray


def load_p4_profiles() -> list[Profile]:
    plan = read_plan()
    profiles: list[Profile] = []
    for run in sorted([r for r in plan if r.startswith("p4_")], key=lambda r: int(r.split("_n")[1])):
        radius_pc, rho_g_cm3, _ = read_vtu(final_file(run))
        row = plan[run]
        x = radius_pc / row["rt_external_pc"]
        y = rho_g_cm3 / row["rho_g_cm3"]
        m = np.isfinite(x) & np.isfinite(y) & (x > 0.0) & (y > 0.0)
        x = x[m]
        y = despike_log_profile(y[m], threshold_dex=0.32, max_passes=1)
        order = np.argsort(x)
        n_rho_exp = -float(int(run.split("_n")[1]))
        profiles.append(Profile(run_id=run, n_rho_exp=n_rho_exp, x=x[order], y=y[order]))
    return sorted(profiles, key=lambda p: p.n_rho_exp)


def make_common_grid(profiles: list[Profile], n_points: int = 900) -> np.ndarray:
    u_min = min(float(np.min(np.log10(p.x))) for p in profiles)
    u_max = max(float(np.max(np.log10(p.x))) for p in profiles)
    return np.linspace(u_min, u_max, n_points)


def profiles_on_grid(profiles: list[Profile], u_grid: np.ndarray) -> np.ndarray:
    table = []
    for p in profiles:
        u = np.log10(p.x)
        ly = np.log10(np.maximum(p.y, 1e-300))
        table.append(np.interp(u_grid, u, ly, left=ly[0], right=ly[-1]))
    return np.asarray(table, dtype=float)


def pchip_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    h = np.diff(x)
    delta = np.diff(y) / h
    m = np.zeros_like(y)
    if len(x) == 2:
        m[:] = delta[0]
        return m

    for k in range(1, len(x) - 1):
        if delta[k - 1] == 0.0 or delta[k] == 0.0 or np.sign(delta[k - 1]) != np.sign(delta[k]):
            m[k] = 0.0
        else:
            w1 = 2.0 * h[k] + h[k - 1]
            w2 = h[k] + 2.0 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])

    m[0] = ((2.0 * h[0] + h[1]) * delta[0] - h[0] * delta[1]) / (h[0] + h[1])
    if np.sign(m[0]) != np.sign(delta[0]):
        m[0] = 0.0
    elif np.sign(delta[0]) != np.sign(delta[1]) and abs(m[0]) > abs(3.0 * delta[0]):
        m[0] = 3.0 * delta[0]

    m[-1] = ((2.0 * h[-1] + h[-2]) * delta[-1] - h[-1] * delta[-2]) / (h[-1] + h[-2])
    if np.sign(m[-1]) != np.sign(delta[-1]):
        m[-1] = 0.0
    elif np.sign(delta[-1]) != np.sign(delta[-2]) and abs(m[-1]) > abs(3.0 * delta[-1]):
        m[-1] = 3.0 * delta[-1]
    return m


def pchip_eval(x: np.ndarray, y: np.ndarray, xq: float) -> float:
    if xq <= x[0]:
        return float(y[0])
    if xq >= x[-1]:
        return float(y[-1])

    k = int(np.searchsorted(x, xq) - 1)
    h = x[k + 1] - x[k]
    t = (xq - x[k]) / h
    m = pchip_slopes(x, y)
    h00 = (2.0 * t**3 - 3.0 * t**2 + 1.0)
    h10 = (t**3 - 2.0 * t**2 + t)
    h01 = (-2.0 * t**3 + 3.0 * t**2)
    h11 = (t**3 - t**2)
    return float(h00 * y[k] + h10 * h * m[k] + h01 * y[k + 1] + h11 * h * m[k + 1])


def interpolate_profile(
    n_query: float,
    x_query: np.ndarray,
    profiles: list[Profile],
    u_grid: np.ndarray,
    logy_table: np.ndarray,
) -> np.ndarray:
    n_train = np.asarray([p.n_rho_exp for p in profiles], dtype=float)
    # Exact pass-through at training densities avoids interpolation blur.
    for p in profiles:
        if abs(n_query - p.n_rho_exp) < 1e-12:
            return 10.0 ** np.interp(np.log10(x_query), np.log10(p.x), np.log10(np.maximum(p.y, 1e-300)), left=np.log10(p.y[0]), right=np.log10(p.y[-1]))

    logy_interp = np.array([pchip_eval(n_train, logy_table[:, j], n_query) for j in range(len(u_grid))])
    y = 10.0 ** np.interp(np.log10(x_query), u_grid, logy_interp, left=logy_interp[0], right=logy_interp[-1])
    return despike_log_profile(y, threshold_dex=0.32, max_passes=1)


def spike_count(y: np.ndarray, threshold_dex: float = 0.32) -> int:
    ly = np.log10(np.maximum(y, 1e-300))
    count = 0
    for i in range(2, len(y) - 2):
        med = float(np.median([ly[i - 2], ly[i - 1], ly[i + 1], ly[i + 2]]))
        if abs(ly[i] - med) <= threshold_dex:
            continue
        if (ly[i] - ly[i - 1]) * (ly[i + 1] - ly[i]) < 0.0:
            count += 1
    return count


def make_plots(profiles: list[Profile], u_grid: np.ndarray, logy_table: np.ndarray) -> tuple[Path, Path, Path, Path]:
    metrics: list[tuple[str, float, float, int]] = []

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    for ax, p in zip(axes.flat, profiles):
        y_model = interpolate_profile(p.n_rho_exp, p.x, profiles, u_grid, logy_table)
        resid = np.log10(np.maximum(y_model, 1e-300)) - np.log10(np.maximum(p.y, 1e-300))
        rms = float(np.sqrt(np.mean(resid**2)))
        mad = float(np.median(np.abs(resid)))
        spikes = spike_count(y_model)
        metrics.append((p.run_id, rms, mad, spikes))

        ax.plot(p.x, p.y, lw=2.0, label="AMRVAC de-spiked")
        ax.plot(p.x, y_model, ls="--", lw=1.8, label="full-profile interpolator")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$r/R_t$")
        ax.set_ylabel(r"$\rho/\rho_{ISM}$")
        ax.set_title(f"{p.run_id}  RMS={rms:.3g}, MAD={mad:.3g}, spikes={spikes}")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=8)
    exact_plot = PLOT_DIR / "p4_full_profile_interpolator_training_overlay.png"
    fig.savefig(exact_plot, dpi=220)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(10, 6), constrained_layout=True)
    colors = plt.cm.viridis(np.linspace(0.10, 0.90, len(profiles)))
    for color, p in zip(colors, profiles):
        ax2.plot(p.x, p.y, color=color, lw=2.0, label=p.run_id)

    half_steps = [-23.5, -22.5, -21.5]
    x_eval = 10.0 ** u_grid
    for nq in half_steps:
        yq = interpolate_profile(nq, x_eval, profiles, u_grid, logy_table)
        ax2.plot(x_eval, yq, color="k", ls="--", lw=1.15, alpha=0.75, label=f"n={nq:g}" if nq == half_steps[0] else None)

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel(r"$r/R_t$")
    ax2.set_ylabel(r"$\rho/\rho_{ISM}$")
    ax2.set_title("Continuous p4 density-profile family (solid grid runs, dashed intermediate densities)")
    ax2.grid(True, which="both", alpha=0.25)
    ax2.legend(fontsize=8, ncol=2)
    family_plot = PLOT_DIR / "p4_full_profile_interpolator_density_family.png"
    fig2.savefig(family_plot, dpi=220)
    plt.close(fig2)

    metrics_csv = PLOT_DIR / "p4_full_profile_interpolator_training_metrics.csv"
    with metrics_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run_id", "rms_log10_resid", "mad_abs_log10_resid", "model_spike_count"])
        w.writerows(metrics)

    report = PLOT_DIR / "p4_full_profile_interpolator_report.txt"
    report.write_text(
        "\n".join(
            [
                "Full-profile density interpolator for p4 AMRVAC profiles",
                "Goal: fit ambient density at fixed ambient pressure without splitting the family.",
                "",
                "Model:",
                "- De-spike each AMRVAC profile only for isolated one-point log-density extrema.",
                "- Store log10(r/Rt) grid and log10(rho/rho_ISM) profile table.",
                "- Interpolate the whole profile as a function of ambient density exponent n using shape-preserving cubic interpolation.",
                "- Exact pass-through is used at simulated training densities.",
                "",
                "Why this replaces the 7-parameter p4_n22 warp:",
                "- The 7-feature warp breaks the coupled density structure and can make good overlays worse.",
                "- The full-profile table keeps the bubble shape whole while still giving one continuous fit parameter: n.",
                "- The extracted features remain useful diagnostics, not the profile generator.",
                "",
                "Training-point residuals:",
            ]
            + [f"{run}: RMS={rms:.6g}, MAD={mad:.6g}, spikes={spikes}" for run, rms, mad, spikes in metrics]
        )
    )

    return exact_plot, family_plot, metrics_csv, report


def main() -> None:
    profiles = load_p4_profiles()
    u_grid = make_common_grid(profiles)
    logy_table = profiles_on_grid(profiles, u_grid)
    for out in make_plots(profiles, u_grid, logy_table):
        print(out)


if __name__ == "__main__":
    main()
