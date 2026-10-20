"""Compare matched AMRVAC physics toggles with the dense-cooling VM pilot."""

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_dense_cooling_run import read_vtu
from validate_vm_pilots import read_quantity


def final_profile(run_dir):
    if (run_dir / "run.exit").read_text().strip() != "0":
        raise ValueError(f"Incomplete run: {run_dir}")
    log = (run_dir / "run.stdout").read_text()
    path = sorted((run_dir / "output").glob("test*.vtu"))[-1]
    age, profile = read_vtu(path)
    return age, profile[1:-1], read_quantity(log, "Temperature unit")


def compare(root, label, directory, output):
    display_label = label.replace("no_conduction", "Conduction disabled").replace(
        "no_cooling", "Cooling disabled"
    ).replace("no_saturation", "Flux saturation disabled")
    base_age, base, base_tunit = final_profile(root / "keohane3")
    age, test, tunit = final_profile(directory)
    if not np.isclose(age, base_age, rtol=0, atol=1e-7):
        raise ValueError(f"Unmatched terminal times: {base_age}, {age}")
    radius = base[:, 0]
    common = (radius >= max(0.05, test[0, 0])) & (radius <= min(2.0, test[-1, 0]))
    if common.sum() < 20:
        raise ValueError("Too few overlapping cells in inner 2 pc")
    r = radius[common]
    hot_base = radius[base[:, 4] * base_tunit >= 1.0e4]
    hot_test = test[:, 0][test[:, 4] * tunit >= 1.0e4]
    if len(hot_base) == 0 or len(hot_test) == 0:
        raise ValueError("Hot-bubble threshold absent in a compared profile")
    colors = ("#156b93", "#c04b35", "#608d3e", "#704ab4")
    fields = (
        ("Density [g cm$^{-3}$]", base[:, 1], test[:, 1], True),
        ("Radial velocity [km s$^{-1}$]", base[:, 2] / 1e5, test[:, 2] / 1e5, False),
        ("Pressure [dyn cm$^{-2}$]", base[:, 3], test[:, 3], True),
        ("Temperature [K]", base[:, 4] * base_tunit, test[:, 4] * tunit, True),
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
    rows = []
    for axis, (name, baseline, variant, logarithmic), color in zip(
        axes.flat, fields, colors
    ):
        interpolated = np.interp(r, test[:, 0], variant)
        actual = baseline[common]
        if logarithmic:
            difference = np.log10(interpolated / actual)
            metric = "rms_log10_ratio_dex"
            magnitude = float(np.sqrt(np.mean(difference**2)))
        else:
            difference = interpolated - actual
            metric = "rms_difference_km_s"
            magnitude = float(np.sqrt(np.mean(difference**2)))
        rows.append({"comparison": label, "field": name, "metric": metric, "value": magnitude})
        axis.plot(base[:, 0], baseline, color=color, lw=2.0, label="Conduction + cooling")
        axis.plot(test[:, 0], variant, color="black", ls="--", lw=1.4,
                  label=display_label)
        axis.set_xlim(0, 2.0)
        if logarithmic:
            axis.set_yscale("log")
        axis.set_ylabel(name)
        axis.set_xlabel("Radius [pc]")
        axis.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f"Matched physics control: {display_label} at {age:.3f} Myr")
    fig.savefig(output / f"{label}_comparison.png", dpi=180)
    fig.savefig(output / f"{label}_comparison.pdf")
    plt.close(fig)
    rows.append({"comparison": label, "field": "Hot extent at T >= 1e4 K", "metric": "baseline_radius_pc", "value": float(hot_base[-1])})
    rows.append({"comparison": label, "field": "Hot extent at T >= 1e4 K", "metric": "variant_radius_pc", "value": float(hot_test[-1])})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_root", type=Path)
    args = parser.parse_args()
    root = args.staging_root
    output = root / "validation"
    output.mkdir(exist_ok=True)
    rows = []
    for label, dirname in (
        ("no_conduction", "control_no_conduction"),
        ("no_cooling", "control_no_cooling"),
    ):
        rows.extend(compare(root, label, root / dirname, output))
    failed = (root / "control_no_saturation" / "run.stdout").read_text()
    if "Error: small value encountered, run crash." not in failed or "Finished AMRVAC in" in failed:
        raise ValueError("Unexpected saturation-off outcome")
    match = re.search(r"Iteration:\s*\d+\s+Time:\s*([\d.Ee+-]+)", failed)
    if match is None:
        raise ValueError("Missing failure time in saturation-off run")
    rows.append({"comparison": "no_saturation", "field": "Negative-pressure crash",
                 "metric": "failure_code_time", "value": float(match.group(1))})
    with (output / "physics_control_metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"{row['comparison']} {row['field']}: {row['value']:.6g} {row['metric']}")


if __name__ == "__main__":
    main()
