# Purpose: Plot native AMRVAC snapshots and overlay their radial density profiles by simulation age.
"""Standalone plotting for this campaign's native v5, 1D HD checkpoints (AMRVAC 3.1/3.2)."""
import argparse
import csv
import math
from pathlib import Path
import re
import struct
import sys

# Physical normalization used in the supplied mod_usr.t; no automatic rescaling.
UNIT_DENSITY = 1e-25                    # g/cm^3
UNIT_VELOCITY = 1e7                    # cm/s
UNIT_PRESSURE = UNIT_DENSITY * UNIT_VELOCITY**2
UNIT_TEMPERATURE = 7.3741968514462502e5 # K
UNIT_LENGTH = 3.0857e18                # cm, one campaign parsec
YEAR_SECONDS = 3.1536e7
UNIT_TIME = UNIT_LENGTH / UNIT_VELOCITY


class UnsupportedSnapshot(ValueError):
    pass


def scalar(text, name, default=None):
    match = re.search(r'(?mi)^\s*' + re.escape(name) + r'\s*=\s*([^!\n]+)', text)
    return match.group(1).strip().strip("'\"") if match else default


def number(text):
    return float(text.lower().replace('d', 'e'))


def grid_settings(path, override):
    if override:
        par = override
    else:
        par = next((folder/name for folder in list(path.parents)[:4]
                    for name in ('run.par','amrvac.par') if (folder/name).is_file()), None)
    if par is None:
        return 'uni', 1.03, None, 'assumed campaign q=1.03; run.par not found'
    text = par.read_text()
    mode = scalar(text, 'stretch_dim(1)', 'none').lower()
    if mode not in ('uni', 'none'):
        raise ValueError('Unsupported grid stretching: ' + mode)
    q = scalar(text, 'qstretch_baselevel(1)')
    return mode, number(q) if q else None, text, str(par)


def read_snapshot(path, par_override=None):
    data = path.read_bytes()
    if len(data) < 4 or struct.unpack_from('<i', data)[0] != 5:
        raise UnsupportedSnapshot('not a native AMRVAC v5 snapshot')
    if len(data) < 100:
        raise ValueError('truncated native checkpoint header')
    version, tree, blocks, nw, ndir, ndim, level_max, leaves, parents, iteration = struct.unpack_from('<10i', data)
    if (nw, ndir, ndim) != (3, 1, 1):
        raise UnsupportedSnapshot('requires 1D HD with density, one momentum, and total energy')
    if len(data) < 96 + 16*nw + 16 + 4:
        raise ValueError('truncated native checkpoint variable/physics header')
    time_code, xmin, xmax = struct.unpack_from('<3d', data, 40)
    nx, block_nx = struct.unpack_from('<2i', data, 64)
    if struct.unpack_from('<i', data, 92)[0]:
        raise UnsupportedSnapshot('staggered snapshots are not supported')
    names = [data[96+16*j:96+16*(j+1)].decode().strip() for j in range(nw)]
    if names != ['rho', 'm1', 'e']:
        raise UnsupportedSnapshot('unexpected conserved-variable order: ' + repr(names))
    if not all(math.isfinite(v) for v in (time_code,xmin,xmax)) or not xmin < xmax:
        raise ValueError('invalid snapshot time or domain')
    if min(nx,block_nx,leaves,level_max) < 1 or parents < 0 or nx % block_nx:
        raise ValueError('invalid mesh dimensions')
    parameter_offset = 96 + 16*nw + 16
    count = struct.unpack_from('<i', data, parameter_offset)[0]
    if not 1 <= count <= 1000:
        raise ValueError('invalid physics-parameter count')
    values = struct.unpack_from('<'+str(count)+'d',data,parameter_offset+4)
    name_offset = parameter_offset + 4 + 8*count
    pnames = [data[name_offset+16*j:name_offset+16*(j+1)].decode().strip() for j in range(count)]
    gamma = dict(zip(pnames,values))['gamma']
    if not math.isfinite(gamma) or gamma <= 1:
        raise ValueError('invalid adiabatic index')
    table = tree + 4*(leaves+parents)
    if table + 16*leaves != blocks:
        raise ValueError('invalid mesh table offset')
    levels = struct.unpack_from('<'+str(leaves)+'i',data,table)
    indices = struct.unpack_from('<'+str(leaves)+'i',data,table+4*leaves)
    offsets = struct.unpack_from('<'+str(leaves)+'q',data,table+8*leaves)
    mode, q, par_text, grid_note = grid_settings(path,par_override)
    if q is not None and (not math.isfinite(q) or q <= 0):
        raise ValueError('invalid grid width ratio')
    if mode == 'uni' and q is None and xmin <= 0:
        raise ValueError('pure logarithmic grid requires a positive inner radius')
    if par_text:
        for name, expected in [('xprobmin1',xmin),('xprobmax1',xmax),('domain_nx1',nx),('block_nx1',block_nx)]:
            actual = scalar(par_text,name)
            if actual is not None and not math.isclose(number(actual),expected,rel_tol=1e-10,abs_tol=1e-12):
                raise ValueError('parameter file does not match checkpoint: ' + name)
    cells = []
    invalid = 0
    for level,index,offset in zip(levels,indices,offsets):
        if not 1 <= level <= level_max or index < 1 or offset < blocks:
            raise ValueError('invalid AMR block metadata')
        low,high = struct.unpack_from('<2i',data,offset)
        if min(low,high) < 0 or max(low,high) > 100:
            raise ValueError('invalid ghost-cell counts')
        size = block_nx + low + high
        state = struct.unpack_from('<'+str(size*nw)+'d',data,offset+8)
        ncells = nx * 2**(level-1)

        def face(i):
            if mode == 'none' or q == 1:
                return xmin+(xmax-xmin)*i/ncells
            if q is None:
                return xmin*math.exp(math.log(xmax/xmin)*i/ncells)
            logq = math.log(q)/2**(level-1)
            return xmin+(xmax-xmin)*math.expm1(logq*i)/math.expm1(logq*ncells)

        for j in range(block_nx):
            i = (index-1)*block_nx+j
            if not 0 <= i < ncells:
                raise ValueError('AMR block extends beyond the domain')
            left,right = face(i),face(i+1)
            rho,mom,energy = (state[low+j+k*size] for k in range(nw))
            valid = all(math.isfinite(v) for v in (rho,mom,energy)) and rho > 0
            pressure = (gamma-1)*(energy-0.5*mom*mom/rho) if valid else math.nan
            valid = valid and math.isfinite(pressure) and pressure > 0
            invalid += not valid
            # Keep bad cells as gaps, never replace them with an invented floor.
            density = rho*UNIT_DENSITY if math.isfinite(rho) and rho > 0 else math.nan
            velocity = mom/rho*UNIT_VELOCITY/1e5 if math.isfinite(mom) and math.isfinite(rho) and rho > 0 else math.nan
            p = pressure*UNIT_PRESSURE if valid else math.nan
            temperature = pressure/rho*UNIT_TEMPERATURE if valid else math.nan
            cells.append((left,right,density,velocity,p,temperature))
    cells.sort(key=lambda c:c[0])
    previous = xmin
    for cell in cells:
        if cell[1] <= cell[0] or not math.isclose(cell[0],previous,rel_tol=1e-10,abs_tol=1e-12):
            raise ValueError('grid has a gap/overlap; check the supplied stretching parameters')
        previous = cell[1]
    if not math.isclose(previous,xmax,rel_tol=1e-10,abs_tol=1e-12):
        raise ValueError('AMR cells do not cover the domain')
    return {'age_years':time_code*UNIT_TIME/YEAR_SECONDS,'iteration':iteration,
            'cells':cells,'invalid_cells':invalid,'grid':grid_note}


def plot_snapshot(snapshot, path, target, args, plt):
    cells = snapshot['cells']
    edges = [cells[0][0]]+[cell[1] for cell in cells]
    fields = [('Density',r'$\rho$ [g cm$^{-3}$]',2,True),
              ('Radial velocity',r'$v_r$ [km s$^{-1}$]',3,False),
              ('Thermal pressure',r'$p$ [erg cm$^{-3}$]',4,True),
              ('Temperature',r'$T$ [K]',5,True)]
    fig,axes = plt.subplots(2,2,figsize=(11,7),sharex=True,layout='constrained')
    try:
        for ax,(title,label,index,logarithmic) in zip(axes.flat,fields):
            values = [cell[index] for cell in cells]
            ax.stairs(values,edges,baseline=None,linewidth=1.15,color='#24668e')
            if logarithmic and any(math.isfinite(v) and v > 0 for v in values):
                ax.set_yscale('log')
            elif not any(math.isfinite(v) for v in values):
                ax.text(.5,.5,'No valid cell values',ha='center',transform=ax.transAxes)
            ax.set_xscale('log')
            if not args.log_radius:
                if edges[0] <= 0:
                    raise ValueError('linear radius requires a positive inner boundary')
                ax.set_xscale('linear')
            if args.rmin is not None or args.rmax is not None:
                ax.set_xlim(left=args.rmin if args.rmin is not None else (edges[0] if not args.log_radius else 0),
                            right=args.rmax)
            ax.set_title(title)
            ax.set_ylabel(label)
            ax.grid(True,which='major',alpha=.25)
        for ax in axes[-1]:
            ax.set_xlabel('Radius [pc]')
        title = ('%s | age = %.6f Myr | iteration %s' %
                 (path.name,snapshot['age_years']/1e6,format(snapshot['iteration'],',')))
        # A parameter file is needed to recover the stretched grid from the native data.
        if snapshot['grid'].startswith('assumed'):
            title += '\nGrid assumed: campaign q=1.03 (no run.par found)'
        if snapshot['invalid_cells']:
            title += '\nWARNING: %d invalid cells; gaps shown' % snapshot['invalid_cells']
        fig.suptitle(title,fontsize=11)
        target.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(target,dpi=args.dpi)
    finally:
        plt.close(fig)


def plot_density_overlay(entries, target, args, plt):
    """Superimpose profiles at their physical density, without vertical offsets."""
    import matplotlib.colors as colors
    from matplotlib.cm import ScalarMappable

    entries = sorted(entries,key=lambda item:(item[1]['age_years'],str(item[0])))
    ages = [info['age_years']/1e6 for _,info in entries]
    multiple_ages = min(ages) != max(ages)
    norm = colors.Normalize(vmin=min(ages),vmax=max(ages)) if multiple_ages else None
    cmap = plt.get_cmap('viridis')
    fig,ax = plt.subplots(figsize=(10,6),layout='constrained')
    try:
        any_positive = False
        for (path,info),age in zip(entries,ages):
            cells = info['cells']
            edges = [cells[0][0]]+[cell[1] for cell in cells]
            density = [cell[2] for cell in cells]
            any_positive = any_positive or any(math.isfinite(v) and v>0 for v in density)
            if not args.log_radius and edges[0] <= 0:
                raise ValueError('linear radius requires a positive inner boundary')
            ax.stairs(density,edges,baseline=None,linewidth=1.2,alpha=.8,
                      color=cmap(norm(age)) if multiple_ages else '#24668e',
                      label='%s: %.6f Myr' % (path.stem,age))
        if any_positive:
            ax.set_yscale('log')
        else:
            ax.text(.5,.5,'No valid positive density values',ha='center',transform=ax.transAxes)
        ax.set_xscale('log')
        #if not args.log_radius:
        #    ax.set_xscale('linear')
        if args.rmin is not None or args.rmax is not None:
            ax.set_xlim(left=args.rmin if args.rmin is not None else (min(info['cells'][0][0] for _,info in entries)
                            if not args.log_radius else 0),right=args.rmax)
        ax.set_xlabel('Radius [pc]')
        ax.set_ylabel(r'$\rho$ [g cm$^{-3}$]')
        ax.grid(True,which='major',alpha=.25)
        title = 'Density evolution | %d snapshots' % len(entries)
        if any(info['grid'].startswith('assumed') for _,info in entries):
            title += '\nGrid assumed: campaign q=1.03 for snapshots without run.par'
        invalid = sum(info['invalid_cells'] for _,info in entries)
        if invalid:
            title += '\nWARNING: %d invalid cells across snapshots' % invalid
        ax.set_title(title)
        if len(entries) <= 10:
            ax.legend(fontsize=8,loc='best')
        if multiple_ages:
            fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,label='Stellar age [Myr]')
        target.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(target,dpi=args.dpi)
    finally:
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path,help='Folder containing native .dat snapshots')
    parser.add_argument('--output',type=Path,help='Output directory; default: INPUT/plots')
    parser.add_argument('--recursive',action='store_true',help='Include all subfolders; retain their structure')
    parser.add_argument('--par',type=Path,help='Use this run.par instead of discovering one near each snapshot')
    parser.add_argument('--format',choices=['png','pdf'],default='png')
    parser.add_argument('--dpi',type=int,default=160)
    parser.add_argument('--log-radius',action='store_true')
    parser.add_argument('--rmin',type=float)
    parser.add_argument('--rmax',type=float,help='Outer plot radius in pc; omitted by default to show the full radial range')
    parser.add_argument('--density-only',action='store_true',help='Only create the combined density plot(s)')
    args = parser.parse_args()
    root = args.folder.expanduser().resolve()
    if not root.is_dir(): parser.error('Input folder does not exist: '+str(root))
    if args.par:
        args.par = args.par.expanduser().resolve()
        if not args.par.is_file(): parser.error('--par file does not exist')
    if args.dpi < 1: parser.error('--dpi must be positive')
    if args.rmin is not None and args.rmax is not None and args.rmin >= args.rmax:
        parser.error('--rmin must be smaller than --rmax')
    output = args.output.expanduser().resolve() if args.output else root/'plots'
    files = sorted(root.rglob('*.dat') if args.recursive else root.glob('*.dat'))
    if not files: parser.error('No .dat files found; use --recursive to include subfolders')
    try:
        import matplotlib
        matplotlib.use('Agg')  # Works over SSH without a display.
        import matplotlib.pyplot as plt
    except ImportError:
        parser.exit(1,'Install the plotting dependency first: python3 -m pip install --user matplotlib\n')
    output.mkdir(parents=True,exist_ok=True)
    rows = []
    density_groups = {}
    columns = ['snapshot','status','age_years','iteration','cells','invalid_cells','grid','plot','density_plot','error']
    for i,path in enumerate(files,1):
        relative = path.relative_to(root)
        target = output/relative.with_suffix('.'+args.format)
        row = {'snapshot':str(relative)}
        try:
            info = read_snapshot(path,args.par)
            if not args.density_only:
                plot_snapshot(info,path,target,args,plt)
            # Keep different cases/output folders separate when scanning recursively.
            density_groups.setdefault(relative.parent,[]).append((path,info))
            row.update(status='WARNING' if info['invalid_cells'] else 'OK',age_years=info['age_years'],
                iteration=info['iteration'],cells=len(info['cells']),invalid_cells=info['invalid_cells'],
                grid=info['grid'],plot='' if args.density_only else str(target))
            print('[%d/%d] %s: %s' % (i,len(files),row['status'],relative if args.density_only else target),flush=True)
        except UnsupportedSnapshot as exc:
            row.update(status='SKIPPED',error=str(exc))
            print('[%d/%d] SKIPPED %s: %s' % (i,len(files),relative,exc),flush=True)
        except (ValueError,OSError,KeyError,struct.error,OverflowError) as exc:
            row.update(status='ERROR',error=str(exc))
            print('[%d/%d] ERROR %s: %s' % (i,len(files),relative,exc),file=sys.stderr,flush=True)
        rows.append(row)
        # Preserve a report even if a later file is interrupted or still being written.
        with (output/'plot_summary.csv').open('w',newline='') as stream:
            stream.write('# Purpose: Plot results and invalid/skipped snapshot diagnostics.\n')
            writer = csv.DictWriter(stream,fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    overlay_failed = False
    overlay_count = 0
    for relative_folder,entries in density_groups.items():
        target = output/relative_folder/('density_overlay.'+args.format)
        try:
            plot_density_overlay(entries,target,args,plt)
            overlay_count += 1
            for row in rows:
                if row['status'] in ('OK','WARNING') and Path(row['snapshot']).parent == relative_folder:
                    row['density_plot'] = str(target)
            print('DENSITY OVERLAY: %s (%d snapshots)' % (target,len(entries)),flush=True)
        except (ValueError,OSError,OverflowError) as exc:
            overlay_failed = True
            print('ERROR creating density overlay %s: %s' % (target,exc),file=sys.stderr,flush=True)
    with (output/'plot_summary.csv').open('w',newline='') as stream:
        stream.write('# Purpose: Plot results and invalid/skipped snapshot diagnostics.\n')
        writer = csv.DictWriter(stream,fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    plotted = sum(row['status'] in ('OK','WARNING') for row in rows)
    print('Plotted %d snapshots; %d density overlay(s) in %s; report: plot_summary.csv' %
          (plotted,overlay_count,output),flush=True)
    return 1 if not plotted or overlay_failed or any(row['status'] in ('ERROR','WARNING') for row in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
