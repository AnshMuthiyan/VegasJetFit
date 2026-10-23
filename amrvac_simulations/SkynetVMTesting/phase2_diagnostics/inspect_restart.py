# Purpose: Validate native 1D-HD AMRVAC v5 restart structure and active-cell conserved states before resuming a production simulation.
import argparse
import math
from pathlib import Path
import struct
import sys


def inspect(path):
    data=path.read_bytes()
    if len(data)<164:
        raise ValueError('truncated native checkpoint header')
    version,tree,blocks,nw,ndir,ndim,max_level,leaves,parents,iteration=struct.unpack_from('<10i',data)
    if (version,nw,ndir,ndim)!=(5,3,1,1):
        raise ValueError('requires native v5 1D HD with three conserved variables')
    time_code,xmin,xmax=struct.unpack_from('<3d',data,40)
    nx,block_nx=struct.unpack_from('<2i',data,64)
    names=[data[96+16*j:112+16*j].decode().strip() for j in range(nw)]
    if names!=['rho','m1','e']:
        raise ValueError('unexpected variable order: '+repr(names))
    if not all(math.isfinite(v) for v in (time_code,xmin,xmax)) or time_code<0 or not xmin<xmax:
        raise ValueError('invalid time/domain header')
    if min(nx,block_nx,max_level,leaves)<1 or parents<0 or iteration<0 or nx%block_nx:
        raise ValueError('invalid mesh/iteration header')
    parameter_offset=96+16*nw+16
    count=struct.unpack_from('<i',data,parameter_offset)[0]
    if not 1<=count<=1000:
        raise ValueError('invalid physics parameter count')
    values=struct.unpack_from('<'+str(count)+'d',data,parameter_offset+4)
    name_offset=parameter_offset+4+8*count
    pnames=[data[name_offset+16*j:name_offset+16*(j+1)].decode().strip() for j in range(count)]
    gamma=dict(zip(pnames,values))['gamma']
    if not math.isfinite(gamma) or gamma<=1:
        raise ValueError('invalid gamma')
    table=tree+4*(leaves+parents)
    if tree<name_offset+16*count or table+16*leaves!=blocks or blocks>len(data):
        raise ValueError('invalid/truncated mesh table')
    levels=struct.unpack_from('<'+str(leaves)+'i',data,table)
    offsets=struct.unpack_from('<'+str(leaves)+'q',data,table+8*leaves)
    cells=0
    min_pressure=float('inf')
    ranges=[]
    for level,offset in zip(levels,offsets):
        if not 1<=level<=max_level or offset<blocks:
            raise ValueError('invalid leaf metadata')
        low,high=struct.unpack_from('<2i',data,offset)
        if not 0<=low<=100 or not 0<=high<=100:
            raise ValueError('invalid ghost-cell counts')
        size=block_nx+low+high
        state=struct.unpack_from('<'+str(size*nw)+'d',data,offset+8)
        ranges.append((offset,offset+8+8*size*nw))
        for i in range(low,low+block_nx):
            rho,momentum,energy=state[i],state[size+i],state[2*size+i]
            if not all(math.isfinite(v) for v in (rho,momentum,energy)) or rho<=0:
                raise ValueError('nonfinite conserved state or nonpositive density')
            pressure=(gamma-1)*(energy-0.5*momentum**2/rho)
            if not math.isfinite(pressure) or pressure<=0:
                raise ValueError('nonfinite or nonpositive active-cell thermal pressure')
            min_pressure=min(min_pressure,pressure)
            cells+=1
    ranges.sort()
    if any(b[0]<a[1] for a,b in zip(ranges,ranges[1:])):
        raise ValueError('overlapping leaf blocks')
    print('VALID:',path)
    print('Code time:',format(time_code,'.17g'))
    print('Stellar age [yr]:',format(time_code*3.0857e11/3.1536e7,'.12g'))
    print('Iteration:',iteration)
    print('Domain [pc]:',xmin,xmax,'base cells:',nx,'cells/block:',block_nx,'max saved AMR level:',max_level)
    print('Active cells checked:',cells,'minimum pressure [code units]:',min_pressure)
    print('This checks saved states, not stability of subsequent evolution.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint',type=Path)
    args=parser.parse_args()
    try:
        inspect(args.checkpoint)
    except (OSError,ValueError,KeyError,OverflowError,struct.error,UnicodeError) as exc:
        print('INVALID OR UNSUPPORTED CHECKPOINT:',exc,file=sys.stderr)
        raise SystemExit(1)
