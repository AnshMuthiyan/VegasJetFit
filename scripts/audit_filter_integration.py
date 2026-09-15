#!/usr/bin/env python3
"""Inventory campaign filters and report verified bandpass coverage."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jetfit.core.bandpass import get_bandpass


def classify(name: str, frequency_hz: float):
    response = get_bandpass(name)
    if response is not None:
        return "integrated_verified", response.canonical_name, str(response.source_file)
    lower = name.strip().lower()
    if lower == "xray":
        return "not_photometric_band", "", "X-ray spectral/integrated observable"
    if frequency_hz < 1.0e12:
        return "radio_frequency_channel", "", "modeled at measured frequency"
    return (
        "instrument_ambiguous_monochromatic",
        "",
        "telescope/camera response not encoded in observation label",
    )


def inventory(campaign: Path):
    rows = []
    for obs_path in sorted(campaign.glob("*/obs.csv")):
        event = obs_path.parent.name
        counts = Counter()
        frequencies = {}
        with obs_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("Include", "1")).strip() not in ("1", "1.0", "True", "true"):
                    continue
                if row.get("ValueType") != "Spectral Flux":
                    continue
                band = str(row.get("Filter", "")).strip()
                try:
                    frequency = float(row.get("Wave", "nan"))
                except ValueError:
                    continue
                counts[band] += 1
                frequencies.setdefault(band, frequency)
        for band in sorted(counts, key=str.lower):
            frequency = frequencies[band]
            status, canonical, source = classify(band, frequency)
            response = get_bandpass(band)
            rows.append({
                "event": event,
                "filter": band,
                "included_points": counts[band],
                "nominal_frequency_hz": f"{frequency:.9g}",
                "status": status,
                "canonical_response": canonical,
                "pivot_wavelength_angstrom": (
                    f"{response.pivot_wavelength_angstrom:.4f}" if response else ""
                ),
                "response_source": source,
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = inventory(args.campaign)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    summary = Counter(row["status"] for row in rows)
    print(f"Wrote {len(rows)} event/filter rows to {args.output}")
    for key, count in sorted(summary.items()):
        print(f"{key}: {count}")


if __name__ == "__main__":
    main()
