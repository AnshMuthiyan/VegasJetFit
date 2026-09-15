import numpy as np

def apply_lyman_limit(obs_wavelengths_angstrom, z_grb, flux_array):
    """
    Applies the source-frame Lyman limit cutoff to the GRB spectrum.
    
    Physics Context:
    Neutral hydrogen in the GRB's host galaxy completely absorbs photons with 
    energies above 13.6 eV. This corresponds to a rest-frame wavelength shorter 
    than 911.6 A (the Lyman limit). Transmission for λ_rest < 911.6 A is exactly 0.0.
    
    Parameters
    ----------
    obs_wavelengths_angstrom : np.ndarray
        The observed wavelengths in Angstroms.
    z_grb : float
        The redshift of the Gamma-Ray Burst.
    flux_array : np.ndarray
        The flux array corresponding to the wavelengths.
        
    Returns
    -------
    np.ndarray
        The modified flux array with the Lyman limit applied.
    """
    # Shift observed wavelengths into the rest frame: λ_rest = λ_obs / (1 + z)
    rest_wav = obs_wavelengths_angstrom / (1.0 + z_grb)
    
    # Identify photons more energetic than the Lyman limit (< 911.6 A)
    mask = rest_wav < 911.6
    
    # Apply total neutral hydrogen absorption
    flux_array[mask] = 0.0
    
    return flux_array

def calculate_igm_transmission(z_f, delta_z_f, delta_igm):
    """
    Calculates the adjusted IGM transmission fraction for a photometric filter.
    
    Physics Context:
    The Ly-alpha forest absorption is modeled via an effective optical depth τ, 
    where T = exp(-τ). Because cosmic variance (varying cloud densities along the 
    line of sight) acts multiplicatively on τ, we shift into ln(τ) space to apply 
    our sampled scatter parameter (delta_igm) additively.
    
    Math:
    T = exp(-τ)  =>  τ = -ln(T)  =>  ln(τ) = ln(-ln(T))
    ln(τ_adjusted) = ln(-ln(T_baseline)) + delta_igm
    T_adjusted = exp(-exp(ln(τ_adjusted)))
    
    Parameters
    ----------
    z_f : float
        Filter-response-weighted mean absorber redshift.
    delta_z_f : float
        Effective redshift binwidth of the filter.
    delta_igm : float
        The sampled cosmic scatter parameter (δ_f^IGM).
        
    Returns
    -------
    float
        The adjusted transmission bounded strictly between [0.0, 1.0].
    """
    # Constants for the empirical broken power-law
    theta1 = np.radians(41.4538)
    theta2 = np.radians(79.1200)
    b1 = -0.20184
    b2 = 1.18711
    z1 = 4.10
    z2 = 6.15
    
    # Calculate baseline in ln(-ln(T)) space (Trotter Eq 3.41)
    term1 = np.exp(b1 + np.tan(theta1) * (z_f - z1))
    term2 = np.exp(b2 + np.tan(theta2) * (z_f - z2))
    ln_neg_ln_T_base = np.log(term1 + term2)
    
    # Apply the cosmic scatter sampled by the MCMC
    ln_neg_ln_T = ln_neg_ln_T_base + delta_igm
    
    # Convert back to linear transmission T
    T_adjusted = np.exp(-np.exp(ln_neg_ln_T))
    
    return np.clip(T_adjusted, 0.0, 1.0)


class TrotterIGMPrior:
    """
    Manager for the Intergalactic Medium (IGM) prior logic.
    Calculates the zero-mean Gaussian penalty for the sampled cosmic 
    scatter parameters (δ_f^IGM) across all relevant photometric filters.
    """
    def __init__(self, alpha_sigma=-0.3682, base_sigma=0.190677, z0=4.23, delta_z0=0.15):
        # Cosmic variance scaling empirical values (Trotter Table 3.6 / Eq 3.44)
        self.alpha_sigma = alpha_sigma
        self.base_sigma = base_sigma
        self.z0 = z0
        self.delta_z0 = delta_z0
        
        # Cache memory for MCMC vectorization (eliminates dictionary loops)
        self._is_cached = False
        self._filter_keys = None
        self._z_f_arr = None
        self._delta_z_f_arr = None

    def _setup_cache(self, igm_dict):
        """Builds vectorized arrays for the filters on the first MCMC step."""
        filter_names = [k.replace('delta_igm_', '') for k in igm_dict.keys() if k.startswith('delta_igm_')]
        self._filter_keys = [f'delta_igm_{f}' for f in filter_names]
        self._z_f_arr = np.array([igm_dict.get(f'z_f_{f}', 0.0) for f in filter_names])
        self._delta_z_f_arr = np.array([igm_dict.get(f'delta_z_f_{f}', 1.0) for f in filter_names])
        self._is_cached = True

    def log_prior(self, igm_dict):
        """
        Calculates the joint log-prior across all filters overlapping the Ly-alpha forest.
        
        Physics Context:
        The variance in the number of absorbing clouds follows Poisson statistics, meaning 
        the standard deviation scales inversely with the square root of the redshift binwidth 
        (Δz_f)^{-1/2}. It also scales with the intrinsic redshift evolution of the IGM (1+z_f)^{α}.
        
        Math:
        σ_f = base_sigma * (((1 + z_f) / (1 + z0))^α_σ) * ((Δz_f / Δz0)^{-1/2})
        log(P) = -0.5 * (δ_f / σ_f)^2 - 0.5 * log(2 * π * σ_f^2)
        """
        if not self._is_cached:
            self._setup_cache(igm_dict)
            
        if not self._filter_keys:
            return 0.0
            
        # Extract the sampled δ_f^IGM variables into a vectorized array
        delta_igm = np.array([igm_dict[k] for k in self._filter_keys])
        
        # Calculate theoretical standard deviation (σ_f) simultaneously for all filters (Eq 3.44)
        sigma = self.base_sigma * (((1.0 + self._z_f_arr) / (1.0 + self.z0)) ** self.alpha_sigma) * ((self._delta_z_f_arr / self.delta_z0) ** -0.5)
        variance = sigma ** 2
        
        # Reshape for broadcasting if delta_igm contains multiple walkers (2D array)
        if delta_igm.ndim > 1:
            variance = variance[:, np.newaxis]
        
        # Calculate the zero-mean Gaussian log-probability across all filters
        log_probs = -0.5 * (delta_igm ** 2) / variance - 0.5 * np.log(2 * np.pi * variance)
        
        # Sum along the filter axis (axis 0). Returns a scalar for 1D, or an array of log-probs for 2D.
        res = np.sum(log_probs, axis=0)
        return float(res) if np.isscalar(res) or res.ndim == 0 else res

