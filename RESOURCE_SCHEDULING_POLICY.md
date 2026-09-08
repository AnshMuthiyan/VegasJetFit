# MCMC Resource Scheduling Policy

## Purpose

MCMC placement is selected from measured CPU throughput and resident-memory
headroom, rather than treating PCRC's larger core count as an automatic win.
This policy applies to final-final resolution refinements and future campaigns.

## Host Classes

| class | hardware | RAM | logical CPUs | normal allocation |
| --- | --- | ---: | ---: | ---: |
| Lyra | Apple M1 Max | 64 GiB | 10 | 8 workers for high-memory jobs, only when post-processing is idle |
| PCRC | Apple M4 Max | 48 GiB | 16 | 14 workers during the school year, only when current access is confirmed |
| Pauley | Apple M1 Max | 32 GiB | 10 | 8 workers, reserving two CPUs for macOS |

The M4 Max systems can provide higher total throughput for a normal job, but
this must be confirmed using elapsed time per completed checkpoint.  An
8-worker Pauley M1 Max job may be equally suitable when the job is not
throughput-critical, or when preserving PCRC for a job that genuinely benefits
from 15 workers.

## Memory Classes and Admission Rule

Before a new MCMC begins, run:

```bash
grb-capacity --class high
```

The tool estimates resident RAM as `4 GiB + workers x class allowance` and
requires a 30% physical-RAM reserve.  It also reports active worker RSS, which
is more useful than virtual-memory size for macOS spawned worker pools.

| class | allowance | use |
| --- | ---: | --- |
| `normal` | 1.5 GiB/worker | initial estimate for ordinary production grids and refinements |
| `high` | 3.0 GiB/worker | conservative initial estimate for a fine grid or costly event |
| `ultra` | 5.0 GiB/worker | conservative initial estimate for an ultra-fine grid |

These are conservative planning allowances, not fixed event properties or
placement decisions. A fine or ultra-fine grid is not thereby high-memory.
After the 1+1 preflight and again at the first full checkpoint, record actual
worker RSS and checkpoint elapsed time in the campaign decision record.  Use
the larger of the prior class allowance and the measured 90th-percentile
per-worker RSS plus 25% for the next placement.

## Placement Rule

1. Do not co-host MCMCs. A host with a live `jetfit.run` is unavailable.
2. **Lyra:** reserve for post-processing by default. Route an MCMC there for
   memory only after a measured warm pool or a documented host-memory incident
   supports a `lyra_only` decision record; then use 8 workers when the
   post-processing queue is idle.
3. **Pauley:** use as the dependable academic-year default for normal runs with
   a reasonable estimated wall-clock time, at 8 workers.
4. **PCRC:** treat as opportunistic school-year capacity. When current access
   is confirmed, prioritize long CPU-bound MCMCs and use 14 workers for normal
   memory behavior; use an exclusive 8-worker pool only for a measured
   memory-risk exception. Do not let an ordinary queue stall merely because a
   PCRC host is offline or no longer available.
5. A measured high-memory job: use Lyra at 8 workers **only when Lyra's
   post-processing queue is empty**. Inspect the preflight and first
   checkpoint; do not increase workers during the first campaign using this
   policy.
6. A measured ultra-memory job: use Lyra at 8 workers **only when Lyra's
   post-processing queue is empty**. Otherwise use a PCRC exclusively at 8
   workers. Never co-host work on that PCRC.
7. If available physical memory becomes low, compressed memory grows rapidly,
   or swap/page-pressure activity rises during the job, do not increase
   workers; checkpoint and resume at a lower allocation or move the job to an
   idle higher-RAM host.

## Event-Specific Placement Exceptions

- **090618:** prefer an idle PCRC for future full MCMC runs when school-year
  access is confirmed. Its high-resolution final-final run fits Pauley memory
  at eight workers but has demonstrated a very long likelihood wall time. Do
  not impose a persistent `pcrc_only` constraint when access is uncertain; a
  Pauley run is slower but preferable to an indefinitely blocked queue. If its
  preflight or first checkpoint demonstrates high/ultra memory use, replace
  that preference with the Lyra high-memory admission rule.

The dispatcher no longer applies a permanent PCRC-only exception because PCRC
access changes with the academic calendar. It enforces an optional
decision-record field `"host_constraint": "pcrc_only"` (or `"lyra_only"`);
an explicit `"any"` records a documented reassessment. It
leaves a constrained event pending until a permitted host is free; host-list
ordering alone is not an adequate guarantee.

For `lyra_only`, the decision record must contain `memory_evidence` with
`basis` (`warm_pool_measurement` or `host_memory_incident`), `host`, `workers`,
and a factual `summary`. The dispatcher rejects an unsupported Lyra-only
constraint. This prevents a previous grid name, slow runtime, or old 8-worker
allocation from becoming a permanent fleet rule.

## Current Evidence

- `111228A` very-fine on PCRC-1 runs 15 workers with about 0.5--0.6 GiB RSS
  per worker and ample headroom.
- `210905A` very-fine on Pauley-1 uses roughly 2--4 GiB RSS per worker at the
  current sampling stage, so grid/event behavior matters as much as grid name.
- `140506A` ultra-fine on PCRC-2 triggered a 15-worker host memory incident;
  its 8-worker restart remains exclusive.  It must not be used as evidence
  that all PCRC jobs require 8 workers.

The next controlled comparison should run the same one-checkpoint preflight on
one idle PCRC and one idle Pauley, then compare elapsed checkpoint time,
median/p90 worker RSS, and free-memory percentage.  That will quantify the
actual PCRC-versus-Pauley speed ratio for this code and make placement
decisions empirical.
