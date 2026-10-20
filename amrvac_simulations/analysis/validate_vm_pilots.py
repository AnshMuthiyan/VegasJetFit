"""Validate and plot independently staged AMRVAC dense-cooling VM pilots."""

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_dense_cooling_run import read_vtu


def read_quantity(log_text, label):
    match = re.search(rf"{re.escape(label)}\s*[:=]\s*([\d.Ee+-]+)", log_text)
    if match is None:
        raise ValueError(f"Missing {label} in run stdout")
    return float(match.group(1))


def validate_case(run_dir, output_dir):
    host = run_dir.name
    if (run_dir / "run.exit").read_text().strip() != "0":
        raise ValueError(f"{host}: run did not exit successfully")
    stdout = (run_dir / "run.stdout").read_text()
    if "Finished AMRVAC in" not in stdout:
        raise ValueError(f"{host}: no normal AMRVAC completion marker")
    if "Spitzer HD par:" not in stdout:
        raise ValueError(f"{host}: Spitzer conduction was not initialized")

    ambient = read_quantity(stdout, "Ambient density [g cm^-3]")
    ambient_t = read_quantity(stdout, "Ambient temperature [K]")
    cutoff = read_quantity(stdout, "Cooling cutoff [K]")
    tunit = read_quantity(stdout, "Temperature unit")
    if not np.isclose(ambient_t, cutoff):
        raise ValueError(f"{host}: cooling cutoff differs from ambient T")

    vtus = sorted((run_dir / "output").glob("test*.vtu"))
    if len(vtus) < 3:
        raise ValueError(f"{host}: too few saved VTU profiles: {len(vtus)}")

    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex="col")
    rows = []
    disturbed_radius = 0.0
    for path in vtus:
        age, profile = read_vtu(path)
        radius = profile[:, 0]
        if not np.all(np.diff(radius) > 0):
            raise ValueError(f"{path}: radius is not strictly increasing")
        if not np.isclose(radius[0], 0.01, atol=1e-5):
            raise ValueError(f"{path}: unexpected inner radius {radius[0]}")
        if not np.isclose(radius[-1], 8.0, atol=1e-4):
            raise ValueError(f"{path}: unexpected outer radius {radius[-1]}")
        temp = profile[:, 4] * tunit
        disturbed = (np.abs(profile[:, 1] / ambient - 1.0) > 0.02) | (
            temp > 1.2 * ambient_t
        )
        if np.any(disturbed):
            disturbed_radius = max(disturbed_radius, float(np.max(radius[disturbed])))
        peak_index = int(np.argmax(profile[:, 1]))
        outer = radius >= 7.5
        row = {
            "host": host,
            "snapshot": path.name,
            "age_Myr": age,
            "points": len(radius),
            "minimum_dx_pc": float(np.min(np.diff(radius))),
            "minimum_density_g_cm3": float(np.min(profile[:, 1])),
            "maximum_density_g_cm3": float(np.max(profile[:, 1])),
            "maximum_density_radius_pc": float(radius[peak_index]),
            "minimum_temperature_K": float(np.min(temp)),
            "maximum_temperature_K": float(np.max(temp)),
            "outer_0p5pc_max_abs_density_fraction": float(
                np.max(np.abs(profile[outer, 1] / ambient - 1.0))
            ),
        }
        rows.append(row)
        label = f"{age:.3f} Myr"
        axes[0, 0].plot(radius, profile[:, 1] / ambient)
        axes[0, 1].plot(radius, profile[:, 1] / ambient, label=label)
        axes[1, 0].plot(radius, temp)
        axes[1, 1].plot(radius, temp)

    ages = np.array([row["age_Myr"] for row in rows])
    if not np.all(np.diff(ages) > 0):
        raise ValueError(f"{host}: snapshot times are not strictly increasing")
    zoom_radius = min(8.0, max(0.2, 1.2 * disturbed_radius))
    axes[0, 0].set_title("Full domain")
    axes[0, 1].set_title("Inner structure")
    axes[0, 0].set_ylabel(r"$\rho / \rho_{\rm ambient}$")
    axes[1, 0].set_ylabel("Temperature [K]")
    for axis in axes[1, :]:
        axis.set_xlabel("Radius [pc]")
    for axis in axes[0, :]:
        axis.set_yscale("log")
    for axis in axes[1, :]:
        axis.set_yscale("log")
    for axis in axes.flat:
        axis.grid(alpha=0.2)
    for axis in axes[:, 0]:
        axis.set_xlim(0, 8)
    for axis in axes[:, 1]:
        axis.set_xlim(0, zoom_radius)
    axes[0, 1].legend(fontsize=7, ncol=2)
    fig.suptitle(f"{host}: AMRVAC dense-cooling pilot")
    fig.tight_layout()
    fig.savefig(output_dir / f"{host}_profiles.png", dpi=180)
    fig.savefig(output_dir / f"{host}_profiles.pdf")
    plt.close(fig)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_root", type=Path)
    args = parser.parse_args()
    root = args.staging_root
    plots = root / "validation"
    plots.mkdir(exist_ok=True)
    rows = []
    for host in ("keohane1", "keohane2", "keohane3", "keohane4"):
        rows.extend(validate_case(root / host, plots))
    with (plots / "profile_metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for host in ("keohane1", "keohane2", "keohane3", "keohane4"):
        final = next(row for row in reversed(rows) if row["host"] == host)
        print(
            f"{host}: {final['age_Myr']:.4f} Myr, "
            f"{final['points']} points, "
            f"T=[{final['minimum_temperature_K']:.1f}, "
            f"{final['maximum_temperature_K']:.1f}] K, "
            f"outer perturbation={final['outer_0p5pc_max_abs_density_fraction']:.3g}"
        )
    print(f"Validated {len(rows)} snapshots; products: {plots}")


if __name__ == "__main__":
    main()
