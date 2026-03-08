#!/usr/bin/env bash
set -euo pipefail

# Run bubble-model follow-up fits for GRBs that showed negative-k powerlaw fits.
# Uses top-hat/on-axis geometry and syncs shared parameters from powerlaw config.

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
RESOURCES_DIR="${RESOURCES_DIR:-$VEGAS_DIR/jetfit/resources/grbs}"

GRBS="${GRBS:-080413B 140506A 210905A}"
THETA_C="${THETA_C:-1.0}"
THETA_V="${THETA_V:-0.0}"
RUN_TAG="${RUN_TAG:-theta1p0_thesis_full}"

MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_full.toml}"
WORKERS="${WORKERS:-8}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RESUME="${RESUME:-0}"
SKIP_COMPLETED="${SKIP_COMPLETED:-1}"
CONTINUE_ON_ERROR="${CONTINUE_ON_ERROR:-1}"
RUN_MINIMIZER="${RUN_MINIMIZER:-1}"

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
TOPHAT_BUILDER="${TOPHAT_BUILDER:-$VEGAS_DIR/scripts/build_tophat_model_toml.py}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$VEGAS_DIR/scripts/sync_compare_model_tomls.py}"
BUBBLE_TEMPLATE="${BUBBLE_TEMPLATE:-$RUN_PROFILE_DIR/parameters_bubble.toml}"

if [ ! -d "$VEGAS_DIR" ]; then
  echo "ERROR: VegasJetFit directory not found: $VEGAS_DIR" >&2
  exit 2
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -f "$TOPHAT_BUILDER" ]; then
  echo "ERROR: top-hat builder not found: $TOPHAT_BUILDER" >&2
  exit 2
fi
if [ ! -f "$SYNC_SCRIPT" ]; then
  echo "ERROR: sync script not found: $SYNC_SCRIPT" >&2
  exit 2
fi
if [ ! -f "$BUBBLE_TEMPLATE" ]; then
  echo "ERROR: bubble template not found: $BUBBLE_TEMPLATE" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings not found: $MCMC_SETTINGS" >&2
  exit 2
fi

LOG_DIR="$VEGAS_DIR/logs"
mkdir -p "$LOG_DIR"
batch_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
summary_csv="$LOG_DIR/negativek_bubble_${RUN_TAG}_${batch_stamp}.csv"
echo "event,status,elapsed_sec,start_utc,end_utc,note,results_dir" > "$summary_csv"

echo "=================================================="
echo "Negative-k Bubble Follow-up"
echo "GRBs:             $GRBS"
echo "MCMC settings:    $MCMC_SETTINGS"
echo "Workers:          $WORKERS"
echo "Preflight:        $ENABLE_PREFLIGHT (burn=$PREFLIGHT_BURN_LENGTH run=$PREFLIGHT_RUN_LENGTH)"
echo "Top-hat theta_c:  $THETA_C"
echo "Top-hat theta_v:  $THETA_V"
echo "Run tag:          $RUN_TAG"
echo "Keep awake:       $KEEP_AWAKE"
echo "Resume:           $RESUME"
echo "Skip completed:   $SKIP_COMPLETED"
echo "Continue on error:$CONTINUE_ON_ERROR"
echo "Summary CSV:      $summary_csv"
echo "=================================================="
echo

overall_rc=0
for event in $GRBS; do
  start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  start_epoch="$(date +%s)"
  status=""
  note=""
  rc=0

  source_model="$RESOURCES_DIR/$event/parameters.toml"
  top_hat_model="$LOG_DIR/${event}.parameters_tophat_theta${THETA_C}.toml"
  bubble_model="$LOG_DIR/${event}.parameters_bubble_theta${THETA_C}.synced.toml"
  results_dir="$VEGAS_DIR/jetfit/results/${event}_bubble_tophat_${RUN_TAG}"

  if [ ! -f "$source_model" ]; then
    status="missing_model"
    note="missing:$source_model"
    rc=4
  elif [ "$SKIP_COMPLETED" = "1" ] && [ -f "$results_dir/best_fit.json" ] && [ -f "$results_dir/chain.npz" ]; then
    status="skipped_completed"
    note="already_has_best_fit_and_chain"
    rc=0
  else
    echo "--------------------------------------------------"
    echo "Starting bubble fit for $event"
    echo "Source model: $source_model"
    echo "Top-hat model: $top_hat_model"
    echo "Bubble model:  $bubble_model"
    echo "Results:       $results_dir"
    echo "--------------------------------------------------"

    "$PYTHON_BIN" "$TOPHAT_BUILDER" \
      --input "$source_model" \
      --output "$top_hat_model" \
      --theta-c "$THETA_C" \
      --theta-v "$THETA_V"

    "$PYTHON_BIN" "$SYNC_SCRIPT" \
      --powerlaw "$top_hat_model" \
      --bubble "$BUBBLE_TEMPLATE" \
      --output "$bubble_model"

    if ROOT="$ROOT" \
      RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
      EVENT_NAME="$event" \
      MODEL_CHOICE="bubble" \
      MODEL_TOML="$bubble_model" \
      MCMC_SETTINGS="$MCMC_SETTINGS" \
      WORKERS="$WORKERS" \
      ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
      PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
      PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
      KEEP_AWAKE="$KEEP_AWAKE" \
      RESUME="$RESUME" \
      RUN_FOREGROUND=1 \
      RUN_MINIMIZER="$RUN_MINIMIZER" \
      RESULTS_DIR="$results_dir" \
      DRIVE_RUN_LABEL="$(basename "$results_dir")" \
      bash "$VEGAS_DIR/jwk_run_vegas_jet_fit.sh"; then
      status="ok"
      rc=0
    else
      rc=$?
      status="error_$rc"
    fi
  fi

  end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - start_epoch))
  echo "$event,$status,$elapsed,$start_utc,$end_utc,$note,$results_dir" >> "$summary_csv"
  echo "[$event] status=$status elapsed=${elapsed}s end=$end_utc"
  echo

  if [ "$rc" -ne 0 ]; then
    overall_rc="$rc"
    if [ "$CONTINUE_ON_ERROR" != "1" ]; then
      break
    fi
  fi
done

echo "Batch complete. Summary:"
cat "$summary_csv"
echo
echo "Saved summary to: $summary_csv"

exit "$overall_rc"
