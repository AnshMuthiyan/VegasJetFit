#!/usr/bin/env python3
"""Dynamic dispatcher for the core-logangle single-power-law 10-temp campaign.

Policy:
- Fill all available machines for the first batch, including Lyra if allowed.
- After Lyra has had one MCMC assignment, reserve it for minimization/postfit.
- Do not bind second-round events to a host until a host is actually free.
- Dispatch queued events in the requested order; 080319B and 080413B are last.
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/jkeohane/GRBs")
VJF = ROOT / "VegasJetFit"
REPORT = VJF / "reports/core_logangle_powerlaw_15grb_10temp_2000_campaign"
DEFAULT_QUEUE = REPORT / "dynamic_event_queue.csv"
DEFAULT_MANIFEST = REPORT / "dispatch_manifest.csv"
RUN_TAG = "core_logangle_powerlawcsm_unseeded_10temp_2000x2000_v1"

MACHINES = [
    ("pcrc-mac-studio-1", 14),
    ("pcrc-mac-studio-2", 14),
    ("pauley404-01", 8),
    ("pauley404-02", 8),
    ("pauley404-03", 8),
    ("lyra", 8),
]

QUEUE_EVENTS = [
    "050525A",
    "050922C",
    "090424",
    "090618",
    "111228A",
    "130612A",
    "131030A",
    "140506A",
    "160131A",
    "171010A",
    "210905A",
    "220101A",
    "221009A",
    "080319B",
    "080413B",
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check, timeout=timeout)


def shell(cmd: str, *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, check=check, timeout=timeout)


def norm_host(host: str) -> str:
    host = host.strip().lower()
    return host[:-6] if host.endswith(".local") else host


@dataclass
class ManifestRow:
    event: str
    host: str
    csm_family: str
    queue_order: str
    workers: str
    run_tag: str
    launched_utc: str


def ensure_queue(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "csm_family", "queue_order", "note"])
        for i, ev in enumerate(QUEUE_EVENTS, start=1):
            note = "deferred_last" if ev in {"080319B", "080413B"} else "normal"
            w.writerow([ev, "power_law", i, note])


def read_queue(path: Path) -> list[str]:
    ensure_queue(path)
    with path.open() as f:
        return [r["event"] for r in csv.DictReader(f) if r.get("event")]


def read_manifest(path: Path) -> list[ManifestRow]:
    if not path.exists():
        return []
    with path.open() as f:
        rows = []
        for r in csv.DictReader(f):
            if not r.get("event"):
                continue
            rows.append(ManifestRow(
                event=r["event"], host=r.get("host", ""), csm_family=r.get("csm_family", "power_law"),
                queue_order=r.get("queue_order", ""), workers=r.get("workers", ""),
                run_tag=r.get("run_tag", RUN_TAG), launched_utc=r.get("launched_utc", ""),
            ))
        return rows


def write_manifest(path: Path, rows: list[ManifestRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "host", "csm_family", "queue_order", "workers", "run_tag", "launched_utc"])
        for r in rows:
            w.writerow([r.event, r.host, r.csm_family, r.queue_order, r.workers, r.run_tag, r.launched_utc])


def local_result_dir(event: str) -> Path:
    return VJF / f"jetfit/results/{event}_{RUN_TAG}"


def result_complete_local(event: str) -> bool:
    d = local_result_dir(event)
    return (d / "chain.npz").is_file() and (d / "best_fit.json").is_file()


def result_published(event: str) -> bool:
    d = ROOT / "Share_Folder/Fits/production_runs/unseeded_runs/26_06_27__core_ejet_gamma_logangles__single_powerlaw_csm__unseeded__10_temperature_2000x2000" / event
    return (d / "core_postfit_products.validated").is_file()


def host_has_running_job(host: str) -> bool:
    pattern = RUN_TAG
    if host == "lyra":
        cp = shell(f"ps -axo command | grep '[j]etfit.run' | grep -F '{pattern}'", check=False)
        return cp.returncode == 0
    cmd = f"ps -axo command | grep '[j]etfit.run' | grep -F '{pattern}'"
    cp = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, cmd], check=False, timeout=12)
    return cp.returncode == 0


def event_running_on_host(event: str, host: str) -> bool:
    pattern = f"{event}_{RUN_TAG}"
    host = norm_host(host)
    if host == "lyra":
        cp = shell(f"ps -axo command | grep '[j]etfit.run' | grep -F '{pattern}'", check=False)
        return cp.returncode == 0
    cp = run([
        "ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host,
        f"ps -axo command | grep '[j]etfit.run' | grep -F '{pattern}'",
    ], check=False, timeout=12)
    return cp.returncode == 0


def event_complete_on_host(event: str, host: str) -> bool:
    host = norm_host(host)
    remote = VJF / f"jetfit/results/{event}_{RUN_TAG}"
    if host == "lyra":
        return result_complete_local(event)
    cp = run([
        "ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host,
        f"test -s '{remote}/chain.npz' -a -s '{remote}/best_fit.json'",
    ], check=False, timeout=12)
    return cp.returncode == 0


def host_reachable(host: str) -> bool:
    if host == "lyra":
        return True
    cp = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, "true"], check=False, timeout=12)
    return cp.returncode == 0


def sync_to_hosts(manifest: Path, hosts: list[str]) -> None:
    for host in hosts:
        if host == "lyra":
            continue
        run(["rsync", "-a", str(manifest), f"{host}:{manifest}"], check=False, timeout=30)
        for script in [
            VJF / "scripts/run_core_logangle_powerlaw_15grb_event.sh",
            VJF / "scripts/run_core_logangle_powerlaw_15grb_queue.sh",
        ]:
            run(["rsync", "-a", str(script), f"{host}:{script}"], check=False, timeout=30)


def launch(event: str, host: str, workers: int, dry_run: bool = False) -> None:
    session = f"core_logangle_powerlaw_10temp_dyn_{event}"
    inner = f"cd {VJF} && env EVENT={event} WORKERS={workers} DISPATCH_MANIFEST={DEFAULT_MANIFEST} bash scripts/run_core_logangle_powerlaw_15grb_event.sh"
    if dry_run:
        print(f"DRY launch {event} on {host} workers={workers}: {inner}")
        return
    if host == "lyra":
        shell(f"tmux has-session -t {session} 2>/dev/null || tmux new-session -d -s {session} {inner!r}")
    else:
        run(["ssh", "-n", host, f"tmux has-session -t {session} 2>/dev/null || tmux new-session -d -s {session} {inner!r}"], check=True, timeout=30)
    print(f"launched event={event} host={host} workers={workers} utc={now()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--once", action="store_true", help="Dispatch at most one wave, then exit.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-lyra-second", action="store_true")
    args = ap.parse_args()

    queue = read_queue(args.queue)
    rows = read_manifest(args.manifest)
    row_by_event = {r.event: r for r in rows}
    launched_events = set(row_by_event)
    completed = {ev for ev in queue if result_published(ev) or result_complete_local(ev)}

    lyra_already_used = any(norm_host(r.host) == "lyra" for r in rows)
    if args.allow_lyra_second:
        lyra_already_used = False

    # Active includes assigned-but-not-complete rows. The dispatcher is allowed to
    # reassign such rows only if their current host is not running that event and
    # the event is not complete.
    running_hosts = {}
    for host, workers in MACHINES:
        reachable = host_reachable(host)
        busy = True if not reachable else host_has_running_job(host)
        running_hosts[host] = busy
        print(f"host_status host={host} reachable={reachable} busy={busy}")

    free = [(h, w) for h, w in MACHINES if not running_hosts.get(h, True)]
    if lyra_already_used:
        free = [(h, w) for h, w in free if h != "lyra"]

    dispatches: list[tuple[str, str, int]] = []
    for host, workers in free:
        # next event is the first queue item not complete and not currently running.
        chosen = None
        for ev in queue:
            if ev in completed:
                continue
            existing = row_by_event.get(ev)
            if existing:
                if event_running_on_host(ev, existing.host):
                    continue
                if event_complete_on_host(ev, existing.host):
                    completed.add(ev)
                    continue
            chosen = ev
            break
        if not chosen:
            break
        existing = row_by_event.get(chosen)
        if existing:
            existing.host = host
            existing.workers = str(workers)
            existing.launched_utc = now()
            existing.run_tag = RUN_TAG
        else:
            order = str(queue.index(chosen) + 1)
            rows.append(ManifestRow(chosen, host, "power_law", order, str(workers), RUN_TAG, now()))
            row_by_event[chosen] = rows[-1]
        completed.add(chosen)  # prevent assigning twice this wave
        dispatches.append((chosen, host, workers))

    if not dispatches:
        print("no_dispatches")
        return 0

    write_manifest(args.manifest, rows)
    sync_to_hosts(args.manifest, [h for h, _ in MACHINES])
    for ev, host, workers in dispatches:
        launch(ev, host, workers, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
