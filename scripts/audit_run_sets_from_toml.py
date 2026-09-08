#!/usr/bin/env python3
"""Audit run sets from model.toml and result artifacts.

Creates:
1. One markdown summary per run-set (set suffix after GRB id).
2. One index markdown with health/status overview.
3. CSV exports for machine parsing.
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
class RunRecord:
    grb: str
    run_dir: str
    set_id: str
    path: Path
    model_name: str
    status: str
    nmap: str
    nmap_source: str
    mcmc_done: bool
    minimized_done: bool
    minimize_success: bool
    param_map: dict[str, str]


def _fmt_num(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val:.6g}"
    return str(val)


def _prior_str(prior: dict[str, Any]) -> str:
    ptype = prior.get("type", "?")
    lower = prior.get("lower")
    upper = prior.get("upper")
    mu = prior.get("mu")
    sigma = prior.get("sigma")
    ig = prior.get("initial_guess")
    isg = prior.get("initial_sigma")
    parts = [f"free:{ptype}"]
    if lower is not None or upper is not None:
        parts.append(f"[{_fmt_num(lower) if lower is not None else ''},{_fmt_num(upper) if upper is not None else ''}]")
    if mu is not None:
        parts.append(f"mu={_fmt_num(mu)}")
    if sigma is not None:
        parts.append(f"sigma={_fmt_num(sigma)}")
    if ig is not None:
        parts.append(f"ig={_fmt_num(ig)}")
    if isg is not None:
        parts.append(f"is={_fmt_num(isg)}")
    return " ".join(parts)


def _extract_param_map(model_toml: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    section_order = ["model", "extinction", "host", "offsets", "slop"]
    for sec in section_order:
        entries = model_toml.get(sec, [])
        if not isinstance(entries, list):
            continue
        for item in entries:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            key = f"{sec}.{name}"
            if "value" in item:
                out[key] = f"fixed:{_fmt_num(item['value'])}"
            elif isinstance(item.get("prior"), dict):
                out[key] = _prior_str(item["prior"])
            else:
                out[key] = "unknown"
    return out


def _get_nmap(run_path: Path) -> tuple[str, str, bool, bool]:
    minimized_path = run_path / "minimized" / "minimized.json"
    best_fit_path = run_path / "best_fit.json"
    chain_path = run_path / "chain.npz"

    mcmc_done = chain_path.exists()
    minimized_done = minimized_path.exists()

    if minimized_path.exists():
        try:
            payload = json.loads(minimized_path.read_text())
            nmap = payload.get("nmap")
            success = bool(payload.get("success", False))
            return (_fmt_num(nmap) if nmap is not None else "", "minimized.json", success, mcmc_done)
        except Exception:
            return ("", "minimized.json(parse_error)", False, mcmc_done)

    if best_fit_path.exists():
        try:
            payload = json.loads(best_fit_path.read_text())
            nmap = payload.get("nmap")
            return (_fmt_num(nmap) if nmap is not None else "", "best_fit.json", False, mcmc_done)
        except Exception:
            return ("", "best_fit.json(parse_error)", False, mcmc_done)

    return ("", "missing", False, mcmc_done)


def _run_status(mcmc_done: bool, minimized_done: bool, minimize_success: bool, nmap: str) -> str:
    if minimized_done and minimize_success and nmap != "":
        return "done_minimized"
    if minimized_done and not minimize_success:
        return "minimized_failed"
    if mcmc_done and not minimized_done:
        return "mcmc_only"
    if not mcmc_done and not minimized_done:
        return "incomplete"
    return "unknown"


def _collect_runs(results_dir: Path) -> list[RunRecord]:
    rows: list[RunRecord] = []
    for p in sorted(results_dir.iterdir()):
        if not p.is_dir():
            continue
        m = GRB_RE.match(p.name)
        if not m:
            continue
        grb, set_id = m.group(1), m.group(2)
        model_toml_path = p / "model.toml"
        if not model_toml_path.exists():
            rows.append(
                RunRecord(
                    grb=grb,
                    run_dir=p.name,
                    set_id=set_id,
                    path=p,
                    model_name="missing_model.toml",
                    status="missing_model_toml",
                    nmap="",
                    nmap_source="missing",
                    mcmc_done=False,
                    minimized_done=False,
                    minimize_success=False,
                    param_map={},
                )
            )
            continue

        try:
            model_toml = tomllib.loads(model_toml_path.read_text())
        except Exception:
            rows.append(
                RunRecord(
                    grb=grb,
                    run_dir=p.name,
                    set_id=set_id,
                    path=p,
                    model_name="model.toml(parse_error)",
                    status="model_toml_parse_error",
                    nmap="",
                    nmap_source="missing",
                    mcmc_done=False,
                    minimized_done=False,
                    minimize_success=False,
                    param_map={},
                )
            )
            continue

        nmap, src, minimize_success, mcmc_done = _get_nmap(p)
        minimized_done = (p / "minimized" / "minimized.json").exists()
        status = _run_status(mcmc_done, minimized_done, minimize_success, nmap)
        rows.append(
            RunRecord(
                grb=grb,
                run_dir=p.name,
                set_id=set_id,
                path=p,
                model_name=str(model_toml.get("name", "unknown")),
                status=status,
                nmap=nmap,
                nmap_source=src,
                mcmc_done=mcmc_done,
                minimized_done=minimized_done,
                minimize_success=minimize_success,
                param_map=_extract_param_map(model_toml),
            )
        )
    return rows


def _inconsistency_summary(records: list[RunRecord], param_cols: list[str]) -> list[str]:
    notes: list[str] = []
    for col in param_cols:
        vals = sorted({r.param_map.get(col, "") for r in records if r.param_map.get(col, "") != ""})
        if len(vals) > 1:
            notes.append(f"{col}: {len(vals)} variants")
    return notes


def _write_set_markdown(out_path: Path, set_id: str, records: list[RunRecord]) -> None:
    records = sorted(records, key=lambda r: r.grb)
    all_cols = sorted({k for r in records for k in r.param_map.keys()})
    inconsistencies = _inconsistency_summary(records, all_cols)

    header_cols = [
        "GRB",
        "run_dir",
        "model_name",
        "status",
        "nmap",
        "nmap_source",
        "mcmc_done",
        "minimized_done",
        "minimize_success",
    ] + all_cols

    lines: list[str] = []
    lines.append(f"# Run Set Audit: `{set_id}`")
    lines.append("")
    lines.append(f"- Generated: `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append(f"- GRB count: `{len(records)}`")
    lines.append("")
    if inconsistencies:
        lines.append("## Consistency Checks")
        lines.append("")
        lines.append("The following parameters differ across GRBs in this set:")
        lines.append("")
        for note in inconsistencies:
            lines.append(f"- `{note}`")
        lines.append("")
    else:
        lines.append("## Consistency Checks")
        lines.append("")
        lines.append("No cross-GRB parameter-spec differences detected in parsed `.toml` fields.")
        lines.append("")

    lines.append("## GRB Table")
    lines.append("")
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")
    for r in records:
        row = [
            r.grb,
            r.run_dir,
            r.model_name,
            r.status,
            r.nmap,
            r.nmap_source,
            "yes" if r.mcmc_done else "no",
            "yes" if r.minimized_done else "no",
            "yes" if r.minimize_success else "no",
        ]
        for c in all_cols:
            row.append(r.param_map.get(c, ""))
        lines.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    out_path.write_text("\n".join(lines) + "\n")


def _write_csv(out_path: Path, records: list[RunRecord]) -> None:
    records = sorted(records, key=lambda r: (r.set_id, r.grb))
    all_cols = sorted({k for r in records for k in r.param_map.keys()})
    fields = [
        "set_id",
        "grb",
        "run_dir",
        "model_name",
        "status",
        "nmap",
        "nmap_source",
        "mcmc_done",
        "minimized_done",
        "minimize_success",
        "path",
    ] + all_cols
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            rec = {
                "set_id": r.set_id,
                "grb": r.grb,
                "run_dir": r.run_dir,
                "model_name": r.model_name,
                "status": r.status,
                "nmap": r.nmap,
                "nmap_source": r.nmap_source,
                "mcmc_done": r.mcmc_done,
                "minimized_done": r.minimized_done,
                "minimize_success": r.minimize_success,
                "path": str(r.path),
            }
            for c in all_cols:
                rec[c] = r.param_map.get(c, "")
            w.writerow(rec)


def _write_index(out_path: Path, set_to_records: dict[str, list[RunRecord]]) -> None:
    lines: list[str] = []
    lines.append("# Run Set Audit Index")
    lines.append("")
    lines.append(f"- Generated: `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append(f"- Set count: `{len(set_to_records)}`")
    lines.append("")
    lines.append("| set_id | grb_count | done_minimized | mcmc_only | incomplete_or_error | file |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    for set_id in sorted(set_to_records):
        recs = set_to_records[set_id]
        done = sum(1 for r in recs if r.status == "done_minimized")
        mcmc_only = sum(1 for r in recs if r.status == "mcmc_only")
        bad = sum(1 for r in recs if r.status not in {"done_minimized", "mcmc_only"})
        md_name = f"set__{set_id}.md"
        lines.append(f"| `{set_id}` | {len(recs)} | {done} | {mcmc_only} | {bad} | `{md_name}` |")
    out_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("/Users/jkeohane/GRBs/VegasJetFit/jetfit/results"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("/Users/jkeohane/GRBs/VegasJetFit/reports/run_set_audit_20260520"),
    )
    parser.add_argument(
        "--share-out-dir",
        type=Path,
        default=Path("/Users/jkeohane/Library/CloudStorage/GoogleDrive-jwkeohane@gmail.com/.shortcut-targets-by-id/1d7HnZ0yxuhMv2vPzbGBL9NNSDX9BjeDp/VegasGRBruns/reports/run_set_audit_20260520"),
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.share_out_dir.mkdir(parents=True, exist_ok=True)

    records = _collect_runs(args.results_dir)
    set_to_records: dict[str, list[RunRecord]] = defaultdict(list)
    for r in records:
        set_to_records[r.set_id].append(r)

    # Per-set markdown
    for set_id, recs in set_to_records.items():
        md_path = args.out_dir / f"set__{set_id}.md"
        _write_set_markdown(md_path, set_id, recs)

    # Index + CSV
    _write_index(args.out_dir / "INDEX.md", set_to_records)
    _write_csv(args.out_dir / "run_set_audit_all_rows.csv", records)

    # Mirror to share
    for p in args.out_dir.iterdir():
        if p.is_file():
            shutil.copy2(p, args.share_out_dir / p.name)

    print(f"Wrote local audit to: {args.out_dir}")
    print(f"Mirrored audit to: {args.share_out_dir}")
    print(f"Run rows: {len(records)}")
    print(f"Set count: {len(set_to_records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
