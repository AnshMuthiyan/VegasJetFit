#!/usr/bin/env python3
"""Review parent figures and add explicitly local density-jump diagnostics.

Peak-based envelope widths are retained, not silently redefined. The new
local_jump_v1 definition is a separate numerical measurement, not shock width.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PARENT = next(p for p in [HERE.parent/'van_marle_full_track_grid_20261023',
    HERE.parent/'full_track_density_pressure_grid_20261023'] if p.is_dir())
spec = importlib.util.spec_from_file_location('parent_native_review', PARENT/'review_completed_diagnostics.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
plt = parent.plt
PC = parent.PC


def local_jump(d, prior):
    rho, r = d['rho_g_cm3'], d['r_center_cm']/PC
    gradient = np.diff(np.log(rho))
    valid = (r[:-1] > .002) & (r[1:] < 140)
    termination = prior['termination_flow_candidate']
    if termination:
        valid &= r[:-1] > 1.2*termination['radius_pc']
    if not np.any(valid):
        return dict(candidate=None, quality_flags=['LOCAL_JUMP_MISSING'])
    score = np.where(valid, gradient, -np.inf)
    j = int(np.argmax(score))
    if score[j] < np.log(1.5):
        return dict(candidate=None, quality_flags=['NO_STRONG_LOCAL_DENSITY_JUMP'])
    lo, hi = max(0,j-6), min(len(rho)-1,j+7)
    before = float(np.median(rho[max(lo,j-5):max(lo+1,j-2)]))
    after = float(np.median(rho[min(j+3,hi-2):hi]))
    if after/before < 3:
        return dict(candidate=None, quality_flags=['LOCAL_CONTRAST_LT3'])
    crosses, cells = [], []
    for f in [.1,.5,.9]:
        level = before+f*(after-before)
        ix = np.where((rho[lo:hi] <= level) & (rho[lo+1:hi+1] >= level))[0]+lo
        if not len(ix):
            return dict(candidate=None, quality_flags=['LOCAL_CROSSING_MISSING'])
        k = int(ix[np.argmin(abs(ix-j))])
        fraction = float((level-rho[k])/(rho[k+1]-rho[k]))
        crosses.append(float(r[k]+fraction*(r[k+1]-r[k])))
        cells.append(k+fraction)
    if not crosses[0] <= crosses[1] <= crosses[2]:
        return dict(candidate=None, quality_flags=['NONMONOTONIC_LOCAL_CROSSINGS'])
    flags = []
    if cells[2]-cells[0] < 5: flags.append('UNRESOLVED_LT5_NATIVE_CELLS')
    if lo < 3: flags.append('INJECTION_ADJACENT')
    if r[hi] >= 140: flags.append('OUTER_BOUNDARY_REGION')
    candidate = dict(r10_pc=crosses[0],r50_pc=crosses[1],r90_pc=crosses[2],
        width_10_90_pc=crosses[2]-crosses[0],cells_10_90=cells[2]-cells[0],
        contrast=after/before,upstream_density_g_cm3=before,downstream_density_g_cm3=after,
        maximum_log_jump_cell=j,window_cell_indices=[lo,hi],flags=flags)
    return dict(candidate=candidate,quality_flags=flags)


def review(case):
    parent.review(case)
    prior = json.loads((case/'reviewed_diagnostics/feature_diagnostics_reviewed.json').read_text())
    data = [np.genfromtxt(p,delimiter=',',names=True) for p in sorted((case/'native_profiles').glob('*.csv'))]
    reviewed = []
    for i,(d,p) in enumerate(zip(data,prior)):
        result = local_jump(d,p)
        legacy = p['inner_rise_candidate']
        if legacy and legacy['width_10_90_pc'] > .1*legacy['r50_pc']:
            result['quality_flags'].append('LEGACY_10_90_WIDTH_SPANS_BROAD_ENVELOPE')
        reviewed.append(dict(snapshot=i,age_myr=p['age_myr'],phase=p['phase'],
            method='local_jump_v1',fit_eligible=False,**result))
    record = dict(definition='Strongest adjacent positive log-density jump beyond 1.2 times the separately flow-selected termination candidate (when present), outside0.002pc and inside140pc; upstream state is a three-cell median and downstream state a four-cell median within a fixed native window (six cells before/seven after).10/50/90 linear-density crossings nearest the maximum gradient, interpolated only between adjacent native centers. Fractional native cell counts; no regridding or physical-thickness/convergence claim.',
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        retained_legacy_definition='Original first-prominent-peak baseline-to-peak crossings remain in feature_diagnostics_initial/reviewed files; broad envelope widths are explicitly flagged and are not interchangeable with local_jump_v1.',
        snapshots=reviewed)
    parent.write_json(case/'reviewed_diagnostics/local_jump_diagnostics.json',record)
    d = data[-1];f = reviewed[-1];c = f['candidate']
    if c:
        j=c['maximum_log_jump_cell'];lo=max(0,j-10);hi=min(len(d)-1,j+11)
        fig,ax=plt.subplots(figsize=(9,5),constrained_layout=True)
        edges=np.r_[d['r_lo_cm'],d['r_hi_cm'][-1]]
        ax.stairs(d['rho_g_cm3'],edges,label='Native cells')
        ax.plot(d['r_center_cm'],d['rho_g_cm3'],'o',ms=3,color='.25',label='Native centers')
        ax.set_xlim(d['r_lo_cm'][lo],d['r_hi_cm'][hi]);ax.set_yscale('log')
        for key,color in [('r10_pc','#197640'),('r50_pc','#bf5c00'),('r90_pc','#8d3d9a')]:
            ax.axvline(c[key]*PC,ls='--',color=color,label=key.replace('_pc',''))
        ax.set_xlabel('Radius (cm)');ax.set_ylabel(r'Density (g cm$^{-3}$)')
        top=ax.secondary_xaxis('top',functions=(lambda cm:cm/PC,lambda pc:pc*PC));top.set_xlabel('Radius (pc)')
        ax.legend(fontsize=8);ax.grid(alpha=.2)
        fig.suptitle(f"{case.name} | local jump | {c['cells_10_90']:.2f} native cells; numerical width",fontsize=10)
        fig.savefig(case/'reviewed_diagnostics/endpoint_local_jump.png',dpi=160);plt.close(fig)
    print(case.name,'local jump review ready',flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('host_result_root',type=Path);args=parser.parse_args()
    for case in sorted(args.host_result_root.glob('m*_n*_pk*')):review(case)
