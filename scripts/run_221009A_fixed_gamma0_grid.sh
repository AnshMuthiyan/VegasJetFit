#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUNNER="${RUNNER:-$VEGAS_DIR/jwk_run_vegas_jet_fit.sh}"
CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/thesis_reproduction_configs/221009A_gamma0_grid_top_hat}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_gamma0grid_600x600.toml}"
RUN_TAG="${RUN_TAG:-gamma0grid_tophat_dylanspec_600x600_v1}"
WORKERS="${WORKERS:-8}"
RESUME="${RESUME:-0}"
MCMC_OBS_CSV="${MCMC_OBS_CSV:-$VEGAS_DIR/jetfit/resources/grbs/221009A/221009Aclean.csv}"
MINIMIZE_OBS_CSV="${MINIMIZE_OBS_CSV:-$VEGAS_DIR/jetfit/resources/grbs/221009A/221009A.csv}"

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 GAMMA0 [GAMMA0 ...]" >&2
  exit 2
fi

for gamma in "$@"; do
  model_toml="$CONFIG_DIR/221009A_g${gamma}.toml"
  if [ ! -f "$model_toml" ]; then
    echo "Missing config: $model_toml" >&2
    exit 2
  fi

  run_label="221009A_g${gamma}_${RUN_TAG}"
  echo "=== Running ${run_label} ==="

  ROOT="$ROOT" \
  EVENT_NAME="221009A" \
  MODEL_CHOICE="powerlaw" \
  MODEL_TOML="$model_toml" \
  OBS_CSV="$MCMC_OBS_CSV" \
  MINIMIZE_OBS_CSV="$MINIMIZE_OBS_CSV" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  WORKERS="$WORKERS" \
  ENABLE_PREFLIGHT="0" \
  KEEP_AWAKE="1" \
  RUN_FOREGROUND="1" \
  RESUME="$RESUME" \
  RUN_MINIMIZER="1" \
  MINIMIZE_MODE="walkers" \
  MINIMIZE_MAX_WALKERS="8" \
  MINIMIZE_MINIMIZER="minimize" \
  MINIMIZE_SCIPY_METHOD="Powell" \
  MINIMIZE_FALLBACK_SCIPY_METHOD="Nelder-Mead" \
  DRIVE_SYNC_ENABLE="0" \
  RESULTS_DIR="$VEGAS_DIR/jetfit/results/${run_label}" \
  LOG_BASENAME="${run_label}" \
  bash "$RUNNER"
done
