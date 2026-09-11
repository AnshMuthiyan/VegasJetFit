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


if __name__ == "__main__":
    unittest.main()
