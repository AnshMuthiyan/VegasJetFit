# VegasJetFit Reproducibility Notes

This repository now vendors the active VegasAfterglow engine required by the current GRB workflow.

## Canonical Setup (Ethan / Ansh / New Mac)

1. Clone VegasJetFit from Ansh's repository.
2. Create and activate a Python environment (recommended: project-local venv).
3. Install VegasJetFit requirements.
4. Install and verify the vendored VegasAfterglow engine.

Example:

```bash
cd VegasJetFit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/setup_vendored_vegasafterglow.sh
```

The setup script:

- installs/rebuilds vendored VegasAfterglow in the active Python environment,
- prints Python executable,
- prints VegasAfterglow import path,
- prints VegasAfterglow version,
- fails if Python imports a non-vendored VegasAfterglow.

## Why This Matters

Current GRB results rely on modified VegasAfterglow behavior. Using arbitrary pip releases or unrelated upstream checkouts can silently change physics outputs and break reproducibility.

## Required Verification

Before production runs, confirm:

- `VegasAfterglow` imports from:
  - `external/VegasAfterglow/VegasAfterglow/__init__.py`
- reported VegasAfterglow version matches the vendored build state used by the team.

## Operational Policy

- Treat `external/VegasAfterglow/` as the pinned engine for this workflow.
- Do not swap to another VegasAfterglow source without explicit revalidation and documentation.

