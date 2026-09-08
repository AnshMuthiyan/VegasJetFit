#!/usr/bin/env python3
"""
Compare a shelf-plus-smooth-contact bubble surrogate against the current
mass-scaled cavity model for a single AMRVAC snapshot.

The new surrogate keeps the same physical GRB-facing parameters:
  - r_t
  - n_t
  - n_ism

and replaces the intershock region with:
  1. a short flat shelf at 4 n_t just after the termination shock
  2. a declining cavity profile
  3. a smooth outer contact transition into the ISM

The total intershock mass is still tied back to the old simple-bubble closure
through a scalar factor f_M.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

from analyze_amrvac_bubble_profiles import (
    PC_TO_CM,
    TINY,
    bubble_number_density,
    bubble_shell_radius,
    read_vtu_snapshot,
)
from compare_empirical_cavity_model import (
    empirical_cavity_profile,
    find_profile_rises,
    fit_empirical_cavity_slope,
    fit_mass_scaled_cavity,
    infer_nism_from_run_name,
    infer_nt_from_inner_wind,
    intershock_mass_ratio,
    outer_ratio_from_mass_ratio,
)


def shelf_plateau_mass_ratio(shelf_ratio: float) -> float:
    return (4.0 / 3.0) * (shelf_ratio**3 - 1.0)


def shelf_cavity_mass_ratio(outer_ratio: float, shelf_ratio: float, slope_s: float) -> float:
    plateau = shelf_plateau_mass_ratio(shelf_ratio)
    if outer_ratio <= shelf_ratio:
        return plateau
    if abs(slope_s - 3.0) < 1e-8:
        cavity = 4.0 * shelf_ratio**slope_s * np.log(outer_ratio / shelf_ratio)
    else:
        cavity = (
            4.0
            * shelf_ratio**slope_s
            * (outer_ratio ** (3.0 - slope_s) - shelf_ratio ** (3.0 - slope_s))
            / (3.0 - slope_s)
        )
    return float(plateau + cavity)


def outer_ratio_from_shelf_mass(target_mass_ratio: float, shelf_ratio: float, slope_s: float) -> float:
    target_mass_ratio = float(max(target_mass_ratio, 1e-12))
    shelf_ratio = float(max(shelf_ratio, 1.0 + 1e-9))
    if target_mass_ratio <= shelf_plateau_mass_ratio(shelf_ratio):
        return shelf_ratio * (1.0 + 1e-9)

    lo = shelf_ratio * (1.0 + 1e-9)
    hi = max(lo * 2.0, lo + 1e-6)
    while shelf_cavity_mass_ratio(hi, shelf_ratio, slope_s) < target_mass_ratio and hi < 1e8:
        hi *= 1.5

    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if shelf_cavity_mass_ratio(mid, shelf_ratio, slope_s) < target_mass_ratio:
            lo = mid
        else:
            hi = mid
    return float(0.5 * (lo + hi))


def shelf_contact_profile(
    radius_cm: np.ndarray,
    rt_pc: float,
    nt_cm3: float,
    nism_cm3: float,
    shelf_ratio: float,
    outer_ratio: float,
    slope_s: float,
    width_dex: float,
) -> np.ndarray:
    rt_cm = rt_pc * PC_TO_CM
    x = np.maximum(np.asarray(radius_cm, dtype=float) / rt_cm, 1e-30)

    inner = nt_cm3 * x**-2.0
    postshock = np.where(
        x < shelf_ratio,
        4.0 * nt_cm3,
        4.0 * nt_cm3 * (x / shelf_ratio) ** (-slope_s),
    )

    trans = 0.5 * (1.0 + np.tanh((np.log10(x) - np.log10(outer_ratio)) / max(width_dex, 1e-6)))
    outer = (1.0 - trans) * postshock + trans * nism_cm3
    return np.where(x < 1.0, inner, outer)


def fit_shelf_contact_model(
    radius_cm: np.ndarray,
    number_density_cm3: np.ndarray,
    rt_pc: float,
    nt_cm3: float,
    nism_cm3: float,
    simple_mass_ratio: float,
    initial_s: float,
    initial_f_mass: float,
) -> tuple[float, float, float, float, float, float]:
    def unpack(params: np.ndarray) -> tuple[float, float, float, float, float]:
        slope_s = 10.0 ** params[0]
        f_mass = 10.0 ** params[1]
        shelf_ratio = 1.0 + 10.0 ** params[2]
        width_dex = 10.0 ** params[3]
        target_mass_ratio = f_mass * simple_mass_ratio
        outer_ratio = outer_ratio_from_shelf_mass(target_mass_ratio, shelf_ratio, slope_s)
        return slope_s, f_mass, shelf_ratio, width_dex, outer_ratio

    def residual(params: np.ndarray) -> np.ndarray:
        slope_s, f_mass, shelf_ratio, width_dex, outer_ratio = unpack(params)
        model = shelf_contact_profile(
            radius_cm=radius_cm,
            rt_pc=rt_pc,
            nt_cm3=nt_cm3,
            nism_cm3=nism_cm3,
            shelf_ratio=shelf_ratio,
            outer_ratio=outer_ratio,
            slope_s=slope_s,
            width_dex=width_dex,
        )
        res = np.log10(np.maximum(model, TINY)) - np.log10(number_density_cm3)
        # Light penalty if the shelf alone already consumes too much mass.
        plateau_over = max(shelf_plateau_mass_ratio(shelf_ratio) - f_mass * simple_mass_ratio, 0.0)
        return np.concatenate([res, np.array([5.0 * plateau_over])])

    initial_s = float(np.clip(initial_s, 0.1, 2.99))
    initial_f_mass = float(np.clip(initial_f_mass, 1e-4, 10.0))
    x0 = [
        np.log10(initial_s),
        np.log10(initial_f_mass),
        np.log10(0.15),
        np.log10(0.03),
    ]
    lower = [np.log10(0.1), np.log10(1e-4), np.log10(1e-3), np.log10(3e-3)]
    upper = [np.log10(2.99), np.log10(10.0), np.log10(1.0), np.log10(0.25)]

    result = least_squares(
        residual,
        x0=x0,
        bounds=(lower, upper),
        loss="soft_l1",
        f_scale=0.1,
        max_nfev=8000,
    )
    slope_s, f_mass, shelf_ratio, width_dex, outer_ratio = unpack(result.x)
    rms = float(
        np.sqrt(
            np.mean(
                (
                    np.log10(
                        np.maximum(
                            shelf_contact_profile(
                                radius_cm=radius_cm,
                                rt_pc=rt_pc,
                                nt_cm3=nt_cm3,
                                nism_cm3=nism_cm3,
                                shelf_ratio=shelf_ratio,
                                outer_ratio=outer_ratio,
                                slope_s=slope_s,
                                width_dex=width_dex,
                            ),
                            TINY,
                        )
                    )
                    - np.log10(number_density_cm3)
                )
                ** 2
            )
        )
    )
    return slope_s, f_mass, shelf_ratio, width_dex, outer_ratio, rms


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vtu",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2025_08_07/density_21/output/Ostar_1D/test0010.vtu",
        help="AMRVAC VTU file to compare.",
    )
    parser.add_argument(
        "--output",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate/density_21_contact_cavity_compare.png",
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

    simple = bubble_number_density(radius_cm, first_rise_pc * PC_TO_CM, nt_cm3, nism_cm3)
    simple_rms = float(np.sqrt(np.mean((np.log10(np.maximum(simple, TINY)) - np.log10(number_density_cm3)) ** 2)))
    _, simple_r2_cm = bubble_shell_radius(first_rise_pc * PC_TO_CM, nt_cm3, nism_cm3)
    simple_outer_ratio = simple_r2_cm / (first_rise_pc * PC_TO_CM)
    simple_mass_ratio = intershock_mass_ratio(simple_outer_ratio, 0.0)

    empirical_s, empirical_rms = fit_empirical_cavity_slope(
        radius_cm=radius_cm,
        number_density_cm3=number_density_cm3,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        outer_rise_pc=second_rise_pc,
    )
    empirical_outer_ratio = second_rise_pc / first_rise_pc
    empirical_mass_ratio = intershock_mass_ratio(empirical_outer_ratio, empirical_s)
    empirical_f_mass = empirical_mass_ratio / simple_mass_ratio

    massfit_s, massfit_f, massfit_outer_ratio, massfit_rms = fit_mass_scaled_cavity(
        radius_cm=radius_cm,
        number_density_cm3=number_density_cm3,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        simple_mass_ratio=simple_mass_ratio,
        initial_s=empirical_s,
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

    contact_s, contact_f, contact_shelf_ratio, contact_width_dex, contact_outer_ratio, contact_rms = fit_shelf_contact_model(
        radius_cm=radius_cm,
        number_density_cm3=number_density_cm3,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        simple_mass_ratio=simple_mass_ratio,
        initial_s=massfit_s,
        initial_f_mass=massfit_f,
    )
    contact = shelf_contact_profile(
        radius_cm=radius_cm,
        rt_pc=first_rise_pc,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        shelf_ratio=contact_shelf_ratio,
        outer_ratio=contact_outer_ratio,
        slope_s=contact_s,
        width_dex=contact_width_dex,
    )
    contact_mass_ratio = shelf_cavity_mass_ratio(contact_outer_ratio, contact_shelf_ratio, contact_s)

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(8.4, 8.9),
        dpi=220,
        sharex=True,
        height_ratios=[3, 1],
    )

    ax1.loglog(radius_pc, number_density_cm3, lw=2.3, label=f"{run_name} AMRVAC")
    ax1.loglog(radius_pc, simple, "--", lw=1.6, label="original simple bubble")
    ax1.loglog(radius_pc, massfit, "-.", lw=1.9, label="mass-scaled cavity fit")
    ax1.loglog(radius_pc, contact, ":", lw=2.5, label="shelf + smooth-contact fit")
    ax1.axvline(first_rise_pc, color="0.35", ls=":", lw=1.0, label=fr"first rise = {first_rise_pc:.3f} pc")
    ax1.axvline(second_rise_pc, color="0.55", ls="--", lw=1.0, label=fr"second rise = {second_rise_pc:.3f} pc")
    ax1.set_ylabel(r"n(r) [cm$^{-3}$]")
    ax1.set_title(f"{run_name}: shelf + smooth-contact surrogate")
    ax1.set_xlim(0.12, float(radius_pc.max()) * 1.22)
    ax1.grid(True, which="both", alpha=0.25)
    ax1.legend(fontsize=8, ncol=2)

    ax2.loglog(radius_pc, np.maximum(simple / number_density_cm3, TINY), lw=1.4, color="C1", alpha=0.9, label="simple/data")
    ax2.loglog(radius_pc, np.maximum(massfit / number_density_cm3, TINY), lw=1.7, color="C3", label="mass-scaled/data")
    ax2.loglog(radius_pc, np.maximum(contact / number_density_cm3, TINY), lw=1.8, color="C2", label="contact/data")
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
            fr"mass-scaled cavity: $s$ = {massfit_s:.3f}, $f_M$ = {massfit_f:.4f}, RMS = {massfit_rms:.3f} dex",
            fr"contact fit: $x_p$ = {contact_shelf_ratio:.3f}, $s$ = {contact_s:.3f}, $w$ = {contact_width_dex:.4f} dex",
            fr"contact fit: $R_2/r_t$ = {contact_outer_ratio:.3f}, $f_M$ = {contact_f:.4f}, RMS = {contact_rms:.3f} dex",
            fr"simple intershock mass / (4 pi n_t r_t^3) = {simple_mass_ratio:.3f}",
            fr"contact intershock mass / (4 pi n_t r_t^3) = {contact_mass_ratio:.3f}",
        ]
    )
    ax1.text(
        0.03,
        0.03,
        text,
        transform=ax1.transAxes,
        fontsize=8.3,
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
    print(f"simple_rms={simple_rms:.6f}")
    print(f"massfit_s={massfit_s:.6f}")
    print(f"massfit_f_mass={massfit_f:.6f}")
    print(f"massfit_B={massfit_outer_ratio:.6f}")
    print(f"massfit_rms={massfit_rms:.6f}")
    print(f"contact_s={contact_s:.6f}")
    print(f"contact_f_mass={contact_f:.6f}")
    print(f"contact_shelf_ratio={contact_shelf_ratio:.6f}")
    print(f"contact_width_dex={contact_width_dex:.6f}")
    print(f"contact_B={contact_outer_ratio:.6f}")
    print(f"contact_rms={contact_rms:.6f}")
    print(f"simple_intershock_mass_ratio={simple_mass_ratio:.6f}")
    print(f"contact_intershock_mass_ratio={contact_mass_ratio:.6f}")


if __name__ == "__main__":
    main()
