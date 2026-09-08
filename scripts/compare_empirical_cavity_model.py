#!/usr/bin/env python3
"""
Compare the original simple bubble model to an empirical shocked-cavity model.

The empirical model keeps the same physical GRB-facing parameters:
  - r_t: termination-shock radius
  - n_t: density just inside the termination shock
  - n_ism: outer ISM density

It then replaces the constant-density intershock region with

  n(r) = 4 n_t (r / r_t)^(-s),   r_t <= r < R_2

where:
  - the factor of 4 is fixed by the strong-shock jump condition
  - R_2 is anchored to the observed outer rise in the AMRVAC profile
  - s is fit from the AMRVAC cavity structure
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

from analyze_amrvac_bubble_profiles import (
    M_P,
    MU,
    PC_TO_CM,
    TINY,
    bubble_shell_radius,
    bubble_number_density,
    read_vtu_snapshot,
)


def infer_nism_from_run_name(run_name: str) -> float:
    match = re.search(r"density_(\d+)", run_name)
    if not match:
        raise ValueError(f"Could not infer rhoISM exponent from run name: {run_name}")
    exponent = int(match.group(1))
    rho_ism = 10.0 ** (-exponent)
    return rho_ism / (MU * M_P)


def find_profile_rises(radius_pc: np.ndarray, number_density_cm3: np.ndarray) -> tuple[float, float]:
    logr = np.log10(radius_pc)
    logn = np.log10(np.maximum(number_density_cm3, TINY))
    slope = np.gradient(logn, logr)

    # The last few points often contain a boundary spike.
    radius_use = radius_pc[:-3]
    slope_use = slope[:-3]

    first_mask = radius_use < 1.2
    second_mask = radius_use > 1.2
    if not np.any(first_mask) or not np.any(second_mask):
        raise ValueError("Could not identify both rises in the profile.")

    first_idx = np.where(first_mask)[0][np.argmax(slope_use[first_mask])]
    second_idx = np.where(second_mask)[0][np.argmax(slope_use[second_mask])]
    return float(radius_use[first_idx]), float(radius_use[second_idx])


def infer_nt_from_inner_wind(radius_cm: np.ndarray, radius_pc: np.ndarray, number_density_cm3: np.ndarray, rt_pc: float) -> float:
    inner_mask = radius_pc < rt_pc * 0.95
    if np.any(inner_mask):
        wind_norm = np.median(number_density_cm3[inner_mask] * (radius_cm[inner_mask] ** 2))
    else:
        wind_norm = np.median(number_density_cm3 * (radius_cm ** 2))
    rt_cm = rt_pc * PC_TO_CM
    return float(max(wind_norm / (rt_cm**2), 1e-12))


def empirical_cavity_profile(
    radius_cm: np.ndarray,
    rt_pc: float,
    nt_cm3: float,
    nism_cm3: float,
    outer_rise_pc: float,
    slope_s: float,
) -> np.ndarray:
    rt_cm = rt_pc * PC_TO_CM
    x = np.maximum(radius_cm / rt_cm, 1e-30)
    b_ratio = outer_rise_pc / rt_pc
    return np.where(
        x < 1.0,
        nt_cm3 * x**-2.0,
        np.where(x < b_ratio, 4.0 * nt_cm3 * x**(-slope_s), nism_cm3),
    )


def fit_empirical_cavity_slope(
    radius_cm: np.ndarray,
    number_density_cm3: np.ndarray,
    rt_pc: float,
    nt_cm3: float,
    nism_cm3: float,
    outer_rise_pc: float,
) -> tuple[float, float]:
    def residual(log_s: np.ndarray) -> np.ndarray:
        slope_s = 10.0 ** log_s[0]
        model = empirical_cavity_profile(radius_cm, rt_pc, nt_cm3, nism_cm3, outer_rise_pc, slope_s)
        return np.log10(np.maximum(model, TINY)) - np.log10(number_density_cm3)

    result = least_squares(
        residual,
        x0=[np.log10(4.0)],
        bounds=([np.log10(0.1)], [np.log10(10.0)]),
        loss="soft_l1",
        f_scale=0.1,
        max_nfev=3000,
    )
    slope_s = float(10.0 ** result.x[0])
    rms_dex = float(np.sqrt(np.mean(residual(result.x) ** 2)))
    return slope_s, rms_dex


def intershock_mass_ratio(outer_ratio: float, slope_s: float) -> float:
    """
    Intershock mass in units of 4*pi*n_t*r_t^3.
    """
    if abs(slope_s - 3.0) < 1e-8:
        return float(4.0 * np.log(outer_ratio))
    return float(4.0 * (outer_ratio ** (3.0 - slope_s) - 1.0) / (3.0 - slope_s))


def outer_ratio_from_mass_ratio(target_mass_ratio: float, slope_s: float) -> float:
    """Solve for B = R2 / rt given a target intershock mass ratio."""
    if target_mass_ratio <= 0.0:
        return 1.0 + 1e-9
    if abs(slope_s - 3.0) < 1e-8:
        return float(np.exp(target_mass_ratio / 4.0))
    exponent = 3.0 - slope_s
    base = 1.0 + target_mass_ratio * exponent / 4.0
    if base <= 1.0:
        return 1.0 + 1e-9
    return float(base ** (1.0 / exponent))


def fit_mass_scaled_cavity(
    radius_cm: np.ndarray,
    number_density_cm3: np.ndarray,
    rt_pc: float,
    nt_cm3: float,
    nism_cm3: float,
    simple_mass_ratio: float,
    initial_s: float,
    initial_f_mass: float,
) -> tuple[float, float, float, float]:
    """
    Fit a declining intershock cavity while preserving the simple-bubble mass
    structure up to a scalar mass factor f_mass.

    Returns:
      slope_s, f_mass, outer_ratio, rms_dex
    """

    def residual(params: np.ndarray) -> np.ndarray:
        slope_s = 10.0 ** params[0]
        f_mass = 10.0 ** params[1]
        outer_ratio = outer_ratio_from_mass_ratio(f_mass * simple_mass_ratio, slope_s)
        model = empirical_cavity_profile(
            radius_cm=radius_cm,
            rt_pc=rt_pc,
            nt_cm3=nt_cm3,
            nism_cm3=nism_cm3,
            outer_rise_pc=rt_pc * outer_ratio,
            slope_s=slope_s,
        )
        return np.log10(np.maximum(model, TINY)) - np.log10(number_density_cm3)

    initial_s = float(np.clip(initial_s, 0.1, 2.99))
    initial_f_mass = float(np.clip(initial_f_mass, 1e-4, 10.0))
    result = least_squares(
        residual,
        x0=[np.log10(initial_s), np.log10(initial_f_mass)],
        bounds=([np.log10(0.1), np.log10(1e-4)], [np.log10(2.99), np.log10(10.0)]),
        loss="linear",
        max_nfev=6000,
    )
    slope_s = float(10.0 ** result.x[0])
    f_mass = float(10.0 ** result.x[1])
    outer_ratio = outer_ratio_from_mass_ratio(f_mass * simple_mass_ratio, slope_s)
    rms_dex = float(np.sqrt(np.mean(residual(result.x) ** 2)))
    return slope_s, f_mass, outer_ratio, rms_dex


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vtu",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2025_08_07/density_21/output/Ostar_1D/test0010.vtu",
        help="AMRVAC VTU file to compare.",
    )
    parser.add_argument(
        "--output",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate/density_21_empirical_cavity_compare.png",
        help="Output plot path.",
    )
    args = parser.parse_args()

    vtu_path = Path(args.vtu)
    run_name = vtu_path.parents[2].name
    snapshot = read_vtu_snapshot(vtu_path)

    radius_cm = snapshot.radius_cm
    number_density_cm3 = np.maximum(snapshot.number_density_cm3, TINY)
    radius_pc = radius_cm / PC_TO_CM

    first_rise_pc, second_rise_pc = find_profile_rises(radius_pc, number_density_cm3)
    nt_cm3 = infer_nt_from_inner_wind(radius_cm, radius_pc, number_density_cm3, first_rise_pc)
    nism_cm3 = infer_nism_from_run_name(run_name)

    old_simple = bubble_number_density(
        radius_cm,
        first_rise_pc * PC_TO_CM,
        nt_cm3,
        nism_cm3,
    )
    old_rms = float(np.sqrt(np.mean((np.log10(np.maximum(old_simple, TINY)) - np.log10(number_density_cm3)) ** 2)))
    _, old_r2_cm = bubble_shell_radius(first_rise_pc * PC_TO_CM, nt_cm3, nism_cm3)
    old_outer_ratio = old_r2_cm / (first_rise_pc * PC_TO_CM)
    old_mass_ratio = intershock_mass_ratio(old_outer_ratio, 0.0)

    slope_s, empirical_rms = fit_empirical_cavity_slope(
        radius_cm,
        number_density_cm3,
        first_rise_pc,
        nt_cm3,
        nism_cm3,
        second_rise_pc,
    )
    empirical = empirical_cavity_profile(
        radius_cm,
        first_rise_pc,
        nt_cm3,
        nism_cm3,
        second_rise_pc,
        slope_s,
    )

    outer_ratio = second_rise_pc / first_rise_pc
    mass_ratio = intershock_mass_ratio(outer_ratio, slope_s)
    empirical_f_mass = mass_ratio / old_mass_ratio

    massfit_s, massfit_f, massfit_outer_ratio, massfit_rms = fit_mass_scaled_cavity(
        radius_cm=radius_cm,
        number_density_cm3=number_density_cm3,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        simple_mass_ratio=old_mass_ratio,
        initial_s=slope_s,
        initial_f_mass=empirical_f_mass,
    )
    massfit = empirical_cavity_profile(
        radius_cm=radius_cm,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        outer_rise_pc=first_rise_pc * massfit_outer_ratio,
        slope_s=massfit_s,
    )

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(8.2, 8.8),
        dpi=220,
        sharex=True,
        height_ratios=[3, 1],
    )

    ax1.loglog(radius_pc, number_density_cm3, lw=2.2, label=f"{run_name} AMRVAC")
    ax1.loglog(radius_pc, old_simple, "--", lw=1.9, label="original simple bubble")
    ax1.loglog(radius_pc, empirical, ":", lw=2.5, label="empirical cavity model")
    ax1.loglog(radius_pc, massfit, "-.", lw=2.0, label="mass-scaled cavity fit")
    ax1.axvline(first_rise_pc, color="0.35", ls=":", lw=1.0, label=fr"first rise = {first_rise_pc:.3f} pc")
    ax1.axvline(second_rise_pc, color="0.55", ls="--", lw=1.0, label=fr"second rise = {second_rise_pc:.3f} pc")
    ax1.set_ylabel(r"n(r) [cm$^{-3}$]")
    ax1.set_title(f"{run_name}: empirical cavity model vs simple bubble")
    ax1.set_xlim(0.12, float(radius_pc.max()) * 1.22)
    ax1.grid(True, which="both", alpha=0.25)
    ax1.legend(fontsize=8, ncol=2)

    ax2.loglog(radius_pc, empirical / number_density_cm3, lw=1.8, color="C2", label="empirical/data")
    ax2.loglog(radius_pc, massfit / number_density_cm3, lw=1.8, color="C3", label="mass-scaled/data")
    ax2.loglog(radius_pc, old_simple / number_density_cm3, lw=1.5, color="C1", alpha=0.85, label="simple/data")
    ax2.axhline(1.0, color="0.4", ls="--", lw=1.0)
    ax2.set_xlabel("Radius (pc)")
    ax2.set_ylabel("fit/data")
    ax2.set_xlim(0.12, float(radius_pc.max()) * 1.22)
    ax2.grid(True, which="both", alpha=0.25)
    ax2.legend(fontsize=8)

    text = "\n".join(
        [
            fr"fixed $n_{{ism}}$ = {nism_cm3:.1f} cm$^{{-3}}$",
            fr"$r_t$ = {first_rise_pc:.3f} pc, $n_t$ = {nt_cm3:.3f} cm$^{{-3}}$",
            fr"empirical: $R_2/r_t$ = {outer_ratio:.3f}, $s$ = {slope_s:.3f}, RMS = {empirical_rms:.3f} dex",
            fr"mass-scaled: $f_M$ = {massfit_f:.4f}, $R_2/r_t$ = {massfit_outer_ratio:.3f}, $s$ = {massfit_s:.3f}, RMS = {massfit_rms:.3f} dex",
            fr"simple: RMS = {old_rms:.3f} dex",
            fr"empirical intershock mass / (4 pi n_t r_t^3) = {mass_ratio:.3f}",
            fr"simple intershock mass / (4 pi n_t r_t^3) = {old_mass_ratio:.3f}",
        ]
    )
    ax1.text(
        0.03,
        0.03,
        text,
        transform=ax1.transAxes,
        fontsize=8.4,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.88, edgecolor="0.7"),
    )

    fig.tight_layout()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")

    print(output_path)
    print(f"first_rise_pc={first_rise_pc:.6f}")
    print(f"second_rise_pc={second_rise_pc:.6f}")
    print(f"nt_cm3={nt_cm3:.6f}")
    print(f"nism_cm3={nism_cm3:.6f}")
    print(f"empirical_s={slope_s:.6f}")
    print(f"empirical_B={outer_ratio:.6f}")
    print(f"empirical_rms={empirical_rms:.6f}")
    print(f"simple_rms={old_rms:.6f}")
    print(f"intershock_mass_ratio={mass_ratio:.6f}")
    print(f"simple_intershock_mass_ratio={old_mass_ratio:.6f}")
    print(f"massfit_s={massfit_s:.6f}")
    print(f"massfit_f_mass={massfit_f:.6f}")
    print(f"massfit_B={massfit_outer_ratio:.6f}")
    print(f"massfit_rms={massfit_rms:.6f}")


if __name__ == "__main__":
    main()
