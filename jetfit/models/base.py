import math

import numpy as np
import astropy.units as u
import astropy.constants as const

from scipy import optimize
from numba import njit

from jetfit.core.structs import SpectralFlux, IntegratedFlux, SpectralIndex
from jetfit.core.utils import crosses, hill

"""
Base models


Notes
-----
Although it would be much easier and much, much cleaner to simply
write the spectral functions (f_peak, nu_a, nu_m, nu_c) in terms
of their fundamental physics (magnetic field, Lorentz factor, and
radius), it would also be significantly slower. Since these methods
are intended to be used with MCMC, I prioritized performance over
simplicity. The current implementations of the spectral functions
take mirco-seconds to execute.

Numba: https://numba.pydata.org/numba-doc/dev/user/5minguide.html.
Many methods make use of the @njit decorator. This compiles the
decorated methods into machine code. There are some restrictions
on the methods that use this. See the link above for details.
"""


# Useful constants and conversions
SoL     = 2.99792458e+10  # [cm s-1]
MassP   = 1.67262192e-24  # [g]
MassE   = 9.1093837e-28   # [g]
SigmaT  = 6.6524e-25      # [cm2]
ECharge = 4.8032e-10      # [g1/2 cm3/2 s-1]
CGS2MJY = 1.0e26
DAY2SEC = 86_400.0        # [s d-1]


# <editor-fold desc="Empirical Models">

# </editor-fold>

# <editor-fold desc="Blast Wave Properties">
# noinspection PyPep8Naming
class BlastWaveModel2:
    """"""
    def __init__(self, E, lf0, n0, k):
        self.E = E
        self.lf0 = lf0
        self.n0 = n0
        self.k = k

    def gamma(self, t_src, adiabatic):
        """ The bulk Lorentz factor. """
        return gamma(
            self.E / self.lf0, self.n0, self.k, t_src, adiabatic=adiabatic
        )

    def energy_loss(self, t_src):
        """ The fractional energy remaining after radiative cooling ends. """
        return self.gamma(t_src, adiabatic=False) / self.lf0


# noinspection PyPep8Naming
@njit(cache=True)
def energy_ad(n0, k, gammaB, R):
    """
    Returns the adiabatic comoving energy [erg].

    Parameters
    ----------
    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray
        The density power-law index.

    gammaB : float or np.ndarray
        The bulk Lorentz factor.

    R : float or np.ndarray
        The blast wave radius [cm].

    Returns
    -------
    float or np.ndarray of float
        The energy [erg].
    """
    # 0.07 ~= 16 * pi * MassP * SoL**2
    return 0.075562 / (17.0 - 4.0 * k) * n0 * gammaB ** 2 * R ** (3.0 - k)


# noinspection PyPep8Naming
@njit(cache=True)
def energy_rad(n0, k, gammaB, gamma0, R):
    """
    Returns the radiative comoving energy [erg].

    Parameters
    ----------
    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray
        The density power-law index.

    gammaB : float or np.ndarray
        The bulk Lorentz factor.

    gamma0 : float
        The initial Lorentz factor.

    R : float or np.ndarray
        The blast wave radius [cm].

    Returns
    -------
    float or np.ndarray of float
        The energy [erg].
    """
    # 0.07 ~= 16 * pi * MassP * SoL**2
    return 0.075562 / (17.0 - 4.0 * k) * n0 * gamma0 * gammaB * R ** (3.0 - k)


# noinspection PyPep8Naming
@njit(cache=True)
def mag_field(E, n0, k, eps_b, t_src, adiabatic=True):
    """
    Returns the comoving magnetic field strength [G].

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``evo==radiative``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    t_src : float or np.ndarray of float
        The source-frame time(s) [s].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be
        True for 'adiabatic' or False for 'radiative'.

    Returns
    -------
    float or np.ndarray of float
        The magnetic field strength [G].
    """
    # where 0.38 ~= SoL * sqrt(32 * pi * MassP)
    return 0.388749 * gamma(E, n0, k, t_src, adiabatic) * np.sqrt(
        eps_b * n0 * radius(E, n0, k, t_src, adiabatic) ** -k
    )


# noinspection PyPep8Naming
@njit(cache=True)
def gamma_m(E, n0, k, p, eps_e, hmf, t_src, adiabatic=True):
    """
    Calculates the comoving minimum Lorentz factor(s).

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``adiabatic==False``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    p : float
        The electron energy index.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    t_src : float or np.ndarray of float
        The source-frame time(s) [s].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be
        True for 'adiabatic' or False for 'radiative'.

    Returns
    -------
    float or np.ndarray of float
        The comoving minimum Lorentz factor(s).
    """
    # where 3672 ~= 2 * MassP / MassE
    return 3672.305347 * (p - 2) / (p - 1) * (
        eps_e * gamma(E, n0, k, t_src, adiabatic) / (1 + hmf)
    )


# noinspection PyPep8Naming
@njit(cache=True)
def gamma_c(E, n0, k, eps_b, t_src, adiabatic=True):
    """
    Calculates the comoving critical Lorentz factor(s).

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``adiabatic==False``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    t_src : float or np.ndarray of float
        The source-frame time(s) [s].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be
        True for 'adiabatic' or False for 'radiative'.

    Returns
    -------
    float or np.ndarray of float
        The comoving critical Lorentz factor(s).
    """
    # 7.3 ~= 6 * pi * MassE * SoL / SigmaT
    return 7.738067e8 * t_src / (
        gamma(E, n0, k, t_src, adiabatic) *
        mag_field(E, n0, k, eps_b, t_src, adiabatic) ** 2
    )


# noinspection PyPep8Naming
@njit(cache=True)
def gamma(E, n0, k, t_src, adiabatic=True):
    """
    Calculates the bulk Lorentz factor(s).

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``evo==radiative``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    t_src : float or np.ndarray
        The source-frame times [s].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be
        True for 'adiabatic' or False for 'radiative'.

    Returns
    -------
    float or np.ndarray of float
        The bulk Lorentz factor(s).
    """
    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    exp = -0.5 / (4.0 - k) if adiabatic else -1.0 / (7.0 - 2.0 * k)

    return (
        hdc_a * hdc_b ** (3.0 - k) * np.pi *
        SoL ** (5.0 - k) * MassP * n0 / E * t_src ** (3.0 - k)
    ) ** exp


# noinspection PyPep8Naming
@njit(cache=True)
def radius(E, n0, k, t_src, adiabatic=True):
    """
    Calculates the source-frame blast wave radius [cm].

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``evo==radiative``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    t_src : float or np.ndarray of float64
        The source-frame times [s].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be
        True for 'adiabatic' or False for 'radiative'.

    Returns
    -------
    float or np.ndarray of float
        The source-frame blast wave radius [cm].
    """
    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    if adiabatic:
        return (
            # where 1.5e-13 ~= pi * MassP * SoL
            hdc_b * E * t_src / (1.575318e-13 * hdc_a * n0)
        ) ** (1 / (4 - k))

    return (
        # where 7.4e-16 ~= (pi * MassP)**2 * SoL**3
        hdc_b * E ** 2 * t_src / (7.439734e-16 * (hdc_a * n0) ** 2)
    ) ** (1 / (7 - 2 * k))


# noinspection PyPep8Naming
@njit(cache=True)
def deceleration_radius(E, n0, k, gamma0):
    """
    Calculates the source-frame blast wave radius [cm].

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    gamma0 : float
        The initial Lorentz factor.

    Returns
    -------
    float or np.ndarray of float
        The source-frame blast wave radius [cm].
    """
    # where 0.018 ~= 4 * pi * MassP * SoL**2
    return ((3.0 - k) * E / (n0 * 0.0188907 * gamma0 ** 2.0)) ** (1.0 / (3.0 - k))


# noinspection PyPep8Naming
@njit(cache=True)
def deceleration_time(E, n0, k, gamma0):
    """
    Calculates the time [s] once the blast waves starts to decelerate.

    The deceleration time is given by:

        .. math:: t = \frac{R_d}{\beta \Gamma_0^2 c}

    And occurs when the swept-up mass equals approximately:

        .. math:: M = \frac{E_0}{\Gamma_0^2 c^2}

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    gamma0 : float
        The initial Lorentz factor.

    Returns
    -------
    float or np.ndarray of float
        The source-frame blast wave radius [cm].
    """
    # Don't use the ``deceleration_radius`` method because calling
    # other methods is too slow. 0.018 ~= 4 * pi * MassP * SoL**2
    r_decel = ((3.0 - k) * E / (n0 * 0.0188907 * gamma0 ** 2.0)) ** (1.0 / (3.0 - k))

    return r_decel / gamma0 ** 2.0 / (4.0 - k) / SoL
# </editor-fold>


# <editor-fold desc="Radiation Properties">
# noinspection PyPep8Naming
class RadiationModel:
    """
    Radiation model.

    Parameters
    ----------
    n0 : float
        The density normalization [cm(k-3)].

    k : float
        The density power-law index.

    p : float
        The electron energy index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy carried by relativistic
        electrons. Must be in the range [0, 1].

    dL : float
        The luminosity distance [cm].

    z : float
        The redshift.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.
    """
    def __init__(self, n0, k, p, eps_b, eps_e, dL, z, hmf):
        self.n0 = n0
        self.k = k
        self.p = p
        self.eps_b = eps_b
        self.eps_e = eps_e
        self.dL = dL
        self.z = z
        self.hmf = hmf

    def peak_flux(self, E, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
        """ Observer-frame peak flux [mJy]. """
        return peak_flux(
            E, self.n0, self.k, self.eps_b, self.dL,
            self.z, self.hmf, t_obs, adiabatic, tj, sj
        )

    def cooling_frequency(self, E, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
        """ Observer-frame cooling frequency [Hz]. """
        return cooling_frequency(
            E, self.n0, self.k, self.eps_b, self.z, t_obs, adiabatic, tj, sj
        )

    def synchrotron_frequency(self, E, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
        """ Observer-frame synchrotron frequency [Hz]. """
        return synchrotron_frequency(
            E, self.n0, self.k, self.p, self.eps_b, self.eps_e,
            self.z, self.hmf, t_obs, adiabatic, tj, sj
        )

    def absorption_frequency(self, E, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
        """ Observer-frame self-absorption frequency [Hz]. """
        return absorption_frequency(
            E, self.n0, self.k, self.p, self.eps_b, self.eps_e,
            self.z, self.hmf, t_obs, adiabatic, tj, sj
        )

    def rad_to_ad_smooth(self, t, t_trans, rad, ad):
        """ Smooths the radiative and adiabatic evolutions. """
        # Generalized s(p) from GS02 for break 9 (s23) and break 11 (s12)
        s = 3.34 + 0.17 * self.k - (0.82 + 0.035 * self.k) * self.p

        # Radiative efficiency
        eff = 1.0 / (1.0 + (t / t_trans) ** (s * (self.p / 2 + 1 / 3)))

        return {
            'p': self.p, 'k': self.k,
            'nu_c': hill(rad['nu_c'], ad['nu_c'], eff),
            'nu_a': hill(rad['nu_a'], ad['nu_a'], eff),
            'nu_m': hill(rad['nu_m'], ad['nu_m'], eff),
            'f_peak': hill(rad['f_peak'], ad['f_peak'], eff),
        }

    def rad_to_ad_time(self, E, t_obs=None, nu_m=None, nu_c=None):
        """ Observer-frame radiative to adiabatic transition time [s]. """
        if isinstance(self.k, np.ndarray):
            # Is there actually a root to find?
            if (i := crosses(nu_m, nu_c)) == -1:
                return

            # return the transition time for a stratified medium [s]
            return optimize.root_scalar(
                self._rad_to_ad_time_stratified, bracket=[t_obs[i], t_obs[i+1]], args=(t_obs, E)
            ).root * DAY2SEC

        # return transition time for a general medium [s]
        return rad_to_ad_time(
            E, self.n0, self.k, self.p, self.eps_b, self.eps_e, self.z, self.hmf
        )

    def _rad_to_ad_time_stratified(self, t, t_obs, E):
        """
            Observer-frame radiative to adiabatic transition time [s]
            for a stratified medium.
        """
        k = np.interp(t, t_obs, self.k)
        n0 = np.interp(t, t_obs, self.n0)

        nu_c = cooling_frequency(E, n0, k, self.eps_b, self.z, t, adiabatic=False)
        nu_m = synchrotron_frequency(E, n0, k, self.p, self.eps_b, self.eps_e, self.z, self.hmf, t, adiabatic=False)
        return nu_c - nu_m


# noinspection PyPep8Naming
@njit(cache=True)
def peak_flux(E, n0, k, eps_b, dL, z, hmf, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
    """
    Calculates the observer-frame peak fluxes [mJy] for
    an ultra-relativistic shock moving through an external
    medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``adiabatic==False``,
        assumes the ``E`` is divided by the initial Lorentz
        factor (i.e., E0 / Gamma0).

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    dL : float
        The luminosity distance to the event [cm].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float
        The observer-frame times [d].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be True
        for 'adiabatic' or False for 'radiative'.

    tj : float, optional, default=-1.0
        The observer-frame jet-break time in days [s]. Only used
        if ``adiabatic`` is True.

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None and ``adiabatic`` is True.

    Returns
    -------
    float or np.ndarray of float
        The observer-frame peak fluxes [mJy].
    """
    if adiabatic:
        return f_peak_ad(E, n0, k, eps_b, dL, z, hmf, t_obs, tj, sj)
    return f_peak_rad(E, n0, k, eps_b, dL, z, hmf, t_obs)


# noinspection PyPep8Naming
@njit(cache=True)
def cooling_frequency(E, n0, k, eps_b, z, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
    """
    Calculates the observer-frame cooling frequencies [Hz] for
    an ultra-relativistic shock moving through an external
    medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``adiabatic==False``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be True
        for 'adiabatic' or False for 'radiative'.

    tj : float, optional, default=-1.0
        The observer-frame jet-break time in days [s]. Only used
        if ``adiabatic`` is True.

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None and ``adiabatic`` is True.

    Returns
    -------
    float or np.ndarray of float
        The observer-frame cooling frequency [Hz].
    """
    if adiabatic:
        return nu_c_ad(E, n0, k, eps_b, z, t_obs, tj, sj)
    return nu_c_rad(E, n0, k, eps_b, z, t_obs)


# noinspection PyPep8Naming
@njit(cache=True)
def synchrotron_frequency(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
    """
    Calculates the observer-frame synchrotron frequencies [Hz]
    for an ultra-relativistic shock moving through an external
    medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``adiabatic==False``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray
        The number density normalization [cm(k-3)].

    p : float
        The electron energy index.

    k : float or np.ndarray
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be True
        for 'adiabatic' or False for 'radiative'.

    tj : float, optional, default=-1.0
        The observer-frame jet-break time in days [s]. Only used
        if ``adiabatic`` is True.

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None and ``adiabatic`` is True.

    Returns
    -------
    float or np.ndarray of float
        The observer-frame synchrotron frequencies [Hz].
    """
    if adiabatic:
        return nu_m_ad(E, k, p, eps_b, eps_e, z, hmf, t_obs, tj=tj, sj=sj)
    return nu_m_rad(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs)


# noinspection PyPep8Naming
def absorption_frequency(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs, adiabatic=True, tj=-1.0, sj=1.0):
    """
    Calculates the observer-frame self-absorption frequencies [Hz]
    for an ultra-relativistic shock moving through an external
    medium with density rho = rho0 * R^-k.

    The analytic approximation for the self-absorption is crude and
    only valid when the breaks are sufficiently far apart. As the
    breaks cross, there will be a sharp jump in the self-absorption
    frequency. A true treatment of the self-absorption requires
    numerical methods.

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``adiabatic==False``,
        assumes that ``E=E0 / Gamma0``.

    n0 : float or np.ndarray of float
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    p : float
        The electron energy index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    adiabatic : bool, optional, default=True
        How is the blast wave evolving? Must be True
        for 'adiabatic' or False for 'radiative'.

    tj : float, optional, default=-1.0
        The observer-frame jet-break time in days [s]. Only used
        if ``adiabatic`` is True.

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None and ``adiabatic`` is True.

    Returns
    -------
    float or np.ndarray of float
        The observer-frame self-absorption frequencies [Hz].
    """
    t_obs = np.atleast_1d(t_obs)

    nu_m = synchrotron_frequency(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs, adiabatic, tj, sj)
    nu_c = cooling_frequency(E, n0, k, eps_b, z, t_obs, adiabatic, tj, sj)

    if adiabatic:
        fast = nu_c < nu_m

        # Determine slow-cooling absorption frequencies
        nu_amc = nu_a_amc_ad(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs, tj, sj)
        nu_mac = nu_a_mac_ad(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs, tj, sj)

        # Initialize with smoothed slow cooling values
        slow_weight = 1.0 / (1.0 + (nu_amc / nu_m) ** 3.0)
        res = slow_weight * nu_amc + (1.0 - slow_weight) * nu_mac

        if fast.any():  # type: ignore


            # Determine fast-cooling absorption frequencies
            nu_acm = nu_a_acm_ad(E, n0, k, eps_b, z, hmf, t_obs, tj, sj)
            nu_cam = nu_a_cam_ad(E, n0, k, z, hmf, t_obs, tj, sj)

            # Smooth across the cooling break
            fast_weight = 1.0 / (1.0 + (nu_acm / nu_c) ** 3.0)
            res_fast = fast_weight * nu_acm + (1.0 - fast_weight) * nu_cam

            # Smooth fast and slow cooling values
            fast_slow_weight = 1.0 / (1.0 + (nu_c / nu_m) ** 3.0)
            res = fast_slow_weight * res_fast + (1.0 - fast_slow_weight) * res

    else:
        # Determine radiative absorption frequencies
        nu_acm = nu_a_acm_rad(E, n0, k, eps_b, z, hmf, t_obs)
        nu_cam = nu_a_cam_rad(E, n0, k, z, hmf, t_obs)
        res = np.where(nu_acm < nu_c, nu_acm, nu_cam)

    return res


# noinspection PyPep8Naming
@njit(cache=True)
def f_peak_ad(E, n0, k, eps_b, dL, z, hmf, t_obs, tj=-1.0, sj=1.0):
    """
    Calculates the observer-frame peak fluxes [mJy] for
    an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    dL : float
        The luminosity distance to the event [cm].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray
        The observer-frame times [days].

    tj : float, optional, default=-1.0
        The observer-frame jet-break time [days].

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None.

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame peak fluxes [mJy].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Evaluate exponents once
    exp_nrg = (8.0 - 3.0 * k) / 2.0

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 4.0 - k, MassP * n0

    lin_fac = (
        hdc_a ** -exp_nrg * hdc_b ** -(k / 2.0) *
        np.pi ** -(2.0 - k) * (1.0 + z) ** ((8.0 - k) / 2.0)
    ) ** (1.0 / x)

    # 22.8 ~= log10(4/6 * sqrt(2) * ECharge**3 / MassE / MassP)
    log_fac = 22.836128 + (
        np.log10(rho0) * 2.0 +
        np.log10(E) * exp_nrg+
        np.log10(SoL) * -((24.0 - 7.0 * k) / 2.0) +
        np.log10(t_obs_s) * -(k / 2.0)
    ) / x

    f_pk = CGS2MJY * (  # observer-frame peak flux [mJy]
        (1.0 + hmf) / dL ** 2.0 * eps_b ** 0.5 * lin_fac * 10.0 ** log_fac
    )

    if tj != -1.0:
        # alpha_pre - alpha_post
        aj = -k / x / 2.0 + 1.0

        # return jet-broken peak flux [Hz]
        return f_pk * (1.0 + (t_obs / tj) ** sj) ** -(aj / sj)

    # return observer-frame peak flux [mJy]
    return f_pk

# noinspection PyPep8Naming
@njit(cache=True)
def f_peak_rad(E, n0, k, eps_b, dL, z, hmf, t_obs):
    """
    Calculates the observer-frame peak fluxes [mJy] for
    an ultra-relativistic shock moving radiatively through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg] divided by the initial
        Lorentz factor (i.e., E0 / Gamma0).

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    dL : float
        The luminosity distance to the event [cm].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray
        The observer-frame times [days].

    Returns
    -------
    float or np.ndarray of float
        The radiative, observer-frame peak fluxes [mJy].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 7.0 - 2.0 * k, MassP * n0

    lin_fac = (
        hdc_a ** -(8.0 - 3.0 * k) * hdc_b ** -((6.0 - k) / 2.0)  *
        np.pi ** -(9.0 - 4.0 * k) * (1.0 + z) ** (2.5 * (4.0 - k))
    ) ** (1 / x)

    # 22.8 ~= log10(4/6 * sqrt(2) * ECharge**3 / MassE / MassP)
    log_fac = 22.836128 + (
        np.log10(rho0) * 2.5 +
        np.log10(E) * (8.0 - 3.0 * k) +
        np.log10(SoL) * -((52.0 - 17.0 * k) / 2.0) +
        np.log10(t_obs_s) * -((6.0 - k) / 2.0)
    ) / x

    # return observer-frame peak flux [mJy]
    return CGS2MJY / dL ** 2.0 * (
        (1.0 + hmf) * eps_b ** 0.5 * lin_fac * 10.0 ** log_fac
    )


# noinspection PyPep8Naming
@njit(cache=True)
def nu_c_ad(E, n0, k, eps_b, z, t_obs, tj=-1.0, sj=1.0):
    """
    Calculates the observer-frame cooling frequencies [Hz] for
    an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    t_obs : float or np.ndarray
        The observer-frame times [d].

    tj : float, optional, default=-1.0
        The observer-frame jet-break time in days [s].

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None.

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame cooling frequency [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Shared exponents
    exp_nrg = -(4.0 - 3.0 * k) / 2.0

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 4.0 - k, MassP * n0

    lin_fac = (
        hdc_a ** -exp_nrg * hdc_b ** ((12.0 - k) / 2.0) *
        np.pi ** -(8.0 - k) * (1.0 + z) ** -((4.0 + k) / 2.0)
    ) ** (1.0 / x)

    # -71.8 ~= log10(81/8192 * sqrt(2) / ECharge**7 * MassE**5)
    log_fac = -71.827659 + (
        np.log10(rho0) * -4.0 +
        np.log10(E) * exp_nrg +
        np.log10(SoL) * ((68.0 - 19.0 * k) / 2.0) +
        np.log10(t_obs_s) * exp_nrg
    ) / x

    nu_c = eps_b ** -1.5 * lin_fac * 10 ** log_fac

    if tj != -1.0:
        # return jet-broken cooling frequency [Hz]
        return nu_c * (1.0 + (t_obs / tj) ** sj) ** -(exp_nrg / x / sj)

    # return observer-frame cooling frequency [Hz]
    return nu_c


# noinspection PyPep8Naming
@njit(cache=True)
def nu_c_rad(E, n0, k, eps_b, z, t_obs):
    """
    Calculates the observer-frame cooling frequencies [Hz] for
    an ultra-relativistic shock moving radiatively through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg] divided by the initial
        Lorentz factor (i.e., E0 / Gamma0).

    n0 : float or np.ndarray of float
        The number density normalization [cm-(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    t_obs : float or np.ndarray
        The observer-frame times [d].

    Returns
    -------
    float or np.ndarray of float
        The radiative, observer-frame cooling frequency [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 7.0 - 2.0 * k, MassP * n0

    lin_fac = (
        hdc_a ** (4.0 - 3.0 * k) * hdc_b ** ((24.0 - 5.0 * k) / 2.0) *
        np.pi ** -(27 - 4.0 * k) * (1.0 + z) ** -((10.0 - k) / 2.0)
    ) ** (1.0 / x)

    # -71.8 ~= log10(81/8192 * sqrt(2) / ECharge**7 * MassE**5)
    log_fac = -71.827659 + (
        np.log10(rho0) * -6.5 +
        np.log10(E) * -(4.0 - 3.0 * k) +
        np.log10(SoL) * ((124.0 - 41.0 * k) / 2.0) +
        np.log10(t_obs_s) * -((4.0 - 3.0 * k) / 2.0)
    ) / x

    # return observer-frame cooling frequency [Hz]
    return eps_b ** -1.5 * lin_fac * 10.0 ** log_fac


# noinspection PyPep8Naming
@njit(cache=True)
def nu_m_ad(E, k, p, eps_b, eps_e, z, hmf, t_obs, tj=1.0, sj=1.0):
    """
    Calculates the observer-frame synchrotron frequencies [Hz]
    for an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg]. If ``adiabatic==False``,
        assumes that ``E=E0 / Gamma0``.

    p : float
        The electron energy index.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray
        The observer-frame time(s) [d].

    tj : float, optional, default=-1.0
        The observer-frame jet-break time [days].

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None.

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame synchrotron frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    nu_m = (hdc_a ** -0.5) * (hdc_b ** -1.5) * 0.041139 * (
        # 0.04 ~= 8 * sqrt(2) / pi * ECharge / MassE**3 * MassP**2 / SoL**-2.5
        (1.0 + hmf) ** -2.0 * (1.0 + z) ** 0.5 * eps_e ** 2.0 * eps_b ** 0.5 *
        E ** 0.5 * ((p - 2.0) / (p - 1.0)) ** 2.0 * t_obs_s ** -1.5
    )

    if tj != -1.0:
        # return jet-broken synchrotron frequency [Hz]
        return nu_m * (1.0 + (t_obs / tj) ** sj) ** -(0.5 / sj)

    # return synchrotron frequency [Hz]
    return nu_m


# noinspection PyPep8Naming
@njit(cache=True)
def nu_m_rad(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs):
    """
    Calculates the observer-frame synchrotron frequencies [Hz]
    for an ultra-relativistic shock moving radiatively through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg] divided by the initial
        Lorentz factor (i.e., E0 / Gamma0).

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    p : float
        The electron energy index.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray
        The observer-frame times [d].

    Returns
    -------
    float or np.ndarray of float
        The radiative, observer-frame synchrotron frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 7.0 - 2.0 * k, MassP * n0

    lin_fac = (
        hdc_a ** -(4.0 - k) * hdc_b ** -((24.0 - 7.0 * k) / 2.0) *
        np.pi ** -((15.0 - 4.0 * k) / 2.0) * (1 + z) ** ((10.0 - 3.0 * k) / 2.0)
    ) ** (1.0 / x)

    # 25.3 ~= log10(8 * sqrt(2) * ECharge / MassE**3 * MassP**2)
    log_fac = 25.303464 + (
        np.log10(rho0) * -0.5 + np.log10(SoL) * -((40.0 - 11.0 * k) / 2.0) +
        np.log10(E) * (4.0 - k) + np.log10(t_obs_s) * -((24.0 - 7.0 * k) / 2.0)
    ) / x

    # return observer-frame synchrotron frequencies [Hz]
    return ((p - 2.0) / (p - 1.0)) ** 2.0 / (1.0 + hmf) ** 2.0 * (
        eps_e ** 2.0 * eps_b ** 0.5 * lin_fac * 10.0 ** log_fac
    )


# noinspection PyPep8Naming
@njit(cache=True)
def nu_a_amc_ad(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs, tj=1.0, sj=1.0):
    """
    Calculates the self-absorption frequency [Hz] in the
    weak self-absorption regime (nu_a < nu_m < nu_c) for
    an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    p : float
        The electron energy index.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    tj : float, optional, default=-1.0
        The observer-frame jet-break time [days].

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None.

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame self-absorption frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Electron energy index factors
    eei = (p + 2.0 / 3.0) ** -0.6 * (p + 2.0) ** 0.6 * (p - 1.0) ** 1.6 / (p - 2.0)

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 5.0 * (4.0 - k), MassP * n0

    lin_fac = (
        hdc_a ** -(4.0 * (1.0 - k)) * hdc_b ** -(3.0 * k) *
        np.pi ** (4.0 + 2.0 * k) * (1.0 + z) ** -(4.0 * (5.0 - 2.0 * k))
    ) ** (1.0 / x)

    # 23.3 ~= log10(2 * 3**0.8 * (ECharge / MassP / 2)**8/5)
    log_fac = 23.334091 + (
        np.log10(rho0) * 12.0 +
        np.log10(E) * (4.0 * (1.0 - k)) +
        np.log10(SoL) * -(4.0 * (5.0 - 2.0 * k)) +
        np.log10(t_obs_s) * -(3.0 * k)
    ) / x

    # Observer-frame self-absorption frequency [Hz]
    nu_a = (1.0 + hmf) ** 1.6 * eei * (
        eps_b ** 0.2 / eps_e * lin_fac * 10.0 ** log_fac
    )

    if tj != -1.0:
        # alpha_pre - alpha_post
        aj = -(3.0 * k) / x + 0.2

        # return jet-broken self-absorption frequencies [Hz]
        return nu_a * (1.0 + (t_obs / tj) ** sj) ** -(aj / sj)

    # return observer-frame self-absorption frequencies [Hz]
    return nu_a


# noinspection PyPep8Naming
@njit(cache=True)
def nu_a_acm_ad(E, n0, k, eps_b, z, hmf, t_obs, tj=-1.0, sj=1.0):
    """
    Calculates the self-absorption frequency [Hz] in the
    weak self-absorption regime (nu_a < nu_c < nu_m) for
    an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    tj : float, optional, default=-1.0
        The observer-frame jet-break time [days].

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None.

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame self-absorption frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 5.0 * (4.0 - k), MassP * n0

    lin_fac = (
        hdc_a ** -(14.0 - 9.0 * k) *
        hdc_b ** -(2.0 * (15.0 - k)) *
        np.pi ** (2.0 + 5.0 * k) *
        (1.0 + z) ** -(2.0 * (5.0 - 4.0 * k))
    ) ** (1.0 / x)

    # 23.3 ~= log10(2 * 3**0.8 * (ECharge / MassP / 2)**8/5)
    log_fac = 71.463454 + (
        np.log10(rho0) * 22.0 +
        np.log10(E) * (14.0 - 9.0 * k) +
        np.log10(SoL) * -(2.0 * (65.0 - 19.0 * k)) +
        np.log10(t_obs_s) * -(10.0 + 3.0 * k)
    ) / x

    # Observer-frame self-absorption frequencies [Hz]
    nu_a = (1.0 + hmf) ** 0.6 * (
        eps_b ** 1.2 * lin_fac * 10.0 ** log_fac
    )

    if tj != -1.0:
        # alpha_pre - alpha_post
        aj = -(10.0 + 3.0 * k) / x + 1.2

        # return jet-broken self-absorption frequencies [Hz]
        return nu_a * (1.0 + (t_obs / tj) ** sj) ** -(aj / sj)

    # return observer-frame self-absorption frequencies [Hz]
    return nu_a


# noinspection PyPep8Naming
@njit(cache=True)
def nu_a_mac_ad(E, n0, k, p, eps_b, eps_e, z, hmf, t_obs, tj=-1.0, sj=1.0):
    """
    Calculates the self-absorption frequency [Hz] in the
    weak self-absorption regime (nu_m < nu_a < nu_c) for
    an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    p : float
        The electron energy index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    tj : float, optional, default=-1.0
        The observer-frame jet-break time [days].

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None.

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame self-absorption frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, y, rho0 = 4.0 - k, p + 4.0, MassP * n0

    eei = (
        # Electron energy index factors
        (p - 2.0) ** (2.0 * (p - 1.0)) *
        (p - 1.0) ** -(2.0 * (p - 2.0)) *
        (p + 2.0) ** 2.0
    ) ** (1.0 / y)

    lin_fac = (
        # Linear factors ^ 1 / (2 * x * y)
        np.pi ** -((8.0 * (p + 2.0) - 2.0 * k * y) / 2.0 / x) *
        hdc_a ** -((4.0 * (p + 2.0) - k * (p + 6.0)) / 2.0 / x) *
        hdc_b ** -((4.0 * (3.0 * p + 2.0) - k * (3.0 * p - 2.0)) / 2.0 / x) *
        (1.0 + z) ** ((4.0 * (p - 6.0) - k * (p - 10.0)) / 2.0 / x) *

        # Linear factors ^ 1 / y
        ((1.0 + hmf) / 2.0) ** -(2.0 * (p + 2.0)) *
        eps_b ** ((p + 2.0) / 2.0) *
        eps_e ** (2.0 * (p - 1.0)) *
        math.gamma(p / 2.0 + 1.0 / 3.0) ** 2.0

    ) ** (1.0 / y)

    log_fac = (
        1.272323 +

        # Log factors ^ 1 / (2 * x * y)
        np.log10(rho0) * (8.0 / x) +
        np.log10(E) * ((4.0 * (p + 2.0) - k * (p + 6.0)) / 2.0 / x) +
        np.log10(SoL) * -((4.0 * (5.0 * p + 10.0) - k * (5.0 * p + 14.0)) / 2.0 / x) +
        np.log10(t_obs_s) * -((4.0 * (3.0 * p + 2.0) - k * (3.0 * p - 2.0)) / 2.0 / x) +

        # Log factors ^ 1 / y
        np.log10(2.0) * ((9.0 * p - 22.0) / 6.0) +
        np.log10(ECharge) * (p + 6.0) +
        np.log10(MassE) * -(3.0 * p + 2.0) +
        np.log10(MassP) * (2.0 * (p - 2.0))

    ) / y

    # Observer-frame self-absorption frequency [Hz]
    nu_a = eei * lin_fac * 10.0 ** log_fac

    if tj != -1.0:
        # alpha_pre - alpha_post
        aj = (
            -((4.0 * (3.0 * p + 2.0) - k * (3.0 * p - 2.0)) / 2.0 / x) / y +
            (2.0 * (p + 1.0) / (p + 4.0))
        )

        # return jet-broken self-absorption frequencies [Hz]
        return nu_a * (1.0 + (t_obs / tj) ** sj) ** -(aj / sj)

    # return observer-frame self-absorption frequencies [Hz]
    return nu_a


# noinspection PyPep8Naming
@njit(cache=True)
def nu_a_cam_ad(E, n0, k, z, hmf, t_obs, tj=-1.0, sj=1.0):
    """
    Calculates the self-absorption frequency [Hz] in the
    strong self-absorption regime (nu_c < nu_a < nu_m) for
    an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float64
        The density power-law index.

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [days].

    tj : float, optional, default=-1.0
        The observer-frame jet-break time [days].

    sj : float, optional, default=1.0
        The jet-break smoothing factor. Only used if ``tj`` is
        not None.

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame self-absorption frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 4.0 - k, MassP * n0

    # 0.75 ~= cbrt(27/32 * cbrt(1.5) * Gamma(4/3))
    lin_fac = 2.5782473920911e+23 * (
        hdc_a ** (k - 2.0) * hdc_b ** -2.0 *
        np.pi ** (2.0 * (k - 3.0)) *
        (1.0 + z) ** (2.0 * (k - 3.0))
    ) ** (1.0 / x)

    log_fac = (
        np.log10(rho0) * 2.0 +
        np.log10(E) * (2.0 - k) +
        np.log10(SoL) * 2.0 +
        np.log10(t_obs_s) * (k - 6.0)
    ) / x

    # Observer-frame self-absorption frequency [Hz]
    nu_a = np.cbrt((1.0 + hmf) * lin_fac * 10.0 ** log_fac)

    if tj != -1.0:
        # alpha_pre - alpha_post
        aj = (k - 6.0) / 3.0 / x + (2.0 / 3.0)

        # return jet-broken self-absorption frequency [Hz]
        return nu_a * (1.0 + (t_obs / tj) ** sj) ** -(aj / sj)

    # return observer-frame self-absorption frequency [Hz]
    return nu_a

# noinspection PyPep8Naming
@njit(cache=True)
def nu_a_acm_rad(E, n0, k, eps_b, z, hmf, t_obs):
    """
    Calculates the self-absorption frequency [Hz] in the
    weak self-absorption regime (nu_a < nu_c < nu_m) for
    an ultra-relativistic shock moving adiabatically through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg] divided by the initial
        Lorentz factor (i.e., E0 / Gamma0).

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    Returns
    -------
    float or np.ndarray of float
        The adiabatic, observer-frame self-absorption frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 7.0 - 2.0 * k, MassP * n0

    lin_fac = (
        np.pi ** (2.0 * k) *
        hdc_a ** -(0.4 * (14.0 - 9.0 * k)) *
        hdc_b ** -((63.0 - 13.0 * k) / 5.0) *
        (1.0 + z) ** -(1.4 * (1.0 - k))
    ) ** (1.0 / x)

    # 71.4 ~= log10(2**28/5 * 3**-0.6 * (ECharge**25 / MassE**4 / MassP**-3 / 2)**0.2)
    log_fac = 71.463454 + (
        np.log10(rho0) * 7.0 +
        np.log10(E) * (0.4 * (14.0 - 9.0 * k)) +
        np.log10(SoL) * (17.0 * k - 49.0) +
        np.log10(t_obs_s) * ((3.0 * k - 28.0) / 5.0)
    ) / x

    # return observer-frame self-absorption frequencies [Hz]
    return (1.0 + hmf) ** 0.6 * (
        eps_b ** 1.2 * lin_fac * 10.0 ** log_fac
    )


# noinspection PyPep8Naming
@njit(cache=True)
def nu_a_cam_rad(E, n0, k, z, hmf, t_obs):
    """
    Calculates the self-absorption frequency [Hz] in the
    strong self-absorption regime (nu_c < nu_a < nu_m) for
    an ultra-relativistic shock moving radiatively through
    an external medium with density rho = rho0 * R^-k.

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm-3] normalized
        to 1 cm.

    k : float or np.ndarray of float
        The density power-law index.

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    t_obs : float or np.ndarray of float64
        The observer-frame times [d].

    Returns
    -------
    float or np.ndarray of float
        The radiative, observer-frame self-absorption frequencies [Hz].
    """
    t_obs_s = DAY2SEC * t_obs

    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = 7.0 - 2.0 * k, MassP * n0

    lin_fac = (
        np.pi ** (4.0 * k - 11.0) *
        hdc_a ** (2.0 * k - 4.0) *
        hdc_b ** (k + 5.0) *
        (1.0 + z) ** (5.0 - k)
    ) ** (1.0 / x)

    # 23.4 ~= log10(27/32 * cbrt(1.5) * Gamma(4/3) / MassP)
    log_fac = 23.411324 + (
        np.log10(rho0) * 3.0 +
        np.log10(E) * (2.0 * (2.0 - k)) +
        np.log10(SoL) * (1.0 + k) +
        np.log10(t_obs_s) * (3.0 * (k - 4.0))
    ) / x

    # return observer-frame self-absorption frequency [Hz]
    return np.cbrt((1.0 + hmf) * lin_fac * 10.0 ** log_fac)


# noinspection PyPep8Naming
@njit(cache=True)
def rad_to_ad_time(E, n0, k, p, eps_b, eps_e, z, hmf):
    """
    Calculates the observer-frame radiative to adiabatic
    transition time [s].

    Parameters
    ----------
    E : float
        The explosion energy [erg].

    n0 : float or np.ndarray of float
        The number density normalization [cm(k-3)].

    k : float or np.ndarray of float
        The density power-law index.

    p : float
        The electron energy index.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy in the electric field.
        Must be in the range [0, 1].

    z : float
        The redshift to the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    Returns
    -------
    float or np.ndarray of float
        The observer-frame transition time [s].
    """
    # Hydrodynamic coefficients
    hdc_a = 16.0 / (17.0 - 4.0 * k)
    hdc_b = 4.0 - k

    # Break up the evaluations for the factors with
    # massive exponents to prevent overflow errors.
    x, rho0 = k - 5.0, MassP * n0

    lin_fac = (1.0 + z) * (
        hdc_a ** (4.0 - 2.0 * k) * hdc_b ** (12.0 - 3.0 * k) *
        (eps_e * eps_b / (1.0 + hmf)) ** -(7.0 - 2.0 * k) *
        ((p - 1.0) / (p - 2.0)) ** (7.0 - 2.0 * k) *
        np.pi ** (k - 39.0 / 4.0)
    ) ** (1.0 / x)

    log_fac = (
        -48.565561 * (7.0 - 2.0 * k) +
        np.log10(rho0) * -3.0 +
        np.log10(E) * (2.0 * k - 4.0) +
        np.log10(SoL) * (41.0 - 13.0 * k)
    ) / x

    # return radiative to adiabatic transition time [s]
    return lin_fac * 10.0 ** log_fac
# </editor-fold>


def has_fts_transition(nu_m, nu_c) -> bool:
    """
    Is there a fast-to-slow cooling transition?

    Parameters
    ----------
    nu_m, nu_c : np.ndarray or list
        Synchrotron (nu_m) and cooling (nu_c) frequencies.

    Returns
    -------
    bool
        True if there is a transition from fast to slow.
    """
    return np.sign(nu_c[0] - nu_m[0]) < np.sign(nu_c[-1] - nu_m[-1])



# noinspection PyPep8Naming
class BaseBlastWaveModel:
    """
    Base BlastWaveModel. Not intended for direct use.

    Parameters
    ----------
    E : float
        The explosion energy normalized to 1e52 ergs.

    n17 : float or u.Quantity['number density']
        The number density normalization at ``ref`` cm.

    k : float
        The density power-law index.
    """
    c = const.c.cgs.value      # type: ignore
    m_p = const.m_p.cgs.value  # type: ignore

    def __init__(self, E, n17, k, ref):
        self.E = E
        self._n17 = n17
        self.k = k
        self.r_ref = ref

    @property
    def n17(self) -> float:
        """ Returns the density normalization. """
        return self._n17

    @n17.setter
    def n17(self, n17) -> None:
        """
        Sets the density normalization as a simple float.

        Define rho as:

        rho = rho_x * R^-k = rho_0 * (R/R_0)^-k

        such that:

        rho_x = rho_0 * R_0^k = n0 * m_p * R_0^k

        where R_0 is the characteristic radius which is
        taken to be 1e17 cm. Then, `n17` is defined as
        the number density with respect to 1e17 cm.

        Parameters
        ----------
        n17 : float or u.Quantity['number density', 'mass density']
            The number density at 1e17 cm.
        """
        if isinstance(n17, u.Quantity):
            if n17.physical_type == 'number density':
                n17 = n17.cgs.value

            elif n17.physical_type == 'mass density':
                n17 = n17.cgs.value / self.m_p

        self._n17 = n17

    @property
    def alpha(self) -> float:
        """ Returns the hydrodynamic coefficient. """
        return 16 / (17 - 4 * self.k)

    @property
    def beta(self) -> float:
        """ Returns the hydrodynamic coefficient. """
        return 4 - self.k

    @property
    def rho17(self):
        """ Returns the density normalization. """
        return self.n17 * self.m_p * (self.r_ref ** self.k)


# noinspection PyPep8Naming
class BlastWaveModel(BaseBlastWaveModel):
    """
    Models a self-similar, ultra-relativistic blast wave.
    """
    def __init__(self, E, n17, k, ref=1e17):
        super().__init__(E, n17, k, ref)

    def lorentz_factor(self, z, t):
        """
        The Lorentz factor of the shocked fluid, gamma.

        Parameters
        ----------
        z : float
            The redshift.

        t : float or np.ndarray
            The observer time [d].

        Returns
        -------
        float or np.ndarray
            The Lorentz factor of the shocked fluid.
        """
        k = self.k

        # Convert to source frame time [s]
        t = t * 86_400 / (1 + z)

        return (
            self.alpha * self.beta ** (3 - k) *
            np.pi * self.c ** (5 - k) * self.rho17 *
            (1e52 * self.E) ** -1 * t ** (3 - k)
        ) ** -(0.5 / (4 - k))

    def shock_radius(self, z, t, t_decel=0.0):
        """
        The shock radius, R(t).

        Parameters
        ----------
        z : float
            The redshift.

        t : float or np.ndarray
            The observer time [d].

        t_decel : float or np.ndarray
            The burst frame (z=0) deceleration time
            of the blast wave [d].

        Returns
        -------
        float or np.ndarray
            The shock radius evaluated at ``t`` [cm].
        """
        # Add the deceleration time [s]
        t = 86_400 * (t_decel + (t / (1 + z)))

        return (
            self.beta * 1e52 * self.E * t /
            (self.alpha * np.pi * self.rho17 * self.c)
        ) ** (1 / (4 - self.k))

    def decel_radius(self, gamma=300):
        """
        The burst-frame deceleration radius measured in cm.

        Parameters
        ----------
        gamma : float or np.ndarray, default=300
            The initial Lorentz factor.

        Returns
        -------
        float or np.ndarray
            The deceleration radius [cm].
        """
        return (
            ((3 - self.k) * 1e52 * self.E) /
            (4 * np.pi * self.rho17 * self.c ** 2 * gamma ** 2)
        ) ** (1 / (3 - self.k))

    def decel_time(self, gamma=300, z=0.0):
        """
        Calculates the deceleration time of the shock
        measured in seconds. If the redshift, `z`, is
        provided, returns the observer-frame time. Else,
        returns the burst frame time (i.e., z=0.0).

        Parameters
        ----------
        gamma : float or np.ndarray, default=300
            The initial Lorentz factor.

        z : float, optional, default=0.0
            The redshift.

        Returns
        -------
        float or np.ndarray
            The deceleration time [s].
        """
        return (1 + z) * (
            self.decel_radius(gamma) / ((4 - self.k) * gamma ** 2 * self.c)
        )


# noinspection PyPep8Naming
class OpeningAngleModel:
    """
    Jet opening angle model.

    Parameters
    ----------
    E : float
        The isotropic energy normalized to 1e52 erg.

    rho0 : float
        The number density. Normalized to the proton
        mass and (1e17cm)^k such that the units are
        1 / cm^3.

    k : float
        The density power-law index.

    z : float
        The redshift.
    """
    def __init__(self, E, rho0, k, z):
        self.rho0 = rho0
        self.E = E
        self.k = k
        self.z = z

    def __repr__(self):
        """ Human-readable string """
        return f'OpeningAngle(E={self.E}, rho0={self.rho0}, k={self.k})'

    def __call__(self, *args, **kwargs):
        """ Calls the evaluate method. """
        return self.evaluate(*args, **kwargs)

    @property
    def alpha(self) -> float:
        """ Returns the hydrodynamic coefficient. """
        return 16 / (17 - 4 * self.k)

    @property
    def beta(self) -> float:
        """ Returns the hydrodynamic coefficient. """
        return 4 - self.k

    def evaluate(self, t, ref=1e17):
        """
        Evaluates the jet opening angle at the jet break
        time ``t``.

        Parameters
        ----------
        t : float or np.ndarray of float
            The jet break time [d].

        ref : float, optional, default=1e17

        Returns
        -------
        float or np.ndarray of float
            The jet opening angle [rad].
        """
        rho_norm = MassP * (ref ** self.k)

        # return the jet opening angle
        return (
            np.pi * self.alpha *
            (self.beta ** (3 - self.k)) *
            ((1 + self.z) ** -(3 - self.k)) *
            (SoL ** (5 - self.k)) *
            (rho_norm * self.rho0) *
            ((1e52 * self.E) **-1) *
            ((DAY2SEC * t) ** (3 - self.k))
        ) ** (0.5 / (4 - self.k))


class ObservedSpectrumModel:
    """
    GRB spectrum for an observational data set.

    The fireball model classes are parameterized by the
    intrinsic properties of the afterglow. However, the
    critical frequencies and peak flux are time-dependent
    and typically calculated using observation times.

    Because of this, it doesn't really make sense to store
    the characteristics in the Fireball classes. However,
    they are used all over the place which means that I
    was constantly passing them to methods which was very
    cumbersome.

    This class is a way to keep the calculations fast but
    in an organized way. It can be used directly, but it
    probably isn't very useful outside its original
    purpose.

    Parameters
    ----------
    nu_m, nu_c : np.ndarray of float
        The characteristic frequencies [Hz].

    nu_a : np.ndarray of float, optional
        The self-absorption frequency [Hz].

    f_peak : np.ndarray of float
        The peak fluxes [mJy].

    p : float
        The electron energy index.

    k : np.ndarray of float or float
        The density power-law index.

    arrays : ObsArray
        Array representation of the ``Observation`` object.

    fts : bool, optional, default=`has_fts_transition()`
        Model a fast-to-slow transition?

    jet : JetBreakModel, optional
        The jet break spectrum and smoothing parameters.
    """
    def __init__(
        self, nu_m, nu_c, f_peak, p, k, arrays,
        nu_a=None, fts=None, jet=None
    ):
        self.nu_a = nu_a
        self.nu_m = nu_m
        self.nu_c = nu_c
        self.f_peak = f_peak
        self.p = p
        self.k = k

        self.arrays = arrays
        self.has_fts = has_fts_transition(
            self.nu_m, self.nu_c) if fts is None else fts
        self.jet = jet

    @property
    def is_valid(self) -> bool:
        """ Not valid when nu_a > nu_m and nu_c. """
        if self.nu_a is not None:
            return not np.logical_and(
                self.nu_a > self.nu_m, self.nu_a > self.nu_c
            ).any()
        return True

    def model(self, subset=None) -> np.ndarray:
        """
        Model the observed spectrum using the observational
        properties in ``arrays``.

        Parameters
        ----------
        subset : np.ndarray
            The subset of data to model.

        Returns
        -------
        np.ndarray of float
            The modeled observational data.
        """
        if not self.is_valid:
            return np.array([np.nan])

        res = np.full(self.arrays.times.size, np.nan)

        if (sfm := self.arrays.sflux_loc).any():
            if subset: sfm = np.logical_and(sfm, subset)
            res[sfm] = self.spectral_flux(sfm)

        if (ifm := self.arrays.iflux_loc).any():
            if subset: ifm = np.logical_and(ifm, subset)
            res[ifm] = self.integrated_flux(ifm)

        if (sim := self.arrays.sindex_loc).any():
            if subset: sim = np.logical_and(sim, subset)
            res[sim] = self.spectral_index(sim)

        return res[subset] if subset is not None else res

    def spectral_flux(self, mask):
        """
        Models the unextinguished spectral flux.

        Parameters
        ----------
        mask : np.ndarray of bool
            The spectral flux locations.

        Returns
        -------
        np.ndarray of float
            The unextinguished spectral flux [mJy].
        """
        return SpectralFluxModel(**self.spectrum(mask)).evaluate(
            self.arrays.frequencies[mask], self.has_fts,
            self.jet.subset(mask) if self.jet else None,
        )

    def integrated_flux(self, mask):
        """
        Models the unextinguished spectral flux.

        Parameters
        ----------
        mask : np.ndarray of bool
            The integrated flux locations.

        Returns
        -------
        np.ndarray of float
            The unextinguished integrated flux [erg cm-2 s-1].
        """
        return IntegratedFluxModel(**self.spectrum(mask)).evaluate(
            self.arrays.int_lower[mask],
            self.arrays.int_upper[mask],
            self.has_fts, self.jet.subset(mask) if self.jet else None
        )

    def spectral_index(self, mask):
        """
        Models the spectral indices.

        Parameters
        ----------
        mask : np.ndarray of bool
            The spectral index locations.

        Returns
        -------
        np.ndarray of float
            The spectral indices.
        """
        return SpectralIndexModel(**self.spectrum(mask)).evaluate(
            self.arrays.int_lower[mask],
            self.arrays.int_upper[mask],
            self.has_fts, self.jet.subset(mask) if self.jet else None
        )

    def spectrum(self, mask=None):
        """
        Returns the spectrum properties as a dict and
        filters based on ``mask``.

        Parameters
        ----------
        mask : np.ndarray of bool
            The spectral index locations.

        Returns
        -------
        dict
            The spectrum properties.
        """
        k = nu_a = nu_m = nu_c = f_pk = None

        if mask is not None:
            # Can be an array for stratified mediums
            if isinstance(self.k, np.ndarray):
                k = self.k[mask]

            # All or none are arrays
            if isinstance(self.nu_m, np.ndarray):
                if self.nu_a is not None:
                    nu_a = self.nu_a[mask]
                nu_m = self.nu_m[mask]
                nu_c = self.nu_c[mask]
                f_pk = self.f_peak[mask]

        # return a masked dict representation
        return {
            'nu_a': nu_a if nu_a is not None else self.nu_a,
            'nu_m': nu_m if nu_m is not None else self.nu_m,
            'nu_c': nu_c if nu_c is not None else self.nu_c,
            'f_peak': f_pk if f_pk is not None else self.f_peak,
            'k': k if k is not None else self.k, 'p': self.p
        }


class BaseFireballModel:
    """
    Base model. Not intended for direct use.

    Implements the ultra-relativistic shock moving into an
    external medium with density rho = rho_0 * R^-k.

    Parameters
    ----------
    E52 : float
        The explosion energy normalized to 1e52 ergs.

    dL28 : float
        The luminosity distance to the event normalized to 1e28 cm.
        Requiring the distance to be provided in addition to the
        redshift prevents the need to assume a cosmology here.

    p : float
        The electron energy index. Must be > 2.

    eps_b : float
        The fraction of thermal energy in the magnetic field.
        Must be in the range [0, 1].

    eps_e : float
        The fraction of thermal energy carried by relativistic
        electrons. Must be in the range [0, 1].

    z : float
        The redshift of the event.

    hmf : float
        The hydrogen mass fraction. Must be in the range [0, 1].
        0 indicates hydrogen depleted. 1 indicates hydrogen rich.

    tj : float, optional
        The jet break time [d].

    sj, sji : float, optional
        The jet break smoothing factor. ``sji`` is the inverse
        smoothing factor. Useful for changing MCMC basis.

    use_sa : bool, optional, default=True
        Should self-absorption be modeled?

    References
    ----------
    [1] Broadband view of blast wave physics: A study
        of gamma-ray burst afterglows
    """

    # noinspection PyPep8Naming
    def __init__(self, E52, p, eps_b, eps_e, z, dL28, hmf, lf0=None, tj=None, sj=None, sji=None, use_sa=True):
        # Intrinsic properties
        self.E52 = E52
        self.p = p
        self.eps_b = eps_b
        self.eps_e = eps_e
        self.hmf = hmf
        self.lf0 = lf0

        # Extrinsic properties
        self.dL28 = dL28
        self.z = z

        # Jet properties
        self.tj = tj
        self.sj = (sj or 1 / sji) if (sj or sji) else None

        self.use_sa = use_sa

    def __repr__(self):
        """ Human-readable representation. """
        return f'{self.__class__.__name__}(E={self.E}, p={self.p}, .., z={self.z})'

    # noinspection PyPep8Naming
    @property
    def E(self):
        """ Returns the initial explosion energy [erg]. """
        return 1e52 * self.E52

    # noinspection PyPep8Naming
    @property
    def dL(self):
        """ Returns the luminosity distance [cm]. """
        return 1e28 * self.dL28

    @property
    def is_valid(self) -> bool:
        """ Whether the model is parameters are valid. """
        # Smoothing parameters are unstable around 0
        if self.sj is not None and abs(self.sj) <= 0.1:
            return False
        return ((self.eps_b + self.eps_e) < 1.0) and (self.p > 2.0)

    @property
    def radiative(self):
        """ Should radiative evolution be considered? """
        return self.eps_e > 0.4 and self.lf0 is not None

    def spectrum(self, *args, **kwargs):
        """ Placeholder. """
        raise NotImplementedError('spectrum is not implemented.')

    def jet_break(self, t):
        """
        Jet break model.

        Parameters
        ----------
        t : np.ndarray of float
            The observer times [d] used to smooth the break.

        Returns
        -------
        JetBreakModel
        """
        if self.tj is not None and self.sj is not None:
            return JetBreakModel(SpectralFluxModel(
                **self.spectrum(self.tj)), self.tj, t, self.p, self.sj)

    def spectral_flux(self, t, nu, fts=False):
        """
        Calculates the spectral fluxes at time(s) ``t`` for
        the frequencies ``nu``.

        Parameters
        ----------
        t : float or np.ndarray of float
            The observer-frame time(s) [d].

        nu : float or np.ndarray of float
            The average band frequencies [Hz].

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        Returns
        -------
        float np.ndarray of float
            The modeled spectral flux [mJy].
        """
        return SpectralFluxModel(**self.spectrum(t)).evaluate(
            nu, fts, None  # self.jet_break(t)
        )

    def integrated_flux(self, t, lower, upper, fts=False):
        """
        Calculates the integrated fluxes at time(s) ``t`` for
        the integration bounds, ``lower`` and ``upper``.

        Parameters
        ----------
        t : float or np.ndarray of float
            The observer-frame time(s) [d].

        lower, upper : float or np.ndarray of float
            The integration bounds [Hz].

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        Returns
        -------
        float or np.ndarray of float
            The modeled spectral flux [erg cm-2 s-1].
        """
        return IntegratedFluxModel(**self.spectrum(t)).evaluate(
            lower, upper, fts, None  # self.jet_break(t)
        )

    def spectral_index(self, t, lower, upper, fts=False):
        """
        Calculates the spectral indices at time(s) ``t`` for
        the integration bounds, ``lower`` and ``upper``.

        Parameters
        ----------
        t : float or np.ndarray of float
            The observer-frame time(s) [d].

        lower, upper : float or np.ndarray of float
            The integration bounds [Hz].

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        Returns
        -------
        float np.ndarray of float
            The modeled spectral index.
        """
        return SpectralIndexModel(**self.spectrum(t)).evaluate(
            lower, upper, fts, None  # self.jet_break(t)
        )


class BaseFluxModel:
    """
    Base flux model. Not intended for direct use.

    Parameters
    ----------
    f_peak : float or np.ndarray
        The peak flux [mJy].

    nu_m : float or np.ndarray
        The synchrotron frequency [Hz].

    nu_c : float or np.ndarray
        The cooling frequency [Hz].

    nu_a : float or np.ndarray
        The self-absorption frequency [Hz].

    p : float
        The electron energy power-law index.

    k : float
        The circumburst density power-law index.

    Attributes
    ----------
    slow, fast, mac, cam : np.ndarray of bool
        Bools indicating the regimes.
            - slow: nu_m < nu_c
            - fast: nu_c < nu_m
            - mac: nu_m < nu_a < nu_c
            - cam: nu_c < nu_a < nu_m
    """
    def __init__(self, nu_m, nu_c, f_peak, p, k, nu_a=None):
        self.f_peak = f_peak
        self.nu_m = np.atleast_1d(nu_m)
        self.nu_c = np.atleast_1d(nu_c)
        self.nu_a = np.atleast_1d(nu_a) if nu_a is not None else None

        if self.nu_m.size != self.nu_c.size != self.nu_a.size:
            raise ValueError(
                f'nu_m, nu_c, nu_a must have the same size: '
                f'{self.nu_m.size, self.nu_c.size, self.nu_a.size}'
            )

        self.p = p
        self.k = k

        # Determine regimes (slow, slow with self-absorption, fast)
        # TODO: Not updated when frequencies are updated. Not good
        # TODO: practice, but its faster. Revisit this before release.
        self.slow = self.nu_m < self.nu_c
        self.fast = ~self.slow

        if self.nu_a is not None:
            self.mac = np.logical_and(self.slow, nu_m < nu_a)
            self.cam = np.logical_and(self.fast, nu_c < nu_a)
        else:
            self.mac = self.cam = None

    def spectral_breaks(self) -> tuple:
        """
        Creates arrays of critical frequencies that define
        the GRB spectrum. See ``base.SpectralFlux``
        for a description of the 12, 23 notation.

        Returns
        -------
        tuple of np.ndarray of float
            The critical frequencies [Hz].
        """
        # Default: nu_a < nu_m < nu_c
        nu12 = np.array(self.nu_m, copy=True)
        nu23 = np.array(self.nu_c, copy=True)

        if self.mac is not None and self.mac.any():
            # Overwrite: nu_m < nu_a < nu_c
            nu12[self.mac] = self.nu_a[self.mac]

        if self.fast.any():
            # Overwrite: nu_a < nu_c < nu_m
            nu12[self.fast] = self.nu_c[self.fast]
            nu23[self.fast] = self.nu_m[self.fast]

            if self.cam is not None and self.cam.any():
                # Overwrite: nu_c < nu_a < nu_m
                nu12[self.cam] = self.nu_a[self.cam]

        return nu12, nu23

    def spectral_indices(self, fts=False) -> tuple:
        """
        Calculates the spectral indices.

        If ``fts==True``, smooths the middle spectral index,
        since a fast-to-slow cooling transition flips has a
        discontinuity. Smoothed spectral indices returns an
        additional index for b2 (i.e., b2 -> b2a, b2b).

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        Returns
        -------
        tuple of np.ndarray of float
            The spectral indices for each segment.
        """
        # Default: nu_a < nu_m < nu_c
        b1 = np.full(self.fast.size, 1 / 3)
        b2 = np.full(self.fast.size, (1 - self.p) / 2)
        b3 = np.full(self.fast.size, -self.p / 2)

        if self.mac is not None and self.mac.any():
            # Overwrite: nu_m < nu_a < nu_c
            b1[self.mac] = 2.5

        if self.fast.any():
            # Overwrite: nu_a < nu_c < nu_m
            b2[self.fast] = -0.5

            if self.cam is not None and self.cam.any():
                # Overwrite: nu_c < nu_a < nu_m
                b1[self.cam] = 2

        # It's important that this check is not moved into the above
        # `if fast` scope. `fts` is not determined based on the data
        # provided, but based on the entire light curve. So even if
        # the data we're modeling does not have `fts`, the greater
        # light curve may have a `fts`.
        if fts:
            return self._fts_spectral_indices(b1, b3)
        return b1, b2, b3

    def smoothing(self, fts=False):
        """
        Determines the smoothing factors for a doubly-broken spectrum.

        Smoothing factors are derived from Table 2, column s(p) in
        Granot & Sari 2002 [1]_. GS02 present smoothing factors
        for ``k=0`` and ``k=2``. The smoothing factors used here
        use a linear interpolation in ``k`` to be generic.

        Parameters
        ----------
        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        Returns
        -------
        tuple of np.ndarray of float
            The smoothing factors.

        References
        ----------
        .. [1] Granot & Sari (2002)
            https://iopscience.iop.org/article/10.1086/338966
        """
        k, p = self.k, self.p

        # Generalized s(p) from GS02 for break 2 (s12) and break 3 (s23)
        # Default: nu_a < nu_m < nu_c
        s12 = np.full(self.fast.size, 1.84 - (0.040 * k) - (0.40 - 0.010 * k) * p)
        s23 = np.full(self.fast.size, 1.15 - (0.125 * k) - (0.06 - 0.015 * k) * p)

        # Generalized s(p) from GS02 for break 5 (s12)
        if self.mac is not None and self.mac.any():
            # Overwrite: nu_m < nu_a < nu_c
            sabs_k = k[self.mac] if isinstance(k, np.ndarray) else k
            s12[self.mac] = 1.47 - 0.11 * sabs_k - (0.21 - 0.015 * sabs_k) * p

        # Generalized s(p) from GS02 for break 9 (s23) and break 11 (s12)
        if self.fast.any():
            # Overwrite: nu_a < nu_c < nu_m
            fast_k = k[self.fast] if isinstance(k, np.ndarray) else k
            s23[self.fast] = 3.34 + 0.17 * fast_k - (0.82 + 0.035 * fast_k) * p
            s12[self.fast] = 0.597

            # Generalized s(p) from GS02 for break 8 (s12)
            if self.cam is not None and self.cam.any():
                # Overwrite: nu_c < nu_a < nu_m
                s12[self.cam] = 0.9

        # It's important that this check is not moved into the above
        # `if fast` scope. `fts` is not determined based on the data
        # provided, but based on the entire light curve. So even if
        # the data we're modeling does not have `fts`, the greater
        # light curve may have a `fts`.
        if fts:
            return self._fts_smoothing(s12, s23)

        return s12, s23

    def _fts_smoothing(self, s12, s23):
        """
        Determines the smoothing factors for a doubly-broken
        spectrum with a fast-to-slow cooling transition.

        Parameters
        ----------
        s12, s23 : np.ndarray
            The smoothing factors before considering a fts
            transition.

        Returns
        -------
        tuple of np.ndarray of float
            The smoothing factors.
        """
        k, p = self.k, self.p

        b1, _, b3 = self.spectral_indices()
        nu_ratio = self.nu_m / self.nu_c

        # Transition smoother
        q12 = -s12 * (b3 - b1)
        q23 = -s23 * (b3 - b1)

        # S12 smoothing
        s12_slow = 1.84 - (0.040 * k) - (0.40 - 0.010 * k) * p
        s12 = 0.597 + (s12_slow - 0.597) / (1.0 + nu_ratio ** q12)

        # s23 smoothing
        s23_fast = 3.34 + 0.17 * k - (0.82 + 0.035 * k) * p
        s23_slow = 1.15 - (0.125 * k) - (0.06 - 0.015 * k) * p
        s23 = s23_fast + (s23_slow - s23_fast) / (1.0 + nu_ratio ** q23)

        return s12, s23

    def _fts_spectral_indices(self, b1, b3) -> tuple:
        """
        Smooths the spectral indices for a doubly-broken
        spectrum with a fast-to-slow cooling transition.

        Parameters
        ----------
        b1, b3 : np.ndarray
            The spectral indices for the first and third segment.

        Returns
        -------
        tuple of np.ndarray of float
        """
        s12, s23 = self.smoothing()
        nu_ratio = self.nu_m / self.nu_c

        # Transition smoother
        q12 = -s12 * (b3 - b1)
        q23 = -s23 * (b3 - b1)

        # Smooth the middle spectral index from -0.5 to (1 - p) / 2
        b2a = -0.5 + ((1.0 - self.p) / 2.0 + 0.5) / (1.0 + nu_ratio ** q12)
        b2b = -0.5 + ((1.0 - self.p) / 2.0 + 0.5) / (1.0 + nu_ratio ** q23)

        return b1, b2a, b2b, b3


class SpectralFluxModel(BaseFluxModel):
    """
    Spectral Fireball Flux Model

    The notation in this class is as follows:
        - b1 = spectral index of segment 1
        - s12 = smoothing between segments 1 and 2
        - nu12 = characteristic frequency at `v_12`

    F_ν
    │                     _
    │              _⎽⎽⎼⎼⎻⎻⎺⎺ ‾│‾---__
    │        _⎽⎽⎼⎼⎻⎻⎺⎺        │      ‾‾---__
    │      ╱ │            │            │\
    │     ╱  │            │            │ \
    │    ╱   │    seg 1   │    seg 2   │  \
    │   ╱    │            │            │   \
    │  ╱     │            │            │    \
    │ ╱      │            │            │
    ├───────────────────────────────────────────▶ ν
            v_0          v_1          v_2
    """
    def __init__(self, nu_m, nu_c, f_peak, p, k, nu_a=None):
        super().__init__(nu_m, nu_c, f_peak, p, k, nu_a)

    def __call__(self, *args, **kwargs):
        """ Calls the `evaluate` method. """
        return self.evaluate(*args, **kwargs)

    def model(self, val: SpectralFlux) -> float:
        """
        Models a `SpectralFlux` value using its frequency.

        Parameters
        ----------
        val : SpectralFlux
            The spectral flux value to model.

        Returns
        -------
        float
            The modeled spectral flux value.
        """
        return self.evaluate(val.frequency.value)

    def evaluate_sharp(self, nu, jet=None):
        """
        Models the spectral flux using a sharply-broken spectrum.

        Parameters
        ----------
        nu : float or np.ndarray of float
            The observed frequency [Hz].

        jet : JetBreakModel, optional
            Smooths the flux across the jet break.

        Returns
        -------
        float or np.ndarray of float
            The modeled spectral flux [mJy].
        """
        nu = np.atleast_1d(nu)
        nu12, nu23 = self.spectral_breaks()
        b1, b2, b3 = self.spectral_indices()

        res = np.full(nu12.size, self.f_peak)

        if nu.size == 1 and nu12.size != 1:
            nu = np.full(nu12.size, nu[0])

        # Segment boundaries
        seg0 = nu <= nu12
        seg1 = (nu > nu12) & (nu < nu23)
        seg2 = nu >= nu23

        # Power-law segments
        res[seg0] *= (nu[seg0] / nu12[seg0]) ** b1[seg0]
        res[seg1] *= (nu[seg1] / nu12[seg1]) ** b2[seg1]
        res[seg2] *= (nu23[seg2] / nu12[seg2]) ** b2[seg2] * (nu[seg2] / nu23[seg2]) ** b3[seg2]

        # Smooth across the jet break
        if jet is not None:
            res = jet.smooth(res, nu)  # type: ignore

        return res[0] if res.size == 1 else res

    def evaluate(self, nu, fts=False, jet=None):
        """
        Calculates the smoothed flux for frequency, `nu`.

        Supports four cases:
            (1) One ``nu`` and many spectral functions:
                Returns an array of flux with length of the
                spectral functions (i.e., nu_m.size).

            (2) Many ``nu`` and one spectral function:
                Returns an array of flux with length of ``nu``.

            (3) Many ``nu`` and many spectral functions:
                All arrays must be of the same size and the
                returned array will have the same size.

            (4) One ``nu`` and one spectral function:
                Returns a single flux value.

        Parameters
        ----------
        nu : float or np.ndarray of float
            The observed frequency [Hz].

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        jet : JetBreakModel, optional, default=None
            Smooths the flux across the jet break.

        Returns
        -------
        float or np.ndarray of float
            The modeled smoothed spectral flux [mJy].
        """
        nu = np.atleast_1d(nu)

        # Get stuff done
        nu12, nu23 = self.spectral_breaks()
        s12, s23 = self.smoothing(fts)

        # Transform for readability
        x12, x23 = nu / nu12, nu / nu23

        if fts:
            b1, b2a, b2b, b3 = self.spectral_indices(fts)
        else:
            b1, b2, b3 = self.spectral_indices()
            b2a = b2b = b2

        # Smooth the spectrum across spectral breaks
        flux = self.f_peak * (
            (x12 ** -(s12 * (b1 - b2a)) + 1) ** (s23 / s12) * x12 ** -(s23 * b2a) +
            ((nu23 / nu12) ** -(s23 * b2b)) * (x23 ** -(s23 * b3))
        ) ** -(1 / s23)

        # Apply flux normalization corrections
        if self.mac is not None and self.mac.any():
            flux = self.correct_mac_flux(flux, b2a)

        if self.cam is not None and self.cam.any():
            flux = self.correct_cam_flux(flux, nu)  # type: ignore

        # Smooth across the jet break
        if jet is not None:
            flux = jet.smooth(flux, nu, fts)  # type: ignore

        # return the smoothed spectral flux [mJy]
        return flux[0] if flux.size == 1 else flux

    def correct_mac_flux(self, flux, b2):
        """
        Applies the peak flux adjustment in the m < a < c regime.

        Parameters
        ----------
        flux : np.ndarray of float
            The flux to adjust [mJy].

        b2 : np.ndarray of float
            The spectral index of the second segment.

        Returns
        -------
        np.ndarray of float
            The corrected flux [mJy].
        """
        corr = (self.nu_a[self.mac] / self.nu_m[self.mac]) ** b2[self.mac]

        if flux.size == self.mac.size:
            flux[self.mac] *= corr
        else:
            flux *= corr

        return flux

    def correct_cam_flux(self, flux, nu):
        """
        Adjusts the flux at ``nu`` > ``nu_a`` that accounts
        for the electron pile at low frequencies.

        Parameters
        ----------
        flux : np.ndarray of float
            The flux to adjust [mJy].

        nu : np.ndarray of float
            The observed frequencies [Hz].

        Returns
        -------
        np.ndarray of float
            The corrected flux [mJy].
        """
        mask = np.logical_and(nu > self.nu_a, self.cam)

        if flux.size == self.cam.size:
            flux[mask] *= (1 / 3) * np.sqrt(self.nu_c[mask] / self.nu_a[mask])
        else:
            flux[mask] *= (1 / 3) * np.sqrt(self.nu_c / self.nu_a)

        return flux


class IntegratedFluxModel(BaseFluxModel):
    """
    Integrated Fireball Flux Model
    """
    def __init__(self, nu_m, nu_c, f_peak, p, k, nu_a=None):
        super().__init__(nu_m, nu_c, f_peak, p, k, nu_a)

    def __call__(self, *args, **kwargs):
        """ Calls the ``evaluate`` method. """
        return self.evaluate(*args, **kwargs)

    def model(self, val: IntegratedFlux):
        """
        Models an ``IntegratedFlux`` value using its integration
        range.

        Parameters
        ----------
        val : IntegratedFlux
            The Integrated flux value to model.

        Returns
        -------
        float
            The modeled integrated flux value.
        """
        return self.evaluate(
            lower=val.int_range.lower.value,
            upper=val.int_range.upper.value
        )

    def evaluate(self, lower, upper, fts=False, jet=None):
        """
        Evaluates the integrated flux model using the
        ``lower`` and ``upper`` integration limits.

        Parameters
        ----------
        lower : float or np.ndarray of float
            The lower integration limit [Hz].

        upper : float or np.ndarray of float
            The upper integration limit [Hz].

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        jet : JetBreakModel, optional, default=None
            Smooths the flux across the jet break.

        Returns
        -------
        float or np.ndarray of float
            The integrated flux [erg cm-2 s-1].
        """
        beta = SpectralIndexModel(
            self.nu_m, self.nu_c, self.f_peak, self.p, self.k, self.nu_a
        ).evaluate(lower, upper, fts, jet)

        flux = SpectralFluxModel(
            self.nu_m, self.nu_c, self.f_peak, self.p, self.k, self.nu_a
        ).evaluate(lower, fts, jet)

        # return the smoothed integrated flux [erg cm-2 s-1]
        return 1e-26 * (
            (flux * lower / (beta + 1)) *
            (((upper / lower) ** (beta + 1)) - 1)
        )


class SpectralIndexModel(BaseFluxModel):
    """
    Spectral Index Model
    """
    def __init__(self, nu_m, nu_c, f_peak, p, k, nu_a=None):
        super().__init__(nu_m, nu_c, f_peak, p, k, nu_a)

    def __call__(self, *args, **kwargs):
        """ Calls the ``evaluate`` method. """
        return self.evaluate(*args, **kwargs)

    def model(self, val: SpectralIndex):
        """
        Models a ``SpectralIndex`` value using its integration
        limits.

        Parameters
        ----------
        val : SpectralIndex
            The spectral index value to model.

        Returns
        -------
        float
            The modeled spectral index value.
        """
        return self.evaluate(
            lower=val.int_range.lower.value,
            upper=val.int_range.upper.value,
        )

    def evaluate(self, lower, upper, fts=False, jet=None):
        """
        Approximates the spectral index using a two
        point approximation.

        Parameters
        ----------
        lower : float or np.ndarray of float
            The lower integration limit [Hz].

        upper : float or np.ndarray of float
            The upper integration limit [Hz].

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        jet : JetBreakModel, optional, default=None
            Smooths the flux across the jet break.

        Returns
        -------
        float or np.ndarray of float
            The modeled spectral index.
        """
        model = SpectralFluxModel(
            self.nu_m, self.nu_c, self.f_peak, self.p, self.k, self.nu_a)

        # return the spectral index
        return (
            np.log10(
                model.evaluate(upper, fts, jet) /
                model.evaluate(lower, fts, jet)
            ) /
            np.log10(upper / lower)
        )


class JetBreakModel:
    """
    Models a jet break in the afterglow light curve.

    Parameters
    ----------
    t_jet : float
        The jet-break time [d].

    t_obs : np.ndarray of float
        The times to smooth over [d].

    p : float
        The electron energy index.

    s : float, optional, default=3
        The smoothing parameter.
    """
    def __init__(self, f_jet, t_jet, t_obs, p, s=3):
        self.f_jet = f_jet
        self.t_jet = t_jet
        self.t_obs = t_obs
        self.p = p
        self.s = s

    def __repr__(self):
        """ Human-readable representation """
        return f'JetBreakModel(t_jet={self.t_jet}, .., s={self.s})'

    def __call__(self, *args, **kwargs):
        """ Calls the smooth method. """
        return self.smooth(*args, **kwargs)

    def subset(self, mask):
        """ Returns a ``JetBreakModel`` with a subset of times. """
        return self.__class__(
            self.f_jet, self.t_jet, self.t_obs[mask], self.p, self.s
        )

    def smooth(self, f_obs, nu, fts=False):
        """
        Smooths the flux ``f_obs`` with the jet flux via
        a smoothly broken power law.

        Parameters
        ----------
        f_obs : np.ndarray of float
            The modeled jet-break flux [mJy or erg cm-2 s-1].

        nu : np.ndarray of float

        fts : bool, optional, default=False
            Is there a fast-to-slow cooling transition?

        Returns
        -------
        np.ndarray of float
            The smoothed flux [mJy or erg cm-2 s-1].
        """
        f_jet = self.f_jet(nu, fts)

        return (
            f_obs ** -self.s +
            (f_jet * (self.t_obs / self.t_jet) ** -self.p) ** -self.s
        ) ** -(1 / self.s)
