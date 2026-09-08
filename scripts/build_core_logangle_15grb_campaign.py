#!/usr/bin/env python3
"""Build the 15-GRB unseeded core-parameter/log-angle campaign configs."""

from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import math
from pathlib import Path
from typing import Any

import toml


POWERLAW_EVENTS = (
    "050525A",
    "050922C",
    "090424",
    "090618",
    "111228A",
    "130612A",
    "131030A",
    "140506A",
    "160131A",
    "171010A",
    "210905A",
    "220101A",
    "221009A",
)
SBPL_EVENTS = ("080319B", "080413B")
EVENTS = tuple(sorted(POWERLAW_EVENTS + SBPL_EVENTS))
HST_OFFSETS_220101A = {
    "F775W_offset": 0.03,
    "F125W_offset": 0.04,
}
MW_RV_EVENT = "221009A"
MW_RV_PRIOR_NAME = "rv_milky_way"


def entry_by_name(entries: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for entry in entries:
        if entry.get("name") == name:
            return entry
    raise KeyError(f"Missing parameter {name!r}")


def replace_energy_gamma(entries: list[dict[str, Any]]) -> None:
    energy_index = next(
        (
            index
            for index, entry in enumerate(entries)
            if entry.get("name") in {"E52", "E_j_52", "E_j_core_52"}
        ),
        None,
    )
    gamma_index = next(
        (
            index
            for index, entry in enumerate(entries)
            if entry.get("name") in {"lf0", "Gamma_0_core_avg"}
        ),
        None,
    )
    if energy_index is None or gamma_index is None:
        raise KeyError("Source config must contain fitted energy and Gamma parameters")

    entries[energy_index] = {
        "name": "E_j_core_52",
        "scale": "log",
        "prior": {"type": "uniform", "lower": -4.0, "upper": 2.0},
    }
    entries[gamma_index] = {
        "name": "Gamma_0_core_avg",
        "scale": "log",
        "prior": {
            "type": "uniform",
            "lower": math.log10(50.0),
            "upper": math.log10(100000.0),
        },
    }


def set_log_uniform(
    entries: list[dict[str, Any]],
    name: str,
    lower: float,
    upper: float,
) -> None:
    entry = entry_by_name(entries, name)
    entry.pop("value", None)
    entry["scale"] = "log"
    entry["prior"] = {"type": "uniform", "lower": lower, "upper": upper}


def set_linear_uniform(
    entries: list[dict[str, Any]],
    name: str,
    lower: float,
    upper: float,
) -> None:
    entry = entry_by_name(entries, name)
    entry.pop("value", None)
    entry["scale"] = "linear"
    entry["prior"] = {"type": "uniform", "lower": lower, "upper": upper}


def remove_initialization(obj: Any) -> None:
    if isinstance(obj, dict):
        obj.pop("initial_guess", None)
        obj.pop("initial_sigma", None)
        for value in obj.values():
            remove_initialization(value)
    elif isinstance(obj, list):
        for value in obj:
            remove_initialization(value)


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

    entry = entry_by_name(entries, MW_RV_PRIOR_NAME)
    entry["scale"] = "log"
    entry.pop("value", None)
    entry["prior"] = {"type": "milkywayrv"}


def build_config(source: dict[str, Any], event: str) -> dict[str, Any]:
    config = deepcopy(source)
    remove_initialization(config)
    entries = config["model"]
    replace_energy_gamma(entries)

    set_log_uniform(entries, "theta_c", -3.0, 0.0)
    set_log_uniform(entries, "theta_v", -4.0, 0.0)
    set_log_uniform(entries, "eps_e", -6.0, 0.0)

    eps_b_name = "eps_B" if any(e.get("name") == "eps_B" for e in entries) else "eps_b"
    set_log_uniform(entries, eps_b_name, -10.0, 0.0)
    set_linear_uniform(entries, "p", 2.0, 3.5)
    set_linear_uniform(entries, "s", 0.1, 10.0)

    if event in POWERLAW_EVENTS:
        set_log_uniform(entries, "n017", -6.0, 10.0)
    else:
        # SBPL's `nt` value is explicitly log10(n_t/cm^-3) inside the model.
        # Keep scale=linear so JetFit does not exponentiate it before the
        # wrapper applies its own 10**nt conversion.
        nt = entry_by_name(entries, "nt")
        nt.pop("value", None)
        nt["scale"] = "linear"
        nt["prior"] = {"type": "uniform", "lower": -6.0, "upper": 10.0}

    extinction = config.get("extinction", [])
    ebv_source = entry_by_name(extinction, "ebv_source_frame")
    ebv_source.pop("value", None)
    ebv_source["scale"] = "linear"
    ebv_source["prior"] = {"type": "uniform", "lower": 0.0, "upper": 1.0}

    if event == "220101A":
        ensure_220101a_hst_offsets(config)
    if event == MW_RV_EVENT:
        ensure_221009a_milky_way_rv_prior(config)

    return config


def audit_config(config: dict[str, Any], event: str) -> dict[str, Any]:
    entries = config["model"]
    values = {entry["name"]: entry for entry in entries}
    eps_b_name = "eps_B" if "eps_B" in values else "eps_b"
    density_name = "n017" if event in POWERLAW_EVENTS else "nt"
    required = {
        "E_j_core_52": (-4.0, 2.0),
        "Gamma_0_core_avg": (math.log10(50.0), 5.0),
        "theta_c": (-3.0, 0.0),
        "theta_v": (-4.0, 0.0),
        eps_b_name: (-10.0, 0.0),
        "eps_e": (-6.0, 0.0),
    }
    for name, expected in required.items():
        entry = values[name]
        prior = entry["prior"]
        actual = (float(prior["lower"]), float(prior["upper"]))
        if entry.get("scale") != "log" or not all(
            math.isclose(a, b) for a, b in zip(actual, expected)
        ):
            raise ValueError(
                f"{event} {name}: expected log bounds {expected}, got "
                f"scale={entry.get('scale')} bounds={actual}"
            )
        if "initial_guess" in prior or "initial_sigma" in prior:
            raise ValueError(f"{event} {name}: campaign must be unseeded")

    density_entry = values[density_name]
    density_prior = density_entry["prior"]
    density_bounds = (
        float(density_prior["lower"]),
        float(density_prior["upper"]),
    )
    expected_density_scale = "log" if event in POWERLAW_EVENTS else "linear"
    if (
        density_entry.get("scale") != expected_density_scale
        or not all(
            math.isclose(a, b) for a, b in zip(density_bounds, (-6.0, 10.0))
        )
    ):
        raise ValueError(
            f"{event} {density_name}: expected scale={expected_density_scale} "
            f"bounds=(-6,10), got scale={density_entry.get('scale')} "
            f"bounds={density_bounds}"
        )

    if event == "220101A":
        offset_names = {
            entry.get("name")
            for entry in config.get("offsets", [])
            if isinstance(entry, dict)
        }
        missing_hst_offsets = sorted(set(HST_OFFSETS_220101A) - offset_names)
        if missing_hst_offsets:
            raise ValueError(
                f"220101A config is missing HST offsets: {missing_hst_offsets}"
            )

    if event == MW_RV_EVENT:
        extinction_entries = {
            entry.get("name"): entry
            for entry in config.get("extinction", [])
            if isinstance(entry, dict)
        }
        rv_entry = extinction_entries.get(MW_RV_PRIOR_NAME)
        rv_prior = rv_entry.get("prior") if isinstance(rv_entry, dict) else None
        if not isinstance(rv_prior, dict) or rv_prior.get("type") != "milkywayrv":
            raise ValueError(
                f"{MW_RV_EVENT} {MW_RV_PRIOR_NAME}: expected prior type "
                f"'milkywayrv', got {rv_prior}"
            )

    for name, expected in {"p": (2.0, 3.5), "s": (0.1, 10.0)}.items():
        entry = values[name]
        prior = entry["prior"]
        actual = (float(prior["lower"]), float(prior["upper"]))
        if entry.get("scale") != "linear" or not all(
            math.isclose(a, b) for a, b in zip(actual, expected)
        ):
            raise ValueError(f"{event} {name}: expected bounds {expected}, got {actual}")

    ebv_entry = entry_by_name(config["extinction"], "ebv_source_frame")
    ebv_prior = ebv_entry["prior"]
    if (float(ebv_prior["lower"]), float(ebv_prior["upper"])) != (0.0, 1.0):
        raise ValueError(f"{event} ebv_source_frame: expected bounds (0,1)")

    return {
        "event": event,
        "csm_family": "power_law" if event in POWERLAW_EVENTS else "smoothly_broken_power_law",
        "model_name": config["name"],
        "n_fitted": sum("prior" in entry for section in config.values() if isinstance(section, list) for entry in section),
        "energy_log10_E52_lower": -4.0,
        "energy_log10_E52_upper": 2.0,
        "energy_erg_lower": 1.0e48,
        "energy_erg_upper": 1.0e54,
        "gamma_core_lower": 50.0,
        "gamma_core_upper": 100000.0,
        "theta_c_rad_lower": 1.0e-3,
        "theta_c_rad_upper": 1.0,
        "theta_v_rad_lower": 1.0e-4,
        "theta_v_rad_upper": 1.0,
        "density_name": density_name,
        "density_fit_representation": (
            "JetFit log scale"
            if event in POWERLAW_EVENTS
            else "native log10 value passed linearly to SBPL wrapper"
        ),
        "density_log10_lower": -6.0,
        "density_log10_upper": 10.0,
        "epsilon_e_log10_lower": -6.0,
        "epsilon_e_log10_upper": 0.0,
        "epsilon_B_log10_lower": -10.0,
        "epsilon_B_log10_upper": 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--powerlaw-source-dir",
        type=Path,
        default=Path("structured_jet_core_physical_configs_active"),
    )
    parser.add_argument(
        "--sbpl-source-dir",
        type=Path,
        default=Path("structured_jet_sbpl_logejet52_penultimate_configs_active"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("structured_jet_core_logangle_15grb_configs_active"),
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=Path("reports/core_logangle_15grb_campaign/config_audit.csv"),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.audit_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for event in EVENTS:
        source_dir = (
            args.powerlaw_source_dir if event in POWERLAW_EVENTS else args.sbpl_source_dir
        )
        source_path = source_dir / f"{event}.toml"
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        config = build_config(toml.load(source_path), event)
        row = audit_config(config, event)
        output_path = args.output_dir / f"{event}.toml"
        output_path.write_text(toml.dumps(config), encoding="utf-8")
        row["source_config"] = str(source_path.resolve())
        row["output_config"] = str(output_path.resolve())
        rows.append(row)
        print(f"WROTE {event}: {output_path}")

    with args.audit_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"AUDIT {args.audit_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
