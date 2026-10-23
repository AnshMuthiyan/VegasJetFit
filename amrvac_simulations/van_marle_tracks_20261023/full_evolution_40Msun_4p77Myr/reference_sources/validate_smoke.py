#!/usr/bin/env python3
"""Validate the isolated ten-year initial-HII hydro smoke VTUs."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

import numpy as np

from preflight import PC_CM, YEAR_S, MP_G


RHO_UNIT = 1.0e-25
SPEED_UNIT = 1.0e7
PRESSURE_UNIT = RHO_UNIT * SPEED_UNIT**2
MU_HD = 1.4 / 2.3
MU_MOLECULAR = 2.33
TEMP_UNIT = MU_HD * MP_G * SPEED_UNIT**2 / 1.380649e-16
RHO_AMBIENT = 1.4 * MP_G * 1.0e3


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
                raise ValueError("non-float32 VTU data length")
            return np.frombuffer(raw, dtype="<f4", count=byte_count // 4, offset=offset + 4)

        radius = values(r'<Points>\s*<DataArray[^>]*offset="\s*(\d+)"').reshape(-1, 3)[:, 0]
        fields = [
            values(r'<DataArray[^>]*Name="' + name + r'"[^>]*offset="\s*(\d+)"')
            for name in ("rho", "v1", "p")
        ]
        chunks.append(np.column_stack((radius, *fields)))
    if not chunks:
        raise ValueError("no VTU pieces")
    return age * PC_CM / SPEED_UNIT / YEAR_S, np.concatenate(chunks)


def validate(root: Path) -> None:
    log = (root / "run.log").read_text(encoding="utf-8")
    if "Finished AMRVAC" not in log or (root / "run.err").stat().st_size:
        raise ValueError("missing normal completion marker or nonempty stderr")
    for index, expected_yr in ((0, 0.0), (1, 10.0)):
        age, data = read_vtu(root / f"ionized_core_smoke{index:04d}.vtu")
        if not np.isclose(age, expected_yr, atol=0.01):
            raise ValueError(f"save {index}: unexpected age {age:g} yr")
        if not np.all(np.isfinite(data)) or np.any(data[:, 1] <= 0) or np.any(data[:, 3] <= 0):
            raise ValueError(f"save {index}: nonfinite or nonpositive fields")
        outer = data[:, 0] > 2.0
        if not np.any(outer) or not np.isclose(
            np.median(data[outer, 1]) * RHO_UNIT, RHO_AMBIENT, rtol=1e-4
        ):
            raise ValueError(f"save {index}: outer density differs from input")
        if index == 0:
            t_equiv = data[:, 3] / data[:, 1] * TEMP_UNIT
            hot = (data[:, 0] > 0.2) & (data[:, 0] < 0.7)
            cold = (data[:, 0] > 1.1) & (data[:, 0] < 1.8)
            if not np.any(hot) or not np.any(cold):
                raise ValueError("missing ionized or molecular samples")
            if not np.isclose(np.median(t_equiv[hot]), 1.0e4, rtol=1e-3):
                raise ValueError("ionized-zone pressure incorrect")
            if not np.isclose(
                np.median(t_equiv[cold]), 20.0 * MU_HD / MU_MOLECULAR, rtol=1e-3
            ):
                raise ValueError("molecular-zone pressure incorrect")
        print(
            f"save {index}: age={age:.6f} yr, {len(data)} points, "
            f"min rho={np.min(data[:, 1])*RHO_UNIT:.3e} g/cm3, "
            f"min p={np.min(data[:, 3])*PRESSURE_UNIT:.3e} dyn/cm2 PASS"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    validate(parser.parse_args().root)


if __name__ == "__main__":
    main()
