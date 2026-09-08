#!/usr/bin/env python3
"""Report live MCMC memory capacity and conservative worker-pool estimates.

The estimate deliberately uses resident memory, not virtual memory.  macOS
``spawn`` workers do not share all of their VegasAfterglow state, so the sum of
worker RSS is the useful first-order scheduling quantity.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass


HOSTS = ("lyra", "pcrc-mac-studio-1", "pcrc-mac-studio-2", "pauley404-01", "pauley404-02", "pauley404-03")
# GiB per worker measured conservatively from the July 2026 final-final runs.
# The parent process plus a 30% host reserve are added below.
RAM_PER_WORKER_GIB = {"normal": 1.5, "high": 3.0, "ultra": 5.0}
PARENT_OVERHEAD_GIB = 4.0
RESERVE_FRACTION = 0.30
PROBE = r'''
set -eu
mem_bytes=$(sysctl -n hw.memsize)
cpus=$(sysctl -n hw.logicalcpu 2>/dev/null || sysctl -n hw.ncpu)
model=$(sysctl -n hw.model 2>/dev/null || echo unknown)
chip=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown)
free_pct=$(memory_pressure 2>/dev/null | awk -F: '/System-wide memory free percentage/ {gsub(/[^0-9.]/, "", $2); print $2; exit}')
worker_rows=$(ps -axo rss=,pcpu=,command= | awk '/multiprocessing\.spawn.*spawn_main/ {rss += $1; n += 1; if (n == 1 || $1 < min) min=$1; if ($1 > max) max=$1; cpu += $2} END {printf "%d %.0f %.0f %.0f %.1f", n, rss, min, max, cpu}')
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$mem_bytes" "$cpus" "$free_pct" "$model" "$chip" "$worker_rows"
'''


@dataclass
class Host:
    name: str
    memory_gib: float
    cpus: int
    free_pct: float | None
    model: str
    chip: str
    workers: int
    worker_rss_gib: float
    worker_min_gib: float
    worker_max_gib: float
    worker_cpu: float


def probe(host: str) -> Host:
    # Deliberately omit ssh -n: this probe is supplied through standard input.
    command = ["/bin/bash", "-s"] if host == "lyra" else ["ssh", "-x", "-o", "ForwardX11=no", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, "/bin/bash", "-s"]
    result = subprocess.run(command, input=PROBE, text=True, capture_output=True, check=False, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "probe failed")
    fields = result.stdout.strip().split("\t")
    if len(fields) != 6:
        raise RuntimeError(f"unexpected probe output: {result.stdout!r}")
    workers, rss, rss_min, rss_max, cpu = fields[5].split()
    return Host(
        name=host,
        memory_gib=int(fields[0]) / 1024**3,
        cpus=int(fields[1]),
        free_pct=float(fields[2]) if fields[2] else None,
        model=fields[3], chip=fields[4], workers=int(workers),
        worker_rss_gib=float(rss) / 1048576,
        worker_min_gib=float(rss_min) / 1048576,
        worker_max_gib=float(rss_max) / 1048576,
        worker_cpu=float(cpu),
    )


def estimate(host: Host, job_class: str, workers: int) -> tuple[float, bool]:
    required = PARENT_OVERHEAD_GIB + workers * RAM_PER_WORKER_GIB[job_class]
    safe_limit = host.memory_gib * (1.0 - RESERVE_FRACTION)
    return required, required <= safe_limit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hosts", nargs="*", default=list(HOSTS), help="Hosts to inspect.")
    parser.add_argument("--class", dest="job_class", choices=RAM_PER_WORKER_GIB, default="high", help="Prospective job class (default: high).")
    parser.add_argument("--workers", type=int, help="Prospective worker count; default is 15 on PCRC and 8 elsewhere.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    for name in args.hosts:
        try:
            host = probe(name)
        except Exception as exc:  # concise status command; one failed host should not hide the rest
            records.append({"host": name, "error": str(exc)})
            continue
        proposed_workers = args.workers if args.workers is not None else (15 if name.startswith("pcrc-") else 8)
        required, fits = estimate(host, args.job_class, proposed_workers)
        available = host.workers == 0 and (host.free_pct is None or host.free_pct >= 50.0) and fits
        if host.workers:
            placement = "busy"
        elif host.free_pct is not None and host.free_pct < 50.0:
            placement = "low headroom"
        else:
            placement = "eligible" if fits else "does not fit"
        records.append({
            "host": host.name, "chip": host.chip, "memory_gib": round(host.memory_gib, 1), "logical_cpus": host.cpus,
            "free_pct": host.free_pct, "active_workers": host.workers, "active_worker_rss_gib": round(host.worker_rss_gib, 2),
            "active_worker_rss_range_gib": [round(host.worker_min_gib, 2), round(host.worker_max_gib, 2)],
            "active_worker_cpu_pct": round(host.worker_cpu, 1), "proposed_class": args.job_class,
            "proposed_workers": proposed_workers, "estimated_job_rss_gib": round(required, 1),
            "safe_rss_limit_gib": round(host.memory_gib * (1 - RESERVE_FRACTION), 1), "fits_with_reserve": fits,
            "available_for_new_job": available, "placement": placement,
        })
    if args.json:
        print(json.dumps(records, indent=2))
        return 0
    print(f"Prospective job: {args.job_class}, {args.workers or 'host default'} workers; estimate = {PARENT_OVERHEAD_GIB:.0f} GiB parent + {RAM_PER_WORKER_GIB[args.job_class]:.1f} GiB/worker; retain {RESERVE_FRACTION:.0%} RAM reserve.")
    print("host                 chip          RAM  CPU  free  active RSS (range)  estimate/safe  decision")
    for row in records:
        if "error" in row:
            print(f"{row['host']:<20} unreachable: {row['error']}")
            continue
        free = "?" if row["free_pct"] is None else f"{row['free_pct']:.0f}%"
        active = f"{row['active_workers']}w {row['active_worker_rss_gib']:.1f} ({row['active_worker_rss_range_gib'][0]:.1f}-{row['active_worker_rss_range_gib'][1]:.1f})"
        decision = str(row["placement"])
        print(f"{row['host']:<20} {row['chip']:<13} {row['memory_gib']:>4.0f}  {row['logical_cpus']:>3}  {free:>4}  {active:<22} {row['estimated_job_rss_gib']:>4.1f}/{row['safe_rss_limit_gib']:.1f}  {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
