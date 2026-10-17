# Purpose: Plot 1D radial profiles (density, temperature, velocity, pressure)
# from the 1 Myr Wolf-Rayet wind bubble simulation snapshots (f_production_1myr).

import os
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
VTU_DIR = HERE / "f_production_1myr" / "output"
OUT_IMG = HERE / "f_production_1myr_profiles.png"

# AMRVAC unit conversion factors from mod_usr.t
UNIT_LENGTH = 3.0857e18       # 1 pc in cm
UNIT_DENSITY = 1.0e-25        # g cm^-3
UNIT_VELOCITY = 1.0e7         # 100 km/s in cm/s
UNIT_PRESSURE = UNIT_DENSITY * UNIT_VELOCITY**2  # 1.0e-11 erg cm^-3
UNIT_TEMPERATURE = 7.37419685144625e5           # K
UNIT_TIME = UNIT_LENGTH / UNIT_VELOCITY          # 3.0857e11 s

# Particle mean molecular weight mu = 1.4 / 2.3 for fully ionized solar H+He
# ambient_rho = ambient_particles_cm3 * mp * (1 + 4*0.1)/(1 + 1 + 0.1*(1+2)) = n_total * mp * 1.4 / 2.3
M_P = 1.67262192369e-24
K_B = 1.380649e-16
MU_TOTAL = 1.4 / 2.3
M_PARTICLE = MU_TOTAL * M_P
YEAR_CODE = 3.1536e7 / UNIT_TIME


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


def extract_vtu_data(path: Path):
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
    time_years = time_code / 3.1536e7

    r_list, rho_list, v_list, p_list, t_list = [], [], [], [], []

    def read_arr(elem):
        offset = int(elem.attrib["offset"])
        nbytes = struct.unpack("<I", raw[offset : offset + 4])[0]
        dtype = vtk_dtype(elem.attrib["type"])
        payload = raw[offset + 4 : offset + 4 + nbytes]
        arr = np.frombuffer(payload, dtype=dtype)
        ncomp = int(elem.attrib.get("NumberOfComponents", "1"))
        if ncomp > 1:
            arr = arr.reshape(-1, ncomp)
        return arr

    for piece in root.findall(".//Piece"):
        pts = read_arr(piece.find("./Points/DataArray"))
        rho = read_arr(piece.find("./PointData/DataArray[@Name='rho']"))
        v1 = read_arr(piece.find("./PointData/DataArray[@Name='v1']"))
        p = read_arr(piece.find("./PointData/DataArray[@Name='p']"))
        temp = read_arr(piece.find("./PointData/DataArray[@Name='temperature_K']"))

        r_list.append(np.asarray(pts[:, 0], dtype=float))
        rho_list.append(np.asarray(rho, dtype=float))
        v_list.append(np.asarray(v1, dtype=float))
        p_list.append(np.asarray(p, dtype=float))
        t_list.append(np.asarray(temp, dtype=float))

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
        if r == unique_r[-1]:
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

    print(f"[{path.name}] t={time_years:.0f} yr | r=[{raw_r.min():.3e}, {raw_r.max():.3e}] | rho=[{raw_rho.min():.3e}, {raw_rho.max():.3e}] | v=[{raw_v.min():.3e}, {raw_v.max():.3e}] | p=[{raw_p.min():.3e}, {raw_p.max():.3e}] | T=[{raw_t.min():.3e}, {raw_t.max():.3e}]")

    # If raw_r > 1e15, r is in cm; otherwise code units (pc)
    r_pc = raw_r / UNIT_LENGTH if raw_r.max() > 100.0 else raw_r
    # If raw_rho < 1e-10, rho is already in g cm^-3 (cgs)
    rho_cgs = raw_rho if raw_rho.max() < 1e-10 else raw_rho * UNIT_DENSITY
    # If raw_v > 1e4, v is already in cm/s
    v_kms = raw_v / 1e5 if raw_v.max() > 1e3 else raw_v * (UNIT_VELOCITY / 1e5)
    # If raw_p < 1e-5, p is in dyn/cm^2
    p_cgs = raw_p if raw_p.max() < 1e-5 else raw_p * UNIT_PRESSURE
    t_k = raw_t

    n_cm3 = rho_cgs / M_PARTICLE
    p_over_k = p_cgs / K_B

    return {
        "time_years": time_years,
        "r_pc": r_pc,
        "n_cm3": n_cm3,
        "t_k": t_k,
        "v_kms": v_kms,
        "p_over_k": p_over_k,
    }


def main():
    vtu_files = sorted(VTU_DIR.glob("test*.vtu"))
    if not vtu_files:
        raise FileNotFoundError(f"No VTU files found in {VTU_DIR}")

    print(f"Found {len(vtu_files)} VTU snapshots:")
    for f in vtu_files:
        print(f"  {f.name}")

    snapshots = [extract_vtu_data(f) for f in vtu_files]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
    ax_n, ax_t = axes[0, 0], axes[0, 1]
    ax_v, ax_p = axes[1, 0], axes[1, 1]

    colors = plt.cm.viridis(np.linspace(0.1, 0.95, len(snapshots)))

    for snap, col in zip(snapshots, colors):
        label = f"{snap['time_years']:,.0f} yr"
        r = snap["r_pc"]

        ax_n.plot(r, snap["n_cm3"], label=label, color=col, lw=1.8)
        ax_t.plot(r, snap["t_k"], label=label, color=col, lw=1.8)
        ax_v.plot(r, snap["v_kms"], label=label, color=col, lw=1.8)
        ax_p.plot(r, snap["p_over_k"], label=label, color=col, lw=1.8)

    # Panel 1: Number Density
    ax_n.set_ylabel("Total Number Density $n$ [cm$^{-3}$]", fontsize=12)
    ax_n.set_yscale("log")
    ax_n.set_ylim(1e-4, 1e7)
    ax_n.axhline(1e4, color="gray", ls="--", alpha=0.5, label="Ambient $n=10^4$ cm$^{-3}$")
    ax_n.grid(True, which="both", alpha=0.3)
    ax_n.legend(loc="lower left", fontsize=9)
    ax_n.set_title("Density Profile $n(r)$", fontsize=13, fontweight="bold")

    # Panel 2: Temperature
    ax_t.set_ylabel("Temperature $T$ [K]", fontsize=12)
    ax_t.set_yscale("log")
    ax_t.set_ylim(50, 5e8)
    ax_t.axhline(100, color="gray", ls="--", alpha=0.5, label="Ambient Floor $T=100$ K")
    ax_t.grid(True, which="both", alpha=0.3)
    ax_t.legend(loc="lower left", fontsize=9)
    ax_t.set_title("Temperature Profile $T(r)$", fontsize=13, fontweight="bold")

    # Panel 3: Velocity
    ax_v.set_xlabel("Radius $r$ [pc]", fontsize=12)
    ax_v.set_ylabel("Radial Velocity $v_r$ [km/s]", fontsize=12)
    ax_v.set_ylim(-50, 2200)
    ax_v.axhline(2000, color="gray", ls="--", alpha=0.5, label="Wind $v_w=2000$ km/s")
    ax_v.grid(True, which="both", alpha=0.3)
    ax_v.legend(loc="upper right", fontsize=9)
    ax_v.set_title("Velocity Profile $v(r)$", fontsize=13, fontweight="bold")

    # Panel 4: Thermal Pressure
    ax_p.set_xlabel("Radius $r$ [pc]", fontsize=12)
    ax_p.set_ylabel("Thermal Pressure $P/k_B$ [K cm$^{-3}$]", fontsize=12)
    ax_p.set_yscale("log")
    ax_p.set_ylim(1e2, 1e10)
    ax_p.axhline(1e4 * 100, color="gray", ls="--", alpha=0.5, label="Ambient $P/k = 10^6$ K cm$^{-3}$")
    ax_p.grid(True, which="both", alpha=0.3)
    ax_p.legend(loc="lower left", fontsize=9)
    ax_p.set_title("Thermal Pressure $P(r)/k_B$", fontsize=13, fontweight="bold")

    for ax in axes.flat:
        ax.set_xlim(0.2, 20.0)

    fig.suptitle(
        "Wolf-Rayet Wind Bubble Evolution over 1 Million Years (f_production_1myr)\n"
        r"$\dot{M}=10^{-5}\,M_\odot/\mathrm{yr},\; v_w=2000\,\mathrm{km/s},\; n_\mathrm{ISM}=10^4\,\mathrm{cm}^{-3},\; T_\mathrm{ISM}=100\,\mathrm{K}$ "
        r"| Conduction (STS) + Exact Cooling ($T_\mathrm{fix}=\mathrm{ON}$)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(OUT_IMG, dpi=200)
    print(f"Saved figure to {OUT_IMG}")

    # Generate Zoomed Figure focusing on the bubble interior and shell (r <= 6 pc)
    zoom_img = HERE / "f_production_1myr_zoom.png"
    fig2, axes2 = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
    ax_n2, ax_t2 = axes2[0, 0], axes2[0, 1]
    ax_v2, ax_p2 = axes2[1, 0], axes2[1, 1]

    for snap, col in zip(snapshots, colors):
        label = f"{snap['time_years']:,.0f} yr"
        r = snap["r_pc"]
        ax_n2.plot(r, snap["n_cm3"], label=label, color=col, lw=2.0)
        ax_t2.plot(r, snap["t_k"], label=label, color=col, lw=2.0)
        ax_v2.plot(r, snap["v_kms"], label=label, color=col, lw=2.0)
        ax_p2.plot(r, snap["p_over_k"], label=label, color=col, lw=2.0)

    ax_n2.set_ylabel("Total Number Density $n$ [cm$^{-3}$]", fontsize=12)
    ax_n2.set_yscale("log")
    ax_n2.set_ylim(1e-4, 5e5)
    ax_n2.axhline(1e4, color="gray", ls="--", alpha=0.5, label="Ambient $n=10^4$ cm$^{-3}$")
    ax_n2.grid(True, which="both", alpha=0.3)
    ax_n2.legend(loc="lower right", fontsize=9)
    ax_n2.set_title("Density Profile $n(r)$ (Zoomed)", fontsize=13, fontweight="bold")

    ax_t2.set_ylabel("Temperature $T$ [K]", fontsize=12)
    ax_t2.set_yscale("log")
    ax_t2.set_ylim(50, 5e7)
    ax_t2.axhline(100, color="gray", ls="--", alpha=0.5, label="Ambient Floor $T=100$ K")
    ax_t2.grid(True, which="both", alpha=0.3)
    ax_t2.legend(loc="upper right", fontsize=9)
    ax_t2.set_title("Temperature Profile $T(r)$ (Zoomed)", fontsize=13, fontweight="bold")

    ax_v2.set_xlabel("Radius $r$ [pc]", fontsize=12)
    ax_v2.set_ylabel("Radial Velocity $v_r$ [km/s]", fontsize=12)
    ax_v2.set_ylim(-50, 2200)
    ax_v2.axhline(2000, color="gray", ls="--", alpha=0.5, label="Wind $v_w=2000$ km/s")
    ax_v2.grid(True, which="both", alpha=0.3)
    ax_v2.legend(loc="upper right", fontsize=9)
    ax_v2.set_title("Velocity Profile $v(r)$ (Zoomed)", fontsize=13, fontweight="bold")

    ax_p2.set_xlabel("Radius $r$ [pc]", fontsize=12)
    ax_p2.set_ylabel("Thermal Pressure $P/k_B$ [K cm$^{-3}$]", fontsize=12)
    ax_p2.set_yscale("log")
    ax_p2.set_ylim(1e2, 5e7)
    ax_p2.axhline(1e4 * 100, color="gray", ls="--", alpha=0.5, label="Ambient $P/k = 10^6$ K cm$^{-3}$")
    ax_p2.grid(True, which="both", alpha=0.3)
    ax_p2.legend(loc="lower right", fontsize=9)
    ax_p2.set_title("Thermal Pressure $P(r)/k_B$ (Zoomed)", fontsize=13, fontweight="bold")

    for ax in axes2.flat:
        ax.set_xlim(0.2, 5.5)

    fig2.suptitle(
        r"Bubble Structure & Swept-up Shell (Zoom $r \leq 5.5$ pc)" + "\n"
        r"Termination shock ($r \approx 1.5$ pc) | Hot bubble ($T \sim 6\times 10^6$ K) | Cooled dense shell ($r \approx 1.8 - 4.3$ pc)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(zoom_img, dpi=200)
    print(f"Saved figure to {zoom_img}")


if __name__ == "__main__":
    main()
