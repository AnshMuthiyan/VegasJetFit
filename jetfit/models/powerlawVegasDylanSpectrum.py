import numpy as np

from jetfit.core.utils import days_to_sec
from jetfit.models.base import (
    IntegratedFluxModel,
    ObservedSpectrumModel,
    SpectralFluxModel,
    SpectralIndexModel,
)
from jetfit.models.powerlawVegas import powerlawVegasModel


class powerlawVegasDylanSpectrumModel(powerlawVegasModel):
    """
    Hybrid VegasAfterglow/JetFit model.

    Dynamics and characteristic frequencies come from VegasAfterglow, while
    the emitted spectrum is evaluated with JetFit's analytical spectral
    smoothing (the Dylan/GS02-style prescription in ``jetfit.models.base``).
    """

    def _interpolated_details(self, t):
        """
        Interpolate VegasAfterglow detail fields to observer times ``t`` [days].
        """
        t_sec = np.atleast_1d(days_to_sec(t)).astype(float)
        details = self.vegas_model.details(float(t_sec.min()), float(t_sec.max()))

        t_obs = np.asarray(details.fwd.t_obs[0, 0, :], dtype=float)
        doppler = np.asarray(details.fwd.Doppler[0, 0, :], dtype=float)

        def observed_freq(name):
            values = np.asarray(getattr(details.fwd, name)[0, 0, :], dtype=float)
            values = values * doppler / (1.0 + self.z)
            return np.interp(t_sec, t_obs, values)

        def direct(name):
            values = np.asarray(getattr(details.fwd, name)[0, 0, :], dtype=float)
            return np.interp(t_sec, t_obs, values)

        return {
            "t_sec": t_sec,
            "t_obs": t_obs,
            "nu_a": observed_freq("nu_a"),
            "nu_m": observed_freq("nu_m"),
            "nu_c": observed_freq("nu_c"),
            "r": direct("r"),
        }

    def nu_m(self, t, **kwargs):
        return self._interpolated_details(t)["nu_m"]

    def nu_c(self, t, **kwargs):
        return self._interpolated_details(t)["nu_c"]

    def nu_a(self, t, **kwargs):
        return self._interpolated_details(t)["nu_a"]

    def radii(self, t, **kwargs):
        return self._interpolated_details(t)["r"]

    def spectrum(self, t, **kwargs):
        """
        Return Vegas characteristic frequencies with Dylan-style smoothing inputs.
        """
        details = self._interpolated_details(t)
        t_arr = np.atleast_1d(t)

        n_eff, k_eff = self.smooth(t_arr, **kwargs)
        nu_a = details["nu_a"]
        nu_m = details["nu_m"]
        nu_c = details["nu_c"]

        # Keep the peak normalization from the numerical Vegas spectrum while
        # replacing the break-shape prescription with JetFit's analytic one.
        nu_peak = np.minimum(nu_m, nu_c)
        f_peak = powerlawVegasModel.spectral_flux(self, t_arr, nu_peak)

        return {
            "nu_m": nu_m,
            "nu_c": nu_c,
            "nu_a": nu_a,
            "f_peak": f_peak,
            "p": self.p,
            "k": k_eff,
        }

    def spectral_flux(self, t, nu, fts=False, **kwargs):
        return SpectralFluxModel(**self.spectrum(t, **kwargs)).evaluate(nu, fts, None)

    def integrated_flux(self, t, lower, upper, fts=False, **kwargs):
        return IntegratedFluxModel(**self.spectrum(t, **kwargs)).evaluate(lower, upper, fts, None)

    def spectral_index(self, t, lower, upper, fts=False, **kwargs):
        return SpectralIndexModel(**self.spectrum(t, **kwargs)).evaluate(lower, upper, fts, None)

    def model(self, obs, subset=None):
        if not self.is_valid:
            return np.array([np.nan])

        return ObservedSpectrumModel(
            **self.spectrum(obs.times()),
            arrays=obs.as_arrays,
            jet=None,
        ).model(subset)
