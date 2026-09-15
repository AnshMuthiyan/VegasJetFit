#!/usr/bin/env python3
"""Inventory IGM/host-H-I sensitivity for an authoritative GRB manifest."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jetfit.core.bandpass import C_ANGSTROM_PER_SECOND, get_bandpass
from jetfit.core.hydrogen_absorption import hydrogen_transmission


def fixed_redshift(model_path: Path) -> float:
    with model_path.open("rb") as handle:
        config = tomllib.load(handle)
    redshifts = [
        entry for entry in config.get("model", [])
        if entry.get("name") == "z" and "value" in entry
    ]
    if len(redshifts) != 1:
        raise ValueError(f"Expected one fixed redshift in {model_path}.")
    return float(redshifts[0]["value"])


def wavelength_angstrom(row: dict[str, str]) -> float:
    value = float(row["Wave"])
    unit = row["WaveUnits"].strip().lower()
    if unit == "hz":
        return C_ANGSTROM_PER_SECOND / value
    if unit == "thz":
        return C_ANGSTROM_PER_SECOND / (value * 1.0e12)
    if unit in {"angstrom", "angstroms", "aa"}:
        return value
    if unit == "nm":
        return 10.0 * value
    raise ValueError(f"Unsupported wavelength/frequency unit {row['WaveUnits']!r}.")


def included_spectral_rows(obs_path: Path) -> list[dict[str, str]]:
    with obs_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        row for row in rows
        if str(row.get("Include", "")).strip().lower() in {"1", "true", "yes"}
        and row.get("ValueType") == "Spectral Flux"
    ]


def audit_event(event: str, result: Path) -> list[dict[str, object]]:
    z = fixed_redshift(result / "model.toml")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in included_spectral_rows(result / "obs.csv"):
        grouped[row.get("Filter", "")].append(row)

    output = []
    for band, rows in sorted(grouped.items(), key=lambda item: item[0].lower()):
        central_wavelengths = np.asarray(
            [wavelength_angstrom(row) for row in rows], dtype=float
        )
        central_igm = hydrogen_transmission(
            central_wavelengths, z, igm_model="inoue2014"
        )
        central_host21 = hydrogen_transmission(
            central_wavelengths,
            z,
            host_model="trotter2011",
            nhi_host_cm2=1.0e21,
        )
        response = get_bandpass(band)
        if response is None:
            treatment = "central_wavelength_approximation"
            response_file = ""
            response_min = float("nan")
            response_max = float("nan")
            response_igm = float("nan")
            response_host21 = float("nan")
        else:
            treatment = "verified_full_response"
            wavelength, weight = response.photon_quadrature(None)
            response_file = str(response.source_file.relative_to(ROOT))
            response_min = float(wavelength.min())
            response_max = float(wavelength.max())
            response_igm = float(np.sum(
                hydrogen_transmission(wavelength, z, igm_model="inoue2014")
                * weight
            ))
            response_host21 = float(np.sum(
                hydrogen_transmission(
                    wavelength,
                    z,
                    host_model="trotter2011",
                    nhi_host_cm2=1.0e21,
                ) * weight
            ))
        audit_igm = (
            response_igm
            if np.isfinite(response_igm)
            else float(np.median(central_igm))
        )
        output.append({
            "event": event,
            "redshift": z,
            "filter": band,
            "included_rows": len(rows),
            "treatment": treatment,
            "response_file": response_file,
            "central_wavelength_min_A": float(central_wavelengths.min()),
            "central_wavelength_median_A": float(np.median(central_wavelengths)),
            "central_wavelength_max_A": float(central_wavelengths.max()),
            "igm_transmission_central_min": float(np.min(central_igm)),
            "igm_transmission_central_median": float(np.median(central_igm)),
            "igm_transmission_central_max": float(np.max(central_igm)),
            "host_logNHI21_transmission_central_median": float(np.median(central_host21)),
            "response_wavelength_min_A": response_min,
            "response_wavelength_max_A": response_max,
            "igm_transmission_flat_fnu_response_mean": response_igm,
            "host_logNHI21_transmission_flat_fnu_response_mean": response_host21,
            "igm_material_at_central_wavelength": bool(np.min(central_igm) < 0.99),
            "igm_transmission_used_for_likelihood_audit": audit_igm,
            "igm_material_in_likelihood_audit": bool(audit_igm < 0.99),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--share-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    rows = []
    for record in manifest["events"]:
        result = args.share_root / record["result_path"]
        rows.extend(audit_event(record["event"], result))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    material = [row for row in rows if row["igm_material_in_likelihood_audit"]]
    verified = sum(row["treatment"] == "verified_full_response" for row in rows)
    print(f"rows={len(rows)} verified={verified} material_igm={len(material)}")
    for row in material:
        print(
            f"{row['event']} {row['filter'] or '<blank>'} z={row['redshift']} "
            f"T_IGM={row['igm_transmission_used_for_likelihood_audit']:.6g} "
            f"{row['treatment']}"
        )
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
