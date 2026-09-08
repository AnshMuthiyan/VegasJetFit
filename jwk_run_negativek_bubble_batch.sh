#!/usr/bin/env bash
set -euo pipefail

# Run bubble-model follow-up fits for GRBs that showed negative-k powerlaw fits.
# Uses the current Dylan-smoothed top-hat control configs for shared parameters
# and seeds rt just inside the earliest sampled radius of the control solution.

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
RESOURCES_DIR="${RESOURCES_DIR:-$VEGAS_DIR/jetfit/resources/grbs}"

GRBS="${GRBS:-080413B 140506A 210905A}"
THETA_C="${THETA_C:-1.0}"
THETA_V="${THETA_V:-0.0}"
RUN_TAG="${RUN_TAG:-theta1p0_bubble_dylanspec_physrt_v1}"

MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_dylanspec_2000x2000.toml}"
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
BUBBLE_BUILDER="${BUBBLE_BUILDER:-$VEGAS_DIR/scripts/build_bubble_dylan_toml.py}"
BUBBLE_TEMPLATE="${BUBBLE_TEMPLATE:-$RUN_PROFILE_DIR/parameters_bubble.toml}"
CONTROL_CONFIG_DIR="${CONTROL_CONFIG_DIR:-$VEGAS_DIR/thesis_reproduction_configs_dylanphyspriors_init5pct_active}"
CONTROL_RESULTS_TAG="${CONTROL_RESULTS_TAG:-theta1p0_thesis_reproduction_dylanphyspriors_init5pct_2000x2000_v1}"
BUBBLE_SEED_RUN_TAG="${BUBBLE_SEED_RUN_TAG:-theta1p0_thesis_full_shellmass_v1}"
RT_SEED_FACTOR="${RT_SEED_FACTOR:-0.9}"
RT_SIGMA_SCALE="${RT_SIGMA_SCALE:-0.05}"
BUBBLE_MODEL_NAME="${BUBBLE_MODEL_NAME:-BubbleVegasDylanSpectrumModel}"

if [ ! -d "$VEGAS_DIR" ]; then
  echo "ERROR: VegasJetFit directory not found: $VEGAS_DIR" >&2
  exit 2
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -f "$BUBBLE_BUILDER" ]; then
  echo "ERROR: bubble Dylan builder not found: $BUBBLE_BUILDER" >&2
  exit 2
fi
if [ ! -d "$CONTROL_CONFIG_DIR" ]; then
  echo "ERROR: control config directory not found: $CONTROL_CONFIG_DIR" >&2
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
echo "Control configs:  $CONTROL_CONFIG_DIR"
echo "Control run tag:  $CONTROL_RESULTS_TAG"
echo "Bubble seed tag:  $BUBBLE_SEED_RUN_TAG"
echo "rt seed factor:   $RT_SEED_FACTOR"
echo "rt sigma scale:   $RT_SIGMA_SCALE"
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
  control_model="$CONTROL_CONFIG_DIR/$event.toml"
  bubble_model="$LOG_DIR/${event}.parameters_bubble_theta${THETA_C}.synced.toml"
  results_dir="$VEGAS_DIR/jetfit/results/${event}_bubble_tophat_${RUN_TAG}"
  control_seed="$VEGAS_DIR/jetfit/results/${event}_thesis_reproduction_${CONTROL_RESULTS_TAG}/minimized/minimized.json"
  bubble_seed="$VEGAS_DIR/jetfit/results/${event}_bubble_tophat_${BUBBLE_SEED_RUN_TAG}/minimized/minimized.json"
  obs_csv="$RESOURCES_DIR/$event/${event}clean.csv"
  if [ ! -f "$obs_csv" ]; then
    obs_csv="$RESOURCES_DIR/$event/${event}.csv"
  fi

  if [ ! -f "$source_model" ]; then
    status="missing_model"
    note="missing:$source_model"
    rc=4
  elif [ ! -f "$control_model" ]; then
    status="missing_control"
    note="missing:$control_model"
    rc=4
  elif [ "$SKIP_COMPLETED" = "1" ] && [ -f "$results_dir/best_fit.json" ] && [ -f "$results_dir/chain.npz" ]; then
    status="skipped_completed"
    note="already_has_best_fit_and_chain"
    rc=0
  else
    echo "--------------------------------------------------"
    echo "Starting bubble fit for $event"
    echo "Source model: $source_model"
    echo "Control model: $control_model"
    echo "Obs CSV:       $obs_csv"
    echo "Bubble model:  $bubble_model"
    echo "Results:       $results_dir"
    echo "--------------------------------------------------"

    build_cmd=(
      "$PYTHON_BIN" "$BUBBLE_BUILDER"
      --powerlaw "$control_model"
      --bubble-template "$BUBBLE_TEMPLATE"
      --output "$bubble_model"
      --obs "$obs_csv"
      --model-name "$BUBBLE_MODEL_NAME"
      --rt-factor "$RT_SEED_FACTOR"
      --rt-sigma-scale "$RT_SIGMA_SCALE"
    )
    if [ -f "$control_seed" ]; then
      build_cmd+=(--seed-best-fit "$control_seed")
    fi
    if [ -f "$bubble_seed" ]; then
      build_cmd+=(--bubble-seed "$bubble_seed")
    fi
    "${build_cmd[@]}"

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
