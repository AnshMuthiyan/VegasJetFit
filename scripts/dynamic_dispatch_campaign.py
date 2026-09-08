#!/usr/bin/env python3
"""Reusable dynamic MCMC dispatcher for multi-GRB campaigns.

Default policy:
- Fill all available machines for the first batch, including Lyra if requested.
- After Lyra has received one MCMC assignment, reserve it for minimization/postfit.
- A Lyra-only event must carry explicit measured memory evidence in its
  decision record; a qualitative resolution label is never sufficient.
- Do not pre-bind second-round events to hosts; assign the next queued event only
  when a machine is actually free.
- Keep a central manifest as the source of truth so stale static queues can skip
  events that were reassigned dynamically.
- A campaign decision record may set ``host_constraint`` to ``pcrc_only`` or
  ``lyra_only``. This makes exceptional placement durable rather than relying
  on the order in which hosts happen to become free.

This script is intentionally generic. Campaign-specific values come from CLI
arguments and environment variables passed to the event runner.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/jkeohane/GRBs")
VJF = ROOT / "VegasJetFit"
# Academic-year default: use dependable Pauley hosts first. PCRC remains useful
# opportunistic capacity, at 14 of 16 logical CPUs, when current access exists.
DEFAULT_MACHINES = "pauley404-01:8,pauley404-02:8,pauley404-03:8,pcrc-mac-studio-1:14,pcrc-mac-studio-2:14,lyra:8"
DEFAULT_SYNC_PATHS = [
    VJF / "scripts/run_core_logangle_powerlaw_15grb_event.sh",
    VJF / "scripts/run_core_logangle_powerlaw_15grb_queue.sh",
]
# Known event-level exceptions that should survive a fresh campaign queue.
# A campaign decision record can explicitly replace one of these when a new
# preflight supplies contrary resource evidence.
DEFAULT_EVENT_HOST_CONSTRAINTS: dict[str, str] = {}
SSH_OPTS = ["-n", "-x", "-o", "ForwardX11=no", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check, timeout=timeout)


def shell(cmd: str, *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, check=check, timeout=timeout)


def norm_host(host: str) -> str:
    host = host.strip().lower()
    return host[:-6] if host.endswith(".local") else host


def is_pending_host(host: str) -> bool:
    return not host.strip() or norm_host(host).startswith("pending")


def pending_host_allows(marker: str, host: str) -> bool:
    """Return whether a pending manifest marker permits assignment to host."""
    marker_norm = norm_host(marker)
    host_norm = norm_host(host)
    if not marker_norm or marker_norm in {"pending", "pending-next-free"}:
        return True
    if marker_norm == "pending-lyra":
        return host_norm == "lyra"
    if marker_norm in {"pending-pcrc", "pending-pcrc-highres"}:
        return host_norm.startswith("pcrc-")
    if marker_norm == "pending-pauley":
        return host_norm.startswith("pauley")
    return marker_norm.startswith("pending")


@dataclass
class ManifestRow:
    event: str
    host: str
    csm_family: str
    queue_order: str
    workers: str
    run_tag: str
    launched_utc: str


def parse_machines(spec: str) -> list[tuple[str, int]]:
    machines: list[tuple[str, int]] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"machine entry must be host:workers, got {item!r}")
        host, workers = item.rsplit(":", 1)
        machines.append((host.strip(), int(workers)))
    if not machines:
        raise ValueError("at least one machine is required")
    return machines


def expected_workers(host: str, pcrc_workers: int) -> int | None:
    """Return the standard worker allocation for a known campaign host."""
    normalized = norm_host(host)
    if normalized.startswith("pcrc-"):
        return pcrc_workers
    if normalized.startswith("pauley") or normalized == "lyra":
        return 8
    return None


def validate_worker_policy(
    machines: list[tuple[str, int]], *, pcrc_workers: int, allow_override: bool
) -> None:
    """Fail closed on an accidental under-allocation of a known host."""
    if allow_override:
        return
    mismatches = [
        f"{host}:{workers} (expected {expected})"
        for host, workers in machines
        if (expected := expected_workers(host, pcrc_workers)) is not None and workers != expected
    ]
    if mismatches:
        raise ValueError(
            "worker policy mismatch: "
            + ", ".join(mismatches)
            + ". Use --pcrc-workers for an intentional PCRC seasonal allocation "
            "or --allow-worker-policy-override for a one-off exception."
        )


def read_queue(path: Path) -> list[str]:
    with path.open() as f:
        reader = csv.DictReader(f)
        if "event" not in (reader.fieldnames or []):
            raise ValueError(f"queue file must have an event column: {path}")
        return [r["event"].strip() for r in reader if r.get("event", "").strip()]


def read_manifest(path: Path, default_run_tag: str) -> list[ManifestRow]:
    if not path.exists():
        return []
    with path.open() as f:
        rows: list[ManifestRow] = []
        for r in csv.DictReader(f):
            event = r.get("event", "").strip()
            if not event:
                continue
            rows.append(ManifestRow(
                event=event,
                host=r.get("host", "").strip(),
                csm_family=r.get("csm_family", "power_law").strip(),
                queue_order=r.get("queue_order", "").strip(),
                workers=r.get("workers", "").strip(),
                run_tag=r.get("run_tag", default_run_tag).strip() or default_run_tag,
                launched_utc=r.get("launched_utc", "").strip(),
            ))
        return rows


def write_manifest(path: Path, rows: list[ManifestRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "host", "csm_family", "queue_order", "workers", "run_tag", "launched_utc"])
        for r in rows:
            w.writerow([r.event, r.host, r.csm_family, r.queue_order, r.workers, r.run_tag, r.launched_utc])


def result_dir(results_root: Path, event: str, run_tag: str, template: str) -> Path:
    return results_root / template.format(event=event, run_tag=run_tag)


def host_reachable(host: str) -> bool:
    host = norm_host(host)
    if host == "lyra":
        return True
    cp = run(["ssh", *SSH_OPTS, host, "true"], check=False, timeout=12)
    return cp.returncode == 0


def host_has_running_job(host: str, busy_pattern: str) -> bool:
    # Restrict the scan to actual ``python -m jetfit.run`` commands. A bare
    # search for ``jetfit.run`` also sees this dispatcher's --busy-pattern arg.
    command_check = (
        "needle='-m jetfit.'; needle=\"${needle}run\"; ps -axo command | "
        f"awk -v pattern={shlex.quote(busy_pattern)} "
        "-v needle=\"$needle\" 'index($0, needle) && index($0, pattern) { found=1 } END { exit !found }'"
    )
    host = norm_host(host)
    if host == "lyra":
        return shell(command_check, check=False).returncode == 0
    return run(["ssh", *SSH_OPTS, host, command_check], check=False, timeout=12).returncode == 0


def lyra_postprocessing_active() -> bool:
    """Return whether a live Lyra post-processing watcher holds its activity marker."""
    activity_dir = VJF / "logs/postprocess_activity"
    for marker in activity_dir.glob("*.active"):
        try:
            values = dict(
                line.split("=", 1)
                for line in marker.read_text().splitlines()
                if "=" in line
            )
            pid = int(values.get("pid", ""))
            os.kill(pid, 0)
        except (OSError, ValueError):
            marker.unlink(missing_ok=True)
            continue
        return True
    return False


def event_running_on_host(event: str, host: str, run_tag: str) -> bool:
    if is_pending_host(host):
        return False
    pattern = f"{event}_{run_tag}"
    grep = f"ps -axo command | grep '[j]etfit.run' | grep -F {shlex.quote(pattern)}"
    host = norm_host(host)
    if host == "lyra":
        return shell(grep, check=False).returncode == 0
    return run(["ssh", *SSH_OPTS, host, grep], check=False, timeout=12).returncode == 0


def event_complete_on_host(event: str, host: str, run_tag: str, results_root: Path, template: str) -> bool:
    if is_pending_host(host):
        return False
    remote = result_dir(results_root, event, run_tag, template)
    test = f"test -s {shlex.quote(str(remote / 'chain.npz'))} -a -s {shlex.quote(str(remote / 'best_fit.json'))}"
    host = norm_host(host)
    if host == "lyra":
        return (remote / "chain.npz").is_file() and (remote / "best_fit.json").is_file()
    return run(["ssh", *SSH_OPTS, host, test], check=False, timeout=12).returncode == 0


def result_published(event: str, campaign: Path | None, marker: str) -> bool:
    return bool(campaign) and (campaign / event / marker).is_file()


def validate_lyra_only_evidence(records: dict[str, dict], events: set[str]) -> None:
    """Require actual memory evidence before reserving Lyra for an MCMC."""
    # A Lyra-only constraint reserves the primary post-processing host, so it
    # must be based on an observed warm pool or an actual host-memory incident.
    # Grid names, CPU saturation, and an old worker default are not evidence.
    missing_evidence = []
    invalid_evidence = []
    for event in sorted(events):
        record = records[event]
        if record.get("host_constraint") != "lyra_only":
            continue
        evidence = record.get("memory_evidence")
        if not isinstance(evidence, dict):
            missing_evidence.append(event)
            continue
        basis = evidence.get("basis")
        if basis not in {"warm_pool_measurement", "host_memory_incident"}:
            invalid_evidence.append(f"{event}={basis!r}")
            continue
        required = {"basis", "host", "workers", "summary"}
        absent = sorted(key for key in required if not evidence.get(key))
        if absent:
            invalid_evidence.append(f"{event} missing {','.join(absent)}")
    if missing_evidence or invalid_evidence:
        details = []
        if missing_evidence:
            details.append("missing memory_evidence for " + ", ".join(missing_evidence))
        details.extend(invalid_evidence)
        raise ValueError(
            "lyra_only requires measured memory evidence "
            "(basis=warm_pool_measurement or host_memory_incident; host, workers, summary): "
            + "; ".join(details)
        )


def read_decision_records(path: Path, events: list[str]) -> dict[str, dict]:
    """Require an approved, durable decision snapshot before dispatch."""
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read decision-record file {path}: {exc}") from exc
    records = payload.get("events")
    if not isinstance(records, dict):
        raise ValueError(f"decision-record file has no events mapping: {path}")
    missing = [event for event in events if not isinstance(records.get(event), dict)]
    if missing:
        raise ValueError(f"decision records missing for: {', '.join(missing)}")
    invalid = {
        event: records[event].get("host_constraint")
        for event in events
        if records[event].get("host_constraint") not in {None, "", "any", "lyra_only", "pcrc_only"}
    }
    if invalid:
        details = ", ".join(f"{event}={constraint!r}" for event, constraint in invalid.items())
        raise ValueError(f"invalid decision-record host_constraint: {details}")
    selected = {event: records[event] for event in events}
    validate_lyra_only_evidence(selected, set(events))
    return selected


def sync_to_hosts(paths: list[Path], hosts: list[str]) -> set[str]:
    """Synchronize launch inputs, isolating a failed host from the campaign."""
    synced: set[str] = set()
    for host in hosts:
        if norm_host(host) == "lyra":
            synced.add(norm_host(host))
            continue
        try:
            host_ok = True
            for path in paths:
                remote_parent = str(path.parent)
                mkdir = run(
                    ["ssh", *SSH_OPTS, host, f"mkdir -p {shlex.quote(remote_parent)}"],
                    check=False,
                    timeout=20,
                )
                if mkdir.returncode != 0:
                    host_ok = False
                    print(f"sync_warning host={host} path={path} stage=mkdir returncode={mkdir.returncode}")
                    break
                if path.is_dir():
                    result = run(["rsync", "-a", f"{path}/", f"{host}:{path}/"], check=False, timeout=30)
                else:
                    result = run(["rsync", "-a", str(path), f"{host}:{path}"], check=False, timeout=30)
                if result.returncode != 0:
                    host_ok = False
                    print(f"sync_warning host={host} path={path} stage=rsync returncode={result.returncode}")
                    break
            if host_ok:
                synced.add(norm_host(host))
        except subprocess.TimeoutExpired as exc:
            print(f"sync_warning host={host} stage=timeout seconds={exc.timeout}")
    return synced


def launch(event: str, host: str, workers: int, run_tag: str, args: argparse.Namespace, dry_run: bool = False) -> None:
    session = f"{args.session_prefix}_{event}"
    env = {
        "EVENT": event,
        "WORKERS": str(workers),
        "RUN_TAG": run_tag,
        "DISPATCH_MANIFEST": str(args.manifest),
    }
    if args.decision_records:
        env["EVENT_DECISION_RECORDS"] = str(args.decision_records)
    env.update(args.env or {})
    env_prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in sorted(env.items()))
    inner = f"cd {shlex.quote(str(VJF))} && env {env_prefix} bash {shlex.quote(str(args.event_script))}"
    if dry_run:
        print(f"DRY launch event={event} host={host} workers={workers}: {inner}")
        return
    host_norm = norm_host(host)
    if host_norm == "lyra":
        shell(f"tmux has-session -t {shlex.quote(session)} 2>/dev/null || tmux new-session -d -s {shlex.quote(session)} {shlex.quote(inner)}")
    else:
        remote_tmux = (
            "PATH=/opt/homebrew/bin:/usr/local/bin:$PATH; "
            f"tmux has-session -t {shlex.quote(session)} 2>/dev/null || "
            f"tmux new-session -d -s {shlex.quote(session)} {shlex.quote(inner)}"
        )
        run(["ssh", *SSH_OPTS, host, remote_tmux], check=True, timeout=30)
    print(f"launched event={event} host={host} workers={workers} utc={now()}")


def parse_env(items: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--env entries must be KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        env[key] = value
    return env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", type=Path, required=True, help="CSV with at least an event column in dispatch order.")
    ap.add_argument("--manifest", type=Path, required=True, help="Central dispatch manifest CSV to read/write.")
    ap.add_argument("--run-tag", required=True)
    ap.add_argument("--event-script", type=Path, required=True, help="Event runner script that honors EVENT, WORKERS, RUN_TAG, DISPATCH_MANIFEST.")
    ap.add_argument("--results-root", type=Path, default=VJF / "jetfit/results")
    ap.add_argument("--results-template", default="{event}_{run_tag}")
    ap.add_argument("--campaign", type=Path, default=None, help="Optional Share_Folder campaign path for published-marker checks.")
    ap.add_argument("--published-marker", default="core_postfit_products.validated")
    ap.add_argument("--machines", default=DEFAULT_MACHINES, help="Comma-separated host:workers list in priority order.")
    ap.add_argument("--pcrc-workers", type=int, default=14, help="Workers per PCRC host during the school year; 14 reserves two of 16 logical CPUs for macOS and student use.")
    ap.add_argument("--allow-worker-policy-override", action="store_true", help="Allow nonstandard worker counts for a deliberate one-off dispatch.")
    ap.add_argument("--session-prefix", default="dynamic_mcmc")
    ap.add_argument("--busy-pattern", default=None, help="Pattern used to detect a busy campaign MCMC; defaults to run-tag.")
    ap.add_argument("--allow-lyra-second", action="store_true", help="Disable the default Lyra-first-batch-only rule.")
    ap.add_argument(
        "--lyra-only-events",
        default="",
        help="Comma-separated events explicitly approved for Lyra-only dispatch after post-processing is idle.",
    )
    ap.add_argument(
        "--pcrc-only-events",
        default="",
        help="Comma-separated CPU-bound events that must wait for an idle PCRC host.",
    )
    ap.add_argument(
        "--disable-default-event-constraints",
        action="store_true",
        help="Ignore built-in historical placement exceptions for a deliberate campaign-specific reassessment.",
    )
    ap.add_argument("--sync-path", action="append", type=Path, default=[], help="Extra path to rsync to remotes before launch.")
    ap.add_argument("--decision-records", type=Path, help="Required pre-dispatch event-decision JSON; copied into each run directory.")
    ap.add_argument("--env", action="append", default=[], help="Extra KEY=VALUE environment passed to event script.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    args.env = parse_env(args.env)
    if not args.queue.is_absolute():
        args.queue = (Path.cwd() / args.queue).resolve()
    if not args.manifest.is_absolute():
        args.manifest = (Path.cwd() / args.manifest).resolve()
    if not args.event_script.is_absolute():
        args.event_script = (Path.cwd() / args.event_script).resolve()
    args.sync_path = [
        (Path.cwd() / path).resolve() if not path.is_absolute() else path
        for path in args.sync_path
    ]
    if args.decision_records and not args.decision_records.is_absolute():
        args.decision_records = (Path.cwd() / args.decision_records).resolve()

    machines = parse_machines(args.machines)
    validate_worker_policy(
        machines,
        pcrc_workers=args.pcrc_workers,
        allow_override=args.allow_worker_policy_override,
    )
    queue = read_queue(args.queue)
    lyra_only_events = {event.strip() for event in args.lyra_only_events.split(",") if event.strip()}
    pcrc_only_events = {event.strip() for event in args.pcrc_only_events.split(",") if event.strip()}
    for option, constrained_events in (("--lyra-only-events", lyra_only_events), ("--pcrc-only-events", pcrc_only_events)):
        unknown = sorted(constrained_events - set(queue))
        if unknown:
            raise ValueError(f"{option} not present in queue: {', '.join(unknown)}")
    decision_records = read_decision_records(args.decision_records, queue) if args.decision_records else {}
    host_constraints = {} if args.disable_default_event_constraints else {
        event: constraint
        for event, constraint in DEFAULT_EVENT_HOST_CONSTRAINTS.items()
        if event in queue
    }
    for event, record in decision_records.items():
        # An explicit record is the campaign's scientific/operational decision,
        # including the ability to supersede a historical default with "any".
        if record.get("host_constraint") is not None:
            host_constraints[event] = record.get("host_constraint")
    for event, constraint in host_constraints.items():
        if constraint == "lyra_only":
            lyra_only_events.add(event)
        elif constraint == "pcrc_only":
            pcrc_only_events.add(event)
    overlap = sorted(lyra_only_events & pcrc_only_events)
    if overlap:
        raise ValueError(f"conflicting host constraints for: {', '.join(overlap)}")
    if lyra_only_events:
        if not args.decision_records:
            raise ValueError("--lyra-only-events requires --decision-records with measured memory evidence")
        constrained_records = {}
        for event in lyra_only_events:
            if event not in decision_records:
                raise ValueError(f"--lyra-only-events lacks a decision record for {event}")
            constrained_records[event] = {**decision_records[event], "host_constraint": "lyra_only"}
        validate_lyra_only_evidence(constrained_records, lyra_only_events)
    rows = read_manifest(args.manifest, args.run_tag)
    original_rows = [ManifestRow(**vars(row)) for row in rows]
    row_by_event = {r.event: r for r in rows}
    completed = {ev for ev in queue if result_published(ev, args.campaign, args.published_marker)}

    lyra_already_used = any(norm_host(r.host) == "lyra" for r in rows) and not args.allow_lyra_second
    busy_pattern = args.busy_pattern or args.run_tag

    free: list[tuple[str, int]] = []
    lyra_postprocess_busy = lyra_postprocessing_active()
    if lyra_postprocess_busy and lyra_only_events:
        print("lyra_postprocess_busy=true")
    for host, workers in machines:
        reachable = host_reachable(host)
        busy = True if not reachable else host_has_running_job(host, busy_pattern)
        print(f"host_status host={host} reachable={reachable} busy={busy}")
        if reachable and not busy:
            free.append((host, workers))
    dispatches: list[tuple[str, str, int, str]] = []
    for host, workers in free:
        chosen = None
        for event in queue:
            if event in completed:
                continue
            is_lyra_only = event in lyra_only_events
            is_pcrc_only = event in pcrc_only_events
            if is_lyra_only and norm_host(host) != "lyra":
                continue
            if is_pcrc_only and not norm_host(host).startswith("pcrc-"):
                continue
            if is_lyra_only and lyra_postprocess_busy:
                continue
            if lyra_already_used and norm_host(host) == "lyra" and not is_lyra_only:
                continue
            existing = row_by_event.get(event)
            if existing:
                # An explicit manifest assignment owns this event.  Only rows
                # marked pending may be dynamically assigned; otherwise a
                # failed/slow launch can be "re-launched" on every poll.
                if not is_pending_host(existing.host):
                    if event_complete_on_host(event, existing.host, existing.run_tag, args.results_root, args.results_template):
                        completed.add(event)
                    continue
                if not pending_host_allows(existing.host, host):
                    continue
            chosen = event
            break
        if chosen is None:
            break
        if args.decision_records:
            # Re-read immediately before a launch in case a decision document
            # was changed while this dispatcher was polling.
            read_decision_records(args.decision_records, [chosen])
        existing = row_by_event.get(chosen)
        if existing:
            existing.host = host
            workers = int(existing.workers) if existing.workers.strip() else workers
            run_tag = existing.run_tag or args.run_tag
            existing.workers = str(workers)
            existing.run_tag = run_tag
            existing.launched_utc = now()
        else:
            run_tag = args.run_tag
            order = str(queue.index(chosen) + 1)
            row = ManifestRow(chosen, host, "power_law", order, str(workers), run_tag, now())
            rows.append(row)
            row_by_event[chosen] = row
        completed.add(chosen)
        dispatches.append((chosen, host, workers, run_tag))

    if not dispatches:
        print("no_dispatches")
        return 0

    if not args.dry_run:
        write_manifest(args.manifest, rows)
        decision_paths = [args.decision_records] if args.decision_records else []
        destination_hosts = list(dict.fromkeys(host for _, host, _, _ in dispatches))
        synced_hosts = sync_to_hosts(
            [args.manifest, args.event_script, *DEFAULT_SYNC_PATHS, *args.sync_path, *decision_paths],
            destination_hosts,
        )
        failed_events = {
            event for event, host, _, _ in dispatches if norm_host(host) not in synced_hosts
        }
        if failed_events:
            original_by_event = {row.event: row for row in original_rows}
            rows = [row for row in rows if row.event not in failed_events]
            rows.extend(original_by_event[event] for event in failed_events if event in original_by_event)
            write_manifest(args.manifest, rows)
            dispatches = [
                item for item in dispatches if norm_host(item[1]) in synced_hosts
            ]
            print(f"deferred_after_sync_failure events={','.join(sorted(failed_events))}")
    for event, host, workers, run_tag in dispatches:
        launch(event, host, workers, run_tag, args, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"dynamic_dispatch_error: {exc}", file=sys.stderr)
        raise
