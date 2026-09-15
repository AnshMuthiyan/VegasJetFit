import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from jetfit.models.trotter_lyman_alpha import TrotterIGMPrior, calculate_igm_transmission

print("=== Testing Trotter IGM Model ===")

# Test Transmission
z_f = 4.2
delta_z_f = 0.15
delta_igm = 0.05
T_adj = calculate_igm_transmission(z_f, delta_z_f, delta_igm)
print(f"Adjusted Transmission: {T_adj:.5f}")

# Test Prior
igm_dict = {
    "delta_igm_uvw1": 0.05,
    "z_f_uvw1": 4.2,
    "delta_z_f_uvw1": 0.15,
    "delta_igm_uvw2": -0.1,
    "z_f_uvw2": 4.5,
    "delta_z_f_uvw2": 0.2,
}
prior = TrotterIGMPrior()
lp = prior.log_prior(igm_dict)
print(f"Log Prior (Scalar dict): {lp:.5f}")

# Test Vectorization robustness
prior = TrotterIGMPrior()  # fresh instance to test setup_cache
igm_dict_vec = {
    "delta_igm_uvw1": np.array([0.05, 0.0, -0.05]),
    "z_f_uvw1": 4.2,
    "delta_z_f_uvw1": 0.15,
    "delta_igm_uvw2": np.array([-0.1, 0.0, 0.1]),
    "z_f_uvw2": 4.5,
    "delta_z_f_uvw2": 0.2,
}
lp_vec = prior.log_prior(igm_dict_vec)
print(f"Log Prior (Vectorized arrays): {lp_vec}")

print("=== Tests Passed Successfully ===")
