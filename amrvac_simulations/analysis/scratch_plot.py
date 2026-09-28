import numpy as np
import matplotlib.pyplot as plt
import re, struct
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

def plot_all_profiles():
    vtu_dir = Path('amrvac_simulations/selected_vtu')
    vtu_files = sorted(vtu_dir.glob('*.vtu'))
    
    plt.figure(figsize=(12, 8))
    
    for file_path in vtu_files:
        x, rho = read_vtu(file_path)
        # Extract the run ID from the filename (e.g., "p4_n21" from "p4_n21__test0004.vtu")
        run_id = file_path.name.split('__')[0]
        
        # Plot on log-log scale
        plt.plot(x, rho, label=run_id, lw=1.5)
        
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Radius (cm)', fontsize=12)
    plt.ylabel(r'Density (g cm$^{-3}$)', fontsize=12)
    plt.title('AMRVAC Wind Bubble Density Profiles', fontsize=14)
    plt.grid(True, which='both', ls=':', alpha=0.6)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    output_file = 'all_density_profiles.png'
    plt.savefig(output_file, dpi=150)
    print(f"Successfully generated {output_file} with {len(vtu_files)} profiles!")

if __name__ == '__main__':
    plot_all_profiles()
