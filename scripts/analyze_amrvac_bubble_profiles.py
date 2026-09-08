#!/usr/bin/env python3
"""
Extract 1D AMRVAC density profiles and compare them to the simple bubble
surrogate used by BubbleVegasModel.

This script avoids a vtk dependency by parsing VTK XML files with raw appended
binary payloads directly.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from glob import glob
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares


MU = 1.3
M_P = 1.67262192369e-24
KB_CGS = 1.380649e-16
SECONDS_PER_YEAR = 365.25 * 86400.0
M_MOL = MU * M_P
PC_TO_CM = 3.086e18
TINY = 1e-300


@dataclass
class VtuSnapshot:
    path: Path
    time_code: float
    radius_cm: np.ndarray
    rho_g_cm3: np.ndarray

    @property
    def number_density_cm3(self) -> np.ndarray:
        return self.rho_g_cm3 / M_MOL


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


def _extract_xml_and_raw(path: Path) -> tuple[ET.Element, bytes]:
    data = path.read_bytes()
    start = data.index(b"<AppendedData")
    open_end = data.index(b">", start)
    close = data.index(b"</AppendedData>", open_end)
    appended = data[open_end + 1 : close]
    underscore = appended.index(b"_")
    raw = appended[underscore + 1 :]
    xml_bytes = data[: open_end + 1] + b"_" + data[close:]
    root = ET.fromstring(xml_bytes)
    return root, raw


def _read_appended_array(raw: bytes, data_array: ET.Element) -> np.ndarray:
    offset = int(data_array.attrib["offset"])
    nbytes = struct.unpack("<I", raw[offset : offset + 4])[0]
    dtype = vtk_dtype(data_array.attrib["type"])
    payload = raw[offset + 4 : offset + 4 + nbytes]
    array = np.frombuffer(payload, dtype=dtype)
    ncomp = int(data_array.attrib.get("NumberOfComponents", "1"))
    if ncomp > 1:
        array = array.reshape(-1, ncomp)
    return array


def _dedupe_sorted(radius_cm: np.ndarray, rho_g_cm3: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(radius_cm)
    radius_cm = radius_cm[order]
    rho_g_cm3 = rho_g_cm3[order]

    unique_r = [radius_cm[0]]
    unique_rho = [rho_g_cm3[0]]
    counts = [1]

    for r, rho in zip(radius_cm[1:], rho_g_cm3[1:]):
        if r == unique_r[-1]:
            unique_rho[-1] += rho
            counts[-1] += 1
        else:
            unique_r.append(r)
            unique_rho.append(rho)
            counts.append(1)

    unique_r = np.asarray(unique_r, dtype=float)
    unique_rho = np.asarray(unique_rho, dtype=float) / np.asarray(counts, dtype=float)
    return unique_r, unique_rho


def read_vtu_snapshot(path: Path) -> VtuSnapshot:
    root, raw = _extract_xml_and_raw(path)

    time_elem = root.find(".//FieldData/DataArray[@Name='TIME']")
    if time_elem is None or time_elem.text is None:
        raise ValueError(f"TIME field missing from {path}")
    time_code = float(time_elem.text.strip())

    radius_chunks = []
    rho_chunks = []
    for piece in root.findall(".//Piece"):
        point_r = _read_appended_array(raw, piece.find("./Points/DataArray"))
        rho_array = piece.find("./PointData/DataArray[@Name='rho']")
        if rho_array is None:
            raise ValueError(f"rho array missing from {path}")
        rho = _read_appended_array(raw, rho_array)
        radius_chunks.append(np.asarray(point_r[:, 0], dtype=float))
        rho_chunks.append(np.asarray(rho, dtype=float))

    radius_cm = np.concatenate(radius_chunks)
    rho_g_cm3 = np.concatenate(rho_chunks)
    radius_cm, rho_g_cm3 = _dedupe_sorted(radius_cm, rho_g_cm3)
    valid = np.isfinite(radius_cm) & np.isfinite(rho_g_cm3) & (radius_cm > 0.0) & (rho_g_cm3 > 0.0)
    radius_cm = radius_cm[valid]
    rho_g_cm3 = rho_g_cm3[valid]
    return VtuSnapshot(path=path, time_code=time_code, radius_cm=radius_cm, rho_g_cm3=rho_g_cm3)


def _extract_literal(text: str, name: str) -> float:
    import re

    pattern = rf"{name}\s*=\s*([0-9.+\-DdEe*()/ ]+)"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Could not find {name} in mod_usr.t")
    expr = match.group(1).replace("D", "e").replace("d", "e")
    return float(eval(expr, {"__builtins__": {}}, {"kb_cgs": KB_CGS, "mp_cgs": M_P}))


def code_unit_years_from_modusr(mod_usr_path: Path) -> float:
    text = mod_usr_path.read_text()
    if "time_convert_factor" in text:
        unit_length = _extract_literal(text, "unit_length")
        momentum_scale = _extract_literal(text, "w_convert_factor\\(mom\\(1\\)\\)")
        return (unit_length / momentum_scale) / SECONDS_PER_YEAR

    unit_length = _extract_literal(text, "unit_length")
    unit_temperature = _extract_literal(text, "unit_temperature")
    unit_numberdensity = _extract_literal(text, "unit_numberdensity")
    unit_density = M_P * unit_numberdensity
    unit_pressure = 2.0 * unit_numberdensity * KB_CGS * unit_temperature
    unit_velocity = math.sqrt(unit_pressure / unit_density)
    unit_time_s = unit_length / unit_velocity
    return unit_time_s / SECONDS_PER_YEAR


def bubble_shell_radius(rt_cm: float, nt_cm3: float, nism_cm3: float) -> tuple[float, float]:
    n_sh = 4.0 * nt_cm3
    n_sh_old = max(4.0 * nt_cm3, 4.0 * nism_cm3)
    denom_old = max(n_sh_old - nism_cm3, TINY)
    ratio_old = (n_sh_old + 3.0 * nt_cm3) / denom_old
    r2_old = rt_cm * max(ratio_old, 1.0 + 1e-12) ** (1.0 / 3.0)
    delta_old = max(r2_old**3 - rt_cm**3, 0.0)
    r2_cubed = rt_cm**3 + (n_sh_old / max(n_sh, TINY)) * delta_old
    r2_cm = max(r2_cubed, rt_cm**3 * (1.0 + 1e-12)) ** (1.0 / 3.0)
    return n_sh, r2_cm


def bubble_number_density(radius_cm: np.ndarray, rt_cm: float, nt_cm3: float, nism_cm3: float) -> np.ndarray:
    n_sh, r2_cm = bubble_shell_radius(rt_cm, nt_cm3, nism_cm3)
    radius_cm = np.asarray(radius_cm, dtype=float)
    radius_safe = np.maximum(radius_cm, 1.0)
    return np.where(
        radius_safe < rt_cm,
        nt_cm3 * (rt_cm / radius_safe) ** 2,
        np.where(radius_safe < r2_cm, n_sh, nism_cm3),
    )


def estimate_initial_guess(radius_cm: np.ndarray, number_density_cm3: np.ndarray) -> np.ndarray:
    n_points = len(radius_cm)
    inner_count = max(8, int(0.15 * n_points))
    outer_count = max(8, int(0.15 * n_points))

    inner_r = radius_cm[:inner_count]
    inner_n = np.maximum(number_density_cm3[:inner_count], TINY)
    outer_n = np.maximum(number_density_cm3[-outer_count:], TINY)

    wind_norm = np.median(inner_n * inner_r**2)
    log_radius = np.log10(radius_cm)
    log_density = np.log10(np.maximum(number_density_cm3, TINY))
    slope = np.gradient(log_density, log_radius)
    ratio_to_wind = np.maximum(number_density_cm3, TINY) * radius_cm**2 / max(wind_norm, TINY)

    candidate = np.where((ratio_to_wind > 1.7) & (slope > -1.5))[0]
    if candidate.size:
        rt_idx = int(candidate[0])
    else:
        rt_idx = int(np.argmax(ratio_to_wind))

    rt_cm = float(np.clip(radius_cm[rt_idx], radius_cm[1], radius_cm[-2]))
    nt_cm3 = float(max(wind_norm / max(rt_cm**2, TINY), TINY))
    nism_cm3 = float(max(np.median(outer_n), TINY))
    return np.log10([rt_cm, nt_cm3, nism_cm3])


def fit_simple_bubble(snapshot: VtuSnapshot, code_unit_years: float) -> dict[str, float]:
    radius_cm = snapshot.radius_cm
    number_density_cm3 = np.maximum(snapshot.number_density_cm3, TINY)

    guess = estimate_initial_guess(radius_cm, number_density_cm3)
    lower = np.log10(
        [
            radius_cm.min() * 1.001,
            max(number_density_cm3.min() / 1e3, 1e-12),
            max(number_density_cm3.min() / 1e3, 1e-12),
        ]
    )
    upper = np.log10(
        [
            radius_cm.max() / 1.001,
            max(number_density_cm3.max() * 1e3, 1e-6),
            max(number_density_cm3.max() * 1e3, 1e-6),
        ]
    )

    def residual(log_params: np.ndarray) -> np.ndarray:
        rt_cm, nt_cm3, nism_cm3 = 10.0 ** log_params
        model_n = bubble_number_density(radius_cm, rt_cm, nt_cm3, nism_cm3)
        return np.log10(np.maximum(model_n, TINY)) - np.log10(number_density_cm3)

    result = least_squares(
        residual,
        x0=np.clip(guess, lower, upper),
        bounds=(lower, upper),
        loss="soft_l1",
        f_scale=0.1,
        max_nfev=2000,
    )

    rt_cm, nt_cm3, nism_cm3 = 10.0 ** result.x
    n_sh, r2_cm = bubble_shell_radius(rt_cm, nt_cm3, nism_cm3)
    resid = residual(result.x)

    return {
        "time_code": snapshot.time_code,
        "time_yr": snapshot.time_code * code_unit_years,
        "n_points": len(radius_cm),
        "rt_cm": rt_cm,
        "rt_pc": rt_cm / PC_TO_CM,
        "nt_cm3": nt_cm3,
        "nism_cm3": nism_cm3,
        "nsh_cm3": n_sh,
        "r2_cm": r2_cm,
        "r2_rt": r2_cm / rt_cm,
        "q_nism_over_nt": nism_cm3 / nt_cm3,
        "rms_dex": float(np.sqrt(np.mean(resid**2))),
        "max_abs_dex": float(np.max(np.abs(resid))),
        "success": bool(result.success),
        "cost": float(result.cost),
        "nfev": int(result.nfev),
    }


def collect_family_snapshots(family_dir: Path, min_snapshots: int) -> tuple[list[VtuSnapshot], list[str]]:
    snapshots = []
    skipped = []
    for run_dir in sorted(p for p in family_dir.glob("density_*") if p.is_dir()):
        vtus = sorted(run_dir.glob("output/Ostar_1D/test*.vtu"))
        if len(vtus) < min_snapshots:
            skipped.append(f"{run_dir.name}: only {len(vtus)} snapshots")
            continue
        snapshots.append(read_vtu_snapshot(vtus[-1]))
    return snapshots, skipped


def plot_profiles(snapshots: list[VtuSnapshot], fits: dict[str, dict[str, float]], output_dir: Path) -> None:
    raw_path = output_dir / "raw_profiles.png"
    fit_path = output_dir / "simple_bubble_fits.png"
    scaled_path = output_dir / "scaled_profiles.png"

    plt.figure(figsize=(8, 6))
    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        plt.loglog(snapshot.radius_cm / PC_TO_CM, snapshot.number_density_cm3, lw=1.5, label=label)
    plt.xlabel("Radius (pc)")
    plt.ylabel(r"n(r) [cm$^{-3}$]")
    plt.title("AMRVAC Final Density Profiles")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(raw_path, dpi=220)
    plt.close()

    plt.figure(figsize=(8, 6))
    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        fit = fits[label]
        model_n = bubble_number_density(snapshot.radius_cm, fit["rt_cm"], fit["nt_cm3"], fit["nism_cm3"])
        plt.loglog(snapshot.radius_cm / PC_TO_CM, snapshot.number_density_cm3, lw=1.2, alpha=0.65, label=f"{label} AMRVAC")
        plt.loglog(snapshot.radius_cm / PC_TO_CM, model_n, "--", lw=1.2, alpha=0.95, label=f"{label} simple bubble")
    plt.xlabel("Radius (pc)")
    plt.ylabel(r"n(r) [cm$^{-3}$]")
    plt.title("AMRVAC vs Simple Bubble Fits")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(fit_path, dpi=220)
    plt.close()

    plt.figure(figsize=(8, 6))
    x_grid = np.logspace(-0.4, 1.0, 400)
    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        fit = fits[label]
        x = snapshot.radius_cm / fit["rt_cm"]
        y = snapshot.number_density_cm3 / fit["nt_cm3"]
        model_y = bubble_number_density(x_grid * fit["rt_cm"], fit["rt_cm"], fit["nt_cm3"], fit["nism_cm3"]) / fit["nt_cm3"]
        plt.loglog(x, y, lw=1.2, alpha=0.65, label=f"{label} AMRVAC")
        plt.loglog(x_grid, model_y, "--", lw=1.2, alpha=0.95, label=f"{label} simple bubble")
    plt.xlabel(r"$r / r_t$")
    plt.ylabel(r"$n(r) / n_t$")
    plt.title("Scaled Profile Collapse")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(scaled_path, dpi=220)
    plt.close()


def write_summary_csv(rows: list[dict[str, float]], output_path: Path) -> None:
    fieldnames = [
        "run",
        "snapshot",
        "time_code",
        "time_yr",
        "n_points",
        "rt_cm",
        "rt_pc",
        "nt_cm3",
        "nism_cm3",
        "nsh_cm3",
        "r2_cm",
        "r2_rt",
        "q_nism_over_nt",
        "rms_dex",
        "max_abs_dex",
        "success",
        "cost",
        "nfev",
    ]
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_collapse(snapshots: list[VtuSnapshot], fits: dict[str, dict[str, float]]) -> tuple[float, float]:
    x_grid = np.logspace(-0.3, 0.8, 250)
    curves = []
    for snapshot in snapshots:
        label = snapshot.path.parents[2].name
        fit = fits[label]
        x = snapshot.radius_cm / fit["rt_cm"]
        y = snapshot.number_density_cm3 / fit["nt_cm3"]
        interp = np.interp(
            np.log10(x_grid),
            np.log10(x),
            np.log10(np.maximum(y, TINY)),
            left=np.nan,
            right=np.nan,
        )
        curves.append(interp)
    curve_stack = np.asarray(curves)
    spread = np.nanstd(curve_stack, axis=0)
    return float(np.nanmedian(spread)), float(np.nanmax(spread))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family-dir",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2025_08_07",
        help="Directory containing density_* AMRVAC runs.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_bubble_surrogate",
        help="Directory for CSV and plot outputs.",
    )
    parser.add_argument(
        "--min-snapshots",
        type=int,
        default=5,
        help="Ignore runs with fewer than this many VTU snapshots.",
    )
    parser.add_argument(
        "--mod-usr",
        default=None,
        help="Path to mod_usr.t used to convert AMRVAC code time to physical years. Defaults to <family-dir>/Template/mod_usr.t",
    )
    args = parser.parse_args()

    family_dir = Path(args.family_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    mod_usr_path = Path(args.mod_usr) if args.mod_usr else family_dir / "Template" / "mod_usr.t"
    code_unit_years = code_unit_years_from_modusr(mod_usr_path)

    snapshots, skipped = collect_family_snapshots(family_dir, args.min_snapshots)
    if not snapshots:
        raise SystemExit("No AMRVAC snapshots found after filtering.")

    rows = []
    fits = {}
    for snapshot in snapshots:
        run_name = snapshot.path.parents[2].name
        fit = fit_simple_bubble(snapshot, code_unit_years)
        fits[run_name] = fit
        rows.append(
            {
                "run": run_name,
                "snapshot": snapshot.path.name,
                **fit,
            }
        )

    write_summary_csv(rows, output_dir / "amrvac_simple_bubble_fit_summary.csv")
    plot_profiles(snapshots, fits, output_dir)

    median_spread_dex, max_spread_dex = summarize_collapse(snapshots, fits)
    notes_path = output_dir / "analysis_notes.txt"
    with notes_path.open("w") as handle:
        if skipped:
            handle.write("Skipped runs:\n")
            for item in skipped:
                handle.write(f"- {item}\n")
            handle.write("\n")
        handle.write(f"Included runs: {len(snapshots)}\n")
        handle.write(f"AMRVAC code time unit (yr): {code_unit_years:.6f}\n")
        handle.write(f"Median scaled-profile spread (dex): {median_spread_dex:.4f}\n")
        handle.write(f"Max scaled-profile spread (dex): {max_spread_dex:.4f}\n")

    print(f"Wrote summary CSV to {output_dir / 'amrvac_simple_bubble_fit_summary.csv'}")
    print(f"Wrote plots to {output_dir}")
    if skipped:
        print("Skipped:")
        for item in skipped:
            print(f"  - {item}")
    print(f"Median scaled-profile spread (dex): {median_spread_dex:.4f}")
    print(f"Max scaled-profile spread (dex): {max_spread_dex:.4f}")


if __name__ == "__main__":
    main()
