#!/usr/bin/env python3
"""
Compute integrated BoOST Weaver-style bubble radii and compare to existing
pressure-grid proxy radii.

This uses the actual time-dependent BoOST wind history:

  L_w(t) = 0.5 Mdot(t) v_w(t)^2
  E_w(t) = integral L_w(t) dt

For the outer bubble radius we use the constant-luminosity Weaver normalization
with an energy-averaged luminosity, L_eff=E_w/t:

  R_b = beta (L_eff / rho_ism)^(1/5) t^(3/5)

where beta=(250/(308*pi))^(1/5).  This is equivalent to
R_b = beta (E_w t^2 / rho_ism)^(1/5), and preserves the standard Weaver
solution for constant L_w.

For the energy-driven termination shock radius, we estimate the shocked-bubble
pressure from the retained hot-bubble energy, E_th ~= (5/11) E_w, and set wind
ram pressure equal to the bubble pressure:

  P_b = (gamma-1) E_th / (4*pi R_b^3 / 3)
  R_t = sqrt(Mdot(t) v_w(t) / (4*pi P_b)).

We also compute a pressure-confined late-time solution.  In that regime the
outer radius is the radius at which the retained hot-bubble energy would have
pressure P_ext, and the termination shock is set directly by P_ext:

  R_b,eq = [3 (gamma-1) E_th / (4*pi P_ext)]^(1/3)
  R_t,ext = sqrt(Mdot(t) v_w(t) / (4*pi P_ext)).

The pressure-limited effective outer radius is min(R_b,Weaver, R_b,eq).
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


MSUN_G = 1.98847e33
YEAR_S = 365.25 * 86400.0
PC_CM = 3.085677581491367e18
KB_CGS = 1.380649e-16
BETA_WEAVER = (250.0 / (308.0 * np.pi)) ** 0.2
GAMMA = 5.0 / 3.0
THERMAL_ENERGY_FRACTION = 5.0 / 11.0
TINY = 1e-300


@dataclass(frozen=True)
class WindHistory:
    age_yr: np.ndarray
    mdot_msun_yr: np.ndarray
    vwind_km_s: np.ndarray
    twind_k: np.ndarray
    lw_erg_s: np.ndarray
    ew_erg: np.ndarray


def read_wind_history(path: Path) -> WindHistory:
    rows = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        age_yr, log_mdot, vwind_km_s, twind_k = map(float, stripped.split()[:4])
        rows.append((age_yr, 10.0**log_mdot, vwind_km_s, twind_k))
    if len(rows) < 2:
        raise ValueError(f"Need at least two wind-history rows in {path}")

    data = np.asarray(rows, dtype=float)
    order = np.argsort(data[:, 0], kind="stable")
    data = data[order]

    # The BoOST export can contain repeated ages near rapid phases.  Keep the
    # last entry for each repeated age to avoid zero-width integration intervals.
    unique_age, unique_indices = np.unique(data[:, 0], return_index=True)
    last_indices = []
    for age in unique_age:
        matches = np.where(data[:, 0] == age)[0]
        last_indices.append(matches[-1])
    data = data[np.asarray(last_indices, dtype=int)]

    age_yr = data[:, 0]
    mdot_msun_yr = data[:, 1]
    vwind_km_s = data[:, 2]
    twind_k = data[:, 3]

    mdot_g_s = mdot_msun_yr * MSUN_G / YEAR_S
    vwind_cm_s = vwind_km_s * 1.0e5
    lw_erg_s = 0.5 * mdot_g_s * vwind_cm_s**2

    ew_erg = np.zeros_like(age_yr)
    dt_s = np.diff(age_yr) * YEAR_S
    trapezoids = 0.5 * (lw_erg_s[:-1] + lw_erg_s[1:]) * dt_s
    ew_erg[1:] = np.cumsum(trapezoids)

    return WindHistory(age_yr, mdot_msun_yr, vwind_km_s, twind_k, lw_erg_s, ew_erg)


def read_pressure_plan(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def interp_wind(history: WindHistory, age_yr: float) -> dict[str, float]:
    age = float(np.clip(age_yr, history.age_yr[0], history.age_yr[-1]))
    return {
        "age_yr": age,
        "mdot_msun_yr": float(np.interp(age, history.age_yr, history.mdot_msun_yr)),
        "vwind_km_s": float(np.interp(age, history.age_yr, history.vwind_km_s)),
        "lw_erg_s": float(np.interp(age, history.age_yr, history.lw_erg_s)),
        "ew_erg": float(np.interp(age, history.age_yr, history.ew_erg)),
    }


def radii_for_environment(
    history: WindHistory,
    rho_ism_g_cm3: float,
    pressure_over_k_k_cm3: float,
    age_yr: float,
) -> dict[str, float]:
    wind = interp_wind(history, age_yr)
    age_s = max(wind["age_yr"] * YEAR_S, TINY)
    ew_erg = max(wind["ew_erg"], TINY)
    rb_cm = BETA_WEAVER * (ew_erg * age_s**2 / max(rho_ism_g_cm3, TINY)) ** 0.2

    e_th = THERMAL_ENERGY_FRACTION * ew_erg
    volume_cm3 = 4.0 * np.pi * rb_cm**3 / 3.0
    p_b_dyn_cm2 = (GAMMA - 1.0) * e_th / max(volume_cm3, TINY)
    p_ext_dyn_cm2 = max(pressure_over_k_k_cm3 * KB_CGS, TINY)

    mdot_g_s = wind["mdot_msun_yr"] * MSUN_G / YEAR_S
    vwind_cm_s = wind["vwind_km_s"] * 1.0e5
    rt_cm = np.sqrt(max(mdot_g_s * vwind_cm_s, TINY) / max(4.0 * np.pi * p_b_dyn_cm2, TINY))
    rt_ext_cm = np.sqrt(max(mdot_g_s * vwind_cm_s, TINY) / max(4.0 * np.pi * p_ext_dyn_cm2, TINY))
    rb_pressure_eq_cm = (
        3.0 * (GAMMA - 1.0) * e_th / max(4.0 * np.pi * p_ext_dyn_cm2, TINY)
    ) ** (1.0 / 3.0)
    rb_effective_cm = min(rb_cm, rb_pressure_eq_cm)

    return {
        **wind,
        "rho_ism_g_cm3": rho_ism_g_cm3,
        "pressure_over_k_k_cm3": pressure_over_k_k_cm3,
        "rb_weaver_pc": rb_cm / PC_CM,
        "rt_weaver_pc": rt_cm / PC_CM,
        "rt_external_pressure_pc": rt_ext_cm / PC_CM,
        "rb_pressure_equilibrium_pc": rb_pressure_eq_cm / PC_CM,
        "rb_effective_pc": rb_effective_cm / PC_CM,
        "bubble_pressure_dyn_cm2": p_b_dyn_cm2,
        "external_pressure_dyn_cm2": p_ext_dyn_cm2,
        "bubble_pressure_over_k_k_cm3": p_b_dyn_cm2 / KB_CGS,
        "pressure_ratio_bubble_to_external": p_b_dyn_cm2 / p_ext_dyn_cm2,
        "pressure_confined": rb_pressure_eq_cm < rb_cm,
    }


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_wind_history(history: WindHistory, output_path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    axes[0].loglog(history.age_yr, history.mdot_msun_yr)
    axes[0].set_ylabel(r"$\dot{M}$ [$M_\odot$ yr$^{-1}$]")
    axes[1].semilogx(history.age_yr, history.vwind_km_s)
    axes[1].set_ylabel(r"$v_w$ [km s$^{-1}$]")
    axes[2].loglog(history.age_yr, history.lw_erg_s, label=r"$L_w$")
    axes[2].loglog(history.age_yr, np.maximum(history.ew_erg / np.maximum(history.age_yr * YEAR_S, TINY), TINY), label=r"$E_w/t$")
    axes[2].set_ylabel(r"Power [erg s$^{-1}$]")
    axes[2].set_xlabel("Age [yr]")
    axes[2].legend()
    fig.suptitle("BoOST Wind History Used for Integrated Weaver Estimate")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_radius_evolution(history: WindHistory, rho_values: list[float], pressure_over_k: float, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    ages = history.age_yr[1:]
    for rho in rho_values:
        rb = []
        rt = []
        rb_eff = []
        for age in ages:
            radii = radii_for_environment(history, rho, pressure_over_k, float(age))
            rb.append(radii["rb_weaver_pc"])
            rt.append(radii["rt_weaver_pc"])
            rb_eff.append(radii["rb_effective_pc"])
        label = rf"$\rho=10^{{{np.log10(rho):.0f}}}$ g cm$^{{-3}}$"
        axes[0].loglog(ages, rb, label=label)
        axes[0].loglog(ages, rb_eff, ls="--", alpha=0.65)
        axes[1].loglog(ages, rt, label=label)
    axes[0].set_ylabel(r"$R_b$ [pc]")
    axes[0].set_title(r"Integrated BoOST Outer Radius; dashed is pressure-limited at $P/k=10^6$")
    axes[1].set_ylabel(r"$R_t$ [pc]")
    axes[1].set_xlabel("Age [yr]")
    axes[1].set_title("Termination Shock from Integrated Bubble Pressure")
    axes[0].legend(fontsize=8)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_plan_comparison(rows: list[dict[str, object]], output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    pressures = sorted({int(row["pressure_exponent"]) for row in rows})
    markers = {4: "o", 5: "s", 6: "^", 7: "D", 8: "P"}
    for pexp in pressures:
        subset = [row for row in rows if int(row["pressure_exponent"]) == pexp]
        subset.sort(key=lambda row: int(row["density_exponent"]))
        dens = [int(row["density_exponent"]) for row in subset]
        rb = [float(row["rb_weaver_pc"]) for row in subset]
        rb_eff = [float(row["rb_effective_pc"]) for row in subset]
        proxy = [float(row["proxy_outer_radius_pc"]) for row in subset]
        rt_ext = [float(row["rt_external_pressure_pc"]) for row in subset]
        axes[0].semilogy(dens, rb, marker=markers.get(pexp, "o"), lw=1.8, label=f"Weaver P=1e{pexp}")
        axes[0].semilogy(dens, rb_eff, marker=markers.get(pexp, "o"), ls=":", lw=1.8, label=f"pressure-limited P=1e{pexp}")
        axes[0].semilogy(dens, proxy, marker=markers.get(pexp, "o"), ls="--", lw=1.2, alpha=0.75, label=f"proxy P=1e{pexp}")
        axes[1].semilogy(dens, rt_ext, marker=markers.get(pexp, "o"), lw=1.8, label=f"external P=1e{pexp}")
    axes[0].invert_xaxis()
    axes[1].invert_xaxis()
    axes[0].set_xlabel(r"Density exponent $N$ in $\rho_{\rm ISM}=10^{-N}$")
    axes[1].set_xlabel(r"Density exponent $N$ in $\rho_{\rm ISM}=10^{-N}$")
    axes[0].set_ylabel("Outer radius [pc]")
    axes[1].set_ylabel(r"$R_t$ [pc]")
    axes[0].set_title(r"Integrated $R_b$ vs existing proxy")
    axes[1].set_title(r"Death-time termination shock from external pressure")
    axes[0].legend(fontsize=6, ncol=2)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_ratio(rows: list[dict[str, object]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    pressures = sorted({int(row["pressure_exponent"]) for row in rows})
    markers = {4: "o", 5: "s", 6: "^", 7: "D", 8: "P"}
    for pexp in pressures:
        subset = [row for row in rows if int(row["pressure_exponent"]) == pexp]
        subset.sort(key=lambda row: int(row["density_exponent"]))
        dens = [int(row["density_exponent"]) for row in subset]
        ratio = [float(row["rb_effective_pc"]) / float(row["proxy_outer_radius_pc"]) for row in subset]
        ax.semilogy(dens, ratio, marker=markers.get(pexp, "o"), lw=1.8, label=f"P/k=1e{pexp}")
    ax.axhline(1.0, color="0.25", ls="--", lw=1.0)
    ax.invert_xaxis()
    ax.set_xlabel(r"Density exponent $N$ in $\rho_{\rm ISM}=10^{-N}$")
    ax.set_ylabel(r"$R_{b,\rm effective}/R_{b,\rm proxy}$")
    ax.set_title("Pressure-Limited BoOST Radius Relative to Existing Proxy")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_regime_comparison(rows: list[dict[str, object]], output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    pressures = sorted({int(row["pressure_exponent"]) for row in rows})
    markers = {4: "o", 5: "s", 6: "^", 7: "D", 8: "P"}
    for pexp in pressures:
        subset = [row for row in rows if int(row["pressure_exponent"]) == pexp]
        subset.sort(key=lambda row: int(row["density_exponent"]))
        dens = [int(row["density_exponent"]) for row in subset]
        p_ratio = [float(row["pressure_ratio_bubble_to_external"]) for row in subset]
        rt_ratio = [float(row["rt_external_pressure_pc"]) / float(row["rt_weaver_pc"]) for row in subset]
        axes[0].semilogy(dens, p_ratio, marker=markers.get(pexp, "o"), lw=1.8, label=f"P/k=1e{pexp}")
        axes[1].semilogy(dens, rt_ratio, marker=markers.get(pexp, "o"), lw=1.8, label=f"P/k=1e{pexp}")
    for ax in axes:
        ax.invert_xaxis()
        ax.axhline(1.0, color="0.25", ls="--", lw=1.0)
        ax.set_xlabel(r"Density exponent $N$ in $\rho_{\rm ISM}=10^{-N}$")
        ax.legend(fontsize=8)
    axes[0].set_ylabel(r"$P_{b,\rm Weaver}/P_{\rm ext}$")
    axes[0].set_title("Regime Diagnostic at Stellar Death")
    axes[1].set_ylabel(r"$R_{t,\rm ext}/R_{t,\rm Weaver}$")
    axes[1].set_title("Termination Shock Shift from External Pressure")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign-dir",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_24_pressure_grid_p4p5p6_boxfactor30_cells6_test",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_pressure_grid_prelim_20260424",
    )
    parser.add_argument(
        "--age-yr",
        type=float,
        default=None,
        help="Age at which to compare radii. Defaults to the last BoOST age.",
    )
    args = parser.parse_args()

    campaign_dir = Path(args.campaign_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    history = read_wind_history(campaign_dir / "stellar_evolution.dat")
    age_yr = float(args.age_yr) if args.age_yr is not None else float(history.age_yr[-1])
    plan = read_pressure_plan(campaign_dir / "pressure_box_plan.csv")

    rows: list[dict[str, object]] = []
    for row in plan:
        radii = radii_for_environment(
            history,
            float(row["rho_g_cm3"]),
            float(row["pressure_k_cm3"]),
            age_yr,
        )
        rows.append(
            {
                "run_id": row["run_id"],
                "pressure_exponent": int(row["pressure_exponent"]),
                "density_exponent": int(row["density_exponent"]),
                "pressure_k_cm3": float(row["pressure_k_cm3"]),
                "rho_g_cm3": float(row["rho_g_cm3"]),
                "nism_cm3": float(row["nism_cm3"]),
                "tism_k": float(row["tism_k"]),
                "age_yr": age_yr,
                "mdot_msun_yr": radii["mdot_msun_yr"],
                "vwind_km_s": radii["vwind_km_s"],
                "lw_erg_s": radii["lw_erg_s"],
                "ew_erg": radii["ew_erg"],
                "bubble_pressure_over_k_k_cm3": radii["bubble_pressure_over_k_k_cm3"],
                "external_pressure_over_k_k_cm3": radii["pressure_over_k_k_cm3"],
                "pressure_ratio_bubble_to_external": radii["pressure_ratio_bubble_to_external"],
                "rt_weaver_pc": radii["rt_weaver_pc"],
                "rt_external_pressure_pc": radii["rt_external_pressure_pc"],
                "rb_weaver_pc": radii["rb_weaver_pc"],
                "rb_pressure_equilibrium_pc": radii["rb_pressure_equilibrium_pc"],
                "rb_effective_pc": radii["rb_effective_pc"],
                "pressure_confined": radii["pressure_confined"],
                "proxy_outer_radius_pc": float(row["outer_radius_pc"]),
                "old_density_proxy_radius_pc": float(row["old_predicted_outer_radius_pc"]),
                "rb_weaver_over_proxy": radii["rb_weaver_pc"] / float(row["outer_radius_pc"]),
                "rb_effective_over_proxy": radii["rb_effective_pc"] / float(row["outer_radius_pc"]),
                "rt_over_rb": radii["rt_weaver_pc"] / radii["rb_weaver_pc"],
                "rt_external_over_rb_effective": radii["rt_external_pressure_pc"] / radii["rb_effective_pc"],
            }
        )

    write_csv(rows, output_dir / "boost_integrated_weaver_radii.csv")
    plot_wind_history(history, output_dir / "boost_wind_history.png")
    rho_values = sorted({float(row["rho_g_cm3"]) for row in plan})
    plot_radius_evolution(history, rho_values, 1.0e6, output_dir / "boost_integrated_weaver_radius_evolution.png")
    plot_plan_comparison(rows, output_dir / "boost_integrated_weaver_vs_proxy.png")
    plot_ratio(rows, output_dir / "boost_integrated_weaver_proxy_ratio.png")
    plot_regime_comparison(rows, output_dir / "boost_integrated_weaver_regime_diagnostic.png")

    print(f"Wrote integrated BoOST Weaver comparison to {output_dir}")
    print(f"Comparison age: {age_yr:.6g} yr")


if __name__ == "__main__":
    main()
