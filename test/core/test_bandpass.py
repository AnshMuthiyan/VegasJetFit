import os
import unittest
from unittest.mock import patch

import numpy as np
from dust_extinction.parameter_averages import CCM89

from jetfit.core.bandpass import (
    C_ANGSTROM_PER_SECOND,
    available_bandpasses,
    get_bandpass,
    requires_bandpass_integration,
)
from jetfit.core.hydrogen_absorption import (
    inoue2014_igm_transmission,
    trotter2011_igm_transmission,
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


def _dense_uvm2_average(fnu_times_attenuation, breakpoints, substeps=64):
    """Independent dense photon-weighted average over the raw UVM2 ARF.

    Reads WAVE_MIN/WAVE_MAX/SPECRESP directly (no jetfit quadrature), splits
    every 10 A bin into ``substeps`` pieces (and exactly at ``breakpoints``),
    and integrates F_nu * attenuation * A / lambda with the trapezoid rule.
    """
    from astropy.io import fits
    with fits.open(get_bandpass('uvm2').source_file) as hdus:
        data = hdus[1].data
        a = np.asarray(data['WAVE_MIN'], float)
        b = np.asarray(data['WAVE_MAX'], float)
        area = np.asarray(data['SPECRESP'], float)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    num = den = 0.0
    for l0, l1, value in zip(lo, hi, area):
        if value <= 0.0:
            continue
        cuts = np.unique([l0, l1] + [p for p in breakpoints if l0 < p < l1])
        for c0, c1 in zip(cuts[:-1], cuts[1:]):
            wl = np.linspace(c0, c1, substeps + 1)
            inner = wl.copy()
            inner[0] += 1e-9 * (c1 - c0)
            inner[-1] -= 1e-9 * (c1 - c0)
            w = value / wl
            num += np.trapezoid(fnu_times_attenuation(inner) * w, wl)
            den += np.trapezoid(w, wl)
    return num / den


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
            # Integrate-all switch: this test is about every verified
            # response being usable, not about the 3.3 um^-1 selection
            # (covered by the companion test below).
            bandpass_selective=False,
        )
        modeled = wrapper.model(params)
        expected = []
        for name in names:
            response = get_bandpass(name)
            wavelength, weight = response.quadrature(None)
            intrinsic = _PowerLawAfterglow(slope=-0.7).spectral_flux(
                np.ones(wavelength.size), C_ANGSTROM_PER_SECOND / wavelength
            )
            expected.append(np.sum(intrinsic * weight))
        np.testing.assert_allclose(modeled, expected, rtol=1e-12)

    def test_default_selective_mode_keeps_bands_below_boundary_monochromatic(self):
        # Team decision (2026-10): integrate where the response crosses
        # x = 3.3 um^-1; a band wholly below it stays on the monochromatic
        # path, and a crossing band is integrated.
        names = list(available_bandpasses())
        frequencies = [
            C_ANGSTROM_PER_SECOND / get_bandpass(name).pivot_wavelength_angstrom
            for name in names
        ]
        obs = _Observation(np.ones(len(names)), frequencies, names)
        z = 0.544
        params = {'model': {'slope': -0.7, 'z': z}, 'extinction': _zero_dust()}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('JETFIT_BANDPASS_SELECTIVE', None)
            wrapper = MCMCModels(
                obs, _PowerLawAfterglow, ext_model=None,
                bandpass_integration='verified', bandpass_nodes=16,
            )
        self.assertTrue(wrapper.bandpass_selective)
        modeled = wrapper.model(params)
        crossing = [
            requires_bandpass_integration(get_bandpass(n), z) for n in names
        ]
        self.assertTrue(any(crossing))
        self.assertFalse(all(crossing))
        for i, name in enumerate(names):
            response = get_bandpass(name)
            if crossing[i]:
                wavelength, weight = response.quadrature(None)
                intrinsic = _PowerLawAfterglow(slope=-0.7).spectral_flux(
                    np.ones(wavelength.size), C_ANGSTROM_PER_SECOND / wavelength
                )
                expected = np.sum(intrinsic * weight)
            else:
                expected = _PowerLawAfterglow(slope=-0.7).spectral_flux(
                    np.ones(1), np.array([frequencies[i]])
                )[0]
            np.testing.assert_allclose(modeled[i], expected, rtol=1e-12,
                                       err_msg=name)

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

    def test_ccm_source_dust_does_not_extrapolate_past_its_uv_limit(self):
        uvm2 = get_bandpass('uvm2')
        pivot_nu = C_ANGSTROM_PER_SECOND / uvm2.pivot_wavelength_angstrom
        obs = _Observation([1.0], [pivot_nu], ['uvm2'])
        redshift = 0.97
        ebv = 0.1
        params = {
            'model': {'slope': -0.7, 'z': redshift},
            'extinction': {'ebv_source_frame': ebv},
        }
        wrapper = MCMCModels(
            obs,
            _PowerLawAfterglow,
            ext_model=CCM89,
            source_extinction_model='ccm89',
            bandpass_integration='verified',
            bandpass_nodes=16,
        )
        modeled = wrapper.model(params)[0]

        wavelength, weight = uvm2.photon_quadrature(None)
        intrinsic = _PowerLawAfterglow(slope=-0.7).spectral_flux(
            np.ones(wavelength.size), C_ANGSTROM_PER_SECOND / wavelength
        )
        source_wave_number = (1.0 + redshift) * 1.0e4 / wavelength
        valid = (
            (source_wave_number >= CCM89.x_range[0])
            & (source_wave_number <= CCM89.x_range[1])
        )
        self.assertTrue(np.any(~valid))
        attenuation = np.ones_like(source_wave_number)
        attenuation[valid] = CCM89(Rv=3.1).extinguish(
            source_wave_number[valid], Ebv=ebv
        )
        expected = np.sum(intrinsic * attenuation * weight)
        self.assertTrue(np.isfinite(modeled))
        # 2026-10: the CCM x = 10 um^-1 edge (observed 1970 A at z = 0.97) is
        # a step inside a UVM2 bin. The plain midpoint sum above (the earlier
        # algorithm) treats the step as if it fell on a bin boundary and is
        # off by 0.8%; the default refines that cell. Check the default
        # against an independent dense integration of the same physics
        # (a STRONGER check than equality with the earlier algorithm), and
        # keep the earlier algorithm exact under the legacy settings.
        model = CCM89(Rv=3.1)

        def attenuated(wl):
            x = (1.0 + redshift) * 1.0e4 / wl
            t = np.ones_like(wl)
            inside = (x >= CCM89.x_range[0]) & (x <= CCM89.x_range[1])
            t[inside] = model.extinguish(x[inside], Ebv=ebv)
            return _PowerLawAfterglow(slope=-0.7).spectral_flux(
                np.ones(wl.size), C_ANGSTROM_PER_SECOND / wl) * t

        steps = [(1.0 + redshift) * 1.0e4 / x for x in CCM89.x_range]
        dense = _dense_uvm2_average(attenuated, steps)
        self.assertLess(abs(float(modeled) / dense - 1.0), 5.0e-5)
        self.assertGreater(abs(float(expected) / dense - 1.0), 5.0e-3)
        wrapper.bandpass_refine = False
        wrapper.bandpass_interpolation = 'linear'
        wrapper.bandpass_node_placement = 'response'
        self.assertAlmostEqual(float(wrapper.model(params)[0]), float(expected), places=12)

    def test_all_verified_filters_remain_finite_with_ccm_and_igm(self):
        names = list(available_bandpasses())
        frequencies = [
            C_ANGSTROM_PER_SECOND / get_bandpass(name).pivot_wavelength_angstrom
            for name in names
        ]
        for redshift in (0.544, 0.97, 4.61, 6.318):
            obs = _Observation(
                np.ones(len(names)), frequencies, names
            )
            params = {
                'model': {'slope': -0.7, 'z': redshift},
                'extinction': {'ebv_source_frame': 0.1},
                'absorption': {},
            }
            wrapper = MCMCModels(
                obs,
                _PowerLawAfterglow,
                ext_model=CCM89,
                source_extinction_model='ccm89',
                bandpass_integration='verified',
                bandpass_nodes=16,
                igm_absorption_model='inoue2014',
            )
            modeled = wrapper.model(params)
            self.assertEqual(modeled.shape, (len(names),))
            self.assertTrue(np.all(np.isfinite(modeled)))
            self.assertTrue(np.all(modeled >= 0.0))

    def test_igm_absorption_is_integrated_inside_uvot_bandpass(self):
        uvm2 = get_bandpass('uvm2')
        pivot_nu = C_ANGSTROM_PER_SECOND / uvm2.pivot_wavelength_angstrom
        obs = _Observation([1.0], [pivot_nu], ['uvm2'])
        redshift = 0.97
        params = {
            'model': {'slope': -0.7, 'z': redshift},
            'extinction': _zero_dust(),
            'absorption': {},
        }
        wrapper = MCMCModels(
            obs,
            _PowerLawAfterglow,
            ext_model=None,
            bandpass_integration='verified',
            bandpass_nodes=16,
            igm_absorption_model='inoue2014',
        )
        modeled = wrapper.model(params)[0]

        wavelength, weight = uvm2.photon_quadrature(None)
        intrinsic = _PowerLawAfterglow(slope=-0.7).spectral_flux(
            np.ones(wavelength.size), C_ANGSTROM_PER_SECOND / wavelength
        )
        expected = np.sum(
            intrinsic
            * inoue2014_igm_transmission(wavelength, redshift)
            * weight
        )
        central = (
            _PowerLawAfterglow(slope=-0.7).spectral_flux(1.0, pivot_nu)
            * inoue2014_igm_transmission(
                uvm2.pivot_wavelength_angstrom, redshift
            )
        )
        # 2026-09-25: the default now refines quadrature cells that contain an
        # H I step (see MCMCModels.__init__). The plain midpoint sum below is
        # the earlier algorithm; against a dense independent reference it is
        # off by ~1e-4 here while the refined default is off by ~1e-6
        # (reports/2026_09_25_filter_integration_verification). So: exact
        # equality under the legacy settings, 5e-4 agreement by default.
        self.assertLess(abs(float(modeled) / float(expected) - 1.0), 5.0e-4)
        wrapper.bandpass_refine = False
        wrapper.bandpass_interpolation = 'linear'
        wrapper.bandpass_node_placement = 'response'
        self.assertAlmostEqual(float(wrapper.model(params)[0]), float(expected), places=12)
        self.assertGreater(abs(modeled / central - 1.0), 1.0e-3)

    def test_trotter_igm_is_applied_per_wavelength_before_integration(self):
        # 2026-10 team decision: the Trotter IGM multiplies the spectrum at
        # every response wavelength (each at its own absorber redshift) and
        # the attenuated spectrum is then integrated -- no per-filter scalar.
        uvm2 = get_bandpass('uvm2')
        pivot_nu = C_ANGSTROM_PER_SECOND / uvm2.pivot_wavelength_angstrom
        obs = _Observation([1.0], [pivot_nu], ['uvm2'])
        redshift = 0.97
        params = {
            'model': {'slope': -0.7, 'z': redshift},
            'extinction': _zero_dust(),
            'absorption': {},
        }
        wrapper = MCMCModels(
            obs,
            _PowerLawAfterglow,
            ext_model=None,
            bandpass_integration='verified',
            bandpass_nodes=16,
            igm_absorption_model='trotter2011',
        )
        modeled = wrapper.model(params)[0]

        def attenuated(wl):
            return _PowerLawAfterglow(slope=-0.7).spectral_flux(
                np.ones(wl.size), C_ANGSTROM_PER_SECOND / wl
            ) * trotter2011_igm_transmission(wl, redshift)

        steps = [911.8 * (1.0 + redshift), 1215.67 * (1.0 + redshift)]
        dense = _dense_uvm2_average(attenuated, steps)
        self.assertLess(abs(float(modeled) / dense - 1.0), 1.0e-4)

        wavelength, weight = uvm2.photon_quadrature(None)
        expected = np.sum(attenuated(wavelength) * weight)
        wrapper.bandpass_refine = False
        wrapper.bandpass_interpolation = 'linear'
        wrapper.bandpass_node_placement = 'response'
        self.assertAlmostEqual(float(wrapper.model(params)[0]), float(expected), places=12)

    def test_unmapped_filter_uses_central_wavelength_gas_attenuation(self):
        frequency = C_ANGSTROM_PER_SECOND / 4500.0
        obs = _Observation([1.0], [frequency], ['generic-g'])
        params = {
            'model': {'slope': -0.7, 'z': 3.375},
            'extinction': _zero_dust(),
            'absorption': {},
        }
        wrapper = MCMCModels(
            obs,
            _PowerLawAfterglow,
            ext_model=None,
            bandpass_integration='verified',
            igm_absorption_model='inoue2014',
        )
        modeled = wrapper.model(params)[0]
        expected = (
            _PowerLawAfterglow(slope=-0.7).spectral_flux(1.0, frequency)
            * inoue2014_igm_transmission(4500.0, 3.375)
        )
        self.assertAlmostEqual(float(modeled), float(expected), places=12)


if __name__ == '__main__':
    unittest.main()
