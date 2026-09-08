"""Core jet-energy and Lorentz-factor conversion helpers.

The sampler may use either the historical on-axis isotropic-equivalent energy
``E52``, the total two-sided jet energy ``E_j_52``, or the two-sided core
energy ``E_j_core_52``.  It may likewise use the historical on-axis ``lf0`` or
the solid-angle-averaged core Lorentz factor ``Gamma_0_core_avg``.
VegasAfterglow constructors still require the on-axis isotropic-equivalent
energy and on-axis Lorentz factor, so these helpers perform the inverse profile
mappings using the same conventions as the post-fit products.
"""

from __future__ import annotations

import math

import numpy as np


def integrated_profile_beaming_fraction(
    jet_type: str,
    theta_c: float,
    k_e: float | None = None,
    n_theta: int = 1024,
) -> float:
    """
    Return the two-sided beaming fraction ``E_j / E_iso,on-axis``.

    The integral is ``int_0^(pi/2) f(theta) sin(theta) dtheta`` where
    ``f(theta)`` is the angular energy profile normalized to unity on-axis.
    This matches the Frail-style two-sided convention: a top-hat jet gives
    ``1 - cos(theta_c)``.
    """
    theta_c = float(theta_c)
    if not math.isfinite(theta_c) or theta_c <= 0.0:
        return float("nan")

    kind = str(jet_type).lower()
    if kind == "tophat":
        return 1.0 - math.cos(theta_c)

    theta = np.linspace(0.0, 0.5 * math.pi, int(n_theta))
    x = theta / theta_c
    if kind == "gaussian":
        profile = np.exp(-0.5 * x * x)
    elif kind == "powerlaw":
        ke = 2.0 if k_e is None or not math.isfinite(float(k_e)) else float(k_e)
        profile = 1.0 / (1.0 + np.power(x, ke))
    else:
        return 1.0 - math.cos(theta_c)

    return float(np.trapezoid(profile * np.sin(theta), theta))


def integrated_core_profile_beaming_fraction(
    jet_type: str,
    theta_c: float,
    k_e: float | None = None,
    n_theta: int = 1024,
) -> float:
    """Return two-sided ``E_j,core / E_iso,on-axis`` through ``theta_c``."""
    theta_c = float(theta_c)
    if not math.isfinite(theta_c) or theta_c <= 0.0:
        return float("nan")

    kind = str(jet_type).lower()
    if kind == "tophat":
        return 1.0 - math.cos(theta_c)

    theta = np.linspace(0.0, theta_c, int(n_theta))
    x = theta / theta_c
    if kind == "gaussian":
        profile = np.exp(-0.5 * x * x)
    elif kind == "powerlaw":
        ke = 2.0 if k_e is None or not math.isfinite(float(k_e)) else float(k_e)
        profile = 1.0 / (1.0 + np.power(x, ke))
    else:
        profile = np.ones_like(theta)
    return float(np.trapezoid(profile * np.sin(theta), theta))


def core_gamma_profile_average(
    jet_type: str,
    theta_c: float,
    k_g: float | None = None,
    n_theta: int = 1024,
) -> float:
    """Return the core solid-angle average of the normalized Gamma profile."""
    theta_c = float(theta_c)
    if not math.isfinite(theta_c) or theta_c <= 0.0:
        return float("nan")

    kind = str(jet_type).lower()
    if kind == "tophat":
        return 1.0

    theta = np.linspace(0.0, theta_c, int(n_theta))
    x = theta / theta_c
    if kind == "gaussian":
        profile = np.exp(-0.5 * x * x)
    elif kind == "powerlaw":
        kg = 2.0 if k_g is None or not math.isfinite(float(k_g)) else float(k_g)
        profile = 1.0 / (1.0 + np.power(x, kg))
    else:
        profile = np.ones_like(theta)
    denominator = 1.0 - math.cos(theta_c)
    return float(np.trapezoid(profile * np.sin(theta), theta) / denominator)


def e_iso52_from_e_jet52(
    e_j_52: float,
    *,
    jet_type: str,
    theta_c: float,
    k_e: float | None = None,
) -> float:
    """Convert two-sided true jet energy in 10^52 erg to on-axis ``E52``."""
    frac = integrated_profile_beaming_fraction(jet_type, theta_c, k_e=k_e)
    if not math.isfinite(frac) or frac <= 0.0:
        return float("nan")
    return float(e_j_52) / frac


def e_iso52_from_e_jet_core52(
    e_j_core_52: float,
    *,
    jet_type: str,
    theta_c: float,
    k_e: float | None = None,
) -> float:
    """Convert two-sided core energy in 10^52 erg to on-axis ``E52``."""
    frac = integrated_core_profile_beaming_fraction(
        jet_type, theta_c, k_e=k_e
    )
    if not math.isfinite(frac) or frac <= 0.0:
        return float("nan")
    return float(e_j_core_52) / frac


def gamma0_axis_from_core_average(
    gamma0_core_avg: float,
    *,
    jet_type: str,
    theta_c: float,
    k_g: float | None = None,
) -> float:
    """Convert core-averaged Gamma0 to the on-axis Gamma0 used by the engine."""
    profile_avg = core_gamma_profile_average(
        jet_type, theta_c, k_g=k_g
    )
    if not math.isfinite(profile_avg) or profile_avg <= 0.0:
        return float("nan")
    return 1.0 + (float(gamma0_core_avg) - 1.0) / profile_avg


def resolve_e_iso52(
    *,
    E52: float | None = None,
    E_j_52: float | None = None,
    E_j_core_52: float | None = None,
    jet_type: str,
    theta_c: float,
    k_e: float | None = None,
) -> float:
    """
    Resolve the internal on-axis isotropic-equivalent ``E52``.

    Precedence preserves backward compatibility: ``E52``, then total
    ``E_j_52``, then core ``E_j_core_52``.
    """
    if E52 is not None:
        return float(E52)
    if E_j_52 is not None:
        return e_iso52_from_e_jet52(
            E_j_52, jet_type=jet_type, theta_c=theta_c, k_e=k_e
        )
    if E_j_core_52 is not None:
        return e_iso52_from_e_jet_core52(
            E_j_core_52, jet_type=jet_type, theta_c=theta_c, k_e=k_e
        )
    raise TypeError("One of E52, E_j_52, or E_j_core_52 must be supplied.")


def resolve_gamma0_axis(
    *,
    lf0: float | None = None,
    Gamma_0_core_avg: float | None = None,
    jet_type: str,
    theta_c: float,
    k_g: float | None = None,
) -> float:
    """Resolve the on-axis Gamma0 required by VegasAfterglow."""
    if lf0 is not None:
        return float(lf0)
    if Gamma_0_core_avg is None:
        raise TypeError("Either lf0 or Gamma_0_core_avg must be supplied.")
    return gamma0_axis_from_core_average(
        Gamma_0_core_avg,
        jet_type=jet_type,
        theta_c=theta_c,
        k_g=k_g,
    )
