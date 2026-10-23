#!/usr/bin/env python3
"""Validate saved low-resolution finite-core wind runs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

from preflight import MP_G
from validate_smoke import RHO_UNIT, SPEED_UNIT, TEMP_UNIT, read_vtu


def expected_nh(radius_pc: np.ndarray, n0: float) -> np.ndarray:
    return np.where(
        radius_pc <= 1.0,
        n0 * np.exp(-radius_pc**2),
        np.where(radius_pc <= 2.0, n0 / np.e / radius_pc**2, n0 / np.e / 4.0),
    )


def expected_front(n0: float, inner_radius_pc: float = 0.1) -> float:
    radius = np.linspace(inner_radius_pc, 2.0, 100_001)
    nh = expected_nh(radius, n0)
    recombinations = 4.0 * np.pi * 2.6e-13 * nh**2 * radius**2 * (3.085677581e18)**3
    cumulative = np.cumsum((recombinations[1:] + recombinations[:-1]) * 0.5 * np.diff(radius))
    index = int(np.searchsorted(cumulative, 2.0e49))
    if index >= len(cumulative):
        raise ValueError(f"initial front exceeds the 2 pc integration range at n0={n0:g}")
    return float(radius[index + 1])


def validate(root: Path, prefix: str, endpoint_myr: float, log_prefix: str,
             n0_cm3: float, inner_radius_pc: float = 0.1) -> None:
    log = (root / f"{log_prefix}.run.log").read_text(encoding="utf-8")
    stderr = root / f"{log_prefix}.run.err"
    if "Finished AMRVAC" not in log or stderr.stat().st_size:
        raise ValueError("missing normal completion or nonempty stderr")
    paths = sorted(root.glob(f"{prefix}[0-9][0-9][0-9][0-9].vtu"))
    if len(paths) < 2:
        raise ValueError("missing initial or endpoint VTU")
    ages = []
    min_rho = np.inf
    min_p = np.inf
    outer_change = 0.0
    core_drift = 0.0
    core_speed = 0.0
    initial = None
    for path in paths:
        age_yr_365p25, data = read_vtu(path)
        age_myr = age_yr_365p25 * (365.25 / 365.0) / 1.0e6
        if not np.all(np.isfinite(data)) or np.any(data[:, 1] <= 0) or np.any(data[:, 3] <= 0):
            raise ValueError(f"nonfinite or nonpositive density/pressure in {path.name}")
        ages.append(age_myr)
        min_rho = min(min_rho, float(np.min(data[:, 1]) * RHO_UNIT))
        min_p = min(min_p, float(np.min(data[:, 3])))
        if initial is None:
            initial = data
            core = (data[:, 0] > 0.15) & (data[:, 0] < 1.9)
            nh = data[core, 1] * RHO_UNIT / (1.4 * MP_G)
            if not np.allclose(nh, expected_nh(data[core, 0], n0_cm3), rtol=0.025):
                raise ValueError("initial core density does not match analytic profile")
            front_initial = expected_front(n0_cm3, inner_radius_pc) if "ion_" in prefix else None
            hot = ((data[:, 0] >= inner_radius_pc) &
                   (data[:, 0] < front_initial - 0.02)) if front_initial else None
            if "ion_" in prefix and np.count_nonzero(hot) < 2:
                raise ValueError("fewer than two resolved initial H II cells")
            if "ion_" in prefix and not np.isclose(
                np.median(data[hot, 3] / data[hot, 1] * TEMP_UNIT), 1.0e4, rtol=0.01
            ):
                raise ValueError("initial H II cells are not at 10,000 K")
            if "ion_" in prefix:
                hot_edge = np.max(data[data[:, 3] / data[:, 1] * TEMP_UNIT > 5000, 0])
                near_front = np.unique(data[np.abs(data[:, 0] - front_initial) < 0.12, 0])
                cell_spacing = float(np.max(np.diff(near_front)))
                if abs(hot_edge - front_initial) > 2.0 * cell_spacing:
                    raise ValueError(
                        f"initial ionization edge {hot_edge:.3f} pc differs "
                        f"from Strömgren integral {front_initial:.3f} pc "
                        f"by more than two local cell spacings"
                    )
        if prefix.startswith("atmosphere"):
            core = (data[:, 0] > 0.15) & (data[:, 0] < 1.9)
            core_drift = max(
                core_drift,
                float(np.max(np.abs(data[core, 1] / initial[core, 1] - 1.0))),
            )
            core_speed = max(core_speed, float(np.max(np.abs(data[core, 2]))))
        outer = data[:, 0] > 39.0
        if np.any(outer):
            outer_change = max(
                outer_change,
                float(np.max(np.abs(data[outer, 1] / initial[outer, 1] - 1.0))),
            )
    if not np.isclose(ages[0], 0.0, atol=1e-9):
        raise ValueError("first save is not at zero age")
    if not np.all(np.diff(ages) > 0):
        raise ValueError("VTU ages are not strictly increasing")
    if not np.isclose(ages[-1], endpoint_myr, atol=2e-5):
        raise ValueError(f"endpoint {ages[-1]:.6f} Myr differs from {endpoint_myr:.6f}")
    if prefix.startswith("ion_") and endpoint_myr > 4.6:
        if len(paths) != 49:
            raise ValueError(f"expected 49 full-lifetime saves, found {len(paths)}")
        for index, expected_kms in ((44, 15.0), (46, 2000.0)):
            _, data = read_vtu(paths[index])
            inner_speeds = data[data[:, 0] <= 0.15, 2] * SPEED_UNIT / 1.0e5
            if not np.any(np.isclose(inner_speeds, expected_kms, rtol=0.05)):
                raise ValueError(
                    f"save {index}: no inner 0.15 pc cell matches "
                    f"phase speed {expected_kms:.1f} km/s within 5%"
                )
    if prefix.startswith("atmosphere") and (core_drift > 0.01 or core_speed > 0.001):
        raise ValueError(
            f"hydrostatic drift too large: density={core_drift:.3g}, "
            f"speed={core_speed:.3g} code"
        )
    fronts = [float(match) for match in re.findall(
        r"^ FRONT\s+\d+\s+\S+\s+(\S+)", log, re.M
    )]
    if "ion_" in prefix and not fronts:
        raise ValueError("no front diagnostics")
    summary = (
        f"{prefix}: n0={n0_cm3:g} cm^-3, {len(paths)} VTUs, "
        f"endpoint={ages[-1]:.6f} Myr, "
        f"min rho={min_rho:.3e} g/cm3, min p={min_p:.3e} code, "
        f"outer density change={outer_change:.3g}"
    )
    if fronts:
        summary += f", last logged front={fronts[-1]:.3f} pc"
    if prefix.startswith("atmosphere"):
        summary += f", core density drift={core_drift:.3g}, speed={core_speed:.3g} code"
    print(summary)
    if fronts and fronts[-1] >= 38.0:
        print("WARNING: ionization front approaches the 40 pc boundary")
    if outer_change >= 0.01:
        print("WARNING: outer radial density differs by >=1% from initial state")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("prefix")
    parser.add_argument("endpoint_myr", type=float)
    parser.add_argument("--log-prefix")
    parser.add_argument("--n0-cm3", type=float, default=2000.0)
    parser.add_argument("--inner-radius-pc", type=float, default=0.1)
    args = parser.parse_args()
    validate(args.root, args.prefix, args.endpoint_myr, args.log_prefix or args.prefix,
             args.n0_cm3, args.inner_radius_pc)


if __name__ == "__main__":
    main()
