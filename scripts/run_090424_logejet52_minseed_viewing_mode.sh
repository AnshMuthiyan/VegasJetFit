#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
MODE_FAMILY="${MODE_FAMILY:?set MODE_FAMILY to onaxis_tv0p045, nearaxis_tv0p177, or offaxis_tv0p374}"

export EVENT="${EVENT:-090424}"
export CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/structured_jet_logejet52_090424_minseed_viewing_mode_configs_active/$MODE_FAMILY}"
export RUN_TAG="${RUN_TAG:-structjet_logejet52_minseed_${MODE_FAMILY}_viewing_mode_diag_10temp_1000x1000_v1}"
if [ -z "${RESULTS_NAME_TEMPLATE:-}" ]; then
  export RESULTS_NAME_TEMPLATE='{event}_{run_tag}'
else
  export RESULTS_NAME_TEMPLATE
fi
export MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_logejet52_mode_diag_10temp_1000x1000.toml}"
export ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
export PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-1}"
export PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-1}"
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
