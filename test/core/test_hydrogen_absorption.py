import unittest

import numpy as np

from jetfit.core.hydrogen_absorption import (
    LYMAN_ALPHA_FREQUENCY_HZ,
    LYMAN_LIMIT_ANGSTROM,
    hydrogen_transmission,
    inoue2014_igm_optical_depth,
    inoue2014_igm_transmission,
    trotter2011_igm_filter_transmission,
    trotter2011_host_dla_delta_log10_flux,
    trotter2011_host_hi_transmission,
)
from jetfit.models.trotter_lyman_alpha import calculate_igm_transmission


class Inoue2014Tests(unittest.TestCase):
    def test_matches_independent_eazy_reference_values(self):
        # Generated with eazy.igm.Inoue14 and its published coefficient tables.
        wavelength = np.array([1500.0, 2246.9531, 4000.0, 5000.0, 7648.3071])
        expected = {
            0.97: [0.7516501542865284, 0.9647682208515884, 1.0, 1.0, 1.0],
            2.198: [0.2877484517470973, 0.3773969129181326, 1.0, 1.0, 1.0],
            4.61: [0.00782212818351546, 0.0026781128196683565,
                   0.002430067579194259, 0.10141482546475075, 1.0],
            6.318: [8.610550862642633e-05, 5.103341924260091e-06,
                    2.7494623094191428e-08, 2.3032227168605475e-08,
                    0.07805034564791977],
        }
        for redshift, reference in expected.items():
            np.testing.assert_allclose(
                inoue2014_igm_transmission(wavelength, redshift),
                reference,
                rtol=2.0e-13,
                atol=0.0,
            )

    def test_redward_of_source_lyman_alpha_is_unabsorbed(self):
        redshift = 3.0
        wavelength = np.array([1215.67 * (1.0 + redshift), 6000.0])
        np.testing.assert_array_equal(
            inoue2014_igm_transmission(wavelength, redshift),
            np.ones(2),
        )

    def test_observed_wavelength_below_a_line_does_not_use_negative_redshift(self):
        # Inoue et al. Eq. 20 requires lambda_j < lambda_obs.  Ly-alpha
        # therefore contributes nothing at 1000 A, while higher Lyman lines do.
        tau_all = inoue2014_igm_optical_depth(1000.0, 0.97)
        self.assertTrue(np.isfinite(tau_all))
        self.assertGreater(tau_all, 0.0)
        self.assertLess(tau_all, 1.0)

    def test_values_are_bounded_and_zero_redshift_is_unity(self):
        wavelength = np.geomspace(920.0, 20000.0, 500)
        transmission = inoue2014_igm_transmission(wavelength, 6.318)
        self.assertTrue(np.all(np.isfinite(transmission)))
        self.assertTrue(np.all((transmission >= 0.0) & (transmission <= 1.0)))
        np.testing.assert_array_equal(
            inoue2014_igm_transmission(wavelength, 0.0),
            np.ones_like(wavelength),
        )


class Trotter2011IGMTests(unittest.TestCase):
    def test_filter_transmission_matches_equation_3_46_and_lyman_limit(self):
        redshift = 3.375
        wavelength = np.array([3500.0, 4500.0, 6000.0])
        actual = trotter2011_igm_filter_transmission(
            wavelength, redshift, z_f=2.7, delta_z_f=0.4, delta_igm=0.1
        )
        expected_filter = calculate_igm_transmission(2.7, 0.4, 0.1)
        np.testing.assert_allclose(
            actual,
            np.array([0.0, expected_filter, expected_filter]),
        )

    def test_user_facing_selector_dispatches_trotter(self):
        wavelength = np.array([4500.0, 5000.0])
        actual = hydrogen_transmission(
            wavelength,
            3.375,
            igm_model='trotter2011',
            igm_z_f=2.7,
            igm_delta_z_f=0.4,
            igm_delta=0.0,
        )
        expected = trotter2011_igm_filter_transmission(
            wavelength, 3.375, 2.7, 0.4, 0.0
        )
        np.testing.assert_allclose(actual, expected)

    def test_forest_overlap_requires_filter_coordinates(self):
        with self.assertRaisesRegex(ValueError, 'requires igm_z_f'):
            hydrogen_transmission(
                4500.0, 3.375, igm_model='trotter2011'
            )


class TrotterHostHITests(unittest.TestCase):
    def test_dla_is_centered_at_redshifted_lyman_alpha(self):
        redshift = 3.375
        center = (
            2.99792458e18 / LYMAN_ALPHA_FREQUENCY_HZ * (1.0 + redshift)
        )
        wavelength = np.array([center - 500.0, center, center + 500.0])
        delta = trotter2011_host_dla_delta_log10_flux(
            wavelength, redshift, 1.0e21
        )
        self.assertLess(delta[1], delta[0])
        self.assertLess(delta[1], delta[2])
        self.assertLess(trotter2011_host_hi_transmission(
            center, redshift, 1.0e21
        ), 1.0e-12)

    def test_optical_depth_scales_linearly_with_column(self):
        wavelength = 6000.0
        low = trotter2011_host_dla_delta_log10_flux(
            wavelength, 3.375, 1.0e20
        )
        high = trotter2011_host_dla_delta_log10_flux(
            wavelength, 3.375, 1.0e21
        )
        self.assertAlmostEqual(high / low, 10.0, places=12)

    def test_host_lyman_limit_is_total_absorption(self):
        redshift = 2.0
        boundary = LYMAN_LIMIT_ANGSTROM * (1.0 + redshift)
        transmission = trotter2011_host_hi_transmission(
            np.array([boundary - 1.0, boundary + 1.0]),
            redshift,
            1.0e20,
        )
        self.assertEqual(transmission[0], 0.0)
        self.assertGreater(transmission[1], 0.0)

    def test_host_column_must_be_one_physical_scalar(self):
        with self.assertRaisesRegex(ValueError, "scalar"):
            trotter2011_host_hi_transmission(
                6000.0, 3.375, np.array([1.0e20, 1.0e21])
            )

    def test_combined_transmission_is_product_of_selected_components(self):
        wavelength = np.array([4500.0, 5000.0, 6000.0])
        redshift = 3.375
        combined = hydrogen_transmission(
            wavelength,
            redshift,
            igm_model='inoue2014',
            host_model='trotter2011',
            nhi_host_cm2=1.0e21,
        )
        expected = (
            inoue2014_igm_transmission(wavelength, redshift)
            * trotter2011_host_hi_transmission(
                wavelength, redshift, 1.0e21
            )
        )
        np.testing.assert_allclose(combined, expected, rtol=1.0e-14)


if __name__ == '__main__':
    unittest.main()
