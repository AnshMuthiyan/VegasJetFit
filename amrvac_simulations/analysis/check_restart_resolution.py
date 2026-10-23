"""Check matched restart and doubled radial resolution against a VM pilot."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_dense_cooling_run import read_vtu
from validate_vm_pilots import read_quantity


def profile(run_dir):
    if (run_dir / "run.exit").read_text().strip() != "0":
        raise ValueError(f"Run incomplete: {run_dir}")
    path = sorted((run_dir / "output").glob("test*.vtu"))[-1]
    age, values = read_vtu(path)
    tunit = read_quantity((run_dir / "run.stdout").read_text(), "Temperature unit")
    values = values[1:-1].copy()
    values[:, 2] /= 1e5
    values[:, 4] *= tunit
    return age, values


def hot_extent(values):
    hot = values[:, 0][values[:, 4] >= 1.0e4]
    if len(hot) == 0:
        raise ValueError("No points meet the hot-bubble threshold")
    return float(hot[-1])


def compare(base, test, label, output):
    r = base[:, 0]
    if label == "restart":
        if not np.array_equal(r, test[:, 0]):
            raise ValueError("Restart changed the AMR radius grid")
        common = np.ones(len(r), dtype=bool)
    else:
        common = (r >= test[0, 0]) & (r <= test[-1, 0])
    rows = []
    fields = (
        ("density", r"Density [g cm$^{-3}$]", 1, True),
        ("velocity", r"Radial velocity [km s$^{-1}$]", 2, False),
        ("pressure", r"Pressure [dyn cm$^{-2}$]", 3, True),
        ("temperature", "Temperature [K]", 4, True),
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    colors = ("#156b93", "#c04b35", "#608d3e", "#704ab4")
    for axis, (name, ylabel, column, logarithmic), color in zip(
        axes.flat, fields, colors
    ):
        nominal = base[common, column]
        variant = np.interp(r[common], test[:, 0], test[:, column])
        if logarithmic:
            if np.any(nominal <= 0) or np.any(variant <= 0):
                raise ValueError(f"Nonpositive {name}")
            delta = np.log10(variant / nominal)
            metric = "rms_log10_ratio_dex"
        else:
            delta = variant - nominal
            metric = "rms_difference_km_s"
        rows.append({"comparison": label, "field": name, "metric": metric,
                     "value": float(np.sqrt(np.mean(delta**2)))})
        base_label = "Uninterrupted" if label == "restart" else "192 base cells"
        axis.plot(base[:, 0], base[:, column], color=color, lw=2, label=base_label)
        test_label = "Resumed" if label == "restart" else "384 base cells"
        axis.plot(test[:, 0], test[:, column], color="black", ls="--", lw=1.4,
                  label=test_label)
        axis.set_xlim(0, 1.5)
        if logarithmic:
            axis.set_yscale("log")
        axis.set_ylabel(ylabel)
        axis.set_xlabel("Radius [pc]")
        axis.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    title = "Checkpoint restart" if label == "restart" else "Radial-grid comparison"
    fig.suptitle(f"{title} at 0.440 Myr")
    fig.savefig(output / f"{label}_comparison.png", dpi=180)
    fig.savefig(output / f"{label}_comparison.pdf")
    plt.close(fig)
    rows.extend((
        {"comparison": label, "field": "hot extent T >= 1e4 K",
         "metric": "baseline_radius_pc", "value": hot_extent(base)},
        {"comparison": label, "field": "hot extent T >= 1e4 K",
         "metric": "variant_radius_pc", "value": hot_extent(test)},
        {"comparison": label, "field": "minimum radial spacing",
         "metric": "baseline_pc", "value": float(np.min(np.diff(base[:, 0])))},
        {"comparison": label, "field": "minimum radial spacing",
         "metric": "variant_pc", "value": float(np.min(np.diff(test[:, 0])))},
    ))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_root", type=Path)
    args = parser.parse_args()
    root = args.staging_root
    output = root / "validation"
    output.mkdir(exist_ok=True)
    age, base = profile(root / "keohane3")
    rows = []
    for label, directory in (("restart", "restart_from10"),
                             ("resolution2x", "resolution2x")):
        variant_age, values = profile(root / directory)
        if not np.isclose(variant_age, age, atol=1e-7, rtol=0):
            raise ValueError(f"Terminal ages differ: {age}, {variant_age}")
        rows.extend(compare(base, values, label, output))
    with (output / "restart_resolution_metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"{row['comparison']} {row['field']}: {row['value']:.6g} {row['metric']}")


if __name__ == "__main__":
    main()
