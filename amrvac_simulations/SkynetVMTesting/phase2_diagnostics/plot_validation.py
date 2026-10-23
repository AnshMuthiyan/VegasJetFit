# Purpose: Plot physical profiles from valid phase-transition snapshots of the corrected model, restricted to the requested 5-pc radius.
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from plot_dat_folder import read_snapshot

early=HERE/'20261020_103817_audited_rsg_full/both/output'
late=HERE/'20261020_103525_audited_full_wr/both/output'
early_files=[(p,read_snapshot(p)) for p in sorted(early.glob('*.dat'))]
late_files=[(p,read_snapshot(p)) for p in sorted(late.glob('*.dat'))]
chosen=[min(early_files,key=lambda item:item[1]['age_years']),
        min(early_files,key=lambda item:abs(item[1]['age_years']-4.5e6)),
        max(early_files,key=lambda item:item[1]['age_years']),
        max(late_files,key=lambda item:item[1]['age_years'])]
fields=[(2,r'Density [g cm$^{-3}$]',True),(3,'Radial velocity [km/s]',False),
        (4,r'Thermal pressure [erg cm$^{-3}$]',True),(5,'Temperature [K]',True)]
fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,layout='constrained')
colors=['#62666b','#d38713','#9750b4','#1678ad']
for (path,snapshot),color in zip(chosen,colors):
    if snapshot['invalid_cells']:
        raise RuntimeError('Refusing to plot an invalid state as a validation result: '+str(path))
    cells=snapshot['cells']
    edges=[cells[0][0]]+[c[1] for c in cells]
    label=f"{snapshot['age_years']/1e6:.4f} Myr"
    for ax,(index,ylabel,logarithmic) in zip(axes.flat,fields):
        ax.stairs([c[index] for c in cells],edges,baseline=None,label=label,color=color,linewidth=1.15)
        ax.set(xlim=(0,5),ylabel=ylabel)
        if logarithmic:
            ax.set_yscale('log')
        ax.grid(alpha=.18,which='both')
for ax in axes[-1,:]:
    ax.set_xlabel('Radius [pc]')
axes[0,0].legend(title='Stellar clock',fontsize=8)
fig.suptitle('Corrected wind injection and conservative AMR: conduction + cooling + Tfix\n'
             'Saved ~1.02-Myr gas state starts with stellar clock reset to 4.3 Myr',fontsize=11)
fig.savefig(HERE/'validation_profiles.png',dpi=180,
            metadata={'Description':'Purpose: physical profile validation of the corrected phase-2 model; radius limited to 5 pc.'})
plt.close(fig)
print(HERE/'validation_profiles.png')
