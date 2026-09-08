#!/usr/bin/env python3
"""Prepare final seeded core-logangle campaign configs without launching jobs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.mcmc.parameters import Parameters
from scripts.build_thesis_reproduction_model_toml import _load_toml, _write_toml


DEFAULT_SOURCE_CAMPAIGN = Path(
    "/Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/unseeded_runs/"
    "26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports/core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_pending"
RUN_TAG = "core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_v1"

SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")
HST_OFFSETS_220101A = {
    "F775W_offset": 0.03,
    "F125W_offset": 0.04,
}
MW_RV_EVENT = "221009A"
MW_RV_PRIOR_NAME = "rv_milky_way"
ALIASES = {
    "eps_B": "eps_b",
    "eps_b": "eps_B",
    "dL28": "dl28",
    "dL": "dl28",
    "dl": "dl28",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-campaign", type=Path, default=DEFAULT_SOURCE_CAMPAIGN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--density-log10-upper", type=float, default=10.0)
    parser.add_argument("--density-log10-lower", type=float, default=-5.0)
    parser.add_argument("--min-initial-sigma", type=float, default=1.0e-3)
    return parser.parse_args()


def campaign_runs(campaign: Path) -> list[Path]:
    return sorted(
        path
        for path in campaign.iterdir()
        if path.is_dir()
        and path.name != "trash"
        and (path / "model.toml").is_file()
        and (path / "chain.npz").is_file()
        and (path / "minimized" / "minimized.json").is_file()
    )


def entry_name(entry: dict[str, Any]) -> str | None:
    name = entry.get("name")
    return name if isinstance(name, str) else None


def candidate_names(name: str) -> tuple[str, ...]:
    alias = ALIASES.get(name)
    return (name, alias) if alias else (name,)


def fitting_names(model_toml: Path) -> list[str]:
    return [param.name for param in Parameters.from_toml(model_toml).fitting]


def chain_arrays(run: Path, names: list[str]) -> dict[str, np.ndarray]:
    with np.load(run / "chain.npz") as data:
        chain = np.asarray(data["chain"], dtype=float)
    flat = chain.reshape(-1, chain.shape[-1])
    return {name: flat[:, index] for index, name in enumerate(names)}


def minimized_vector(run: Path, names: list[str]) -> dict[str, float]:
    payload = json.loads((run / "minimized" / "minimized.json").read_text())
    x = np.asarray(payload["x"], dtype=float)
    if x.size != len(names):
        raise ValueError(f"{run.name}: minimized vector length {x.size} != {len(names)}")
    return {name: float(value) for name, value in zip(names, x)}


def posterior_sigma(values: np.ndarray, fallback: float) -> tuple[float, float, float, float]:
    finite = np.asarray(values[np.isfinite(values)], dtype=float)
    if finite.size == 0:
        return float("nan"), float("nan"), float("nan"), fallback
    q16, q50, q84 = np.quantile(finite, [0.16, 0.50, 0.84])
    sigma = 0.5 * float(q84 - q16)
    if not math.isfinite(sigma) or sigma <= 0.0:
        sigma = fallback
    return float(q16), float(q50), float(q84), max(float(sigma), fallback)


def ensure_220101a_hst_offsets(config: dict[str, Any]) -> None:
    offsets = config.setdefault("offsets", [])
    if not isinstance(offsets, list):
        raise TypeError("Config offsets section must be a list")

    existing = {entry.get("name") for entry in offsets if isinstance(entry, dict)}
    for name, sigma in HST_OFFSETS_220101A.items():
        if name in existing:
            continue
        offsets.append(
            {
                "name": name,
                "scale": "linear",
                "prior": {
                    "type": "gaussian",
                    "mu": 0.0,
                    "sigma": sigma,
                },
            }
        )


def ensure_221009a_milky_way_rv_prior(config: dict[str, Any]) -> None:
    entries = config.get("extinction")
    if not isinstance(entries, list):
        raise TypeError("Config extinction section must be a list")

    for entry in entries:
        if isinstance(entry, dict) and entry.get("name") == MW_RV_PRIOR_NAME:
            entry["scale"] = "log"
            entry.pop("value", None)
            entry["prior"] = {"type": "milkywayrv"}
            return
    raise KeyError(f"{MW_RV_EVENT} config is missing {MW_RV_PRIOR_NAME}")


def seed_config(
    run: Path,
    output_path: Path,
    density_lower: float,
    density_upper: float,
    min_initial_sigma: float,
) -> list[dict[str, Any]]:
    config = _load_toml(run / "model.toml")
    names = fitting_names(run / "model.toml")
    chains = chain_arrays(run, names)
    minimized = minimized_vector(run, names)
    audits: list[dict[str, Any]] = []

    for section in SECTION_ORDER:
        entries = config.get(section)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry_name(entry)
            prior = entry.get("prior")
            if name is None or not isinstance(prior, dict):
                continue
            if "lower" not in prior or "upper" not in prior:
                continue

            old_lower = float(prior["lower"])
            old_upper = float(prior["upper"])
            if section == "model" and name == "n017":
                prior["lower"] = float(density_lower)
                prior["upper"] = float(density_upper)

            source_name = next((candidate for candidate in candidate_names(name) if candidate in minimized), None)
            if source_name is None:
                continue

            lower = float(prior["lower"])
            upper = float(prior["upper"])
            if not (math.isfinite(lower) and math.isfinite(upper) and upper > lower):
                continue

            q16, q50, q84, sigma = posterior_sigma(chains[source_name], min_initial_sigma)
            sigma = min(sigma, 0.5 * (upper - lower))
            guess_unclipped = float(minimized[source_name])
            guess = min(max(guess_unclipped, lower), upper)
            prior["initial_guess"] = guess
            prior["initial_sigma"] = sigma
            audits.append(
                {
                    "event": run.name,
                    "section": section,
                    "name": name,
                    "source_name": source_name,
                    "scale": entry.get("scale", ""),
                    "old_lower": old_lower,
                    "old_upper": old_upper,
                    "lower": lower,
                    "upper": upper,
                    "minimized_fit_value_unclipped": guess_unclipped,
                    "initial_guess": guess,
                    "posterior_q16": q16,
                    "posterior_median": q50,
                    "posterior_q84": q84,
                    "initial_sigma": sigma,
                    "n_chain_samples": int(np.isfinite(chains[source_name]).sum()),
                }
            )

    if run.name == "220101A":
        ensure_220101a_hst_offsets(config)
    if run.name == MW_RV_EVENT:
        ensure_221009a_milky_way_rv_prior(config)

    _write_toml(output_path, config)
    return audits


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_queue(path: Path, runs: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event", "csm_family", "queue_order", "note"])
        for index, run in enumerate(runs, start=1):
            writer.writerow(
                [
                    run.name,
                    "power_law",
                    index,
                    "pending_final_seeded_review;do_not_launch_until_meeting_notes_are_applied",
                ]
            )


def write_pending_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event", "host", "csm_family", "queue_order", "workers", "run_tag", "launched_utc"])


def write_run_card(path: Path, args: argparse.Namespace, runs: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Final Seeded k[-10,3] 10-Temperature Campaign Pending Review

Status: prepared only; do not launch until meeting notes have been applied per event.

- Source campaign: `{args.source_campaign.resolve()}`
- Config directory: `{args.output_dir.resolve()}`
- Report directory: `{args.report_dir.resolve()}`
- Run tag: `{RUN_TAG}`
- Density prior change: `log10(n_0,17)` upper bound set to `{args.density_log10_upper}`.
- Seeding: `initial_guess` from each event's minimized best fit; `initial_sigma` from half of each posterior 16th-84th interval in fit space.
- 220101A data handling: standard obs loading is used, but the resource CSV must include `F775W`/`F125W` and Dylan's early X-ray clump near `t~10^-2.7 d`; the event runner validates this before launch, and this prep script adds the matching HST offset priors.
- 221009A Milky Way prior: `rv_milky_way` must use the custom `milkywayrv` prior, not a broad uniform log prior; the event runner validates this before launch, and this prep script enforces it when regenerating pending configs.
- Event count: `{len(runs)}`

Launch command to use later, after review:

```bash
cd /Users/jkeohane/GRBs/VegasJetFit
PYTHONPATH=/Users/jkeohane/GRBs/VegasJetFit /Users/jkeohane/GRBs/.venv/bin/python scripts/dynamic_dispatch_campaign.py \\
  --queue {args.report_dir.resolve()}/dynamic_event_queue.csv \\
  --manifest {args.report_dir.resolve()}/dispatch_manifest.csv \\
  --run-tag {RUN_TAG} \\
  --event-script scripts/run_core_logangle_powerlaw_15grb_event.sh \\
  --campaign /Users/jkeohane/GRBs/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_07__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__final_seeded__10_temperature_5000x5000 \\
  --session-prefix core_logangle_powerlaw_kminus10to3_final_seeded_10temp_5000 \\
  --busy-pattern core_logangle_powerlawcsm \\
  --sync-path {args.output_dir.resolve()} \\
  --sync-path /Users/jkeohane/GRBs/VegasJetFit/Ansh_Run/mcmc_settings_core_logangle_kminus10to3_10temp_5000x5000.toml \\
  --sync-path {args.report_dir.resolve()} \\
  --env CONFIG_DIR={args.output_dir.resolve()} \\
  --env MCMC_SETTINGS=/Users/jkeohane/GRBs/VegasJetFit/Ansh_Run/mcmc_settings_core_logangle_kminus10to3_10temp_5000x5000.toml
```
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_campaign = args.source_campaign.expanduser().resolve()
    args.source_campaign = source_campaign
    args.output_dir = args.output_dir.expanduser().resolve()
    args.report_dir = args.report_dir.expanduser().resolve()

    runs = campaign_runs(source_campaign)
    if not runs:
        raise SystemExit(f"No completed source runs found under {source_campaign}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    audit_rows: list[dict[str, Any]] = []
    for run in runs:
        output_path = args.output_dir / f"{run.name}.toml"
        audit_rows.extend(
            seed_config(
                run,
                output_path,
                args.density_log10_lower,
                args.density_log10_upper,
                args.min_initial_sigma,
            )
        )
        print(f"WROTE {output_path}")

    audit_csv = args.report_dir / "seed_audit.csv"
    write_csv(audit_csv, audit_rows)
    queue_csv = args.report_dir / "dynamic_event_queue.csv"
    write_queue(queue_csv, runs)
    manifest = args.report_dir / "dispatch_manifest.csv"
    write_pending_manifest(manifest)
    run_card = args.report_dir / "RUN_CARD.md"
    write_run_card(run_card, args, runs)

    print(f"AUDIT {audit_csv}")
    print(f"QUEUE {queue_csv}")
    print(f"PENDING_MANIFEST {manifest}")
    print(f"RUN_CARD {run_card}")
    print("NOT_LAUNCHED true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
