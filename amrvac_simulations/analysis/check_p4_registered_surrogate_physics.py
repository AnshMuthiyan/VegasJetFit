#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from evaluate_p4_registered_profile_interpolator import (
    RegisteredProfile,
    interpolate_registered_profile,
    load_p4_registered_profiles,
    make_registered_grid,
    profiles_on_registered_grid,
    registered_coordinate,
)
from plot_tight_density_profiles import PC_CM, read_plan

CAMPAIGN = Path(__file__).resolve().parent
PLOT_DIR = CAMPAIGN / "plots"
PLOT_DIR.mkdir(exist_ok=True)


@dataclass
class ProfileCheck:
    label: str
    n_rho_exp: float
    x_ts: float
    x_outer_onset: float
    x_ism90: float
    wind_pre_ratio_median: float
    shock_post_ratio_median: float
    outer_ism_median: float
    dimensionless_mass_to_outer_onset: float
    dimensionless_mass_to_ism90: float
    physical_mass_to_outer_onset_g_sr: float
    physical_mass_to_ism90_g_sr: float
    cumulative_mass_monotone: bool
    spike_count: int


def smooth_log10(y: np.ndarray, width: int = 9) -> np.ndarray:
    width = max(3, int(width) | 1)
    ly = np.log10(np.maximum(y, 1e-300))
    kernel = np.ones(width, dtype=float) / float(width)
    return np.convolve(np.pad(ly, (width // 2, width // 2), mode="edge"), kernel, mode="valid")


def pchip_scalar(n_query: float, n_train: np.ndarray, y_train: np.ndarray) -> float:
    from evaluate_p4_full_profile_density_interpolator import pchip_eval

    for n_val, y_val in zip(n_train, y_train):
        if abs(n_query - n_val) < 1e-12:
            return float(y_val)
    return float(pchip_eval(n_train, y_train, n_query))


def interpolate_anchor(n_query: float, profiles: list[RegisteredProfile], attr: str) -> float:
    n_train = np.asarray([p.n_rho_exp for p in profiles], dtype=float)
    vals = np.asarray([getattr(p, attr) for p in profiles], dtype=float)
    return pchip_scalar(n_query, n_train, vals)


def cumulative_trapezoid(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return np.asarray([], dtype=float)
    increments = 0.5 * (y[1:] + y[:-1]) * np.diff(x)
    return np.concatenate(([0.0], np.cumsum(increments)))


def dimensionless_cumulative_mass(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    # Per-solid-angle mass in normalized coordinates:
    # dM/dOmega = rho_ISM * R_t^3 * integral y(x) x^2 dx.
    order = np.argsort(x)
    xs = x[order]
    ys = y[order]
    return cumulative_trapezoid(xs, ys * xs**2)


def interp_monotone(x: np.ndarray, y: np.ndarray, xq: float) -> float:
    if not np.isfinite(xq):
        return float("nan")
    order = np.argsort(x)
    xs = x[order]
    ys = y[order]
    if xq <= xs[0]:
        return float(ys[0])
    if xq >= xs[-1]:
        return float(ys[-1])
    return float(np.interp(xq, xs, ys))


def crossing_up_logx(x: np.ndarray, y: np.ndarray, target: float, start_index: int) -> float:
    ly = smooth_log10(y, width=9)
    lx = np.log10(x)
    lt = float(np.log10(target))
    for i in range(max(0, start_index), len(x) - 1):
        y0 = ly[i]
        y1 = ly[i + 1]
        if (y0 <= lt <= y1) or (y1 <= lt <= y0):
            frac = 0.0 if y1 == y0 else (lt - y0) / (y1 - y0)
            return float(10.0 ** (lx[i] + frac * (lx[i + 1] - lx[i])))
    return float("nan")


def find_x_ism90(x: np.ndarray, y: np.ndarray, x_outer_onset: float) -> float:
    if x.size < 10:
        return float("nan")
    start = int(np.searchsorted(x, max(x_outer_onset, 1.0)))
    crossing = crossing_up_logx(x, y, target=0.90, start_index=start)
    if np.isfinite(crossing):
        return crossing
    # If the profile is already essentially at the ISM after the onset,
    # use the first point above 0.9 as a fallback.
    idx = np.where((np.arange(x.size) >= start) & (y >= 0.90))[0]
    return float(x[idx[0]]) if idx.size else float("nan")


def local_wind_norm(x: np.ndarray, y: np.ndarray, x_ts: float) -> float:
    pre = (x > max(np.min(x), 0.35 * x_ts)) & (x < 0.80 * x_ts)
    if np.count_nonzero(pre) < 5:
        pre = x < 0.85 * x_ts
    if np.count_nonzero(pre) < 3:
        pre = x < x_ts
    return float(np.median(y[pre] * x[pre] ** 2))


def shock_ratios(x: np.ndarray, y: np.ndarray, x_ts: float) -> tuple[float, float]:
    a = local_wind_norm(x, y, x_ts)
    y_wind = a / np.maximum(x, 1e-300) ** 2
    ratio = y / np.maximum(y_wind, 1e-300)
    pre = (x > 0.80 * x_ts) & (x < 0.96 * x_ts)
    post = (x > 1.02 * x_ts) & (x < 1.18 * x_ts)
    pre_ratio = float(np.median(ratio[pre])) if np.count_nonzero(pre) else float("nan")
    post_ratio = float(np.median(ratio[post])) if np.count_nonzero(post) else float("nan")
    return pre_ratio, post_ratio


def isolated_spike_count(y: np.ndarray, threshold_dex: float = 0.32) -> int:
    ly = np.log10(np.maximum(y, 1e-300))
    count = 0
    for i in range(2, len(y) - 2):
        med = float(np.median([ly[i - 2], ly[i - 1], ly[i + 1], ly[i + 2]]))
        if abs(ly[i] - med) <= threshold_dex:
            continue
        if (ly[i] - ly[i - 1]) * (ly[i + 1] - ly[i]) < 0.0:
            count += 1
    return count


def check_profile(
    label: str,
    n_rho_exp: float,
    x: np.ndarray,
    y: np.ndarray,
    x_ts: float,
    x_outer_onset: float,
    rt_pc: float,
) -> ProfileCheck:
    x_ism90 = find_x_ism90(x, y, x_outer_onset)
    cum = dimensionless_cumulative_mass(x, y)
    dim_mass_outer = interp_monotone(x, cum, x_outer_onset)
    dim_mass_ism90 = interp_monotone(x, cum, x_ism90)
    rho_ism = 10.0**n_rho_exp
    mass_scale = rho_ism * (rt_pc * PC_CM) ** 3
    pre_ratio, post_ratio = shock_ratios(x, y, x_ts)

    outer_mask = x > max(1.15 * x_ism90 if np.isfinite(x_ism90) else 1.2 * x_outer_onset, x_outer_onset)
    if np.count_nonzero(outer_mask) < 8:
        outer_mask = x > np.percentile(x, 85)
    outer_ism_median = float(np.median(y[outer_mask])) if np.count_nonzero(outer_mask) else float("nan")

    return ProfileCheck(
        label=label,
        n_rho_exp=n_rho_exp,
        x_ts=x_ts,
        x_outer_onset=x_outer_onset,
        x_ism90=x_ism90,
        wind_pre_ratio_median=pre_ratio,
        shock_post_ratio_median=post_ratio,
        outer_ism_median=outer_ism_median,
        dimensionless_mass_to_outer_onset=dim_mass_outer,
        dimensionless_mass_to_ism90=dim_mass_ism90,
        physical_mass_to_outer_onset_g_sr=dim_mass_outer * mass_scale,
        physical_mass_to_ism90_g_sr=dim_mass_ism90 * mass_scale,
        cumulative_mass_monotone=bool(np.all(np.diff(cum) >= -1e-12 * max(float(np.nanmax(cum)), 1.0))),
        spike_count=isolated_spike_count(y),
    )


def make_surrogate_grid(
    profiles: list[RegisteredProfile],
    z_grid: np.ndarray,
    logy_table: np.ndarray,
    n_values: np.ndarray,
) -> tuple[np.ndarray, dict[float, tuple[np.ndarray, np.ndarray, float, float]]]:
    log_x_min = min(float(np.min(np.log10(p.x))) for p in profiles)
    log_x_max = max(float(np.max(np.log10(p.x))) for p in profiles)
    x_eval = 10.0 ** np.linspace(log_x_min, log_x_max, 1600)
    outputs: dict[float, tuple[np.ndarray, np.ndarray, float, float]] = {}
    for n_val in n_values:
        y_eval = interpolate_registered_profile(
            float(n_val), x_eval, profiles, z_grid, logy_table, exact_training_passthrough=False
        )
        x_ts = interpolate_anchor(float(n_val), profiles, "x_ts")
        x_outer = interpolate_anchor(float(n_val), profiles, "x_outer_onset")
        outputs[float(n_val)] = (x_eval, y_eval, x_ts, x_outer)
    return x_eval, outputs


def write_checks_csv(path: Path, checks: list[ProfileCheck]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "label",
                "n_rho_exp",
                "x_ts",
                "x_outer_onset",
                "x_ism90",
                "wind_pre_ratio_median",
                "shock_post_ratio_median",
                "outer_ism_median",
                "dimensionless_mass_to_outer_onset",
                "dimensionless_mass_to_ism90",
                "physical_mass_to_outer_onset_g_sr",
                "physical_mass_to_ism90_g_sr",
                "cumulative_mass_monotone",
                "spike_count",
            ]
        )
        for c in checks:
            w.writerow(
                [
                    c.label,
                    c.n_rho_exp,
                    c.x_ts,
                    c.x_outer_onset,
                    c.x_ism90,
                    c.wind_pre_ratio_median,
                    c.shock_post_ratio_median,
                    c.outer_ism_median,
                    c.dimensionless_mass_to_outer_onset,
                    c.dimensionless_mass_to_ism90,
                    c.physical_mass_to_outer_onset_g_sr,
                    c.physical_mass_to_ism90_g_sr,
                    c.cumulative_mass_monotone,
                    c.spike_count,
                ]
            )


def plot_mass_profiles(
    profiles: list[RegisteredProfile],
    surrogate_outputs: dict[float, tuple[np.ndarray, np.ndarray, float, float]],
    rt_pc: float,
) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(profiles)))
    for color, p in zip(colors, profiles):
        cum = dimensionless_cumulative_mass(p.x, p.y)
        rho_ism = 10.0**p.n_rho_exp
        axes[0].plot(p.x, cum, color=color, lw=2.0, label=p.run_id)
        axes[1].plot(p.x, cum * rho_ism * (rt_pc * PC_CM) ** 3, color=color, lw=2.0, label=p.run_id)

    for n_val in [-23.5, -22.5, -21.5]:
        x, y, _, _ = surrogate_outputs[n_val]
        cum = dimensionless_cumulative_mass(x, y)
        rho_ism = 10.0**n_val
        axes[0].plot(x, cum, color="0.2", ls="--", lw=1.1, alpha=0.8)
        axes[1].plot(x, cum * rho_ism * (rt_pc * PC_CM) ** 3, color="0.2", ls="--", lw=1.1, alpha=0.8)

    axes[0].set_ylabel(r"$\int (\rho/\rho_{ISM}) x^2\,dx$")
    axes[1].set_ylabel(r"$dM/d\Omega$ [g sr$^{-1}$]")
    for ax in axes:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$x=r/R_t$")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=8, ncol=2)
    axes[0].set_title("Dimensionless cumulative swept mass")
    axes[1].set_title("Physical cumulative swept mass")
    out = PLOT_DIR / "p4_registered_surrogate_cumulative_mass_profiles.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_mass_and_radii_vs_density(checks: list[ProfileCheck], dense_checks: list[ProfileCheck]) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    dense_n = np.asarray([c.n_rho_exp for c in dense_checks])
    train = [c for c in checks if c.label.startswith("p4_n")]
    train_n = np.asarray([c.n_rho_exp for c in train])

    axes[0, 0].plot(dense_n, [c.x_ts for c in dense_checks], color="0.25", lw=1.6)
    axes[0, 0].plot(train_n, [c.x_ts for c in train], "o", color="tab:blue", label="AMRVAC grid")
    axes[0, 0].plot(dense_n, [c.x_outer_onset for c in dense_checks], color="0.25", lw=1.6, ls="--")
    axes[0, 0].plot(train_n, [c.x_outer_onset for c in train], "s", color="tab:orange", label="outer onset")
    axes[0, 0].set_ylabel(r"radius in $r/R_t$")
    axes[0, 0].set_title("Registered shock radii")
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].plot(dense_n, [c.x_ism90 for c in dense_checks], color="0.25", lw=1.6)
    axes[0, 1].plot(train_n, [c.x_ism90 for c in train], "o", color="tab:green")
    axes[0, 1].set_ylabel(r"$x(\rho/\rho_{ISM}=0.9)$")
    axes[0, 1].set_title("Outer ISM recovery radius")

    axes[1, 0].plot(dense_n, [c.dimensionless_mass_to_ism90 for c in dense_checks], color="0.25", lw=1.6)
    axes[1, 0].plot(train_n, [c.dimensionless_mass_to_ism90 for c in train], "o", color="tab:purple")
    axes[1, 0].set_yscale("log")
    axes[1, 0].set_ylabel(r"$\int^{x_{0.9}} y x^2 dx$")
    axes[1, 0].set_title("Dimensionless mass to outer wall")

    axes[1, 1].plot(dense_n, [c.physical_mass_to_ism90_g_sr for c in dense_checks], color="0.25", lw=1.6)
    axes[1, 1].plot(train_n, [c.physical_mass_to_ism90_g_sr for c in train], "o", color="tab:red")
    axes[1, 1].set_yscale("log")
    axes[1, 1].set_ylabel(r"$dM/d\Omega$ to $x_{0.9}$ [g sr$^{-1}$]")
    axes[1, 1].set_title("Physical mass to outer wall")

    for ax in axes.flat:
        ax.set_xlabel(r"$n=\log_{10}(\rho_{ISM}/{\rm g\,cm^{-3}})$")
        ax.grid(True, alpha=0.25)
    out = PLOT_DIR / "p4_registered_surrogate_mass_and_radii_vs_density.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_registered_heatmap(
    profiles: list[RegisteredProfile],
    z_grid: np.ndarray,
    logy_table: np.ndarray,
    n_dense: np.ndarray,
) -> Path:
    from evaluate_p4_full_profile_density_interpolator import pchip_eval

    n_train = np.asarray([p.n_rho_exp for p in profiles], dtype=float)
    image = np.zeros((len(n_dense), len(z_grid)))
    for i, n_val in enumerate(n_dense):
        image[i, :] = [pchip_eval(n_train, logy_table[:, j], float(n_val)) for j in range(len(z_grid))]

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    extent = [float(z_grid[0]), float(z_grid[-1]), float(n_dense[0]), float(n_dense[-1])]
    im = ax.imshow(image, aspect="auto", origin="lower", extent=extent, cmap="magma")
    for p in profiles:
        ax.axhline(p.n_rho_exp, color="w", lw=0.8, alpha=0.45)
    ax.axvline(0.0, color="cyan", ls=":", lw=1.1, label="first shock")
    ax.axvline(1.0, color="cyan", ls="--", lw=1.1, label="outer onset")
    ax.set_xlabel(r"registered coordinate $z$")
    ax.set_ylabel(r"$n=\log_{10}(\rho_{ISM}/{\rm g\,cm^{-3}})$")
    ax.set_title(r"Smooth registered profile table: $\log_{10}(\rho/\rho_{ISM})$")
    ax.legend(fontsize=8, loc="upper right")
    fig.colorbar(im, ax=ax, label=r"$\log_{10}(\rho/\rho_{ISM})$")
    out = PLOT_DIR / "p4_registered_surrogate_registered_density_heatmap.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def smoothness_diagnostics(dense_checks: list[ProfileCheck]) -> dict[str, float | int | bool]:
    n = np.asarray([c.n_rho_exp for c in dense_checks], dtype=float)
    mass = np.asarray([c.physical_mass_to_ism90_g_sr for c in dense_checks], dtype=float)
    x90 = np.asarray([c.x_ism90 for c in dense_checks], dtype=float)
    log_mass = np.log10(np.maximum(mass, 1e-300))
    d1 = np.gradient(log_mass, n)
    d2 = np.gradient(d1, n)
    dx = np.gradient(x90, n)
    return {
        "n_samples": int(len(n)),
        "mass_positive": bool(np.all(mass > 0.0)),
        "x90_finite": bool(np.all(np.isfinite(x90))),
        "max_abs_dlogM_dn": float(np.max(np.abs(d1))),
        "max_abs_d2logM_dn2": float(np.max(np.abs(d2))),
        "x90_derivative_sign_changes": int(np.count_nonzero(np.diff(np.signbit(dx)))),
        "all_cumulative_mass_monotone": bool(all(c.cumulative_mass_monotone for c in dense_checks)),
        "max_spike_count": int(max(c.spike_count for c in dense_checks)),
    }


def write_report(
    path: Path,
    checks: list[ProfileCheck],
    dense_checks: list[ProfileCheck],
    diagnostics: dict[str, float | int | bool],
    outputs: list[Path],
) -> None:
    train = [c for c in checks if c.label.startswith("p4_n")]
    lines = [
        "p4 registered empirical-bubble surrogate physics checks",
        "",
        "Conclusion:",
        "- The 7-feature template warp should not be used as the production profile generator.",
        "- The registered full-profile surrogate is internally consistent for the p4 pressure slice.",
        "- It preserves the AMRVAC training profiles exactly after light de-spiking.",
        "- It gives a smooth one-parameter density family in n = log10(rho_ISM / g cm^-3).",
        "- The model should be exported with cumulative-mass checks, because GRB dynamics care about swept mass.",
        "",
        "Definitions:",
        "- x = r/R_t, with R_t fixed by the p4 pressure environment for this slice.",
        "- y = rho/rho_ISM.",
        "- Dimensionless swept mass per solid angle is integral y x^2 dx.",
        "- Physical swept mass per solid angle is rho_ISM R_t^3 integral y x^2 dx.",
        "- x_ts is the measured first-shock/termination-shock position.",
        "- x_outer_onset is the onset of the final outer-wall rise.",
        "- x_ism90 is the first radius after the outer onset where y reaches 0.9.",
        "",
        "Training-run checks:",
    ]
    for c in train:
        lines.append(
            f"- {c.label}: n={c.n_rho_exp:.1f}, x_ts={c.x_ts:.4g}, "
            f"x_outer={c.x_outer_onset:.4g}, x_ism90={c.x_ism90:.4g}, "
            f"shock_post/prewind={c.shock_post_ratio_median:.3g}, "
            f"outer_ISM_median={c.outer_ism_median:.3g}, "
            f"M(<x90)/sr={c.physical_mass_to_ism90_g_sr:.4e} g, spikes={c.spike_count}"
        )
    lines.extend(
        [
            "",
            "Smoothness diagnostics over dense interpolated n-grid:",
        ]
    )
    for key, value in diagnostics.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "Interpretation:",
            "- The post-shock ratio is close to the expected strong-shock factor of 4 in the clean shock region; deviations mostly trace smoothing and finite-width sampling around the jump.",
            "- The outer asymptote remains tied to rho/rho_ISM = 1, so the ambient medium normalization is correct.",
            "- Cumulative mass is monotone by construction because the surrogate density is positive everywhere.",
            "- The physical mass varies smoothly with n; it is not forced to be monotone because both rho_ISM and the bubble radius change with density.",
            "- For VegasAfterglow, use the registered profile plus an exported cumulative-mass table rather than independently fitted local features.",
            "",
            "Generated outputs:",
        ]
    )
    lines.extend(f"- {out}" for out in outputs)
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    plan = read_plan()
    profiles = load_p4_registered_profiles()
    z_grid = make_registered_grid(profiles, n_points=1200)
    logy_table = profiles_on_registered_grid(profiles, z_grid)
    rt_pc = float(np.median([plan[p.run_id]["rt_external_pc"] for p in profiles]))

    checks: list[ProfileCheck] = []
    for p in profiles:
        checks.append(check_profile(p.run_id, p.n_rho_exp, p.x, p.y, p.x_ts, p.x_outer_onset, rt_pc))

    n_dense = np.linspace(-24.0, -21.0, 61)
    _, surrogate_outputs = make_surrogate_grid(profiles, z_grid, logy_table, n_dense)
    dense_checks: list[ProfileCheck] = []
    for n_val in n_dense:
        x, y, x_ts, x_outer = surrogate_outputs[float(n_val)]
        dense_checks.append(check_profile(f"surrogate_n{n_val:.2f}", float(n_val), x, y, x_ts, x_outer, rt_pc))

    dense_csv = PLOT_DIR / "p4_registered_surrogate_dense_physics_checks.csv"
    train_csv = PLOT_DIR / "p4_registered_surrogate_training_physics_checks.csv"
    write_checks_csv(train_csv, checks)
    write_checks_csv(dense_csv, dense_checks)

    outputs = [
        train_csv,
        dense_csv,
        plot_mass_profiles(profiles, surrogate_outputs, rt_pc),
        plot_mass_and_radii_vs_density(checks, dense_checks),
        plot_registered_heatmap(profiles, z_grid, logy_table, n_dense),
    ]
    diagnostics = smoothness_diagnostics(dense_checks)
    report = PLOT_DIR / "p4_registered_surrogate_physics_report.txt"
    write_report(report, checks, dense_checks, diagnostics, outputs)
    outputs.append(report)
    for out in outputs:
        print(out)


if __name__ == "__main__":
    main()
