"""Inspect the selected AMRVAC snapshots without importing the fitting package.

Outputs raw-profile zooms and measurements; no smoothing is applied. The
reader follows the existing plot_tight_density_profiles.py VTU convention.
"""
import csv
import re
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "outer_wall_inspection"
PC_CM = 3.0857e18


def read_vtu(path):
    raw = path.read_bytes()
    app_start = raw.find(b"<AppendedData")
    data_start = raw.find(b"_", app_start) + 1
    data_end = raw.find(b"</AppendedData>", data_start)
    header = raw[:app_start].decode("ascii", "ignore")
    appended = raw[data_start:data_end]
    pairs = []
    for piece in re.finditer(r"<Piece\b[^>]*>(.*?)</Piece>", header, re.S):
        body = piece.group(1)
        rho_m = re.search(r'<DataArray[^>]*Name="rho"[^>]*offset="(\d+)"', body)
        pts_m = re.search(r'<Points>\s*<DataArray[^>]*offset="(\d+)"', body, re.S)
        if not rho_m or not pts_m:
            continue
        rho_off, pts_off = int(rho_m.group(1)), int(pts_m.group(1))
        rho_len = struct.unpack_from("<I", appended, rho_off)[0]
        pts_len = struct.unpack_from("<I", appended, pts_off)[0]
        rho = np.frombuffer(appended, dtype="<f4", count=rho_len // 4, offset=rho_off + 4)
        pts = np.frombuffer(appended, dtype="<f4", count=pts_len // 4, offset=pts_off + 4).reshape(-1, 3)
        pairs.extend(zip(pts[:, 0] / PC_CM, rho))
    arr = np.asarray(pairs, dtype=float)
    arr = arr[np.argsort(arr[:, 0])]
    rounded = np.round(arr[:, 0], 12)
    unique, first, counts = np.unique(rounded, return_index=True, return_counts=True)
    # Collapse shared boundary nodes, as in the existing campaign reader.
    radius = np.array([np.median(arr[i:i+n, 0]) for i, n in zip(first, counts)])
    density = np.array([np.median(arr[i:i+n, 1]) for i, n in zip(first, counts)])
    good = np.isfinite(density) & (density > 0) & (radius > 0)
    return radius[good], density[good]


def crossing(r, y, target, start):
    for i in range(start, len(r) - 1):
        if y[i] <= target <= y[i + 1]:
            fraction = (target - y[i]) / (y[i + 1] - y[i])
            return r[i] + fraction * (r[i + 1] - r[i])
    raise ValueError("No upward crossing")


def main():
    OUT.mkdir(exist_ok=True)
    with (ROOT / "tables" / "log_grid_plan.csv").open(newline="") as fh:
        plans = {row["run_id"]: row for row in csv.DictReader(fh)}
    with (ROOT / "tables" / "allP_run_quality_table.csv").open(newline="") as fh:
        quality = list(csv.DictReader(fh))
    fig, axes = plt.subplots(3, 2, figsize=(12, 11), constrained_layout=True)
    records = []
    for row in quality:
        run = row["run_id"]
        plan = plans[run]
        r, rho = read_vtu(ROOT / "selected_vtu" / f"{run}__{row['chosen_snapshot']}")
        y = rho / float(plan["rho_g_cm3"])
        onset = float(row["x_final_rise"]) * float(plan["rt_external_pc"])
        floor_window = (r > 0.5 * onset) & (r < onset)
        floor_i = np.where(floor_window)[0][np.argmin(y[floor_window])]
        floor = y[floor_i]
        rlo = crossing(r, y, 2 * floor, floor_i)
        r90 = crossing(r, y, 0.9, floor_i)
        outer = r >= onset
        peak_i = np.where(outer)[0][np.argmax(y[outer])]
        records.append(dict(run_id=run, snapshot=row["chosen_snapshot"],
                            cavity_floor_over_ism=floor, rise_start_pc=rlo,
                            rise_90ism_pc=r90, rise_width_pc=r90-rlo,
                            rise_width_dex=np.log10(r90/rlo),
                            rise_unique_samples=int(np.sum((r >= rlo) & (r <= r90))),
                            outer_peak_over_ism=y[peak_i], peak_radius_pc=r[peak_i]))
        panel = int(run[1]) - 4
        color = plt.cm.viridis((int(run.split("_n")[1]) % 10) / 5)
        mask = (r / r90 > 0.7) & (r / r90 < 1.6)
        axes[panel, 0].plot(r[mask] / r90, y[mask], color=color, label=run)
        axes[panel, 1].plot(r[mask] / r90, y[mask], color=color, lw=1,
                            marker=".", markersize=2, label=run)
    for i in range(3):
        for j in range(2):
            ax = axes[i, j]
            ax.axhline(1, color="black", ls="--", lw=0.8, label="ISM" if i == 0 else None)
            ax.set_ylabel(r"$\rho / \rho_{\rm ISM}$")
            ax.set_xlabel(r"$r/r_{90}$ (first outer-rise crossing of $0.9\rho_{\rm ISM}$)")
            ax.set_title(f"p{i+4}: " + ("wall peak and outer edge" if j == 0 else "rise, raw radial samples"))
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
            if j == 1:
                ax.set_yscale("log")
                ax.set_xlim(0.7, 1.2)
    fig.savefig(OUT / "outer_wall_ramps.png", dpi=180)
    plt.close(fig)
    with (OUT / "outer_wall_measurements.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    for row in records:
        print(f"{row['run_id']}: floor/ISM={row['cavity_floor_over_ism']:.3g}, "
              f"outer peak/ISM={row['outer_peak_over_ism']:.4g}, "
              f"rise={row['rise_width_dex']:.4f} dex, {row['rise_unique_samples']} samples")


if __name__ == "__main__":
    main()
