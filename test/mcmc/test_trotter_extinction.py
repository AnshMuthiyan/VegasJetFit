import unittest

import numpy as np

from jetfit.mcmc.mcmc import MCMCModels
from jetfit.mcmc.trotter_extinction import (
    TrotterDustPrior,
    trotter_source_attenuation,
)


def dust_params(**updates):
    params = {
        "av_source_frame": 1.0,
        "c2": 1.0,
        "c4": 0.5,
        "delta_c2_c1": 0.0,
        "delta_c1": 0.0,
        "delta_c2_rv": 0.0,
        "delta_rv": 0.0,
        "delta_c2_bh": 0.0,
        "delta_bh": 0.0,
        "delta_x0": 0.0,
        "delta_gamma": 0.0,
    }
    params.update(updates)
    return params


class TestTrotterDustPhysics(unittest.TestCase):
    def test_zero_av_is_identity(self):
        x = np.array([0.1, 0.5, 1.82, 3.3, 5.9, 8.0, 20.0])
        np.testing.assert_allclose(
            trotter_source_attenuation(x, dust_params(av_source_frame=0.0)),
            np.ones_like(x),
        )

    def test_model_is_continuous_at_ccm_fm_boundaries(self):
        params = dust_params()
        for boundary in (1.82, 3.3):
            values = trotter_source_attenuation(
                np.array([boundary - 1.0e-7, boundary, boundary + 1.0e-7]), params
            )
            np.testing.assert_allclose(values, values[1], rtol=2.0e-6, atol=1.0e-10)

    def test_c4_changes_only_far_uv_term(self):
        x = np.array([2.0, 5.8, 6.5, 9.0])
        without = trotter_source_attenuation(x, dust_params(c4=0.0))
        with_c4 = trotter_source_attenuation(x, dust_params(c4=2.0))
        np.testing.assert_allclose(without[:2], with_c4[:2])
        self.assertTrue(np.all(with_c4[2:] < without[2:]))

    def test_each_horizontal_scatter_term_changes_only_its_relation(self):
        prior = TrotterDustPrior()
        base = np.asarray(prior.get_physical_dust_params(1.0, dust_params()))
        mapping = {
            "delta_c2_c1": 0,
            "delta_c2_rv": 1,
            "delta_c2_bh": 2,
        }
        for name, changed_index in mapping.items():
            changed = np.asarray(
                prior.get_physical_dust_params(1.0, dust_params(**{name: 0.05}))
            )
            differing = np.flatnonzero(~np.isclose(base, changed))
            np.testing.assert_array_equal(differing, [changed_index])

    def test_prior_rejects_nonphysical_derived_parameters(self):
        prior = TrotterDustPrior()
        self.assertTrue(np.isfinite(prior.log_prior(dust_params())))
        self.assertEqual(prior.log_prior(dust_params(delta_bh=-20.0)), -np.inf)
        self.assertEqual(prior.log_prior(dust_params(delta_gamma=-2.0)), -np.inf)

    def test_asymmetric_gaussian_uses_thesis_normalization(self):
        x = np.linspace(-1.0, 1.0, 200_001)
        density = np.exp(TrotterDustPrior._asymmetric_logpdf(x, 0.17, 0.11))
        np.testing.assert_allclose(np.trapezoid(density, x), 1.0, rtol=1.0e-7)


class TestTrotterDustLikelihoodWiring(unittest.TestCase):
    def test_trotter_parameters_change_modeled_flux(self):
        arrays = type("Arrays", (), {"wave_numbers": np.array([1.0, 2.5, 6.5])})()
        observation = type(
            "Observation",
            (),
            {
                "extinguishable": np.array([True, True, True], dtype=bool),
                "as_arrays": arrays,
                "hosts": None,
            },
        )()
        wrapper = MCMCModels(
            observation, afg_model=None, ext_model=None
        )
        base = {
            "model": {"z": 0.544},
            "extinction": dust_params(c2=0.8),
            "host": None,
        }
        changed = {
            "model": {"z": 0.544},
            "extinction": dust_params(c2=1.2),
            "host": None,
        }
        flux_base = wrapper.model_extinction(np.ones(3), base)
        flux_changed = wrapper.model_extinction(np.ones(3), changed)
        self.assertFalse(np.allclose(flux_base, flux_changed))
        self.assertTrue(np.all((flux_base > 0.0) & (flux_base <= 1.0)))
        self.assertTrue(np.all((flux_changed > 0.0) & (flux_changed <= 1.0)))


if __name__ == "__main__":
    unittest.main()
