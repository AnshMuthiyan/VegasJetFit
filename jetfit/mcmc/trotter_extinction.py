"""Trotter (2011) source-frame dust extinction model and fitted priors.

The attenuation law follows thesis equations 3.25--3.29.  The fitted-prior
relations follow equations 3.32--3.38, conditioned here on the peak values of
the hyperparameter posteriors in Tables 3.2--3.5.  Their quoted cosmic scatter
is represented by explicit nuisance parameters in both coordinates.
"""

from __future__ import annotations

import numpy as np


class TrotterDustPrior:
    """Evaluate the conditional Trotter dust prior and its physical parameters."""

    hyperparams = {
        "b_c1": -1.5038,
        "theta_c1": 106.953,
        "b_rv1": 4.8118,
        "theta_rv1": 95.995,
        "b_rv2": 2.8987,
        "theta_rv2": -6.945,
        "b_bh1": 2.4845,
        "theta_bh1": 262.749,
        "b_bh2": 2.2511,
        "theta_bh2": -64.803,
        "x0_base": 4.60604,
        "gamma_base": 0.84195,
    }

    # Zero-mean nuisance priors.  Symmetric entries are (sigma+, sigma-).
    delta_sigmas = {
        "delta_c2_c1": (0.08720, 0.08720),
        "delta_c1": (0.29313, 0.29313),
        "delta_c2_rv": (0.15495, 0.15495),
        "delta_rv": (0.36246, 0.36246),
        "delta_c2_bh": (0.14246, 0.14246),
        "delta_bh": (0.48315, 0.48315),
        "delta_x0": (0.01212, 0.03839),
        "delta_gamma": (0.16949, 0.10605),
    }

    def get_custom_param_names(self):
        return set(self.delta_sigmas)

    @staticmethod
    def _asymmetric_logpdf(value, sigma_plus, sigma_minus):
        value = np.asarray(value)
        sigma = np.where(value >= 0.0, sigma_plus, sigma_minus)
        normalization = 2.0 / (
            np.sqrt(2.0 * np.pi) * (sigma_plus + sigma_minus)
        )
        return np.log(normalization) - 0.5 * (value / sigma) ** 2

    def log_prior(self, extinction):
        """Return nuisance log prior plus hard physical constraints."""
        total = 0.0
        for name, (sigma_plus, sigma_minus) in self.delta_sigmas.items():
            total += self._asymmetric_logpdf(
                extinction.get(name, 0.0), sigma_plus, sigma_minus
            )

        c1, rv, bh, x0, gamma = self.get_physical_dust_params(
            extinction["c2"], extinction
        )
        av = extinction.get("av_source_frame")
        c4 = extinction.get("c4")
        physical = np.asarray([c1, rv, bh, x0, gamma, av, c4], dtype=float)
        if not np.all(np.isfinite(physical)):
            return -np.inf
        if av < 0.0 or c4 < 0.0 or rv <= 0.0 or not 0.0 <= bh <= 10.0 or gamma <= 0.0:
            return -np.inf
        return float(total)

    def get_physical_dust_params(self, c2, extinction):
        """Map sampled parameters to (c1, Rv, BH, x0, gamma)."""
        hp = self.hyperparams
        c2 = np.asarray(c2)

        c2_c1 = c2 - extinction.get("delta_c2_c1", 0.0)
        c1 = (
            hp["b_c1"]
            + np.tan(np.radians(hp["theta_c1"])) * (c2_c1 - 1.2403)
            + extinction.get("delta_c1", 0.0)
        )

        c2_rv = c2 - extinction.get("delta_c2_rv", 0.0)
        rv_term1 = hp["b_rv1"] + np.tan(np.radians(hp["theta_rv1"])) * (
            c2_rv + 0.0708
        )
        rv_term2 = hp["b_rv2"] + np.tan(np.radians(hp["theta_rv2"])) * (
            c2_rv - 1.4953
        )
        rv = np.logaddexp(rv_term1, rv_term2) + extinction.get("delta_rv", 0.0)

        c2_bh = c2 - extinction.get("delta_c2_bh", 0.0)
        bh_term1 = -hp["b_bh1"] - np.tan(np.radians(hp["theta_bh1"])) * (
            c2_bh + 0.0143
        )
        bh_term2 = -hp["b_bh2"] - np.tan(np.radians(hp["theta_bh2"])) * (
            c2_bh - 1.4087
        )
        bh = -np.logaddexp(bh_term1, bh_term2) + extinction.get("delta_bh", 0.0)

        x0 = hp["x0_base"] + extinction.get("delta_x0", 0.0)
        gamma = hp["gamma_base"] + extinction.get("delta_gamma", 0.0)
        return c1, rv, bh, x0, gamma


def _ccm_a_b(wavenumber):
    """Return CCM89 a(x), b(x) for the IR/optical interval used here."""
    x = np.asarray(wavenumber, dtype=float)
    a = np.empty_like(x)
    b = np.empty_like(x)
    infrared = x < 1.1
    a[infrared] = 0.574 * x[infrared] ** 1.61
    b[infrared] = -0.527 * x[infrared] ** 1.61

    y = x[~infrared] - 1.82
    a[~infrared] = np.polyval(
        [0.32999, -0.77530, 0.01979, 0.72085, -0.02427, -0.50447, 0.17699, 1.0], y
    )
    b[~infrared] = np.polyval(
        [-2.09002, 5.30260, -0.62251, -5.38434, 1.07233, 2.28305, 1.41338, 0.0], y
    )
    return a, b


def _fm_extinction_magnitudes(x, av, c1, c2, bh, c4, rv, x0, gamma):
    far_uv = np.where(
        x > 5.9,
        0.5392 * (x - 5.9) ** 2 + 0.05644 * (x - 5.9) ** 3,
        0.0,
    )
    drude = x**2 / (((x**2 - x0**2) ** 2) / gamma**2 + x**2)
    return av * (1.0 + (c1 + c2 * x + bh * drude + c4 * far_uv) / rv)


def trotter_source_attenuation(wavenumber, extinction, prior=None):
    """Return source-frame flux attenuation for inverse microns.

    Dust attenuation is intentionally unity outside 0.3 < x < 10.97 um^-1;
    radio/X-ray handling and Lyman absorption are separate physical effects.
    """
    prior = prior or TrotterDustPrior()
    x = np.asarray(wavenumber, dtype=float)
    scalar = x.ndim == 0
    x = np.atleast_1d(x)
    attenuation = np.ones_like(x)
    valid = np.isfinite(x) & (x > 0.3) & (x < 10.97)
    if not np.any(valid):
        return float(attenuation[0]) if scalar else attenuation

    xv = x[valid]
    av = float(extinction["av_source_frame"])
    c2 = float(extinction["c2"])
    c4 = float(extinction["c4"])
    c1, rv, bh, x0, gamma = prior.get_physical_dust_params(c2, extinction)
    c1, rv, bh, x0, gamma = map(float, (c1, rv, bh, x0, gamma))

    magnitudes = np.empty_like(xv)
    ccm = xv < 1.82
    if np.any(ccm):
        a, b = _ccm_a_b(xv[ccm])
        magnitudes[ccm] = av * (a + b / rv)

    transition = (xv >= 1.82) & (xv <= 3.3)
    if np.any(transition):
        xt = xv[transition]
        a, b = _ccm_a_b(xt)
        ccm_t = av * (a + b / rv)
        a33, b33 = _ccm_a_b(np.asarray([3.3]))
        ccm_33 = av * (a33[0] + b33[0] / rv)
        fm_33 = _fm_extinction_magnitudes(
            np.asarray([3.3]), av, c1, c2, bh, c4, rv, x0, gamma
        )[0]
        if av == 0.0:
            magnitudes[transition] = 0.0
        else:
            scale = 1.0 + ((fm_33 - ccm_33) / ccm_33) * (
                (xt - 1.82) / (3.3 - 1.82)
            )
            magnitudes[transition] = ccm_t * scale

    ultraviolet = xv > 3.3
    if np.any(ultraviolet):
        magnitudes[ultraviolet] = _fm_extinction_magnitudes(
            xv[ultraviolet], av, c1, c2, bh, c4, rv, x0, gamma
        )

    attenuation[valid] = 10.0 ** (-0.4 * magnitudes)
    return float(attenuation[0]) if scalar else attenuation


trotter_dust_prior = TrotterDustPrior()
