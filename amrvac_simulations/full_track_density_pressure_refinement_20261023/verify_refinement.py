#!/usr/bin/env python3
"""Check midpoint coverage and exact inherited source/numerical inputs."""

import csv
import hashlib
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "van_marle_full_track_grid_20261023"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_base(source):
    for key in ("n_ref_cm3", "star_mass_msun", "external_pressure_over_k"):
        source, count = re.subn(
            rf"(?m)^\s*{key}\s*=\s*[^\n]*$", f"  {key} = VALUE", source
        )
        assert count == 1, key
    return source


def main():
    parent_rows = list(csv.DictReader((PARENT / "manifest.csv").open()))
    rows = list(csv.DictReader((HERE / "manifest.csv").open()))
    assert len(parent_rows) == 24 and len(rows) == 46
    original = {row["case"] for row in parent_rows}
    assert len({row["case"] for row in rows}) == 46
    assert not original.intersection(row["case"] for row in rows)
    expected = {
        (star, density, pressure)
        for star in (25, 40)
        for density in (3000, 5477, 10000, 17321, 30000)
        for pressure in (1000000, 3162278, 10000000, 31622777, 100000000, 316227766, 1000000000)
    }
    actual = {
        (int(row["star_mass_msun"]), int(row["n_ref_cm3_at_1pc"]), int(row["external_pressure_over_k_K_cm3"]))
        for row in parent_rows + rows
    }
    assert actual == expected
    assert digest(HERE / "mod_usr.t") == digest(PARENT / "mod_usr.t")
    for arch in ("arm64", "linux_x86_64"):
        for name in ("amrvac", "mod_usr.t", "preflight_results.json", "atmosphere_preflight_results.json"):
            assert digest(HERE / "builds" / arch / name) == digest(PARENT / "builds" / arch / name)
    templates = {int(row["star_mass_msun"]): row for row in parent_rows}
    for row in rows:
        case = row["case"]
        parent = templates[int(row["star_mass_msun"])]
        assert int(row["cells"]) == 1024
        assert row["inner_pc"] == parent["inner_pc"]
        assert row["outer_pc"] == parent["outer_pc"]
        assert row["first_width_pc"] == parent["first_width_pc"]
        assert row["endpoint_myr"] == parent["endpoint_myr"]
        assert row["expected_vtus"] == parent["expected_vtus"]
        assert canonical_base((HERE / "inputs" / row["base_file"]).read_text()) == canonical_base(
            (PARENT / "inputs" / parent["base_file"]).read_text()
        )
        for stage in ("base", "static", "smoke", "full"):
            assert digest(HERE / "inputs" / row[f"{stage}_file"]) == row[f"{stage}_sha256"]
            if stage != "base":
                new_text = (HERE / "inputs" / row[f"{stage}_file"]).read_text().replace(case, "CASE")
                old_text = (PARENT / "inputs" / parent[f"{stage}_file"]).read_text().replace(parent["case"], "CASE")
                assert new_text == old_text
    quotas = {"keohane1": 7, "keohane2": 7, "keohane3": 7, "keohane4": 8,
              "pauley404-01": 4, "pauley404-02": 5, "pauley404-03": 8}
    for host, count in quotas.items():
        assert sum(row["host"] == host for row in rows) == count
    print("PASS: 70-point tensor, 46 unique midpoint cases, 184 SHA-pinned inputs")
    print("PASS: exact parent source/binaries, fixed mesh and unchanged stage settings")


if __name__ == "__main__":
    main()
