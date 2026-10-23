#!/usr/bin/env python3
"""Estimate scales for a 40 Msun wind entering an initially ionized core.

The Spitzer expansion estimate is illustrative only: it assumes uniform,
dust-free gas and omits winds, gravity, and external pressure.
"""

from __future__ import annotations

import argparse
import json
from math import pi, sqrt


PC_CM = 3.085677581e18
YEAR_S = 365.25 * 86400.0
MSUN_G = 1.98847e33
MP_G = 1.6726219e-24
G_CGS = 6.67430e-8
ALPHA_B_10000K = 2.6e-13


def scales(n_h: float, q_h: float, core_radius_pc: float) -> dict[str, float]:
    if min(n_h, q_h, core_radius_pc) <= 0:
        raise ValueError("density, photon rate, and core radius must be positive")

    radius_cm = (3.0 * q_h / (4.0 * pi * ALPHA_B_10000K * n_h**2)) ** (1.0 / 3.0)
    core_cm = core_radius_pc * PC_CM
    c_ii = 1.0e6  # 10 km/s, illustrative ionized-gas sound speed
    t_cross_s = None
    if core_cm > radius_cm:
        t_cross_s = 4.0 * radius_cm / (7.0 * c_ii) * (
            (core_cm / radius_cm) ** (7.0 / 4.0) - 1.0
        )

    cloud_mass_g = 4.0 * pi / 3.0 * core_cm**3 * 1.4 * MP_G * n_h
    return {
        "n_h_cm3": n_h,
        "q_h_per_s": q_h,
        "core_radius_pc": core_radius_pc,
        "stromgren_radius_pc": radius_cm / PC_CM,
        "recombination_time_yr": 1.0 / (ALPHA_B_10000K * n_h) / YEAR_S,
        "illustrative_hii_crossing_time_myr": (
            None if t_cross_s is None else t_cross_s / YEAR_S / 1.0e6
        ),
        "uniform_core_mass_msun": cloud_mass_g / MSUN_G,
        "core_escape_speed_km_s": sqrt(
            2.0 * G_CGS * (cloud_mass_g + 40.0 * MSUN_G) / core_cm
        ) / 1.0e5,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-h", type=float, default=1.0e3)
    parser.add_argument("--q-h", type=float, default=2.0e49)
    parser.add_argument("--core-radius-pc", type=float, default=2.0)
    args = parser.parse_args()
    print(json.dumps(scales(args.n_h, args.q_h, args.core_radius_pc), indent=2))


if __name__ == "__main__":
    main()
