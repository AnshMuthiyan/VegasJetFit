#!/usr/bin/env bash
set -euo pipefail

# Run two full fits sequentially on the SAME dataset:
#   1) powerlawVegasModel (Ansh priors)
#   2) BubbleVegasModel   (Ansh-aligned priors)
#
# This script runs foreground so model-2 starts only after model-1 completes.

ROOT="${ROOT:-$HOME/GRBs}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$ROOT/VegasJetFit/Ansh_Run}"
EVENT_NAME="${EVENT_NAME:-221009A}"

NUM_CPUS="$(sysctl -n hw.ncpu 2>/dev/null || echo 1)"
DEFAULT_WORKERS="${DEFAULT_WORKERS:-8}"
if [ -n "${WORKERS:-}" ]; then
  MCMC_WORKERS="$WORKERS"
elif [ "$NUM_CPUS" -gt "$DEFAULT_WORKERS" ]; then
  MCMC_WORKERS="$DEFAULT_WORKERS"
elif [ "$NUM_CPUS" -gt 1 ]; then
  MCMC_WORKERS="$((NUM_CPUS - 1))"
else
  MCMC_WORKERS=1
fi

MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings.toml}"
OBS_CSV="${OBS_CSV:-$ROOT/VegasJetFit/jetfit/resources/grbs/$EVENT_NAME/${EVENT_NAME}clean.csv}"
POWERLAW_MODEL="${POWERLAW_MODEL:-$RUN_PROFILE_DIR/parameters_powerlaw.toml}"
BUBBLE_MODEL="${BUBBLE_MODEL:-$RUN_PROFILE_DIR/parameters_bubble.toml}"
SYNC_SHARED_PARAMS="${SYNC_SHARED_PARAMS:-1}"

ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
JETFIT_MP_START_METHOD="${JETFIT_MP_START_METHOD:-auto}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RESUME="${RESUME:-0}"

if [ ! -f "$ROOT/VegasJetFit/jwk_run_vegas_jet_fit.sh" ]; then
  echo "ERROR: launcher not found: $ROOT/VegasJetFit/jwk_run_vegas_jet_fit.sh" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings not found: $MCMC_SETTINGS" >&2
  exit 2
fi
if [ ! -f "$OBS_CSV" ]; then
  echo "ERROR: observation CSV not found: $OBS_CSV" >&2
  exit 2
fi
if [ ! -f "$POWERLAW_MODEL" ]; then
  echo "ERROR: powerlaw model TOML not found: $POWERLAW_MODEL" >&2
  exit 2
fi
if [ ! -f "$BUBBLE_MODEL" ]; then
  echo "ERROR: bubble model TOML not found: $BUBBLE_MODEL" >&2
  exit 2
fi

SYNC_SCRIPT="$ROOT/VegasJetFit/scripts/sync_compare_model_tomls.py"
SYNCED_BUBBLE_MODEL="$ROOT/VegasJetFit/logs/${EVENT_NAME}.parameters_bubble.synced.toml"

if [ "$SYNC_SHARED_PARAMS" = "1" ]; then
  if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "ERROR: sync helper not found: $SYNC_SCRIPT" >&2
    exit 2
  fi
  if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "ERROR: python not found: $ROOT/.venv/bin/python" >&2
    exit 2
  fi

  mkdir -p "$ROOT/VegasJetFit/logs"
  "$ROOT/.venv/bin/python" "$SYNC_SCRIPT" \
    --powerlaw "$POWERLAW_MODEL" \
    --bubble "$BUBBLE_MODEL" \
    --output "$SYNCED_BUBBLE_MODEL"
  BUBBLE_MODEL="$SYNCED_BUBBLE_MODEL"
fi

run_one() {
  local model_choice="$1"
  local model_toml="$2"
  local results_dir="$3"

  echo
  echo "=================================================="
  echo "Running model:   $model_choice"
  echo "Event:           $EVENT_NAME"
  echo "Obs:             $OBS_CSV"
  echo "Model TOML:      $model_toml"
  echo "MCMC settings:   $MCMC_SETTINGS"
  echo "Workers:         $MCMC_WORKERS"
  echo "Keep awake:      $KEEP_AWAKE"
  echo "Resume:          $RESUME"
  echo "Results:         $results_dir"
  echo "=================================================="
  echo

  ROOT="$ROOT" \
  RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
  EVENT_NAME="$EVENT_NAME" \
  OBS_CSV="$OBS_CSV" \
  MODEL_CHOICE="$model_choice" \
  MODEL_TOML="$model_toml" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  WORKERS="$MCMC_WORKERS" \
  ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
  PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
  PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
  PREFLIGHT_ONLY=0 \
  RUN_FOREGROUND=1 \
  KEEP_AWAKE="$KEEP_AWAKE" \
  RESUME="$RESUME" \
  RESULTS_DIR="$results_dir" \
  JETFIT_MP_START_METHOD="$JETFIT_MP_START_METHOD" \
  bash "$ROOT/VegasJetFit/jwk_run_vegas_jet_fit.sh"
}

POWERLAW_RESULTS="${POWERLAW_RESULTS:-$ROOT/VegasJetFit/jetfit/results/${EVENT_NAME}_powerlaw_AnshPriors}"
BUBBLE_RESULTS="${BUBBLE_RESULTS:-$ROOT/VegasJetFit/jetfit/results/${EVENT_NAME}_bubble_AnshPriors}"

run_one "powerlaw" "$POWERLAW_MODEL" "$POWERLAW_RESULTS"
run_one "bubble" "$BUBBLE_MODEL" "$BUBBLE_RESULTS"

echo
echo "Both runs finished."
echo "Powerlaw results: $POWERLAW_RESULTS"
echo "Bubble results:   $BUBBLE_RESULTS"
