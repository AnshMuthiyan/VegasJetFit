import numpy as np
import matplotlib.pyplot as plt
import csv, re, struct
from pathlib import Path

# --- VTU Reader ---
def read_vtu(path):
    raw = path.read_bytes()
    app_start = raw.find(b'<AppendedData')
    data_start = raw.find(b'_', app_start) + 1
    data_end = raw.find(b'</AppendedData>', data_start)
    header = raw[:app_start].decode('ascii', 'ignore')
    appended = raw[data_start:data_end]
    xs = []; rhos = []
    for piece in re.finditer(r'<Piece NumberOfPoints=\"\s*(\d+)\".*?</Piece>', header, re.S):
        body = piece.group(0)
        rho_m = re.search(r'Name=\"rho\"[^>]*offset=\"(\d+)\"', body)
        pts_m = re.search(r'<Points>\s*<DataArray[^>]*offset=\"(\d+)\"', body, re.S)
        if not rho_m or not pts_m: continue
        rho_off = int(rho_m.group(1)); pts_off = int(pts_m.group(1))
        rho_len = struct.unpack_from('<I', appended, rho_off)[0]
        pts_len = struct.unpack_from('<I', appended, pts_off)[0]
        rho = np.frombuffer(appended, dtype='<f4', count=rho_len // 4, offset=rho_off + 4).copy()
        pts = np.frombuffer(appended, dtype='<f4', count=pts_len // 4, offset=pts_off + 4).reshape(-1, 3).copy()
        xs.extend(pts[:, 0]); rhos.extend(rho)
    arr = np.array(list(zip(xs, rhos)), dtype=float)
    arr = arr[np.argsort(arr[:, 0])]
    return arr[:, 0], arr[:, 1]

# --- Surrogate Implementation ---
from scipy.interpolate import PchipInterpolator

class BubbleSurrogate:
    def __init__(self):
        self.pc_to_cm = 3.0857e18
        
        # Load grid plan
        self.plan = {}
        with open('amrvac_simulations/tables/log_grid_plan.csv') as f:
            for row in csv.DictReader(f):
                self.plan[row['run_id']] = float(row['rt_external_pc'])
                
        # Load quality table (for registration training)
        self.quality = {}
        with open('amrvac_simulations/tables/allP_run_quality_table.csv') as f:
            for row in csv.DictReader(f):
                # We need the p and n values to build the interpolation grid
                self.quality[row['run_id']] = {
                    'p': float(row['p']),
                    'n': float(row['n']),
                    'x_ts': float(row['x_ts']), 
                    'x_outer': float(row['x_final_rise'])
                }
                
        # Build Master 2D Density Table
        self.z_grid = np.linspace(-0.5, 1.5, 500)
        
        self.records = []
        for file_path in sorted(Path('amrvac_simulations/selected_vtu').glob('*.vtu')):
            run_id = file_path.name.split('__')[0]
            if run_id not in self.quality: continue
            
            x_ts = self.quality[run_id]['x_ts']
            x_out = self.quality[run_id]['x_outer']
            r_cm, rho_g = read_vtu(file_path)
            
            r_pc = r_cm / self.pc_to_cm
            x = r_pc / self.plan[run_id]
            rho_ism = 10**self.quality[run_id]['n']
            rho_norm = np.log10(rho_g / rho_ism)
            
            z = (np.log10(x) - np.log10(x_ts)) / (np.log10(x_out) - np.log10(x_ts))
            
            # Interpolate onto standard Z grid
            interp_curve = np.interp(self.z_grid, z, rho_norm, left=rho_norm[0], right=rho_norm[-1])
            
            self.records.append({
                'p': self.quality[run_id]['p'],
                'n': self.quality[run_id]['n'],
                'x_ts': x_ts,
                'x_outer': x_out,
                'curve': interp_curve
            })

    def predict_density(self, p_query, n_query, r_cm):
        # 1. We must interpolate across n, then across p
        unique_p = sorted(list(set(r['p'] for r in self.records)))
        
        ly_per_p = {}
        lxts_per_p = {}
        lxouter_per_p = {}
        
        for p0 in unique_p:
            sub = [r for r in self.records if r['p'] == p0]
            sub.sort(key=lambda r: r['n'])
            
            n_train = np.array([r['n'] for r in sub])
            lxts_train = np.log10(np.array([r['x_ts'] for r in sub]))
            lxouter_train = np.log10(np.array([r['x_outer'] for r in sub]))
            ly_rows = np.array([r['curve'] for r in sub])
            
            # PCHIP interpolation across density 'n'
            ly_interp = np.zeros_like(self.z_grid)
            for j in range(len(self.z_grid)):
                ly_interp[j] = PchipInterpolator(n_train, ly_rows[:, j])(n_query)
                
            ly_per_p[p0] = ly_interp
            lxts_per_p[p0] = float(PchipInterpolator(n_train, lxts_train)(n_query))
            lxouter_per_p[p0] = float(PchipInterpolator(n_train, lxouter_train)(n_query))
            
        # PCHIP interpolation across pressure 'p'
        p_train = np.array(unique_p)
        ly_stack = np.array([ly_per_p[p0] for p0 in unique_p])
        
        ly_final = np.zeros_like(self.z_grid)
        for j in range(len(self.z_grid)):
            ly_final[j] = PchipInterpolator(p_train, ly_stack[:, j])(p_query)
            
        lxts_final = float(PchipInterpolator(p_train, np.array([lxts_per_p[p0] for p0 in unique_p]))(p_query))
        lxouter_final = float(PchipInterpolator(p_train, np.array([lxouter_per_p[p0] for p0 in unique_p]))(p_query))
        
        x_ts = 10**lxts_final
        x_out = 10**lxouter_final
        
        # 2. Convert query radius r_cm -> z
        # Theoretical Rt scales exactly as P^{-1/2}. 
        # Base Rt at p=4 is ~0.9838 pc.
        base_rt_p4 = 0.9838477348677321
        Rt_pc = base_rt_p4 * 10**(-(p_query - 4.0) / 2.0)
        
        x = (r_cm / self.pc_to_cm) / Rt_pc
        z = (np.log10(x) - np.log10(x_ts)) / (np.log10(x_out) - np.log10(x_ts))
        
        # 3. Lookup in master table
        predicted_rho_norm = np.interp(z, self.z_grid, ly_final, left=ly_final[0], right=ly_final[-1])
        
        # 4. Un-normalize density
        rho_ism = 10**n_query
        rho_out = rho_ism * (10**predicted_rho_norm)
        
        # 5. Enforce analytical free wind for unsimulated inner regions (x < 0.2)
        # Find the exact density at the simulation boundary to act as the anchor
        z_boundary = (np.log10(0.2) - np.log10(x_ts)) / (np.log10(x_out) - np.log10(x_ts))
        rho_norm_boundary = np.interp(z_boundary, self.z_grid, ly_final)
        rho_boundary = rho_ism * (10**rho_norm_boundary)
        
        inner_mask = x < 0.2
        if np.any(inner_mask):
            rho_out[inner_mask] = rho_boundary * (x[inner_mask] / 0.2)**(-2)
            
        return rho_out

# --- Testing Off-Grid Morphing ---
def test_inbetween():
    surrogate = BubbleSurrogate()
    
    # Define some off-grid target test environments
    test_cases = [
        {'p': 4.5, 'n': -22.5, 'title': 'Midway (p=4.5, n=-22.5)'},
        {'p': 5.5, 'n': -20.5, 'title': 'High Pressure (p=5.5, n=-20.5)'},
        {'p': 4.2, 'n': -23.5, 'title': 'Sparse & Large (p=4.2, n=-23.5)'},
        {'p': 5.8, 'n': -19.5, 'title': 'Dense & Crushed (p=5.8, n=-19.5)'}
    ]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    # Extended evaluation radius deep into the unsimulated free wind zone (down to 10^15 cm)
    r_eval = np.logspace(16.5, 19.5, 800) 
    
    for ax, case in zip(axes.flat, test_cases):
        p_q, n_q = case['p'], case['n']
        
        # Evaluate the off-grid surrogate
        rho_pred = surrogate.predict_density(p_q, n_q, r_eval)
        
        # Plot the off-grid prediction
        ax.plot(r_eval, rho_pred, 'r-', lw=2.5, label=f'Off-grid Predictor\np={p_q}, n={n_q}')
        
        # Also evaluate & plot the nearest on-grid integers to provide visual context
        p_floor, p_ceil = int(np.floor(p_q)), int(np.ceil(p_q))
        n_floor, n_ceil = int(np.floor(n_q)), int(np.ceil(n_q))
        
        rho_near1 = surrogate.predict_density(p_floor, n_floor, r_eval)
        rho_near2 = surrogate.predict_density(p_ceil, n_ceil, r_eval)
        
        ax.plot(r_eval, rho_near1, 'k--', alpha=0.5, label=f'On-grid context\np={p_floor}, n={n_floor}')
        ax.plot(r_eval, rho_near2, 'b--', alpha=0.5, label=f'On-grid context\np={p_ceil}, n={n_ceil}')
        
        # Mark the simulation boundary
        rt_pc = 0.9838477348677321 * 10**(-(p_q - 4.0) / 2.0)
        sim_boundary_cm = 0.2 * rt_pc * 3.0857e18
        ax.axvline(sim_boundary_cm, color='gray', linestyle=':', label='Simulated Boundary (x=0.2)')
        
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_title(case['title'], fontsize=14)
        ax.set_xlabel('Radius (cm)')
        ax.set_ylabel('Density (g cm-3)')
        ax.legend()
        ax.grid(True, ls=':', alpha=0.6)

    fig.suptitle('Off-Grid Surrogate Interpolation (With r^-2 analytical free wind extension)', fontsize=16)
    plt.tight_layout()
    plt.savefig('surrogate_off_grid_tests.png', dpi=150)
    print("In-between testing complete! Results saved to surrogate_off_grid_tests.png")

if __name__ == '__main__':
    test_inbetween()
