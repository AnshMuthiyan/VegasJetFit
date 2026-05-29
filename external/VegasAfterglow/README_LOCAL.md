# Local Vendor Notes: VegasAfterglow

This directory is a vendored copy of the active VegasAfterglow engine used by the current VegasJetFit GRB workflow.

## Source Snapshot

- Source copied from:
  - `/Users/jkeohane/GRBs/VegasAfterglow_v2.0.1`
- Source branch:
  - `codex/gs02-smoothing-v201`
- Source commit:
  - `eb288506fd32e355e50e63908c758f8e45de08e6`
- Source remote:
  - `origin: git@github.com:AnshMuthiyan/AnshVegas.git`
  - `upstream: git@github.com:YihanWangAstro/VegasAfterglow.git`
- Date copied:
  - `2026-05-29`

## Dirty-tree Status at Copy Time

The source tree had uncommitted modifications. Preservation artifacts were recorded at:

- `/Users/jkeohane/GRBs/VegasAfterglow_v2.0.1_dirty_worktree_20260528.patch`
- `/Users/jkeohane/GRBs/VegasAfterglow_v2.0.1_dirty_worktree_20260528.status.txt`

This vendored copy is intended to capture the effective engine state used by active fitting workflows.

## Why This Is Vendored

VegasJetFit has repeatedly depended on a specific local, modified VegasAfterglow build. Vendoring here reduces ambiguity about:

- which source tree is active,
- which code changes are required for reproducibility,
- which engine Ethan/Ansh should install for consistent outputs.

## Guardrails

- Do not casually replace this directory with an arbitrary upstream checkout.
- Do not switch to pip-released VegasAfterglow for this workflow unless we explicitly revalidate fits.
- Use `scripts/setup_vendored_vegasafterglow.sh` to install and verify import path/version.

