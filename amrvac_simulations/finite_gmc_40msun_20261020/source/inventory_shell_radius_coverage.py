#!/usr/bin/env python3
"""Inventory quality-gated direct-WR inner-rise radii in 0.2-dex bins."""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections.abc import Sequence
from pathlib import Path


BIN_LOG_WIDTH = 0.2
BIN_LOG_MAX = 1.0


def bin_layout(min_radius_pc: float) -> tuple[float, int]:
    if min_radius_pc not in (0.001, 0.01, 0.1):
        raise ValueError("minimum radius must be 0.001, 0.01 or 0.1 pc")
    log_min = math.log10(min_radius_pc)
    return log_min, round((BIN_LOG_MAX - log_min) / BIN_LOG_WIDTH)


def radius_bin(radius_pc: float, min_radius_pc: float = 0.1) -> int | None:
    log_min, count = bin_layout(min_radius_pc)
    if not math.isfinite(radius_pc) or not min_radius_pc <= radius_pc <= 10.0:
        return None
    return min(count - 1,
               max(0, math.floor((math.log10(radius_pc) - log_min) / BIN_LOG_WIDTH)))


def mesh_cells(base_file: Path) -> int:
    match = re.search(r"^\s*domain_nx1\s*=\s*(\d+)",
                      base_file.read_text(encoding="ascii"), re.MULTILINE)
    if not match:
        raise ValueError(f"missing domain_nx1 in {base_file}")
    return int(match.group(1))


def manifest_cases(root: Path) -> dict[str, dict[str, str | int]]:
    cases = {}
    for path in sorted(root.glob("dense_gmc_inputs_*/manifest.csv")):
        with path.open(newline="", encoding="ascii") as stream:
            for row in csv.DictReader(stream):
                if row["stage"] != "wind":
                    continue
                info = {"n_ref_cm3": row["n_ref_cm3"],
                        "n_gmc_cm3": row["n_gmc_cm3"],
                        "mesh_cells": mesh_cells(path.parent / row["base_file"]),
                        "inner_pc": row["inner_pc"],
                        "first_width_pc": row["first_width_pc"],
                        "domain_max_pc": row["domain_max_pc"],
                        "atmosphere_outer_pc": row.get("atmosphere_outer_pc") or row["domain_max_pc"],
                        "manifest": str(path)}
                previous = cases.get(row["case"])
                if previous and any(previous[key] != info[key]
                                    for key in ("n_ref_cm3", "n_gmc_cm3", "mesh_cells",
                                                "inner_pc", "first_width_pc", "domain_max_pc",
                                                "atmosphere_outer_pc")):
                    raise ValueError(f"conflicting manifests for {row['case']}")
                cases[row["case"]] = info
    return cases


def inventory(root: Path, diagnostics: Path, min_radius_pc: float = 0.1,
              additional_diagnostics: Sequence[Path] = ()) -> list[dict[str, str | int | float | bool]]:
    cases = manifest_cases(root)
    rows = []
    seen = set()
    sources = (diagnostics, *additional_diagnostics)
    paths = sorted(path for source in sources
                   for path in source.glob("*agefix/inner_shell_metrics.csv"))
    if not paths:
        raise ValueError(f"no age-corrected diagnostics in {sources}")
    for path in paths:
        with path.open(newline="", encoding="ascii") as stream:
            for item in csv.DictReader(stream):
                case = item["case"]
                if case not in cases:
                    raise ValueError(f"no manifest for {case}")
                key = (case, item["age_myr"])
                if key in seen:
                    raise ValueError(f"duplicate diagnostic snapshot: {key}")
                seen.add(key)
                radius = float(item["inner_radius_pc"] or "nan")
                bin_number = radius_bin(radius, min_radius_pc)
                quality = item["shell_quality_pass"] == "True"
                measured = item["inner_edge_status"] == "measured"
                accepted = quality and measured and bin_number is not None
                rows.append({"case": case, "age_myr": float(item["age_myr"]),
                             **cases[case], "inner_radius_pc": radius,
                             "shell_inner_nh_cm3": item["shell_inner_nh_cm3"],
                             "shell_peak_nh_cm3": item["shell_peak_nh_cm3"],
                             "shell_fwhm_cells": item["shell_fwhm_cells"],
                             "shell_contrast": item["shell_contrast"],
                             "inner_ramp_cells": item["inner_ramp_cells"],
                             "shell_quality_pass": quality,
                             "inner_edge_status": item["inner_edge_status"],
                             "inner_ramp_resolved": item["inner_ramp_resolved"] == "True",
                             "accepted_for_coverage": accepted,
                             "bin_index": bin_number if accepted else "",
                             "source_csv": str(path)})
    return sorted(rows, key=lambda row: (row["inner_radius_pc"], row["age_myr"]))


def summarize(rows: list[dict], min_radius_pc: float = 0.1) -> list[dict]:
    log_min, count = bin_layout(min_radius_pc)
    result = []
    for number in range(count):
        lo = 10 ** (log_min + number * BIN_LOG_WIDTH)
        hi = 10 ** (log_min + (number + 1) * BIN_LOG_WIDTH)
        center = math.sqrt(lo * hi)
        members = [row for row in rows if row["bin_index"] == number]
        representative = min(members, key=lambda row: abs(math.log10(row["inner_radius_pc"] / center))) if members else None
        result.append({"bin_index": number, "radius_lo_pc": lo,
                       "radius_hi_pc": hi, "target_pc": center,
                       "snapshot_count": len(members),
                       "distinct_case_count": len({row["case"] for row in members}),
                       "ramp_resolved_count": sum(row["inner_ramp_resolved"] for row in members),
                       "representative_case": representative["case"] if representative else "",
                       "representative_age_myr": representative["age_myr"] if representative else "",
                       "representative_radius_pc": representative["inner_radius_pc"] if representative else "",
                       "representative_shell_nh_cm3": representative["shell_inner_nh_cm3"] if representative else ""})
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="ascii") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(root: Path, diagnostics: Path, output: Path, min_radius_pc: float = 0.1,
         additional_diagnostics: Sequence[Path] = ()) -> None:
    rows = inventory(root, diagnostics, min_radius_pc, additional_diagnostics)
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "snapshot_inventory.csv", rows)
    bins = summarize(rows, min_radius_pc)
    write_csv(output / "log_radius_bins.csv", bins)
    occupied = sum(row["snapshot_count"] > 0 for row in bins)
    print(f"{occupied}/{len(bins)} quality-gated radius bins occupied; wrote {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagnostics", type=Path, help="Age-corrected inner-edge diagnostic root")
    parser.add_argument("output", type=Path, help="New output directory")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--additional-diagnostics", type=Path, action="append", default=[],
                        help="Additional age-corrected diagnostic root; repeat as needed")
    parser.add_argument("--min-radius-pc", type=float, choices=(0.001, 0.01, 0.1), default=0.1,
                        help="Lower radius limit; keep 0.1 pc for the original inventory")
    args = parser.parse_args()
    main(args.root, args.diagnostics, args.output, args.min_radius_pc,
         args.additional_diagnostics)
