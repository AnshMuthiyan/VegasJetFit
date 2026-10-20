#!/usr/bin/env python3
"""Check an AMRVAC 2D initial VTU before time-advancing runs."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

import numpy as np


PC_CM = 3.0857e18
YEAR_S = 3.1536e7
AMBIENT_RHO = 10.0 ** (-22.5)
RHO_UNIT = 1.0e-25
VELOCITY_UNIT = 1.0e7
PRESSURE_UNIT = RHO_UNIT * VELOCITY_UNIT**2
CENTERS = {"star40": (0.0,), "star25": (0.0,), "both": (-8.1, 8.1)}


def read_vtu(path: Path) -> tuple[float, np.ndarray]:
    raw = path.read_bytes()
    appended = raw.index(b"<AppendedData")
    base = raw.index(b"_", appended) + 1
    header = raw[:appended].decode("ascii")
    age = float(re.search(r'Name="TIME"[^>]*>\s*([^<]+)', header).group(1))
    chunks = []

    for piece in re.finditer(r"<Piece\b[^>]*>(.*?)</Piece>", header, re.S):
        body = piece.group(1)

        def values(pattern: str) -> np.ndarray:
            match = re.search(pattern, body, re.S)
            if match is None:
                raise ValueError(f"missing VTU array: {pattern}")
            offset = base + int(match.group(1))
            byte_count = struct.unpack_from("<I", raw, offset)[0]
            if byte_count % 4:
                raise ValueError("non-float32 data length")
            return np.frombuffer(raw, dtype="<f4", count=byte_count // 4, offset=offset + 4)

        xyz = values(r'<Points>\s*<DataArray[^>]*offset="\s*(\d+)"').reshape(-1, 3)
        fields = [
            values(r'<DataArray[^>]*Name="' + name + r'"[^>]*offset="\s*(\d+)"')
            for name in ("rho", "v1", "v2", "p")
        ]
        chunks.append(
            np.column_stack(
                (
                    xyz[:, 0],
                    xyz[:, 1],
                    fields[0] * RHO_UNIT,
                    fields[1] * VELOCITY_UNIT,
                    fields[2] * VELOCITY_UNIT,
                    fields[3] * PRESSURE_UNIT,
                )
            )
        )
    if not chunks:
        raise ValueError("no VTU pieces")
    return age, np.concatenate(chunks)


def validate(path: Path, case: str, expected_age_myr: float = 0.0) -> str:
    time, data = read_vtu(path)
    age_myr = time * PC_CM / VELOCITY_UNIT / YEAR_S / 1.0e6
    if not np.isclose(age_myr, expected_age_myr, atol=1e-6) or not np.all(np.isfinite(data)):
        raise ValueError(f"saved age {age_myr:g} Myr differs from expected age or fields are nonfinite")
    if np.any(data[:, 2] <= 0) or np.any(data[:, 5] <= 0):
        raise ValueError("nonpositive density or pressure")
    centers = CENTERS[case]
    distance = np.minimum.reduce([np.hypot(data[:, 0], data[:, 1] - z) for z in centers])
    ambient = distance > 10.0
    if not np.any(ambient):
        raise ValueError("no ambient samples")
    median_rho = float(np.median(data[ambient, 2]))
    if not np.isclose(median_rho, AMBIENT_RHO, rtol=1e-4):
        raise ValueError(f"ambient density {median_rho:g} differs from {AMBIENT_RHO:g}")
    for z in centers:
        inner = np.hypot(data[:, 0], data[:, 1] - z) < 1.25
        if np.count_nonzero(inner) < 2:
            raise ValueError(f"missing source samples near z={z:g} pc")
        if float(np.median(data[inner, 2])) >= AMBIENT_RHO / 10:
            raise ValueError(f"wind region near z={z:g} pc lacks low density")
        if float(np.max(np.hypot(data[inner, 3], data[inner, 4]))) < 1e7:
            raise ValueError(f"wind region near z={z:g} pc lacks velocity")
    return (
        f"{case}: {len(data)} points, age={age_myr:.6f} Myr, "
        f"{len(centers)} source(s), rho_ISM={median_rho:.6e}, finite-positive PASS"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vtu", type=Path)
    parser.add_argument("--case", choices=CENTERS, required=True)
    parser.add_argument("--expected-age-myr", type=float, default=0.0)
    args = parser.parse_args()
    print(validate(args.vtu, args.case, args.expected_age_myr))


if __name__ == "__main__":
    main()
