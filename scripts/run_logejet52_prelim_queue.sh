#!/usr/bin/env bash
set -euo pipefail

# Full preliminary queue template for the standard priors:
# log10(E_j,52)=[-3,2] and Gamma_0=[50,10000].
# Do not launch until Jonathan reviews the notes.  This runs production MCMC.

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="${VJF:-$ROOT/VegasJetFit}"
EVENTS="${EVENTS:-}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/structured_jet_logejet52_configs_active}"
RUN_TAG="${RUN_TAG:-structjet_logejet52_prelim_5temp_1000x1000_v1}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_structjet_prelim_5temp_1000x1000.toml}"
WORKERS="${WORKERS:-8}"

if [ -z "$EVENTS" ]; then
  echo "ERROR: set EVENTS to one or more GRBs." >&2
  exit 2
fi

cd "$VJF"
for event in $EVENTS; do
  echo "===== LOGEJET52 PRELIM MCMC: $event ====="
  EVENT="$event" \
  CONFIG_DIR="$CONFIG_DIR" \
  RUN_TAG="$RUN_TAG" \
  RESULTS_NAME_TEMPLATE="{event}_{run_tag}" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  ENABLE_PREFLIGHT=1 \
  PREFLIGHT_BURN_LENGTH=1 \
  PREFLIGHT_RUN_LENGTH=1 \
  RUN_FOREGROUND=1 \
  RUN_MINIMIZER=0 \
  DRIVE_SYNC_ENABLE=0 \
  WORKERS="$WORKERS" \
  CLEAN_INCOMPLETE=1 \
  SKIP_COMPLETED=1 \
  REQUIRE_AUDIT_OBS_ROWS=0 \
  /bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
done
