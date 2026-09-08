#!/usr/bin/env python3
"""Organize Google Drive GRB fit runs into a physics-first folder tree.

Run from a project Python environment, for example:

    /Users/jkeohane/GRBs/.venv/bin/python scripts/organize_share_runs.py <share_root>

This moves TOML-backed run directories from the legacy
`<GRB>/jkeohane/<run_id>` layout into:

    Fits/<jet>/<csm>/<spectrum>/<campaign>/<GRB>

The canonical run ID is preserved in `RUN_CARD.md` and `run_registry.csv`.
The script also writes campaign-level README/index files.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(f"tomllib unavailable: {exc}")


GRB_RE = re.compile(r"^(\d{6}[A-Z]?)_(.+)$")


@dataclass
class RunInfo:
    grb: str
    run_id: str
    set_id: str
    old_path: Path
    new_path: Path
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


def _fmt(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val:.6g}"
    return str(val)


def _slug(text: str) -> str:
    text = text.strip().replace(" ", "_")
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "unknown"


def _entries(toml: dict[str, Any], section: str) -> list[dict[str, Any]]:
    value = toml.get(section, [])
    return value if isinstance(value, list) else []


def _param_names(toml: dict[str, Any], section: str, *, free: bool) -> list[str]:
    names: list[str] = []
    for item in _entries(toml, section):
        if not isinstance(item, dict) or "name" not in item:
            continue
        is_free = isinstance(item.get("prior"), dict)
        is_fixed = "value" in item
        if free and is_free:
            names.append(str(item["name"]))
        if not free and is_fixed:
            names.append(f"{item['name']}={_fmt(item['value'])}")
    return names


def _model_param_names(toml: dict[str, Any]) -> set[str]:
    return {str(item.get("name")) for item in _entries(toml, "model") if isinstance(item, dict)}


def _classify_jet(model_name: str, params: set[str]) -> str:
    name = model_name.lower()
    if "powerlawjet" in name or {"k_e", "k_g", "s"}.issubset(params):
        return "jet_structured_powerlaw"
    return "jet_tophat"


def _classify_csm(model_name: str, params: set[str], run_id: str) -> str:
    name = model_name.lower()
    rid = run_id.lower()
    if "empiricalbubble" in name or "empirical_bubble" in rid:
        return "csm_wind_bubble/empirical_bubble"
    if "bubble" in name or "simple_bubble" in rid or "bubble_" in rid:
        return "csm_wind_bubble/simple_bubble"
    if {"k1", "k2", "sn"}.issubset(params) or "smoothbroken" in name or "sbpl" in rid:
        return "csm_broken_powerlaw"
    return "csm_powerlaw"


def _classify_spectrum(model_name: str, run_id: str) -> str:
    low = f"{model_name} {run_id}".lower()
    if "dylanspectrum" in low or "dylanspec" in low:
        return "spectrum_dylan_smoothed"
    if "spectrum_standard" in low or "standard_spectrum" in low:
        return "spectrum_standard"
    # New campaigns should default to Dylan's smoothed spectrum.  Only route
    # runs to spectrum_standard when they explicitly say they are standard.
    return "spectrum_dylan_smoothed"


def _nmap_and_status(path: Path) -> tuple[str, str]:
    min_path = path / "minimized" / "minimized.json"
    best_path = path / "best_fit.json"
    chain_path = path / "chain.npz"
    if min_path.exists():
        try:
            payload = json.loads(min_path.read_text())
            nmap = payload.get("nmap")
            success = bool(payload.get("success", False))
            status = "done_minimized" if success and nmap is not None else "minimized_check_needed"
            return (_fmt(nmap) if nmap is not None else "", status)
        except Exception:
            return ("", "minimized_parse_error")
    if best_path.exists():
        try:
            payload = json.loads(best_path.read_text())
            nmap = payload.get("nmap")
            return (_fmt(nmap) if nmap is not None else "", "mcmc_done_not_minimized")
        except Exception:
            return ("", "best_fit_parse_error")
    if chain_path.exists():
        return ("", "mcmc_done_not_minimized")
    return ("", "incomplete")


def _read_run(path: Path, root: Path, fits_root: Path) -> RunInfo | None:
    m = GRB_RE.match(path.name)
    if not m:
        return None
    grb, set_id = m.group(1), m.group(2)
    toml_path = path / "model.toml"
    if not toml_path.exists():
        return None
    toml = tomllib.loads(toml_path.read_text())
    model_name = str(toml.get("name", "unknown"))
    params = _model_param_names(toml)
    jet = _classify_jet(model_name, params)
    csm = _classify_csm(model_name, params, path.name)
    spectrum = _classify_spectrum(model_name, path.name)
    campaign = _slug(set_id)
    nmap, status = _nmap_and_status(path)
    new_path = fits_root / jet / csm / spectrum / campaign / grb
    nuisance_sections = ["extinction", "host", "offsets", "slop"]
    free_nuisance = []
    fixed_nuisance = []
    for sec in nuisance_sections:
        free_nuisance.extend(f"{sec}.{n}" for n in _param_names(toml, sec, free=True))
        fixed_nuisance.extend(f"{sec}.{n}" for n in _param_names(toml, sec, free=False))
    return RunInfo(
        grb=grb,
        run_id=path.name,
        set_id=set_id,
        old_path=path,
        new_path=new_path,
        model_name=model_name,
        jet=jet,
        csm=csm,
        spectrum=spectrum,
        campaign=campaign,
        status=status,
        nmap=nmap,
        free_model_params=", ".join(_param_names(toml, "model", free=True)),
        fixed_model_params=", ".join(_param_names(toml, "model", free=False)),
        free_nuisance_params=", ".join(free_nuisance),
        fixed_nuisance_params=", ".join(fixed_nuisance),
    )


def _discover(root: Path, fits_root: Path) -> list[RunInfo]:
    runs: list[RunInfo] = []
    for toml_path in root.glob("*/jkeohane/*/model.toml"):
        path = toml_path.parent
        info = _read_run(path, root, fits_root)
        if info is not None:
            runs.append(info)
    return sorted(runs, key=lambda r: (r.jet, r.csm, r.spectrum, r.campaign, r.grb, r.run_id))


def _write_run_card(info: RunInfo) -> None:
    text = f"""# Run Card: `{info.run_id}`

- Display name: `{info.grb} {info.campaign}`
- Canonical run ID: `{info.run_id}`
- GRB: `{info.grb}`
- Model wrapper: `{info.model_name}`
- Jet family: `{info.jet}`
- Circumstellar medium: `{info.csm}`
- Spectrum: `{info.spectrum}`
- Campaign: `{info.campaign}`
- Status: `{info.status}`
- nmap: `{info.nmap}`
- Previous share path: `{info.old_path}`

## Frozen / Thawed State

- Thawed model parameters: `{info.free_model_params}`
- Frozen model parameters: `{info.fixed_model_params}`
- Thawed nuisance parameters: `{info.free_nuisance_params}`
- Frozen nuisance parameters: `{info.fixed_nuisance_params}`

## Notes

This card was generated from `model.toml` during the share-directory
reorganization. The canonical run ID above preserves provenance while the
human-facing folder path stays compact.
"""
    (info.new_path / "RUN_CARD.md").write_text(text)


def _write_csv(path: Path, rows: list[RunInfo]) -> None:
    fieldnames = [
        "grb",
        "run_id",
        "set_id",
        "model_name",
        "jet",
        "csm",
        "spectrum",
        "campaign",
        "status",
        "nmap",
        "free_model_params",
        "fixed_model_params",
        "free_nuisance_params",
        "fixed_nuisance_params",
        "old_path",
        "new_path",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: str(getattr(r, k)) for k in fieldnames})


def _write_readmes(fits_root: Path, rows: list[RunInfo]) -> None:
    generated = datetime.now().isoformat(timespec="seconds")
    (fits_root / "README.md").write_text(
        f"""# Organized GRB Fit Results

Generated: `{generated}`

This directory is organized by physics first:

```text
Fits/<jet_family>/<csm_family>/<spectrum>/<campaign>/<GRB>
```

Each GRB run folder contains a generated `RUN_CARD.md` with the canonical run
ID, model wrapper, frozen/thawed parameters, status, and `nmap` when available.

Rows organized: `{len(rows)}`

The full machine-readable registry is `run_registry.csv`.
"""
    )
    by_campaign: dict[Path, list[RunInfo]] = defaultdict(list)
    for row in rows:
        campaign_dir = fits_root / row.jet / row.csm / row.spectrum / row.campaign
        by_campaign[campaign_dir].append(row)
    for campaign_dir, campaign_rows in by_campaign.items():
        campaign_rows = sorted(campaign_rows, key=lambda r: (r.grb, r.run_id))
        lines = [
            f"# Campaign: `{campaign_rows[0].campaign}`",
            "",
            f"- Jet family: `{campaign_rows[0].jet}`",
            f"- Circumstellar medium: `{campaign_rows[0].csm}`",
            f"- Spectrum: `{campaign_rows[0].spectrum}`",
            f"- Run count: `{len(campaign_rows)}`",
            "",
            "| GRB | status | nmap | run_id |",
            "|---|---|---:|---|",
        ]
        for row in campaign_rows:
            rel = row.new_path.relative_to(campaign_dir)
            lines.append(f"| `{row.grb}` | `{row.status}` | `{row.nmap}` | [{row.run_id}]({rel.as_posix()}/RUN_CARD.md) |")
        lines.append("")
        campaign_dir.mkdir(parents=True, exist_ok=True)
        (campaign_dir / "README.md").write_text("\n".join(lines))


def organize(root: Path, dry_run: bool) -> list[RunInfo]:
    fits_root = root / "Fits"
    rows = _discover(root, fits_root)
    for row in rows:
        if dry_run:
            continue
        if row.new_path.exists():
            raise FileExistsError(f"Destination already exists: {row.new_path}")
        row.new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(row.old_path), str(row.new_path))
        _write_run_card(row)
    if not dry_run:
        _write_csv(fits_root / "run_registry.csv", rows)
        _write_readmes(fits_root, rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("share_root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = organize(args.share_root.expanduser().resolve(), args.dry_run)
    print(f"{'Would organize' if args.dry_run else 'Organized'} {len(rows)} TOML-backed runs")
    if rows:
        print(f"First: {rows[0].old_path} -> {rows[0].new_path}")
        print(f"Last:  {rows[-1].old_path} -> {rows[-1].new_path}")


if __name__ == "__main__":
    main()
