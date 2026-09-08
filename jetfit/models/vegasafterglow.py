import numpy as np

from jetfit.core.utils import days_to_sec
from jetfit.models.jet_energy import resolve_e_iso52, resolve_gamma0_axis
from jetfit.models.vegas_resolution import (
    model_kwargs_with_resolution,
    resolve_vegas_resolutions,
)

try:
    from VegasAfterglow import Model, ISM, Wind, Medium, TophatJet, GaussianJet, PowerLawJet
    try:
        from VegasAfterglow import SmoothBrokenPowerLawMedium
    except ImportError:
        SmoothBrokenPowerLawMedium = None
    from VegasAfterglow import Observer, Radiation
    _HAS_VEGASAFTERGLOW = True
except ImportError:
    _HAS_VEGASAFTERGLOW = False
    SmoothBrokenPowerLawMedium = None


"""
Adapter for integrating VegasAfterglow with JetFit's MCMC infrastructure.

This module wraps the VegasAfterglow numerical simulation package and 
adapts it for use with JetFit's MCMC framework.

Notes
-----
VegasAfterglow is a high-performance numerical afterglow simulator that
computes radiation from relativistic blast waves. It supports various jet
structures (tophat, Gaussian, power-law) and circumburst media (ISM, wind).

The model is computationally intensive compared to analytical models, so
multiprocessing is recommended for MCMC fitting.

References
----------
.. [1] VegasAfterglow: https://github.com/YihanWangAstro/VegasAfterglow
"""


class VegasAfterglowModel:
    """
    Adapter for the VegasAfterglow numerical afterglow simulator.

    Parameters
    ----------
    E_iso52 : float
        Isotropic equivalent energy [erg] normalized to e52.

    lf0 : float
        Initial Lorentz factor (dimensionless).

    theta_c : float
        Half-opening angle of the jet core [rad].

    theta_v : float
        Viewing angle [rad].

    n_ism : float, optional
        ISM number density [cm^-3]. Use for constant density medium.

    A_star : float, optional
        Wind density parameter. Use for wind medium (rho = A_star / r^2).

    eps_e : float
        Fraction of shock energy in electrons. Must be in [0, 1].

    eps_B : float
        Fraction of shock energy in magnetic field. Must be in [0, 1].

    p : float
        Electron power-law index (dimensionless). Typically p >= 2.

    z : float
        Redshift.

    lumi_dist : float
        Luminosity distance [cm].

    jet_type : str, optional, default='tophat'
        Type of jet structure: 'tophat', 'gaussian', or 'powerlaw'.

    medium_type : str, optional, default='ism'
        Type of circumburst medium: 'ism' or 'wind'.

    k_e : float, optional
        Energy power-law index for structured jets. Default=None (tophat).

    k_g : float, optional
        Lorentz factor power-law index for structured jets. Default=None.

    smooth_fast_to_slow_transition : bool, optional
        Enable the compiled AMPy / Dutton (2025) fast-to-slow transition
        spectral smoothing in native VegasAfterglow. This is the descriptive
        native name for the historical ``fts=True`` option used in the local
        workflow.

    References
    ----------
    .. [1] VegasAfterglow: A Numerical Code for GRB Afterglow
    """
    def __init__(
        self,
        E52=None,
        lf0=None,
        theta_c=None,
        theta_v=None,
        eps_e=None,
        eps_B=None,
        p=None,
        z=None,
        dl28=None,
        nt=None, #log particle number density at transition radius
        rt=None, #transition radius in log cm
        k1=None, #inner density power-law index
        k2=None, #outer density power-law index
        sn=None, #smoothing parameter for smoothly broken power-law density profile
        jet_type='tophat',
        medium_type='smooth_broken',
        n_ism=None,
        A_star=None,
        k_e=None,
        k_g=None,
        smooth_fast_to_slow_transition=True,
        E_j_52=None,
        E_j_core_52=None,
        Gamma_0_core_avg=None,
        vegas_resolutions=None,
        vegas_resolution_phi=None,
        vegas_resolution_theta=None,
        vegas_resolution_t=None,
    ):
        if not _HAS_VEGASAFTERGLOW:
            raise ImportError(
                "VegasAfterglow is not installed or failed to import. "
                "Install it from: https://github.com/YihanWangAstro/VegasAfterglow"
            )

        # NOTE: JetFit already converts "scale=log" parameters to linear
        # So we receive linear values here, NOT log10 values
        self.E_j_52 = E_j_52
        self.E_j_core_52 = E_j_core_52
        self.Gamma_0_core_avg = Gamma_0_core_avg
        self.E_iso52 = resolve_e_iso52(
            E52=E52,
            E_j_52=E_j_52,
            E_j_core_52=E_j_core_52,
            jet_type=jet_type,
            theta_c=theta_c,
            k_e=k_e,
        ) * 1e52  # internal on-axis isotropic-equivalent energy [erg]
        self.lf0 = resolve_gamma0_axis(
            lf0=lf0,
            Gamma_0_core_avg=Gamma_0_core_avg,
            jet_type=jet_type,
            theta_c=theta_c,
            k_g=k_g,
        )
        self.theta_c = theta_c
        self.theta_v = theta_v
        self.eps_e = eps_e         # Already linear (JetFit converted from log10)
        self.eps_B = eps_B         # Already linear (JetFit converted from log10)
        self.p = p
        self.z = z
        self.nt = nt               # Still log10 (used in smooth_broken_medium)
        self.rt = rt               # Still log10 (used in smooth_broken_medium)
        self.k1 = k1
        self.k2 = k2
        self.sn = sn
        self.lumi_dist = dl28 * 1e28  # dl28 is linear multiplier, convert to cm
        self.jet_type = jet_type
        self.medium_type = medium_type
        self.n_ism = n_ism
        self.A_star = A_star
        self.k_e = k_e
        self.k_g = k_g
        self.smooth_fast_to_slow_transition = bool(smooth_fast_to_slow_transition)
        self._default_ref_radius = 1.0e17  # Reference radius [cm]
        self.vegas_resolutions = resolve_vegas_resolutions(
            vegas_resolutions=vegas_resolutions,
            vegas_resolution_phi=vegas_resolution_phi,
            vegas_resolution_theta=vegas_resolution_theta,
            vegas_resolution_t=vegas_resolution_t,
        )

        # Initialize VegasAfterglow components
        self._setup_model()


    def _convert_log_scales(self, params: dict) -> dict:
        """
        Convert known log10-scaled parameters to linear and print diagnostics.
        Returns a new dict with converted values (others kept unchanged).
        """
        log_keys = {
            "E52", "lf0", "nt", "rt", "eps_e", "eps_B",
            "g_host", "r_host", "dl28"
        }

        converted = {}
        print("[vegasafterglow] _convert_log_scales: received parameter dump")
        for k, v in params.items():
            try:
                val = float(v)
            except Exception:
                converted[k] = v
                print(f"[vegasafterglow]  {k}: non-numeric, kept as-is: {v}")
                continue

            if k in log_keys:
                lin = 10.0 ** val
                converted[k] = lin
                print(f"[vegasafterglow]  {k}: received={val} (log10) -> linear={lin}")
            else:
                converted[k] = val
                print(f"[vegasafterglow]  {k}: received={val} (kept)")

        # store for debugging/inspection
        self._params_raw = dict(params)
        self._params_linear = dict(converted)
        return converted

    def _sanity_check_physical(self, params: dict) -> None:
        """Print warnings for common physical constraint violations."""
        # Hot path during wide-prior MCMC: keep warning I/O opt-in only.
        # The checks remain useful for debugging, but unconditional printing
        # can dominate logs and slow failed walker proposals.
        import os
        if os.environ.get("JETFIT_VERBOSE_PHYSICS_WARNINGS", "0") != "1":
            return

        ee = params.get("eps_e")
        eb = params.get("eps_B")
        if ee is not None and eb is not None:
            try:
                if (ee + eb) >= 1.0:
                    print(f"[vegasafterglow][WARN] eps_e + eps_B >= 1 ({ee + eb}) -> invalid (energy fractions)")
            except Exception:
                pass

        pval = params.get("p")
        if pval is not None:
            try:
                if pval < 2.0:
                    print(f"[vegasafterglow][WARN] p < 2 ({pval}) -> unphysical electron index")
            except Exception:
                pass

        lf0 = params.get("lf0")
        if lf0 is not None:
            try:
                if lf0 <= 1.0:
                    print(f"[vegasafterglow][WARN] lf0 <= 1 ({lf0}) -> Lorentz factor must be > 1")
            except Exception:
                pass

        theta_c = params.get("theta_c")
        if theta_c is not None:
            try:
                if theta_c <= 0.0:
                    print(f"[vegasafterglow][WARN] theta_c <= 0 ({theta_c}) -> must be > 0")
            except Exception:
                pass


    def _setup_model(self):
        """Initialize the VegasAfterglow model with current parameters."""

        # Build params dict from instance attributes (already converted in __init__)
        params = {
            "E52": self.E_iso52 / 1e52,  # Convert back for logging
            "E_j_52": self.E_j_52,
            "lf0": self.lf0,             # Already linear from __init__
            "theta_c": self.theta_c,
            "theta_v": self.theta_v,
            "eps_e": self.eps_e,
            "eps_B": self.eps_B,
            "p": self.p,
            "z": self.z,
            "dl28": self.lumi_dist / 1e28,
            "nt": self.nt,
            "rt": self.rt,
            "k1": self.k1,
            "k2": self.k2,
            "sn": self.sn,
        }
        
        # Run sanity checks on the linear values
        self._sanity_check_physical(params)

        
        # print(f"DEBUG: Setting up model with parameters:")
        # print(f"  E_iso52 = {self.E_iso52:.3e} erg")
        # print(f"  lf0 = {self.lf0:.2f}")
        # print(f"  theta_c = {self.theta_c:.4f} rad")
        # print(f"  theta_v = {self.theta_v:.4f} rad")
        # print(f"  eps_e = {self.eps_e:.4f}")
        # print(f"  eps_B = {self.eps_B:.4e}")
        # print(f"  p = {self.p:.2f}")
        # print(f"  medium_type = {self.medium_type}")

        # Smoothly-broken power-law density profile (no angular dependence).
        # Returns mass density rho in g/cm^3 for VegasAfterglow Medium
        def smooth_broken_medium(phi, theta, r):
            """
            Smoothly-broken power-law mass density profile.

            Parameters
            ----------
            phi : float or np.ndarray
                Azimuthal angle (not used in this profile)
            theta : float or np.ndarray
                Polar angle (not used in this profile)
            r : float or np.ndarray
                Radius [cm]

            Returns
            -------
            float or np.ndarray
                Mass density [g/cm^3]
            """
            # Convert from log units
            n0t = 10**self.nt  # cm^-3
            rt = 10**self.rt   # cm
            
            # Rename for convenience
            s, k1, k2 = self.sn, self.k1, self.k2

            x = r / rt

            # Calculate the effective number densities [cm^-3]
            n = n0t * (2 ** (1 / s)) * (
                x ** (k1 * s) + x ** (k2 * s)
            ) ** -(1 / s)

            # Calculate the effective density power-law indices
            k_eff_num = k1 * x ** (k1 * s) + k2 * x ** (k2 * s)
            k_eff_den = x ** (k1 * s) + x ** (k2 * s)
            k_eff = k_eff_num / k_eff_den

            # Number density normalized to `rt`
            n0 = n * (r / rt) ** k_eff

            # Convert number density to mass density (assuming fully ionized hydrogen)
            # rho = m_p * n, where m_p = 1.67262192e-24 g
            X = 0.7 # Hydrogen mass fraction
            m_p = 1.67262192e-24  # proton mass in g
            rho = m_p * n0 * X

            return rho

        # Create medium
        if self.medium_type.lower() == 'ism':
            if self.n_ism is None:
                raise ValueError("n_ism must be specified for ISM medium")
            medium = ISM(n_ism=self.n_ism)
        elif self.medium_type.lower() == 'wind':
            if self.A_star is None:
                raise ValueError("A_star must be specified for wind medium")
            medium = Wind(A_star=self.A_star)
        elif self.medium_type.lower() == 'smooth_broken':
            n0t = 10**self.nt  # cm^-3
            rt = 10**self.rt   # cm
            if SmoothBrokenPowerLawMedium is not None:
                medium = SmoothBrokenPowerLawMedium(
                    n_t=n0t,
                    r_t=rt,
                    k1=self.k1,
                    k2=self.k2,
                    s_n=self.sn,
                    X_h=0.7,
                )
            else:
                # Fallback for older VegasAfterglow builds lacking native support.
                medium = Medium(rho=smooth_broken_medium)
        else:
            raise ValueError(f"Unknown medium_type: {self.medium_type}")

        # Create jet
        if self.jet_type.lower() == 'tophat':
            jet = TophatJet(
                theta_c=self.theta_c,
                E_iso=self.E_iso52,
                Gamma0=self.lf0
            )
        elif self.jet_type.lower() == 'gaussian':
            jet = GaussianJet(
                theta_c=self.theta_c,
                E_iso=self.E_iso52,
                Gamma0=self.lf0
            )
        elif self.jet_type.lower() == 'powerlaw':
            if self.k_e is None or self.k_g is None:
                raise ValueError("k_e and k_g must be specified for powerlaw jet")
            jet = PowerLawJet(
                theta_c=self.theta_c,
                E_iso=self.E_iso52,
                Gamma0=self.lf0,
                k_e=self.k_e,
                k_g=self.k_g
            )
        else:
            raise ValueError(f"Unknown jet_type: {self.jet_type}")

        # Create observer and radiation
        observer = Observer(
            lumi_dist=self.lumi_dist,
            z=self.z,
            theta_obs=self.theta_v
        )

        radiation = Radiation(
            eps_e=self.eps_e,
            eps_B=self.eps_B,
            p=self.p,
            smooth_fast_to_slow_transition=self.smooth_fast_to_slow_transition,
        )

        # Create the model - Note: Model expects (jet, medium, observer, fwd_rad)
        # print(f"DEBUG: Creating VegasAfterglow Model...")
        try:
            self.vegas_model = Model(
                **model_kwargs_with_resolution(
                    jet=jet,
                    medium=medium,
                    observer=observer,
                    radiation=radiation,
                    resolutions=self.vegas_resolutions,
                )
            )
            # print(f"DEBUG: Model created successfully!")
        except Exception as e:
            print(f"DEBUG: Model creation FAILED: {e}")
            raise

    @property
    def is_valid(self) -> bool:
        """Check if model parameters are physically valid."""
        valid = (
            (self.eps_B + self.eps_e) < 1.0 and
            self.p >= 2.0 and
            self.theta_c > 0 and
            self.lf0 > 1
        )
        # if not valid:
            # print(f"DEBUG: Model is_valid=False:")
            # print(f"  eps_B + eps_e = {self.eps_B + self.eps_e} < 1.0? {(self.eps_B + self.eps_e) < 1.0}")
            # print(f"  p = {self.p} >= 2.0? {self.p >= 2.0}")
            # print(f"  theta_c = {self.theta_c} > 0? {self.theta_c > 0}")
            # print(f"  lf0 = {self.lf0} > 1? {self.lf0 > 1}")
        return valid

    def nu_m(self, t, **kwargs):
        """
        Calculate the minimum synchrotron frequency (cooling break).
        
        This is an analytical approximation since VegasAfterglow is numerical.
        Uses standard synchrotron formulas for electron injection frequency.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray of float
            Minimum synchrotron frequency [Hz].
        """
        # Placeholder: return typical nu_m scaling
        # nu_m ~ eps_e^2 * eps_B^(1/2) * (1+z) * t^(-3/2) for ISM
        # This is a rough approximation - VegasAfterglow computes spectra numerically
        t_sec = days_to_sec(t)
        
        # Rough scaling (should be calibrated to actual model output)
        nu_m_0 = 1e14  # Typical scale [Hz]
        return nu_m_0 * (t_sec / 1e5)**(-1.5)
    
    def nu_c(self, t, **kwargs):
        """
        Calculate the cooling frequency.
        
        This is an analytical approximation since VegasAfterglow is numerical.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray of float
            Cooling frequency [Hz].
        """
        # Placeholder: return typical nu_c scaling
        # nu_c ~ eps_B^(-3/2) * (1+z) * t^(-1/2) for ISM
        t_sec = days_to_sec(t)
        
        # Rough scaling
        nu_c_0 = 1e16  # Typical scale [Hz]
        return nu_c_0 * (t_sec / 1e5)**(-0.5)
    
    def nu_a(self, t, **kwargs):
        """
        Calculate the self-absorption frequency.
        
        This is an analytical approximation since VegasAfterglow is numerical.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray of float
            Self-absorption frequency [Hz].
        """
        # Placeholder: return typical nu_a scaling
        # nu_a scaling depends on geometry and density profile
        t_sec = days_to_sec(t)
        
        # Rough scaling (decays with time)
        nu_a_0 = 1e10  # Typical scale [Hz]
        return nu_a_0 * (t_sec / 1e5)**(-1.2)
    
    def spectrum(self, t, **kwargs):
        """
        Return a dictionary of spectral characteristics at given times.
        
        This provides the same interface as analytical models for compatibility
        with JetFit's plotting routines.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        dict
            Dictionary with keys: 'nu_m', 'nu_c', 'nu_a', 'f_peak', 'p', 'k'
            containing the characteristic frequencies [Hz], peak flux, and
            spectral parameters at each time.
        """
        # Get density parameters
        n_eff, k_eff = self.smooth(t, **kwargs)
        
        # Estimate peak flux (very rough approximation)
        # F_peak ~ (eps_B * eps_e^2)^(1/2) * E / (d_L^2 * t)
        t_sec = days_to_sec(t)
        t_arr = np.atleast_1d(t_sec)
        
        # Rough peak flux scaling
        f_peak_scale = 1e-3  # mJy, typical scale
        f_peak = f_peak_scale * (t_arr / 1e5)**(-1.0)
        
        return {
            'nu_m': self.nu_m(t, **kwargs),
            'nu_c': self.nu_c(t, **kwargs),
            'nu_a': self.nu_a(t, **kwargs),
            'f_peak': f_peak,
            'p': self.p,
            'k': k_eff,
        }
    
    def smooth(self, t, **kwargs):
        """
        Return effective density normalization and power-law index.
        
        For VegasAfterglow with smooth_broken medium, returns the
        density parameters at the transition radius.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        n_eff : np.ndarray
            Effective number density [cm^-3] at transition radius.
        k_eff : np.ndarray
            Effective density power-law index.
        """
        # For smooth_broken profile, return fixed values at rt
        if self.medium_type.lower() == 'smooth_broken':
            n0t = 10**self.nt  # Number density at transition radius
            # At the transition radius, k_eff is approximately the average
            k_avg = (self.k1 + self.k2) / 2.0
            
            # Return arrays of constant values matching input size
            t_arr = np.atleast_1d(t)
            n_eff = np.full_like(t_arr, n0t)
            k_eff = np.full_like(t_arr, k_avg)
            return n_eff, k_eff
        elif self.medium_type.lower() == 'ism':
            t_arr = np.atleast_1d(t)
            return np.full_like(t_arr, self.n_ism), np.zeros_like(t_arr)
        elif self.medium_type.lower() == 'wind':
            t_arr = np.atleast_1d(t)
            # Wind: k=2 always
            return np.full_like(t_arr, self.A_star), np.full_like(t_arr, 2.0)
        else:
            t_arr = np.atleast_1d(t)
            return np.full_like(t_arr, np.nan), np.full_like(t_arr, np.nan)
    
    def radii(self, t, **kwargs):
        """
        Return blast wave radius at given times.
        
        This is a rough estimate since VegasAfterglow computes it numerically.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray
            Blast wave radius [cm].
        """
        # Rough Sedov-Taylor or Blandford-McKee scaling
        # R ~ (E / n)^(1/5) * c * t^(2/5)  for ISM
        # or R ~ c * t * Gamma0 for early times
        t_sec = days_to_sec(t)
        
        # Very rough approximation
        c = 2.998e10  # cm/s
        R = c * t_sec * np.sqrt(self.lf0)  # Rough ballpark
        return R
    
    @property
    def ref_radius(self):
        """
        Return the reference/transition radius.
        
        Returns
        -------
        float
            Reference radius [cm].
        """
        if self.medium_type.lower() == 'smooth_broken':
            return 10**self.rt  # Transition radius in cm
        else:
            return self._default_ref_radius

    def spectral_flux(self, t, nu, **kwargs):
        """
        Calculate spectral flux density at given times and frequencies.

        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].

        nu : float or np.ndarray of float
            Frequencies [Hz].

        Returns
        -------
        np.ndarray of float
            Spectral flux density [mJy].
        """
        t_sec = days_to_sec(t)
        
        # Ensure inputs are arrays
        t_sec = np.atleast_1d(t_sec)
        nu = np.atleast_1d(nu)
        
        # VegasAfterglow's flux_density requires equal-length time and freq arrays
        # If they're different sizes, we need to match them up properly
        if t_sec.size == nu.size:
            # Simple case: same size, compute flux_density directly
            flux_dict = self.vegas_model.flux_density(t_sec, nu)
            flux_cgs = np.asarray(flux_dict.total)
        elif nu.size == 1:
            # Single frequency, multiple times
            nu_array = np.full_like(t_sec, nu[0])
            flux_dict = self.vegas_model.flux_density(t_sec, nu_array)
            flux_cgs = np.asarray(flux_dict.total)
        elif t_sec.size == 1:
            # Single time, multiple frequencies
            t_array = np.full_like(nu, t_sec[0])
            flux_dict = self.vegas_model.flux_density(t_array, nu)
            flux_cgs = np.asarray(flux_dict.total)
        else:
            # Different sizes: this means we have paired (t, nu) observations
            # Pad the shorter array or use flux_density_grid
            raise ValueError(
                f"Time array size ({t_sec.size}) and frequency array size ({nu.size}) "
                f"must match or one must be scalar. Use flux_density_grid for grid output."
            )
        
        # Convert to mJy: 1 mJy = 1e-26 erg/cm^2/s/Hz
        return flux_cgs / 1e-26

    def integrated_flux(self, t, lower, upper, **kwargs):
        """
        Calculate integrated flux over a frequency band.

        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].

        lower, upper : float or np.ndarray of float
            Frequency integration bounds [Hz].

        Returns
        -------
        np.ndarray of float
            Integrated flux [erg cm^-2 s^-1].
        """
        # Use numerical integration over the band
        # For now, use spectral index approximation
        sflux = self.spectral_flux(t, lower)
        beta = self.spectral_index(t, lower, upper)

        return 1e-26 * (
            (sflux * lower / (beta + 1)) *
            (((upper / lower) ** (beta + 1)) - 1)
        )

    def spectral_index(self, t, lower, upper, **kwargs):
        # print("Hi")
        """
        Calculate spectral index between two frequencies.

        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].

        lower, upper : float or np.ndarray of float
            Frequency bounds [Hz].

        Returns
        -------
        np.ndarray of float
            Spectral index (dimensionless).
        """
        flux_lower = self.spectral_flux(t, lower)
        flux_upper = self.spectral_flux(t, upper)

        return np.log10(flux_upper / flux_lower) / np.log10(upper / lower)

    def model(self, obs, subset=None):
        """
        Model an Observation object.

        Parameters
        ----------
        obs : Observation
            The observational data.

        subset : np.ndarray of bool, optional
            Subset of data to model.

        Returns
        -------
        np.ndarray of float
            Modeled observational data.
        """
        if not self.is_valid:
            return np.array([np.nan])

        res = np.full(obs.as_arrays.times.size, np.nan)

        # Model spectral flux
        if (sfm := obs.as_arrays.sflux_loc).any():
            if subset is not None:
                sfm = np.logical_and(sfm, subset)
            res[sfm] = self.spectral_flux(
                obs.times()[sfm], obs.freqs()[sfm]
            )

        # Model integrated flux
        if (ifm := obs.as_arrays.iflux_loc).any():
            if subset is not None:
                ifm = np.logical_and(ifm, subset)
            res[ifm] = self.integrated_flux(
                obs.times()[ifm],
                obs.int_lowers()[ifm],
                obs.int_uppers()[ifm]
            )

        # Model spectral indices
        if (sim := obs.as_arrays.sindex_loc).any():
            if subset is not None:
                sim = np.logical_and(sim, subset)
            res[sim] = self.spectral_index(
                obs.times()[sim],
                obs.int_lowers()[sim],
                obs.int_uppers()[sim]
            )

        return res
