# VegasJetFit/scripts Handoff

This directory contains active post-fit product scripts.

## Vendored Engine Status (2026-05-29)

- The reproducible VegasAfterglow engine is now vendored at:
  - `/Users/jkeohane/GRBs/VegasJetFit/external/VegasAfterglow`
- Install/verify script:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/setup_vendored_vegasafterglow.sh`
- Repro docs:
  - `/Users/jkeohane/GRBs/VegasJetFit/REPRODUCIBILITY.md`
  - `/Users/jkeohane/GRBs/VegasJetFit/ETHAN_SETUP_ON_MAC.md`

## Known Relevant Files

- `generate_postfit_products.py`
  - builds radius-based post-fit products
  - creates `mass_profile.csv` and `mass_profile.pdf`
  - relevant terms: `m_swept_iso_g`, `m_decel_iso_g`, `m_ejecta_iso_g`, `r_decel_cm`, `r_ejecta_equal_cm`

- `build_mass_vs_time_products.py`
  - builds mass-vs-observer-time products
  - calls `model.vegas_model.details(...)`
  - known fields used: `details.fwd.t_obs`, `details.fwd.N_p`
  - need to identify the instantaneous forward-shock Lorentz factor field in `details.fwd`

## Current Swept-Mass Issue

The old diagnostic uses:

```text
M_ej / Gamma0
```

The desired diagnostic uses instantaneous Lorentz factor:

```text
M_ej / Gamma(t or r)
10 M_ej / Gamma(t or r)
```

The Gamma array must be on the same grid as swept-up mass, observer time, and radius, or it must be explicitly interpolated and documented.

Preserve units:

- time plot bottom axis: days
- time plot top axis: seconds
- radius plot bottom axis: cm
- radius plot top axis: parsecs
- mass plot left axis: grams
- mass plot right axis: solar masses

Do not update anything inside a `trash` folder.

## Notes for Future Codex Sessions

Before searching broadly, inspect this file and the root-level files:

- `/Users/jkeohane/GRBs/AGENTS.md`
- `/Users/jkeohane/GRBs/CODEX_HANDOFF.md`
- `/Users/jkeohane/GRBs/WORKSPACE_MAP.md`
- `/Users/jkeohane/GRBs/CODEX_TODO_WHEN_TOKENS_RETURN.md`

If the forward-shock Lorentz-factor field in `details.fwd` is discovered, record it here with the exact field name, array shape, and the line/file where it is used.

### Discovered Forward-Shock Lorentz Field

- Field: `details.fwd.Gamma`
- Access pattern used in current scripts: `details.fwd.Gamma[0, 0, :]`
- Grid compatibility: aligned with `details.fwd.t_obs[0,0,:]`, `details.fwd.r[0,0,:]`, and `details.fwd.N_p[0,0,:]` in the current VegasAfterglow detail output.
- Current usage locations:
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/build_mass_vs_time_products.py`
  - `/Users/jkeohane/GRBs/VegasJetFit/scripts/generate_postfit_products.py`
