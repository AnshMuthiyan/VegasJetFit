"""Neutral-hydrogen attenuation for GRB afterglow photometry.

The intergalactic component implements the mean Inoue et al. (2014) model,
including 39 Lyman-series lines and Lyman-continuum opacity from both the
Ly-alpha-forest and DLA absorber populations.  The host component implements
the damped Ly-alpha profile used by Trotter (2011, Eq. 3.39), following Totani
et al. (2006), plus the source-frame Lyman limit assumed by Trotter.

All public functions accept observed-frame wavelengths in Angstrom.  Dust
extinction is deliberately kept in a separate module.

References
----------
Inoue, A. K., Shimizu, I., Iwata, I., & Tanaka, M. 2014, MNRAS, 442, 1805.
Trotter, A. S. 2011, PhD thesis, UNC-Chapel Hill, Section 3.4.
Totani, T. et al. 2006, PASJ, 58, 485.
"""

from __future__ import annotations

import numpy as np


C_ANGSTROM_PER_SECOND = 2.99792458e18
LYMAN_LIMIT_ANGSTROM = 911.8
LYMAN_ALPHA_FREQUENCY_HZ = 2.46605e15

# Inoue et al. (2014), Table 2.  Columns are wavelength, the three LAF
# coefficients, and the two DLA coefficients.  The paper numbers the series
# from j=2 (Ly-alpha) through j=40.
_LYMAN_SERIES = np.asarray([
    (1215.670, 1.68976e-02, 2.35379e-03, 1.02611e-04, 1.61698e-04, 5.38995e-05),
    (1025.720, 4.69229e-03, 6.53625e-04, 2.84940e-05, 1.54539e-04, 5.15129e-05),
    (972.537, 2.23898e-03, 3.11884e-04, 1.35962e-05, 1.49767e-04, 4.99222e-05),
    (949.743, 1.31901e-03, 1.83735e-04, 8.00974e-06, 1.46031e-04, 4.86769e-05),
    (937.803, 8.70656e-04, 1.21280e-04, 5.28707e-06, 1.42893e-04, 4.76312e-05),
    (930.748, 6.17843e-04, 8.60640e-05, 3.75186e-06, 1.40159e-04, 4.67196e-05),
    (926.226, 4.60924e-04, 6.42055e-05, 2.79897e-06, 1.37714e-04, 4.59048e-05),
    (923.150, 3.56887e-04, 4.97135e-05, 2.16720e-06, 1.35495e-04, 4.51650e-05),
    (920.963, 2.84278e-04, 3.95992e-05, 1.72628e-06, 1.33452e-04, 4.44841e-05),
    (919.352, 2.31771e-04, 3.22851e-05, 1.40743e-06, 1.31561e-04, 4.38536e-05),
    (918.129, 1.92348e-04, 2.67936e-05, 1.16804e-06, 1.29785e-04, 4.32617e-05),
    (917.181, 1.62155e-04, 2.25878e-05, 9.84689e-07, 1.28117e-04, 4.27056e-05),
    (916.429, 1.38498e-04, 1.92925e-05, 8.41033e-07, 1.26540e-04, 4.21799e-05),
    (915.824, 1.19611e-04, 1.66615e-05, 7.26340e-07, 1.25041e-04, 4.16804e-05),
    (915.329, 1.04314e-04, 1.45306e-05, 6.33446e-07, 1.23614e-04, 4.12046e-05),
    (914.919, 9.17397e-05, 1.27791e-05, 5.57091e-07, 1.22248e-04, 4.07494e-05),
    (914.576, 8.12784e-05, 1.13219e-05, 4.93564e-07, 1.20938e-04, 4.03127e-05),
    (914.286, 7.25069e-05, 1.01000e-05, 4.40299e-07, 1.19681e-04, 3.98938e-05),
    (914.039, 6.50549e-05, 9.06198e-06, 3.95047e-07, 1.18469e-04, 3.94896e-05),
    (913.826, 5.86816e-05, 8.17421e-06, 3.56345e-07, 1.17298e-04, 3.90995e-05),
    (913.641, 5.31918e-05, 7.40949e-06, 3.23008e-07, 1.16167e-04, 3.87225e-05),
    (913.480, 4.84261e-05, 6.74563e-06, 2.94068e-07, 1.15071e-04, 3.83572e-05),
    (913.339, 4.42740e-05, 6.16726e-06, 2.68854e-07, 1.14011e-04, 3.80037e-05),
    (913.215, 4.06311e-05, 5.65981e-06, 2.46733e-07, 1.12983e-04, 3.76609e-05),
    (913.104, 3.73821e-05, 5.20723e-06, 2.27003e-07, 1.11972e-04, 3.73241e-05),
    (913.006, 3.45377e-05, 4.81102e-06, 2.09731e-07, 1.11002e-04, 3.70005e-05),
    (912.918, 3.19891e-05, 4.45601e-06, 1.94255e-07, 1.10051e-04, 3.66836e-05),
    (912.839, 2.97110e-05, 4.13867e-06, 1.80421e-07, 1.09125e-04, 3.63749e-05),
    (912.768, 2.76635e-05, 3.85346e-06, 1.67987e-07, 1.08220e-04, 3.60734e-05),
    (912.703, 2.58178e-05, 3.59636e-06, 1.56779e-07, 1.07337e-04, 3.57789e-05),
    (912.645, 2.41479e-05, 3.36374e-06, 1.46638e-07, 1.06473e-04, 3.54909e-05),
    (912.592, 2.26347e-05, 3.15296e-06, 1.37450e-07, 1.05629e-04, 3.52096e-05),
    (912.543, 2.12567e-05, 2.96100e-06, 1.29081e-07, 1.04802e-04, 3.49340e-05),
    (912.499, 1.99967e-05, 2.78549e-06, 1.21430e-07, 1.03991e-04, 3.46636e-05),
    (912.458, 1.88476e-05, 2.62543e-06, 1.14452e-07, 1.03198e-04, 3.43994e-05),
    (912.420, 1.77928e-05, 2.47850e-06, 1.08047e-07, 1.02420e-04, 3.41402e-05),
    (912.385, 1.68222e-05, 2.34330e-06, 1.02153e-07, 1.01657e-04, 3.38856e-05),
    (912.353, 1.59286e-05, 2.21882e-06, 9.67268e-08, 1.00908e-04, 3.36359e-05),
    (912.324, 1.50996e-05, 2.10334e-06, 9.16925e-08, 1.00168e-04, 3.33895e-05),
], dtype=float)


def _validated_inputs(wavelength_angstrom, source_redshift):
    wavelength = np.asarray(wavelength_angstrom, dtype=float)
    scalar = wavelength.ndim == 0
    wavelength = np.atleast_1d(wavelength)
    z = float(source_redshift)
    if not np.isfinite(z) or z < 0.0:
        raise ValueError("source_redshift must be finite and non-negative.")
    if not np.all(np.isfinite(wavelength)) or np.any(wavelength <= 0.0):
        raise ValueError("wavelength_angstrom must be finite and positive.")
    return wavelength, z, scalar


def inoue2014_igm_optical_depth(wavelength_angstrom, source_redshift):
    """Return the mean IGM optical depth from Inoue et al. (2014).

    The analytic continuum expressions are published for observed wavelengths
    above the Lyman limit.  At shorter observed wavelengths the transmission
    is set to zero, which is conservative and outside the range of the current
    photometric data.
    """
    wavelength, z, scalar = _validated_inputs(
        wavelength_angstrom, source_redshift
    )
    if z == 0.0:
        result = np.zeros_like(wavelength)
        return float(result[0]) if scalar else result

    lam = _LYMAN_SERIES[:, 0, np.newaxis]
    wave = wavelength[np.newaxis, :]
    in_path = (wave > lam) & (wave < lam * (1.0 + z))

    laf = np.zeros_like(wave * lam)
    low = in_path & (wave < 2.2 * lam)
    middle = in_path & (wave >= 2.2 * lam) & (wave < 5.7 * lam)
    high = in_path & (wave >= 5.7 * lam)
    laf[low] = (
        _LYMAN_SERIES[:, 1, np.newaxis] * (wave / lam) ** 1.2
    )[low]
    laf[middle] = (
        _LYMAN_SERIES[:, 2, np.newaxis] * (wave / lam) ** 3.7
    )[middle]
    laf[high] = (
        _LYMAN_SERIES[:, 3, np.newaxis] * (wave / lam) ** 5.5
    )[high]

    dla = np.zeros_like(laf)
    low = in_path & (wave < 3.0 * lam)
    high = in_path & (wave >= 3.0 * lam)
    dla[low] = (
        _LYMAN_SERIES[:, 4, np.newaxis] * (wave / lam) ** 2.0
    )[low]
    dla[high] = (
        _LYMAN_SERIES[:, 5, np.newaxis] * (wave / lam) ** 3.0
    )[high]

    tau = laf.sum(axis=0) + dla.sum(axis=0)
    continuum = (wavelength > LYMAN_LIMIT_ANGSTROM) & (
        wavelength < LYMAN_LIMIT_ANGSTROM * (1.0 + z)
    )
    x = wavelength / LYMAN_LIMIT_ANGSTROM

    tau_laf = np.zeros_like(wavelength)
    if z < 1.2:
        tau_laf[continuum] = 0.3248 * (
            x[continuum] ** 1.2
            - (1.0 + z) ** -0.9 * x[continuum] ** 2.1
        )
    elif z < 4.7:
        upper = continuum & (wavelength >= 2.2 * LYMAN_LIMIT_ANGSTROM)
        lower = continuum & ~upper
        tau_laf[upper] = 2.545e-2 * (
            (1.0 + z) ** 1.6 * x[upper] ** 2.1 - x[upper] ** 3.7
        )
        tau_laf[lower] = (
            2.545e-2 * (1.0 + z) ** 1.6 * x[lower] ** 2.1
            + 0.3248 * x[lower] ** 1.2
            - 0.2496 * x[lower] ** 2.1
        )
    else:
        upper = continuum & (wavelength > 5.7 * LYMAN_LIMIT_ANGSTROM)
        middle = continuum & (wavelength >= 2.2 * LYMAN_LIMIT_ANGSTROM) & ~upper
        lower = continuum & ~(upper | middle)
        tau_laf[upper] = 5.221e-4 * (
            (1.0 + z) ** 3.4 * x[upper] ** 2.1 - x[upper] ** 5.5
        )
        tau_laf[middle] = (
            5.221e-4 * (1.0 + z) ** 3.4 * x[middle] ** 2.1
            + 0.2182 * x[middle] ** 2.1
            - 2.545e-2 * x[middle] ** 3.7
        )
        tau_laf[lower] = (
            5.221e-4 * (1.0 + z) ** 3.4 * x[lower] ** 2.1
            + 0.3248 * x[lower] ** 1.2
            - 3.140e-2 * x[lower] ** 2.1
        )

    tau_dla = np.zeros_like(wavelength)
    if z < 2.0:
        tau_dla[continuum] = (
            0.2113 * (1.0 + z) ** 2.0
            - 0.07661 * (1.0 + z) ** 2.3 * x[continuum] ** -0.3
            - 0.1347 * x[continuum] ** 2.0
        )
    else:
        upper = continuum & (wavelength >= 3.0 * LYMAN_LIMIT_ANGSTROM)
        lower = continuum & ~upper
        tau_dla[upper] = (
            0.04696 * (1.0 + z) ** 3.0
            - 0.01779 * (1.0 + z) ** 3.3 * x[upper] ** -0.3
            - 0.02916 * x[upper] ** 3.0
        )
        tau_dla[lower] = (
            0.6340
            + 0.04696 * (1.0 + z) ** 3.0
            - 0.01779 * (1.0 + z) ** 3.3 * x[lower] ** -0.3
            - 0.1347 * x[lower] ** 2.0
            - 0.2905 * x[lower] ** -0.3
        )

    tau += np.maximum(tau_laf, 0.0) + np.maximum(tau_dla, 0.0)
    tau[wavelength <= LYMAN_LIMIT_ANGSTROM] = np.inf
    tau = np.maximum(tau, 0.0)
    return float(tau[0]) if scalar else tau


def inoue2014_igm_transmission(wavelength_angstrom, source_redshift):
    """Return mean IGM transmission, ``exp(-tau_IGM)``."""
    tau = inoue2014_igm_optical_depth(wavelength_angstrom, source_redshift)
    return np.exp(-tau)


def trotter2011_host_dla_delta_log10_flux(
    wavelength_angstrom, source_redshift, nhi_cm2
):
    """Return Trotter (2011) Eq. 3.39 host-DLA ``Delta log10(F_nu)``."""
    wavelength, z, scalar = _validated_inputs(
        wavelength_angstrom, source_redshift
    )
    nhi = np.asarray(nhi_cm2, dtype=float)
    if nhi.ndim != 0 or not np.isfinite(nhi) or nhi < 0.0:
        raise ValueError("nhi_cm2 must be a finite, non-negative scalar.")
    nhi = float(nhi)

    nu_rest = C_ANGSTROM_PER_SECOND * (1.0 + z) / wavelength
    ratio = nu_rest / LYMAN_ALPHA_FREQUENCY_HZ
    numerator = -2.9979e6 * ratio**4 * nhi
    denominator = (
        39.4784 * (nu_rest - LYMAN_ALPHA_FREQUENCY_HZ) ** 2
        + 9.78275e16 * ratio**6
    )
    result = numerator / denominator
    return float(result[0]) if scalar and result.size == 1 else result


def trotter2011_host_hi_transmission(
    wavelength_angstrom, source_redshift, nhi_cm2, *, lyman_limit=True
):
    """Return host H I transmission from the DLA profile and Lyman limit."""
    wavelength, z, scalar = _validated_inputs(
        wavelength_angstrom, source_redshift
    )
    delta = trotter2011_host_dla_delta_log10_flux(wavelength, z, nhi_cm2)
    transmission = np.power(10.0, delta)
    if lyman_limit:
        transmission[
            wavelength < LYMAN_LIMIT_ANGSTROM * (1.0 + z)
        ] = 0.0
    return float(transmission[0]) if scalar else transmission


def hydrogen_transmission(
    wavelength_angstrom,
    source_redshift,
    *,
    igm_model="none",
    host_model="none",
    nhi_host_cm2=None,
):
    """Return the product of independently selected IGM and host H I models."""
    wavelength, z, scalar = _validated_inputs(
        wavelength_angstrom, source_redshift
    )
    transmission = np.ones_like(wavelength)

    if igm_model == "inoue2014":
        transmission *= inoue2014_igm_transmission(wavelength, z)
    elif igm_model != "none":
        raise ValueError(f"Unknown IGM absorption model: {igm_model!r}.")

    if host_model == "trotter2011":
        if nhi_host_cm2 is None:
            raise ValueError(
                "host_model='trotter2011' requires nhi_host_cm2."
            )
        transmission *= trotter2011_host_hi_transmission(
            wavelength, z, nhi_host_cm2
        )
    elif host_model != "none":
        raise ValueError(f"Unknown host H I absorption model: {host_model!r}.")

    return float(transmission[0]) if scalar else transmission
