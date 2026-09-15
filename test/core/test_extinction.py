import unittest

import numpy as np

from jetfit.core import extinction


class TrotterExtinctionTests(unittest.TestCase):
    PARAMS = {
        "Av": 0.8,
        "Rv": 3.2,
        "c1": -0.4,
        "c2": 0.9,
        "BH": 3.0,
        "c4": 0.5,
        "x0": 4.6,
        "gamma": 0.9,
    }

    def test_bump_height_and_c3_forms_are_equivalent(self):
        x = np.linspace(0.4, 10.0, 200)
        p = self.PARAMS
        with_bh = extinction.trotter_extinction_bh(x, **p)
        with_c3 = extinction.trotter_extinction(
            x,
            p["Av"],
            p["Rv"],
            p["c1"],
            p["c2"],
            p["BH"] * p["gamma"] ** 2,
            p["c4"],
            p["x0"],
            p["gamma"],
        )
        np.testing.assert_allclose(with_bh, with_c3, rtol=1.0e-13)

    def test_zero_av_has_unit_transmission(self):
        magnitudes = extinction.trotter_extinction_bh(
            np.array([0.5, 1.82, 3.3, 5.9, 8.0]),
            **{**self.PARAMS, "Av": 0.0},
        )
        np.testing.assert_array_equal(extinction.transmission(magnitudes), 1.0)

    def test_thesis_splice_is_continuous(self):
        for boundary in (extinction.X_LOW, extinction.X_HIGH):
            x = np.array([boundary - 1.0e-7, boundary, boundary + 1.0e-7])
            values = extinction.trotter_extinction_bh(x, **self.PARAMS)
            np.testing.assert_allclose(values, values[1], rtol=2.0e-6)

    def test_resolver_uses_requested_c4_key(self):
        params = {
            "av_source_frame": 0.8,
            "c2": 0.9,
            "c4": 1.5,
        }

        def physical(_c2, _params):
            return (-0.4, 3.2, 3.0, 4.6, 0.9)

        far_uv = np.array([8.0])
        with_c4 = extinction.resolve_source_frame_transmission(
            far_uv, params, physical, c4_key="c4"
        )
        without_c4 = extinction.resolve_source_frame_transmission(
            far_uv, params, physical
        )
        self.assertLess(with_c4[0], without_c4[0])

    def test_reference_curve_values(self):
        x = np.array([0.5, 1.82, 3.3, 5.9, 8.0])
        expected = np.array([
            0.107272080023,
            0.800000000000,
            1.500383061023,
            2.126079214110,
            2.883173335565,
        ])
        actual = extinction.trotter_extinction_bh(x, **self.PARAMS)
        np.testing.assert_allclose(actual, expected, rtol=1.0e-8)


if __name__ == "__main__":
    unittest.main()
