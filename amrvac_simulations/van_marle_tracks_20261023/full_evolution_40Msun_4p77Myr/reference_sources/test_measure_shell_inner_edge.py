#!/usr/bin/env python3
"""Focused tests for local inner-rise crossings."""

import unittest

import numpy as np

from measure_shell_inner_edge import case_age_myr
from plot_dense_gmc_scan import inner_rise


class InnerRiseTests(unittest.TestCase):
    def test_saved_age_matches_case_year_convention(self):
        self.assertAlmostEqual(case_age_myr(270000 * 365.0 / 365.25), 0.27)

    def test_ignores_later_broad_crest(self):
        radius = np.linspace(0.1, 3.0, 2901)
        density = np.ones_like(radius)
        density += 20.0 / (1.0 + np.exp(-(radius - 1.2) / 0.15))
        density += 99.0 / (1.0 + np.exp(-(radius - 1.5) / 0.005))
        density += 20.0 * np.exp(-((radius - 1.9) / 0.08) ** 2)
        result = inner_rise(radius, density, 1.9)
        self.assertAlmostEqual(result["inner_radius_pc"], 1.489, delta=0.005)
        self.assertAlmostEqual(result["inner_midrise_pc"], 1.5, delta=0.005)
        self.assertLess(result["inner_rise_90_pc"], 1.52)
        self.assertGreater(result["prejump_nh_cm3"], 10.0)
        self.assertGreater(result["shell_peak_nh_cm3"], result["shell_inner_nh_cm3"])

    def test_rejects_no_jump(self):
        radius = np.linspace(0.1, 3.0, 100)
        with self.assertRaises(ValueError):
            inner_rise(radius, np.ones_like(radius), 2.0)

    def test_measures_jump_below_old_search_floor(self):
        radius = np.linspace(0.0004, 0.01, 9601)
        density = 1.0 + 100.0 / (1.0 + np.exp(-(radius - 0.003) / 0.00003))
        density += 8.0 * np.exp(-((radius - 0.0035) / 0.0002) ** 2)
        result = inner_rise(radius, density, 0.0035, 0.0004)
        self.assertAlmostEqual(result["inner_midrise_pc"], 0.003, delta=0.00003)
        self.assertGreater(result["inner_ramp_cells"], 100)

    def test_rejects_unsorted_radius(self):
        with self.assertRaises(ValueError):
            inner_rise(np.array([1.0, 0.5]), np.array([1.0, 10.0]), 1.0)


if __name__ == "__main__":
    unittest.main()
