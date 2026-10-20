#!/usr/bin/env python3
"""Input-only checks for the short-domain, inward-boundary WR pilot."""

import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from generate_dense_gmc_scan import generate, stretch_ratio
from validate_cloud_mass import atmosphere_table


class LocalBoundaryPilotTests(unittest.TestCase):
    def test_pair_retains_full_atmosphere_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = (("control", 0.001, 0.00025),
                     ("inward", 0.0002, 0.00005))
            for name, inner, first_width in cases:
                output = root / name
                generate(output, cells=8192, selected={"n20000b2000"},
                         suffix=f"_{name}", wr_only=True,
                         wr_duration_myr=0.004,
                         wind_save_interval_myr=0.00025,
                         domain_max_pc=2.5, atmosphere_outer_pc=20.0,
                         inner_override_pc=inner,
                         first_width_override_pc=first_width,
                         host_override="Pauley404-01")
                with (output / "manifest.csv").open(newline="", encoding="ascii") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual([row["stage"] for row in rows], ["atmosphere", "wind"])
                self.assertEqual([int(row["expected_vtus"]) for row in rows], [2, 17])
                self.assertAlmostEqual(float(rows[0]["inner_pc"]), inner)
                self.assertAlmostEqual(float(rows[0]["first_width_pc"]), first_width)
                self.assertEqual(float(rows[0]["domain_max_pc"]), 2.5)
                self.assertEqual(float(rows[0]["atmosphere_outer_pc"]), 20.0)
                base = (output / rows[0]["base_file"]).read_text(encoding="ascii")
                self.assertIn("xprobmax1 = 2.50000000d0", base)
                self.assertIn("atmosphere_outer_pc = 20.00000000d0", base)
                self.assertIn("hd_radiative_cooling = .false.", base)
                self.assertIn("hd_thermal_conduction = .false.", base)
                for row in rows:
                    self.assertLessEqual(len(row["case"] + "0000.vtu"), 80)

    def test_rejects_domain_too_short_for_first_cell(self):
        with self.assertRaises(ValueError):
            stretch_ratio(0.001, 0.00025, 8192, 1.0)

    def test_rejects_short_domain_without_pressure_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "no_reference"
            with self.assertRaises(ValueError):
                generate(output, cells=8192, selected={"n20000b2000"},
                         suffix="_noref", wr_only=True, domain_max_pc=2.5)
            self.assertFalse(output.exists())

    def test_short_outer_boundary_needs_full_pressure_reference(self):
        parameters = dict(n_ref=20000, edge_width=0.5, cloud_pc=2.0,
                          slope=1.8, star_mass_msun=40.0,
                          inner_pc=0.0002, n_bg=2000, finite_gmc=True,
                          n_ext=10.0, gmc_pc=15.0, gmc_edge_width=1.0)
        full = atmosphere_table(domain_max_pc=20.0, **parameters)
        short = atmosphere_table(domain_max_pc=2.5, **parameters)
        full_pressure = np.interp(0.1, full[0], full[3])
        short_pressure = np.interp(0.1, short[0], short[3])
        self.assertLess(short_pressure / full_pressure, 0.95)


if __name__ == "__main__":
    unittest.main()
