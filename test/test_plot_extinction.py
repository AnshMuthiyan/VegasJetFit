import unittest

import numpy as np
from dust_extinction.parameter_averages import CCM89

from scripts.plot.visualize import (
    PROTON_MASS_G,
    density_shell_properties,
    model_galactic_extinction,
    model_extinction,
    powerlaw_density_shell_properties,
)

from jetfit.mcmc.trotter_extinction import trotter_source_attenuation


class TestPlotExtinction(unittest.TestCase):
    def test_trotter_plot_path_matches_likelihood_attenuation(self):
        class Wave:
            def __init__(self, value):
                self.value = value

            def to_value(self, unit):
                return self.value

        data = [
            type("Datum", (), {"wavelength": Wave(value)})()
            for value in (1.0, 0.4, 0.15)
        ]
        extinction = {
            "av_source_frame": 0.6,
            "c2": 1.0,
            "c4": 0.4,
            "ebv_milky_way": 0.0,
        }
        params = {"model": {"z": 0.544}, "extinction": extinction, "host": None}
        actual = model_extinction(np.ones(3), CCM89(Rv=3.1), data, params)
        expected = trotter_source_attenuation(
            1.544 * np.array([1.0, 2.5, 1.0 / 0.15]), extinction
        )
        np.testing.assert_allclose(actual, expected)

    def test_mixed_band_vector_applies_milky_way_extinction_per_band(self):
        """Radio/X-ray entries must not disable the optical correction."""
        wavenumbers = np.array([1.0e-4, 1.25, 2.0, 15.0])
        ebv = 1.3021
        rv = 2.46422

        actual = model_galactic_extinction(wavenumbers, CCM89(Rv=3.1), ebv, rv)
        expected = np.ones_like(wavenumbers)
        valid = (CCM89.x_range[0] < wavenumbers) & (wavenumbers < CCM89.x_range[1])
        expected[valid] = CCM89(Rv=rv).extinguish(wavenumbers[valid], Ebv=ebv)

        np.testing.assert_allclose(actual, expected)
        self.assertEqual(actual[0], 1.0)
        self.assertEqual(actual[-1], 1.0)
        self.assertLess(actual[1], 1.0)
        self.assertLess(actual[2], 1.0)


class TestDensityShellMass(unittest.TestCase):
    def test_constant_density_shell_recovers_analytic_mass_and_mean_density(self):
        radius = np.linspace(2.0, 7.0, 10_001)
        number_density = np.full_like(radius, 3.5)
        result = density_shell_properties(radius, number_density)
        self.assertIsNotNone(result)
        assert result is not None
        volume = (4.0 * np.pi / 3.0) * (7.0 ** 3 - 2.0 ** 3)
        np.testing.assert_allclose(result["shell_mass_g"], PROTON_MASS_G * 3.5 * volume, rtol=2.0e-9)
        np.testing.assert_allclose(result["mean_number_density_cm3"], 3.5, rtol=2.0e-9)
        np.testing.assert_allclose(result["mean_mass_density_g_cm3"], PROTON_MASS_G * 3.5, rtol=2.0e-9)

    def test_powerlaw_shell_matches_dense_numerical_integration(self):
        r_inner, r_outer, n017, k = 2.0e16, 8.0e18, 4.2, -2.7
        radius = np.geomspace(r_inner, r_outer, 100_001)
        density = n017 * (radius / 1.0e17) ** (-k)
        numerical = density_shell_properties(radius, density)
        analytic = powerlaw_density_shell_properties(r_inner, r_outer, n017, k)
        self.assertIsNotNone(numerical)
        self.assertIsNotNone(analytic)
        assert numerical is not None and analytic is not None
        np.testing.assert_allclose(analytic["shell_mass_g"], numerical["shell_mass_g"], rtol=1.0e-8)
        np.testing.assert_allclose(
            analytic["mean_number_density_cm3"],
            analytic["shell_mass_g"] / (PROTON_MASS_G * analytic["shell_volume_cm3"]),
            rtol=1.0e-12,
        )
