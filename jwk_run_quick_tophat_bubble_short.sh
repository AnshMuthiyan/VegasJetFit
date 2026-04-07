#!/usr/bin/env bash
set -euo pipefail

# Run Dylan "quick" GRBs with:
#   1) powerlawVegasModel in top-hat mode (theta_c fixed)
#   2) BubbleVegasModel synced to same shared parameters
#
# Defaults:
#   - powerlaw uses thesis-style short MCMC profile
#   - bubble uses a faster profile so wall-time stays in the "few hours" range

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"

# Backward-compatible override: if MCMC_SETTINGS is set, use it for both.
if [ -n "${MCMC_SETTINGS:-}" ]; then
  POWERLAW_MCMC_SETTINGS="${POWERLAW_MCMC_SETTINGS:-$MCMC_SETTINGS}"
  BUBBLE_MCMC_SETTINGS="${BUBBLE_MCMC_SETTINGS:-$MCMC_SETTINGS}"
else
  POWERLAW_MCMC_SETTINGS="${POWERLAW_MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_short.toml}"
  BUBBLE_MCMC_SETTINGS="${BUBBLE_MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_bubble_few_hours.toml}"
fi
WORKERS="${WORKERS:-8}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RESUME="${RESUME:-0}"
CONTINUE_ON_ERROR="${CONTINUE_ON_ERROR:-1}"
DRY_RUN="${DRY_RUN:-0}"

THETA_C="${THETA_C:-1.0}"
THETA_V="${THETA_V:-0.0}"

TOPHAT_BUILDER="${TOPHAT_BUILDER:-$VEGAS_DIR/scripts/build_tophat_model_toml.py}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$VEGAS_DIR/scripts/sync_compare_model_tomls.py}"
BUBBLE_TEMPLATE="${BUBBLE_TEMPLATE:-$RUN_PROFILE_DIR/parameters_bubble.toml}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"

GRBS="${GRBS:-130612A 171010A 050525A 050922C 210905A}"

if [ ! -d "$VEGAS_DIR" ]; then
  echo "ERROR: VegasJetFit directory not found: $VEGAS_DIR" >&2
  exit 2
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: Python not found/executable: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -f "$POWERLAW_MCMC_SETTINGS" ]; then
  echo "ERROR: powerlaw MCMC settings not found: $POWERLAW_MCMC_SETTINGS" >&2
  exit 2
fi
if [ ! -f "$BUBBLE_MCMC_SETTINGS" ]; then
  echo "ERROR: bubble MCMC settings not found: $BUBBLE_MCMC_SETTINGS" >&2
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

THETA_LABEL="$(echo "$THETA_C" | tr '.' 'p')"
RUN_TAG="theta${THETA_LABEL}_thesis_short"

LOG_DIR="$VEGAS_DIR/logs"
mkdir -p "$LOG_DIR"

batch_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
summary_csv="$LOG_DIR/quick_tophat_bubble_${RUN_TAG}_${batch_stamp}.csv"
echo "event,model,status,elapsed_sec,start_utc,end_utc,note" > "$summary_csv"

echo "=================================================="
echo "Quick GRB Top-Hat + Bubble Runner"
echo "GRBs:             $GRBS"
echo "Powerlaw MCMC:    $POWERLAW_MCMC_SETTINGS"
echo "Bubble MCMC:      $BUBBLE_MCMC_SETTINGS"
echo "Workers:          $WORKERS"
echo "Preflight:        $ENABLE_PREFLIGHT (burn=$PREFLIGHT_BURN_LENGTH run=$PREFLIGHT_RUN_LENGTH)"
echo "Top-hat theta_c:  $THETA_C"
echo "Top-hat theta_v:  $THETA_V"
echo "Keep awake:       $KEEP_AWAKE"
echo "Resume:           $RESUME"
echo "Continue on error:$CONTINUE_ON_ERROR"
echo "Dry run:          $DRY_RUN"
echo "Summary CSV:      $summary_csv"
echo "=================================================="
echo

run_one_model() {
  local event="$1"
  local model_choice="$2"
  local model_toml="$3"
  local results_dir="$4"
  local mcmc_file="$5"
  local start_utc start_epoch end_utc end_epoch elapsed status note rc

  start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  start_epoch="$(date +%s)"
  note=""

  echo "[$event][$model_choice] start=$start_utc"
  echo "[$event][$model_choice] model=$model_toml"
  echo "[$event][$model_choice] mcmc=$mcmc_file"
  echo "[$event][$model_choice] results=$results_dir"

  if [ "$DRY_RUN" = "1" ]; then
    rc=0
    status="dry_run"
    note="no_execution"
  else
    if ROOT="$ROOT" \
       RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
       EVENT_NAME="$event" \
       MODEL_CHOICE="$model_choice" \
       MODEL_TOML="$model_toml" \
       MCMC_SETTINGS="$mcmc_file" \
       WORKERS="$WORKERS" \
       ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
       PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
       PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
       KEEP_AWAKE="$KEEP_AWAKE" \
       RESUME="$RESUME" \
       RUN_FOREGROUND=1 \
       RESULTS_DIR="$results_dir" \
       bash "$VEGAS_DIR/jwk_run_vegas_jet_fit.sh"; then
      rc=0
      status="ok"
    else
      rc=$?
      status="error_$rc"
    fi
  fi

  end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - start_epoch))
  echo "$event,$model_choice,$status,$elapsed,$start_utc,$end_utc,$note" >> "$summary_csv"
  echo "[$event][$model_choice] status=$status elapsed=${elapsed}s end=$end_utc"
  echo
  return "${rc:-0}"
}

overall_rc=0
for event in $GRBS; do
  source_model="$VEGAS_DIR/jetfit/resources/grbs/$event/parameters.toml"
  if [ ! -f "$source_model" ]; then
    echo "[$event] ERROR missing source model: $source_model"
    now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "$event,setup,missing_model,0,$now_utc,$now_utc,missing:$source_model" >> "$summary_csv"
    overall_rc=4
    if [ "$CONTINUE_ON_ERROR" != "1" ]; then
      break
    fi
    continue
  fi

  top_hat_model="$LOG_DIR/${event}.parameters_tophat_theta${THETA_C}.toml"
  bubble_model="$LOG_DIR/${event}.parameters_bubble_theta${THETA_C}.synced.toml"

  echo "[$event] building top-hat model config..."
  "$PYTHON_BIN" "$TOPHAT_BUILDER" \
    --input "$source_model" \
    --output "$top_hat_model" \
    --theta-c "$THETA_C" \
    --theta-v "$THETA_V"

  echo "[$event] syncing bubble config to top-hat shared parameters..."
  "$PYTHON_BIN" "$SYNC_SCRIPT" \
    --powerlaw "$top_hat_model" \
    --bubble "$BUBBLE_TEMPLATE" \
    --output "$bubble_model"

  powerlaw_results="$VEGAS_DIR/jetfit/results/${event}_powerlaw_tophat_${RUN_TAG}"
  bubble_results="$VEGAS_DIR/jetfit/results/${event}_bubble_tophat_${RUN_TAG}"

  if run_one_model "$event" "powerlaw" "$top_hat_model" "$powerlaw_results" "$POWERLAW_MCMC_SETTINGS"; then
    :
  else
    rc=$?
    overall_rc="$rc"
    if [ "$CONTINUE_ON_ERROR" != "1" ]; then
      echo "Stopping batch after powerlaw failure for $event (rc=$rc)."
      break
    fi
  fi

  if run_one_model "$event" "bubble" "$bubble_model" "$bubble_results" "$BUBBLE_MCMC_SETTINGS"; then
    :
  else
    rc=$?
    overall_rc="$rc"
    if [ "$CONTINUE_ON_ERROR" != "1" ]; then
      echo "Stopping batch after bubble failure for $event (rc=$rc)."
      break
    fi
  fi
done

echo "Batch complete. Summary:"
cat "$summary_csv"
echo
echo "Saved summary to: $summary_csv"

exit "$overall_rc"
