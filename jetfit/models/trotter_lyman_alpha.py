"""Trotter (2011) empirical Ly-alpha-forest transmission relation.

Trotter (2011, Sec. 3.4.2) fits the mean Ly-alpha-forest transmission T as a
function of absorber redshift z_abs (Eq. 3.41, peak values of Table 3.6):

    ln[-ln T(z_abs)] = ln[ e^(b1 + tan(th1)(z_abs - z1))
                         + e^(b2 + tan(th2)(z_abs - z2)) ]       (Eq. 3.41)

where z_abs is related to observed frequency by nu_obs = nu_LyA / (1 + z_abs)
(Eq. 3.40). Scatter is Gaussian in ln(-ln T) with width Eq. 3.44; in a fit an
offset delta enters as -ln T = e^delta [...] (Eq. 3.46). In his fitting
procedure he then assigns ONE such transmission to each filter, at that
filter's response-weighted mean absorber redshift z_f, with a per-filter
scatter delta_f whose prior width is Eq. 3.45 (Eq. 3.46).

Production use (2026-10 team decision): the relation is evaluated
CONTINUOUSLY in wavelength -- each observed wavelength lambda in the forest
window gets z_abs = lambda / 1215.67 A - 1 -- as in the model spectra of
Trotter's Fig. 3.24; it multiplies the model spectrum before the filter
integral (``jetfit.core.hydrogen_absorption.trotter2011_igm_transmission``).
The per-filter construct (``calculate_igm_transmission`` for a filter's z_f,
``filter_igm_parameters``, ``TrotterIGMPrior``, and
``jetfit.core.hydrogen_absorption.trotter2011_igm_filter_transmission``) is
kept as Trotter's published prescription for reference and diagnostics; it is
NOT used to attenuate filters in production. z_f and Delta z_f remain the
natural carriers of the Eq. 3.45 prior width if a scatter term is adopted. How Trotter's sight-line scatter (Eq. 3.45,
defined per filter) should enter the continuous model has not been decided;
production uses the mean relation.
"""

from __future__ import annotations

import re

import numpy as np


LYMAN_LIMIT_ANGSTROM = 911.8
LYMAN_ALPHA_ANGSTROM = 1215.67


def filter_parameter_suffix(filter_name):
    """Return the stable TOML suffix used for one filter's IGM parameters."""
    suffix = re.sub(r"[^a-z0-9]+", "_", str(filter_name).strip().lower())
    return suffix.strip("_")


def apply_lyman_limit(obs_wavelengths_angstrom, z_grb, flux_array):
    """Return a copy of ``flux_array`` with the source Lyman limit applied."""
    wavelength = np.asarray(obs_wavelengths_angstrom, dtype=float)
    flux = np.array(flux_array, dtype=float, copy=True)
    flux[wavelength / (1.0 + float(z_grb)) < LYMAN_LIMIT_ANGSTROM] = 0.0
    return flux


# Trotter (2011) Table 3.6 peak values for Eq. 3.41 / 3.46.
_TROTTER_B1 = -0.20184
_TROTTER_THETA1_DEG = 41.4538
_TROTTER_Z1 = 4.10
_TROTTER_B2 = 1.18711
_TROTTER_THETA2_DEG = 79.1200
_TROTTER_Z2 = 6.15


def trotter_igm_optical_depth(absorber_redshift):
    """Mean Ly-alpha-forest optical depth -ln T at absorber redshift(s).

    Trotter (2011) Eq. 3.41 with the Table 3.6 peak values and zero scatter;
    vectorized over ``absorber_redshift``.
    """
    z_abs = np.asarray(absorber_redshift, dtype=float)
    theta1 = np.radians(_TROTTER_THETA1_DEG)
    theta2 = np.radians(_TROTTER_THETA2_DEG)
    return np.exp(
        _TROTTER_B1 + np.tan(theta1) * (z_abs - _TROTTER_Z1)
    ) + np.exp(
        _TROTTER_B2 + np.tan(theta2) * (z_abs - _TROTTER_Z2)
    )


def calculate_igm_transmission(z_f, delta_z_f, delta_igm=0.0):
    """Return Trotter's filter-level IGM transmission at one redshift ``z_f``.

    Trotter's per-filter prescription (Eq. 3.46); retained for reference and
    diagnostics -- production attenuates with the continuous relation (module
    docstring). ``delta_z_f`` does not enter the mean relation directly; it
    determines the width of the prior on ``delta_igm`` in
    :class:`TrotterIGMPrior`.
    """
    z_f = float(z_f)
    delta_z_f = float(delta_z_f)
    delta_igm = np.asarray(delta_igm, dtype=float)
    if not np.isfinite(z_f) or z_f < 0.0:
        raise ValueError("z_f must be finite and non-negative.")
    if not np.isfinite(delta_z_f) or delta_z_f <= 0.0:
        raise ValueError("delta_z_f must be finite and positive.")
    if not np.all(np.isfinite(delta_igm)):
        raise ValueError("delta_igm must be finite.")

    optical_depth = trotter_igm_optical_depth(z_f)
    transmission = np.exp(-np.exp(delta_igm) * optical_depth)
    transmission = np.clip(transmission, 0.0, 1.0)
    return float(transmission) if transmission.ndim == 0 else transmission


def filter_igm_parameters(absorption, filter_name):
    """Return ``(z_f, delta_z_f, delta_igm)`` for one configured filter."""
    suffix = filter_parameter_suffix(filter_name)
    keys = (
        f"z_f_{suffix}",
        f"delta_z_f_{suffix}",
        f"delta_igm_{suffix}",
    )
    missing = [key for key in keys if key not in absorption]
    if missing:
        raise ValueError(
            "Trotter IGM model requires filter parameters for "
            f"{filter_name!r}: {', '.join(missing)}."
        )
    return tuple(float(absorption[key]) for key in keys)


class TrotterIGMPrior:
    """Evaluate the filter-specific cosmic-scatter prior from Eq. 3.45."""

    def __init__(
        self,
        alpha_sigma=-0.3682,
        base_sigma=0.190677,
        z0=4.23,
        delta_z0=0.15,
    ):
        self.alpha_sigma = alpha_sigma
        self.base_sigma = base_sigma
        self.z0 = z0
        self.delta_z0 = delta_z0

    def log_prior(self, absorption):
        """Return the joint Gaussian log prior for all ``delta_igm_*`` values."""
        delta_keys = sorted(
            key for key in absorption if key.startswith("delta_igm_")
        )
        if not delta_keys:
            return 0.0

        total = 0.0
        for delta_key in delta_keys:
            suffix = delta_key.removeprefix("delta_igm_")
            z_key = f"z_f_{suffix}"
            width_key = f"delta_z_f_{suffix}"
            if z_key not in absorption or width_key not in absorption:
                raise ValueError(
                    f"{delta_key!r} requires {z_key!r} and {width_key!r}."
                )
            z_f = float(absorption[z_key])
            delta_z_f = float(absorption[width_key])
            delta = np.asarray(absorption[delta_key], dtype=float)
            if z_f < 0.0 or not np.isfinite(z_f):
                return -np.inf
            if delta_z_f <= 0.0 or not np.isfinite(delta_z_f):
                return -np.inf
            sigma = self.base_sigma * (
                ((1.0 + z_f) / (1.0 + self.z0)) ** self.alpha_sigma
                * (delta_z_f / self.delta_z0) ** -0.5
            )
            total += np.sum(
                -0.5 * (delta / sigma) ** 2
                - np.log(np.sqrt(2.0 * np.pi) * sigma)
            )
        return float(total)
