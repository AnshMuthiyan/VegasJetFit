"""Plot raw AMRVAC 1D VTU point profiles with physical units."""
import argparse
import csv
import re
import struct
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

PC = 3.0857e18
YEAR = 365 * 86400  # installed AMRVAC const_years = 3.1536e7 s


def read_vtu(path):
    raw = path.read_bytes()
    app = raw.index(b'<AppendedData')
    base = raw.index(b'_', app) + 1
    header = raw[:app].decode('ascii')
    time = float(re.search(r'Name="TIME"[^>]*>\s*([^<]+)', header).group(1))
    chunks = []
    for piece in re.finditer(r'<Piece\b[^>]*>(.*?)</Piece>', header, re.S):
        body = piece.group(1)

        def array(pattern):
            match = re.search(pattern, body, re.S)
            if match is None:
                raise ValueError(f'{path}: missing VTU array {pattern}')
            offset = base + int(match.group(1))
            count = struct.unpack_from('<I', raw, offset)[0] // 4
            return np.frombuffer(raw, dtype='<f4', count=count, offset=offset+4).astype(float)

        xyz = array(r'<Points>\s*<DataArray[^>]*offset="\s*(\d+)"').reshape(-1, 3)
        fields = [array(r'<DataArray[^>]*Name="'+name+r'"[^>]*offset="\s*(\d+)"')
                  for name in ('rho', 'v1', 'p', 'Te')]
        chunk = np.column_stack((xyz[:, 0]/PC, *fields))
        if not np.all(np.isfinite(chunk)):
            raise ValueError(f'{path}: nonfinite saved values')
        if np.any(chunk[:, [1, 3, 4]] <= 0):
            raise ValueError(f'{path}: nonpositive density, pressure or temperature ratio')
        chunks.append(chunk)
    values = np.concatenate(chunks)
    values = values[np.argsort(values[:, 0])]
    # Shared block-edge nodes are duplicated; retain their median, no smoothing.
    radii, first, count = np.unique(np.round(values[:, 0], 10), return_index=True, return_counts=True)
    profiles = np.array([np.median(values[i:i+n], axis=0) for i, n in zip(first, count)])
    return time/YEAR/1e6, profiles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    out = run/'plots'
    out.mkdir(exist_ok=True)
    log_bytes = (run/'run.log').read_bytes()
    encoding = 'utf-16' if log_bytes.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    log = log_bytes.decode(encoding, errors='replace')
    rho_ism = float(re.search(r'Ambient density \[g cm\^-3\]:\s*(\S+)', log).group(1))
    tunit = float(re.search(r'Temperature unit:\s*(\S+)', log).group(1))
    cutoff_match = re.search(r'Cooling cutoff \[K\]:\s*(\S+)', log)
    cooling_cutoff = float(cutoff_match.group(1)) if cutoff_match else 50.0
    snapshots = []
    records = []
    for path in sorted(run.glob('test*.vtu')):
        age, profile = read_vtu(path)
        # Domain-face point values mix physical and prescribed ghost cells.
        # Plot only interior points; read_vtu validates all raw values first.
        profile = profile[1:-1]
        profile[:, 2] /= 1e5  # velocity output is already cm/s
        profile[:, 4] *= tunit  # Te = p_code/rho_code, not kelvin
        snapshots.append((path.name, age, profile))
        peak = np.argmax(profile[:, 1])
        records.append(dict(snapshot=path.name, age_Myr=age, unique_points=len(profile),
                            min_rho_g_cm3=profile[:, 1].min(), max_rho_g_cm3=profile[:, 1].max(),
                            peak_r_pc=profile[peak, 0], peak_over_ISM=profile[peak, 1]/rho_ism,
                            min_v_km_s=profile[:, 2].min(), max_v_km_s=profile[:, 2].max(),
                            min_p_dyn_cm2=profile[:, 3].min(), max_p_dyn_cm2=profile[:, 3].max(),
                            min_T_K=profile[:, 4].min(), max_T_K=profile[:, 4].max()))
        np.savetxt(out/(path.stem+'_profile.csv'), profile, delimiter=',',
                   header='radius_pc,rho_g_cm3,v_km_s,p_dyn_cm2,T_K', comments='')
    if not snapshots:
        raise ValueError('No VTU snapshots found')
    colors = plt.cm.viridis(np.linspace(.05, .9, len(snapshots)))
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, layout='constrained')
    labels = [r'Density $\rho$ [g cm$^{-3}$]', 'Radial velocity [km/s]',
              r'Thermal pressure [dyn cm$^{-2}$]', 'Temperature [K]']
    for ax, column, label in zip(axes.flat, range(1, 5), labels):
        for (_, age, p), color in zip(snapshots, colors):
            ax.plot(p[:, 0], p[:, column], color=color, lw=1.5, label=f'{age:.3f} Myr')
        if column != 2:
            ax.set_yscale('log')
        ax.set_ylabel(label)
        ax.set_xlabel('Radius [pc]')
        ax.grid(alpha=.22)
    axes[0, 0].axhline(rho_ism, color='grey', ls='--', label='Ambient ISM')
    axes[1, 1].axhline(cooling_cutoff, color='grey', ls='--',
                      label=f'{cooling_cutoff:g} K cooling cutoff')
    axes[0, 0].legend(fontsize=9)
    fig.suptitle('Dense cooling run: saved radial profiles')
    fig.savefig(out/'radial_profiles.png', dpi=180)
    fig.savefig(out/'radial_profiles.pdf')
    for ax in axes.flat:
        ax.set_xlim(snapshots[-1][2][0, 0], 1.2)
    fig.suptitle('Dense cooling run: inner 1.2 pc (saved point profiles)')
    fig.savefig(out/'inner_profiles.png', dpi=180)
    fig.savefig(out/'inner_profiles.pdf')
    plt.close(fig)

    name, age, p = snapshots[-1]
    peak = int(np.argmax(p[:, 1]))
    center = p[peak, 0]
    half_width = max(.1, .12*center)
    zoom = (p[:, 0] >= center-half_width) & (p[:, 0] <= center+half_width)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    for (_, time, data), color in zip(snapshots, colors):
        axes[0].plot(data[:, 0], data[:, 1]/rho_ism, color=color, label=f'{time:.3f} Myr')
    axes[0].set_yscale('log')
    axes[0].legend(fontsize=9)
    axes[0].set_title('Density evolution')
    axes[1].plot(p[zoom, 0], p[zoom, 1]/rho_ism, '.-', color=colors[-1], markersize=4)
    axes[1].set_title(f'Final density peak: {age:.3f} Myr')
    for ax in axes:
        ax.axhline(1, color='grey', ls='--')
        ax.set_xlabel('Radius [pc]')
        ax.set_ylabel(r'$\rho/\rho_{\mathrm{ISM}}$')
        ax.grid(alpha=.22)
    fig.savefig(out/'density_wall_zoom.png', dpi=180)
    fig.savefig(out/'density_wall_zoom.pdf')
    plt.close(fig)
    with (out/'snapshot_summary.csv').open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    for row in records:
        print(f"{row['snapshot']}: t={row['age_Myr']:.6f} Myr, "
              f"peak/ISM={row['peak_over_ISM']:.6g} at {row['peak_r_pc']:.6f} pc, "
              f"T=[{row['min_T_K']:.6g}, {row['max_T_K']:.6g}] K")
    print('All raw saved rho/p/Te values finite and positive; velocity finite.')
    print('Plots and profile tables:', out)


if __name__ == '__main__':
    main()
