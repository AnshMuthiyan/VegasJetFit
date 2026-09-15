import numpy as np
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from jetfit.models.trotter_lyman_alpha import apply_lyman_limit, calculate_igm_transmission

class TestTrotterLymanAlpha(unittest.TestCase):
    def test_apply_lyman_limit(self):
        # We want rest_wav = 900.0. Since rest_wav = obs / (1+z),
        # if z=0, obs=900.0 gives rest_wav=900.0.
        z_grb = 0.0
        obs_wav = np.array([900.0, 915.0])
        flux = np.array([1.0, 1.0])
        
        flux_out = apply_lyman_limit(obs_wav, z_grb, flux)
        
        self.assertEqual(flux_out[0], 0.0, "Flux below Lyman limit should be 0.0")
        self.assertEqual(flux_out[1], 1.0, "Flux above Lyman limit should remain unchanged")

    def test_calculate_igm_transmission(self):
        # Test calculate_igm_transmission at z_f = 4.10 and delta_igm = 0
        z_f = 4.10
        delta_z_f = 0.15 # any arbitrary value since it is unused without the prior
        delta_igm = 0.0
        
        # We just want to ensure it calculates without throwing a math error and returns a valid float bounded [0,1]
        T_adj = calculate_igm_transmission(z_f, delta_z_f, delta_igm)
        
        self.assertIsInstance(T_adj, float, "Output must be a float")
        self.assertTrue(0.0 <= T_adj <= 1.0, "Transmission must be bounded between 0 and 1")
        print(f"\n[Validation] calculate_igm_transmission(z_f=4.10, delta_igm=0.0) -> T = {T_adj:.6f}")

if __name__ == "__main__":
    unittest.main()

