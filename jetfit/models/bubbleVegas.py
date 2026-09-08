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


if gil_free is not None:
    @gil_free
    def bubble_medium_native(phi, theta, r, rt, r2, n_t, n_sh, n_ism, m_mol):
        """GIL-free scalar bubble density profile for the VegasAfterglow hot loop."""
        r_safe = r if r > 1.0 else 1.0
        if r_safe < rt:
            n = n_t * math.pow(rt / r_safe, 2.0)
        elif r_safe < r2:
            n = n_sh
        else:
            n = n_ism
        return m_mol * n
else:
    bubble_medium_native = None


class BubbleVegasModel(powerlawVegasModel):
    """
    VegasAfterglow adapter with a wind-bubble external medium:

      n(r) = n_t * (R_t / r)^2,          r < R_t
           = n_sh,                        R_t <= r < R_2
           = n_ism,                       r >= R_2

    where n_sh = 4 n_t at the termination shock (strong-shock jump condition).
    R_2 is solved so the spherical shell mass integral matches the original
    max-shell prescription used in Wind_Bubble_Model.py.

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
        vegas_resolutions=None,
        vegas_resolution_phi=None,
        vegas_resolution_theta=None,
        vegas_resolution_t=None,
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
        self.vegas_resolutions = resolve_vegas_resolutions(
            vegas_resolutions=vegas_resolutions,
            vegas_resolution_phi=vegas_resolution_phi,
            vegas_resolution_theta=vegas_resolution_theta,
            vegas_resolution_t=vegas_resolution_t,
        )

        # Keep a stable reference radius for diagnostics.
        self.ref_radius = self.rt

        # Precompute shell quantities for profile and medium.
        self.n_sh, self.r2 = self._bubble_shell(self.nt, self.nism, self.rt)

        self._setup_model()

    @staticmethod
    def _bubble_shell(n_t, n_ism, r_t):
        """Return shell density n_sh and outer shell radius R_2."""
        n_sh = 4.0 * n_t
        tiny = 1e-300

        # Match the original bubble-shell total mass from Wind_Bubble_Model.py:
        #   n_sh_old = max(4 n_t, 4 n_ism)
        #   R2_old = R_t * ((n_sh_old + 3 n_t)/(n_sh_old - n_ism))^(1/3)
        # and enforce:
        #   ∫_{R_t}^{R2_new} n_sh * 4πr^2 dr = ∫_{R_t}^{R2_old} n_sh_old * 4πr^2 dr
        n_sh_old = max(4.0 * n_t, 4.0 * n_ism)
        denom_old = max(n_sh_old - n_ism, tiny)
        ratio_old = (n_sh_old + 3.0 * n_t) / denom_old
        r2_old = r_t * max(ratio_old, 1.0 + 1e-12) ** (1.0 / 3.0)

        delta_old = max(r2_old**3 - r_t**3, 0.0)
        r2_cubed = r_t**3 + (n_sh_old / max(n_sh, tiny)) * delta_old
        r2 = max(r2_cubed, r_t**3 * (1.0 + 1e-12)) ** (1.0 / 3.0)
        return n_sh, r2

    def _setup_model(self):
        """Initialize VegasAfterglow with a bubble medium profile."""
        m_p = 1.67262192e-24  # g
        m_mol = self.mu * m_p
        rt = self.rt
        r2 = self.r2
        n_t = self.nt
        n_ism = self.nism
        n_sh = self.n_sh

        if bubble_medium_native is not None:
            medium = Medium(
                rho=bubble_medium_native(
                    rt=rt,
                    r2=r2,
                    n_t=n_t,
                    n_sh=n_sh,
                    n_ism=n_ism,
                    m_mol=m_mol,
                )
            )
        else:
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

            medium = Medium(rho=bubble_medium)

        jet = TophatJet(theta_c=self.theta_c, E_iso=self.E_iso52, Gamma0=self.lf0)
        observer = Observer(
            lumi_dist=self.lumi_dist,
            z=self.z,
            theta_obs=self.theta_v,
        )
        radiation = Radiation(eps_e=self.eps_e, eps_B=self.eps_b, p=self.p)

        self.vegas_model = Model(
            **model_kwargs_with_resolution(
                jet=jet,
                medium=medium,
                observer=observer,
                radiation=radiation,
                resolutions=self.vegas_resolutions,
            )
        )

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
