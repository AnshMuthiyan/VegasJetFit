# Vendored VegasAfterglow Integration Report

Date: 2026-05-29  
Host: Lyra (`/Users/jkeohane/GRBs`)

## Summary

VegasJetFit was updated to vendor the active modified VegasAfterglow engine so collaborators can reproduce the current GRB workflow from one repository.

## What Was Done

1. Preserved source dirty-tree artifacts from:
   - `/Users/jkeohane/GRBs/VegasAfterglow_v2.0.1`
2. Vendored cleaned source copy into:
   - `/Users/jkeohane/GRBs/VegasJetFit/external/VegasAfterglow`
3. Added vendoring metadata:
   - `external/VegasAfterglow/README_LOCAL.md`
4. Added setup/verification script:
   - `scripts/setup_vendored_vegasafterglow.sh`
5. Added reproducibility docs:
   - `REPRODUCIBILITY.md`
   - `ETHAN_SETUP_ON_MAC.md`
6. Updated handoff files:
   - `/Users/jkeohane/GRBs/CODEX_HANDOFF.md`
   - `scripts/CODEX_HANDOFF.md`

## Exclusion Policy Used During Vendoring

Excluded from vendor copy:

- `.git/`
- `build/`
- `build_kfix/`
- `dist/`
- `*.egg-info/`
- `__pycache__/`
- `*.pyc`
- `.DS_Store`
- `*.so`
- `*.dylib`

## Smoke Validation

Validation command:

```bash
./scripts/setup_vendored_vegasafterglow.sh
```

Expected checks:

- prints active Python executable,
- installs `external/VegasAfterglow` in editable mode,
- verifies `VegasAfterglow` import path resolves to vendored tree,
- prints VegasAfterglow version,
- exits non-zero if import source does not match vendored location.

## Collaborator Directions

Primary quickstart is:

- `ETHAN_SETUP_ON_MAC.md`

This should be sent to Ethan/Ansh for one-command setup and verification.

