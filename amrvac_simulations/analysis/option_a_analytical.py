import numpy as np
import matplotlib.pyplot as plt

class AnalyticalBubbleOptionA:
    def __init__(self, mdot_msun_yr, vwind_km_s, 
                 r_ism_cm, rho_ism_g_cm3,
                 r_ts_cm=None, rho_shocked_wind_g_cm3=None,
                 r_wall_cm=None, rho_wall_g_cm3=None):
        """
        Option A Analytical Model (Piecewise Geometric Bubble)
        
        Mandatory features:
        - Free Wind (defined by mdot and vwind)
        - Undisturbed ISM (defined by r_ism_cm and rho_ism_g_cm3)
        
        Optional features (set to None to omit):
        - Termination Shock (r_ts_cm, rho_shocked_wind_g_cm3)
        - Swept-up Wall / Shell (r_wall_cm, rho_wall_g_cm3)
        """
        self.r_ism = r_ism_cm
        self.rho_ism = rho_ism_g_cm3
        self.r_ts = r_ts_cm
        self.rho_cavity = rho_shocked_wind_g_cm3
        self.r_wall = r_wall_cm
        self.rho_wall = rho_wall_g_cm3
        
        # Physical constants
        msun_g = 1.989e33
        yr_s = 3.154e7
        
        # Calculate the free wind density coefficient: rho = A / r^2
        # Mdot = 4 * pi * r^2 * rho * v_wind  =>  rho = Mdot / (4 * pi * v_wind * r^2)
        mdot_cgs = mdot_msun_yr * (msun_g / yr_s)
        vwind_cgs = vwind_km_s * 1e5
        self.wind_coeff = mdot_cgs / (4.0 * np.pi * vwind_cgs)

    def evaluate(self, r_cm):
        r = np.atleast_1d(r_cm)
        rho_out = np.zeros_like(r)
        
        # We will build the piecewise regions from the outside in, overriding values.
        
        # 1. Base Region: Undisturbed ISM
        rho_out[:] = self.rho_ism
        
        # 2. Swept-Up Wall (If parameters are provided)
        # Bounded between r_wall and r_ism
        if self.r_wall is not None and self.rho_wall is not None:
            mask_wall = (r >= self.r_wall) & (r < self.r_ism)
            rho_out[mask_wall] = self.rho_wall
            inner_boundary_for_cavity = self.r_wall
        else:
            inner_boundary_for_cavity = self.r_ism
            
        # 3. Shocked Wind / Cavity (If parameters are provided)
        # Bounded between r_ts and whatever the next outer feature is
        if self.r_ts is not None and self.rho_cavity is not None:
            mask_cavity = (r >= self.r_ts) & (r < inner_boundary_for_cavity)
            rho_out[mask_cavity] = self.rho_cavity
            inner_boundary_for_wind = self.r_ts
        else:
            inner_boundary_for_wind = inner_boundary_for_cavity
            
        # 4. Free Wind (Always present)
        # Exists everywhere inside the innermost defined shock
        mask_wind = r < inner_boundary_for_wind
        rho_out[mask_wind] = self.wind_coeff / (r[mask_wind]**2)
        
        return rho_out

def run_tests():
    # Parameters broadly matching the AMRVAC scales
    mdot = 1e-6    # Msun/yr
    vw = 1000.0    # km/s
    pc = 3.086e18  # cm
    
    r_eval = np.logspace(17, 19.5, 1000)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Test 1: Full Classical 4-Region Bubble (Like p4)
    model1 = AnalyticalBubbleOptionA(
        mdot_msun_yr=mdot, vwind_km_s=vw,
        r_ts_cm=1.0*pc, rho_shocked_wind_g_cm3=1e-26,
        r_wall_cm=5.0*pc, rho_wall_g_cm3=1e-22,
        r_ism_cm=6.0*pc, rho_ism_g_cm3=1e-24
    )
    axes[0].plot(r_eval, model1.evaluate(r_eval), 'b-', lw=2)
    axes[0].set_title('Full 4-Region Bubble\n(All optional params given)')
    
    # Test 2: Crushed 3-Region Bubble (Like p6 - No Swept-up Wall)
    model2 = AnalyticalBubbleOptionA(
        mdot_msun_yr=mdot, vwind_km_s=vw,
        r_ts_cm=0.3*pc, rho_shocked_wind_g_cm3=1e-24,
        r_wall_cm=None, rho_wall_g_cm3=None,       # OMITTED
        r_ism_cm=2.0*pc, rho_ism_g_cm3=1e-22
    )
    axes[1].plot(r_eval, model2.evaluate(r_eval), 'r-', lw=2)
    axes[1].set_title('Crushed 3-Region Bubble\n(No Swept-Up Wall parameters)')
    
    # Test 3: Naked Free Wind hitting ISM (No shock/cavity params)
    model3 = AnalyticalBubbleOptionA(
        mdot_msun_yr=mdot, vwind_km_s=vw,
        r_ts_cm=None, rho_shocked_wind_g_cm3=None, # OMITTED
        r_wall_cm=None, rho_wall_g_cm3=None,       # OMITTED
        r_ism_cm=0.5*pc, rho_ism_g_cm3=1e-22
    )
    axes[2].plot(r_eval, model3.evaluate(r_eval), 'k-', lw=2)
    axes[2].set_title('Naked Wind hitting ISM\n(Only mandatory params)')
    
    for ax in axes:
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_ylim(1e-28, 1e-20)
        ax.set_xlabel('Radius (cm)')
        ax.set_ylabel('Density (g cm^-3)')
        ax.grid(True, ls=':', alpha=0.6)
        
    plt.tight_layout()
    plt.savefig('option_a_demonstration.png', dpi=150)
    print("Saved Option A test plots to option_a_demonstration.png")

if __name__ == '__main__':
    run_tests()
