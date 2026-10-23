#!/usr/bin/env python3
"""Focused tests for quality-gated log-radius inventory."""

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory_shell_radius_coverage import inventory, radius_bin, summarize


class RadiusCoverageTests(unittest.TestCase):
    def test_bin_bounds(self):
        self.assertEqual(radius_bin(0.1), 0)
        self.assertEqual(radius_bin(1.0), 5)
        self.assertEqual(radius_bin(10.0), 9)
        self.assertIsNone(radius_bin(0.099))
        self.assertIsNone(radius_bin(10.01))
        self.assertEqual(radius_bin(0.01, 0.01), 0)
        self.assertEqual(radius_bin(0.1, 0.01), 5)
        self.assertEqual(radius_bin(1.0, 0.01), 10)
        self.assertEqual(radius_bin(10.0, 0.01), 14)
        self.assertIsNone(radius_bin(0.009, 0.01))

    def test_summary_counts_distinct_cases_and_resolved_ramps(self):
        rows = [{"case": "a", "age_myr": 0.01, "inner_radius_pc": 0.12,
                 "inner_ramp_resolved": False, "bin_index": 0,
                 "shell_inner_nh_cm3": "100"},
                {"case": "a", "age_myr": 0.02, "inner_radius_pc": 0.13,
                 "inner_ramp_resolved": True, "bin_index": 0,
                 "shell_inner_nh_cm3": "200"},
                {"case": "b", "age_myr": 0.02, "inner_radius_pc": 0.9,
                 "inner_ramp_resolved": False, "bin_index": 4,
                 "shell_inner_nh_cm3": "300"}]
        bins = summarize(rows)
        self.assertEqual(bins[0]["snapshot_count"], 2)
        self.assertEqual(bins[0]["distinct_case_count"], 1)
        self.assertEqual(bins[0]["ramp_resolved_count"], 1)
        self.assertEqual(bins[4]["representative_case"], "b")
        self.assertEqual(bins[9]["snapshot_count"], 0)

    def test_extended_summary_keeps_empty_small_radius_bins(self):
        bins = summarize([], min_radius_pc=0.01)
        self.assertEqual(len(bins), 15)
        self.assertAlmostEqual(bins[0]["radius_lo_pc"], 0.01)
        self.assertAlmostEqual(bins[5]["radius_lo_pc"], 0.1)
        self.assertEqual(sum(row["snapshot_count"] for row in bins), 0)
        fit_bins = summarize([], min_radius_pc=0.001)
        self.assertEqual(len(fit_bins), 20)
        self.assertAlmostEqual(fit_bins[0]["radius_lo_pc"], 0.001)
        self.assertAlmostEqual(fit_bins[10]["radius_lo_pc"], 0.1)
        self.assertEqual(radius_bin(0.001225, 0.001), 0)

    def test_additional_diagnostics_join_without_silencing_duplicates(self):
        fields = ("case", "age_myr", "inner_radius_pc", "shell_quality_pass",
                  "inner_edge_status", "shell_inner_nh_cm3", "shell_peak_nh_cm3",
                  "shell_fwhm_cells", "shell_contrast", "inner_ramp_cells",
                  "inner_ramp_resolved")
        with tempfile.TemporaryDirectory() as temp:
            roots = [Path(temp) / name for name in ("first", "second")]
            for root, age in zip(roots, (0.01, 0.02)):
                folder = root / "case_agefix"
                folder.mkdir(parents=True)
                with (folder / "inner_shell_metrics.csv").open("w", newline="", encoding="ascii") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerow({"case": "case", "age_myr": age,
                                     "inner_radius_pc": 0.08, "shell_quality_pass": True,
                                     "inner_edge_status": "measured", "shell_inner_nh_cm3": 100,
                                     "shell_peak_nh_cm3": 200, "shell_fwhm_cells": 6,
                                     "shell_contrast": 4, "inner_ramp_cells": 3,
                                     "inner_ramp_resolved": False})
            with patch("inventory_shell_radius_coverage.manifest_cases", return_value={"case": {}}):
                rows = inventory(Path(temp), roots[0], 0.001, (roots[1],))
                self.assertEqual(len(rows), 2)
                self.assertTrue(all(row["accepted_for_coverage"] for row in rows))
                with self.assertRaisesRegex(ValueError, "duplicate diagnostic snapshot"):
                    inventory(Path(temp), roots[0], 0.001, (roots[0],))


if __name__ == "__main__":
    unittest.main()
