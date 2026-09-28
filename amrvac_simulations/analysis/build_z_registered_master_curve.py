import numpy as np
import matplotlib.pyplot as plt
import csv, re, struct
from pathlib import Path

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

def load_tables():
    plan = {}
    with open('amrvac_simulations/tables/log_grid_plan.csv') as f:
        for row in csv.DictReader(f):
            plan[row['run_id']] = {'rt': float(row['rt_external_pc']), 'rho_ism': float(row['rho_g_cm3'])}
            
    quality = {}
    with open('amrvac_simulations/tables/allP_run_quality_table.csv') as f:
        for row in csv.DictReader(f):
            quality[row['run_id']] = {'x_ts': float(row['x_ts']), 'x_outer': float(row['x_final_rise'])}
    return plan, quality

def main():
    plan, quality = load_tables()
    vtu_files = sorted(Path('amrvac_simulations/selected_vtu').glob('*.vtu'))
    
    # We will make two plots side-by-side: Unregistered vs Registered
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Colormap based on index
    colors = plt.cm.viridis(np.linspace(0, 1, len(vtu_files)))
    
    # common Z grid for interpolation (optional, but let's just scatter plot first)
    z_grid = np.linspace(-0.5, 1.5, 500)
    
    for i, file_path in enumerate(vtu_files):
        run_id = file_path.name.split('__')[0]
        if run_id not in quality:
            continue
            
        r_cm, rho_g_cm3 = read_vtu(file_path)
        
        # Physical constants
        pc_to_cm = 3.0857e18
        
        # 1. Normalize variables
        r_pc = r_cm / pc_to_cm
        rt_pc = plan[run_id]['rt']
        x = r_pc / rt_pc
        
        rho_ism = plan[run_id]['rho_ism']
        rho_norm = np.log10(rho_g_cm3 / rho_ism)
        
        # Unregistered Plot (x-axis is just normalized radius)
        ax1.plot(np.log10(x), rho_norm, color=colors[i], label=run_id, alpha=0.7)
        
        # 2. Warp to Z coordinate
        x_ts = quality[run_id]['x_ts']
        x_outer = quality[run_id]['x_outer']
        
        log_x = np.log10(x)
        log_ts = np.log10(x_ts)
        log_out = np.log10(x_outer)
        
        z = (log_x - log_ts) / (log_out - log_ts)
        
        # Registered Plot
        ax2.plot(z, rho_norm, color=colors[i], label=run_id, alpha=0.7)

    # Format Unregistered Plot
    ax1.set_title('Unregistered (log x)', fontsize=14)
    ax1.set_xlabel('log10(r / Rt)', fontsize=12)
    ax1.set_ylabel('log10(rho / rho_ISM)', fontsize=12)
    ax1.grid(True, ls=':', alpha=0.6)
    
    # Format Registered Plot
    ax2.set_title('Z-Registered Master Curve', fontsize=14)
    ax2.set_xlabel('z (Warped Coordinate)', fontsize=12)
    ax2.set_ylabel('log10(rho / rho_ISM)', fontsize=12)
    ax2.grid(True, ls=':', alpha=0.6)
    
    # Highlight the registration points
    ax2.axvline(0, color='red', linestyle='--', label='z=0 (Termination Shock)')
    ax2.axvline(1, color='blue', linestyle='--', label='z=1 (Outer Shell Onset)')
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig('z_registered_master_curve.png', dpi=150)
    print("Registration complete! Saved to z_registered_master_curve.png")

if __name__ == '__main__':
    main()
