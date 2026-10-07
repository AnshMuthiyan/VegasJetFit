import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from jetfit.run import log


class RunMetadataTests(unittest.TestCase):
    def test_log_records_distinct_burn_and_production_lengths(self):
        sampler = SimpleNamespace(
            name="parallel_tempered",
            iteration=100,
            nwalkers=100,
            get_log_prob=lambda flat=True: np.array([-3.0, -2.0]),
        )
        ampy = SimpleNamespace(
            mcmc=SimpleNamespace(
                sampler=sampler,
                params=SimpleNamespace(model="TestModel"),
            ),
            get_best_params=lambda: {"model": {"p": 2.2}},
        )

        with tempfile.TemporaryDirectory() as directory:
            log(ampy, Path(directory), burn_length=25, run_length=100)
            payload = json.loads(Path(directory, "best_fit.json").read_text())

        self.assertEqual(payload["mcmc"]["burn_len"], 25)
        self.assertEqual(payload["mcmc"]["prod_len"], 100)

    def test_log_records_band_treatment_provenance(self):
        sampler = SimpleNamespace(
            name="parallel_tempered", iteration=100, nwalkers=100,
            get_log_prob=lambda flat=True: np.array([-3.0, -2.0]),
        )
        seen_z = []

        def treatment(z):
            seen_z.append(z)
            return {"uvw2": {"treatment": "integrated", "response_source": "instrument",
                             "response_file": "swuw2_20041120v105.arf",
                             "reason": "verified response"},
                    "r": {"treatment": "monochromatic", "response_source": "monochromatic",
                          "response_file": None,
                          "reason": "no response registered for this label"}}

        models = SimpleNamespace(bandpass_mode="verified", bandpass_nodes=16,
                                 bandpass_selective=True, bandpass_x_threshold=3.3,
                                 bandpass_treatment=treatment)
        ampy = SimpleNamespace(
            mcmc=SimpleNamespace(sampler=sampler, models=models,
                                 params=SimpleNamespace(model="TestModel")),
            get_best_params=lambda: {"model": {"p": 2.2, "z": 0.544}},
        )
        with tempfile.TemporaryDirectory() as directory:
            log(ampy, Path(directory), burn_length=25, run_length=100)
            payload = json.loads(Path(directory, "best_fit.json").read_text())

        photometry = payload["photometry"]
        self.assertEqual(seen_z, [0.544])  # evaluated at the best-fit redshift
        self.assertTrue(photometry["bandpass_selective"])
        self.assertEqual(photometry["bandpass_x_threshold_inv_micron"], 3.3)
        self.assertEqual(photometry["band_treatment"]["uvw2"]["treatment"], "integrated")
        self.assertEqual(photometry["band_treatment"]["r"]["response_source"], "monochromatic")


if __name__ == "__main__":
    unittest.main()
