# Purpose: Fit a -2/5 conduction-density profile to a native snapshot and export static and interactive parameter controls.
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from plot_dat_folder import read_snapshot


def model(radius, p0, r2, r0):
    """Normalize at the observed post-shock start, so rho(r0) is exactly p0."""
    return p0 * ((r2-radius)/(r2-r0))**(-0.4)


def fit_profile(snapshot, minimum_temperature, wall_tolerance):
    cells = np.asarray(snapshot['cells'])
    radius = (cells[:,0]+cells[:,1])/2
    density,velocity,temperature = cells[:,2],cells[:,3],cells[:,5]
    if snapshot['invalid_cells']:
        raise ValueError('Fit requires finite positive cells; snapshot has invalid states')
    ambient = float(np.median(density[radius > .9*radius.max()]))
    peak = int(np.argmax(density))
    shock = np.flatnonzero((radius < radius[peak]) & (temperature > 1e5)
                           & (velocity < .5*velocity.max()))
    if not len(shock):
        raise ValueError('Cannot find the first wind-termination density jump')
    # Use the resolved plateau after the numerically broadened wind termination shock.
    settled = np.flatnonzero((np.arange(len(radius)) >= shock[0])
        & (radius < radius[peak]) & (temperature >= minimum_temperature)
        & (np.abs(velocity) < .01*velocity.max()))
    if not len(settled):
        raise ValueError('Cannot find a settled hot post-shock start')
    start = int(settled[0])
    r0,measured_p0 = float(radius[start]),float(density[start])
    exterior = np.flatnonzero((np.arange(len(radius))>=peak) & (density > (1+wall_tolerance)*ambient))
    if not len(exterior) or exterior[-1] == len(radius)-1:
        raise ValueError('Wall does not return to the ambient density inside the domain')
    wall_end = float(cells[exterior[-1],1])
    # Stop at the first cold transition, rather than fitting the radiatively cooled shell.
    end = start
    while end+1 < len(radius) and temperature[end+1] >= minimum_temperature and end+1 < peak:
        end += 1
    if end-start < 4:
        raise ValueError('Too few resolved hot-front cells')
    r,y = radius[start:end+1],density[start:end+1]
    weights = cells[start:end+1,1]-cells[start:end+1,0]
    weights = weights/weights.sum()

    def amplitude_and_loss(r2):
        shape = -.4*np.log((r2-r)/(r2-r0))
        log_p0 = float(np.sum(weights*(np.log(y)-shape)))
        residual = (log_p0+shape-np.log(y))/np.log(10)
        return math.exp(log_p0),float(np.sum(weights*residual**2))

    # Search log distance from the last fitted radius, then refine the best interval.
    lower = float(r[-1]+1e-5)
    upper = max(wall_end*2,lower+.1)
    offsets = np.geomspace(lower-r[-1],upper-r[-1],400)
    trial = r[-1]+offsets
    losses = np.array([amplitude_and_loss(value)[1] for value in trial])
    best_index = int(np.argmin(losses))
    lo = float(trial[max(0,best_index-1)])
    hi = float(trial[min(len(trial)-1,best_index+1)])
    golden = (math.sqrt(5)-1)/2
    for _ in range(100):
        a,b = hi-golden*(hi-lo),lo+golden*(hi-lo)
        if amplitude_and_loss(a)[1] < amplitude_and_loss(b)[1]:
            hi = b
        else:
            lo = a
    fitted_r2 = (lo+hi)/2
    fitted_p0,loss = amplitude_and_loss(fitted_r2)
    anchored_prediction = model(r,measured_p0,wall_end,r0)
    fixed_wall_p0,fixed_wall_loss = amplitude_and_loss(wall_end)
    report = {'purpose':'Conduction-front fit; p0 is normalized at the resolved post-shock start.',
        'age_years':snapshot['age_years'],'iteration':snapshot['iteration'],'exponent':-.4,
        'formula':'rho(r)=p0*((1-r/R2)/(1-r0/R2))^(-2/5)',
        'density_units':'g/cm^3','radius_units':'pc','r0_pc':r0,
        'fit_radius_min_pc':float(r[0]),'fit_radius_max_pc':float(r[-1]),'fit_cells':len(r),
        'minimum_fit_temperature_K':minimum_temperature,'weighting':'radial cell width; squared log10-density residual',
        'measured_p0_g_cm3':measured_p0,'measured_outer_wall_pc':wall_end,
        'wall_ambient_tolerance_fraction':wall_tolerance,'ambient_density_g_cm3':ambient,
        'measured_anchor_rmse_dex':float(np.sqrt(np.sum(weights*np.log10(anchored_prediction/y)**2))),
        'fixed_outer_wall_fit_p0_g_cm3':fixed_wall_p0,'fixed_outer_wall_fit_rmse_dex':math.sqrt(fixed_wall_loss),
        'fitted_p0_g_cm3':fitted_p0,'fitted_R2_pc':float(fitted_r2),'fit_rmse_dex':math.sqrt(loss),
        'fit_geometric_fractional_scatter':10**math.sqrt(loss)-1,
        'fitted_R2_is_outer_wall':False,
        'interpretation':'Free R2 is an effective shape radius, not the measured exterior of the cold wall. '
            'The hot-gas fit excludes the cold swept-up shell.'}
    return cells,r,y,weights,report


def make_static(cells,r,y,report,target,rmax,p0,r2):
    fig,axes = plt.subplots(2,1,figsize=(11,8),sharex=True,layout='constrained')
    try:
        edges = np.r_[cells[0,0],cells[:,1]]
        curve_r = np.linspace(report['r0_pc'],min(report['fit_radius_max_pc'],r2*(1-1e-8)),600)
        for ax in axes:
            ax.stairs(cells[:,2],edges,baseline=None,color='#343d49',linewidth=1,label='Simulation')
            ax.scatter(r,y,s=7,color='#2c8c91',alpha=.55,label='Hot cells used in fit',zorder=3)
            ax.plot(r,model(r,report['measured_p0_g_cm3'],report['measured_outer_wall_pc'],report['r0_pc']),
                    '--',color='#bd681c',label='Measured first-jump / outer-wall anchors')
            ax.plot(curve_r,model(curve_r,p0,r2,report['r0_pc']),color='#2877b8',linewidth=2,label='Adjusted model' if
                    p0!=report['fitted_p0_g_cm3'] or r2!=report['fitted_R2_pc'] else 'Best hot-front shape fit')
            ax.axvline(report['r0_pc'],color='#888888',linestyle=':',linewidth=.8)
            ax.axvline(report['measured_outer_wall_pc'],color='#bd681c',linestyle=':',linewidth=1)
            ax.axvline(r2,color='#2877b8',linestyle=':',linewidth=1)
            ax.axvspan(report['fit_radius_min_pc'],report['fit_radius_max_pc'],color='#2c8c91',alpha=.06)
            ax.set_yscale('log')
            ax.set_xlim(0,rmax)
            ax.set_ylabel(r'$\rho$ [g cm$^{-3}$]')
            ax.grid(alpha=.2)
        axes[0].set_title('Complete density profile; fit applies only to hot gas')
        axes[0].legend(fontsize=8,loc='upper left')
        axes[1].set_ylim(float(y.min()*.6),float(y.max()*2))
        axes[1].set_title('Same radius range, density zoom on the conduction region')
        axes[1].set_xlabel('Radius [pc]')
        title = ('%s conduction front | age %.6f Myr\n'
                 'p0 = %.5e g/cm³, R2 = %.6f pc; measured wall = %.6f pc' %
                 (report['snapshot_name'],report['age_years']/1e6,p0,r2,report['measured_outer_wall_pc']))
        fig.suptitle(title,fontsize=11)
        fig.savefig(target,dpi=170)
    finally:
        plt.close(fig)


def make_html(cells,r,y,weights,report,target,rmax,p0,r2):
    visible = cells[cells[:,0]<=rmax]
    payload = {'report':report,'rmax':rmax,'initial_p0':p0,'initial_R2':r2,
        'cells':visible[:,[0,1,2]].tolist(),'fit_r':r.tolist(),'fit_y':y.tolist(),'weights':weights.tolist()}
    template = r'''<!-- Purpose: Standalone interactive conduction-front density fit with editable p0 and R2. -->
<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Conduction-front fit: test0015</title>
<style>
body{font:15px system-ui,sans-serif;color:#243342;background:#f5f7fa;margin:0}main{max-width:1120px;margin:24px auto;padding:0 20px}
h1{font-size:25px;margin-bottom:6px}.muted{color:#55677c}section{background:white;border:1px solid #d9e2ec;border-radius:10px;padding:18px;margin:14px 0}
.controls{display:grid;grid-template-columns:1fr 1fr;gap:24px}label{display:block;font-weight:600;margin:6px 0}input[type=number]{padding:7px;width:180px;font:inherit;border:1px solid #aebdcd;border-radius:5px}
input[type=range]{width:100%;margin-top:14px}button{padding:9px 12px;margin:10px 6px 0 0;border:1px solid #b4c5d6;border-radius:5px;background:#edf4fa;cursor:pointer}
svg{display:block;width:100%;height:auto}#error{color:#a22}.metrics{font-variant-numeric:tabular-nums;line-height:1.8}.legend span{display:inline-block;margin-right:20px}.line{display:inline-block;width:24px;border-top:3px solid;vertical-align:middle;margin-right:6px}
@media(max-width:650px){.controls{grid-template-columns:1fr}}
</style><main><h1>Conduction-front density fit</h1><div id="subtitle" class="muted"></div>
<section><div><b>Model:</b> ρ(r) = p₀ [(1 − r/R₂)/(1 − r₀/R₂)]<sup>−2/5</sup></div>
<p class="muted">Normalization makes p₀ the density at r₀, the first resolved post-shock plateau. The fitted curve is shown over the hot-gas fitting interval; the cold shell is excluded.</p>
<div class="controls"><div><label for="p0">p₀ [g/cm³]</label><input id="p0" type="number" step="any" min="0"><input id="pSlider" aria-label="Logarithmic p0 slider" type="range" step="0.001"></div>
<div><label for="r2">R₂ [pc]</label><input id="r2" type="number" step="0.0001"><input id="rSlider" aria-label="R2 slider" type="range" step="0.0001"></div></div>
<button id="best">Reset to best shape fit</button><button id="anchors">Use measured jump / outer wall</button><button id="save">Download adjusted parameters</button><button id="savePlot">Download adjusted plot (SVG)</button>
<div id="error"></div><div id="metrics" class="metrics"></div></section>
<section><div class="legend"><span><i class="line" style="border-color:#343d49"></i>Simulation</span><span><i class="line" style="border-color:#2877b8"></i>Current model</span><span><i class="line" style="border-color:#bd681c"></i>Measured-anchor model</span></div>
<svg id="full" viewBox="0 0 1050 380" aria-label="Full density profile"></svg><svg id="zoom" viewBox="0 0 1050 380" aria-label="Density zoom on hot gas"></svg></section>
<section id="details" class="metrics"></section></main><script>
const D=__PAYLOAD__,R=D.report, NS='http://www.w3.org/2000/svg';
const p=document.getElementById('p0'),q=document.getElementById('r2'),ps=document.getElementById('pSlider'),qs=document.getElementById('rSlider');
const minimumR=R.r0_pc+1e-5; ps.min=Math.log10(R.fitted_p0_g_cm3)-1.5;ps.max=Math.log10(R.fitted_p0_g_cm3)+1.5;
q.min=minimumR;qs.min=minimumR;qs.max=Math.max(D.rmax,R.measured_outer_wall_pc*1.2);q.value=D.initial_R2;p.value=D.initial_p0;
function curve(r,a,b){return r>=R.r0_pc && r<b ? a*Math.pow((b-r)/(b-R.r0_pc),-0.4):NaN}
function svgNode(parent,name,attrs,text){let node=document.createElementNS(NS,name);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,v);if(text!==undefined)node.textContent=text;parent.appendChild(node);return node}
function render(id,low,high,a,b,title){const s=document.getElementById(id);s.replaceChildren();const left=90,right=1020,top=38,bottom=322;
const X=r=>left+(right-left)*r/D.rmax,Y=y=>bottom-(bottom-top)*(Math.log10(y)-Math.log10(low))/(Math.log10(high)-Math.log10(low));
svgNode(s,'text',{x:left,y:22,'font-size':16,'font-weight':600},title);
let defs=svgNode(s,'defs',{}),clip=svgNode(defs,'clipPath',{id:id+'clip'});svgNode(clip,'rect',{x:left,y:top,width:right-left,height:bottom-top});
for(let i=0;i<=5;i++){let val=D.rmax*i/5,x=X(val);svgNode(s,'line',{x1:x,x2:x,y1:top,y2:bottom,stroke:'#e6eaf0'});svgNode(s,'text',{x,y:343,'text-anchor':'middle','font-size':12},val.toFixed(1))}
for(let i=0;i<=4;i++){let exponent=Math.log10(low)+(Math.log10(high)-Math.log10(low))*i/4,y=Y(10**exponent);svgNode(s,'line',{x1:left,x2:right,y1:y,y2:y,stroke:'#e6eaf0'});svgNode(s,'text',{x:left-8,y:y+4,'text-anchor':'end','font-size':12},(10**exponent).toExponential(1))}
let group=svgNode(s,'g',{'clip-path':'url(#'+id+'clip)'});svgNode(group,'rect',{x:X(R.fit_radius_min_pc),y:top,width:X(R.fit_radius_max_pc)-X(R.fit_radius_min_pc),height:bottom-top,fill:'#2c8c91',opacity:.06});
let d='';for(let c of D.cells){d+=(d?'L':'M')+X(c[0])+','+Y(c[2])+'L'+X(c[1])+','+Y(c[2])}svgNode(group,'path',{d,fill:'none',stroke:'#343d49','stroke-width':1.3});
function drawModel(amp,end,color,dash){let d='';for(let i=0;i<=700;i++){let r=R.r0_pc+(R.fit_radius_max_pc-R.r0_pc)*i/700,v=curve(r,amp,end);if(!Number.isFinite(v)||v<=0)continue;d+=(d?'L':'M')+X(r)+','+Y(v)}svgNode(group,'path',{d,fill:'none',stroke:color,'stroke-width':2,'stroke-dasharray':dash})}
drawModel(R.measured_p0_g_cm3,R.measured_outer_wall_pc,'#bd681c','6 4');drawModel(a,b,'#2877b8','');
for(let [r,color] of [[R.r0_pc,'#888'],[R.measured_outer_wall_pc,'#bd681c'],[b,'#2877b8']])svgNode(group,'line',{x1:X(r),x2:X(r),y1:top,y2:bottom,stroke:color,'stroke-dasharray':'3 4'});
svgNode(s,'rect',{x:left,y:top,width:right-left,height:bottom-top,fill:'none',stroke:'#667'});svgNode(s,'text',{x:(left+right)/2,y:371,'text-anchor':'middle'},'Radius [pc]');svgNode(s,'text',{x:16,y:180,transform:'rotate(-90 16 180)','text-anchor':'middle'},'Density [g/cm³]');}
function refresh(){const a=Number(p.value),b=Number(q.value),error=document.getElementById('error');if(!(a>0&&Number.isFinite(a)&&b>minimumR&&Number.isFinite(b))){error.textContent='Enter positive p₀ and R₂ greater than r₀.';document.getElementById('save').disabled=true;document.getElementById('savePlot').disabled=true;return}
ps.min=Math.min(Number(ps.min),Math.log10(a));ps.max=Math.max(Number(ps.max),Math.log10(a));ps.value=Math.log10(a);qs.max=Math.max(Number(qs.max),b);qs.value=b;
let valid=b>R.fit_radius_max_pc;error.textContent=valid?'':'R₂ lies inside the fit interval: the model is undefined for some fitted cells.';document.getElementById('save').disabled=!valid;document.getElementById('savePlot').disabled=!valid;
let sum=0;if(valid)D.fit_r.forEach((r,i)=>{sum+=D.weights[i]*Math.log10(curve(r,a,b)/D.fit_y[i])**2});
document.getElementById('metrics').textContent=valid?'Weighted RMS log error: '+Math.sqrt(sum).toFixed(4)+' dex; geometric scatter: '+((10**Math.sqrt(sum)-1)*100).toFixed(1)+'%.  R₂ − measured outer wall: '+(b-R.measured_outer_wall_pc).toFixed(4)+' pc.':'';
let densities=D.cells.map(c=>c[2]);render('full',Math.min(...densities)*.5,Math.max(...densities)*2,a,b,'Full profile — radius capped at '+D.rmax+' pc');render('zoom',Math.min(...D.fit_y)*.6,Math.max(...D.fit_y)*2,a,b,'Density zoom — same radius range');}
for(let node of [p,q])node.addEventListener('input',refresh);ps.addEventListener('input',()=>{p.value=10**Number(ps.value);refresh()});qs.addEventListener('input',()=>{q.value=qs.value;refresh()});
document.getElementById('best').onclick=()=>{p.value=R.fitted_p0_g_cm3;q.value=R.fitted_R2_pc;refresh()};document.getElementById('anchors').onclick=()=>{p.value=R.measured_p0_g_cm3;q.value=R.measured_outer_wall_pc;refresh()};
function download(contents,type,name){let url=URL.createObjectURL(new Blob([contents],{type}));let link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
document.getElementById('save').onclick=()=>{let values={purpose:'Manually adjusted conduction-front parameters.',p0_g_cm3:Number(p.value),R2_pc:Number(q.value),r0_pc:R.r0_pc,exponent:-0.4,fit_radius_min_pc:R.fit_radius_min_pc,fit_radius_max_pc:R.fit_radius_max_pc,snapshot:R.snapshot_name};download(JSON.stringify(values,null,2),'application/json','conduction_front_parameters.json')};
document.getElementById('savePlot').onclick=()=>{let svg='<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="840" viewBox="0 0 1050 840"><style>text{font-family:Arial,sans-serif}</style><text x="90" y="22">p0 = '+Number(p.value).toExponential(6)+' g/cm³; R2 = '+Number(q.value).toFixed(6)+' pc; age = '+(R.age_years/1e6).toFixed(6)+' Myr</text><text x="90" y="44">Black: simulation. Blue: adjusted model. Orange: measured jump / outer-wall model.</text><g transform="translate(0 55)">'+document.getElementById('full').innerHTML+'</g><g transform="translate(0 445)">'+document.getElementById('zoom').innerHTML+'</g></svg>';download(svg,'image/svg+xml','conduction_front_adjusted.svg')};
document.getElementById('subtitle').textContent=R.snapshot_name+' • age '+(R.age_years/1e6).toFixed(6)+' Myr';
document.getElementById('details').textContent='Measured start r₀ = '+R.r0_pc.toFixed(6)+' pc; measured p₀ = '+R.measured_p0_g_cm3.toExponential(6)+' g/cm³. Outer wall R₂ = '+R.measured_outer_wall_pc.toFixed(6)+' pc (within '+(R.wall_ambient_tolerance_fraction*100)+'% of ambient). Fit interval '+R.fit_radius_min_pc.toFixed(4)+'–'+R.fit_radius_max_pc.toFixed(4)+' pc, T ≥ '+R.minimum_fit_temperature_K.toExponential(1)+' K. Free fitted R₂ is a shape radius; it need not equal the outer wall. A fixed exponent cannot be guaranteed to fit the entire profile exactly.';
refresh();</script></html>'''
    target.write_text(template.replace('__PAYLOAD__',json.dumps(payload,allow_nan=False)),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--par',type=Path)
    parser.add_argument('--rmax',type=float,default=5)
    parser.add_argument('--min-temperature',type=float,default=1e6)
    parser.add_argument('--wall-tolerance',type=float,default=.01)
    parser.add_argument('--p0',type=float,help='Manually set density at the post-shock start [g/cm^3]')
    parser.add_argument('--R2',type=float,help='Manually set model radius [pc]')
    args=parser.parse_args()
    if args.rmax<=0 or args.min_temperature<=0 or args.wall_tolerance<=0:
        parser.error('Radius, fit temperature, and wall tolerance must be positive')
    snapshot=read_snapshot(args.snapshot.resolve(),args.par.resolve() if args.par else None)
    cells,r,y,weights,report=fit_profile(snapshot,args.min_temperature,args.wall_tolerance)
    report['snapshot_name']=args.snapshot.name
    report['source_snapshot']=str(args.snapshot.resolve())
    p0=args.p0 if args.p0 is not None else report['fitted_p0_g_cm3']
    r2=args.R2 if args.R2 is not None else report['fitted_R2_pc']
    if not math.isfinite(p0) or p0<=0 or not math.isfinite(r2) or r2<=report['fit_radius_max_pc']:
        parser.error('p0 must be positive; R2 must be beyond the hot-gas fitting interval')
    output=args.output.resolve() if args.output else args.snapshot.resolve().parent/('fit_'+args.snapshot.stem)
    output.mkdir(parents=True,exist_ok=True)
    report.update(display_p0_g_cm3=p0,display_R2_pc=r2,plot_radius_limit_pc=args.rmax)
    (output/'fit_parameters.json').write_text(json.dumps(report,indent=2)+'\n')
    with (output/'fit_data.csv').open('w',newline='') as stream:
        stream.write('# Purpose: Hot-gas cells and best/anchored conduction-front predictions.\n')
        writer=csv.writer(stream)
        writer.writerow(['radius_pc','density_g_cm3','radial_weight','best_fit_g_cm3','measured_anchor_model_g_cm3'])
        writer.writerows(zip(r,y,weights,model(r,report['fitted_p0_g_cm3'],report['fitted_R2_pc'],report['r0_pc']),
            model(r,report['measured_p0_g_cm3'],report['measured_outer_wall_pc'],report['r0_pc'])))
    make_static(cells,r,y,report,output/'conduction_front_fit.png',args.rmax,p0,r2)
    make_html(cells,r,y,weights,report,output/'conduction_front_fit.html',args.rmax,p0,r2)
    print(json.dumps(report,indent=2))
    print('Interactive controls:',output/'conduction_front_fit.html')


if __name__=='__main__':
    main()
