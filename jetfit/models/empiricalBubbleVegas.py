import math
import numpy as np

from jetfit.models.bubbleVegas import BubbleVegasModel, _HAS_VEGASAFTERGLOW, gil_free
from jetfit.models.vegas_resolution import model_kwargs_with_resolution
from jetfit.models.empiricalBubbleProfile import (
    PSI_BLEND_START,
    PSI_BLEND_VALUE,
    empirical_local_k,
    empirical_number_density_cm3,
)

try:
    from VegasAfterglow import Model, Medium, Observer, Radiation, TophatJet
except ImportError:
    Model = Medium = Observer = Radiation = TophatJet = None


if gil_free is not None:
    @gil_free
    def empirical_bubble_medium_native(phi, theta, r, rt, r2, n_t, n_ism, m_mol):
        """GIL-free scalar empirical-bubble density profile for VegasAfterglow."""
        r_safe = r if r > 1.0 else 1.0
        if r_safe < rt:
            n = n_t * math.pow(rt / r_safe, 2.0)
            return m_mol * n

        if r_safe >= r2:
            return m_mol * n_ism

        delta_r = r2 - rt if r2 > rt else 1.0e-30
        x = (r_safe - rt) / delta_r

        if x <= 0.02:
            psi = 0.0
        elif x <= 0.05:
            psi = (x - 0.02) * (-0.02387276) / 0.03
        elif x <= 0.10:
            psi = -0.02387276 + (x - 0.05) * (-0.02557549 + 0.02387276) / 0.05
        elif x <= 0.15:
            psi = -0.02557549 + (x - 0.10) * (-0.05940523 + 0.02557549) / 0.05
        elif x <= 0.20:
            psi = -0.05940523 + (x - 0.15) * (-0.29653253 + 0.05940523) / 0.05
        elif x <= 0.35:
            psi = -0.29653253 + (x - 0.20) * (-0.53368392 + 0.29653253) / 0.15
        elif x <= 0.50:
            psi = -0.53368392 + (x - 0.35) * (-0.62300054 + 0.53368392) / 0.15
        elif x <= 0.65:
            psi = -0.62300054 + (x - 0.50) * (-1.09729905 + 0.62300054) / 0.15
        elif x <= 0.72:
            psi = -1.09729905 + (x - 0.65) * (-1.10627881 + 1.09729905) / 0.07
        elif x <= 0.78:
            psi = -1.10627881 + (x - 0.72) * (-1.09210474 + 1.10627881) / 0.06
        elif x <= PSI_BLEND_START:
            psi = -1.09210474 + (x - 0.78) * (PSI_BLEND_VALUE + 1.09210474) / 0.04
        elif x < 1.0:
            u = (x - PSI_BLEND_START) / (1.0 - PSI_BLEND_START)
            s = u * u * (3.0 - 2.0 * u)
            psi = (1.0 - s) * PSI_BLEND_VALUE + s
        else:
            psi = 1.0

        log_inner = math.log10(max(4.0 * n_t, 1.0e-300))
        log_outer = math.log10(max(n_ism, 1.0e-300))
        n = math.pow(10.0, log_inner + (log_outer - log_inner) * psi)
        return m_mol * n
else:
    empirical_bubble_medium_native = None


class EmpiricalBubbleVegasModel(BubbleVegasModel):
    """
    VegasAfterglow adapter with the calibrated three-parameter empirical bubble.

    The fit parameters remain ``rt``, ``nt``, and ``nism``. The simple bubble
    closure still defines the outer radius ``R2``; only the inter-shock density
    profile is replaced by the smooth empirical ``psi(x)`` calibration derived
    from the AMRVAC ``density_21`` profile.
    """

    def _setup_model(self):
        if not _HAS_VEGASAFTERGLOW:
            raise ImportError(
                "VegasAfterglow is not installed or failed to import. "
                "Install it from: https://github.com/YihanWangAstro/VegasAfterglow"
            )

        self.medium_type = "empirical_bubble"

        m_p = 1.67262192e-24
        m_mol = self.mu * m_p
        rt = self.rt
        r2 = self.r2
        n_t = self.nt
        n_ism = self.nism

        if empirical_bubble_medium_native is not None:
            medium = Medium(
                rho=empirical_bubble_medium_native(
                    rt=rt,
                    r2=r2,
                    n_t=n_t,
                    n_ism=n_ism,
                    m_mol=m_mol,
                )
            )
        else:
            def empirical_bubble_medium(phi, theta, r):
                number_density = empirical_number_density_cm3(
                    radius_cm=r,
                    rt_cm=rt,
                    nt_cm3=n_t,
                    nism_cm3=n_ism,
                    r2_cm=r2,
                )
                rho = m_mol * number_density
                if np.ndim(np.asarray(r)) == 0:
                    return float(np.asarray(rho))
                return rho

            medium = Medium(rho=empirical_bubble_medium)

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

    def smooth(self, t, **kwargs):
        """
        Return n(r) and local k(r) sampled along the VegasAfterglow radius track.
        """
        t_arr = np.atleast_1d(t)
        radii = np.asarray(self.radii(t_arr), dtype=float)
        n_eff = empirical_number_density_cm3(
            radius_cm=radii,
            rt_cm=self.rt,
            nt_cm3=self.nt,
            nism_cm3=self.nism,
            r2_cm=self.r2,
        )
        k_eff = empirical_local_k(
            radius_cm=radii,
            rt_cm=self.rt,
            nt_cm3=self.nt,
            nism_cm3=self.nism,
            r2_cm=self.r2,
        )
        return n_eff, k_eff
