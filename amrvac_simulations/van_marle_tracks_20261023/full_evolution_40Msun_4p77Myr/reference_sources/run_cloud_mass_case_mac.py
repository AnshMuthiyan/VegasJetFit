#!/usr/bin/env python3
"""Run one serial AMRVAC case on macOS with a wall-time guard and fixed records."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import signal
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_file", type=Path)
    parser.add_argument("case")
    parser.add_argument("guard_seconds", type=int)
    args = parser.parse_args()
    if args.guard_seconds <= 0 or not args.case.isidentifier():
        parser.error("guard must be positive and case must be an identifier")

    binary = Path("amrvac")
    source = Path("mod_usr.t")
    parameter = Path(f"{args.case}.par")
    for path in (binary, source, args.base_file, parameter):
        if not path.is_file():
            parser.error(f"missing input: {path}")
    records = [Path(f"{args.case}.run.{suffix}") for suffix in ("log", "err", "exit", "sha256")]
    if not Path("output").is_dir():
        parser.error("missing output directory")
    if any(path.exists() for path in records) or list(Path("output").glob(f"{args.case}*.vtu")):
        parser.error("case already has results; refusing to overwrite")

    with records[3].open("x", encoding="ascii") as stream:
        for path in (binary, source, args.base_file, parameter):
            stream.write(f"{sha256(path)}  {path}\n")

    status = 1
    with records[0].open("x", encoding="utf-8") as stdout, records[1].open("x", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            [str(binary.resolve()), "-i", str(args.base_file), str(parameter)],
            stdout=stdout, stderr=stderr, start_new_session=True,
        )
        try:
            status = process.wait(timeout=args.guard_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            status = 124
    records[2].write_text(f"{status}\n", encoding="ascii")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
