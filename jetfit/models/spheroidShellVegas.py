# Spheroidal wind-bubble wall model for VegasJetFit using the volume-symmetric (Method B)
# logistic transition from rho_inside = 1e-4 * rho_bubble to rho_bubble.
import math
import numpy as np

from jetfit.models.powerlawVegas import powerlawVegasModel
from jetfit.models.vegas_resolution import (
    model_kwargs_with_resolution,
    resolve_vegas_resolutions,
)

try:
    from VegasAfterglow import Model, Medium, TophatJet
    from VegasAfterglow import Observer, Radiation
    try:
        from VegasAfterglow.native import gil_free
    except ImportError:
        gil_free = None
    _HAS_VEGASAFTERGLOW = True
except ImportError:
    _HAS_VEGASAFTERGLOW = False
    gil_free = None


RHO_INSIDE_RATIO = 1.0e-4
TWO_LN_9_OVER_3 = 2.0 * math.log(9.0) / 3.0


def spheroid_bubble_radius(theta, R_wall, q):
    """
    Spheroidal midpoint radius R_bubble(theta, q):
        R_bubble(theta, q) = R_wall / sqrt(cos^2(theta) + q^2 * sin^2(theta))
    """
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    return R_wall / np.sqrt(cos_t * cos_t + (q * q) * (sin_t * sin_t))


def spheroid_shell_density_cgs(r, theta, R_wall, rho_bubble, w, q):
    """
    Vectorized/scalar evaluation of the Method B spheroidal wall density profile [g cm^-3]:
        rho(r, theta) = rho_inside + (rho_bubble - rho_inside) / (
            1 + exp(-(2 ln 9 / (3 w)) * ((r / R_bubble(theta, q))^3 - 1))
        )
    where rho_inside = 1e-4 * rho_bubble.
    """
    r_arr = np.asarray(r, dtype=float)
    r_safe = np.maximum(r_arr, 1.0)
    r_bub = spheroid_bubble_radius(theta, R_wall, q)
    u3_minus_1 = (r_safe / r_bub) ** 3 - 1.0
    z = -(TWO_LN_9_OVER_3 / w) * u3_minus_1
    z_clipped = np.clip(z, -500.0, 500.0)
    s = 1.0 / (1.0 + np.exp(z_clipped))
    rho_inside = RHO_INSIDE_RATIO * rho_bubble
    rho = rho_inside + (rho_bubble - rho_inside) * s
    if np.ndim(r) == 0 and np.ndim(theta) == 0:
        return float(np.asarray(rho))
    return rho


if gil_free is not None:
    @gil_free
    def spheroid_shell_medium_native(phi, theta, r, R_wall, rho_bubble, w, q):
        r_safe = r if r > 1.0 else 1.0
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        denom = math.sqrt(cos_theta * cos_theta + q * q * sin_theta * sin_theta)

        # u = r / R_bubble(theta, q) = r * sqrt(cos^2(theta) + q^2 * sin^2(theta)) / R_wall
        u = r_safe * denom / R_wall
        u3_minus_1 = u * u * u - 1.0

        # z = -(2 * ln(9) / (3 * w)) * (u^3 - 1)
        z = -(1.464816384890813 / w) * u3_minus_1

        if z > 500.0:
            s = 0.0
        elif z < -500.0:
            s = 1.0
        else:
            s = 1.0 / (1.0 + math.exp(z))

        rho_inside = 1.0e-4 * rho_bubble
        return rho_inside + (rho_bubble - rho_inside) * s
else:
    spheroid_shell_medium_native = None


class SpheroidShellVegasModel(powerlawVegasModel):
    """
    VegasAfterglow adapter for the spheroidal wind-bubble conduction wall (Method B):

        R_bubble(theta, q) = R_wall / sqrt(cos^2(theta) + q^2 * sin^2(theta))

        rho(r, theta) = rho_inside + (rho_bubble - rho_inside) / (
            1 + exp(-2 * ln(9) / (3 * w) * ((r / R_bubble(theta, q))^3 - 1))
        )

    with rho_inside fixed to 10^-4 * rho_bubble.
    """

    RHO_INSIDE_RATIO = RHO_INSIDE_RATIO

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
        R_wall=None,
        R_pole=None,
        R_bubble=None,
        rho_bubble=None,
        n_bubble=None,
        n_wall=None,
        n_ism=None,
        w=None,
        eps=None,
        q=1.0,
        dl28=None,
        dL28=None,
        hmf=0.7,
        mu=1.0,
        **kwargs
    ):
        dl = dl28 if dl28 is not None else dL28
        if dl is None:
            raise ValueError("SpheroidShellVegasModel requires dl28 (or dL28).")

        # Standard physics attributes (already linear from JetFit MCMC)
        self.E_iso52 = float(E52) * 1e52
        self.lf0 = float(lf0)
        self.theta_c = float(theta_c)
        self.theta_v = float(theta_v)
        self.eps_e = float(eps_e)
        self.eps_b = float(eps_b)
        self.p = float(p)
        self.z = float(z)
        self.lumi_dist = float(dl) * 1e28

        self.hmf = float(hmf)
        self.mu = float(mu)
        m_p = 1.67262192e-24
        self.m_mol = self.mu * m_p

        # Resolve polar wall radius R_wall [cm] (accept R_wall, R_pole, or R_bubble)
        r_wall_val = R_wall if R_wall is not None else (R_pole if R_pole is not None else R_bubble)
        if r_wall_val is None:
            raise ValueError("SpheroidShellVegasModel requires R_wall (or alias R_pole / R_bubble).")
        self.R_wall = float(r_wall_val)
        self.R_pole = self.R_wall

        # Resolve transition fractional width w (accept w or legacy eps)
        w_val = w if w is not None else eps
        if w_val is None:
            raise ValueError("SpheroidShellVegasModel requires transition width w.")
        self.w = float(w_val)

        # Resolve spheroid axis ratio q = c / a
        self.q = float(q)

        # Resolve wall density rho_bubble [g cm^-3] (or convert from number density if n_bubble is passed)
        if rho_bubble is not None:
            self.rho_bubble = float(rho_bubble)
            self.n_bubble = self.rho_bubble / self.m_mol
        else:
            n_val = n_bubble if n_bubble is not None else (n_wall if n_wall is not None else n_ism)
            if n_val is None:
                raise ValueError(
                    "SpheroidShellVegasModel requires rho_bubble (or number density n_bubble)."
                )
            self.n_bubble = float(n_val)
            self.rho_bubble = self.m_mol * self.n_bubble

        # Fixed inner density ratio: rho_inside = 10^-4 * rho_bubble
        self.rho_inside = self.RHO_INSIDE_RATIO * self.rho_bubble
        self.n_inside = self.RHO_INSIDE_RATIO * self.n_bubble

        self.jet_type = "tophat"
        self.medium_type = "spheroid_shell"
        self.ref_radius = self.R_wall

        self.vegas_resolutions = resolve_vegas_resolutions(
            vegas_resolutions=kwargs.get('vegas_resolutions'),
            vegas_resolution_phi=kwargs.get('vegas_resolution_phi'),
            vegas_resolution_theta=kwargs.get('vegas_resolution_theta'),
            vegas_resolution_t=kwargs.get('vegas_resolution_t')
        )

        self._setup_model()

    def _setup_model(self):
        if not _HAS_VEGASAFTERGLOW:
            raise ImportError("VegasAfterglow is not installed or failed to import.")

        # Standard Tophat Jet
        self.vegas_jet = TophatJet(
            theta_c=self.theta_c,
            E_iso=self.E_iso52,
            Gamma0=self.lf0,
        )

        # Medium setup
        if spheroid_shell_medium_native is not None:
            self.vegas_medium = Medium(
                rho=spheroid_shell_medium_native(
                    R_wall=self.R_wall,
                    rho_bubble=self.rho_bubble,
                    w=self.w,
                    q=self.q,
                )
            )
        else:
            def spheroid_shell_medium(phi, theta, r):
                return spheroid_shell_density_cgs(
                    r=r,
                    theta=theta,
                    R_wall=self.R_wall,
                    rho_bubble=self.rho_bubble,
                    w=self.w,
                    q=self.q,
                )

            self.vegas_medium = Medium(rho=spheroid_shell_medium)

        self.vegas_observer = Observer(
            lumi_dist=self.lumi_dist,
            z=self.z,
            theta_obs=self.theta_v,
        )

        self.vegas_radiation = Radiation(
            eps_e=self.eps_e,
            eps_B=self.eps_b,
            p=self.p,
        )

        self.vegas_model = Model(
            **model_kwargs_with_resolution(
                jet=self.vegas_jet,
                medium=self.vegas_medium,
                observer=self.vegas_observer,
                radiation=self.vegas_radiation,
                resolutions=self.vegas_resolutions,
            )
        )

    @property
    def is_valid(self) -> bool:
        """Check if model parameters are physically valid."""
        return (
            (self.eps_b + self.eps_e) < 1.0
            and self.p >= 2.0
            and self.theta_c > 0.0
            and self.lf0 > 1.0
            and self.R_wall > 0.0
            and self.rho_bubble > 0.0
            and self.w > 0.0
            and self.q > 0.0
        )

    def mass_density_cgs(self, radius_cm, theta=0.0):
        """Return mass density rho(r, theta) [g cm^-3] (defaults to polar axis theta=0)."""
        return spheroid_shell_density_cgs(
            r=radius_cm,
            theta=theta,
            R_wall=self.R_wall,
            rho_bubble=self.rho_bubble,
            w=self.w,
            q=self.q,
        )

    def number_density_cm3(self, radius_cm, theta=0.0):
        """Return number density n(r, theta) [cm^-3] along polar angle theta (default 0)."""
        return self.mass_density_cgs(radius_cm, theta=theta) / self.m_mol

    def local_k(self, radius_cm, theta=0.0):
        """Return local logarithmic density slope k(r, theta) = -d ln(rho) / d ln(r)."""
        r_arr = np.asarray(radius_cm, dtype=float)
        r_safe = np.maximum(r_arr, 1.0)
        r_bub = spheroid_bubble_radius(theta, self.R_wall, self.q)
        u3 = (r_safe / r_bub) ** 3
        z = -(TWO_LN_9_OVER_3 / self.w) * (u3 - 1.0)
        z_clipped = np.clip(z, -500.0, 500.0)
        s = 1.0 / (1.0 + np.exp(z_clipped))

        # dS / d ln(r) = (2 ln 9 / w) * u^3 * S * (1 - S)
        ds_dlnr = (3.0 * TWO_LN_9_OVER_3 / self.w) * u3 * s * (1.0 - s)
        delta_rho = self.rho_bubble - self.rho_inside
        rho = self.rho_inside + delta_rho * s
        k_eff = -(delta_rho * ds_dlnr) / np.maximum(rho, 1.0e-300)
        if np.ndim(radius_cm) == 0 and np.ndim(theta) == 0:
            return float(np.asarray(k_eff))
        return k_eff

    def smooth(self, t, **kwargs):
        """Return n(r) and local k(r) sampled along the on-axis blast-wave radius history."""
        t_arr = np.atleast_1d(t)
        radii = np.asarray(self.radii(t_arr), dtype=float)
        n_eff = self.number_density_cm3(radii, theta=0.0)
        k_eff = self.local_k(radii, theta=0.0)
        return n_eff, k_eff

