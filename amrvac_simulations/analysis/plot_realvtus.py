import numpy as np
import matplotlib.pyplot as plt
import re, struct
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
        rho_m = re.search(r'Name=\"rho\"[^>]*offset=\"\s*(\d+)\"', body)
        pts_m = re.search(r'<Points>\s*<DataArray[^>]*offset=\"\s*(\d+)\"', body, re.S)
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

def main():
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Run 1: Evolving Wind (RealVtus root)
    # Get the final snapshot
    evolving_files = sorted(Path(r'C:\Users\anshm\Projects\GRB modelling\Hydrocodes\RealVtus').glob('test*.vtu'))
    if evolving_files:
        final_evolving = evolving_files[-1]
        r_cm, rho = read_vtu(final_evolving)
        ax.plot(r_cm, rho, 'r-', lw=2, label=f'Evolving Wind Run ({final_evolving.name})')
        
    # Run 2: Steady Wind (RealVtus/Steadywind)
    steady_files = sorted(Path(r'C:\Users\anshm\Projects\GRB modelling\Hydrocodes\RealVtus\Steadywind').glob('steady*.vtu'))
    if steady_files:
        final_steady = steady_files[-1]
        r_cm_s, rho_s = read_vtu(final_steady)
        ax.plot(r_cm_s, rho_s, 'b--', lw=2, label=f'Steady Wind Run ({final_steady.name})')
        
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Radius (cm)', fontsize=14)
    ax.set_ylabel('Density (g cm^-3)', fontsize=14)
    ax.set_title('Final Snapshots of Evolving vs Steady Wind Runs (RealVtus)', fontsize=16)
    ax.grid(True, ls=':', alpha=0.6)
    ax.legend(fontsize=12)
    
    plt.tight_layout()
    plt.savefig('realvtus_comparison.png', dpi=150)
    print("Saved plot to realvtus_comparison.png")

if __name__ == '__main__':
    main()
