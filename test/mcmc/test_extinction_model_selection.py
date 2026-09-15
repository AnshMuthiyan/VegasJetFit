import unittest
import warnings

import numpy as np
from dust_extinction.parameter_averages import CCM89

from jetfit.mcmc.mcmc import MCMCModels
from jetfit.mcmc.parameters import (
    Parameters,
    add_source_extinction_toml_comments,
    hydrogen_absorption_toml_lines,
    normalize_host_hi_absorption_model,
    normalize_igm_absorption_model,
    normalize_source_extinction_model,
)


def fixed_parameter(name, value):
    return {'name': name, 'scale': 'linear', 'value': value}


def fitting_parameter(name, lower, upper):
    return {
        'name': name,
        'scale': 'linear',
        'prior': {'type': 'uniform', 'lower': lower, 'upper': upper},
    }


def model_config(extinction, source_model=None):
    config = {
        'name': 'FireballModel',
        'extinction': [
            fixed_parameter(name, value) for name, value in extinction.items()
        ],
    }
    if source_model is not None:
        config['source_extinction_model'] = source_model
    return config


class SourceExtinctionConfigurationTests(unittest.TestCase):
    def test_trotter_is_the_default_for_new_configs(self):
        params = Parameters.from_toml(model_config({}))
        self.assertEqual(params.source_extinction_model, 'trotter2011')
        self.assertEqual(params.source_extinction_model_origin, 'default')

    def test_explicit_trotter_config_requires_complete_physical_coordinates(self):
        params = Parameters.from_toml(model_config(
            {'av_source_frame': 0.5, 'c2': 1.0, 'c4': 0.2},
            source_model='trotter2011',
        ))
        self.assertEqual(params.source_extinction_model, 'trotter2011')
        with self.assertRaisesRegex(ValueError, 'requires these parameters.*c4'):
            Parameters.from_toml(model_config(
                {'av_source_frame': 0.5, 'c2': 1.0},
                source_model='trotter2011',
            ))

    def test_explicit_ccm_config_and_short_alias(self):
        params = Parameters.from_toml(model_config(
            {'ebv_source_frame': 0.1}, source_model='ccm'
        ))
        self.assertEqual(params.source_extinction_model, 'ccm89')
        self.assertEqual(normalize_source_extinction_model('trotter'), 'trotter2011')

    def test_legacy_unmarked_ccm_is_inferred_with_a_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            params = Parameters.from_toml(model_config(
                {'ebv_source_frame': 0.1}
            ))
        self.assertEqual(params.source_extinction_model, 'ccm89')
        self.assertEqual(
            params.source_extinction_model_origin,
            'legacy_parameter_inference',
        )
        self.assertTrue(any('inferred' in str(item.message) for item in caught))

    def test_mixed_model_parameters_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'cannot be used with CCM parameters'):
            Parameters.from_toml(model_config(
                {
                    'av_source_frame': 0.5,
                    'c2': 1.0,
                    'c4': 0.2,
                    'ebv_source_frame': 0.1,
                },
                source_model='trotter2011',
            ))
        with self.assertRaisesRegex(ValueError, 'cannot be used with Trotter parameters'):
            Parameters.from_toml(model_config(
                {'av_source_frame': 0.5, 'c2': 1.0, 'c4': 0.2},
                source_model='ccm89',
            ))

    def test_generated_toml_switch_includes_both_references(self):
        rendered = add_source_extinction_toml_comments(
            'name = "FireballModel"\nsource_extinction_model = "trotter2011"\n'
        )
        self.assertIn('Trotter, A. S. 2011', rendered)
        self.assertIn('Cardelli, Clayton, and Mathis 1989', rendered)
        self.assertIn("source_extinction_model = 'trotter2011'", rendered)


class SourceExtinctionDispatchTests(unittest.TestCase):
    def test_ccm_selection_uses_ccm_even_though_trotter_is_default(self):
        arrays = type('Arrays', (), {'wave_numbers': np.array([1.0, 2.0, 3.0])})()
        observation = type(
            'Observation',
            (),
            {
                'extinguishable': np.array([True, True, True], dtype=bool),
                'as_arrays': arrays,
                'hosts': None,
            },
        )()
        wrapper = MCMCModels(
            observation,
            afg_model=None,
            ext_model=CCM89,
            source_extinction_model='ccm89',
        )
        params = {
            'model': {'z': 0.5},
            'extinction': {'ebv_source_frame': 0.1},
            'host': None,
        }
        actual = wrapper.model_extinction(np.ones(3), params)
        expected = CCM89(Rv=3.1).extinguish(1.5 * arrays.wave_numbers, Ebv=0.1)
        np.testing.assert_allclose(actual, expected)


class HydrogenAbsorptionConfigurationTests(unittest.TestCase):
    def test_unmarked_legacy_config_remains_gas_off(self):
        params = Parameters.from_toml(model_config({}))
        self.assertEqual(params.igm_absorption_model, 'none')
        self.assertEqual(params.host_hi_absorption_model, 'none')
        self.assertEqual(params.igm_absorption_model_origin, 'legacy_default_off')

    def test_inoue_requires_one_fixed_known_redshift(self):
        config = model_config({}) | {
            'igm_absorption_model': 'inoue14',
            'model': [fixed_parameter('z', 3.375)],
        }
        params = Parameters.from_toml(config)
        self.assertEqual(params.igm_absorption_model, 'inoue2014')

        without_z = model_config({}) | {'igm_absorption_model': 'inoue2014'}
        with self.assertRaisesRegex(ValueError, 'fixed, known model redshift'):
            Parameters.from_toml(without_z)

    def test_trotter_igm_is_an_explicit_user_facing_choice(self):
        config = model_config({}) | {
            'igm_absorption_model': 'trotter',
            'model': [fixed_parameter('z', 3.375)],
            'absorption': [
                fitting_parameter('delta_igm_generic_g', -3.0, 3.0),
                fixed_parameter('z_f_generic_g', 2.7),
                fixed_parameter('delta_z_f_generic_g', 0.4),
            ],
        }
        params = Parameters.from_toml(config)
        self.assertEqual(params.igm_absorption_model, 'trotter2011')
        self.assertEqual(normalize_igm_absorption_model('trotter11'), 'trotter2011')

    def test_trotter_igm_rejects_absorbers_behind_the_source(self):
        config = model_config({}) | {
            'igm_absorption_model': 'trotter2011',
            'model': [fixed_parameter('z', 0.544)],
            'absorption': [
                fitting_parameter('delta_igm_uvw1', -3.0, 3.0),
                fixed_parameter('z_f_uvw1', 2.3),
                fixed_parameter('delta_z_f_uvw1', 0.15),
            ],
        }
        with self.assertRaisesRegex(ValueError, 'between zero and source redshift'):
            Parameters.from_toml(config)

    def test_host_model_requires_nhi_host(self):
        config = model_config({}) | {
            'host_hi_absorption_model': 'trotter2011',
            'model': [fixed_parameter('z', 3.375)],
        }
        with self.assertRaisesRegex(ValueError, 'requires.*nhi_host'):
            Parameters.from_toml(config)

        config['absorption'] = [{
            'name': 'nhi_host',
            'scale': 'log',
            'prior': {'type': 'uniform', 'lower': 18.0, 'upper': 23.0},
        }]
        params = Parameters.from_toml(config)
        self.assertEqual(params.host_hi_absorption_model, 'trotter2011')
        sample = params.samples_to_dict(np.array([21.0]))
        self.assertAlmostEqual(sample['absorption']['nhi_host'], 1.0e21)

    def test_cli_overrides_are_atomic(self):
        params = Parameters.from_toml(model_config({}) | {
            'model': [fixed_parameter('z', 1.0)],
        })
        params.set_hydrogen_absorption_models(igm_model='inoue')
        self.assertEqual(params.igm_absorption_model, 'inoue2014')
        with self.assertRaisesRegex(ValueError, 'requires.*nhi_host'):
            params.set_hydrogen_absorption_models(host_model='trotter')
        self.assertEqual(params.host_hi_absorption_model, 'none')

    def test_toml_comments_distinguish_gas_from_dust(self):
        lines = hydrogen_absorption_toml_lines('trotter2011', 'none')
        text = '\n'.join(lines)
        self.assertIn('separate from dust extinction', text)
        self.assertIn('Inoue et al. 2014', text)
        self.assertIn('Trotter 2011', text)
        self.assertIn("igm_absorption_model = 'trotter2011'", text)
        self.assertEqual(normalize_host_hi_absorption_model('off'), 'none')
        self.assertEqual(normalize_igm_absorption_model('inoue14'), 'inoue2014')


if __name__ == '__main__':
    unittest.main()
