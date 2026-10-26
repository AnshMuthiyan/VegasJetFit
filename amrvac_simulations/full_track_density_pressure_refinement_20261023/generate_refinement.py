#!/usr/bin/env python3
"""Generate only the log-midpoint cases missing from the frozen full-track grid."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "van_marle_full_track_grid_20261023"
DENSITIES = (3000, 5477, 10000, 17321, 30000)
PRESSURES = (1000000, 3162278, 10000000, 31622777, 100000000, 316227766, 1000000000)
ORIGINAL_DENSITIES = {3000, 10000, 30000}
ORIGINAL_PRESSURES = {1000000, 10000000, 100000000, 1000000000}
QUOTAS = {
    "keohane1": 7,
    "keohane2": 7,
    "keohane3": 7,
    "keohane4": 8,
    "pauley404-01": 4,
    "pauley404-02": 5,
    "pauley404-03": 8,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_setting(source: str, key: str, value: str) -> str:
    result, count = re.subn(
        rf"(?m)^(\s*{re.escape(key)}\s*=\s*)[^\n]*$",
        lambda match: match.group(1) + value,
        source,
    )
    if count != 1:
        raise ValueError(f"Expected one {key} setting, found {count}")
    return result


def make_stage(parent_case: str, case: str, stage: str) -> str:
    source = (PARENT / "inputs" / f"{parent_case}_{stage}.par").read_text()
    old = f"base_filename = '{parent_case}_{stage}'"
    if source.count(old) != 1:
        raise ValueError(f"Unexpected {stage} filename in parent input")
    return source.replace(old, f"base_filename = '{case}_{stage}'")


def main() -> None:
    if (HERE / "manifest.csv").exists() or (HERE / "inputs").exists():
        raise SystemExit("Refinement inputs already exist; refusing overwrite")
    parent_rows = list(csv.DictReader((PARENT / "manifest.csv").open()))
    parent_cases = {row["case"] for row in parent_rows}
    if len(parent_cases) != 24:
        raise ValueError("Parent manifest is not the frozen 24-case grid")
    parent_by_mass = {int(row["star_mass_msun"]): row for row in parent_rows}
    if set(parent_by_mass) != {25, 40}:
        raise ValueError("Missing parent stellar track")

    cases = [
        (star, density, pressure)
        for star in (25, 40)
        for density in DENSITIES
        for pressure in PRESSURES
        if density not in ORIGINAL_DENSITIES or pressure not in ORIGINAL_PRESSURES
    ]
    if len(cases) != 46:
        raise ValueError("Refined grid must add exactly 46 points")

    # The slower Mac03 gets short 40-Msun tracks; the other 38 cases stay balanced.
    mac03 = [case for case in cases if case[0] == 40][: QUOTAS["pauley404-03"]]
    remaining = [case for case in cases if case not in mac03]
    other_hosts = [host for host in QUOTAS if host != "pauley404-03"]
    available = {host: QUOTAS[host] for host in other_hosts}
    assignments = {case: "pauley404-03" for case in mac03}
    turn = 0
    for case in remaining:
        while available[other_hosts[turn % len(other_hosts)]] == 0:
            turn += 1
        host = other_hosts[turn % len(other_hosts)]
        assignments[case] = host
        available[host] -= 1
        turn += 1
    if any(available.values()):
        raise ValueError("Host quotas do not sum to the refinement size")

    inputs = HERE / "inputs"
    inputs.mkdir()
    rows = []
    for star, density, pressure in cases:
        case = f"m{star}_n{density}_pk{pressure}"
        if case in parent_cases:
            raise ValueError(f"Duplicate parent case: {case}")
        parent_case = parent_by_mass[star]["case"]
        base = (PARENT / "inputs" / f"{parent_case}_base.par").read_text()
        base = replace_setting(base, "n_ref_cm3", f"{density}.0d0")
        base = replace_setting(base, "star_mass_msun", f"{star}.0d0")
        base = replace_setting(base, "external_pressure_over_k", f"{pressure}.0d0")
        (inputs / f"{case}_base.par").write_text(base)
        for stage in ("static", "smoke", "full"):
            (inputs / f"{case}_{stage}.par").write_text(make_stage(parent_case, case, stage))
        row = dict(parent_by_mass[star])
        row.update(
            case=case,
            host=assignments[(star, density, pressure)],
            n_ref_cm3_at_1pc=density,
            central_untapered_nh_cm3=density * 26**0.9,
            external_pressure_over_k_K_cm3=pressure,
            base_file=f"{case}_base.par",
            static_file=f"{case}_static.par",
            smoke_file=f"{case}_smoke.par",
            full_file=f"{case}_full.par",
        )
        for stage in ("base", "static", "smoke", "full"):
            row[f"{stage}_sha256"] = digest(inputs / row[f"{stage}_file"])
        rows.append(row)

    with (HERE / "manifest.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(parent_rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    design = json.loads((PARENT / "design.json").read_text())
    design.update(
        count=46,
        parent_campaign=PARENT.name,
        parent_manifest_sha256=digest(PARENT / "manifest.csv"),
        purpose="Log-midpoint interpolation and withheld-profile validation; same physics and mesh",
        n_ref_grid_cm3_at_1pc=list(DENSITIES),
        external_pressure_grid_over_k_K_cm3=list(PRESSURES),
        original_case_count=24,
    )
    (HERE / "design.json").write_text(json.dumps(design, indent=2) + "\n")
    print("Generated 46 distinct midpoint cases and 184 inputs")
    for host, count in QUOTAS.items():
        print(host, count)


if __name__ == "__main__":
    main()
