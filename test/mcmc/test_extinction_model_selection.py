import unittest
import warnings

import numpy as np
from dust_extinction.parameter_averages import CCM89

from jetfit.mcmc.mcmc import MCMCModels
from jetfit.mcmc.parameters import (
    Parameters,
    add_source_extinction_toml_comments,
    normalize_source_extinction_model,
)


def fixed_parameter(name, value):
    return {'name': name, 'scale': 'linear', 'value': value}


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


if __name__ == '__main__':
    unittest.main()
