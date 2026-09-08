#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="${EVENT:?set EVENT}"
FAMILY="${FAMILY:-sbpl}"
WORKERS="${WORKERS:-8}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml}"
case "$FAMILY" in
  sbpl)
    CONFIG_DIR="$VJF/structured_jet_sbpl_logejet52_penultimate_configs_active"
    RUN_TAG="structjet_sbpl_logejet52_penultimate_10temp_5000x5000_v1"
    ;;
  powerlaw)
    CONFIG_DIR="$VJF/structured_jet_logejet52_sbpl_pair_powerlaw_csm_configs_active"
    RUN_TAG="structjet_logejet52_powerlawcsm_penultimate_10temp_5000x5000_v1"
    ;;
  *) echo "ERROR: FAMILY must be sbpl or powerlaw" >&2; exit 2;;
esac
cd "$VJF"
EVENT="$EVENT" \
CONFIG_DIR="$CONFIG_DIR" \
RUN_TAG="$RUN_TAG" \
RESULTS_NAME_TEMPLATE='{event}_{run_tag}' \
MCMC_SETTINGS="$MCMC_SETTINGS" \
ENABLE_PREFLIGHT=1 \
PREFLIGHT_BURN_LENGTH=1 \
PREFLIGHT_RUN_LENGTH=1 \
PREFLIGHT_ONLY=0 \
RUN_FOREGROUND=1 \
RUN_MINIMIZER=0 \
RUN_POSTFIT_PRODUCTS=0 \
DRIVE_SYNC_ENABLE=0 \
WORKERS="$WORKERS" \
CLEAN_INCOMPLETE="${CLEAN_INCOMPLETE:-1}" \
SKIP_COMPLETED="${SKIP_COMPLETED:-1}" \
REQUIRE_AUDIT_OBS_ROWS=0 \
/bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
