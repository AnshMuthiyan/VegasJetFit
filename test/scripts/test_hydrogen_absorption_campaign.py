from pathlib import Path

import toml

from scripts.prepare_hydrogen_absorption_comparison import MCMC_DIAGNOSTIC
from scripts.write_hydrogen_absorption_comparison_report import tag


ROOT = Path(__file__).resolve().parents[2]


def test_diagnostic_dimensions_match_launch_watch_and_report():
    sampler = toml.loads(MCMC_DIAGNOSTIC)["sampler"]
    burn = int(sampler["burn_length"])
    production = int(sampler["run_length"])
    dimensions = f"{burn}x{production}"

    assert dimensions == "12x40"
    assert tag("220101A", "igm").endswith(f"5temp_{dimensions}_v1")

    launcher = (ROOT / "scripts/run_hydrogen_absorption_variant.sh").read_text()
    watcher = (ROOT / "scripts/watch_hydrogen_absorption_comparison.sh").read_text()
    assert f'dimensions="{dimensions}"' in launcher
    assert f"dimensions={dimensions}" in watcher
    assert f'else {production}' in watcher
