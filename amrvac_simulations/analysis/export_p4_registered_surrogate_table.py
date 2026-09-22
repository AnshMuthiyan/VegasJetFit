#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np

from check_p4_registered_surrogate_physics import (
    check_profile,
    dimensionless_cumulative_mass,
    find_x_ism90,
    interpolate_anchor,
)
from evaluate_p4_registered_profile_interpolator import (
    interpolate_registered_profile,
    load_p4_registered_profiles,
    make_registered_grid,
    profiles_on_registered_grid,
)
from plot_tight_density_profiles import PC_CM, read_plan

CAMPAIGN = Path(__file__).resolve().parent
PLOT_DIR = CAMPAIGN / "plots"
PLOT_DIR.mkdir(exist_ok=True)


def main() -> None:
    plan = read_plan()
    profiles = load_p4_registered_profiles()
    z_grid = make_registered_grid(profiles, n_points=1200)
    logy_table = profiles_on_registered_grid(profiles, z_grid)
    rt_pc = float(np.median([plan[p.run_id]["rt_external_pc"] for p in profiles]))

    n_train = np.asarray([p.n_rho_exp for p in profiles], dtype=float)
    x_ts_train = np.asarray([p.x_ts for p in profiles], dtype=float)
    x_outer_train = np.asarray([p.x_outer_onset for p in profiles], dtype=float)

    log_x_min = min(float(np.min(np.log10(p.x))) for p in profiles)
    log_x_max = max(float(np.max(np.log10(p.x))) for p in profiles)
    x_grid = 10.0 ** np.linspace(log_x_min, log_x_max, 1800)
    n_dense = np.linspace(float(np.min(n_train)), float(np.max(n_train)), 121)

    log10_y_dense = np.zeros((len(n_dense), len(x_grid)), dtype=float)
    dimensionless_cum_mass_dense = np.zeros_like(log10_y_dense)
    physical_cum_mass_dense_g_sr = np.zeros_like(log10_y_dense)
    x_ts_dense = np.zeros(len(n_dense), dtype=float)
    x_outer_onset_dense = np.zeros(len(n_dense), dtype=float)
    x_ism90_dense = np.zeros(len(n_dense), dtype=float)
    mass_to_ism90_g_sr = np.zeros(len(n_dense), dtype=float)

    for i, n_val in enumerate(n_dense):
        y = interpolate_registered_profile(
            float(n_val), x_grid, profiles, z_grid, logy_table, exact_training_passthrough=False
        )
        x_ts = interpolate_anchor(float(n_val), profiles, "x_ts")
        x_outer = interpolate_anchor(float(n_val), profiles, "x_outer_onset")
        x_ism90 = find_x_ism90(x_grid, y, x_outer)
        cum = dimensionless_cumulative_mass(x_grid, y)
        rho_ism = 10.0 ** float(n_val)
        physical_cum = cum * rho_ism * (rt_pc * PC_CM) ** 3

        log10_y_dense[i, :] = np.log10(np.maximum(y, 1e-300))
        dimensionless_cum_mass_dense[i, :] = cum
        physical_cum_mass_dense_g_sr[i, :] = physical_cum
        x_ts_dense[i] = x_ts
        x_outer_onset_dense[i] = x_outer
        x_ism90_dense[i] = x_ism90
        mass_to_ism90_g_sr[i] = np.interp(x_ism90, x_grid, physical_cum) if np.isfinite(x_ism90) else np.nan

    out_npz = PLOT_DIR / "p4_registered_surrogate_table.npz"
    np.savez_compressed(
        out_npz,
        pressure_exponent=np.asarray([4.0]),
        rt_pc=np.asarray([rt_pc]),
        n_train=n_train,
        z_grid=z_grid,
        log10_y_registered_train=logy_table,
        x_ts_train=x_ts_train,
        x_outer_onset_train=x_outer_train,
        n_dense=n_dense,
        x_grid=x_grid,
        log10_y_dense=log10_y_dense,
        dimensionless_cum_mass_dense=dimensionless_cum_mass_dense,
        physical_cum_mass_dense_g_sr=physical_cum_mass_dense_g_sr,
        x_ts_dense=x_ts_dense,
        x_outer_onset_dense=x_outer_onset_dense,
        x_ism90_dense=x_ism90_dense,
        mass_to_ism90_g_sr=mass_to_ism90_g_sr,
    )

    summary = PLOT_DIR / "p4_registered_surrogate_table_summary.csv"
    with summary.open("w") as fh:
        fh.write("n_rho_exp,x_ts,x_outer_onset,x_ism90,mass_to_ism90_g_sr\n")
        for vals in zip(n_dense, x_ts_dense, x_outer_onset_dense, x_ism90_dense, mass_to_ism90_g_sr):
            fh.write(",".join(f"{v:.16e}" for v in vals) + "\n")

    readme = PLOT_DIR / "p4_registered_surrogate_table_readme.txt"
    readme.write_text(
        "\n".join(
            [
                "p4 registered empirical-bubble surrogate export",
                "",
                "This table is the current p4 pressure-slice target for a future VegasAfterglow implementation.",
                "",
                "Coordinates:",
                "  n = log10(rho_ISM / g cm^-3)",
                "  x = r/R_t",
                "  y = rho/rho_ISM",
                "  z = [log10(x) - log10(x_ts)] / [log10(x_outer_onset) - log10(x_ts)]",
                "",
                "Mass:",
                "  dimensionless_cum_mass = integral y x^2 dx",
                "  physical_cum_mass_g_sr = rho_ISM * R_t^3 * dimensionless_cum_mass",
                "",
                "Use log10_y_registered_train with n_train/z_grid for the native registered model.",
                "Use log10_y_dense and cumulative-mass arrays as regression-test products.",
                "Do not use the older 7-feature p4_n22 template warp as the production generator.",
            ]
        )
        + "\n"
    )

    # Smoke-check a representative dense profile before declaring success.
    mid = len(n_dense) // 2
    check = check_profile(
        f"export_smoke_n{n_dense[mid]:.3f}",
        float(n_dense[mid]),
        x_grid,
        10.0 ** log10_y_dense[mid],
        float(x_ts_dense[mid]),
        float(x_outer_onset_dense[mid]),
        rt_pc,
    )
    if not check.cumulative_mass_monotone or check.spike_count != 0:
        raise RuntimeError("export smoke check failed")

    for out in [out_npz, summary, readme]:
        print(out)


if __name__ == "__main__":
    main()
