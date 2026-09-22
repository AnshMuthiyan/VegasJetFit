#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from evaluate_p4_full_profile_density_interpolator import pchip_eval, profiles_on_grid
from evaluate_p4n22_7param_model import despike_log_profile
from fit_p4_additional_features import extract_features
from plot_tight_density_profiles import final_file, read_plan, read_vtu

CAMPAIGN = Path(__file__).resolve().parent
PLOT_DIR = CAMPAIGN / "plots"
PLOT_DIR.mkdir(exist_ok=True)


@dataclass
class RegisteredProfile:
    run_id: str
    n_rho_exp: float
    x: np.ndarray
    y: np.ndarray
    x_ts: float
    x_outer_onset: float

    @property
    def log_x_ts(self) -> float:
        return float(np.log10(self.x_ts))

    @property
    def log_x_outer_onset(self) -> float:
        return float(np.log10(self.x_outer_onset))


def load_p4_registered_profiles() -> list[RegisteredProfile]:
    plan = read_plan()
    profiles: list[RegisteredProfile] = []
    run_ids = sorted([r for r in plan if r.startswith("p4_")], key=lambda r: int(r.split("_n")[1]))
    for run_id in run_ids:
        row = plan[run_id]
        radius_pc, rho_g_cm3, _ = read_vtu(final_file(run_id))
        x = radius_pc / row["rt_external_pc"]
        y = rho_g_cm3 / row["rho_g_cm3"]
        m = np.isfinite(x) & np.isfinite(y) & (x > 0.0) & (y > 0.0)
        x = x[m]
        y = despike_log_profile(y[m], threshold_dex=0.32, max_passes=1)
        order = np.argsort(x)
        x = x[order]
        y = y[order]

        feat = extract_features(x, y, run_id, row["rt_external_pc"])
        if not np.isfinite(feat.x_ts) or not np.isfinite(feat.x_final_rise):
            raise RuntimeError(f"{run_id}: could not extract registration anchors")
        if feat.x_final_rise <= feat.x_ts:
            raise RuntimeError(
                f"{run_id}: invalid registration anchors x_ts={feat.x_ts}, "
                f"x_final_rise={feat.x_final_rise}"
            )

        profiles.append(
            RegisteredProfile(
                run_id=run_id,
                n_rho_exp=-float(int(run_id.split("_n")[1])),
                x=x,
                y=y,
                x_ts=float(feat.x_ts),
                x_outer_onset=float(feat.x_final_rise),
            )
        )
    return sorted(profiles, key=lambda p: p.n_rho_exp)


def registered_coordinate(log_x: np.ndarray, log_x_ts: float, log_x_outer_onset: float) -> np.ndarray:
    span = log_x_outer_onset - log_x_ts
    if span <= 0.0:
        raise ValueError("registration span must be positive")
    return (log_x - log_x_ts) / span


def make_registered_grid(profiles: list[RegisteredProfile], n_points: int = 1000) -> np.ndarray:
    z_min = min(
        float(np.min(registered_coordinate(np.log10(p.x), p.log_x_ts, p.log_x_outer_onset)))
        for p in profiles
    )
    z_max = max(
        float(np.max(registered_coordinate(np.log10(p.x), p.log_x_ts, p.log_x_outer_onset)))
        for p in profiles
    )
    return np.linspace(z_min, z_max, n_points)


def profiles_on_registered_grid(profiles: list[RegisteredProfile], z_grid: np.ndarray) -> np.ndarray:
    table = []
    for p in profiles:
        z = registered_coordinate(np.log10(p.x), p.log_x_ts, p.log_x_outer_onset)
        ly = np.log10(np.maximum(p.y, 1e-300))
        table.append(np.interp(z_grid, z, ly, left=ly[0], right=ly[-1]))
    return np.asarray(table, dtype=float)


def interpolate_scalar_parameter(n_query: float, profiles: list[RegisteredProfile], values: np.ndarray) -> float:
    n_train = np.asarray([p.n_rho_exp for p in profiles], dtype=float)
    for n_val, value in zip(n_train, values):
        if abs(n_query - n_val) < 1e-12:
            return float(value)
    return float(pchip_eval(n_train, values, n_query))


def interpolate_registered_profile(
    n_query: float,
    x_query: np.ndarray,
    profiles: list[RegisteredProfile],
    z_grid: np.ndarray,
    logy_table: np.ndarray,
    exact_training_passthrough: bool = True,
) -> np.ndarray:
    n_train = np.asarray([p.n_rho_exp for p in profiles], dtype=float)
    if exact_training_passthrough:
        for p in profiles:
            if abs(n_query - p.n_rho_exp) < 1e-12:
                ly = np.log10(np.maximum(p.y, 1e-300))
                return 10.0 ** np.interp(np.log10(x_query), np.log10(p.x), ly, left=ly[0], right=ly[-1])

    log_x_ts = interpolate_scalar_parameter(
        n_query, profiles, np.asarray([p.log_x_ts for p in profiles], dtype=float)
    )
    log_x_outer = interpolate_scalar_parameter(
        n_query, profiles, np.asarray([p.log_x_outer_onset for p in profiles], dtype=float)
    )
    z_query = registered_coordinate(np.log10(x_query), log_x_ts, log_x_outer)

    logy_interp = np.array([pchip_eval(n_train, logy_table[:, j], n_query) for j in range(len(z_grid))])
    ly = np.interp(z_query, z_grid, logy_interp, left=logy_interp[0], right=logy_interp[-1])
    return despike_log_profile(10.0**ly, threshold_dex=0.32, max_passes=1)


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


def leave_one_out_prediction(
    target: RegisteredProfile,
    all_profiles: list[RegisteredProfile],
    z_points: int = 1000,
) -> np.ndarray:
    subset = [p for p in all_profiles if p.run_id != target.run_id]
    z_grid = make_registered_grid(subset, n_points=z_points)
    table = profiles_on_registered_grid(subset, z_grid)
    return interpolate_registered_profile(
        target.n_rho_exp,
        target.x,
        subset,
        z_grid,
        table,
        exact_training_passthrough=False,
    )


def make_plots(profiles: list[RegisteredProfile], z_grid: np.ndarray, logy_table: np.ndarray) -> tuple[Path, ...]:
    metrics: list[tuple[str, float, float, int, float, float]] = []

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    for ax, p in zip(axes.flat, profiles):
        y_model = interpolate_registered_profile(p.n_rho_exp, p.x, profiles, z_grid, logy_table)
        resid = np.log10(np.maximum(y_model, 1e-300)) - np.log10(np.maximum(p.y, 1e-300))
        rms = float(np.sqrt(np.mean(resid**2)))
        mad = float(np.median(np.abs(resid)))
        spikes = spike_count(y_model)
        metrics.append((p.run_id, rms, mad, spikes, p.x_ts, p.x_outer_onset))

        ax.plot(p.x, p.y, lw=2.0, label="AMRVAC de-spiked")
        ax.plot(p.x, y_model, ls="--", lw=1.8, label="registered full-profile model")
        ax.axvline(p.x_ts, color="0.25", ls=":", lw=1.0)
        ax.axvline(p.x_outer_onset, color="0.25", ls="--", lw=1.0)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$r/R_t$")
        ax.set_ylabel(r"$\rho/\rho_{ISM}$")
        ax.set_title(f"{p.run_id}  RMS={rms:.3g}, MAD={mad:.3g}, spikes={spikes}")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=8)
    training_plot = PLOT_DIR / "p4_registered_profile_interpolator_training_overlay.png"
    fig.savefig(training_plot, dpi=220)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(10, 6), constrained_layout=True)
    colors = plt.cm.viridis(np.linspace(0.10, 0.90, len(profiles)))
    for color, p in zip(colors, profiles):
        ax2.plot(p.x, p.y, color=color, lw=2.0, label=p.run_id)

    log_x_min = min(float(np.min(np.log10(p.x))) for p in profiles)
    log_x_max = max(float(np.max(np.log10(p.x))) for p in profiles)
    x_eval = 10.0 ** np.linspace(log_x_min, log_x_max, 1200)
    half_steps = [-23.5, -22.5, -21.5]
    for nq in half_steps:
        yq = interpolate_registered_profile(nq, x_eval, profiles, z_grid, logy_table, exact_training_passthrough=False)
        ax2.plot(x_eval, yq, color="k", ls="--", lw=1.2, alpha=0.78, label=f"n={nq:g}" if nq == half_steps[0] else None)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel(r"$r/R_t$")
    ax2.set_ylabel(r"$\rho/\rho_{ISM}$")
    ax2.set_title("Registered full-profile family at fixed pressure p=4")
    ax2.grid(True, which="both", alpha=0.25)
    ax2.legend(fontsize=8, ncol=2)
    family_plot = PLOT_DIR / "p4_registered_profile_interpolator_density_family.png"
    fig2.savefig(family_plot, dpi=220)
    plt.close(fig2)

    interior = [p for p in profiles if p.run_id in {"p4_n23", "p4_n22"}]
    fig3, axes3 = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)
    loo_rows: list[tuple[str, float, float, int]] = []
    for ax, p in zip(axes3.flat, interior):
        y_loo = leave_one_out_prediction(p, profiles)
        resid = np.log10(np.maximum(y_loo, 1e-300)) - np.log10(np.maximum(p.y, 1e-300))
        rms = float(np.sqrt(np.mean(resid**2)))
        mad = float(np.median(np.abs(resid)))
        spikes = spike_count(y_loo)
        loo_rows.append((p.run_id, rms, mad, spikes))
        ax.plot(p.x, p.y, lw=2.0, label="AMRVAC de-spiked")
        ax.plot(p.x, y_loo, ls="--", lw=1.8, label="leave-one-out prediction")
        ax.axvline(p.x_ts, color="0.25", ls=":", lw=1.0)
        ax.axvline(p.x_outer_onset, color="0.25", ls="--", lw=1.0)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$r/R_t$")
        ax.set_ylabel(r"$\rho/\rho_{ISM}$")
        ax.set_title(f"{p.run_id}  LOO RMS={rms:.3g}, MAD={mad:.3g}, spikes={spikes}")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=8)
    loo_plot = PLOT_DIR / "p4_registered_profile_interpolator_leave_one_out.png"
    fig3.savefig(loo_plot, dpi=220)
    plt.close(fig3)

    metrics_csv = PLOT_DIR / "p4_registered_profile_interpolator_metrics.csv"
    with metrics_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run_id", "rms_log10_resid", "mad_abs_log10_resid", "model_spike_count", "x_ts", "x_outer_onset"])
        w.writerows(metrics)

    loo_csv = PLOT_DIR / "p4_registered_profile_interpolator_leave_one_out_metrics.csv"
    with loo_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run_id", "loo_rms_log10_resid", "loo_mad_abs_log10_resid", "loo_model_spike_count"])
        w.writerows(loo_rows)

    report = PLOT_DIR / "p4_registered_profile_interpolator_report.txt"
    report.write_text(
        "\n".join(
            [
                "Registered full-profile density interpolator for p4 AMRVAC profiles",
                "",
                "Big-picture model:",
                "- Do not generate profiles by independently fitting many local features.",
                "- Use the two robust physical radii as a global registration map: true first shock and outer-wall rise onset.",
                "- Interpolate the entire registered log-density curve as a function of ambient density exponent n.",
                "- This preserves the connected AMRVAC morphology while still exposing one GRB-fit parameter at fixed pressure: n.",
                "",
                "Training-point residuals use exact pass-through at simulated densities:",
            ]
            + [f"{run}: RMS={rms:.6g}, MAD={mad:.6g}, spikes={spikes}, x_ts={x_ts:.6g}, x_outer={xout:.6g}" for run, rms, mad, spikes, x_ts, xout in metrics]
            + [
                "",
                "Leave-one-out interior checks:",
            ]
            + [f"{run}: LOO_RMS={rms:.6g}, LOO_MAD={mad:.6g}, spikes={spikes}" for run, rms, mad, spikes in loo_rows]
        )
    )

    return training_plot, family_plot, loo_plot, metrics_csv, loo_csv, report


def main() -> None:
    profiles = load_p4_registered_profiles()
    z_grid = make_registered_grid(profiles)
    logy_table = profiles_on_registered_grid(profiles, z_grid)
    for out in make_plots(profiles, z_grid, logy_table):
        print(out)


if __name__ == "__main__":
    main()
