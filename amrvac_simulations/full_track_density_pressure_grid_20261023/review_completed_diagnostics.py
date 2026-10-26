#!/usr/bin/env python3
"""Add readable native-grid review figures and explicit feature limitations.

Consumes completed reconciliation products only; never launches or transfers.
Preserves the first diagnostic products and writes a new reviewed_diagnostics/.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/amrvac_full_grid_mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, LogFormatterSciNotation
import numpy as np

PC = 3.085677581e18
MSUN = 1.98892e33


def radius_axes(ax, inner=False):
    ax.set_xscale('log')
    ax.set_xlim(.001*PC, (2 if inner else 160)*PC)
    ax.set_xlabel('Radius (cm)')
    top = ax.secondary_xaxis('top', functions=(lambda cm: cm/PC, lambda pc: pc*PC))
    top.set_xlabel('Radius (pc)')
    ax.grid(alpha=.18, which='both')


def write_json(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def review(case):
    dest = case/'reviewed_diagnostics'
    dest.mkdir(exist_ok=False)
    features = json.loads((case/'feature_diagnostics.json').read_text())
    data = [np.genfromtxt(p, delimiter=',', names=True) for p in sorted((case/'native_profiles').glob('snapshot_*.csv'))]
    assert len(data) == len(features)
    for f in features:
        flags = []
        for key in ('inner_rise_candidate', 'outer_shell_candidate', 'termination_flow_candidate'):
            if f[key] is None:
                flags.append(key.upper()+'_MISSING')
            elif f[key].get('flags'):
                flags.extend(key.upper()+'_'+v for v in f[key]['flags'])
        for c in f['all_density_rise_candidates']:
            if c['local_peak_fwhm_pc'] is not None and c['local_peak_fwhm_pc'] > c['peak_pc']:
                c['flags'].append('NONLOCAL_HALF_HEIGHT_ENVELOPE')
            c['width_interpretation'] = 'Numerical profile crossings, not physical shock thickness; broad half-height widths may include the declining initial cloud envelope.'
        f['quality_flags'] = sorted(set(flags))
        f['fit_eligible'] = False
        f['fit_eligibility_reason'] = 'No approved surrogate; single survey mesh. Missing or unresolved physical features require independent review and refinement.'
    write_json(dest/'feature_diagnostics_reviewed.json', features)
    chosen = [0, 64, 66, 70] if len(data) == 71 else [0, 42, 44, 46, 48]
    for inner in (False, True):
        fig, axes = plt.subplots(2, 1, figsize=(9, 8), constrained_layout=True)
        for i in chosen:
            d = data[i]
            edges = np.r_[d['r_lo_cm'], d['r_hi_cm'][-1]]
            label = f"{features[i]['age_myr']:.2f} Myr ({features[i]['phase']})"
            axes[0].stairs(d['rho_g_cm3'], edges, label=label)
            axes[1].plot(d['r_center_cm'], d['cumulative_gas_g'], label=label)
        for ax in axes:
            ax.set_yscale('log');radius_axes(ax, inner)
            ax.yaxis.set_major_locator(LogLocator(base=10, numticks=12))
            ax.yaxis.set_major_formatter(LogFormatterSciNotation())
        axes[0].set_ylabel(r'Density (g cm$^{-3}$)');axes[0].legend(fontsize=8)
        axes[1].set_ylabel('Cumulative gas mass (g)')
        right = axes[1].secondary_yaxis('right', functions=(lambda g:g/MSUN, lambda m:m*MSUN))
        right.set_ylabel(r'Cumulative gas mass ($M_\odot$)')
        right.yaxis.set_major_locator(LogLocator(base=10, numticks=12))
        right.yaxis.set_major_formatter(LogFormatterSciNotation())
        fig.suptitle(case.name+(' | inner 2 pc' if inner else ' | full domain'))
        fig.savefig(dest/('phases_inner.png' if inner else 'phases_full.png'), dpi=150);plt.close(fig)
    d = data[-1];f = features[-1]
    for inner in (False, True):
        fig, axes = plt.subplots(3, 1, figsize=(9, 9), constrained_layout=True)
        axes[0].stairs(d['rho_g_cm3'], np.r_[d['r_lo_cm'], d['r_hi_cm'][-1]])
        axes[0].set_yscale('log');axes[0].set_ylabel(r'Density (g cm$^{-3}$)')
        axes[1].plot(d['r_center_cm'], d['v_cm_s']/1e5);axes[1].set_ylabel('Radial speed (km/s)')
        axes[2].plot(d['r_center_cm'], d['mach']);axes[2].set_yscale('symlog', linthresh=1)
        axes[2].axhline(1,color='.5',ls=':');axes[2].set_ylabel('Radial Mach number')
        for ax in axes:
            radius_axes(ax, inner)
            for key, color in [('inner_rise_candidate','#bf5c00'),('outer_shell_candidate','#197640'),('termination_flow_candidate','#8d3d9a')]:
                v = f[key]
                if v:
                    radius = v.get('r50_pc', v.get('radius_pc'))
                    ax.axvline(radius*PC, color=color, ls='--', label=key.replace('_candidate','').replace('_',' '))
        handles, labels = axes[0].get_legend_handles_labels()
        if handles: axes[0].legend(handles,labels,fontsize=8)
        fig.suptitle(case.name+' | endpoint candidate features | '+('inner' if inner else 'full domain'))
        fig.savefig(dest/('endpoint_flow_inner.png' if inner else 'endpoint_flow_full.png'),dpi=150);plt.close(fig)
    # Preserve the established 49-save sheet while including every 25-Msun save.
    columns = 7
    rows = (len(data) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(18, 15*rows/7),
                             constrained_layout=True, squeeze=False)
    for i, ax in enumerate(axes.flat):
        if i >= len(data): ax.set_visible(False);continue
        d=data[i];ax.stairs(d['rho_g_cm3'],np.r_[d['r_lo_cm'],d['r_hi_cm'][-1]],lw=.6)
        ax.set_xscale('log');ax.set_yscale('log');ax.set_xlim(.001*PC,160*PC)
        ax.set_title(f"{i:04} | {features[i]['age_myr']:.2f} Myr",fontsize=7)
        ax.tick_params(labelsize=5)
    fig.suptitle(case.name+' | all saved native density profiles | radius cm, density g/cm3')
    fig.savefig(dest/'all_save_review.png',dpi=130);plt.close(fig)
    write_json(dest/'review_provenance.json', {'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'input_profiles':len(data),'input_cells_each':1024,'endpoint_features':features[-1],
        'contact_sheet_snapshots':list(range(len(data))),
        'contact_sheet_rows':rows,'contact_sheet_columns':columns,
        'mass_definition':'Gas from r>=0.001 pc, excluding the star. Positive density-excess mass is Eulerian, not a tracer-defined swept mass.',
        'width_definition':'10--90 crossings of the local density rise and envelope half-height crossings; fractional native cell counts. No physical thickness or convergence claim.'})
    print(case.name,'review products ready',flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('host_result_root',type=Path);args=parser.parse_args()
    for case in sorted(args.host_result_root.glob('m*_n*_pk*')): review(case)
