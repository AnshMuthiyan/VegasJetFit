import math
import numpy as np

from jetfit.models.powerlawVegas import powerlawVegasModel
from jetfit.models.vegas_resolution import resolve_vegas_resolutions

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


if gil_free is not None:
    @gil_free
    def spheroid_shell_medium_native(phi, theta, r, R_pole, n_ism, eps, q, n_cav, m_mol):
        r_safe = r if r > 1.0 else 1.0
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        q2 = q * q
        
        # denom = sqrt(cos^2 + q^2 * sin^2)
        denom = math.sqrt(cos_theta * cos_theta + q2 * sin_theta * sin_theta)
        
        R_outer = R_pole / denom
        R_inner = (1.0 - eps) * R_outer
        
        if r_safe > R_outer:
            n = n_ism
        elif r_safe >= R_inner:
            # n_sh = n_ism / (1 - (1-eps)^3)
            eps_factor = 1.0 - eps
            n = n_ism / (1.0 - eps_factor * eps_factor * eps_factor)
        else:
            n = n_cav
            
        return m_mol * n
else:
    spheroid_shell_medium_native = None


class SpheroidShellVegasModel(powerlawVegasModel):
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
        R_pole=None,
        n_ism=None,
        eps=None,
        q=None,
        n_cav=1e-2,
        dl28=None,
        dL28=None,
        hmf=0.7,
        mu=1.0,
        **kwargs
    ):
        dl = dl28 if dl28 is not None else dL28
        
        # Standard physics attributes
        self.E_iso52 = E52 * 1e52
        self.lf0 = float(lf0)
        self.theta_c = float(theta_c)
        self.theta_v = float(theta_v)
        self.eps_e = float(eps_e)
        self.eps_b = float(eps_b)
        self.p = float(p)
        self.z = float(z)
        self.lumi_dist = float(dl) * 1e28
        
        # New model parameters (already linear from JetFit MCMC)
        self.R_pole = float(R_pole)
        self.n_ism = float(n_ism)
        self.eps = float(eps)
        self.q = float(q)
        self.n_cav = float(n_cav)
        
        self.hmf = float(hmf)
        self.mu = float(mu)
        self.jet_type = "tophat"
        self.medium_type = "spheroid_shell"
        self.ref_radius = self.R_pole
        
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

        m_p = 1.67262192e-24
        m_mol = self.mu * m_p

        # Standard Tophat Jet
        self.vegas_jet = TophatJet(self.theta_c, self.E_iso52, self.lf0)

        # Medium setup
        self.vegas_medium = Medium(
            rho=spheroid_shell_medium_native(
                R_pole=self.R_pole,
                n_ism=self.n_ism,
                eps=self.eps,
                q=self.q,
                n_cav=self.n_cav,
                m_mol=m_mol
            )
        )

        self.vegas_observer = Observer(self.theta_v, self.lumi_dist, self.z)

        # Standard radiation physics setup
        if self.hmf is not None:
            self.vegas_radiation = Radiation(self.eps_e, self.eps_b, self.p, self.hmf)
        else:
            self.vegas_radiation = Radiation(self.eps_e, self.eps_b, self.p)

        from jetfit.models.vegas_resolution import model_kwargs_with_resolution

        self.vegas_model = Model(
            **model_kwargs_with_resolution(
                jet=self.vegas_jet,
                medium=self.vegas_medium,
                observer=self.vegas_observer,
                radiation=self.vegas_radiation,
                resolutions=self.vegas_resolutions
            )
        )

    def number_density_cm3(self, radius_cm):
        # Simplistic 1D representation for plotting if needed (returns along polar axis)
        R_outer = self.R_pole
        R_inner = (1.0 - self.eps) * R_outer
        n = np.zeros_like(radius_cm)
        n[radius_cm > R_outer] = self.n_ism
        eps_factor = 1.0 - self.eps
        n_sh = self.n_ism / (1.0 - eps_factor**3)
        n[(radius_cm <= R_outer) & (radius_cm >= R_inner)] = n_sh
        n[radius_cm < R_inner] = self.n_cav
        return n
