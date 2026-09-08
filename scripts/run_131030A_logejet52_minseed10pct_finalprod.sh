#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"

export EVENT="${EVENT:-131030A}"
export CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/structured_jet_logejet52_131030A_minseed10pct_final_configs_active}"
export RUN_TAG="${RUN_TAG:-structjet_logejet52_minseed10pct_finalprod_10temp_5000x5000_v1}"
if [ -z "${RESULTS_NAME_TEMPLATE:-}" ]; then
  export RESULTS_NAME_TEMPLATE='{event}_{run_tag}'
else
  export RESULTS_NAME_TEMPLATE
fi
export MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml}"

export ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
export PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-1}"
export PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-1}"
export PREFLIGHT_ONLY="${PREFLIGHT_ONLY:-0}"

export RUN_FOREGROUND="${RUN_FOREGROUND:-1}"
export RUN_MINIMIZER="${RUN_MINIMIZER:-0}"
export RUN_POSTFIT_PRODUCTS="${RUN_POSTFIT_PRODUCTS:-0}"
export DRIVE_SYNC_ENABLE="${DRIVE_SYNC_ENABLE:-0}"
export WORKERS="${WORKERS:-8}"
export KEEP_AWAKE="${KEEP_AWAKE:-1}"
export SKIP_COMPLETED="${SKIP_COMPLETED:-1}"
export CLEAN_INCOMPLETE="${CLEAN_INCOMPLETE:-1}"
export REQUIRE_AUDIT_OBS_ROWS="${REQUIRE_AUDIT_OBS_ROWS:-0}"

exec bash "$VEGAS_DIR/jwk_run_thesis_reproduction_event.sh"
