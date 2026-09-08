#!/usr/bin/env python3
"""
Plot an AMRVAC density profile together with the simple bubble and the current
three-parameter empirical bubble implementation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analyze_amrvac_bubble_profiles import PC_TO_CM, TINY, bubble_number_density, read_vtu_snapshot
from compare_empirical_cavity_model import find_profile_rises, infer_nism_from_run_name, infer_nt_from_inner_wind
from jetfit.models.empiricalBubbleProfile import empirical_number_density_cm3, simple_bubble_outer_radius_cm


def rms_dex(model_n: np.ndarray, data_n: np.ndarray) -> float:
    return float(
        np.sqrt(
            np.mean(
                (np.log10(np.maximum(model_n, TINY)) - np.log10(np.maximum(data_n, TINY))) ** 2
            )
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vtu",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2025_08_07/density_21/output/Ostar_1D/test0010.vtu",
        help="AMRVAC VTU file to compare.",
    )
    parser.add_argument(
        "--output",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/empirical_bubble_note/figures/07_density21_simple_vs_empirical_bubble.png",
        help="Output plot path.",
    )
    args = parser.parse_args()

    vtu_path = Path(args.vtu)
    run_name = vtu_path.parents[2].name
    snapshot = read_vtu_snapshot(vtu_path)

    radius_cm = snapshot.radius_cm
    radius_pc = radius_cm / PC_TO_CM
    number_density_cm3 = np.maximum(snapshot.number_density_cm3, TINY)

    rt_pc, _ = find_profile_rises(radius_pc, number_density_cm3)
    nt_cm3 = infer_nt_from_inner_wind(radius_cm, radius_pc, number_density_cm3, rt_pc)
    nism_cm3 = infer_nism_from_run_name(run_name)

    simple = bubble_number_density(radius_cm, rt_pc * PC_TO_CM, nt_cm3, nism_cm3)
    r2_cm = simple_bubble_outer_radius_cm(rt_pc * PC_TO_CM, nt_cm3, nism_cm3)
    r2_simple_pc = r2_cm / PC_TO_CM
    empirical = empirical_number_density_cm3(
        radius_cm=radius_cm,
        rt_cm=rt_pc * PC_TO_CM,
        nt_cm3=nt_cm3,
        nism_cm3=nism_cm3,
        r2_cm=r2_cm,
    )

    simple_rms = rms_dex(simple, number_density_cm3)
    empirical_rms = rms_dex(empirical, number_density_cm3)

    fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=220)
    ax.loglog(radius_pc, number_density_cm3, lw=2.3, label=f"{run_name} AMRVAC")
    ax.loglog(radius_pc, simple, "--", lw=1.8, label="simple bubble")
    ax.loglog(radius_pc, empirical, ":", lw=2.5, label="empirical bubble")
    ax.axvline(rt_pc, color="0.35", ls=":", lw=1.0, label=fr"$R_t$ = {rt_pc:.3f} pc")
    ax.axvline(r2_simple_pc, color="0.55", ls="--", lw=1.0, label=fr"$R_2$ = {r2_simple_pc:.3f} pc")
    ax.set_xlabel("Radius (pc)")
    ax.set_ylabel(r"n(r) [cm$^{-3}$]")
    ax.set_title(f"{run_name}: AMRVAC vs simple bubble vs empirical bubble")
    ax.set_xlim(0.12, float(radius_pc.max()) * 1.22)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8, ncol=2)

    text = "\n".join(
        [
            fr"$n_{{ism}}$ = {nism_cm3:.1f} cm$^{{-3}}$",
            fr"$R_t$ = {rt_pc:.3f} pc, $n_t$ = {nt_cm3:.3f} cm$^{{-3}}$",
            fr"simple RMS = {simple_rms:.3f} dex",
            fr"empirical RMS = {empirical_rms:.3f} dex",
            r"empirical uses the adopted $\mathrm{density\_21}$ $\psi(x)$ template",
        ]
    )
    ax.text(
        0.03,
        0.03,
        text,
        transform=ax.transAxes,
        fontsize=8.5,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.88, edgecolor="0.7"),
    )

    fig.tight_layout()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")

    print(output_path)
    print(f"run={run_name}")
    print(f"rt_pc={rt_pc:.6f}")
    print(f"nt_cm3={nt_cm3:.6f}")
    print(f"nism_cm3={nism_cm3:.6f}")
    print(f"r2_simple_pc={r2_simple_pc:.6f}")
    print(f"r2_empirical_pc={r2_simple_pc:.6f}")
    print(f"simple_rms={simple_rms:.6f}")
    print(f"empirical_rms={empirical_rms:.6f}")


if __name__ == "__main__":
    main()
