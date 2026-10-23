"""Check the selected inspection VTUs and the reviewed meeting PDF."""

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PDF_SHA256 = "58b92dfb89e3cac0f38c0ecfc7c95ac2995abb35f74fcdaec2ec182effd86c4f"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    with (ROOT / "selected_vtu_manifest.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 5, f"expected five selected VTUs, found {len(rows)}"
    expected_names = {row["file"] for row in rows}
    assert len(expected_names) == len(rows), "duplicate selected VTU filename"
    actual_names = {path.name for path in (ROOT / "selected_vtu").glob("*.vtu")}
    assert actual_names == expected_names, "selected VTU set differs from manifest"

    for row in rows:
        path = ROOT / "selected_vtu" / row["file"]
        assert path.stat().st_size == int(row["bytes"]), f"size mismatch: {row['file']}"
        assert sha256(path) == row["sha256"], f"SHA-256 mismatch: {row['file']}"

    pdf = ROOT / "meeting_book" / "main.pdf"
    assert sha256(pdf) == PDF_SHA256, "meeting PDF SHA-256 mismatch"
    print("verified five selected VTUs and meeting PDF")


if __name__ == "__main__":
    main()
