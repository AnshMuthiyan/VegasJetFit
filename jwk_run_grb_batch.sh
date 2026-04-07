#!/usr/bin/env bash
set -euo pipefail

# Batch launcher for GRB runs grouped by expected runtime tier.
#
# Defaults:
#   - TIER=quick
#   - MODE=compare   (runs both powerlaw + bubble via jwk_run_compare_models.sh)
#
# Usage examples:
#   bash jwk_run_grb_batch.sh
#   TIER=reasonable bash jwk_run_grb_batch.sh
#   MODE=powerlaw TIER=quick bash jwk_run_grb_batch.sh
#   GRBS="130612A 050525A" bash jwk_run_grb_batch.sh
#   DRY_RUN=1 TIER=quick bash jwk_run_grb_batch.sh

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"

TIER="${TIER:-quick}"               # quick | reasonable | slow | all
MODE="${MODE:-compare}"             # compare | powerlaw | bubble | tophat
GRBS="${GRBS:-}"                    # Optional explicit list (space/comma separated)
DRY_RUN="${DRY_RUN:-0}"             # 1 = print only, do not run
CONTINUE_ON_ERROR="${CONTINUE_ON_ERROR:-1}"

WORKERS="${WORKERS:-8}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings.toml}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RESUME="${RESUME:-0}"
RUN_FOREGROUND="${RUN_FOREGROUND:-1}"
THETA_C="${THETA_C:-1.0}"           # used when MODE=tophat
THETA_V="${THETA_V:-0.0}"           # used when MODE=tophat
TOPHAT_BUILDER="${TOPHAT_BUILDER:-$VEGAS_DIR/scripts/build_tophat_model_toml.py}"

quick_events=(130612A 171010A 050525A 050922C 210905A)
reasonable_events=(090424 090618 111228A 131030A 140506A 161031A 220101A)
slow_events=(080413B 080319B 221009A)

if [ ! -d "$VEGAS_DIR" ]; then
  echo "ERROR: VegasJetFit directory not found: $VEGAS_DIR" >&2
  exit 2
fi

if [ ! -d "$RUN_PROFILE_DIR" ]; then
  echo "ERROR: profile directory not found: $RUN_PROFILE_DIR" >&2
  exit 2
fi

if [ -n "$GRBS" ]; then
  read -r -a events <<< "$(echo "$GRBS" | tr ',' ' ')"
  resolved_tier="custom"
else
  case "$TIER" in
    quick)
      events=("${quick_events[@]}")
      ;;
    reasonable)
      events=("${reasonable_events[@]}")
      ;;
    slow)
      events=("${slow_events[@]}")
      ;;
    all)
      events=("${quick_events[@]}" "${reasonable_events[@]}" "${slow_events[@]}")
      ;;
    *)
      echo "ERROR: TIER must be quick|reasonable|slow|all (got '$TIER')" >&2
      exit 2
      ;;
  esac
  resolved_tier="$TIER"
fi

case "$MODE" in
  compare|powerlaw|bubble|tophat)
    ;;
  *)
    echo "ERROR: MODE must be compare|powerlaw|bubble|tophat (got '$MODE')" >&2
    exit 2
    ;;
esac

if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings not found: $MCMC_SETTINGS" >&2
  exit 2
fi

if [ "$MODE" = "tophat" ] && [ ! -f "$TOPHAT_BUILDER" ]; then
  echo "ERROR: top-hat builder script not found: $TOPHAT_BUILDER" >&2
  exit 2
fi

if [ "${#events[@]}" -eq 0 ]; then
  echo "ERROR: no GRBs selected." >&2
  exit 2
fi

LOG_DIR="$VEGAS_DIR/logs"
mkdir -p "$LOG_DIR"
batch_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
summary_csv="$LOG_DIR/grb_batch_${resolved_tier}_${MODE}_${batch_stamp}.csv"

echo "event,tier,mode,status,elapsed_sec,start_utc,end_utc,note" > "$summary_csv"

echo "=================================================="
echo "GRB batch run"
echo "Tier:             $resolved_tier"
echo "Mode:             $MODE"
echo "Events:           ${events[*]}"
echo "Workers:          $WORKERS"
echo "MCMC settings:    $MCMC_SETTINGS"
echo "Preflight:        $ENABLE_PREFLIGHT (burn=$PREFLIGHT_BURN_LENGTH run=$PREFLIGHT_RUN_LENGTH)"
echo "Keep awake:       $KEEP_AWAKE"
echo "Resume:           $RESUME"
if [ "$MODE" = "tophat" ]; then
  echo "Top-hat theta_c:  $THETA_C"
  echo "Top-hat theta_v:  $THETA_V"
fi
echo "Continue on error:$CONTINUE_ON_ERROR"
echo "Dry run:          $DRY_RUN"
echo "Summary CSV:      $summary_csv"
echo "=================================================="
echo

run_event() {
  local event="$1"
  local obs_dir="$VEGAS_DIR/jetfit/resources/grbs/$event"
  local obs_clean="$obs_dir/${event}clean.csv"
  local obs_plain="$obs_dir/${event}.csv"
  local obs_csv=""
  local model_toml=""
  local source_model="$obs_dir/parameters.toml"
  local start_utc start_epoch end_utc end_epoch elapsed rc note status

  start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  start_epoch="$(date +%s)"
  note=""

  if [ -n "${OBS_CSV:-}" ]; then
    obs_csv="$OBS_CSV"
  elif [ -f "$obs_clean" ]; then
    obs_csv="$obs_clean"
  elif [ -f "$obs_plain" ]; then
    obs_csv="$obs_plain"
  else
    obs_csv="$(find "$obs_dir" -maxdepth 1 -type f -name '*.csv' 2>/dev/null | sort | head -n 1 || true)"
  fi

  if [ ! -f "$obs_csv" ]; then
    status="missing_obs"
    note="missing:$obs_csv"
    echo "[$event] Missing observation file: $obs_csv"
    end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    end_epoch="$(date +%s)"
    elapsed=$((end_epoch - start_epoch))
    echo "$event,$resolved_tier,$MODE,$status,$elapsed,$start_utc,$end_utc,$note" >> "$summary_csv"
    return 3
  fi

  echo "--------------------------------------------------"
  echo "Starting $event ($MODE)"
  echo "Obs: $obs_csv"
  echo "Start: $start_utc"
  if [ "$MODE" = "tophat" ]; then
    model_toml="$LOG_DIR/${event}.parameters_tophat_theta${THETA_C}.toml"
    echo "Base model: $source_model"
    echo "Top-hat model: $model_toml"
  fi
  echo "--------------------------------------------------"

  if [ "$DRY_RUN" = "1" ]; then
    rc=0
    status="dry_run"
    note="no_execution"
  else
    if [ "$MODE" = "compare" ]; then
      if ROOT="$ROOT" \
         RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
         EVENT_NAME="$event" \
         MCMC_SETTINGS="$MCMC_SETTINGS" \
         WORKERS="$WORKERS" \
         ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
         PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
         PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
         KEEP_AWAKE="$KEEP_AWAKE" \
         RESUME="$RESUME" \
         bash "$VEGAS_DIR/jwk_run_compare_models.sh"; then
        rc=0
      else
        rc=$?
      fi
    elif [ "$MODE" = "tophat" ]; then
      if [ ! -f "$source_model" ]; then
        rc=4
        note="missing_model:$source_model"
      else
        if ! "$ROOT/.venv/bin/python" "$TOPHAT_BUILDER" \
          --input "$source_model" \
          --output "$model_toml" \
          --theta-c "$THETA_C" \
          --theta-v "$THETA_V"; then
          rc=$?
        else
          if ROOT="$ROOT" \
             RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
             EVENT_NAME="$event" \
             MODEL_CHOICE="powerlaw" \
             MODEL_TOML="$model_toml" \
             MCMC_SETTINGS="$MCMC_SETTINGS" \
             WORKERS="$WORKERS" \
             ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
             PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
             PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
             KEEP_AWAKE="$KEEP_AWAKE" \
             RESUME="$RESUME" \
             RUN_FOREGROUND="$RUN_FOREGROUND" \
             bash "$VEGAS_DIR/jwk_run_vegas_jet_fit.sh"; then
            rc=0
          else
            rc=$?
          fi
        fi
      fi
    else
      if ROOT="$ROOT" \
         RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
         EVENT_NAME="$event" \
         MODEL_CHOICE="$MODE" \
         MCMC_SETTINGS="$MCMC_SETTINGS" \
         WORKERS="$WORKERS" \
         ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
         PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
         PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
         KEEP_AWAKE="$KEEP_AWAKE" \
         RESUME="$RESUME" \
         RUN_FOREGROUND="$RUN_FOREGROUND" \
         bash "$VEGAS_DIR/jwk_run_vegas_jet_fit.sh"; then
        rc=0
      else
        rc=$?
      fi
    fi

    if [ "$rc" -eq 0 ]; then
      status="ok"
    else
      status="error_$rc"
    fi
  fi

  end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - start_epoch))
  echo "$event,$resolved_tier,$MODE,$status,$elapsed,$start_utc,$end_utc,$note" >> "$summary_csv"

  echo "[$event] status=$status elapsed=${elapsed}s end=$end_utc"
  echo
  return "${rc:-0}"
}

overall_rc=0
for event in "${events[@]}"; do
  if run_event "$event"; then
    :
  else
    rc=$?
    overall_rc="$rc"
    if [ "$CONTINUE_ON_ERROR" != "1" ]; then
      echo "Stopping batch on first error (event=$event, rc=$rc)."
      break
    fi
  fi
done

echo "Batch complete. Summary:"
cat "$summary_csv"
echo
echo "Saved summary to: $summary_csv"

exit "$overall_rc"
