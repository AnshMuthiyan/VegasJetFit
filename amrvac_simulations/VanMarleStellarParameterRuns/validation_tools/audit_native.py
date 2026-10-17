# Purpose: Independently inspect native AMRVAC v5 1D HD cells for finite states,
# positive recovered pressure, temperature, shell radius, and integrated quantities.
# Layout is taken from the installed mod_input_output/helper Fortran, not VTU nodes.
from pathlib import Path
import argparse
import csv
import math
import re
import struct

ROOT=Path(__file__).resolve().parent.parent
UNIT_T=7.3741968514462502e5
UNIT_RHO=1e-25
UNIT_V=1e7
UNIT_L=3.0857e18
YEAR_CODE=3.1536e7/3.0857e11


def read(path):
    data=path.read_bytes()
    version,tree,blocks,nw,ndir,ndim,levmax,nleaf,nparent,it=struct.unpack_from('<10i',data)
    if version!=5 or ndim!=1 or nw!=3 or ndir!=1:
        raise ValueError('Reader requires a native v5, 1D, three-variable HD snapshot')
    time,xmin,xmax=struct.unpack_from('<3d',data,40)
    nx,bnx=struct.unpack_from('<2i',data,64)
    staggered=struct.unpack_from('<i',data,92)[0]
    if staggered: raise ValueError('Staggered snapshots are outside this HD reader')
    param_offset=96+16*nw+16
    npar=struct.unpack_from('<i',data,param_offset)[0]
    pvalues=struct.unpack_from('<'+str(npar)+'d',data,param_offset+4)
    names_offset=param_offset+4+8*npar
    pnames=[data[names_offset+16*j:names_offset+16*(j+1)].decode().strip() for j in range(npar)]
    gamma=dict(zip(pnames,pvalues))['gamma']
    offset=tree+4*(nleaf+nparent)
    levels=struct.unpack_from('<'+str(nleaf)+'i',data,offset)
    indices=struct.unpack_from('<'+str(nleaf)+'i',data,offset+4*nleaf)
    offsets=struct.unpack_from('<'+str(nleaf)+'q',data,offset+8*nleaf)
    assert offset+16*nleaf==blocks
    par=(path.parent.parent/'run.par').read_text()
    logarithmic=bool(re.search(r"stretch_dim\(1\)\s*=\s*'uni'",par))
    specified_q=re.search(r'qstretch_baselevel\(1\)\s*=\s*([\d.eEdD+-]+)',par)
    base_q=float(specified_q.group(1).lower().replace('d','e')) if specified_q else None
    cells=[]
    for level,index,pos in zip(levels,indices,offsets):
        glo,ghi=struct.unpack_from('<2i',data,pos)
        count=bnx+glo+ghi
        values=struct.unpack_from('<'+str(count*nw)+'d',data,pos+8)
        ncells=nx*2**(level-1)
        for j in range(bnx):
            logical=(index-1)*bnx+j
            if logarithmic:
                if base_q:
                    logq=math.log(base_q)/2**(level-1)
                    left=xmin+(xmax-xmin)*math.expm1(logq*logical)/math.expm1(logq*ncells)
                    right=xmin+(xmax-xmin)*math.expm1(logq*(logical+1))/math.expm1(logq*ncells)
                else:
                    left=xmin*math.exp(math.log(xmax/xmin)*logical/ncells)
                    right=xmin*math.exp(math.log(xmax/xmin)*(logical+1)/ncells)
            else:
                left=xmin+(xmax-xmin)*logical/ncells
                right=xmin+(xmax-xmin)*(logical+1)/ncells
            rho,mom,energy=(values[glo+j+k*count] for k in range(nw))
            if not all(math.isfinite(v) for v in (rho,mom,energy)) or rho<=0:
                raise ValueError(f'{path}: nonfinite state or nonpositive density at {left:g} pc')
            thermal=energy-.5*mom*mom/rho
            pressure=(gamma-1)*thermal
            if not math.isfinite(pressure) or pressure<=0:
                raise ValueError(f'{path}: nonpositive recovered pressure at {left:g} pc: {pressure}')
            temperature=pressure/rho*UNIT_T
            cells.append((left,right,rho,mom,energy,pressure,temperature))
    cells.sort()
    return time,it,xmin,xmax,cells


def audit(path):
    # Running jobs can still supply paths through the pre-move compatibility link.
    path=Path(path).resolve()
    path=path.resolve()
    time,it,xmin,xmax,cells=read(path)
    par=(path.parent.parent/'run.par').read_text()
    if re.search(r'hd_radiative_cooling\s*=\s*\.true\.',par,re.I):
        if min(c[6] for c in cells)<100*(1-1e-8):
            raise ValueError(f'{path}: cooling-enabled state violates the 100 K Tfix floor')
    volumes=[4*math.pi/3*(cell[1]**3-cell[0]**3)*UNIT_L**3 for cell in cells]
    ambient=cells[-1][2]
    shell=[(c,v) for c,v in zip(cells,volumes) if c[2]>1.1*ambient]
    disturbed=[c for c in cells if abs(c[2]/ambient-1)>.05]
    return dict(snapshot=str(path.relative_to(ROOT)),age_yr=time/YEAR_CODE,iteration=it,
        cells=len(cells),min_pressure_code=min(c[5] for c in cells),
        min_temperature_K=min(c[6] for c in cells),max_temperature_K=max(c[6] for c in cells),
        mass_g=math.fsum(c[2]*UNIT_RHO*v for c,v in zip(cells,volumes)),
        total_energy_erg=math.fsum(c[4]*UNIT_RHO*UNIT_V**2*v for c,v in zip(cells,volumes)),
        thermal_energy_erg=math.fsum(c[5]/(5/3-1)*UNIT_RHO*UNIT_V**2*v for c,v in zip(cells,volumes)),
        shell_mass_g=math.fsum(c[2]*UNIT_RHO*v for c,v in shell),
        disturbed_radius_pc=max((c[1] for c in disturbed),default=xmin),
        shell_peak_radius_pc=sum(max(cells,key=lambda c:c[2])[:2])/2,
        outer_ambient_density_code=ambient,outer_boundary_pc=xmax)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folders',nargs='+')
    args=parser.parse_args()
    for item in args.folders:
        folder=Path(item)
        rows=[audit(path) for path in sorted((folder/'output').glob('test*.dat'))]
        if not rows: raise ValueError(f'No native snapshots in {folder}')
        with (folder/'native_audit.csv').open('w',newline='') as stream:
            stream.write('# Purpose: Native-cell finite/positivity and integrated-state audit.\n')
            writer=csv.DictWriter(stream,fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)
        print(folder.name,rows[-1])
