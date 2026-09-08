#!/usr/bin/env python3
"""Rebuild the registry for an already-organized GRB `Fits` tree.

This script does not move run directories. It scans the current
`Fits/<jet>/<csm>/<spectrum>/<campaign>/<GRB>` layout, rebuilds
`run_registry.csv` from each `model.toml`, and creates missing `RUN_CARD.md`
files. It is intentionally separate from `organize_share_runs.py`, which is
for moving legacy run folders into the organized tree.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(f"tomllib unavailable: {exc}")

from organize_share_runs import (
    _classify_csm,
    _classify_jet,
    _classify_spectrum,
    _fmt,
    _model_param_names,
    _nmap_and_status,
    _param_names,
)


GRB_DIR_RE = re.compile(r"^\d{6}[A-Z]?$")
RUN_CARD_ID_RE = re.compile(r"^- Canonical run ID:\s+`([^`]+)`\s*$", re.MULTILINE)


@dataclass(frozen=True)
class RegistryRow:
    grb: str
    run_id: str
    set_id: str
    model_name: str
    jet: str
    csm: str
    spectrum: str
    campaign: str
    status: str
    nmap: str
    free_model_params: str
    fixed_model_params: str
    free_nuisance_params: str
    fixed_nuisance_params: str
    old_path: str
    new_path: str


def _fits_root(path: Path) -> Path:
    path = path.expanduser().resolve()
    return path if path.name == "Fits" else path / "Fits"


def _read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text())


def _run_id(run_dir: Path, grb: str, set_id: str) -> str:
    card = run_dir / "RUN_CARD.md"
    if card.exists():
        match = RUN_CARD_ID_RE.search(card.read_text())
        if match:
            return match.group(1)
    return f"{grb}_{set_id}"


def _layout_from_path(fits_root: Path, run_dir: Path, model_name: str, params: set[str], run_id: str) -> tuple[str, str, str, str, str]:
    rel = run_dir.relative_to(fits_root).parts
    grb = run_dir.name
    spectrum_idx = next((i for i, part in enumerate(rel) if part.startswith("spectrum_")), None)
    jet = rel[0] if rel and rel[0].startswith("jet_") else _classify_jet(model_name, params)
    if spectrum_idx is None:
        csm = _classify_csm(model_name, params, run_id)
        spectrum = _classify_spectrum(model_name, run_id)
        campaign_parts = rel[1:-1]
    else:
        csm = "/".join(rel[1:spectrum_idx]) or _classify_csm(model_name, params, run_id)
        spectrum = rel[spectrum_idx]
        campaign_parts = rel[spectrum_idx + 1 : -1]
    campaign = "/".join(campaign_parts) if campaign_parts else run_id.removeprefix(f"{grb}_")
    set_id = campaign_parts[-1] if campaign_parts else campaign
    return grb, set_id, jet, csm, spectrum, campaign


def _nuisance_params(toml: dict[str, Any], *, free: bool) -> str:
    names: list[str] = []
    for section in ["extinction", "host", "offsets", "slop"]:
        names.extend(f"{section}.{name}" for name in _param_names(toml, section, free=free))
    return ", ".join(names)


def _previous_path(run_dir: Path) -> str:
    card = run_dir / "RUN_CARD.md"
    if not card.exists():
        return ""
    for line in card.read_text().splitlines():
        if line.startswith("- Previous share path:"):
            return line.split(":", 1)[1].strip().strip("`")
    return ""


def _write_missing_run_card(row: RegistryRow, run_dir: Path) -> bool:
    card = run_dir / "RUN_CARD.md"
    if card.exists():
        return False
    text = f"""# Run Card: `{row.run_id}`

- Display name: `{row.grb} {row.campaign}`
- Canonical run ID: `{row.run_id}`
- GRB: `{row.grb}`
- Model wrapper: `{row.model_name}`
- Jet family: `{row.jet}`
- Circumstellar medium: `{row.csm}`
- Spectrum: `{row.spectrum}`
- Campaign: `{row.campaign}`
- Status: `{row.status}`
- nmap: `{row.nmap}`
- Previous share path: ``

## Frozen / Thawed State

- Thawed model parameters: `{row.free_model_params}`
- Frozen model parameters: `{row.fixed_model_params}`
- Thawed nuisance parameters: `{row.free_nuisance_params}`
- Frozen nuisance parameters: `{row.fixed_nuisance_params}`

## Notes

This card was generated from `model.toml` while rebuilding the organized
`Fits` registry. The visible folder path is the human-facing organization; the
canonical run ID above preserves the machine-readable run provenance.
"""
    card.write_text(text)
    return True


def _row_for_model(fits_root: Path, toml_path: Path) -> RegistryRow | None:
    run_dir = toml_path.parent
    if not GRB_DIR_RE.match(run_dir.name):
        return None
    toml = _read_toml(toml_path)
    model_name = str(toml.get("name", "unknown"))
    params = _model_param_names(toml)
    provisional_set_id = run_dir.parent.name
    run_id = _run_id(run_dir, run_dir.name, provisional_set_id)
    grb, set_id, jet, csm, spectrum, campaign = _layout_from_path(
        fits_root, run_dir, model_name, params, run_id
    )
    nmap, status = _nmap_and_status(run_dir)
    return RegistryRow(
        grb=grb,
        run_id=run_id,
        set_id=set_id,
        model_name=model_name,
        jet=jet,
        csm=csm,
        spectrum=spectrum,
        campaign=campaign,
        status=status,
        nmap=nmap,
        free_model_params=", ".join(_param_names(toml, "model", free=True)),
        fixed_model_params=", ".join(_param_names(toml, "model", free=False)),
        free_nuisance_params=_nuisance_params(toml, free=True),
        fixed_nuisance_params=_nuisance_params(toml, free=False),
        old_path=_previous_path(run_dir),
        new_path=str(run_dir),
    )


def rebuild(fits_root: Path, *, write_cards: bool) -> tuple[list[RegistryRow], int]:
    rows = []
    cards_written = 0
    for toml_path in sorted(fits_root.rglob("model.toml")):
        row = _row_for_model(fits_root, toml_path)
        if row is None:
            continue
        rows.append(row)
        if write_cards and _write_missing_run_card(row, toml_path.parent):
            cards_written += 1
    rows.sort(key=lambda r: (r.jet, r.csm, r.spectrum, r.campaign, r.grb, r.run_id))
    return rows, cards_written


def write_registry(path: Path, rows: list[RegistryRow]) -> None:
    fieldnames = list(RegistryRow.__dataclass_fields__)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: getattr(row, name) for name in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="Share root or Fits directory")
    parser.add_argument("--no-run-cards", action="store_true", help="Do not create missing RUN_CARD.md files")
    args = parser.parse_args()
    fits_root = _fits_root(args.root)
    rows, cards_written = rebuild(fits_root, write_cards=not args.no_run_cards)
    write_registry(fits_root / "run_registry.csv", rows)
    print(f"Rebuilt {fits_root / 'run_registry.csv'}")
    print(f"Rows: {len(rows)}")
    print(f"Missing run cards written: {cards_written}")


if __name__ == "__main__":
    main()
