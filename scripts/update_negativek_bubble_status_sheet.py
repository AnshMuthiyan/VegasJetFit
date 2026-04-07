#!/usr/bin/env python3
"""Build a Drive-friendly status summary for negative-k bubble runs."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BEST_PARAM_KEYS = [
    "E52",
    "lf0",
    "nt",
    "nism",
    "rt",
    "eps_e",
    "eps_b",
    "p",
    "theta_c",
    "theta_v",
    "z",
    "dl28",
    "hmf",
]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create CSV/XLSX status sheet for monitored negative-k bubble runs."
    )
    parser.add_argument(
        "--vegas-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit",
        help="VegasJetFit repository directory.",
    )
    parser.add_argument(
        "--drive-root",
        default="/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns",
        help="Shared Drive root used for synced results.",
    )
    parser.add_argument(
        "--owner-subdir",
        default="jkeohane",
        help="Owner subdirectory under each GRB in Drive.",
    )
    parser.add_argument(
        "--events",
        nargs="+",
        default=["080413B", "140506A", "210905A"],
        help="GRB event list.",
    )
    parser.add_argument(
        "--run-tags",
        nargs="+",
        default=["theta1p0_4h_target", "theta1p0_moderate24h"],
        help="Run-tag suffixes to include.",
    )
    parser.add_argument(
        "--output-csv",
        default="/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns/NegativeK_Bubble_Run_Status.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--output-xlsx",
        default="/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns/NegativeK_Bubble_Run_Status.xlsx",
        help="Output XLSX path.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def parse_ps() -> list[tuple[int, float, str]]:
    try:
        out = subprocess.check_output(
            ["ps", "-Ao", "pid=,pcpu=,command="], text=True
        )
    except Exception:
        return []
    rows: list[tuple[int, float, str]] = []
    for line in out.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split(maxsplit=2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            cpu = float(parts[1])
        except ValueError:
            continue
        rows.append((pid, cpu, parts[2]))
    return rows


def get_obs_file(resources_event_dir: Path, event: str) -> str:
    primary = resources_event_dir / f"{event}.csv"
    if primary.exists():
        return str(primary)
    alt = resources_event_dir / f"{event}clean.csv"
    if alt.exists():
        return str(alt)
    csvs = sorted(resources_event_dir.glob("*.csv"))
    return str(csvs[0]) if csvs else ""


def to_float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def status_label(
    run_exists: bool,
    has_best: bool,
    has_chain: bool,
    has_min: bool,
    has_synced_min: bool,
    jetfit_pids: int,
) -> str:
    if has_synced_min:
        return "synced"
    if has_min:
        return "minimized_pending_sync"
    if has_best and has_chain:
        return "complete_pending_minimize"
    if jetfit_pids > 0:
        return "running"
    if run_exists and not has_best:
        return "partial_or_stalled"
    if run_exists:
        return "incomplete"
    return "not_started"


def write_xlsx(df: pd.DataFrame, out_xlsx: Path) -> None:
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="status")
        ws = writer.sheets["status"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                text = "" if cell.value is None else str(cell.value)
                max_len = max(max_len, len(text))
            ws.column_dimensions[col_letter].width = min(max(10, max_len + 2), 42)


def main() -> int:
    args = parse_args()

    vegas_dir = Path(args.vegas_dir)
    results_root = vegas_dir / "jetfit" / "results"
    resources_root = vegas_dir / "jetfit" / "resources" / "grbs"
    logs_root = vegas_dir / "logs"
    drive_root = Path(args.drive_root)

    ps_rows = parse_ps()
    timestamp = now_utc_iso()
    rows: list[dict[str, Any]] = []

    for run_tag in args.run_tags:
        for event in args.events:
            run_name = f"{event}_bubble_tophat_{run_tag}"
            run_dir = results_root / run_name
            best_fit_path = run_dir / "best_fit.json"
            chain_path = run_dir / "chain.npz"
            checkpoint_path = run_dir / "pt_resume_state.npz"
            minimized_path = run_dir / "minimized" / "minimized.json"

            drive_run_dir = drive_root / event / args.owner_subdir / run_name
            drive_sync_manifest = drive_run_dir / "sync_manifest.txt"
            drive_minimized = drive_run_dir / "minimized" / "minimized.json"

            best_fit = load_json(best_fit_path)
            best_model = (
                best_fit.get("model", {}) if isinstance(best_fit.get("model"), dict) else {}
            )
            minimized = load_json(minimized_path)
            min_params = (
                minimized.get("params", {})
                if isinstance(minimized.get("params"), dict)
                else {}
            )

            jetfit_matches = [
                (pid, cpu, cmd)
                for pid, cpu, cmd in ps_rows
                if "jetfit.run" in cmd and f"--event {event}" in cmd and run_name in cmd
            ]
            min_matches = [
                (pid, cpu, cmd)
                for pid, cpu, cmd in ps_rows
                if "minimize.py" in cmd and str(run_dir) in cmd
            ]

            has_synced_min = drive_minimized.exists() and drive_sync_manifest.exists()
            status = status_label(
                run_exists=run_dir.exists(),
                has_best=best_fit_path.exists(),
                has_chain=chain_path.exists(),
                has_min=minimized_path.exists(),
                has_synced_min=has_synced_min,
                jetfit_pids=len(jetfit_matches),
            )

            row: dict[str, Any] = {
                "timestamp_utc": timestamp,
                "event": event,
                "run_tag": run_tag,
                "status": status,
                "run_dir": str(run_dir),
                "drive_dir": str(drive_run_dir),
                "run_exists": run_dir.exists(),
                "has_chain": chain_path.exists(),
                "has_best_fit": best_fit_path.exists(),
                "has_checkpoint": checkpoint_path.exists(),
                "has_minimized": minimized_path.exists(),
                "has_synced_manifest": drive_sync_manifest.exists(),
                "has_synced_minimized": drive_minimized.exists(),
                "jetfit_pid_count": len(jetfit_matches),
                "jetfit_cpu_sum": round(sum(cpu for _, cpu, _ in jetfit_matches), 2),
                "minimize_pid_count": len(min_matches),
                "minimize_cpu_sum": round(sum(cpu for _, cpu, _ in min_matches), 2),
                "nmap_best_fit": to_float_or_none(best_fit.get("nmap")),
                "nmap_minimized": to_float_or_none(minimized.get("nmap")),
                "minimize_success": minimized.get("success"),
                "minimize_message": minimized.get("message"),
                "obs_file": get_obs_file(resources_root / event, event),
                "log_file": str(logs_root / f"{event}.bubble.log"),
            }

            for key in BEST_PARAM_KEYS:
                row[f"best_{key}"] = to_float_or_none(best_model.get(key))
                row[f"min_{key}"] = to_float_or_none(min_params.get(key))

            rows.append(row)

    df = pd.DataFrame(rows).sort_values(["run_tag", "event"]).reset_index(drop=True)

    out_csv = Path(args.output_csv)
    out_xlsx = Path(args.output_xlsx)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    write_xlsx(df, out_xlsx)

    print(f"Wrote status CSV: {out_csv}")
    print(f"Wrote status XLSX: {out_xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
