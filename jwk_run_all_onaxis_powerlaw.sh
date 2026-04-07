#!/usr/bin/env bash
set -euo pipefail

# Run one shared on-axis top-hat powerlaw configuration across all GRBs
# available in jetfit/resources/grbs.
#
# Defaults:
# - canonical event directory names only: ^[0-9]{6}[A-Z]?$
# - fixed top-hat geometry: theta_c=1.0, theta_v=0.0
# - shared short MCMC profile for all events
# - sequential foreground runs (safe for long unattended execution)
# - resume partial runs, skip already-complete runs

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
RESOURCES_DIR="${RESOURCES_DIR:-$VEGAS_DIR/jetfit/resources/grbs}"

MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_short.toml}"
WORKERS="${WORKERS:-8}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RESUME="${RESUME:-1}"
SKIP_COMPLETED="${SKIP_COMPLETED:-1}"
CONTINUE_ON_ERROR="${CONTINUE_ON_ERROR:-1}"
DRY_RUN="${DRY_RUN:-0}"

THETA_C="${THETA_C:-1.0}"
THETA_V="${THETA_V:-0.0}"
K_LOWER="${K_LOWER:--10.0}"
K_UPPER="${K_UPPER:-3.0}"

TOPHAT_BUILDER="${TOPHAT_BUILDER:-$VEGAS_DIR/scripts/build_tophat_model_toml.py}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
SEED_BEST_FIT_ROOT="${SEED_BEST_FIT_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
USE_DYLAN_SEEDS="${USE_DYLAN_SEEDS:-1}"

# Optional override list, space/comma separated.
GRBS="${GRBS:-}"

if [ ! -d "$VEGAS_DIR" ]; then
  echo "ERROR: VegasJetFit directory not found: $VEGAS_DIR" >&2
  exit 2
fi
if [ ! -d "$RESOURCES_DIR" ]; then
  echo "ERROR: resources directory not found: $RESOURCES_DIR" >&2
  exit 2
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings not found: $MCMC_SETTINGS" >&2
  exit 2
fi
if [ ! -f "$TOPHAT_BUILDER" ]; then
  echo "ERROR: top-hat builder not found: $TOPHAT_BUILDER" >&2
  exit 2
fi

events=()
if [ -n "$GRBS" ]; then
  read -r -a events <<< "$(echo "$GRBS" | tr ',' ' ')"
else
  for d in "$RESOURCES_DIR"/*; do
    [ -d "$d" ] || continue
    ev="$(basename "$d")"
    if [[ "$ev" =~ ^[0-9]{6}[A-Z]?$ ]]; then
      if [ -f "$d/parameters.toml" ] && find "$d" -maxdepth 1 -type f -name '*.csv' | read -r _; then
        events+=("$ev")
      fi
    fi
  done
  if [ "${#events[@]}" -gt 0 ]; then
    sorted_events=()
    while IFS= read -r ev; do
      [ -n "$ev" ] && sorted_events+=("$ev")
    done < <(printf '%s\n' "${events[@]}" | sort)
    events=("${sorted_events[@]}")
  fi
fi

if [ "${#events[@]}" -eq 0 ]; then
  echo "ERROR: no events selected." >&2
  exit 2
fi

theta_label="$(echo "$THETA_C" | tr '.' 'p')"
run_tag="${RUN_TAG:-theta${theta_label}_thesis_short}"
LOG_DIR="$VEGAS_DIR/logs"
mkdir -p "$LOG_DIR"

batch_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
summary_csv="$LOG_DIR/all_onaxis_powerlaw_${run_tag}_${batch_stamp}.csv"
echo "event,status,elapsed_sec,start_utc,end_utc,note,results_dir" > "$summary_csv"

echo "=================================================="
echo "All-GRB On-Axis Powerlaw Runner"
echo "Events:           ${events[*]}"
echo "MCMC settings:    $MCMC_SETTINGS"
echo "Workers:          $WORKERS"
echo "Preflight:        $ENABLE_PREFLIGHT (burn=$PREFLIGHT_BURN_LENGTH run=$PREFLIGHT_RUN_LENGTH)"
echo "Top-hat theta_c:  $THETA_C"
echo "Top-hat theta_v:  $THETA_V"
echo "Top-hat k prior:  [$K_LOWER, $K_UPPER]"
echo "Use Dylan seeds:  $USE_DYLAN_SEEDS"
echo "Seed root:        $SEED_BEST_FIT_ROOT"
echo "Keep awake:       $KEEP_AWAKE"
echo "Resume:           $RESUME"
echo "Skip completed:   $SKIP_COMPLETED"
echo "Continue on error:$CONTINUE_ON_ERROR"
echo "Dry run:          $DRY_RUN"
echo "Run tag:          $run_tag"
echo "Summary CSV:      $summary_csv"
echo "=================================================="
echo

run_one_event() {
  local event="$1"
  local source_model="$RESOURCES_DIR/$event/parameters.toml"
  local top_hat_model="$LOG_DIR/${event}.parameters_tophat_theta${THETA_C}.toml"
  local results_dir="$VEGAS_DIR/jetfit/results/${event}_powerlaw_tophat_${run_tag}"
  local start_utc start_epoch end_utc end_epoch elapsed note status rc
  local seed_best_fit=""
  local candidate=""
  local -a builder_args=()

  note=""
  start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  start_epoch="$(date +%s)"

  if [ ! -f "$source_model" ]; then
    status="missing_model"
    note="missing:$source_model"
    rc=4
  elif [ "$SKIP_COMPLETED" = "1" ] && [ -f "$results_dir/best_fit.json" ] && [ -f "$results_dir/chain.npz" ]; then
    status="skipped_completed"
    rc=0
  else
    if [ "$USE_DYLAN_SEEDS" = "1" ] && [ -d "$SEED_BEST_FIT_ROOT/$event" ]; then
      for candidate in \
        "$SEED_BEST_FIT_ROOT/$event/PL Open OnAxis/best_fit.json" \
        "$SEED_BEST_FIT_ROOT/$event/2000 2000Run/best_fit.json" \
        "$SEED_BEST_FIT_ROOT/$event/2000 2000Run (1)/best_fit.json"; do
        if [ -f "$candidate" ]; then
          seed_best_fit="$candidate"
          break
        fi
      done
    fi

    echo "--------------------------------------------------"
    echo "Starting $event"
    echo "Source model: $source_model"
    echo "Top-hat model: $top_hat_model"
    if [ -n "$seed_best_fit" ]; then
      echo "Seed best-fit: $seed_best_fit"
    fi
    echo "Results: $results_dir"
    echo "Start: $start_utc"
    echo "--------------------------------------------------"

    builder_args=(
      --input "$source_model"
      --output "$top_hat_model"
      --theta-c "$THETA_C"
      --theta-v "$THETA_V"
      --k-lower "$K_LOWER"
      --k-upper "$K_UPPER"
    )
    if [ -n "$seed_best_fit" ]; then
      builder_args+=(--seed-best-fit "$seed_best_fit")
    fi

    if "$PYTHON_BIN" "$TOPHAT_BUILDER" "${builder_args[@]}"; then
      if [ "$DRY_RUN" = "1" ]; then
        status="dry_run"
        note="no_execution"
        rc=0
      else
        if ROOT="$ROOT" \
           RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
           EVENT_NAME="$event" \
           MODEL_CHOICE="powerlaw" \
           MODEL_TOML="$top_hat_model" \
           MCMC_SETTINGS="$MCMC_SETTINGS" \
           WORKERS="$WORKERS" \
           ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
           PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
           PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
           KEEP_AWAKE="$KEEP_AWAKE" \
           RESUME="$RESUME" \
           RUN_FOREGROUND=1 \
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
    else
      rc=$?
      status="error_build_$rc"
      note="build_tophat_failed"
    fi
  fi

  end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - start_epoch))
  echo "$event,$status,$elapsed,$start_utc,$end_utc,$note,$results_dir" >> "$summary_csv"
  echo "[$event] status=$status elapsed=${elapsed}s end=$end_utc"
  echo
  return "${rc:-0}"
}

overall_rc=0
for event in "${events[@]}"; do
  if run_one_event "$event"; then
    :
  else
    rc=$?
    overall_rc="$rc"
    if [ "$CONTINUE_ON_ERROR" != "1" ]; then
      echo "Stopping on first error (event=$event rc=$rc)."
      break
    fi
  fi
done

echo "Run complete. Summary:"
cat "$summary_csv"
echo
echo "Saved summary to: $summary_csv"
exit "$overall_rc"
