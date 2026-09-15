"""Trotter (2011) empirical Ly-alpha-forest transmission model.

Unlike the wavelength-resolved Inoue et al. (2014) prescription, Trotter's
model assigns one effective IGM transmission to each photometric filter. The
filter coordinates ``z_f`` and ``delta_z_f`` are the response-weighted mean
absorber redshift and effective redshift bin width of the filter portion that
lies between the source-frame Lyman limit and Ly-alpha.

The population relation follows Trotter (2011), Equations 3.41 and 3.46. The
filter-specific scatter prior follows Equations 3.44 and 3.45. Keeping this
filter-level model separate from the Inoue opacity prevents the two physically
different prescriptions from being mixed accidentally.
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


def calculate_igm_transmission(z_f, delta_z_f, delta_igm=0.0):
    """Return Trotter's filter-level IGM transmission.

    ``delta_z_f`` does not enter the mean relation directly; it determines the
    width of the prior on ``delta_igm`` in :class:`TrotterIGMPrior`.
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

    theta1 = np.radians(41.4538)
    theta2 = np.radians(79.1200)
    b1 = -0.20184
    b2 = 1.18711
    z1 = 4.10
    z2 = 6.15
    optical_depth = np.exp(
        b1 + np.tan(theta1) * (z_f - z1)
    ) + np.exp(
        b2 + np.tan(theta2) * (z_f - z2)
    )
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
