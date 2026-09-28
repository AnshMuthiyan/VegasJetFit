import numpy as np
import matplotlib.pyplot as plt
import re, struct, csv
from pathlib import Path
from matplotlib.gridspec import GridSpec

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

def extract_features(x, rho, expected_rho_ism):
    features = {
        'R_wind_end': np.nan, 'Rho_wind_end': np.nan,
        'R_cavity': np.nan, 'Rho_cavity': np.nan,
        'R_peak': np.nan, 'Rho_peak': np.nan,
        'R_ism': np.nan, 'Rho_ism': np.nan
    }
    
    far_right_rho = rho[-1]
    deviation = np.abs(rho - expected_rho_ism) / expected_rho_ism
    above_ism = np.where(deviation > 0.02)[0]
    if len(above_ism) > 0:
        ism_idx = above_ism[-1] + 1
        if ism_idx >= len(rho):
            ism_idx = len(rho) - 1
    else:
        ism_idx = len(rho) - 1
        
    features['R_ism'] = x[ism_idx]
    features['Rho_ism'] = rho[ism_idx]
    
    if rho[1] < rho[0]:
        diffs = np.diff(rho)
        increases = np.where(diffs > 0)[0]
        if len(increases) > 0:
            ts_idx = increases[0]
            features['R_wind_end'] = x[ts_idx]
            features['Rho_wind_end'] = rho[ts_idx]
        else:
            ts_idx = None
    else:
        ts_idx = None
        
    max_rho_ratio = np.max(rho) / expected_rho_ism
    if max_rho_ratio > 1.05:
        peak_idx = np.argmax(rho)
        features['R_peak'] = x[peak_idx]
        features['Rho_peak'] = rho[peak_idx]
    else:
        peak_idx = None
        
    if ts_idx is not None and peak_idx is not None and peak_idx > ts_idx:
        cavity_idx = ts_idx + np.argmin(rho[ts_idx:peak_idx])
        features['R_cavity'] = x[cavity_idx]
        features['Rho_cavity'] = rho[cavity_idx]
        
    return features

def main():
    vtu_dir = Path('amrvac_simulations/selected_vtu')
    vtu_files = sorted(vtu_dir.glob('*.vtu'))
    
    # Identify unique densities
    all_n = set()
    for file_path in vtu_files:
        run_id = file_path.name.split('__')[0]
        n_val = int(run_id.split('_n')[1])
        all_n.add(n_val)
        
    all_n = sorted(list(all_n))
    
    # Create a grid for the plots (e.g., 2 rows, 3 columns for 6 densities)
    rows, cols = 2, 3
    fig, axes = plt.subplots(rows, cols, figsize=(20, 10))
    axes = axes.flatten()
    
    n_to_ax = {n_val: ax for n_val, ax in zip(all_n, axes)}
    
    for i, file_path in enumerate(vtu_files):
        x, rho = read_vtu(file_path)
        run_id = file_path.name.split('__')[0]
        
        pressure_group = int(run_id.split('_')[0][1:])
        n_val = int(run_id.split('_n')[1])
        expected_ism = 10**(-n_val)
        
        features = extract_features(x, rho, expected_ism)
        
        ax = n_to_ax[n_val]
        color = plt.cm.tab10(pressure_group % 10) 
        
        ax.plot(x, rho, label=run_id, color=color, lw=1.5)
        
        ax.scatter(features['R_wind_end'], features['Rho_wind_end'], color=color, marker='o', s=60, edgecolors='k', zorder=5)
        ax.scatter(features['R_cavity'], features['Rho_cavity'], color=color, marker='v', s=60, edgecolors='k', zorder=5)
        ax.scatter(features['R_peak'], features['Rho_peak'], color=color, marker='^', s=60, edgecolors='k', zorder=5)
        ax.scatter(features['R_ism'], features['Rho_ism'], color=color, marker='s', s=60, edgecolors='k', zorder=5)

    for n_val, ax in n_to_ax.items():
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('Radius (cm)', fontsize=12)
        ax.set_ylabel('Density (g cm{-3}$)', fontsize=12)
        ax.set_title(f'Density: ISM = 10^{{-{n_val}}}', fontsize=14)
        ax.legend(loc='upper right')
        ax.grid(True, which='both', ls=':', alpha=0.5)
        
    fig.suptitle('Extracted Bubble Features Grouped by Ambient Density\n(Circle: TS, Down-Triangle: Cavity, Up-Triangle: Peak, Square: ISM)', fontsize=18, y=1.02)
    plt.tight_layout()
    plt.savefig('extracted_features_by_density.png', dpi=150, bbox_inches='tight')
    
    print("Saved extracted_features_by_density.png")

if __name__ == '__main__':
    main()
