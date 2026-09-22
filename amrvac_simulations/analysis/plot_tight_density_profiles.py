#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import struct
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PC_CM = 3.0857e18
CAMPAIGN = Path(__file__).resolve().parent
PLOT_DIR = CAMPAIGN / "plots"
PLOT_DIR.mkdir(exist_ok=True)

REPO_ROOT = CAMPAIGN.parents[3]
VEGAS_JETFIT = REPO_ROOT / "VegasJetFit"
if str(VEGAS_JETFIT) not in sys.path:
    sys.path.insert(0, str(VEGAS_JETFIT))

from jetfit.models.empiricalBubbleProfile import empirical_number_density_cm3, simple_bubble_outer_radius_cm

# Empirical first-shock position model from all 12 tight-inner runs.
# log10(x_ts) = a0 + a1*dp + a2*dn + a3*dp*dn + a4*dp^2 + a5*dn^2 + a6*dp^2*dn + a7*dp*dn^2,
# where x_ts = r_ts,real / R_t_external and ambient density is rho_ism = 10^n.
TS_P0 = 5.0
TS_N0 = -21.5
TS_A0 = -0.32081197
TS_A1 = -0.03118870
TS_A2 = -0.03646271
TS_A3 = +0.07928646
TS_A4 = +0.01120312
TS_A5 = -0.00488433
TS_A6 = -0.09371896
TS_A7 = +0.06063005


def read_plan() -> dict[str, dict[str, float]]:
    rows = {}
    with (CAMPAIGN / "log_grid_plan.csv").open(newline="") as fh:
        for row in csv.DictReader(fh):
            rows[row["run_id"]] = {k: float(v) if k != "run_id" else v for k, v in row.items()}
    return rows


def read_vtu(path: Path) -> tuple[np.ndarray, np.ndarray, float]:
    raw = path.read_bytes()
    app_start = raw.find(b"<AppendedData")
    data_start = raw.find(b"_", app_start) + 1
    data_end = raw.find(b"</AppendedData>", data_start)
    header = raw[:app_start].decode("ascii", "ignore")
    appended = raw[data_start:data_end]

    tm = re.search(r'<DataArray type="Float32" Name="TIME"[^>]*>\s*([0-9.E+-]+)', header)
    time_s = float(tm.group(1)) if tm else np.nan

    xs: list[float] = []
    rhos: list[float] = []
    for piece in re.finditer(r'<Piece NumberOfPoints="\s*(\d+)" NumberOfCells="\s*(\d+)">(.*?)</Piece>', header, re.S):
        body = piece.group(3)
        rho_m = re.search(r'<DataArray[^>]*Name="rho"[^>]*offset="(\d+)"', body)
        pts_m = re.search(r'<Points>\s*<DataArray[^>]*offset="(\d+)"', body, re.S)
        if not rho_m or not pts_m:
            continue
        rho_off = int(rho_m.group(1))
        pts_off = int(pts_m.group(1))
        rho_len = struct.unpack_from("<I", appended, rho_off)[0]
        pts_len = struct.unpack_from("<I", appended, pts_off)[0]
        rho = np.frombuffer(appended, dtype="<f4", count=rho_len // 4, offset=rho_off + 4).copy()
        pts = np.frombuffer(appended, dtype="<f4", count=pts_len // 4, offset=pts_off + 4).reshape(-1, 3).copy()
        xs.extend(pts[:, 0])
        rhos.extend(rho)

    arr = np.array(list(zip(xs, rhos)), dtype=float)
    arr = arr[np.argsort(arr[:, 0])]
    # AMRVAC pieces share boundary nodes; collapse duplicate radii by median rho.
    rounded = np.round(arr[:, 0] / PC_CM, 12)
    uniq = []
    for val in np.unique(rounded):
        mask = rounded == val
        uniq.append((np.median(arr[mask, 0]) / PC_CM, np.median(arr[mask, 1])))
    out = np.array(uniq)
    return out[:, 0], out[:, 1], time_s


def final_file(run_id: str) -> Path:
    files = sorted((CAMPAIGN / f"pressure_{run_id}" / "output" / "Ostar_1D").glob("test*.vtu"))
    if not files:
        raise FileNotFoundError(run_id)
    return files[-1]


def all_run_ids(plan: dict[str, dict[str, float]]) -> list[str]:
    return sorted(plan, key=lambda r: (int(r[1]), int(r.split("_n")[1])))


def predicted_initial_shock_x(run_id: str) -> float:
    p = float(int(run_id[1]))
    n = -float(int(run_id.split("_n")[1]))
    dp = p - TS_P0
    dn = n - TS_N0
    log10_x = (
        TS_A0
        + TS_A1 * dp
        + TS_A2 * dn
        + TS_A3 * dp * dn
        + TS_A4 * dp**2
        + TS_A5 * dn**2
        + TS_A6 * dp**2 * dn
        + TS_A7 * dp * dn**2
    )
    return float(10.0 ** log10_x)


def infer_nt_at_rt(radius_pc: np.ndarray, rho_g_cm3: np.ndarray, rt_pc: float) -> float:
    rt_cm = rt_pc * PC_CM
    if rt_cm <= 0.0:
        return 1e-300
    inner_mask = (radius_pc > 0.0) & (radius_pc < 0.95 * rt_pc)
    if np.count_nonzero(inner_mask) < 5:
        inner_mask = (radius_pc > 0.0) & (radius_pc < rt_pc)
    if np.count_nonzero(inner_mask) == 0:
        inner_mask = radius_pc > 0.0

    wind_norm = np.median(rho_g_cm3[inner_mask] * (radius_pc[inner_mask] * PC_CM) ** 2)
    nt = wind_norm / (rt_cm**2)
    return float(max(nt, 1e-300))


def empirical_mass_density_profile(radius_pc: np.ndarray, rho_g_cm3: np.ndarray, rt_pc: float, rho_ism_g_cm3: float) -> np.ndarray:
    rt_cm = rt_pc * PC_CM
    nt_g_cm3 = infer_nt_at_rt(radius_pc, rho_g_cm3, rt_pc)
    r2_cm = simple_bubble_outer_radius_cm(rt_cm, nt_g_cm3, rho_ism_g_cm3)
    return empirical_number_density_cm3(
        radius_cm=radius_pc * PC_CM,
        rt_cm=rt_cm,
        nt_cm3=nt_g_cm3,
        nism_cm3=rho_ism_g_cm3,
        r2_cm=r2_cm,
    )


def plot_final_by_pressure(plan: dict[str, dict[str, float]]) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(9, 11), sharex=False, constrained_layout=True)
    pressures = [4, 5, 6]
    colors = plt.cm.viridis(np.linspace(0.15, 0.9, 4))
    for ax, p in zip(axes, pressures):
        runs = [r for r in all_run_ids(plan) if r.startswith(f"p{p}_")]
        for color, run in zip(colors, runs):
            x, rho, _ = read_vtu(final_file(run))
            row = plan[run]
            ax.plot(x, rho, lw=1.8, color=color, label=run)
            ax.axvline(row["rt_external_pc"], color=color, ls=":", alpha=0.35)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylabel(r"$\rho$ [g cm$^{-3}$]")
        ax.set_title(rf"Final profiles, pressure $P/k=10^{p}$ K cm$^{{-3}}$; dotted lines mark $R_t$")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(ncol=4, fontsize=8)
    axes[-1].set_xlabel("r [pc]")
    out = PLOT_DIR / "tight_inner_final_density_by_pressure.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_normalized(plan: dict[str, dict[str, float]], include_empirical: bool = True) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    empirical_label_used = False
    shock_label_used = False
    for run in all_run_ids(plan):
        x, rho, _ = read_vtu(final_file(run))
        row = plan[run]
        xnorm = x / row["rt_external_pc"]
        ynorm = rho / row["rho_g_cm3"]
        valid = np.isfinite(xnorm) & np.isfinite(ynorm) & (xnorm > 0.0) & (ynorm > 0.0)
        if np.count_nonzero(valid) < 3:
            continue
        xplot = xnorm[valid]
        yplot = ynorm[valid]

        base = ax.plot(xplot, yplot, lw=1.4, label=run)
        color = base[0].get_color()

        if include_empirical:
            empirical_rho = empirical_mass_density_profile(
                radius_pc=x,
                rho_g_cm3=rho,
                rt_pc=row["rt_external_pc"],
                rho_ism_g_cm3=row["rho_g_cm3"],
            )
            ax.plot(
                xplot,
                (empirical_rho / row["rho_g_cm3"])[valid],
                lw=1.05,
                ls="--",
                color=color,
                alpha=0.9,
                label="empirical bubble" if not empirical_label_used else None,
            )
            empirical_label_used = True
        ax.axvline(
            predicted_initial_shock_x(run),
            lw=1.0,
            ls=":",
            color=color,
            alpha=0.75,
            label=r"predicted initial shock" if not shock_label_used else None,
        )
        shock_label_used = True
    ax.axvline(1.0, color="k", lw=1, ls=":", label=r"$R_t$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$r/R_t$")
    ax.set_ylabel(r"$\rho/\rho_{ISM}$")
    if include_empirical:
        ax.set_title("Final tight-inner profiles (solid: AMRVAC, dashed: empirical bubble, dotted: predicted initial shock)")
    else:
        ax.set_title("Final tight-inner profiles (solid: AMRVAC, dotted: predicted initial shock)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(ncol=4, fontsize=8)
    if include_empirical:
        out = PLOT_DIR / "tight_inner_final_density_normalized_rt_with_predicted_shock.png"
    else:
        out = PLOT_DIR / "tight_inner_final_density_normalized_rt_with_predicted_shock_no_empirical.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_time_evolution(plan: dict[str, dict[str, float]]) -> Path:
    runs = ["p4_n21", "p4_n24", "p5_n20", "p5_n23", "p6_n19", "p6_n22"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), constrained_layout=True)
    for ax, run in zip(axes.flat, runs):
        files = sorted((CAMPAIGN / f"pressure_{run}" / "output" / "Ostar_1D").glob("test*.vtu"))
        for f in files:
            x, rho, t_s = read_vtu(f)
            t_code = t_s / 3.08570010e11 if np.isfinite(t_s) else np.nan
            ax.plot(x, rho, lw=1.0, label=f"t={t_code:.2g}")
        ax.axvline(plan[run]["rt_external_pc"], color="k", ls=":", lw=1)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(run)
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=7)
    for ax in axes[:, 0]:
        ax.set_ylabel(r"$\rho$ [g cm$^{-3}$]")
    for ax in axes[-1, :]:
        ax.set_xlabel("r [pc]")
    out = PLOT_DIR / "tight_inner_density_time_evolution_examples.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def main() -> None:
    plan = read_plan()
    outs = [
        plot_final_by_pressure(plan),
        plot_normalized(plan, include_empirical=True),
        plot_normalized(plan, include_empirical=False),
        plot_time_evolution(plan),
    ]
    for out in outs:
        print(out)


if __name__ == "__main__":
    main()
