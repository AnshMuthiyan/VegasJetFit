# Purpose: Plot only the completed tracks' final native density snapshots and select endpoint anchors for the latest three-input density fit.
"""Run without arguments to make an atlas and an offline interactive anchor/fit viewer.

Click a profile in final_density_profiles.html to select R and rho(R), edit the
values as needed, then preview the one-parameter fit. Download the anchors and
pass --anchors PATH to reproduce those fits in Python. All generated analysis
files share this existing directory; the archives are read without extraction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import tarfile

sys.dont_write_bytecode = True

import numpy as np
from scipy.optimize import minimize_scalar

HERE = Path(__file__).resolve().parent
SIMULATIONS = HERE.parents[1]
sys.path.insert(0, str(SIMULATIONS / "SkynetVMTesting"))
from plot_dat_folder import read_snapshot

MODEL_PATH = SIMULATIONS / "Ansh_40_solar_mass_runs/tc_on_rc_on/fit_test0098_density_simple.py"
spec = importlib.util.spec_from_file_location("latest_density_model", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class BufferedSnapshot:
    """Give the established checkpoint reader archive bytes without disk copies."""
    def __init__(self, raw):
        self.raw = raw

    def read_bytes(self):
        return self.raw


def load_profiles():
    with (HERE / "CASE_INDEX.csv").open(newline="") as stream:
        cases = list(csv.DictReader(stream))
    profiles = []
    for number, case in enumerate(cases, 1):
        archive = (HERE.parent / case["archive"]).resolve()
        archive.relative_to(HERE)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != case["archive_sha256"]:
            raise ValueError(f"Archive checksum mismatch: {case['case']}")
        with tarfile.open(archive) as source:
            snapshots = [m for m in source.getmembers() if m.isfile() and m.name.endswith(".dat")]
            if len(snapshots) != int(case["saved_dat"]):
                raise ValueError(f"Unexpected snapshot count: {case['case']}")
            # Select by saved physical time, rather than filesystem date or name alone.
            saved = [(source.extractfile(member).read(), member.name) for member in snapshots]
            raw, snapshot = max(saved, key=lambda item: struct.unpack_from("<d", item[0], 40)[0])
        time_code, xmin, xmax = struct.unpack_from("<3d", raw, 40)
        nx = struct.unpack_from("<i", raw, 64)[0]
        if xmax == 80:
            base = "cloud_mass_base_2048_80pc.par"
        elif xmin == 0.01:
            base = f"evolving_base_inner0p01_{nx}.par"
        else:
            base = "evolving_base" + ("" if nx == 256 else f"_{nx}") + ".par"
        info = read_snapshot(BufferedSnapshot(raw), HERE / "reference_sources" / base)
        # This bundle uses a 365-day stellar year, unlike some legacy plot readers.
        age = time_code * (3.085677581e18 / 1e7) / 31536000 / 1e6
        if info["invalid_cells"] or not math.isclose(age, 4.77, abs_tol=1e-7):
            raise ValueError(f"Invalid or incomplete endpoint: {case['case']}")
        cells = np.asarray(info["cells"])
        radius = (cells[:, 0] + cells[:, 1]) / 2
        # Default fit window starts after the inner fast-wind drop. It is editable
        # in the viewer and is an interval choice, not a fitted shape coefficient.
        inner_speed = np.median(cells[:min(8, len(cells)), 3])
        postwind = np.flatnonzero(cells[:, 3] < 0.3 * inner_speed)
        start = int(postwind[0]) if len(postwind) else 0
        gravity = "no gravity" if case["gravity"] == "none" else "gravity"
        convention = "n_ref" if "n_ref" in case["density_convention"] else "n0"
        title = f"{number:02d} | {convention}={int(case['n_input_cm3']):,} | {gravity} | {nx} cells"
        profile = dict(number=number, case=case["case"], title=title, age_myr=age,
                       snapshot=snapshot, archive=str(archive.relative_to(HERE)),
                       xmin=xmin, xmax=xmax, r=radius.tolist(), rho=cells[:, 2].tolist(),
                       left=cells[:, 0].tolist(), right=cells[:, 1].tolist(),
                       rmin=float(radius[start]), inner_pc=xmin,
                       note="Shell underresolved (~4 native cells)" if xmax == 80 else "Cooling off; conduction off")
        profiles.append(profile)
        print(f"{number:02d}: {case['case']} | {Path(snapshot).name} | {age:.8f} Myr | {len(cells)} valid cells")
    return profiles


def fit_profile(profile, R, rhoR, rmin):
    r, rho = np.asarray(profile["r"]), np.asarray(profile["rho"])
    if not (np.isfinite([R, rhoR, rmin]).all() and r[0] <= rmin < R <= r[-1] and rhoR > 0):
        raise ValueError(f"Invalid endpoint or fit interval for {profile['case']}")
    selected = (r >= rmin) & (r <= R)
    r, rho = r[selected], rho[selected]
    widths = (np.minimum(np.asarray(profile["right"])[selected], R)
              - np.maximum(np.asarray(profile["left"])[selected], rmin))
    if len(r) < 5 or np.any(widths <= 0):
        raise ValueError("Choose an interval containing at least five cells")
    weights = widths / widths.sum()

    def loss(a):
        predicted = model.density_profile(r, R, rhoR, rhoR * np.exp(-a), "flat")
        return np.sum(weights * np.log(predicted / rho)**2)

    # A grid brackets the global best basin before a scalar refinement.
    grid = np.linspace(0.01, 30, 301)
    best = int(np.argmin([loss(a) for a in grid]))
    result = minimize_scalar(loss, bounds=(grid[max(0, best-1)], grid[min(300, best+1)]),
                             method="bounded", options={"xatol": 1e-12})
    if not result.success:
        raise ValueError("Single-parameter fit failed")
    return dict(case=profile["case"], R_pc=R, rho_R_g_cm3=rhoR, rmin_pc=rmin,
                rho_min_g_cm3=float(rhoR*np.exp(-result.x)),
                rms_log10_dex=float(np.sqrt(result.fun)/np.log(10)),
                fitted_cells=int(len(r)))


def load_anchors(path, profiles):
    results = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = csv.DictReader(line for line in stream if not line.startswith("#"))
        lookup = {p["case"]: p for p in profiles}
        for row in rows:
            if not row.get("R_pc") or not row.get("rho_R_g_cm3"):
                continue
            p = lookup[row["case"]]
            if p["case"] in results:
                raise ValueError(f"Duplicate anchor: {p['case']}")
            results[p["case"]] = fit_profile(p, float(row["R_pc"]), float(row["rho_R_g_cm3"]),
                                               float(row.get("rmin_pc") or p["rmin"]))
    return results


def plot_atlas(profiles, fits, rmax=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator, NullFormatter

    for page, first in enumerate(range(0, len(profiles), 9), 1):
        fig, axes = plt.subplots(3, 3, figsize=(16, 13), layout="constrained")
        for ax, p in zip(axes.flat, profiles[first:first+9]):
            edges = p["left"] + [p["right"][-1]]
            color = "#b35320" if "nogravity" in p["case"] else "#22638e"
            ax.stairs(p["rho"], edges, baseline=None, color=color, linewidth=1.4)
            fit = fits.get(p["case"])
            if fit:
                x = np.geomspace(max(p["xmin"], fit["rmin_pc"]), fit["R_pc"], 1000)
                ax.plot(x, model.density_profile(x, fit["R_pc"], fit["rho_R_g_cm3"],
                                                 fit["rho_min_g_cm3"]), "--", color="#bd2970", lw=1.5)
                ax.plot(fit["R_pc"], fit["rho_R_g_cm3"], "o", color="#bd2970", ms=4)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlim(p["xmin"], p["xmax"] if rmax is None else rmax)
            ax.xaxis.set_minor_locator(LogLocator(base=10, subs=range(2, 10)))
            ax.xaxis.set_minor_formatter(NullFormatter())
            ax.tick_params(axis="x", which="both", top=True, bottom=True,
                           labeltop=True, labelbottom=True, labelsize=9)
            ax.xaxis.set_label_position("top")
            ax.set_xlabel("Radius [pc]", fontsize=9)
            ax.set_ylabel(r"$\rho$ [g cm$^{-3}$]", fontsize=10)
            ax.set_title(p["title"] + f"\ninner radius {p['inner_pc']:g} pc", fontsize=10, pad=13)
            ax.grid(which="major", alpha=0.3)
            ax.grid(axis="x", which="minor", alpha=0.2, lw=0.5)
            if p["xmax"] == 80:
                ax.text(.04, .05, "Shell underresolved (~4 cells)", transform=ax.transAxes,
                        fontsize=8, color="#9c4821")
        for ax in list(axes.flat)[len(profiles[first:first+9]):]:
            ax.set_visible(False)
        status = "selected anchors fitted" if fits else "choose R [pc] and rho(R) [g/cm^3] by panel number"
        fig.suptitle(f"Final snapshots | 40 solar masses | 4.77 Myr | page {page}\n{status}", fontsize=15)
        target = HERE / f"final_density_profiles_{page:02d}.png"
        fig.savefig(target, dpi=170, metadata={"Description":
                    "Purpose: Numbered final native density profiles for choosing endpoint-anchored fits; full radius unless --rmax supplied."})
        plt.close(fig)
        print(f"Plot: {target}")


HTML = r'''<!-- Purpose: Inspect the final native density snapshots, select endpoint anchors, and preview the latest one-parameter density fit offline. -->
<!doctype html><html lang="en"><meta charset="utf-8"><title>Final density profiles</title>
<style>
body{font:16px system-ui,sans-serif;background:#f3f5f7;color:#182d3b;margin:24px}
h1{font-size:25px}p{max-width:1100px;line-height:1.5}button,input{font:inherit;padding:6px;border:1px solid #9cacb7;border-radius:4px}
button{cursor:pointer;background:#e5eff6}input{width:120px}label{display:inline-block;margin:4px;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,620px),1fr));gap:20px}
article{background:white;border:1px solid #d1dce3;border-radius:8px;padding:16px;min-width:0}h2{font-size:17px;margin:0 0 4px}
small{display:block;color:#4a6577;overflow-wrap:anywhere}canvas{width:100%;height:auto;cursor:crosshair;touch-action:pan-y}
.readout{font:14px monospace;min-height:22px}.status{min-height:42px;font-size:13px;color:#4d5860;line-height:1.5}
.tools{margin:16px 0;position:sticky;top:0;background:#f3f5f7;padding:10px 0;z-index:2}
</style><h1>Final density profiles: 17 completed 40 M☉ runs at 4.77 Myr</h1>
<p>Click a curve to select its saved cell radius <b>R [pc]</b> and mass density <b>ρ(R) [g/cm³]</b>, then edit either value.
Use <b>Preview fit</b> to fit only the extra minimum-density parameter of the latest model, with its flat inner limit and inner index bounded below by −2.
The fit start initially follows the inner fast-wind speed drop; change it to select the region you want fitted.
The curve inward of that start is the imposed inner extension, outside the fitting interval.
Scroll over a plot to zoom in radius; double-click to restore the full range. Radius labels appear at the top and bottom.</p>
<p>These profiles come from the native final <b>0048.dat</b> cells, without VTU interpolation. The older ionized-core runs have cooling and conduction off;
this is a test of an empirical shape across different physics. No endpoint has been chosen automatically.
Panel 17 has an underresolved shell (~4 cells).</p>
<div class="tools"><button id="download">Download chosen anchors (CSV)</button> <span id="count">No anchors selected</span></div>
<main class="grid" id="plots"></main><script>
const profiles=__DATA__, saved=__FITS__, states=[];
const log=Math.log, exp=Math.exp, pow=Math.pow;
function base(x,a,m){const f=6.75*x*x*(1-x);return log(m)+a*(1-f*f)/(1+a*a*f*f)}
function slope(x,a){const f=6.75*x*x*(1-x),d=6.75*x*(2-3*x);return -2*a*(1+a*a)*f*d*x/pow(1+a*a*f*f,2)}
function golden(fn,lo,hi){const g=(Math.sqrt(5)-1)/2;let c=hi-g*(hi-lo),d=lo+g*(hi-lo),fc=fn(c),fd=fn(d);
for(let i=0;i<90;i++){if(fc<fd){hi=d;d=c;fd=fc;c=hi-g*(hi-lo);fc=fn(c)}else{lo=c;c=d;fc=fd;d=lo+g*(hi-lo);fd=fn(d)}}return (lo+hi)/2}
function innerBreak(a){const m=golden(x=>slope(x,a),1e-10,2/3);if(slope(m,a)>=-2)return 0;
let lo=m,hi=2/3;for(let i=0;i<65;i++){const x=(lo+hi)/2;if(slope(x,a)<-2)lo=x;else hi=x}return (lo+hi)/2}
function logDensity(r,fit){const x=r/fit.R_pc,a=fit.a,b=fit.xb;
if(b>0&&x<b){const t=x/b;return base(b,a,fit.rho_min_g_cm3)+(1-t*t)}return base(x,a,fit.rho_min_g_cm3)}
function preview(p,R,rhoR,rmin){if(!(Number.isFinite(R)&&Number.isFinite(rhoR)&&Number.isFinite(rmin)&&rhoR>0&&R>rmin&&rmin>=p.r[0]&&R<=p.r.at(-1)))throw Error('Require first cell ≤ fit start < R ≤ last cell; positive finite density.');
const indices=p.r.map((r,i)=>r>=rmin&&r<=R?i:-1).filter(i=>i>=0);if(indices.length<5)throw Error('Fit interval needs at least five saved cells.');
const weights=indices.map(i=>Math.min(p.right[i],R)-Math.max(p.left[i],rmin)),sw=weights.reduce((a,b)=>a+b,0);
function loss(a){const f={a,xb:innerBreak(a),R_pc:R,rho_min_g_cm3:rhoR*exp(-a)};
return indices.reduce((s,j,k)=>s+weights[k]*pow(logDensity(p.r[j],f)-log(p.rho[j]),2),0)/sw}
let best=0,value=Infinity;for(let i=0;i<=300;i++){const a=.01+(30-.01)*i/300,z=loss(a);if(z<value){value=z;best=i}}
const a=golden(loss,.01+(30-.01)*Math.max(0,best-1)/300,.01+(30-.01)*Math.min(300,best+1)/300);
return {case:p.case,R_pc:R,rho_R_g_cm3:rhoR,rmin_pc:rmin,rho_min_g_cm3:rhoR*exp(-a),a,xb:innerBreak(a),rms_log10_dex:Math.sqrt(loss(a))/log(10),fitted_cells:indices.length}}
function format(v){return Number(v).toExponential(5)}
function updateCount(){document.querySelector('#count').textContent=states.filter(s=>s.R.value&&s.rho.value).length+' / '+profiles.length+' anchors selected'}
function init(p){const card=document.createElement('article');card.innerHTML=`<h2>${p.title}</h2><small>${p.case}</small><small>${p.note}; inner radius ${p.inner_pc} pc</small>
<canvas width="1000" height="480"></canvas><div class="readout">Hover for a saved cell; click to choose the endpoint.</div>
<label>R [pc]<br><input class="radius" type="number" min="0" step="any"></label>
<label>ρ(R) [g/cm³]<br><input class="density" type="number" min="0" step="any"></label>
<label>Fit start [pc]<br><input class="start" type="number" min="0" step="any" value="${p.rmin.toPrecision(9)}"></label>
<button class="fit">Preview fit</button> <button class="clear">Clear</button><div class="status">Waiting for your endpoint anchors.</div>`;
document.querySelector('#plots').appendChild(card);const canvas=card.querySelector('canvas');
const state={p,card,canvas,R:card.querySelector('.radius'),rho:card.querySelector('.density'),start:card.querySelector('.start'),fit:null,
lo:Math.log10(p.xmin),hi:Math.log10(p.xmax),hover:-1};states.push(state);
canvas.onmousemove=e=>{const i=nearest(state,e);state.hover=i;if(i>=0)card.querySelector('.readout').textContent=`cell ${i+1}: R = ${p.r[i].toPrecision(9)} pc; ρ = ${format(p.rho[i])} g/cm³`;draw(state)};
canvas.onmouseleave=()=>{state.hover=-1;draw(state)};
canvas.onclick=e=>{const i=nearest(state,e);if(i<0)return;state.R.value=p.r[i].toPrecision(12);state.rho.value=p.rho[i].toPrecision(12);state.fit=null;card.querySelector('.status').textContent='Endpoint selected. Edit values if needed, then preview fit.';draw(state);updateCount()};
canvas.onwheel=e=>{e.preventDefault();const rect=canvas.getBoundingClientRect(),u=Math.max(0,Math.min(1,((e.clientX-rect.left)/rect.width*1000-105)/860));
const at=state.lo+u*(state.hi-state.lo),f=e.deltaY<0?.8:1.25,span=Math.min(Math.log10(p.xmax/p.xmin),(state.hi-state.lo)*f);
state.lo=Math.max(Math.log10(p.xmin),at-u*span);state.hi=Math.min(Math.log10(p.xmax),state.lo+span);state.lo=Math.max(Math.log10(p.xmin),state.hi-span);draw(state)};
canvas.ondblclick=e=>{e.preventDefault();state.lo=Math.log10(p.xmin);state.hi=Math.log10(p.xmax);draw(state)};
function fit(){try{state.fit=preview(p,+state.R.value,+state.rho.value,+state.start.value);const f=state.fit;
card.querySelector('.status').textContent=`Fitted ρ_min = ${format(f.rho_min_g_cm3)} g/cm³; ${f.fitted_cells} cells; RMS log error = ${f.rms_log10_dex.toFixed(3)} dex. R and ρ(R) are fixed. Pink dashed = model; gray line = fit start.`;draw(state);updateCount()}
catch(e){state.fit=null;card.querySelector('.status').textContent=e.message;draw(state)}}
card.querySelector('.fit').onclick=fit;card.querySelector('.clear').onclick=()=>{state.R.value='';state.rho.value='';state.fit=null;card.querySelector('.status').textContent='Waiting for your endpoint anchors.';draw(state);updateCount()};
for(const input of [state.R,state.rho,state.start])input.oninput=()=>{state.fit=null;card.querySelector('.status').textContent='Values changed. Preview fit to update the model.';draw(state);updateCount()};
if(saved[p.case]){const f=saved[p.case];state.R.value=f.R_pc;state.rho.value=f.rho_R_g_cm3;state.start.value=f.rmin_pc;fit()}else draw(state)}
function nearest(s,e){const rect=s.canvas.getBoundingClientRect(),px=(e.clientX-rect.left)/rect.width*1000,py=(e.clientY-rect.top)/rect.height*480;
if(px<105||px>965||py<55||py>405)return -1;const r=pow(10,s.lo+(px-105)/860*(s.hi-s.lo));
let lo=0,hi=s.p.r.length;while(lo<hi){const mid=(lo+hi)>>1;if(s.p.r[mid]<r)lo=mid+1;else hi=mid}
if(lo===0)return 0;if(lo===s.p.r.length)return lo-1;return Math.abs(log(s.p.r[lo]/r))<Math.abs(log(s.p.r[lo-1]/r))?lo:lo-1}
function draw(s){const c=s.canvas.getContext('2d'),p=s.p,W=1000,H=480,l=105,t=55,w=860,h=350;
c.clearRect(0,0,W,H);c.fillStyle='white';c.fillRect(0,0,W,H);const ymin=Math.floor(Math.log10(Math.min(...p.rho)))-.2,ymax=Math.ceil(Math.log10(Math.max(...p.rho)))+.2;
const X=r=>l+(Math.log10(r)-s.lo)/(s.hi-s.lo)*w,Y=y=>t+h-(Math.log10(y)-ymin)/(ymax-ymin)*h;
c.font='17px system-ui';c.textAlign='center';c.fillStyle='#263e4d';c.fillText('Radius [pc]',l+w/2,18);c.fillText('Radius [pc]',l+w/2,468);
c.save();c.translate(24,t+h/2);c.rotate(-Math.PI/2);c.fillText('ρ [g/cm³]',0,0);c.restore();
for(let k=Math.floor(s.lo);k<=Math.ceil(s.hi);k++)for(let m=1;m<=9;m++){const v=m*pow(10,k),x=X(v);if(x<l||x>l+w)continue;
c.strokeStyle=m===1?'#cbd4db':'#edf0f3';c.lineWidth=1;c.beginPath();c.moveTo(x,t);c.lineTo(x,t+h);c.stroke();
if(m===1||(s.hi-s.lo<1.5&&[2,5].includes(m))){c.fillStyle='#334e60';c.fillText(Number(v.toPrecision(4)).toString(),x,t-12);c.fillText(Number(v.toPrecision(4)).toString(),x,t+h+25)}}
for(let k=Math.ceil(ymin);k<=Math.floor(ymax);k++){const y=Y(pow(10,k));c.strokeStyle='#dfe5e9';c.beginPath();c.moveTo(l,y);c.lineTo(l+w,y);c.stroke();c.fillStyle='#334e60';c.textAlign='right';c.fillText('1e'+k,l-10,y+6)}c.textAlign='center';
c.save();c.beginPath();c.rect(l,t,w,h);c.clip();c.strokeStyle=p.case.includes('nogravity')?'#b35320':'#22638e';c.lineWidth=2.4;c.beginPath();
for(let i=0;i<p.r.length;i++){const x1=X(p.left[i]),x2=X(p.right[i]),y=Y(p.rho[i]);if(i===0)c.moveTo(x1,y);else c.lineTo(x1,y);c.lineTo(x2,y)}c.stroke();
if(s.fit){const f=s.fit;c.strokeStyle='#bd2970';c.setLineDash([8,5]);c.lineWidth=2.5;c.beginPath();for(let i=0;i<1000;i++){const r=exp(log(p.xmin)+(log(f.R_pc)-log(p.xmin))*i/999),x=X(r),y=Y(exp(logDensity(r,f)));if(i===0)c.moveTo(x,y);else c.lineTo(x,y)}c.stroke();c.setLineDash([])}
if(s.R.value&&s.rho.value){const x=X(+s.R.value),y=Y(+s.rho.value);c.strokeStyle='#bd2970';c.setLineDash([4,4]);c.beginPath();c.moveTo(x,t);c.lineTo(x,t+h);c.stroke();c.setLineDash([]);c.fillStyle='#bd2970';c.beginPath();c.arc(x,y,6,0,7);c.fill()}
if(s.start.value){c.strokeStyle='#9aa7ad';c.setLineDash([3,5]);c.beginPath();c.moveTo(X(+s.start.value),t);c.lineTo(X(+s.start.value),t+h);c.stroke();c.setLineDash([])}
if(s.hover>=0){const i=s.hover;c.fillStyle='#111';c.beginPath();c.arc(X(p.r[i]),Y(p.rho[i]),4,0,7);c.fill()}c.restore();c.strokeStyle='#657c8c';c.strokeRect(l,t,w,h)}
profiles.forEach(init);updateCount();document.querySelector('#download').onclick=()=>{const rows=['# Purpose: User-selected endpoint anchors for fitting only final native density snapshots.','case,R_pc,rho_R_g_cm3,rmin_pc,rho_min_g_cm3'];
for(const s of states)if(s.R.value&&s.rho.value)rows.push([s.p.case,s.R.value,s.rho.value,s.start.value,s.fit?s.fit.rho_min_g_cm3:''].join(','));
const url=URL.createObjectURL(new Blob([rows.join('\n')+'\n'],{type:'text/csv'})),a=document.createElement('a');a.href=url;a.download='final_density_anchors.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchors", type=Path, help="CSV downloaded from the viewer; only specified endpoints are fitted")
    parser.add_argument("--rmax", type=float, help="Optional atlas upper radius; omitted means each complete domain")
    args = parser.parse_args()
    if args.rmax is not None and (not math.isfinite(args.rmax) or args.rmax <= 0.1):
        parser.error("--rmax must be finite and greater than 0.1 pc")
    profiles = load_profiles()
    fits = load_anchors(args.anchors, profiles) if args.anchors else {}
    plot_atlas(profiles, fits, args.rmax)
    html = HTML.replace("__DATA__", json.dumps(profiles, allow_nan=False)).replace("__FITS__", json.dumps(fits, allow_nan=False))
    viewer = HERE / "final_density_profiles.html"
    viewer.write_text(html, encoding="utf-8")
    print(f"Interactive viewer: {viewer}")
    if fits:
        target = HERE / "final_density_fit_parameters.csv"
        with target.open("w", newline="") as stream:
            stream.write("# Purpose: Reproducible single-parameter density fits with user-supplied endpoint anchors; flat inner continuation.\n")
            writer = csv.DictWriter(stream, fieldnames=list(next(iter(fits.values()))))
            writer.writeheader()
            writer.writerows(fits.values())
        print(f"Fitted {len(fits)} specified endpoints; parameters: {target}")
    else:
        print("No R or rho(R) supplied: final profiles plotted; fits await your anchors.")


if __name__ == "__main__":
    main()
