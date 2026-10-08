import numpy as np
import matplotlib.pyplot as plt

try:
    from jetfit.models.bubbleVegas import BubbleVegasModel
    from jetfit.models.spheroidShellVegas import SpheroidShellVegasModel
except ImportError as e:
    print(f"Error importing models: {e}")
    exit(1)

# Standard jet parameters
jet_kwargs = {
    'E52': 1.0, 'lf0': 300.0, 'theta_c': 0.1, 'theta_v': 0.0,
    'eps_e': 0.1, 'eps_b': 0.01, 'p': 2.2, 'z': 1.0, 'dL28': 1.0
}

# Values as they would be AFTER JetFit converts log10 -> linear
rt_linear = 10**17.5
nt_linear = 10**0.0
nism_linear = 10**0.0

# 1. Old BubbleVegasModel (rt, nt, nism)
bubble_model = BubbleVegasModel(
    **jet_kwargs,
    rt=rt_linear, nt=nt_linear, nism=nism_linear
)

# 2. New SpheroidShellVegasModel (R_pole, n_ism, eps, q)
spheroid_model = SpheroidShellVegasModel(
    **jet_kwargs,
    R_pole=rt_linear, n_ism=nism_linear, eps=0.1, q=10**0.5, n_cav=10**(-2.0)
)

r_arr = np.logspace(16, 18.5, 500)

def bubble_density(r):
    rt = bubble_model.rt
    r2 = bubble_model.r2
    n_t = bubble_model.nt
    n_ism = bubble_model.nism
    out = np.zeros_like(r)
    # Avoid div by zero or negative density due to float precision
    r2_safe = r2 if r2 > rt else r2 + 1.0
    
    out[r < rt] = n_t * (rt / r[r < rt])**2
    
    # Weaver approx:
    weaver_shelf = n_ism / (1.0 - (rt/r2_safe)**3)
    out[(r >= rt) & (r < r2)] = weaver_shelf
    out[r >= r2] = n_ism
    return out

plt.figure(figsize=(10, 6))

plt.plot(r_arr, bubble_density(r_arr), 
         label="Old Weaver Bubble (Termination Shock, rt=10^17.5)", color="blue", lw=2)

plt.plot(r_arr, spheroid_model.number_density_cm3(r_arr), 
         label="New Spheroid Shell (Polar axis, q=0.5, eps=0.1)", color="red", linestyle="--", lw=2)

plt.xscale('log')
plt.yscale('log')
plt.xlabel("Radius (cm)")
plt.ylabel("Density (cm^-3)")
plt.title("Density Profile Comparison: Weaver Bubble vs Asymmetric Spheroid")
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig("amrvac_simulations/analysis/model_comparison_density.png")
print("Saved amrvac_simulations/analysis/model_comparison_density.png")
