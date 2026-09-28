import numpy as np
import matplotlib.pyplot as plt
import re, struct, csv
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

def extract_features(x, rho, expected_rho_ism):
    # Default to NaN for all features
    features = {
        'R_wind_end': np.nan, 'Rho_wind_end': np.nan,
        'R_cavity': np.nan, 'Rho_cavity': np.nan,
        'R_peak': np.nan, 'Rho_peak': np.nan,
        'R_ism': np.nan, 'Rho_ism': np.nan
    }
    
    # 1. Start of unperturbed ISM (always exists)
    # Start from the rightmost edge and walk inwards until density is 2% higher or lower than ISM
    far_right_rho = rho[-1]
    # Check deviation from expected ISM
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
    
    # 2. End of free wind (Termination Shock base)
    # Check if the profile starts by decreasing. If it increases immediately, no free wind was captured!
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
        
    # 3. Peak / Jump (Forward Shock Shell)
    # Check if a dense shell actually exists. If max density isn't > 1.05x ISM, it's just a crushed cavity.
    max_rho_ratio = np.max(rho) / expected_rho_ism
    if max_rho_ratio > 1.05:
        peak_idx = np.argmax(rho)
        features['R_peak'] = x[peak_idx]
        features['Rho_peak'] = rho[peak_idx]
    else:
        peak_idx = None
        
    # 4. Pre-jump Cavity
    # The lowest density point between the termination shock and the shell peak
    # Only exists if BOTH the termination shock and the shell peak exist
    if ts_idx is not None and peak_idx is not None and peak_idx > ts_idx:
        cavity_idx = ts_idx + np.argmin(rho[ts_idx:peak_idx])
        features['R_cavity'] = x[cavity_idx]
        features['Rho_cavity'] = rho[cavity_idx]
        
    return features

def main():
    vtu_dir = Path('amrvac_simulations/selected_vtu')
    vtu_files = sorted(vtu_dir.glob('*.vtu'))
    
    results = []
    
    # Create a 1x3 subplot grid for p4, p5, p6
    fig, axes = plt.subplots(1, 3, figsize=(20, 6), sharey=True)
    pressure_to_ax = {'p4': axes[0], 'p5': axes[1], 'p6': axes[2]}
    
    for i, file_path in enumerate(vtu_files):
        x, rho = read_vtu(file_path)
        run_id = file_path.name.split('__')[0]
        
        # Parse expected ISM density and pressure group
        pressure_group = run_id.split('_')[0]
        n_val = int(run_id.split('_n')[1])
        expected_ism = 10**(-n_val)
        
        features = extract_features(x, rho, expected_ism)
        
        row = {'Run_ID': run_id}
        row.update(features)
        results.append(row)
        
        # Plotting on the correct subplot
        ax = pressure_to_ax[pressure_group]
        color = plt.cm.tab10(n_val % 10) # distinctive color based on density
        
        ax.plot(x, rho, label=run_id, color=color, lw=1.5)
        
        # Mark features
        ax.scatter(features['R_wind_end'], features['Rho_wind_end'], color=color, marker='o', s=60, edgecolors='k', zorder=5)
        ax.scatter(features['R_cavity'], features['Rho_cavity'], color=color, marker='v', s=60, edgecolors='k', zorder=5)
        ax.scatter(features['R_peak'], features['Rho_peak'], color=color, marker='^', s=60, edgecolors='k', zorder=5)
        ax.scatter(features['R_ism'], features['Rho_ism'], color=color, marker='s', s=60, edgecolors='k', zorder=5)

    # Format all subplots
    for ax, p_label in zip(axes, ['p4 (P/k=10^4)', 'p5 (P/k=10^5)', 'p6 (P/k=10^6)']):
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('Radius (cm)', fontsize=14)
        if ax == axes[0]:
            ax.set_ylabel('Density (g cm$^{-3}$)', fontsize=14)
        ax.set_title(f'Pressure: {p_label}', fontsize=16)
        ax.legend(loc='upper right')
        ax.grid(True, which='both', ls=':', alpha=0.5)
        
    fig.suptitle('Extracted Bubble Features\n(Circle: TS, Down-Triangle: Cavity, Up-Triangle: Peak, Square: ISM)', fontsize=18, y=1.05)
    plt.tight_layout()
    plt.savefig('extracted_features_plot.png', dpi=150, bbox_inches='tight')
    
    # Save CSV
    keys = results[0].keys()
    with open('extracted_bubble_features.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
        
    print("Feature extraction complete! Saved to extracted_bubble_features.csv and extracted_features_plot.png.")

if __name__ == '__main__':
    main()
