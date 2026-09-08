from jetfit.core.utils import days_to_sec
from jetfit.models.powerlawVegas import powerlawVegasModel
import numpy as np


class powerlawVegasDylanSpectrumModel(powerlawVegasModel):
    """
    Native VegasAfterglow model with the AMPy / Dutton (2025) spectral smoother.

    The active VegasAfterglow runtime now applies the translated AMPy smooth
    synchrotron prescription in compiled code, including the local
    medium-slope-dependent smoothing needed for variable-k circumstellar media
    and the historical fast-to-slow transition smoothing that Dylan enabled
    with ``fts=True``.
    This class keeps the historical JetFit model name for backwards
    compatibility while routing the actual flux evaluation through the native
    VegasAfterglow path.

    The legacy ``spectrum()`` helper is retained only for diagnostics that want
    break-frequency summaries.  MCMC model evaluation should use the inherited
    native methods from ``powerlawVegasModel``.
    """

    def __init__(
        self,
        *args,
        smooth_fast_to_slow_transition=True,
        break_frequency_mode="eats_weighted",
        **kwargs,
    ):
        super().__init__(
            *args,
            smooth_fast_to_slow_transition=smooth_fast_to_slow_transition,
            **kwargs,
        )
        # "eats_weighted": approximate Dylan's EATS luminosity-weighted breaks.
        # "local_trace": legacy single-zone break trace used previously.
        self.break_frequency_mode = str(break_frequency_mode)

    def _resolve_transition_smoothing_flag(self, fts):
        """
        Map the historical ``fts`` keyword onto the native descriptive flag.

        The compiled VegasAfterglow path fixes this behavior at model
        construction through ``smooth_fast_to_slow_transition``.  The old
        ``fts`` keyword is accepted only as a compatibility shim.
        """
        if fts is None:
            return self.smooth_fast_to_slow_transition
        if bool(fts) != self.smooth_fast_to_slow_transition and not getattr(
            self, "_fts_override_warned", False
        ):
            # Legacy plotting paths may still pass fts=... at call time.
            # Native VegasAfterglow now owns this setting at construction, so
            # we ignore call-time mismatches to preserve backwards compatibility
            # without silently changing model behavior.
            print(
                "WARN: ignoring legacy call-time fts override; using "
                f"smooth_fast_to_slow_transition={self.smooth_fast_to_slow_transition}."
            )
            self._fts_override_warned = True
        return self.smooth_fast_to_slow_transition

    def _weighted_observed_freq(self, details, name, t_sec):
        """
        Approximate Dylan/JetSimpy EATS luminosity-weighted break frequencies.

        We use a per-cell weight proportional to ``I_nu_max * Doppler^3`` from
        VegasAfterglow details as an observer-frame emissivity proxy, then
        perform a weighted average over angular cells at fixed observer time.
        """
        return self._weighted_observed_freqs(details, (name,), t_sec)[name]

    def _weighted_observed_freqs(self, details, names, t_sec):
        """
        Compute multiple EATS-weighted observer-frame break frequencies at once.

        This keeps the science identical to ``_weighted_observed_freq`` while
        avoiding repeated reshaping and weight interpolation for ``nu_a``,
        ``nu_m``, and ``nu_c`` during posterior frequency plotting.
        """
        t_obs = np.asarray(details.fwd.t_obs, dtype=float)
        doppler = np.asarray(details.fwd.Doppler, dtype=float)
        i_nu_max = np.asarray(details.fwd.I_nu_max, dtype=float)

        weights = np.clip(i_nu_max * np.power(np.clip(doppler, 0.0, None), 3.0), 0.0, None)
        values_obs = {
            name: np.asarray(getattr(details.fwd, name), dtype=float) * doppler / (1.0 + self.z)
            for name in names
        }

        # Collapse every axis except the trailing time axis.
        t_grid = t_obs.reshape(-1, t_obs.shape[-1])
        w_grid = weights.reshape(-1, weights.shape[-1])
        v_grids = {
            name: values.reshape(-1, values.shape[-1])
            for name, values in values_obs.items()
        }

        out = {name: np.empty_like(t_sec, dtype=float) for name in names}
        for i, tgt in enumerate(t_sec):
            nums = {name: 0.0 for name in names}
            dens = {name: 0.0 for name in names}
            for row_idx, (tz, wz) in enumerate(zip(t_grid, w_grid)):
                if not np.all(np.isfinite(tz)) or not np.all(np.isfinite(wz)):
                    continue
                if tgt < tz[0] or tgt > tz[-1]:
                    continue
                w = float(np.interp(tgt, tz, wz))
                if not (np.isfinite(w) and w > 0.0):
                    continue
                for name, v_grid in v_grids.items():
                    vz = v_grid[row_idx]
                    if not np.all(np.isfinite(vz)):
                        continue
                    v = float(np.interp(tgt, tz, vz))
                    if np.isfinite(v):
                        nums[name] += w * v
                        dens[name] += w
            for name in names:
                den = dens[name]
                out[name][i] = nums[name] / den if den > 0.0 else np.nan
        return out

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

        result = {
            "t_sec": t_sec,
            "t_obs": t_obs,
            "nu_a_local_trace": observed_freq("nu_a"),
            "nu_m_local_trace": observed_freq("nu_m"),
            "nu_c_local_trace": observed_freq("nu_c"),
            "r": direct("r"),
            "break_frequency_mode": self.break_frequency_mode,
        }

        if self.break_frequency_mode == "local_trace":
            result["nu_a"] = result["nu_a_local_trace"]
            result["nu_m"] = result["nu_m_local_trace"]
            result["nu_c"] = result["nu_c_local_trace"]
            return result

        result.update(self._weighted_observed_freqs(details, ("nu_a", "nu_m", "nu_c"), t_sec))
        return result

    def nu_m(self, t, **kwargs):
        return self._interpolated_details(t)["nu_m"]

    def nu_c(self, t, **kwargs):
        return self._interpolated_details(t)["nu_c"]

    def nu_a(self, t, **kwargs):
        return self._interpolated_details(t)["nu_a"]

    def radii(self, t, **kwargs):
        return self._interpolated_details(t)["r"]

    def critical_frequencies(self, t, **kwargs):
        """Return EATS-weighted diagnostic breaks without computing peak flux."""
        details = self._interpolated_details(t)
        return {
            "nu_m": details["nu_m"],
            "nu_c": details["nu_c"],
            "nu_a": details["nu_a"],
        }

    def spectrum(self, t, **kwargs):
        """
        Return Vegas characteristic frequencies and local smoothing metadata.

        This is a diagnostic helper only.  The actual spectral evaluation used
        by MCMC now stays inside native VegasAfterglow.
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

    def spectral_flux(self, t, nu, fts=None, **kwargs):
        # Native VegasAfterglow now handles the smooth synchrotron spectrum in
        # compiled code, so keep the hot path out of the Python wrapper.
        self._resolve_transition_smoothing_flag(fts)
        return super().spectral_flux(t, nu, **kwargs)

    def integrated_flux(self, t, lower, upper, fts=None, **kwargs):
        self._resolve_transition_smoothing_flag(fts)
        return super().integrated_flux(t, lower, upper, **kwargs)

    def spectral_index(self, t, lower, upper, fts=None, **kwargs):
        self._resolve_transition_smoothing_flag(fts)
        return super().spectral_index(t, lower, upper, **kwargs)

    def model(self, obs, subset=None):
        return super().model(obs, subset=subset)
