#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 EVENT [EVENT ...]" >&2
  exit 2
fi

export ROOT="${ROOT:-/Users/jkeohane/GRBs}"
export VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
export CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/structured_jet_anshstyle_thetavthawed_configs_active}"
export RUN_TAG="${RUN_TAG:-anshstyle_structjet_thetavthawed_v1}"
export MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml}"
export RUN_MINIMIZER="${RUN_MINIMIZER:-1}"
export RUN_FOREGROUND="${RUN_FOREGROUND:-1}"
export KEEP_AWAKE="${KEEP_AWAKE:-1}"
export SKIP_COMPLETED="${SKIP_COMPLETED:-1}"

runner="$VEGAS_DIR/jwk_run_thesis_reproduction_event.sh"
if [ ! -x "$runner" ]; then
  echo "ERROR: runner not executable: $runner" >&2
  exit 2
fi

for event in "$@"; do
  echo "[queue] start ${event} $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  EVENT="$event" bash "$runner"
  echo "[queue] done  ${event} $(date -u +%Y-%m-%dT%H:%M:%SZ)"
done
