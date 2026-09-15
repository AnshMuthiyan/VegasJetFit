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
        """
        Calculates the log-probability of a value given an asymmetric Gaussian distribution.
        
        Math Context:
        If a parameter has skewed empirical distributions, we evaluate a piecewise Gaussian:
        P(x) ∝ exp(-0.5 * (x - μ)² / σ²) where σ = σ_plus if x >= μ else σ_minus.
        """
        value = np.asarray(value)
        sigma = np.where(value >= 0.0, sigma_plus, sigma_minus)
        normalization = 2.0 / (
            np.sqrt(2.0 * np.pi) * (sigma_plus + sigma_minus)
        )
        return np.log(normalization) - 0.5 * (value / sigma) ** 2

    def log_prior(self, extinction):
        """Return nuisance log prior plus hard physical constraints.
        
        Physics Context:
        The dust model shape is fundamentally driven by a single master parameter (c2). 
        All other physical parameters (c1, Rv, Bump Height) are deterministically linked 
        to c2 via observed empirical relations. 
        
        However, nature isn't perfectly deterministic! The 'deltas' (δ) are cosmic 
        scatter variables sampled by the MCMC to allow real GRBs to deviate slightly 
        from the strict empirical relations. This function penalizes those deviations.
        """
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
        """Map sampled parameters to (c1, Rv, BH, x0, gamma).
        
        Physics & Math Context:
        While some relationships (like c1 vs c2) are strictly linear, empirical data shows that 
        Rv and Bump Height (BH) hit physical "floors" or "ceilings" and change slopes. 
        
        To model this broken-linear relationship smoothly (without sharp derivatives that 
        would crash the MCMC's gradient tracking), we use `np.logaddexp(A, B)`.
        Mathematically, log(e^A + e^B) acts as a soft-maximum function, smoothly transitioning 
        between the linear asymptote A and the linear asymptote B.
        """
        hp = self.hyperparams
        c2 = np.asarray(c2)

        # c1 is a strict linear function of c2 plus its cosmic scatter (δ_c1)
        c2_c1 = c2 - extinction.get("delta_c2_c1", 0.0)
        c1 = (
            hp["b_c1"]
            + np.tan(np.radians(hp["theta_c1"])) * (c2_c1 - 1.2403)
            + extinction.get("delta_c1", 0.0)
        )

        # Rv features a smooth transition between two linear asymptotes
        c2_rv = c2 - extinction.get("delta_c2_rv", 0.0)
        rv_term1 = hp["b_rv1"] + np.tan(np.radians(hp["theta_rv1"])) * (
            c2_rv + 0.0708
        )
        rv_term2 = hp["b_rv2"] + np.tan(np.radians(hp["theta_rv2"])) * (
            c2_rv - 1.4953
        )
        rv = np.logaddexp(rv_term1, rv_term2) + extinction.get("delta_rv", 0.0)

        # Bump Height (BH) also uses a soft-transition between two asymptotes, but inverted
        c2_bh = c2 - extinction.get("delta_c2_bh", 0.0)
        bh_term1 = -hp["b_bh1"] - np.tan(np.radians(hp["theta_bh1"])) * (
            c2_bh + 0.0143
        )
        bh_term2 = -hp["b_bh2"] - np.tan(np.radians(hp["theta_bh2"])) * (
            c2_bh - 1.4087
        )
        bh = -np.logaddexp(bh_term1, bh_term2) + extinction.get("delta_bh", 0.0)

        # Bump center (x0) and width (γ) only depend on their base values plus tight cosmic scatter.
        x0 = hp["x0_base"] + extinction.get("delta_x0", 0.0)
        gamma = hp["gamma_base"] + extinction.get("delta_gamma", 0.0)
        return c1, rv, bh, x0, gamma


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

    from jetfit.core.extinction import resolve_source_frame_transmission

    attenuation[valid] = resolve_source_frame_transmission(
        x[valid],
        extinction,
        prior.get_physical_dust_params,
        c4_key="c4",
    )
    return float(attenuation[0]) if scalar else attenuation


trotter_dust_prior = TrotterDustPrior()
