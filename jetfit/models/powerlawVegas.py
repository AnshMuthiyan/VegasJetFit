import os

import numpy as np

from jetfit.core.utils import days_to_sec

try:
    from VegasAfterglow import Model, ISM, Wind, Medium, TophatJet, GaussianJet, PowerLawJet
    from VegasAfterglow import Observer, Radiation
    try:
        from VegasAfterglow.native import gil_free
    except ImportError:
        gil_free = None
    _HAS_VEGASAFTERGLOW = True
except ImportError:
    _HAS_VEGASAFTERGLOW = False
    gil_free = None


if gil_free is not None:
    @gil_free
    def power_law_medium_native(phi, theta, r, n017, k, r0, mass_scale):
        r_safe = r if r > 1.0 else 1.0
        return mass_scale * n017 * (r_safe / r0) ** (-k)
else:
    power_law_medium_native = None


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


class powerlawVegasModel:
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

    eps_b : float
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
        Enable the AMPy / Dutton (2025) smoothing across the full
        fast-cooling to slow-cooling transition. This is the descriptive
        native VegasAfterglow name for the historical ``fts=True`` option.

    References
    ----------
    .. [1] VegasAfterglow: A Numerical Code for GRB Afterglow
    """

    _REF_RADIUS_CM = 1.0e17
    _PROTON_MASS_G = 1.67262192e-24
    _HYDROGEN_MASS_FRACTION = 0.7
    _WIND_ASTAR_NORM = 5.0e11
    
    def __init__(
        self,
        E52,
        lf0,
        theta_c,
        theta_v,
        eps_e,
        eps_b,
        p,
        z,
        dl28,
        n017,  # number density at r = 10^17 cm [cm^-3] (log scale in parameters.toml)
        k,
        hmf = 0.7,     # density power-law index: n(r) = n017 * (r/r0)^(-k)
        n_ism=None,
        A_star=None,
        k_e=None,
        k_g=None,
        jet_type='tophat',
        medium_type='powerlaw',
        ref_radius=1.0e17,
        smooth_fast_to_slow_transition=False,

    ):
        if not _HAS_VEGASAFTERGLOW:
            raise ImportError(
                "VegasAfterglow is not installed or failed to import. "
                "Install it from: https://github.com/YihanWangAstro/VegasAfterglow"
            )

        # NOTE: JetFit already converts "scale=log" parameters to linear
        # So we receive linear values here, NOT log10 values
        self.E_iso52 = E52 * 1e52  # E52 is linear multiplier, convert to erg
        self.lf0 = lf0             # Already linear (JetFit converted from log10)
        self.theta_c = theta_c
        self.theta_v = theta_v
        self.eps_e = eps_e         # Already linear (JetFit converted from log10)
        self.eps_b = eps_b         # Already linear (JetFit converted from log10)
        self.p = p
        self.z = z
        self.hmf = hmf
        self.lumi_dist = dl28 * 1e28  # dl28 is linear multiplier, convert to cm
        self.jet_type = jet_type
        self.medium_type = medium_type
        self.n017 = n017           # Already linear (JetFit converted from log10)
        self.k = k                 # Power-law index (linear scale)
        self.n_ism = n_ism
        self.A_star = A_star
        self.k_e = k_e
        self.k_g = k_g
        self.ref_radius = ref_radius  # Reference radius [cm]
        self.smooth_fast_to_slow_transition = bool(smooth_fast_to_slow_transition)


        # Initialize VegasAfterglow components
        self._setup_model()

    @classmethod
    def _native_powerlaw_astar(cls, n017, ref_radius=None):
        """Map n(r0)=n017 onto VegasAfterglow's native Wind(A_star, k) normalization."""
        r0 = cls._REF_RADIUS_CM if ref_radius is None else float(ref_radius)
        return (
            cls._HYDROGEN_MASS_FRACTION
            * cls._PROTON_MASS_G
            * float(n017)
            * r0 * r0
            / cls._WIND_ASTAR_NORM
        )


    def _convert_log_scales(self, params: dict) -> dict:
        """
        Convert known log10-scaled parameters to linear and print diagnostics.
        Returns a new dict with converted values (others kept unchanged).
        """
        log_keys = {
            "E52", "lf0", "nt", "rt", "eps_e", "eps_b",
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
        # Hot path during MCMC: keep warning I/O opt-in only.
        if os.environ.get("JETFIT_VERBOSE_PHYSICS_WARNINGS", "0") != "1":
            return

        ee = params.get("eps_e")
        eb = params.get("eps_b")
        if ee is not None and eb is not None:
            try:
                if (ee + eb) >= 1.0:
                    print(f"[vegasafterglow][WARN] eps_e + eps_b >= 1 ({ee + eb}) -> invalid (energy fractions)")
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
            "lf0": self.lf0,             # Already linear from __init__
            "theta_c": self.theta_c,
            "theta_v": self.theta_v,
            "eps_e": self.eps_e,
            "eps_b": self.eps_b,
            "p": self.p,
            "z": self.z,
            "dl28": self.lumi_dist / 1e28,
            "n017": self.n017,
            "k": self.k,
        }
        
        # Run sanity checks on the linear values
        self._sanity_check_physical(params)

        # Reference radius: 10^17 cm
        r0 = self._REF_RADIUS_CM
        # print("[vegasafterglow] Setting up VegasAfterglow Model with parameters:")
        # print(f"  E_iso52: {self.E_iso52} erg")
        # print(f"  lf0: {self.lf0}")
        # print(f"  theta_c: {self.theta_c} rad")
        # print(f"  theta_v: {self.theta_v} rad")
        # print(f"  eps_e: {self.eps_e}")
        # print(f"  eps_b: {self.eps_b}")
        # print(f"  p: {self.p}")
        # print(f"  z: {self.z}")
        # print(f"  lumi_dist: {self.lumi_dist} cm")
        # print(f"  medium_type: {self.medium_type}")
        # print(f"  jet_type: {self.jet_type}")
        # print(f"  n017: {self.n017} cm^-3 at r0={r0} cm")
        # print(f"  k: {self.k}")
        # # Single power-law density profile: n(r) = n017 * (r/r0)^(-k)
        # Returns mass density rho in g/cm^3 for VegasAfterglow Medium
        def power_law_medium(phi, theta, r):
            """
            Single power-law mass density profile.

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
            # n017 is already linear (JetFit converted from log10)
            # n(r) = n017 * (r / r0)^(-k)
            n = self.n017 * (r / r0) ** (-self.k)

            # Convert number density to mass density
            # rho = m_p * n, where m_p = 1.67262192e-24 g
            rho = self._PROTON_MASS_G * n * self._HYDROGEN_MASS_FRACTION

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
        elif self.medium_type.lower() == 'powerlaw':
            if os.environ.get("JETFIT_FORCE_PY_POWERLAW_MEDIUM") == "1":
                medium = Medium(rho=power_law_medium)
            elif os.environ.get("JETFIT_USE_VEGAS_NATIVE_POWERLAW") == "1":
                native_astar = self._native_powerlaw_astar(self.n017, r0)
                self.A_star = native_astar
                try:
                    medium = Wind(A_star=native_astar, n_ism=0.0, n0=np.inf, k_m=self.k)
                except TypeError:
                    medium = Medium(rho=power_law_medium)
            elif power_law_medium_native is not None:
                medium = Medium(
                    rho=power_law_medium_native(
                        n017=self.n017,
                        k=self.k,
                        r0=r0,
                        mass_scale=self._PROTON_MASS_G * self._HYDROGEN_MASS_FRACTION,
                    )
                )
            else:
                medium = Medium(rho=power_law_medium)
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
            eps_B=self.eps_b,
            p=self.p,
            smooth_fast_to_slow_transition=self.smooth_fast_to_slow_transition,
        )

        # Create the model - Note: Model expects (jet, medium, observer, fwd_rad)
        # print(f"DEBUG: Creating VegasAfterglow Model...")
        try:
            self.vegas_model = Model(jet=jet, medium=medium, observer=observer, fwd_rad=radiation)
            # print(f"DEBUG: Model created successfully!")
        except Exception as e:
            print(f"DEBUG: Model creation FAILED: {e}")
            raise

    @property
    def is_valid(self) -> bool:
        """Check if model parameters are physically valid."""
        valid = (
            (self.eps_b + self.eps_e) < 1.0 and
            self.p >= 2.0 and
            self.theta_c > 0 and
            self.lf0 > 1
        )
        # if not valid:
            # print(f"DEBUG: Model is_valid=False:")
            # print(f"  eps_b + eps_e = {self.eps_b + self.eps_e} < 1.0? {(self.eps_b + self.eps_e) < 1.0}")
            # print(f"  p = {self.p} >= 2.0? {self.p >= 2.0}")
            # print(f"  theta_c = {self.theta_c} > 0? {self.theta_c > 0}")
            # print(f"  lf0 = {self.lf0} > 1? {self.lf0 > 1}")
        return valid

    def nu_m(self, t, **kwargs):
        """
        Calculate the minimum synchrotron frequency (cooling break).
        
        This extracts nu_m from VegasAfterglow's details.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray of float
            Minimum synchrotron frequency [Hz].
        """
        t_sec = days_to_sec(t)
        t_sec = np.atleast_1d(t_sec)

        try:
            # Get details over the time range - details() is a method call with (t_min, t_max)
            details = self.vegas_model.details(t_sec.min(), t_sec.max())
            
            # Extract nu_m from the model's details
            # Shape is typically [phi, theta, time] - take the on-axis value
            nu_m = np.asarray(details.fwd.nu_m[0,0,:]*details.fwd.Doppler[0,0,:]/(1+self.z))
            
            # Get radius and time arrays for comparison with FireballModel
            r_vegas = np.asarray(details.fwd.r[0, 0, :])
            t_obs_vegas = np.asarray(details.fwd.t_obs[0, 0, :])
            
            # Find index closest to requested time for debug output
            idx_mid = len(t_obs_vegas) // 2
            # print(f"Radius VegasAfterglow {r_vegas[idx_mid]:.3e} cm at t_obs={t_obs_vegas[idx_mid]:.3e} s")
            
            # print("[vegasafterglow] nu_m extraction debug (at t_min, on-axis):")
            # print(f"  nu_m: {nu_m[14:18]} Hz")
            # print(f"  t_obs: {details.fwd.t_obs[0,0,14:18]} s, r: {details.fwd.r[0,0,14:18]} cm")
            # print(f"  t_src: {details.fwd.t_comv[0,0,14:18]*details.fwd.Gamma[0,0,14:18]} s")
            # print(f"  nu_mBAd: {details.fwd.nu_m[0,0,14:18]} Hz, B_comv: {details.fwd.B_comv[0,0,14:18]} G, gamma_m: {details.fwd.gamma_m[0,0,14:18]}")
            # print(f"  Doppler: {details.fwd.Doppler[0,0,14:18]}, z: {self.z}")
            
            # Interpolate to match requested times if needed
            if len(nu_m) != len(t_sec):
                t_details = np.asarray(details.fwd.t_obs[0, 0, :])
                nu_m = np.interp(t_sec, t_details, nu_m)
        except Exception as e:
            raise RuntimeError(f"Failed to extract nu_m from VegasAfterglow: {e}")

        return np.atleast_1d(nu_m)
    
    def nu_c(self, t, **kwargs):
        """
        Calculate the cooling frequency.
        
        This extracts nu_c from VegasAfterglow's details.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray of float
            Cooling frequency [Hz].
        """
        t_sec = days_to_sec(t)
        t_sec = np.atleast_1d(t_sec)

        try:
            # Get details over the time range - details() is a method call with (t_min, t_max)
            details = self.vegas_model.details(t_sec.min(), t_sec.max())
            
            # Extract nu_c from the model's details
            nu_c = np.asarray(details.fwd.nu_c[0,0,:]*details.fwd.Doppler[0,0,:]/(1+self.z))
            
            # Interpolate to match requested times if needed
            if len(nu_c) != len(t_sec):
                t_details = np.asarray(details.fwd.t_obs[0, 0, :])
                nu_c = np.interp(t_sec, t_details, nu_c)
        except Exception as e:
            raise RuntimeError(f"Failed to extract nu_c from VegasAfterglow: {e}")

        return np.atleast_1d(nu_c)
    
    def nu_a(self, t, **kwargs):
        """
        Calculate the self-absorption frequency.
        
        This extracts nu_a from VegasAfterglow's details.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray of float
            Self-absorption frequency [Hz].
        """
        t_sec = days_to_sec(t)
        t_sec = np.atleast_1d(t_sec)
        # pee = self.pee 

        try:
            # Get details over the time range - details() is a method call with (t_min, t_max)
            details = self.vegas_model.details(t_sec.min(), t_sec.max())
            
            # Extract nu_a from the model's details
            nu_a = np.asarray(details.fwd.nu_a[0,0,:]*details.fwd.Doppler[0,0,:]/(1+self.z))
            
            # Interpolate to match requested times if needed
            if len(nu_a) != len(t_sec):
                t_details = np.asarray(details.fwd.t_obs[0, 0, :])
                nu_a = np.interp(t_sec, t_details, nu_a)
        except Exception as e:
            raise RuntimeError(f"Failed to extract nu_a from VegasAfterglow: {e}")

        return np.atleast_1d(nu_a)
    
    def spectrum(self, t, **kwargs):
        """
        Return a dictionary of spectral characteristics at given times.
        ...
        """
        # Get density parameters
        n_eff, k_eff = self.smooth(t, **kwargs)
        
        # Get break frequencies
        nu_m = self.nu_m(t, **kwargs)
        nu_c = self.nu_c(t, **kwargs)
        nu_a = self.nu_a(t, **kwargs)
        
        # Compute f_peak by evaluating flux at nu_m (the spectral peak)
        # In slow cooling (nu_m < nu_c), peak is at nu_m
        # In fast cooling (nu_c < nu_m), peak is at nu_c
        nu_peak = np.minimum(nu_m, nu_c)  # Peak is at min(nu_m, nu_c)
        f_peak = self.spectral_flux(t, nu_peak)
        
        return {
            'nu_m': nu_m,
            'nu_c': nu_c,
            'nu_a': nu_a,
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
        elif self.medium_type.lower() == 'powerlaw':
            t_arr = np.atleast_1d(t)
            return np.full_like(t_arr, self.n017), np.full_like(t_arr, self.k)
        elif self.medium_type.lower() == 'ism':
            t_arr = np.atleast_1d(t)
            return np.full_like(t_arr, self.n_ism), np.zeros_like(t_arr)
        elif self.medium_type.lower() == 'wind':
            t_arr = np.atleast_1d(t)
            # Wind: k=2 always
            return np.full_like(t_arr, self.A_star), np.full_like(t_arr, 2.0)
        else:
            raise ValueError(f"Unknown medium_type '{self.medium_type}' in smooth(). "
                           f"Supported types: 'powerlaw', 'ism', 'wind', 'smooth_broken'")
    
    def radii(self, t, **kwargs):
        """
        Return blast wave radius at given times.
        
        Extracts the actual computed radius from VegasAfterglow's details.
        
        Parameters
        ----------
        t : np.ndarray of float
            Observer times [days].
            
        Returns
        -------
        np.ndarray
            Blast wave radius [cm].
        """
        t_sec = days_to_sec(t)
        t_sec = np.atleast_1d(t_sec)
        
        try:
            # Get details over the time range
            details = self.vegas_model.details(t_sec.min(), t_sec.max())
            
            # Extract radius from VegasAfterglow (lab frame, in cm)
            # Shape is [phi, theta, time] - take on-axis value
            r = np.asarray(details.fwd.r[0, 0, :])
            
            # Interpolate to match requested times if needed
            if len(r) != len(t_sec):
                t_details = np.asarray(details.fwd.t_obs[0, 0, :])
                r = np.interp(t_sec, t_details, r)
            
            return r
        except Exception as e:
            raise RuntimeError(f"Failed to extract radius from VegasAfterglow: {e}")

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
        # Use spectral-index approximation.
        # Reuse lower-band flux to avoid an extra VegasAfterglow call.
        sflux = self.spectral_flux(t, lower)
        beta = self.spectral_index(t, lower, upper, flux_lower=sflux)

        return 1e-26 * (
            (sflux * lower / (beta + 1)) *
            (((upper / lower) ** (beta + 1)) - 1)
        )

    def spectral_index(self, t, lower, upper, flux_lower=None, **kwargs):
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
        if flux_lower is None:
            flux_lower = self.spectral_flux(t, lower)
        flux_upper = self.spectral_flux(t, upper)

        with np.errstate(divide='ignore', invalid='ignore'):
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
