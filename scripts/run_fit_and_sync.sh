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
RUN_POSTFIT_PRODUCTS="1"
SKIP_MCMC_PLOTS="0"
MINIMIZE_MODE="walkers"
MINIMIZE_MAX_WALKERS="0"
MINIMIZE_PARALLEL_WORKERS="1"
MINIMIZE_MINIMIZER="minimize"
MINIMIZE_SCIPY_METHOD="Powell"
MINIMIZE_FALLBACK_SCIPY_METHOD="Nelder-Mead"
MINIMIZE_OUTPUT=""
MINIMIZE_OBS=""
MINIMIZE_PARAMS=""
MINIMIZE_STRICT="0"
MINIMIZE_SCRIPT=""
DRIVE_SYNC_ENABLE="1"
DRIVE_ROOT=""
DRIVE_OWNER=""
DRIVE_RUN_LABEL=""
SYNC_SCRIPT=""
POSTFIT_PRODUCTS_SCRIPT=""
CORE_POSTFIT_VALIDATOR=""

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
    --run-postfit-products) RUN_POSTFIT_PRODUCTS="${2:-}"; shift 2 ;;
    --skip-mcmc-plots) SKIP_MCMC_PLOTS="${2:-}"; shift 2 ;;
    --minimize-mode) MINIMIZE_MODE="${2:-}"; shift 2 ;;
    --minimize-max-walkers) MINIMIZE_MAX_WALKERS="${2:-}"; shift 2 ;;
    --minimize-parallel-workers) MINIMIZE_PARALLEL_WORKERS="${2:-}"; shift 2 ;;
    --minimize-minimizer) MINIMIZE_MINIMIZER="${2:-}"; shift 2 ;;
    --minimize-scipy-method) MINIMIZE_SCIPY_METHOD="${2:-}"; shift 2 ;;
    --minimize-fallback-scipy-method) MINIMIZE_FALLBACK_SCIPY_METHOD="${2:-}"; shift 2 ;;
    --minimize-output) MINIMIZE_OUTPUT="${2:-}"; shift 2 ;;
    --minimize-obs) MINIMIZE_OBS="${2:-}"; shift 2 ;;
    --minimize-params) MINIMIZE_PARAMS="${2:-}"; shift 2 ;;
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

# Ensure helper scripts executed by path (e.g. scripts/minimize.py) can import
# the local `jetfit` package regardless of how Python initializes sys.path.
export PYTHONPATH="$ROOT/VegasJetFit${PYTHONPATH:+:$PYTHONPATH}"
POSTFIT_PRODUCTS_SCRIPT="$ROOT/VegasJetFit/scripts/generate_postfit_products.py"
CORE_POSTFIT_VALIDATOR="$ROOT/VegasJetFit/scripts/validate_core_postfit_products.py"

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
if [ "$SKIP_MCMC_PLOTS" = "1" ]; then
  cmd+=(--skip-plots)
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
    --scipy-method "$MINIMIZE_SCIPY_METHOD"
    --fallback-scipy-method "$MINIMIZE_FALLBACK_SCIPY_METHOD"
    --parallel-workers "$MINIMIZE_PARALLEL_WORKERS"
  )
  if [ "$MINIMIZE_MAX_WALKERS" != "0" ]; then
    min_cmd+=( --max-walkers "$MINIMIZE_MAX_WALKERS" )
  fi
  if [ -n "$MINIMIZE_OUTPUT" ]; then
    min_cmd+=( --output "$MINIMIZE_OUTPUT" )
  fi
  if [ -n "$MINIMIZE_OBS" ]; then
    min_cmd+=( --obs "$MINIMIZE_OBS" )
  fi
  if [ -n "$MINIMIZE_PARAMS" ]; then
    min_cmd+=( --params "$MINIMIZE_PARAMS" )
  fi

  {
    echo "[run_fit_and_sync] minimizer_start_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "[run_fit_and_sync] minimizer_mode=$MINIMIZE_MODE backend=$MINIMIZE_MINIMIZER method=$MINIMIZE_SCIPY_METHOD fallback=$MINIMIZE_FALLBACK_SCIPY_METHOD max_walkers=$MINIMIZE_MAX_WALKERS parallel_workers=$MINIMIZE_PARALLEL_WORKERS minimize_obs=${MINIMIZE_OBS:-auto} minimize_params=${MINIMIZE_PARAMS:-auto}"
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

if [ "$status" -eq 0 ] && [ "$RUN_POSTFIT_PRODUCTS" = "1" ] && [ -f "$POSTFIT_PRODUCTS_SCRIPT" ]; then
  echo "[run_fit_and_sync] postfit_products_start_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$LOG_FILE"
  if "$PYTHON_BIN" "$POSTFIT_PRODUCTS_SCRIPT" --results "$RESULTS" --event "$EVENT" >> "$LOG_FILE" 2>&1; then
    if "$PYTHON_BIN" "$CORE_POSTFIT_VALIDATOR" --results "$RESULTS" >> "$LOG_FILE" 2>&1; then
      echo "[run_fit_and_sync] postfit_products_done status=0 core_validation=passed" >> "$LOG_FILE"
    else
      postfit_status=$?
      status="$postfit_status"
      echo "[run_fit_and_sync] core_postfit_validation_failed status=$postfit_status" >> "$LOG_FILE"
    fi
  else
    postfit_status=$?
    status="$postfit_status"
    echo "[run_fit_and_sync] postfit_products_failed status=$postfit_status" >> "$LOG_FILE"
  fi
elif [ "$status" -eq 0 ] && [ "$RUN_POSTFIT_PRODUCTS" != "1" ]; then
  echo "[run_fit_and_sync] postfit_products_skipped RUN_POSTFIT_PRODUCTS=$RUN_POSTFIT_PRODUCTS" >> "$LOG_FILE"
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
