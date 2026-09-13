import os
import unittest
from unittest.mock import patch

import numpy as np
from dust_extinction.parameter_averages import CCM89

from jetfit.core.bandpass import (
    C_ANGSTROM_PER_SECOND,
    available_bandpasses,
    get_bandpass,
)
from jetfit.mcmc.mcmc import MCMCModels


class _Arrays:
    def __init__(self, times, frequencies, bands):
        self.times = np.asarray(times, dtype=float)
        self.frequencies = np.asarray(frequencies, dtype=float)
        self.wave_numbers = self.frequencies / (C_ANGSTROM_PER_SECOND / 1.0e4)
        self.bands = np.asarray(bands, dtype='U10')
        self.sflux_loc = np.ones(self.times.size, dtype=bool)


class _Observation:
    def __init__(self, times, frequencies, bands):
        self.as_arrays = _Arrays(times, frequencies, bands)
        self.length = len(times)
        self.extinguishable = np.ones(self.length, dtype=bool)
        self.hosts = None


class _PowerLawAfterglow:
    def __init__(self, slope=-0.7, z=0.0, **kwargs):
        self.slope = float(slope)

    def spectral_flux(self, times, frequencies):
        times = np.asarray(times, dtype=float)
        frequencies = np.asarray(frequencies, dtype=float)
        return (1.0 + times) * (frequencies / 1.0e15) ** self.slope

    def model(self, observation):
        arrays = observation.as_arrays
        return self.spectral_flux(arrays.times, arrays.frequencies)


def _zero_dust():
    return {
        'av_source_frame': 0.0,
        'c2': 1.0,
        'c4': 0.5,
        'delta_c2_c1': 0.0,
        'delta_c1': 0.0,
        'delta_c2_rv': 0.0,
        'delta_rv': 0.0,
        'delta_c2_bh': 0.0,
        'delta_bh': 0.0,
        'delta_x0': 0.0,
        'delta_gamma': 0.0,
    }


class BandpassResourceTests(unittest.TestCase):
    def test_all_six_uvot_curves_load_and_generic_labels_do_not_alias(self):
        self.assertEqual(
            available_bandpasses(),
            (
                'F125W', 'F775W',
                'uvm2', 'uvot-b', 'uvot-u', 'uvot-v', 'uvw1', 'uvw2',
            ),
        )
        for name in available_bandpasses():
            response = get_bandpass(name)
            self.assertIsNotNone(response)
            self.assertGreater(response.effective_area_cm2.max(), 0.0)
        for ambiguous in ('U', 'B', 'V', 'R', 'r', 'i'):
            self.assertIsNone(get_bandpass(ambiguous))

    def test_caldb_pivot_wavelengths_are_stable(self):
        expected = {
            'uvot-v': 5424.6578,
            'uvot-b': 4349.5261,
            'uvot-u': 3467.0363,
            'uvw1': 2582.5294,
            'uvm2': 2246.9531,
            'uvw2': 2057.9601,
            'F775W': 7648.3071,
            'F125W': 12486.0694,
        }
        for name, pivot in expected.items():
            self.assertAlmostEqual(
                get_bandpass(name).pivot_wavelength_angstrom, pivot, places=3
            )

    def test_constant_fnu_is_preserved_exactly(self):
        for name in available_bandpasses():
            response = get_bandpass(name)
            for nodes in (16, 32, 64, None):
                _, weight = response.photon_quadrature(nodes)
                value = response.integrate_fnu(np.full(weight.size, 7.25), nodes)
                self.assertAlmostEqual(float(value), 7.25, places=13)

    def test_128_node_power_law_agrees_with_full_caldb_grid(self):
        for name in available_bandpasses():
            response = get_bandpass(name)
            for slope in (-2.0, -1.0, 0.0, 1.0, 2.0):
                wavelength, _ = response.photon_quadrature(None)
                full = response.integrate_fnu(
                    (C_ANGSTROM_PER_SECOND / wavelength / 1.0e15) ** slope
                )
                wavelength64, _ = response.photon_quadrature(128)
                compressed = response.integrate_fnu(
                    (C_ANGSTROM_PER_SECOND / wavelength64 / 1.0e15) ** slope,
                    128,
                )
                self.assertLess(abs(compressed / full - 1.0), 1.0e-3)


class BandpassLikelihoodTests(unittest.TestCase):
    def test_every_verified_filter_is_integrated_in_one_mixed_observation(self):
        names = list(available_bandpasses())
        frequencies = [
            C_ANGSTROM_PER_SECOND / get_bandpass(name).pivot_wavelength_angstrom
            for name in names
        ]
        obs = _Observation(np.ones(len(names)), frequencies, names)
        params = {'model': {'slope': -0.7, 'z': 0.544}, 'extinction': _zero_dust()}
        wrapper = MCMCModels(
            obs,
            _PowerLawAfterglow,
            ext_model=None,
            bandpass_integration='verified',
            bandpass_nodes=16,
        )
        modeled = wrapper.model(params)
        expected = []
        for name in names:
            response = get_bandpass(name)
            wavelength, weight = response.photon_quadrature(None)
            intrinsic = _PowerLawAfterglow(slope=-0.7).spectral_flux(
                np.ones(wavelength.size), C_ANGSTROM_PER_SECOND / wavelength
            )
            expected.append(np.sum(intrinsic * weight))
        np.testing.assert_allclose(modeled, expected, rtol=1e-12)

    def test_supported_filter_is_integrated_and_generic_filter_is_unchanged(self):
        uvw2 = get_bandpass('uvw2')
        pivot_nu = C_ANGSTROM_PER_SECOND / uvw2.pivot_wavelength_angstrom
        obs = _Observation([1.0, 1.0], [pivot_nu, 4.81e14], ['uvw2', 'r'])
        params = {'model': {'slope': -0.7, 'z': 0.544}, 'extinction': _zero_dust()}
        with patch.dict(os.environ, {'JETFIT_BANDPASS_INTEGRATION': '1'}):
            wrapper = MCMCModels(obs, _PowerLawAfterglow, ext_model=None)
        modeled = wrapper.model(params)

        wavelength, weight = uvw2.photon_quadrature(None)
        frequencies = C_ANGSTROM_PER_SECOND / wavelength
        expected_uvw2 = np.sum(
            _PowerLawAfterglow(slope=-0.7).spectral_flux(
                np.ones(wavelength.size), frequencies
            ) * weight
        )
        expected_r = _PowerLawAfterglow(slope=-0.7).spectral_flux(1.0, 4.81e14)
        np.testing.assert_allclose(modeled, [expected_uvw2, expected_r], rtol=1e-12)

    def test_source_dust_is_integrated_inside_the_bandpass(self):
        uvw2 = get_bandpass('uvw2')
        pivot_nu = C_ANGSTROM_PER_SECOND / uvw2.pivot_wavelength_angstrom
        obs = _Observation([1.0], [pivot_nu], ['uvw2'])
        extinction = _zero_dust()
        extinction['av_source_frame'] = 1.2
        params = {'model': {'slope': -0.7, 'z': 0.544}, 'extinction': extinction}
        with patch.dict(os.environ, {'JETFIT_BANDPASS_INTEGRATION': '1'}):
            wrapper = MCMCModels(obs, _PowerLawAfterglow, ext_model=None)
        modeled = wrapper.model(params)[0]

        wavelength, weight = uvw2.photon_quadrature(None)
        frequencies = C_ANGSTROM_PER_SECOND / wavelength
        intrinsic = _PowerLawAfterglow(slope=-0.7).spectral_flux(
            np.ones(wavelength.size), frequencies
        )
        attenuation = wrapper._node_extinction(1.0e4 / wavelength, params)
        expected = np.sum(intrinsic * attenuation * weight)
        self.assertAlmostEqual(float(modeled), float(expected), places=12)

    def test_full_response_extinction_preserves_uvot_red_leak(self):
        uvw2 = get_bandpass('uvw2')
        pivot_nu = C_ANGSTROM_PER_SECOND / uvw2.pivot_wavelength_angstrom
        obs = _Observation([1.0], [pivot_nu], ['uvw2'])
        extinction = _zero_dust()
        extinction['av_source_frame'] = 10.0
        params = {'model': {'slope': -0.7, 'z': 0.544}, 'extinction': extinction}
        wrapper = MCMCModels(
            obs,
            _PowerLawAfterglow,
            ext_model=None,
            bandpass_integration='verified',
            bandpass_nodes=16,
        )
        modeled = wrapper.model(params)[0]
        wavelength, weight = uvw2.photon_quadrature(None)
        intrinsic = _PowerLawAfterglow(slope=-0.7).spectral_flux(
            np.ones(wavelength.size), C_ANGSTROM_PER_SECOND / wavelength
        )
        expected = np.sum(
            intrinsic * wrapper._node_extinction(1.0e4 / wavelength, params) * weight
        )
        self.assertAlmostEqual(float(modeled), float(expected), places=12)

    def test_precomputed_mw_extinction_is_subset_for_unintegrated_rows(self):
        uvw2 = get_bandpass('uvw2')
        pivot_nu = C_ANGSTROM_PER_SECOND / uvw2.pivot_wavelength_angstrom
        obs = _Observation([1.0, 1.0], [pivot_nu, 4.81e14], ['uvw2', 'r'])
        ebv = 0.12
        central = CCM89(Rv=3.1).extinguish(obs.as_arrays.wave_numbers, Ebv=ebv)
        params = {
            'model': {'slope': -0.7, 'z': 0.544},
            'extinction': _zero_dust() | {'ebv_milky_way': ebv},
        }
        wrapper = MCMCModels(
            obs,
            _PowerLawAfterglow,
            ext_model=CCM89,
            ext_mw_pc=central,
            bandpass_integration='verified',
            bandpass_nodes=16,
        )
        modeled = wrapper.model(params)
        expected_r = (
            _PowerLawAfterglow(slope=-0.7).spectral_flux(1.0, 4.81e14)
            * central[1]
        )
        self.assertAlmostEqual(float(modeled[1]), float(expected_r), places=12)
        self.assertTrue(np.isfinite(modeled[0]))


if __name__ == '__main__':
    unittest.main()
