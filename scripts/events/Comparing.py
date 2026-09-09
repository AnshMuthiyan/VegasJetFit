import numpy as np
from jetfit.models.fireball import FireballModel
from jetfit.models.powerlawVegas import powerlawVegasModel
import matplotlib.pyplot as plt

# Parameters from best_fitFire.json
E52 = 136.25
lf0 = 670.6
n017 = .26
k = 2.3
z = 0.151
dL28 = 0.229
p = 2.2
eps_e = 0.548
eps_b = 0.000227
hmf = 0.7
theta_c = 0.1  # ~6 degrees for tophat

# Time range around 1600s
t_obs_d = np.array([1600/86400])

print('='*60)
print('FIREBALL MODEL')
print('='*60)
fb = FireballModel(E52=E52, p=p, eps_b=eps_b, eps_e=eps_e, z=z, dL28=dL28, n017=n017, k=k, hmf=hmf, lf0=lf0)
nu_fb = fb.nu_m(t_obs_d)

print()
print('='*60)
print('VEGAS AFTERGLOW MODEL')
print('='*60)
vegas = powerlawVegasModel(E52=E52, lf0=lf0, theta_c=theta_c, theta_v=0.0, eps_e=eps_e, eps_b=eps_b, p=p, z=z, dl28=dL28, n017=n017, k=k, hmf=hmf)
nu_vegas = vegas.nu_m(t_obs_d)

print()
print('='*60)
print('DENSITY PROFILE FROM VEGAS OBJECT')
print('='*60)

# Create radius array from 10^15 to 10^19 cm
r = np.logspace(15, 19, 500)  # cm

# Query the actual density from the VegasAfterglow model
# vegas_model.medium(phi, theta, r) returns mass density [g/cm³]
rho_vegas = vegas.vegas_model.medium(0, 0, r)

# Convert mass density to number density for comparison
m_p = 1.67262192e-24  # proton mass [g]
X = 0.7  # Hydrogen mass fraction (same as used in powerlawVegas)
n_vegas = rho_vegas / (m_p * X)  # number density [cm⁻³]

# Reference values
r0 = 1e17  # Reference radius [cm]
rho_at_r0 = vegas.vegas_model.medium(0, 0, np.array([r0]))[0]
n_at_r0 = rho_at_r0 / (m_p * X)

print(f'Queried density from vegas.vegas_model.medium():')
print(f'  At r = 10^15 cm: rho = {vegas.vegas_model.medium(0, 0, np.array([1e15]))[0]:.3e} g/cm³')
print(f'  At r = 10^17 cm: rho = {rho_at_r0:.3e} g/cm³, n = {n_at_r0:.3e} cm⁻³')
print(f'  At r = 10^18 cm: rho = {vegas.vegas_model.medium(0, 0, np.array([1e18]))[0]:.3e} g/cm³')
print(f'  At r = 10^19 cm: rho = {vegas.vegas_model.medium(0, 0, np.array([1e19]))[0]:.3e} g/cm³')

# Create the plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Number density vs radius (from Vegas object)
ax1.loglog(r, n_vegas, 'b-', linewidth=2, label='n(r) from vegas.medium()')
ax1.axvline(r0, color='r', linestyle='--', alpha=0.7, label=f'r₀ = 10¹⁷ cm')
ax1.axhline(n_at_r0, color='g', linestyle=':', alpha=0.7, label=f'n(r₀) = {n_at_r0:.2f} cm⁻³')
ax1.set_xlabel('Radius [cm]', fontsize=12)
ax1.set_ylabel('Number Density [cm⁻³]', fontsize=12)
ax1.set_title(f'VegasAfterglow Density Profile (from object)\nn(r₀) = {n_at_r0:.2f} cm⁻³', fontsize=14)
ax1.legend(loc='upper right')
ax1.grid(True, alpha=0.3, which='both')
ax1.set_xlim(1e15, 1e19)

# Plot 2: Mass density vs radius (from Vegas object)
ax2.loglog(r, rho_vegas, 'b-', linewidth=2, label='ρ(r) from vegas.medium()')
ax2.axvline(r0, color='r', linestyle='--', alpha=0.7, label=f'r₀ = 10¹⁷ cm')
ax2.axhline(rho_at_r0, color='g', linestyle=':', alpha=0.7, label=f'ρ(r₀) = {rho_at_r0:.2e} g/cm³')
ax2.set_xlabel('Radius [cm]', fontsize=12)
ax2.set_ylabel('Mass Density [g/cm³]', fontsize=12)
ax2.set_title(f'Mass Density Profile (from Vegas object)', fontsize=14)
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3, which='both')
ax2.set_xlim(1e15, 1e19)

plt.tight_layout()
plt.savefig('vegas_density_profile.png', dpi=150, bbox_inches='tight')
plt.show()

print(f'\nDensity profile saved to vegas_density_profile.png')
print(f'  Input n017 = {n017:.3f} cm⁻³')
print(f'  Actual n(r₀) from Vegas = {n_at_r0:.3f} cm⁻³')
print(f'  Input k = {k:.3f}')

print()
print('='*60)
print('SUMMARY')
print('='*60)
print(f'FireballModel nu_m = {nu_fb[0]:.3e} Hz')
print(f'VegasAfterglow nu_m = {nu_vegas[0]:.3e} Hz')
print(f'Difference in nu_m = {abs(nu_fb[0] - nu_vegas[0]):.3e} Hz')
print(f'Ratio nu_m (Fireball / Vegas) = {nu_fb[0] / nu_vegas[0]:.3f}')

print()
print('='*60)
print('SENSITIVITY ANALYSIS: S_i ≈ [D(θ×f) - D(θ/f)] / (2 ln f)')
print('='*60)
print('Finding which parameter causes the discrepancy...')
print()

# Base parameters
base_params = {
    'E52': E52,
    'lf0': lf0,
    'n017': n017,
    'k': k,
    'p': p,
    'eps_e': eps_e,
    'eps_b': eps_b,
    'hmf': hmf,
}

# Perturbation factor
f = 2  # 10% perturbation

def compute_fireball_nu_m(params):
    """Compute nu_m from FireballModel with given parameters."""
    try:
        model = FireballModel(
            E52=params['E52'], p=params['p'], eps_b=params['eps_b'],
            eps_e=params['eps_e'], z=z, dL28=dL28, n017=params['n017'],
            k=params['k'], hmf=params['hmf'], lf0=params['lf0']
        )
        return model.nu_m(t_obs_d)[0]
    except:
        return np.nan

def compute_vegas_nu_m(params):
    """Compute nu_m from VegasAfterglow with given parameters."""
    try:
        model = powerlawVegasModel(
            E52=params['E52'], lf0=params['lf0'], theta_c=theta_c, theta_v=0.0,
            eps_e=params['eps_e'], eps_b=params['eps_b'], p=params['p'],
            z=z, dl28=dL28, n017=params['n017'], k=params['k'], hmf=params['hmf']
        )
        return model.nu_m(t_obs_d)[0]
    except:
        return np.nan

def compute_discrepancy(params):
    """Compute D = log10(nu_m_fireball / nu_m_vegas)."""
    nu_fb = compute_fireball_nu_m(params)
    nu_vg = compute_vegas_nu_m(params)
    if nu_fb > 0 and nu_vg > 0:
        return np.log10(nu_fb / nu_vg)
    return np.nan

# Compute base discrepancy
D_base = compute_discrepancy(base_params)
print(f'Base discrepancy D = log10(nu_fb/nu_vegas) = {D_base:.4f}')
print(f'  (D > 0 means Fireball gives higher nu_m)')
print()

# Sensitivity analysis for each parameter
print(f'Perturbation factor f = {f} ({(f-1)*100:.0f}%)')
print()
print(f'{"Parameter":<10} {"θ_base":<12} {"D(θ×f)":<12} {"D(θ/f)":<12} {"S_i":<12} {"Contribution":<12}')
print('-' * 70)

sensitivities = {}
for param_name, param_value in base_params.items():
    # Create perturbed parameter sets
    params_up = base_params.copy()
    params_down = base_params.copy()
    
    params_up[param_name] = param_value * f
    params_down[param_name] = param_value / f
    
    # Compute discrepancy at perturbed values
    # D_up = compute_discrepancy(params_up)
    # D_down = compute_discrepancy(params_down)
    D_up = compute_fireball_nu_m(params_up)
    D_down = compute_fireball_nu_m(params_down)
    
    # Sensitivity: S_i = [D(θ×f) - D(θ/f)] / (2 ln f)
    if not np.isnan(D_up) and not np.isnan(D_down):
        S_i = (D_up - D_down) / (2 * np.log(f))
        sensitivities[param_name] = S_i
        
        # Contribution to discrepancy (larger |S_i| = more sensitive)
        contrib = abs(S_i)
        print(f'{param_name:<10} {param_value:<12.4g} {D_up:<12.4f} {D_down:<12.4f} {S_i:<12.4f} {contrib:<12.4f}')
    else:
        print(f'{param_name:<10} {param_value:<12.4g} {"NaN":<12} {"NaN":<12} {"NaN":<12} {"NaN":<12}')

print()
print('='*60)
print('INTERPRETATION')
print('='*60)
print('S_i > 0: Increasing θ_i increases discrepancy (Fireball/Vegas ratio)')
print('S_i < 0: Increasing θ_i decreases discrepancy')
print('|S_i| large: Parameter strongly affects discrepancy')
print()

# Sort by absolute sensitivity
if sensitivities:
    sorted_sens = sorted(sensitivities.items(), key=lambda x: abs(x[1]), reverse=True)
    print('Parameters ranked by sensitivity to discrepancy:')
    for i, (name, sens) in enumerate(sorted_sens, 1):
        direction = '↑' if sens > 0 else '↓'
        print(f'  {i}. {name}: S = {sens:+.4f} {direction}')


