import numpy as np

from jetfit.models.powerlawVegas import powerlawVegasModel

try:
    from VegasAfterglow import Model, Medium, TophatJet
    from VegasAfterglow import Observer, Radiation
    _HAS_VEGASAFTERGLOW = True
except ImportError:
    _HAS_VEGASAFTERGLOW = False


class BubbleVegasModel(powerlawVegasModel):
    """
    VegasAfterglow adapter with a wind-bubble external medium:

      n(r) = n_t * (R_t / r)^2,          r < R_t
           = n_sh,                        R_t <= r < R_2
           = n_ism,                       r >= R_2

    where n_sh = max(4 n_t, 4 n_ism) and
    R_2 = R_t * ((n_sh + 3 n_t) / (n_sh - n_ism))^(1/3).

    Parameters are expected to be already converted to linear scale by JetFit.
    """

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
        dl28=None,
        dL28=None,
        rt=None,
        R_t=None,
        nt=None,
        n017=None,
        nism=None,
        n_ism=None,
        log10_n_t=None,
        log10_n_ism=None,
        hmf=0.7,
        mu=1.3,
        **kwargs,
    ):
        if not _HAS_VEGASAFTERGLOW:
            raise ImportError(
                "VegasAfterglow is not installed or failed to import. "
                "Install it from: https://github.com/YihanWangAstro/VegasAfterglow"
            )

        # Core jet/radiation params
        self.E_iso52 = E52 * 1e52
        self.lf0 = float(lf0)
        self.theta_c = float(theta_c)
        self.theta_v = float(theta_v)
        self.eps_e = float(eps_e)
        self.eps_b = float(eps_b)
        self.p = float(p)
        self.z = float(z)

        dl = dl28 if dl28 is not None else dL28
        if dl is None:
            raise ValueError("BubbleVegasModel requires dl28 (or dL28).")
        self.lumi_dist = float(dl) * 1e28

        # Bubble-medium params (support common aliases)
        rt_val = rt if rt is not None else R_t
        if rt_val is None:
            rt_val = 1e17
        self.rt = float(rt_val)

        nt_val = nt if nt is not None else n017
        if nt_val is None and log10_n_t is not None:
            nt_val = 10.0 ** float(log10_n_t)
        if nt_val is None:
            nt_val = 1.0
        self.nt = float(nt_val)

        nism_val = nism if nism is not None else n_ism
        if nism_val is None and log10_n_ism is not None:
            nism_val = 10.0 ** float(log10_n_ism)
        if nism_val is None:
            nism_val = 1e-2
        self.nism = float(nism_val)

        self.hmf = float(hmf)
        self.mu = float(mu)
        self.jet_type = "tophat"
        self.medium_type = "bubble"

        # Keep a stable reference radius for diagnostics.
        self.ref_radius = self.rt

        # Precompute shell quantities for profile and medium.
        self.n_sh, self.r2 = self._bubble_shell(self.nt, self.nism, self.rt)

        self._setup_model()

    @staticmethod
    def _bubble_shell(n_t, n_ism, r_t):
        """Return shell density n_sh and outer shell radius R_2."""
        n_sh = max(4.0 * n_t, 4.0 * n_ism)
        denom = n_sh - n_ism
        if denom <= 0:
            return n_sh, r_t
        r2 = r_t * ((n_sh + 3.0 * n_t) / denom) ** (1.0 / 3.0)
        return n_sh, max(r2, r_t)

    def _setup_model(self):
        """Initialize VegasAfterglow with a bubble medium profile."""
        m_p = 1.67262192e-24  # g
        m_mol = self.mu * m_p
        rt = self.rt
        r2 = self.r2
        n_t = self.nt
        n_ism = self.nism
        n_sh = self.n_sh

        def bubble_medium(phi, theta, r):
            r_arr = np.asarray(r, dtype=float)
            r_safe = np.maximum(r_arr, 1.0)

            n = np.where(
                r_safe < rt,
                n_t * (rt / r_safe) ** 2,
                np.where(r_safe < r2, n_sh, n_ism),
            )

            # Match bubble-script convention: rho = mu * m_p * n.
            rho = m_mol * n

            if np.ndim(r_arr) == 0:
                return float(np.asarray(rho))
            return rho

        jet = TophatJet(theta_c=self.theta_c, E_iso=self.E_iso52, Gamma0=self.lf0)
        observer = Observer(
            lumi_dist=self.lumi_dist,
            z=self.z,
            theta_obs=self.theta_v,
        )
        radiation = Radiation(eps_e=self.eps_e, eps_B=self.eps_b, p=self.p)

        self.vegas_model = Model(jet=jet, medium=Medium(rho=bubble_medium), observer=observer, fwd_rad=radiation)

    @property
    def is_valid(self) -> bool:
        """Check if parameters are physically valid."""
        return (
            (self.eps_b + self.eps_e) < 1.0
            and self.p >= 2.0
            and self.theta_c > 0
            and self.lf0 > 1
            and self.rt > 0
            and self.nt > 0
            and self.nism > 0
        )

    def smooth(self, t, **kwargs):
        """
        Return effective density normalization n(r) and local slope k(r)
        sampled along the modeled blast-wave radius history.
        """
        t_arr = np.atleast_1d(t)
        radii = np.asarray(self.radii(t_arr), dtype=float)
        r_safe = np.maximum(radii, 1.0)

        n_eff = np.where(
            r_safe < self.rt,
            self.nt * (self.rt / r_safe) ** 2,
            np.where(r_safe < self.r2, self.n_sh, self.nism),
        )
        k_eff = np.where(r_safe < self.rt, 2.0, 0.0)

        return n_eff, k_eff
