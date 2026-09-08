# Dynamic MCMC Dispatch Policy

Updated: 2026-09-02

This is the default practice for multi-GRB MCMC campaigns.

## Default Rule

1. Use all available MCMC machines for the first batch, including Lyra if Lyra is free.
2. Do not assign second-round GRBs to specific machines ahead of time.
3. When a machine finishes, dispatch the next queued GRB to that machine.
4. Do not dispatch a second ordinary MCMC run to Lyra by default. After Lyra's first MCMC assignment, use Lyra for pulling results, minimization, post-processing, validation, and Share_Folder publishing. **Exception:** high-memory MCMCs are Lyra-only at 8 workers, but wait for any active Lyra post-processing to finish first. Carina may perform the same post-processing work concurrently when it is awake and available; select the host with capacity, without waiting for the other host to become idle.

This avoids idle PCRC/Pauley time while keeping Lyra available for the serial/interactive work that bottlenecks the science workflow, except where Lyra's 64 GiB RAM is specifically needed.

### Memory Classification Requires Measurement

Do not infer a high-memory classification from a high-resolution grid, a slow
likelihood, a high CPU load, or a low-memory-pressure snapshot on a roomy host.
After a guarded warm-pool preflight at the intended worker count, record the
aggregate worker RSS, the maximum worker RSS, host RAM, compression, swap, and
page pressure. Use the aggregate fraction of host RAM as the placement rule:

- below 55% with no compression/swap growth: normal-memory placement is allowed;
- 55--70%: dedicate the host and avoid concurrent post-processing;
- above 70%, or any sustained swap/compression/page-pressure growth: classify as
  high-memory and cap workers or route to Lyra.

For example, `080413B` measured 21.97 GiB aggregate RSS at 15 active workers
on PCRC-1 (48 GiB, about 46%), so it is CPU-heavy but not Lyra-only.

## Post-Processing Hosts

- Lyra and Carina are both approved post-processing hosts.
- Prefer Carina for unattended overnight pulls, minimization, products, and
  publication when it is awake; use Lyra concurrently for a separate completed
  result when capacity is available.
- Do not move a running product build between hosts merely to balance load.
- For a given shared campaign, designate exactly one publishing host (normally
  Lyra). Carina may pull, minimize, and generate a complete local result, but
  transfers that completed result to the publishing host with `rsync`; only the
  publisher writes or renames directories below `Share_Folder/Fits/...`.
- Never run two post-processing wrappers that publish the same event/campaign
  pair. A duplicate Drive client upload can create nested or suffixed folders
  even when the scientific contents are identical.
- Carina has Homebrew `tmux` at `/opt/homebrew/bin/tmux`. Non-interactive SSH
  sessions must prepend `/opt/homebrew/bin:/usr/local/bin` to `PATH` before
  invoking it; then use normal tmux sessions and logs.

## Machine Priority

During the academic year, use machines in this default order unless a campaign
has a documented reason not to:

```text
pauley404-01:8
pauley404-02:8
pauley404-03:8
pcrc-mac-studio-1:14  (only after current access is confirmed)
pcrc-mac-studio-2:14  (only after current access is confirmed)
lyra:8
```

The PCRC machines have 16 logical CPUs. They supplied valuable extra throughput
during the summer, when 15 workers could be used, but school-year access must
not be assumed. When current access is confirmed, use 14 workers and leave two
logical CPUs for macOS and student use. A normal campaign must not remain
blocked solely because PCRC is offline or unavailable; use an idle Pauley at
8 workers. The dispatcher rejects an accidental mismatch between its active
seasonal allocation and `--machines` unless an explicit override is provided.

### High-Memory Exception

For a fine/very-fine/ultra-fine job classified as `high` or `ultra` by
`RESOURCE_SCHEDULING_POLICY.md`, mark its manifest host `pending-lyra` and
include it in the dispatcher's `--lyra-only-events` list. Run
`grb-capacity --class high --workers 8` (or `--class ultra`) before launch.
Wait for an active Lyra product build to finish; do not silently place the job
on a 32 GiB Pauley host to fill the gap.

### Duration-Aware Assignment

Use the resource class and prior checkpoint/wall-clock evidence together:

1. Lyra is for post-processing first, then high/ultra-memory MCMCs at 8
   workers once its product queue is idle.
2. Pauley is the dependable academic-year default for normal runs, at 8
   workers.
3. PCRC is preferred for the long CPU-bound tail only when current access has
   been confirmed; use 14 workers during the school year.

This ordering prevents slow jobs from monopolizing a Pauley while a faster
routine job waits for an available PCRC.

For an established CPU-bound outlier such as `090618`, prefer PCRC when access
is currently confirmed. Use `"host_constraint": "pcrc_only"` only for that
specific active-access window; otherwise leave the constraint as `"any"` so a
Pauley can make progress instead of becoming a stale blocker. Reassess if its
preflight or first checkpoint shows a high/ultra-memory requirement.

## Required Campaign Files

Each campaign should have:

- a queue CSV with an `event` column in the desired scientific priority order;
- a short `README.md` and a fuller `CAMPAIGN_METHOD_REPORT.md`, generated from
  the canonical TOMLs and manifest with
  `scripts/write_campaign_documentation.py` before the first MCMC launch;
  write the same pair into the Share_Folder campaign directory when it exists;
- a dispatch manifest CSV with columns:

```text
event,host,csm_family,queue_order,workers,run_tag,launched_utc
```

The manifest is the source of truth for what host owns each event.

## Standard Dispatcher

Use the reusable dispatcher for new campaigns:

```bash
cd /Users/jkeohane/GRBs/VegasJetFit
/Users/jkeohane/GRBs/.venv/bin/python scripts/dynamic_dispatch_campaign.py \
  --queue reports/<campaign>/dynamic_event_queue.csv \
  --manifest reports/<campaign>/dispatch_manifest.csv \
  --run-tag <run_tag> \
  --event-script scripts/<campaign_event_runner>.sh \
  --campaign /Users/jkeohane/GRBs/Share_Folder/Fits/<campaign_share_path> \
  --session-prefix <short_campaign_prefix>
```

For unattended monitoring, run the dispatcher in a Lyra tmux loop:

```bash
tmux new-session -d -s dynamic_dispatch_<campaign> \
  'cd /Users/jkeohane/GRBs/VegasJetFit && while true; do date -u; /Users/jkeohane/GRBs/.venv/bin/python scripts/dynamic_dispatch_campaign.py <args>; sleep 300; done'
```

## Event Runner Requirement

The event runner must honor these environment variables:

```text
EVENT
WORKERS
RUN_TAG
DISPATCH_MANIFEST
```

It should also enforce the manifest host assignment before launching. If a stale static queue tries to start an event whose manifest host is another machine, the runner should print a `skip_unassigned_event` message and exit successfully.

## Current Campaign Exception

The active 2026-06-27 10-temperature campaign is already running with the campaign-specific wrapper:

```text
VegasJetFit/scripts/dynamic_dispatch_core_logangle_powerlaw_10temp.py
```

Leave that live campaign-specific dispatcher in place. Use `scripts/dynamic_dispatch_campaign.py` as the template/default for future campaigns.
