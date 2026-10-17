# Purpose: Test whether the Weaver-like thermal conduction front profile
# rho(r) = rho_0 * (1 - r/R2)^(-2/5) parameterizes the hot bubble density structure
# across all evolved snapshots of the 1 Myr simulation (f_production_1myr).

import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from plot_production_1myr import extract_vtu_data, VTU_DIR

HERE = Path(__file__).resolve().parent
OUT_IMG = HERE / "conduction_front_fits.png"
OUT_CSV = HERE / "conduction_front_metrics.csv"


def find_bubble_boundaries(r, n, T, v):
    """
    Find termination shock Rt and wall start R2.
    Rt: where velocity drops below 1000 km/s and T jumps above 1e5 K.
    R2: where the cold dense swept-up wall starts (T drops sharply, n rises towards shell).
    """
    # 1. Termination shock Rt: where v drops below 1000 km/s and T > 1e5 K
    shock_mask = np.where((v < 1000.0) & (T > 1e5))[0]
    if len(shock_mask) == 0:
        raise ValueError("Could not locate termination shock")
    rt_idx = shock_mask[0]
    rt = r[rt_idx]

    # Post-shock relaxed location: the spot right after the shock where wind has fully decelerated (v < 200 km/s)
    post_shock_mask = np.where((r >= rt) & (v < 200.0))[0]
    post_idx = post_shock_mask[0] if len(post_shock_mask) > 0 else min(rt_idx + 1, len(r) - 1)
    r_post = r[post_idx]
    n0 = n[post_idx]
    t0 = T[post_idx]

    # 2. Shell peak
    peak_idx = np.argmax(n)
    r_peak = r[peak_idx]

    # 3. Wall start R2: where the cold dense swept-up ISM wall starts
    # In the hot bubble, T is high (> 1e6 K) and n is low (< 1 cm^-3).
    # The wall starts where T drops below 1e5 K or n surges above 100 cm^-3.
    wall_candidates = np.where((r > r_post) & ((T < 1e5) | (n > 100.0)))[0]
    if len(wall_candidates) > 0:
        r2_idx = wall_candidates[0]
    else:
        r2_idx = peak_idx

    r2 = r[r2_idx]

    return {
        "rt_idx": rt_idx,
        "rt": rt,
        "post_idx": post_idx,
        "r_post": r_post,
        "n0": n0,
        "t0": t0,
        "r2_idx": r2_idx,
        "r2": r2,
        "r_peak": r_peak,
        "n_peak": n[peak_idx],
    }


def analyze_snapshot(snap_path: Path):
    data = extract_vtu_data(snap_path)
    r = data["r_pc"]
    n = data["n_cm3"]
    T = data["t_k"]
    v = data["v_kms"]
    time_yr = data["time_years"]

    bounds = find_bubble_boundaries(r, n, T, v)
    rt = bounds["rt"]
    r_post = bounds["r_post"]
    r2 = bounds["r2"]
    n0 = bounds["n0"]

    # Conduction zone points: r_post <= r < R2
    cond_mask = np.where((r >= r_post) & (r < r2) & (1.0 - r / r2 > 1e-4))[0]
    r_cond = r[cond_mask]
    n_cond = n[cond_mask]
    T_cond = T[cond_mask]

    # 1. Weaver profile normalized at r_post:
    # n_model(r) = n0 * [(1 - r/R2) / (1 - r_post/R2)]^(-2/5)
    base_factor = (1.0 - r_cond / r2) / (1.0 - r_post / r2)
    n_model_norm = n0 * (base_factor ** (-0.4))

    x_log = np.log(1.0 - r_cond / r2)
    y_log = np.log(n_cond)

    # 2. Optimal amplitude for fixed 2/5: n(r) = A_25 * (1 - r/R2)^(-0.4)
    ln_A_25 = np.mean(y_log + 0.4 * x_log)
    A_fixed_25 = np.exp(ln_A_25)
    n_model_opt25 = A_fixed_25 * ((1.0 - r_cond / r2) ** (-0.4))

    # 3. Optimal amplitude for fixed 2/7 (Weaver with radiative cooling): n(r) = A_27 * (1 - r/R2)^(-2/7)
    ln_A_27 = np.mean(y_log + (2.0 / 7.0) * x_log)
    A_fixed_27 = np.exp(ln_A_27)
    n_model_opt27 = A_fixed_27 * ((1.0 - r_cond / r2) ** (-2.0 / 7.0))

    # 4. Fit generalized power-law: n(r) = A * (1 - r/R2)^(-alpha)
    if len(r_cond) >= 3:
        fit_coeffs = np.polyfit(x_log, y_log, 1)
        alpha_fit = -fit_coeffs[0]
        A_fit = np.exp(fit_coeffs[1])
        n_fit = A_fit * ((1.0 - r_cond / r2) ** (-alpha_fit))
    else:
        alpha_fit = np.nan
        A_fit = np.nan
        n_fit = n_model_norm

    # 5. Fit temperature profile: T(r) = T0 * [(1 - r/R2) / (1 - Rt/R2)]^(2/5)
    T0 = bounds["t0"]
    T_model = T0 * (base_factor ** 0.4)

    # Metrics for user anchored n_model_norm
    ss_tot = np.sum((np.log10(n_cond) - np.mean(np.log10(n_cond))) ** 2)
    ss_res_norm = np.sum((np.log10(n_cond) - np.log10(n_model_norm)) ** 2)
    r2_score_norm = 1.0 - (ss_res_norm / ss_tot) if ss_tot > 0 else 0.0
    rel_err_norm = np.mean(np.abs(n_cond - n_model_norm) / n_cond) * 100.0

    # Metrics for optimal fixed 2/5
    ss_res_opt25 = np.sum((np.log10(n_cond) - np.log10(n_model_opt25)) ** 2)
    r2_score_opt25 = 1.0 - (ss_res_opt25 / ss_tot) if ss_tot > 0 else 0.0
    rel_err_opt25 = np.mean(np.abs(n_cond - n_model_opt25) / n_cond) * 100.0

    # Metrics for optimal fixed 2/7
    ss_res_opt27 = np.sum((np.log10(n_cond) - np.log10(n_model_opt27)) ** 2)
    r2_score_opt27 = 1.0 - (ss_res_opt27 / ss_tot) if ss_tot > 0 else 0.0
    rel_err_opt27 = np.mean(np.abs(n_cond - n_model_opt27) / n_cond) * 100.0

    # Metrics for best fit alpha
    ss_res_fit = np.sum((np.log10(n_cond) - np.log10(n_fit)) ** 2)
    r2_score_fit = 1.0 - (ss_res_fit / ss_tot) if ss_tot > 0 else 0.0
    rel_err_fit = np.mean(np.abs(n_cond - n_fit) / n_cond) * 100.0

    return {
        "snapshot": snap_path.name,
        "time_yr": time_yr,
        "rt": rt,
        "r2": r2,
        "n0": n0,
        "t0": T0,
        "r_peak": bounds["r_peak"],
        "n_peak": bounds["n_peak"],
        "r_cond": r_cond,
        "n_cond": n_cond,
        "T_cond": T_cond,
        "n_model_norm": n_model_norm,
        "n_model_opt25": n_model_opt25,
        "A_fixed_25": A_fixed_25,
        "r2_score_opt25": r2_score_opt25,
        "rel_err_opt25": rel_err_opt25,
        "n_model_opt27": n_model_opt27,
        "A_fixed_27": A_fixed_27,
        "r2_score_opt27": r2_score_opt27,
        "rel_err_opt27": rel_err_opt27,
        "n_fit": n_fit,
        "T_model": T_model,
        "alpha_fit": alpha_fit,
        "A_fit": A_fit,
        "r2_score_norm": r2_score_norm,
        "rel_err_norm": rel_err_norm,
        "r2_score_fit": r2_score_fit,
        "rel_err_fit": rel_err_fit,
    }


def main():
    vtu_files = sorted(VTU_DIR.glob("test000[1-4].vtu"))
    results = [analyze_snapshot(f) for f in vtu_files]

    # Print summary table
    print(f"{'Snapshot':<12} {'Time [yr]':<12} {'Rt [pc]':<9} {'R2 [pc]':<9} {'n0 [cm^-3]':<11} {'Anchored 2/5 Err':<18} {'Opt 2/5 Err (R^2)':<20} {'Best alpha (Err)':<18}")
    print("-" * 115)
    for res in results:
        print(f"{res['snapshot']:<12} {res['time_yr']:<12,.0f} {res['rt']:<9.3f} {res['r2']:<9.3f} {res['n0']:<11.4f} "
              f"{res['rel_err_norm']:>5.1f}% (R^2={res['r2_score_norm']:>5.2f})    "
              f"{res['rel_err_opt25']:>5.1f}% (R^2={res['r2_score_opt25']:>5.2f})      "
              f"alpha={res['alpha_fit']:.2f} ({res['rel_err_fit']:.1f}%)")

    # Save CSV
    with open(OUT_CSV, "w") as f:
        f.write("# Purpose: Quantitative metrics for Weaver conduction front (1-r/R2)^(-2/5) fit across snapshots\n")
        f.write("snapshot,time_years,Rt_pc,R2_pc,n0_cm3,T0_K,alpha_best_fit,rel_err_best_fit,rel_err_anchored_2_5,R2_anchored_2_5,A_opt_2_5,rel_err_opt_2_5,R2_opt_2_5,A_opt_2_7,rel_err_opt_2_7,R2_opt_2_7\n")
        for res in results:
            f.write(
                f"{res['snapshot']},{res['time_yr']:.1f},{res['rt']:.4f},{res['r2']:.4f},"
                f"{res['n0']:.4e},{res['t0']:.4e},{res['alpha_fit']:.4f},{res['rel_err_fit']:.2f},"
                f"{res['rel_err_norm']:.2f},{res['r2_score_norm']:.4f},"
                f"{res['A_fixed_25']:.4e},{res['rel_err_opt25']:.2f},{res['r2_score_opt25']:.4f},"
                f"{res['A_fixed_27']:.4e},{res['rel_err_opt27']:.2f},{res['r2_score_opt27']:.4f}\n"
            )
    print(f"Metrics saved to {OUT_CSV}")

    # Generate multi-panel figure
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    colors = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd"]

    for idx, (res, col) in enumerate(zip(results, colors)):
        ax = axes.flat[idx]
        r = res["r_cond"]
        n_sim = res["n_cond"]
        n_mod_norm = res["n_model_norm"]
        n_mod_opt25 = res["n_model_opt25"]
        n_fit = res["n_fit"]

        # Plot simulation data points
        ax.plot(r, n_sim, "o-", color=col, lw=2.2, ms=5, label=f"Simulation ({res['time_yr']:,.0f} yr)")

        # Plot Weaver 2/5 model anchored to n0
        ax.plot(
            r,
            n_mod_norm,
            "--",
            color="black",
            lw=2.0,
            label=rf"Weaver $(1 - r/R_2)^{{-2/5}}$ (anchored to $n_0$, err={res['rel_err_norm']:.1f}%)",
        )

        # Plot Weaver 2/5 model with optimal amplitude
        ax.plot(
            r,
            n_mod_opt25,
            "-.",
            color="#e377c2",
            lw=1.8,
            label=rf"Weaver $(1 - r/R_2)^{{-2/5}}$ (opt $A={res['A_fixed_25']:.2f}$, err={res['rel_err_opt25']:.1f}%)",
        )

        # Plot best-fit power law
        ax.plot(
            r,
            n_fit,
            ":",
            color="#17becf",
            lw=2.0,
            label=rf"Best-fit $(1 - r/R_2)^{{-\alpha}}$ ($\alpha={res['alpha_fit']:.2f}$, err={res['rel_err_fit']:.1f}%)",
        )

        # Annotations
        ax.axvline(res["rt"], color="blue", ls=":", alpha=0.6, label=f"$R_t = {res['rt']:.2f}$ pc (shock)")
        ax.axvline(res["r2"], color="red", ls=":", alpha=0.6, label=f"$R_2 = {res['r2']:.2f}$ pc (wall start)")

        ax.set_yscale("log")
        ax.set_xlabel("Radius $r$ [pc]", fontsize=11)
        ax.set_ylabel("Number Density $n$ [cm$^{-3}$]", fontsize=11)
        ax.set_title(
            f"{res['snapshot']} ($t = {res['time_yr']:,.0f}$ yr) | $R_t={res['rt']:.2f}$ pc, $R_2={res['r2']:.2f}$ pc\n"
            f"Anchored 2/5 Err = {res['rel_err_norm']:.1f}% | Opt 2/5 Err = {res['rel_err_opt25']:.1f}% | Best $\\alpha = {res['alpha_fit']:.2f}$",
            fontsize=12,
            fontweight="bold",
        )
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(loc="upper left", fontsize=8.5, framealpha=0.92)

    fig.suptitle(
        r"Testing Conduction Front Parameterization: $\rho(r) \propto \rho_0 (1 - r/R_2)^{-2/5}$ Across Snapshots" + "\n"
        r"$\rho_0 \equiv \rho(R_t^+)$ (Post-Shock Density), $R_2 \equiv$ Radius Where Dense Swept-up Wall Starts",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(OUT_IMG, dpi=200)
    print(f"Saved figure to {OUT_IMG}")


if __name__ == "__main__":
    main()
