#!/usr/bin/env python3
"""Compare matched BoOST p4 Mac and VM VTUs at the same physical ages."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
GRBS = ROOT.parents[1]
sys.path.insert(0, str(GRBS / "VegasJetFit_wind_bubble_handoff/amrvac_simulations/analysis"))
from plot_dense_cooling_run import read_vtu  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mac-root", type=Path, default=ROOT / "results_mac_full")
    parser.add_argument("--vm-root", type=Path, default=ROOT / "results_full")
    parser.add_argument("--output", type=Path, default=ROOT / "mac_vm_matched_age_profiles.csv")
    args = parser.parse_args()
    rows = []
    radial_grid = np.geomspace(0.25, 30.0, 1000)
    for mac_run in sorted(args.mac_root.glob("p4_*_*")):
        vm_run = args.vm_root / mac_run.name
        if not (mac_run / "run.exit").exists() or not (vm_run / "run.exit").exists():
            continue
        if (mac_run / "run.exit").read_text().strip() != "0":
            continue
        if (vm_run / "run.exit").read_text().strip() != "0":
            continue
        mac_files = sorted((mac_run / "output").glob("test*.vtu"))
        vm_files = sorted((vm_run / "output").glob("test*.vtu"))
        if len(mac_files) != len(vm_files) or not mac_files:
            raise ValueError(f"Unmatched snapshot count for {mac_run.name}")
        for mac_file, vm_file in zip(mac_files, vm_files):
            mac_age, mac = read_vtu(mac_file)
            vm_age, vm = read_vtu(vm_file)
            if not np.isclose(mac_age, vm_age, rtol=1e-6, atol=1e-8):
                raise ValueError(f"Unmatched ages for {mac_file} and {vm_file}")
            if not (np.isfinite(mac).all() and np.isfinite(vm).all()):
                raise ValueError(f"Nonfinite saved field for {mac_run.name} at {mac_age}")
            if np.any(mac[:, (1, 3)] <= 0) or np.any(vm[:, (1, 3)] <= 0):
                raise ValueError(f"Nonpositive density or pressure for {mac_run.name} at {mac_age}")
            row = {
                "case_variant": mac_run.name,
                "age_Myr": mac_age,
                "native_radii_equal": mac.shape == vm.shape and np.array_equal(mac[:, 0], vm[:, 0]),
            }
            # Node profiles are interpolated onto a fixed common inner grid.
            for column, field in ((1, "rho"), (3, "pressure")):
                mac_log = np.interp(radial_grid, mac[:, 0], np.log10(mac[:, column]))
                vm_log = np.interp(radial_grid, vm[:, 0], np.log10(vm[:, column]))
                delta = np.abs(mac_log - vm_log)
                row[f"mean_abs_log10{field}"] = float(delta.mean())
                row[f"max_abs_log10{field}"] = float(delta.max())
            rows.append(row)
    if not rows:
        raise ValueError("No completed matched Mac/VM full runs")
    output = args.output
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for case in sorted({row["case_variant"] for row in rows}):
        match = [row for row in rows if row["case_variant"] == case]
        final = match[-1]
        print(
            f"{case}: {len(match)} ages, final mean/max log-rho "
            f"{final['mean_abs_log10rho']:.3g}/{final['max_abs_log10rho']:.3g} dex, "
            f"native radii equal={final['native_radii_equal']}"
        )
    print(f"Wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
