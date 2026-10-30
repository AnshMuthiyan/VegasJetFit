#!/usr/bin/env python3
"""Independently validate and diagnose immutable full-track pulls; never dispatch.

DAT fields are native conservative cell data. VTU fields are interpolated vertex
data with Float32 time labels; DAT times control exact endpoint/cadence gates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/amrvac_full_grid_mplconfig")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grid_runtime
from analysis_support import amrvac_datfile_utilities_v31 as du

PC = 3.085677581e18
YEAR = 365 * 86400.0
MSUN = 1.98892e33  # Pinned AMRVAC v3.1 const_MSun, used by injected rates.
MP = 1.6726219e-24
KB = 1.380649e-16
G = 6.67430e-8
TIME_MYR = PC / 1e7 / YEAR / 1e6


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def profile_nh(r, nref):
    core = nref * (26 / (1 + (r / .2) ** 2)) ** .9
    ambient = 10 + 990 * .5 * (1 - np.tanh(r - 15))
    return ambient + np.maximum(0, core - ambient) * .5 * (1 - np.tanh((r - 2) / .5))


def atmosphere_pressure(r, nref, pk, mass):
    # Independent integration on the source's documented atmosphere grid.
    x = np.geomspace(.001, 160, 16385)
    mid = (x[1:] + x[:-1]) / 2
    density = profile_nh(mid, nref) * 1.4 * MP
    dm = 4 * np.pi * (mid * PC) ** 2 * density * np.diff(x) * PC
    enclosed = mass * MSUN + np.r_[0, np.cumsum(dm)]
    grav = G * (enclosed[1:] + enclosed[:-1]) / 2 / (mid * PC) ** 2
    dp = density * grav * np.diff(x) * PC
    pressure = pk * KB + np.r_[np.cumsum(dp[::-1])[::-1], 0]
    return np.interp(r, x, pressure)


def read_native(path, design):
    with path.open("rb") as f:
        h = du.get_header(f)
        levels, indices, offsets = du.get_tree_info(f)
        assert h["datfile_version"] == 5 and h["geometry"] == "spherical"
        assert h["nw"] == 3 and h["w_names"] == ["rho", "m1", "e"]
        assert h["ndim"] == 1 and h["levmax"] == 1 and np.all(levels == 1)
        n, bn = int(h["domain_nx"][0]), int(h["block_nx"][0])
        assert n == 1024 and bn == 8 and h["nleafs"] == 128
        assert sorted(indices[:, 0].tolist()) == list(range(1, 129))
        a = np.full((n, 3), np.nan)
        for index, offset in zip(indices[:, 0], offsets):
            a[(index - 1) * bn:index * bn] = du.get_single_block_data(f, offset, (bn, 3))
    q = design["qstretch"]
    edges = .001 + .0003 * np.expm1(np.arange(n + 1) * np.log(q)) / (q - 1)
    assert abs(edges[-1] - 160) < 1e-8
    r = (edges[:-1] + edges[1:]) / 2
    rho = a[:, 0] * 1e-25
    v = a[:, 1] / a[:, 0] * 1e7
    p = (h["gamma"] - 1) * (a[:, 2] - .5 * a[:, 1] ** 2 / a[:, 0]) * 1e-11
    assert np.isfinite(a).all() and np.isfinite(p).all()
    assert np.all(rho > 0) and np.all(p > 0)
    sound = np.sqrt(h["gamma"] * p / rho)
    vol = 4 * np.pi / 3 * np.diff((edges * PC) ** 3)
    return dict(age=h["time"] * TIME_MYR, edges=edges, r=r, rho=rho,
                v=v, p=p, mach=v / sound, mass=np.cumsum(rho * vol), volume=vol)


def features(d, initial, speed):
    """Operational candidates only; no physical width or convergence inference."""
    r, rho, v, p, mach = (d[k] for k in ("r", "rho", "v", "p", "mach"))
    peaks, props = find_peaks(np.log(rho), prominence=np.log(2), distance=3)
    candidates = []
    previous = 0
    for peak_number, peak in enumerate(peaks):
        if peak < 3:
            continue
        lo = previous + int(np.argmin(rho[previous:peak]))
        previous = int(peak)
        baseline, height = rho[lo], rho[peak]
        if height / baseline < 2:
            continue
        crossings, positions = [], []
        for frac in (.1, .5, .9):
            target = baseline + frac * (height - baseline)
            jj = np.where((rho[lo:peak] <= target) & (rho[lo+1:peak+1] >= target))[0]
            if not len(jj):
                break
            j = lo + int(jj[-1])
            f = (target - rho[j]) / (rho[j+1] - rho[j])
            crossings.append(float(r[j] + f * (r[j+1] - r[j])))
            positions.append(j + float(f))
        if len(crossings) != 3:
            continue
        flags = []
        cells = positions[2] - positions[0]
        if cells < 5:
            flags.append("UNRESOLVED_LT5_NATIVE_CELLS")
        if lo < 3 or crossings[0] <= d["edges"][3]:
            flags.append("NEAR_INJECTION_BOUNDARY")
        if r[peak] >= 140:
            flags.append("OUTER_BOUNDARY_REGION")
        right_stop = int(peaks[peak_number + 1]) if peak_number + 1 < len(peaks) else len(r) - 1
        right_min = int(peak) + int(np.argmin(rho[peak:right_stop + 1]))
        half = baseline + .5 * (height - baseline)
        falling = np.where((rho[peak:right_min] >= half) & (rho[peak + 1:right_min + 1] <= half))[0]
        fwhm, fwhm_cells = None, None
        if len(falling):
            j = int(peak) + int(falling[0])
            frac = float((half - rho[j]) / (rho[j + 1] - rho[j]))
            fwhm = float(r[j] + frac * (r[j + 1] - r[j]) - crossings[1])
            fwhm_cells = j + frac - positions[1]
        else:
            flags.append("FWHM_RIGHT_CROSSING_MISSING")
        candidates.append(dict(peak_pc=float(r[peak]), r10_pc=crossings[0],
            r50_pc=crossings[1], r90_pc=crossings[2],
            width_10_90_pc=crossings[2] - crossings[0], cells_10_90=cells,
            local_peak_fwhm_pc=fwhm, local_peak_fwhm_cells=fwhm_cells,
            peak_to_local_baseline=float(height / baseline),
            peak_to_initial=float(height / initial["rho"][peak]), flags=flags))
    # Distinct flow gate: outward supersonic-to-subsonic transition, pressure and
    # density jumps, and an upstream speed compatible with the injected wind.
    termination = []
    for i in np.where((mach[:-1] > 1) & (mach[1:] <= 1))[0]:
        l, u = max(0, i - 4), min(len(r) - 1, i + 4)
        upstream = l + int(np.argmax(mach[l:i+1]))
        downstream = i + 1 + int(np.argmax(p[i+1:u+1]))
        if (mach[upstream] >= 2 and v[upstream] > .5 * speed * 1e5
                and p[downstream] / p[upstream] > 2
                and rho[downstream] / rho[upstream] > 1.5):
            termination.append(dict(radius_pc=float((r[i] + r[i+1]) / 2),
                upstream_mach=float(mach[upstream]), downstream_mach=float(mach[i+1]),
                pressure_jump=float(p[downstream] / p[upstream]),
                density_jump=float(rho[downstream] / rho[upstream]),
                flags=["NEAR_INJECTION_BOUNDARY"] if i < 3 else []))
    outer = [c for c in candidates if c["peak_to_initial"] > 2]
    return dict(inner_rise_candidate=candidates[0] if candidates else None,
        all_density_rise_candidates=candidates,
        outer_shell_candidate=outer[-1] if outer else None,
        termination_flow_candidate=termination[0] if termination else None,
        all_termination_flow_candidates=termination,
        interpretation="Operational native-grid candidates; density peaks are not identified as termination shocks. Missing, injection-adjacent and unresolved features are excluded from surrogate eligibility.")


def radial_axes(ax, inner=False):
    ax.set_xscale("log")
    ax.set_xlim(.001 * PC, (2 if inner else 160) * PC)
    ax.set_xlabel("Radius (cm)")
    top = ax.secondary_xaxis("top", functions=(lambda cm: cm / PC, lambda pc: pc * PC))
    top.set_xlabel("Radius (pc)")
    ax.grid(alpha=.2, which="both")


def phase(age, mass):
    if mass == 25:
        return ("MS", 1500) if age < 6.5 else ("RSG", 15)
    return ("MS", 2000) if age < 4.3 else (("RSG", 15) if age < 4.5 else ("WR", 2000))


def reconcile(case_dir, row, design):
    raw = case_dir / "raw"
    dest = case_dir / "independent_validation"
    dest.mkdir(exist_ok=False)
    view = dest / "grid_runtime_view"
    view.mkdir()
    # Keep the original remote validation.json immutable.
    for f in raw.iterdir():
        if f.name != "validation.json":
            (view / f.name).symlink_to(f.resolve(), target_is_directory=f.is_dir())
    runtime = grid_runtime.check(view, row, "full", float(row["endpoint_myr"]), int(row["expected_vtus"]))
    mass, expected_count = int(row["star_mass_msun"]), int(row["expected_vtus"])
    paths = sorted((raw / "output").glob(row["case"] + "_full[0-9][0-9][0-9][0-9].dat"))
    vtus = sorted((raw / "output").glob(row["case"] + "_full[0-9][0-9][0-9][0-9].vtu"))
    assert len(paths) == len(vtus) == expected_count
    assert [f.stem[-4:] for f in paths] == [f"{i:04}" for i in range(expected_count)]
    assert [f.stem for f in paths] == [f.stem for f in vtus]
    data = [read_native(f, design) for f in paths]
    expected = np.r_[np.arange(expected_count - 1) * .1, float(row["endpoint_myr"])]
    age_error = max(abs(d["age"] - age) for d, age in zip(data, expected))
    assert age_error <= 1e-9, age_error
    nref, pk = float(row["n_ref_cm3_at_1pc"]), float(row["external_pressure_over_k_K_cm3"])
    initial = data[0]
    density_error = float(np.max(abs(initial["rho"] / (profile_nh(initial["r"], nref) * 1.4 * MP) - 1)))
    pressure_error = float(np.max(abs(initial["p"] / atmosphere_pressure(initial["r"], nref, pk, mass) - 1)))
    assert density_error < 1e-8, density_error
    assert pressure_error < 1e-6, pressure_error
    outer = initial["r"] >= 40
    outer_history = [dict(age_myr=d["age"], density_relative_drift=float(np.max(abs(d["rho"][outer] / initial["rho"][outer] - 1))),
        pressure_relative_drift=float(np.max(abs(d["p"][outer] / initial["p"][outer] - 1)))) for d in data]
    outer_density = outer_history[-1]["density_relative_drift"]
    outer_pressure = outer_history[-1]["pressure_relative_drift"]
    assert outer_density < .02 and outer_pressure < .02, (outer_density, outer_pressure)
    report = dict(case=row["case"], status="PASS", endpoint_myr=data[-1]["age"],
        saves=len(data), max_exact_dat_age_error_myr=float(age_error),
        max_initial_density_relative_error=density_error,
        max_initial_pressure_relative_error=pressure_error,
        stable_outer_region_pc=[40, 160], max_outer_density_drift=outer_density,
        max_outer_pressure_drift=outer_pressure, outer_drift_limit=.02,
        outer_gate_scope="Endpoint r>=40 pc relative to initial; all transient saves retained separately below",
        outer_history=outer_history,
        all_history_max_outer_density_drift=max(d["density_relative_drift"] for d in outer_history),
        all_history_max_outer_pressure_drift=max(d["pressure_relative_drift"] for d in outer_history),
        analysis_recipe_sha256=sha(__file__), dat_reader_sha256=sha(HERE / "analysis_support/amrvac_datfile_utilities_v31.py"),
        runtime_check_status=runtime["status"], native_cells=1024,
        age_authority="Float64 DAT headers; Float32 VTU time labels retain their original rounding",
        profile_authority="Native DAT conservative cell data; no VTU vertex interpolation or regridding",
        mass_units=f"grams; pinned AMRVAC solar mass {MSUN:.6e} g; gas mass excludes the star and r<0.001 pc",
        dat_sha256={f.name:sha(f) for f in paths}, vtu_sha256={f.name:sha(f) for f in vtus})
    write_json(dest / "independent_gates.json", report)
    images = case_dir / "images"
    profiles = case_dir / "native_profiles"
    images.mkdir(exist_ok=False)
    profiles.mkdir(exist_ok=False)
    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    ax.plot([d["age_myr"] for d in outer_history], [100*d["density_relative_drift"] for d in outer_history], label="Density")
    ax.plot([d["age_myr"] for d in outer_history], [100*d["pressure_relative_drift"] for d in outer_history], label="Pressure")
    ax.set(xlabel="Integration age (Myr)", ylabel="Maximum relative change (%)", title=row["case"] + " | outer atmosphere 40--160 pc")
    ax.legend();ax.grid(alpha=.2);fig.savefig(images/"outer_atmosphere_history.png",dpi=150);plt.close(fig)
    all_features = []
    for i, d in enumerate(data):
        ph, speed = phase(d["age"], mass)
        f = features(d, initial, speed)
        all_features.append(dict(snapshot=i, age_myr=d["age"], phase=ph, **f))
        excess = np.cumsum(np.maximum(0, d["rho"] - initial["rho"]) * d["volume"])
        matrix = np.column_stack((d["edges"][:-1] * PC, d["edges"][1:] * PC,
            d["r"] * PC, d["rho"], d["v"], d["p"], d["mach"], d["mass"], excess,
            d["mass"] - initial["mass"]))
        np.savetxt(profiles / f"snapshot_{i:04}.csv", matrix, delimiter=",",
            header="r_lo_cm,r_hi_cm,r_center_cm,rho_g_cm3,v_cm_s,p_dyn_cm2,mach,cumulative_gas_g,cumulative_positive_excess_g,cumulative_gas_change_g", comments="")
        fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
        ax.stairs(d["rho"], d["edges"] * PC, color="#145785", label="Native simulation cells")
        ax.plot(initial["r"] * PC, initial["rho"], "--", color=".5", lw=1, label="Initial cloud")
        ax.set_yscale("log");ax.set_ylabel(r"Density (g cm$^{-3}$)")
        radial_axes(ax)
        ax.set_title(f"{row['case']} | {d['age']:.6f} Myr | {ph}", pad=48, fontsize=10)
        ax.legend(fontsize=8)
        fig.savefig(images / f"density_{i:04}.png", dpi=130)
        plt.close(fig)
    write_json(case_dir / "feature_diagnostics.json", all_features)
    indices = [0, *([64, 66, 70] if mass == 25 else [42, 44, 46, 48])]
    for inner in (False, True):
        fig, axes = plt.subplots(2, 1, figsize=(9, 8), constrained_layout=True)
        for i in indices:
            d = data[i];ph, _ = phase(d["age"], mass)
            label=f"{d['age']:.2f} Myr ({ph})"
            axes[0].stairs(d["rho"], d["edges"] * PC, label=label)
            axes[1].plot(d["r"] * PC, d["mass"], label=label)
        for ax in axes:
            ax.set_yscale("log");radial_axes(ax, inner)
        axes[0].set_ylabel(r"Density (g cm$^{-3}$)");axes[0].legend(fontsize=8)
        axes[1].set_ylabel("Cumulative gas mass (g)")
        right=axes[1].secondary_yaxis("right", functions=(lambda g:g/MSUN,lambda m:m*MSUN))
        right.set_ylabel(r"Cumulative gas mass ($M_\odot$)")
        fig.suptitle(row["case"] + (" | inner 2 pc" if inner else " | full domain"))
        fig.savefig(images / ("phases_inner.png" if inner else "phases_full.png"), dpi=150)
        plt.close(fig)
    d=data[-1];f=all_features[-1]
    fig, axes=plt.subplots(3,1,figsize=(9,9),constrained_layout=True)
    axes[0].stairs(d["rho"],d["edges"]*PC);axes[0].set_yscale("log");axes[0].set_ylabel(r"Density (g cm$^{-3}$)")
    axes[1].plot(d["r"]*PC,d["v"]/1e5);axes[1].set_ylabel("Radial speed (km/s)")
    axes[2].plot(d["r"]*PC,d["mach"]);axes[2].set_yscale("symlog",linthresh=1);axes[2].axhline(1,color=".5",ls=":");axes[2].set_ylabel("Radial Mach number")
    for ax in axes:
        radial_axes(ax,True)
        for key,color in [("inner_rise_candidate","#bf5c00"),("outer_shell_candidate","#197640"),("termination_flow_candidate","#8d3d9a")]:
            feature=f[key]
            if feature:
                radius=feature.get("r50_pc",feature.get("radius_pc"))
                ax.axvline(radius*PC,color=color,ls="--",label=key.replace("_candidate",""))
    axes[0].legend(fontsize=7)
    fig.suptitle(row["case"]+" | exact endpoint | operational feature candidates")
    fig.savefig(images/"endpoint_flow_features.png",dpi=150);plt.close(fig)
    return {**report, "endpoint_features":all_features[-1], "density_pngs":len(data),
            "native_profile_csvs":len(data), "raw":str(raw)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("host_result_root",type=Path);args=parser.parse_args()
    base=args.host_result_root.resolve()
    design=json.loads((HERE/"design.json").read_text())
    rows={r["case"]:r for r in csv.DictReader((HERE/"manifest.csv").open())}
    results=[]
    for d in sorted(base.glob("m*_n*_pk*")):
        results.append(reconcile(d,rows[d.name],design))
        print(d.name,"independent gates and diagnostics PASS",flush=True)
    write_json(base/"reconciliation_summary.json",results)
    print(json.dumps({"cases":len(results),"status":"PASS","density_pngs":sum(r["density_pngs"] for r in results)}))


if __name__ == "__main__":
    main()
