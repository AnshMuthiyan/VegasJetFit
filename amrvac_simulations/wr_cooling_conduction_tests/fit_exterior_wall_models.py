# Purpose: Refit the Weaver conduction front parameterization rho(r) ~ rho0 * (1 - r/R2)^(-2/5)
# using the updated definition where R2 is the exterior of the swept-up wall (the point right before
# the density drops back to ambient ISM), for both:
# 1) Jonathan's p4_n2x simulations (from amrvac_simulations/selected_vtu and Pauley profiles)
# 2) Our 1-Myr production simulation snapshots (f_production_1myr).

import os
from pathlib import Path
import struct
import re
import matplotlib.pyplot as plt
import numpy as np
import xml.etree.ElementTree as ET

# AMRVAC / physical constants
PC_CM = 3.0857e18
M_P = 1.67262192369e-24
MU_TOTAL = 1.4 / 2.3
M_PARTICLE = MU_TOTAL * M_P

HERE = Path(__file__).resolve().parent
OUR_VTU_DIR = HERE / "f_production_1myr" / "output"
JONATHAN_VTU_DIR = Path("/mnt/c/Users/anshm/Projects/GRB modelling/AmrvacBoostresults26-10-13/amrvac_simulations/selected_vtu")

OUT_FIG_OURS = HERE / "our_sim_exterior_wall_fits.png"
OUT_FIG_JONATHAN = HERE / "jonathan_p4_exterior_wall_fits.png"
OUT_CSV_OURS = HERE / "our_sim_exterior_wall_metrics.csv"
OUT_CSV_JONATHAN = HERE / "jonathan_p4_exterior_wall_metrics.csv"


def vtk_dtype(type_name: str) -> np.dtype:
    return {
        "Float32": np.dtype("<f4"),
        "Float64": np.dtype("<f8"),
        "Int32": np.dtype("<i4"),
        "UInt32": np.dtype("<u4"),
        "Int64": np.dtype("<i8"),
        "UInt64": np.dtype("<u8"),
        "UInt8": np.dtype("u1"),
    }[type_name]


def read_vtu_general(path: Path):
    """
    Extract radial profile from AMRVAC VTU file using ElementTree.
    Supports both our format (temperature_K) and Jonathan's format (Te).
    """
    data = path.read_bytes()
    start = data.index(b"<AppendedData")
    open_end = data.index(b">", start)
    close = data.index(b"</AppendedData>", open_end)
    appended = data[open_end + 1 : close]
    underscore = appended.index(b"_")
    raw = appended[underscore + 1 :]
    xml_bytes = data[: open_end + 1] + b"_" + data[close:]
    root = ET.fromstring(xml_bytes)

    time_elem = root.find(".//FieldData/DataArray[@Name='TIME']")
    time_code = float(time_elem.text.strip()) if time_elem is not None and time_elem.text else 0.0
    time_yr = time_code / 3.1536e7

    def read_arr(elem):
        if elem is None:
            return None
        offset = int(elem.attrib["offset"])
        nbytes = struct.unpack("<I", raw[offset : offset + 4])[0]
        dtype = vtk_dtype(elem.attrib["type"])
        payload = raw[offset + 4 : offset + 4 + nbytes]
        arr = np.frombuffer(payload, dtype=dtype)
        ncomp = int(elem.attrib.get("NumberOfComponents", "1"))
        if ncomp > 1:
            arr = arr.reshape(-1, ncomp)
        return arr

    r_list, rho_list, v_list, p_list, t_list = [], [], [], [], []
    for piece in root.findall(".//Piece"):
        pts = read_arr(piece.find("./Points/DataArray"))
        rho = read_arr(piece.find("./PointData/DataArray[@Name='rho']"))
        v1 = read_arr(piece.find("./PointData/DataArray[@Name='v1']"))
        p = read_arr(piece.find("./PointData/DataArray[@Name='p']"))
        temp = read_arr(piece.find("./PointData/DataArray[@Name='temperature_K']"))
        if temp is None:
            temp = read_arr(piece.find("./PointData/DataArray[@Name='Te']"))

        r_list.append(np.asarray(pts[:, 0], dtype=float))
        rho_list.append(np.asarray(rho, dtype=float))
        v_list.append(np.asarray(v1, dtype=float) if v1 is not None else np.zeros_like(rho))
        p_list.append(np.asarray(p, dtype=float) if p is not None else np.zeros_like(rho))
        t_list.append(np.asarray(temp, dtype=float) if temp is not None else np.zeros_like(rho))

    r_all = np.concatenate(r_list)
    rho_all = np.concatenate(rho_list)
    v_all = np.concatenate(v_list)
    p_all = np.concatenate(p_list)
    t_all = np.concatenate(t_list)

    order = np.argsort(r_all)
    r_all = r_all[order]
    rho_all = rho_all[order]
    v_all = v_all[order]
    p_all = p_all[order]
    t_all = t_all[order]

    # Deduplicate overlapping cell boundaries
    unique_r, unique_rho, unique_v, unique_p, unique_t = [r_all[0]], [rho_all[0]], [v_all[0]], [p_all[0]], [t_all[0]]
    counts = [1]
    for r, rho, v, p, t in zip(r_all[1:], rho_all[1:], v_all[1:], p_all[1:], t_all[1:]):
        if np.isclose(r, unique_r[-1], rtol=1e-10, atol=1e-12):
            unique_rho[-1] += rho
            unique_v[-1] += v
            unique_p[-1] += p
            unique_t[-1] += t
            counts[-1] += 1
        else:
            unique_r.append(r)
            unique_rho.append(rho)
            unique_v.append(v)
            unique_p.append(p)
            unique_t.append(t)
            counts.append(1)

    cnt = np.asarray(counts, dtype=float)
    raw_r = np.asarray(unique_r, dtype=float)
    raw_rho = np.asarray(unique_rho, dtype=float) / cnt
    raw_v = np.asarray(unique_v, dtype=float) / cnt
    raw_p = np.asarray(unique_p, dtype=float) / cnt
    raw_t = np.asarray(unique_t, dtype=float) / cnt

    # Unit conversion
    r_pc = raw_r / PC_CM if raw_r.max() > 100.0 else raw_r
    rho_cgs = raw_rho if raw_rho.max() < 1e-10 else raw_rho * 1.0e-25
    v_kms = raw_v / 1e5 if raw_v.max() > 1e3 else raw_v * 100.0
    # Temperature: if max < 1000, it is in code units (T_code * 1.2027e8)
    t_k = raw_t if raw_t.max() > 1000.0 else raw_t * 1.20271e8

    n_cm3 = rho_cgs / M_PARTICLE

    return {
        "r_pc": r_pc,
        "rho_cgs": rho_cgs,
        "n_cm3": n_cm3,
        "v_kms": v_kms,
        "t_k": t_k,
        "time_yr": time_yr,
    }


def analyze_bubble_with_exterior_wall(data, name, is_number_density=True, expected_rho_ism=None):
    """
    Locates:
    - Rt (termination shock)
    - r_post (relaxed post-shock bubble floor)
    - R_wall_in (interior edge of the swept-up wall)
    - R_peak (peak density of the swept-up shell)
    - R2 (exterior of the wall: point right before density returns to ambient ISM)
    And fits:
    rho(r) = rho0 * [(1 - r/R2) / (1 - r_post/R2)]^(-2/5)
    """
    r = data["r_pc"]
    dens = data["n_cm3"] if is_number_density else data["rho_cgs"]
    T = data["t_k"]
    v = data["v_kms"]

    # 1. Ambient ISM level
    dens_ism = expected_rho_ism if expected_rho_ism is not None else dens[-1]

    # 2. Shell Peak: search beyond r > 0.5 pc to avoid inner boundary wind injection
    search_indices = np.where(r > 0.5)[0] if np.any(r > 0.5) else np.arange(len(r))
    peak_local_idx = np.argmax(dens[search_indices])
    peak_idx = search_indices[peak_local_idx]
    r_peak = r[peak_idx]
    dens_peak = dens[peak_idx]

    # 3. Termination shock Rt and relaxed r_post:
    inner_mask = np.where((r >= 0.2) & (r < r_peak))[0]
    r_inner = r[inner_mask]
    dens_inner = dens[inner_mask]
    v_inner = v[inner_mask]
    T_inner = T[inner_mask]

    # Look for termination shock jump
    shock_candidates = np.where((v_inner < 1000.0) & (T_inner > 1e6))[0]
    if is_number_density and len(shock_candidates) > 0:
        # For our simulation where wind drops from ~2000 km/s to <200 km/s
        rt_local = shock_candidates[0]
        rt = r_inner[rt_local]
        post_candidates = np.where((r_inner >= rt) & (v_inner < 200.0))[0]
        post_idx = inner_mask[post_candidates[0]] if len(post_candidates) > 0 else inner_mask[rt_local]
        r_post = r[post_idx]
    else:
        # For Jonathan's runs where flow is subsonic/smooth, Rt is the minimum of density (cavity base)
        min_local = np.argmin(dens_inner)
        rt = r_inner[min_local]
        r_post = rt
        post_idx = inner_mask[min_local]

    dens0 = dens[post_idx]

    # 4. Interior of swept-up wall (R_wall_in):
    # Where dense shell starts rising steeply out of the hot bubble
    # For our runs: T drops below 1e5 K or dens > 0.05 * dens_peak
    # For Jonathan's runs: where dens exceeds 5% of peak or 5 * dens0
    wall_in_candidates = np.where((r > r_post) & (r < r_peak) & ((T < 1e5) | (dens > 0.05 * dens_peak) | (dens > 5.0 * dens0)))[0]
    if len(wall_in_candidates) > 0:
        wall_in_idx = wall_in_candidates[0]
    else:
        wall_in_idx = peak_idx
    r_wall_in = r[wall_in_idx]

    # 5. Exterior of swept-up wall R2:
    # "the point right before the density goes back to ISM density"
    # Walking outward from peak, find the last cell where density is still elevated above ISM (e.g. > 1.002 * dens_ism)
    beyond_peak = np.where((r >= r_peak) & (dens > 1.002 * dens_ism))[0]
    if len(beyond_peak) > 0:
        r2_ext_idx = beyond_peak[-1]
    else:
        r2_ext_idx = peak_idx
    r2_ext = r[r2_ext_idx]

    # Conduction zone points: r_post <= r < R_wall_in
    cond_mask = np.where((r >= r_post) & (r < r_wall_in) & (1.0 - r / r2_ext > 1e-4))[0]
    r_cond = r[cond_mask]
    dens_cond = dens[cond_mask]

    # Guard: if too few points, expand slightly to r_peak
    if len(r_cond) < 3:
        cond_mask = np.where((r >= r_post) & (r <= r_wall_in) & (1.0 - r / r2_ext > 1e-4))[0]
        r_cond = r[cond_mask]
        dens_cond = dens[cond_mask]

    # 1. Anchored Weaver model: dens(r) = dens0 * [(1 - r/R2) / (1 - r_post/R2)]^(-2/5)
    base_factor = (1.0 - r_cond / r2_ext) / (1.0 - r_post / r2_ext)
    dens_model_anchored = dens0 * (base_factor ** (-0.4))

    # 2. Optimal amplitude for fixed 2/5: dens(r) = A * (1 - r/R2)^(-2/5)
    x_log = np.log(1.0 - r_cond / r2_ext)
    y_log = np.log(dens_cond)
    ln_A_25 = np.mean(y_log + 0.4 * x_log)
    A_opt_25 = np.exp(ln_A_25)
    dens_model_opt25 = A_opt_25 * ((1.0 - r_cond / r2_ext) ** (-0.4))

    # 3. Free power-law fit: dens(r) = A * (1 - r/R2)^(-alpha)
    if len(r_cond) >= 3:
        fit_coeffs = np.polyfit(x_log, y_log, 1)
        alpha_fit = -fit_coeffs[0]
        A_fit = np.exp(fit_coeffs[1])
        dens_fit = A_fit * ((1.0 - r_cond / r2_ext) ** (-alpha_fit))
    else:
        alpha_fit = 0.4
        A_fit = A_opt_25
        dens_fit = dens_model_opt25

    # Metrics
    ss_tot = np.sum((np.log10(dens_cond) - np.mean(np.log10(dens_cond))) ** 2)
    # Anchored
    ss_res_anc = np.sum((np.log10(dens_cond) - np.log10(dens_model_anchored)) ** 2)
    r2_score_anc = 1.0 - (ss_res_anc / ss_tot) if ss_tot > 0 else 0.0
    rel_err_anc = np.mean(np.abs(dens_cond - dens_model_anchored) / dens_cond) * 100.0

    # Opt 2/5
    ss_res_opt = np.sum((np.log10(dens_cond) - np.log10(dens_model_opt25)) ** 2)
    r2_score_opt = 1.0 - (ss_res_opt / ss_tot) if ss_tot > 0 else 0.0
    rel_err_opt = np.mean(np.abs(dens_cond - dens_model_opt25) / dens_cond) * 100.0

    # Free alpha
    rel_err_fit = np.mean(np.abs(dens_cond - dens_fit) / dens_cond) * 100.0

    return {
        "name": name,
        "time_yr": data["time_yr"],
        "rt": rt,
        "r_post": r_post,
        "dens0": dens0,
        "r_wall_in": r_wall_in,
        "r_peak": r_peak,
        "r2_ext": r2_ext,
        "dens_ism": dens_ism,
        "r_cond": r_cond,
        "dens_cond": dens_cond,
        "dens_model_anchored": dens_model_anchored,
        "dens_model_opt25": dens_model_opt25,
        "A_opt_25": A_opt_25,
        "dens_fit": dens_fit,
        "alpha_fit": alpha_fit,
        "rel_err_anc": rel_err_anc,
        "r2_score_anc": r2_score_anc,
        "rel_err_opt": rel_err_opt,
        "r2_score_opt": r2_score_opt,
        "rel_err_fit": rel_err_fit,
    }


def main():
    print("=========================================================================================")
    print("ANALYSIS 1: OUR PRODUCTION SIMULATION (f_production_1myr) WITH EXTERIOR WALL R2")
    print("=========================================================================================")

    our_snaps = ["test0001.vtu", "test0002.vtu", "test0003.vtu", "test0004.vtu"]
    our_results = []
    for s in our_snaps:
        p = OUR_VTU_DIR / s
        data = read_vtu_general(p)
        res = analyze_bubble_with_exterior_wall(data, s, is_number_density=True, expected_rho_ism=10000.0)
        our_results.append(res)

    print(f"{'Snapshot':<12} {'Time [yr]':<11} {'Rt [pc]':<8} {'R_wall,in':<10} {'Peak [pc]':<10} {'R2_ext':<8} {'Anchored 2/5 Err':<18} {'Opt 2/5 Err':<14} {'Best alpha':<10}")
    print("-" * 105)
    for res in our_results:
        print(f"{res['name']:<12} {res['time_yr']:<11,.0f} {res['rt']:<8.3f} {res['r_wall_in']:<10.3f} {res['r_peak']:<10.3f} {res['r2_ext']:<8.3f} "
              f"{res['rel_err_anc']:>5.1f}% (R^2={res['r2_score_anc']:>5.2f})    "
              f"{res['rel_err_opt']:>5.1f}% (A={res['A_opt_25']:>4.2f})   "
              f"alpha={res['alpha_fit']:.2f}")

    # Plot Our Sim Results
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    colors = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd"]
    for idx, (res, col) in enumerate(zip(our_results, colors)):
        ax = axes.flat[idx]
        r = res["r_cond"]
        ax.plot(r, res["dens_cond"], "o-", color=col, lw=2.2, ms=5, label=f"Simulation ({res['time_yr']:,.0f} yr)")
        ax.plot(r, res["dens_model_anchored"], "--", color="black", lw=2.0,
                label=rf"Weaver $(1 - r/R_2)^{{-2/5}}$ (anchored to $n_0$, err={res['rel_err_anc']:.1f}%)")
        ax.plot(r, res["dens_model_opt25"], "-.", color="#e377c2", lw=1.8,
                label=rf"Weaver $(1 - r/R_2)^{{-2/5}}$ (opt $A={res['A_opt_25']:.2f}$, err={res['rel_err_opt']:.1f}%)")
        ax.plot(r, res["dens_fit"], ":", color="#17becf", lw=2.0,
                label=rf"Best-fit $(1 - r/R_2)^{{-\alpha}}$ ($\alpha={res['alpha_fit']:.2f}$, err={res['rel_err_fit']:.1f}%)")

        ax.axvline(res["rt"], color="blue", ls=":", alpha=0.6, label=f"$R_t = {res['rt']:.2f}$ pc (shock)")
        ax.axvline(res["r_wall_in"], color="orange", ls=":", alpha=0.6, label=f"$R_{{wall,in}} = {res['r_wall_in']:.2f}$ pc")
        ax.axvline(res["r2_ext"], color="red", ls="-", alpha=0.8, lw=1.5, label=f"$R_2 = {res['r2_ext']:.2f}$ pc (wall exterior)")

        ax.set_yscale("log")
        ax.set_xlabel("Radius $r$ [pc]", fontsize=11)
        ax.set_ylabel("Number Density $n$ [cm$^{-3}$]", fontsize=11)
        ax.set_title(
            f"{res['name']} ($t = {res['time_yr']:,.0f}$ yr) | $R_t={res['rt']:.2f}$ pc, $R_2={res['r2_ext']:.2f}$ pc (exterior)\n"
            f"Anchored 2/5 Err = {res['rel_err_anc']:.1f}% | Opt 2/5 Err = {res['rel_err_opt']:.1f}% | Best $\\alpha = {res['alpha_fit']:.2f}$",
            fontsize=12, fontweight="bold",
        )
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(loc="upper left", fontsize=8.5, framealpha=0.92)

    fig.suptitle(
        r"Refitting Our Simulation: $\rho(r) \propto \rho_0 (1 - r/R_2)^{-2/5}$ with $R_2 \equiv$ Exterior of Swept-up Wall" + "\n"
        r"$R_2$ Defined as Outer Edge of Shell Right Before Returning to Ambient ISM ($n = 10^4\ \mathrm{cm}^{-3}$)",
        fontsize=14, fontweight="bold", y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(OUT_FIG_OURS, dpi=200)
    print(f"Saved figure to {OUT_FIG_OURS}")

    # Save CSV for Our Sim
    with open(OUT_CSV_OURS, "w") as f:
        f.write("# Purpose: Metrics for Weaver conduction front with R2 defined as exterior of swept-up wall (Our sim)\n")
        f.write("snapshot,time_years,Rt_pc,r_wall_in_pc,r_peak_pc,R2_exterior_pc,n0_cm3,rel_err_anchored_2_5,R2_anchored_2_5,A_opt_2_5,rel_err_opt_2_5,R2_opt_2_5,alpha_best_fit,rel_err_best_fit\n")
        for res in our_results:
            f.write(f"{res['name']},{res['time_yr']:.1f},{res['rt']:.4f},{res['r_wall_in']:.4f},{res['r_peak']:.4f},{res['r2_ext']:.4f},"
                    f"{res['dens0']:.4e},{res['rel_err_anc']:.2f},{res['r2_score_anc']:.4f},{res['A_opt_25']:.4e},{res['rel_err_opt']:.2f},{res['r2_score_opt']:.4f},"
                    f"{res['alpha_fit']:.4f},{res['rel_err_fit']:.2f}\n")
    print(f"Metrics saved to {OUT_CSV_OURS}")

    print("\n=========================================================================================")
    print("ANALYSIS 2: JONATHAN'S SIMULATIONS (p4_n2x) WITH EXTERIOR WALL R2")
    print("=========================================================================================")

    jonathan_cases = [
        ("p4_n21", 1e-21),
        ("p4_n22", 1e-22),
        ("p4_n23", 1e-23),
        ("p4_n24", 1e-24),
    ]
    jonathan_results = []
    for c, rho_ism in jonathan_cases:
        p = JONATHAN_VTU_DIR / f"{c}__test0004.vtu"
        if p.exists():
            data = read_vtu_general(p)
            res = analyze_bubble_with_exterior_wall(data, c, is_number_density=False, expected_rho_ism=rho_ism)
            jonathan_results.append(res)

    print(f"{'Case':<10} {'Time [yr]':<11} {'Rt [pc]':<8} {'R_wall,in':<10} {'Peak [pc]':<10} {'R2_ext':<8} {'Anchored 2/5 Err':<18} {'Opt 2/5 Err':<14} {'Best alpha':<10}")
    print("-" * 105)
    for res in jonathan_results:
        print(f"{res['name']:<10} {res['time_yr']:<11,.0f} {res['rt']:<8.3f} {res['r_wall_in']:<10.3f} {res['r_peak']:<10.3f} {res['r2_ext']:<8.3f} "
              f"{res['rel_err_anc']:>5.1f}% (R^2={res['r2_score_anc']:>5.2f})    "
              f"{res['rel_err_opt']:>5.1f}% (A={res['A_opt_25']:>8.2e})   "
              f"alpha={res['alpha_fit']:.2f}")

    # Plot Jonathan Results
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    for idx, (res, col) in enumerate(zip(jonathan_results, colors)):
        ax = axes.flat[idx]
        r = res["r_cond"]
        ax.plot(r, res["dens_cond"], "o-", color=col, lw=2.2, ms=5, label=f"Jonathan VTU ({res['name']})")
        ax.plot(r, res["dens_model_anchored"], "--", color="black", lw=2.0,
                label=rf"Weaver $(1 - r/R_2)^{{-2/5}}$ (anchored to $\rho_0$, err={res['rel_err_anc']:.1f}%)")
        ax.plot(r, res["dens_model_opt25"], "-.", color="#e377c2", lw=1.8,
                label=rf"Weaver $(1 - r/R_2)^{{-2/5}}$ (opt $A={res['A_opt_25']:.1e}$, err={res['rel_err_opt']:.1f}%)")
        ax.plot(r, res["dens_fit"], ":", color="#17becf", lw=2.0,
                label=rf"Best-fit $(1 - r/R_2)^{{-\alpha}}$ ($\alpha={res['alpha_fit']:.2f}$, err={res['rel_err_fit']:.1f}%)")

        ax.axvline(res["rt"], color="blue", ls=":", alpha=0.6, label=f"$R_t = {res['rt']:.2f}$ pc")
        ax.axvline(res["r_wall_in"], color="orange", ls=":", alpha=0.6, label=f"$R_{{wall,in}} = {res['r_wall_in']:.2f}$ pc")
        ax.axvline(res["r2_ext"], color="red", ls="-", alpha=0.8, lw=1.5, label=f"$R_2 = {res['r2_ext']:.2f}$ pc (wall exterior)")

        ax.set_yscale("log")
        ax.set_xlabel("Radius $r$ [pc]", fontsize=11)
        ax.set_ylabel(r"Mass Density $\rho$ [g cm$^{-3}$]", fontsize=11)
        ax.set_title(
            f"{res['name']} ($t = {res['time_yr']:,.0f}$ yr) | $R_t={res['rt']:.2f}$ pc, $R_2={res['r2_ext']:.2f}$ pc (exterior)\n"
            f"Anchored 2/5 Err = {res['rel_err_anc']:.1f}% | Opt 2/5 Err = {res['rel_err_opt']:.1f}% | Best $\\alpha = {res['alpha_fit']:.2f}$",
            fontsize=12, fontweight="bold",
        )
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(loc="lower left", fontsize=8.5, framealpha=0.92)

    fig.suptitle(
        r"Fitting Jonathan's $p4\_n2x$ Simulations: $\rho(r) \propto \rho_0 (1 - r/R_2)^{-2/5}$ with Exterior Wall $R_2$" + "\n"
        r"$R_2$ Defined as Outer Edge of Swept-up Shell Right Before Returning to Ambient ISM",
        fontsize=14, fontweight="bold", y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(OUT_FIG_JONATHAN, dpi=200)
    print(f"Saved figure to {OUT_FIG_JONATHAN}")

    # Save CSV for Jonathan
    with open(OUT_CSV_JONATHAN, "w") as f:
        f.write("# Purpose: Metrics for Weaver conduction front with R2 defined as exterior of swept-up wall (Jonathan p4)\n")
        f.write("case,time_years,Rt_pc,r_wall_in_pc,r_peak_pc,R2_exterior_pc,rho0_cgs,rel_err_anchored_2_5,R2_anchored_2_5,A_opt_2_5,rel_err_opt_2_5,R2_opt_2_5,alpha_best_fit,rel_err_best_fit\n")
        for res in jonathan_results:
            f.write(f"{res['name']},{res['time_yr']:.1f},{res['rt']:.4f},{res['r_wall_in']:.4f},{res['r_peak']:.4f},{res['r2_ext']:.4f},"
                    f"{res['dens0']:.4e},{res['rel_err_anc']:.2f},{res['r2_score_anc']:.4f},{res['A_opt_25']:.4e},{res['rel_err_opt']:.2f},{res['r2_score_opt']:.4f},"
                    f"{res['alpha_fit']:.4f},{res['rel_err_fit']:.2f}\n")
    print(f"Metrics saved to {OUT_CSV_JONATHAN}")


if __name__ == "__main__":
    main()
