#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="${EVENT:?set EVENT}"
WORKERS="${WORKERS:-8}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_core_logangle_5temp_2000x2000.toml}"
RUN_TAG="${RUN_TAG:-core_logangle_unseeded_5temp_2000x2000_v1}"
host="$(hostname | tr '[:upper:]' '[:lower:]')"

if [ "$EVENT" = "220101A" ] && [[ "$host" == pauley404-03* ]] && \
   [ -e "$VJF/reports/core_logangle_15grb_campaign/220101A_reassigned_to_pcrc1.flag" ]; then
  echo "skip_reassigned_event_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) event=$EVENT host=$host reassigned_to=pcrc-mac-studio-1"
  exit 0
fi

cd "$VJF"
EVENT="$EVENT" \
CONFIG_DIR="$VJF/structured_jet_core_logangle_15grb_configs_active" \
RUN_TAG="$RUN_TAG" \
RESULTS_NAME_TEMPLATE='{event}_{run_tag}' \
MCMC_SETTINGS="$MCMC_SETTINGS" \
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}" \
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-1}" \
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-1}" \
PREFLIGHT_ONLY="${PREFLIGHT_ONLY:-0}" \
RUN_FOREGROUND=1 \
RUN_MINIMIZER=0 \
RUN_POSTFIT_PRODUCTS=0 \
SKIP_MCMC_PLOTS=1 \
DRIVE_SYNC_ENABLE=0 \
WORKERS="$WORKERS" \
CLEAN_INCOMPLETE="${CLEAN_INCOMPLETE:-1}" \
SKIP_COMPLETED="${SKIP_COMPLETED:-1}" \
REQUIRE_AUDIT_OBS_ROWS=0 \
REQUIRE_STANDARD_EJET_GAMMA_PRIORS=0 \
/bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
