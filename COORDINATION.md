# Codex Coordination

This repo is currently being worked from multiple Macs and multiple Codex sessions.

## Current Machine Roles

- `lyra` (Mac Studio): primary GRB and batch/remote compute machine.
- `carina` (laptop): travel, teaching, monitoring, and interactive inspection machine.
- lab machines: future overflow/parallel compute machines once remote access is set up on site.

## Live State

- Date: `2026-03-16`
- Active base branch: `mac_version_jwk`
- Treat any older note implying active GRB production on `carina` as stale.
- Before launching or resuming production work, verify which machine currently owns the run and do not duplicate the same `event + run_tag`.
- Lab production claim (`2026-03-17`, shell-mass bubble production):
  - `pauley404-01`: `080413B` with run tag `theta1p0_thesis_full_shellmass_v1`
  - `pauley404-02`: `140506A` with run tag `theta1p0_thesis_full_shellmass_v1`
  - `pauley404-03`: `210905A` with run tag `theta1p0_thesis_full_shellmass_v1`

## Working Rules

- Use separate work branches per machine/session:
  - `codex/carina-<task>`
  - `codex/lyra-<task>`
- Keep commits small and push often.
- Add a short handoff note in commit messages when stopping:
  - example: `handoff: next run should resume 210905A bubble`
- Rebase frequently on the active base branch (`mac_version_jwk` for now).
- Let one Codex session own the final merge/conflict resolution for any shared task.

## Batch Safety

- Avoid writing to the same results directory from two machines.
- Before launching a long run, claim the event/run in this file or in a fresh commit message.
- If a run is only for benchmarking, note the machine and worker count.

## Suggested Division Of Labor

- `lyra`: primary production runs, heavier batch runs, minimizer batches, longer unattended jobs.
- `carina`: interactive checks, monitoring, result inspection, and light validation that does not interfere with laptop/teaching use.
- lab machines: additional science runs only after remote access, ownership rules, and result-path separation are documented.

## Handoff Template

Use a short note like this in commits or chat:

```text
machine: <lyra|carina|lab-host>
branch: codex/<machine>-<task>
status: <what is running / what changed>
next: <next safe action>
avoid: <paths or runs another session should not touch>
```
