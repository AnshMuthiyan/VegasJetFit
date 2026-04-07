#!/usr/bin/env bash
set -euo pipefail

ROOT=""
EVENT=""
OBS=""
MODEL=""
RESULTS=""
MCMC=""
WORKERS=""
START_METHOD=""
PYTHON_BIN=""
LOG_FILE=""
RESUME="0"
KEEP_AWAKE="1"
RUN_MINIMIZER="1"
MINIMIZE_MODE="walkers"
MINIMIZE_MAX_WALKERS="0"
MINIMIZE_MINIMIZER="minimize"
MINIMIZE_OUTPUT=""
MINIMIZE_STRICT="0"
MINIMIZE_SCRIPT=""
DRIVE_SYNC_ENABLE="1"
DRIVE_ROOT=""
DRIVE_OWNER=""
DRIVE_RUN_LABEL=""
SYNC_SCRIPT=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:-}"; shift 2 ;;
    --event) EVENT="${2:-}"; shift 2 ;;
    --obs) OBS="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --results) RESULTS="${2:-}"; shift 2 ;;
    --mcmc) MCMC="${2:-}"; shift 2 ;;
    --workers) WORKERS="${2:-}"; shift 2 ;;
    --start-method) START_METHOD="${2:-}"; shift 2 ;;
    --python-bin) PYTHON_BIN="${2:-}"; shift 2 ;;
    --log-file) LOG_FILE="${2:-}"; shift 2 ;;
    --resume) RESUME="${2:-}"; shift 2 ;;
    --keep-awake) KEEP_AWAKE="${2:-}"; shift 2 ;;
    --run-minimizer) RUN_MINIMIZER="${2:-}"; shift 2 ;;
    --minimize-mode) MINIMIZE_MODE="${2:-}"; shift 2 ;;
    --minimize-max-walkers) MINIMIZE_MAX_WALKERS="${2:-}"; shift 2 ;;
    --minimize-minimizer) MINIMIZE_MINIMIZER="${2:-}"; shift 2 ;;
    --minimize-output) MINIMIZE_OUTPUT="${2:-}"; shift 2 ;;
    --minimize-strict) MINIMIZE_STRICT="${2:-}"; shift 2 ;;
    --minimize-script) MINIMIZE_SCRIPT="${2:-}"; shift 2 ;;
    --drive-sync-enable) DRIVE_SYNC_ENABLE="${2:-}"; shift 2 ;;
    --drive-root) DRIVE_ROOT="${2:-}"; shift 2 ;;
    --drive-owner) DRIVE_OWNER="${2:-}"; shift 2 ;;
    --drive-run-label) DRIVE_RUN_LABEL="${2:-}"; shift 2 ;;
    --sync-script) SYNC_SCRIPT="${2:-}"; shift 2 ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

for req in ROOT EVENT OBS MODEL RESULTS MCMC WORKERS START_METHOD PYTHON_BIN LOG_FILE; do
  if [ -z "${!req}" ]; then
    echo "ERROR: missing required argument ($req)." >&2
    exit 2
  fi
done

cd "$ROOT/VegasJetFit"

{
  echo "[run_fit_and_sync] start_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[run_fit_and_sync] event=$EVENT results=$RESULTS workers=$WORKERS keep_awake=$KEEP_AWAKE resume=$RESUME"
} >> "$LOG_FILE"

cmd=(/usr/bin/time -p "$PYTHON_BIN" -u -m jetfit.run
  --event "$EVENT"
  --obs "$OBS"
  --model "$MODEL"
  --results "$RESULTS"
  --mcmc "$MCMC"
  --workers "$WORKERS"
  --start-method "$START_METHOD")

if [ "$RESUME" = "1" ]; then
  cmd+=(--resume)
fi

if [ "$KEEP_AWAKE" = "1" ] && command -v caffeinate >/dev/null 2>&1; then
  if caffeinate -is "${cmd[@]}" > "$LOG_FILE" 2>&1; then
    status=0
  else
    status=$?
  fi
else
  if "${cmd[@]}" > "$LOG_FILE" 2>&1; then
    status=0
  else
    status=$?
  fi
fi

if [ "$status" -eq 0 ] && [ "$RUN_MINIMIZER" = "1" ]; then
  min_cmd=( "$PYTHON_BIN" "$MINIMIZE_SCRIPT"
    --results "$RESULTS"
    --mode "$MINIMIZE_MODE"
    --minimizer "$MINIMIZE_MINIMIZER"
  )
  if [ "$MINIMIZE_MAX_WALKERS" != "0" ]; then
    min_cmd+=( --max-walkers "$MINIMIZE_MAX_WALKERS" )
  fi
  if [ -n "$MINIMIZE_OUTPUT" ]; then
    min_cmd+=( --output "$MINIMIZE_OUTPUT" )
  fi

  {
    echo "[run_fit_and_sync] minimizer_start_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "[run_fit_and_sync] minimizer_mode=$MINIMIZE_MODE minimizer=$MINIMIZE_MINIMIZER max_walkers=$MINIMIZE_MAX_WALKERS"
  } >> "$LOG_FILE"

  if [ ! -f "$MINIMIZE_SCRIPT" ]; then
    min_status=2
    echo "[run_fit_and_sync] minimizer_missing_script=$MINIMIZE_SCRIPT" >> "$LOG_FILE"
  elif [ "$KEEP_AWAKE" = "1" ] && command -v caffeinate >/dev/null 2>&1; then
    if caffeinate -is "${min_cmd[@]}" >> "$LOG_FILE" 2>&1; then
      min_status=0
    else
      min_status=$?
    fi
  else
    if "${min_cmd[@]}" >> "$LOG_FILE" 2>&1; then
      min_status=0
    else
      min_status=$?
    fi
  fi

  if [ "$min_status" -ne 0 ]; then
    echo "[run_fit_and_sync] minimizer_failed status=$min_status" >> "$LOG_FILE"
    if [ "$MINIMIZE_STRICT" = "1" ]; then
      status="$min_status"
    fi
  else
    echo "[run_fit_and_sync] minimizer_done status=0" >> "$LOG_FILE"
  fi
fi

if [ "$status" -eq 0 ] && [ "$DRIVE_SYNC_ENABLE" = "1" ] && [ -n "$SYNC_SCRIPT" ] && [ -x "$SYNC_SCRIPT" ] && [ -d "$DRIVE_ROOT" ]; then
  run_label="$DRIVE_RUN_LABEL"
  if [ -z "$run_label" ]; then
    run_label="$(basename "$RESULTS")"
  fi
  "$SYNC_SCRIPT" \
    --results-dir "$RESULTS" \
    --event "$EVENT" \
    --drive-root "$DRIVE_ROOT" \
    --owner-subdir "$DRIVE_OWNER" \
    --run-label "$run_label" \
    --log-file "$LOG_FILE" \
    --mcmc-file "$MCMC" \
    --model-file "$MODEL" \
    --obs-file "$OBS" >> "$LOG_FILE" 2>&1 || true
fi

if [ "$status" -ne 0 ]; then
  echo "[run_fit_and_sync] fit failed (status=$status)." >> "$LOG_FILE"
fi

exit "$status"
