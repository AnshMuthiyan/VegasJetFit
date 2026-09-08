#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="${VJF:-$ROOT/VegasJetFit}"
EVENTS="${EVENTS:-}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/structured_jet_logejet52_configs_active}"
RUN_TAG="${RUN_TAG:-structjet_logejet52_smoke_v1}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_logejet52_smoke_5temp_100walkers.toml}"
WORKERS="${WORKERS:-8}"

if [ -z "$EVENTS" ]; then
  echo "ERROR: set EVENTS to one or more GRBs, e.g. EVENTS='050525A 090618'." >&2
  exit 2
fi

cd "$VJF"
for event in $EVENTS; do
  echo "===== LOGEJET52 SMOKE PREFLIGHT ONLY: $event ====="
  EVENT="$event" \
  CONFIG_DIR="$CONFIG_DIR" \
  RUN_TAG="$RUN_TAG" \
  RESULTS_NAME_TEMPLATE="{event}_{run_tag}" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  ENABLE_PREFLIGHT=1 \
  PREFLIGHT_BURN_LENGTH=1 \
  PREFLIGHT_RUN_LENGTH=1 \
  PREFLIGHT_ONLY=1 \
  RUN_FOREGROUND=1 \
  RUN_MINIMIZER=0 \
  DRIVE_SYNC_ENABLE=0 \
  WORKERS="$WORKERS" \
  CLEAN_INCOMPLETE=1 \
  SKIP_COMPLETED=0 \
  REQUIRE_AUDIT_OBS_ROWS=0 \
  /bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
done
