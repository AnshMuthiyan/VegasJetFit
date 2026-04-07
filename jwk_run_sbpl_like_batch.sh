#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="$ROOT/VegasJetFit"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
LOG_DIR="$VEGAS_DIR/logs"
RESULTS_ROOT="$VEGAS_DIR/jetfit/results"
BUILD_SCRIPT="$VEGAS_DIR/scripts/build_sbpl_like_model_toml.py"
RUN_SCRIPT="$VEGAS_DIR/jwk_run_vegas_jet_fit.sh"
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_short.toml}"
WAIT_TMUX_SESSION="${WAIT_TMUX_SESSION:-}"
WAIT_SECS="${WAIT_SECS:-120}"
WORKERS="${WORKERS:-8}"
RUN_TAG="${RUN_TAG:-smoothbroken_thesis_short}"
SUMMARY_CSV="${SUMMARY_CSV:-$LOG_DIR/${RUN_TAG}_$(date -u +%Y%m%dT%H%M%SZ).csv}"
K1_LOWER="${K1_LOWER:--10.0}"
K1_UPPER="${K1_UPPER:-3.0}"
INITIAL_SIGMA_SCALE="${INITIAL_SIGMA_SCALE:-0.5}"
GRBS="${GRBS:-050525A 080413B 080319B 221009A}"

mkdir -p "$LOG_DIR"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python not found at $PYTHON_BIN" >&2
  exit 2
fi
echo "event,status,elapsed_sec,start_utc,end_utc,note,results_dir" > "$SUMMARY_CSV"

wait_for_session() {
  if [ -z "$WAIT_TMUX_SESSION" ]; then
    return 0
  fi

  echo "Waiting for tmux session to finish: $WAIT_TMUX_SESSION"
  while tmux has-session -t "$WAIT_TMUX_SESSION" 2>/dev/null; do
    echo "  still active at $(date -u +%Y-%m-%dT%H:%M:%SZ); sleeping ${WAIT_SECS}s"
    sleep "$WAIT_SECS"
  done
  echo "Wait target cleared: $WAIT_TMUX_SESSION"
}

contains_event() {
  local wanted="$1"
  local ev
  for ev in "${run_events[@]}"; do
    if [ "$ev" = "$wanted" ]; then
      return 0
    fi
  done
  return 1
}

run_one() {
  local event="$1"
  local model_toml="$2"
  local results_dir="$3"
  local start_utc start_epoch end_utc end_epoch elapsed status note rc

  start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  start_epoch="$(date +%s)"
  status="ok"
  note=""

  echo
  echo "=================================================="
  echo "Starting SBPL-like run: $event"
  echo "Model:   $model_toml"
  echo "Results: $results_dir"
  echo "Start:   $start_utc"
  echo "=================================================="

  if env \
      ROOT="$ROOT" \
      RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
      EVENT_NAME="$event" \
      MODEL_CHOICE="sbpl" \
      MODEL_TOML="$model_toml" \
      RESULTS_DIR="$results_dir" \
      DRIVE_RUN_LABEL="$(basename "$results_dir")" \
      MCMC_SETTINGS="$MCMC_SETTINGS" \
      WORKERS="$WORKERS" \
      KEEP_AWAKE="1" \
      ENABLE_PREFLIGHT="1" \
      PREFLIGHT_BURN_LENGTH="10" \
      PREFLIGHT_RUN_LENGTH="10" \
      PREFLIGHT_ONLY="0" \
      RUN_FOREGROUND="1" \
      RESUME="0" \
      bash "$RUN_SCRIPT"; then
    rc=0
  else
    rc=$?
    status="error_$rc"
  fi

  end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - start_epoch))

  if [ "$rc" -ne 0 ]; then
    note="run_failed"
  fi

  echo "$event,$status,$elapsed,$start_utc,$end_utc,$note,$results_dir" >> "$SUMMARY_CSV"
}

pick_seed_file() {
  local event="$1"
  local sbpl_seed="$RESULTS_ROOT/${event}_smoothbroken_thesis_short/best_fit.json"
  local tophat_seed="$RESULTS_ROOT/${event}_powerlaw_tophat_theta1p0_thesis_short/best_fit.json"
  if [ -f "$sbpl_seed" ]; then
    echo "$sbpl_seed"
    return 0
  fi
  if [ -f "$tophat_seed" ]; then
    echo "$tophat_seed"
    return 0
  fi
  echo ""
}

cd "$VEGAS_DIR"
read -r -a run_events <<< "$(echo "$GRBS" | tr ',' ' ')"
if [ "${#run_events[@]}" -eq 0 ]; then
  echo "ERROR: GRBS list is empty." >&2
  exit 2
fi
echo "SBPL events: ${run_events[*]}"

if contains_event "050525A"; then
  seed_050525A="$(pick_seed_file "050525A")"
  if [ -n "$seed_050525A" ]; then
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/050525A/parameters.toml" \
      --seed-best-fit "$seed_050525A" \
      --output "$LOG_DIR/050525A.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 1.0 \
      --rt-initial 17.0
  else
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/050525A/parameters.toml" \
      --output "$LOG_DIR/050525A.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 1.0 \
      --rt-initial 17.0
  fi
fi

if contains_event "080413B"; then
  seed_080413B="$(pick_seed_file "080413B")"
  if [ -n "$seed_080413B" ]; then
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/080413B/parameters.toml" \
      --seed-best-fit "$seed_080413B" \
      --output "$LOG_DIR/080413B.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 0.5 \
      --rt-initial 17.2
  else
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/080413B/parameters.toml" \
      --output "$LOG_DIR/080413B.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 0.5 \
      --rt-initial 17.2
  fi
fi

if contains_event "080319B"; then
  seed_080319B="$(pick_seed_file "080319B")"
  if [ -n "$seed_080319B" ]; then
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/080319B/parameters.toml" \
      --seed-best-fit "$seed_080319B" \
      --output "$LOG_DIR/080319B.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 0.5 \
      --rt-initial 17.5
  else
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/080319B/parameters.toml" \
      --output "$LOG_DIR/080319B.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 0.5 \
      --rt-initial 17.5
  fi
fi

if contains_event "221009A"; then
  seed_221009A="$(pick_seed_file "221009A")"
  if [ -n "$seed_221009A" ]; then
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/221009A/parameters.toml" \
      --seed-best-fit "$seed_221009A" \
      --output "$LOG_DIR/221009A.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 1.0 \
      --rt-initial 17.5
  else
    "$PYTHON_BIN" "$BUILD_SCRIPT" \
      --source "$VEGAS_DIR/jetfit/resources/grbs/221009A/parameters.toml" \
      --output "$LOG_DIR/221009A.parameters_sbpl_like.toml" \
      --k1-lower "$K1_LOWER" \
      --k1-upper "$K1_UPPER" \
      --initial-sigma-scale "$INITIAL_SIGMA_SCALE" \
      --k2-initial 1.0 \
      --rt-initial 17.5
  fi
fi

wait_for_session

if contains_event "050525A"; then
  run_one \
    "050525A" \
    "$LOG_DIR/050525A.parameters_sbpl_like.toml" \
    "$RESULTS_ROOT/050525A_${RUN_TAG}"
fi

if contains_event "080413B"; then
  run_one \
    "080413B" \
    "$LOG_DIR/080413B.parameters_sbpl_like.toml" \
    "$RESULTS_ROOT/080413B_${RUN_TAG}"
fi

if contains_event "080319B"; then
  run_one \
    "080319B" \
    "$LOG_DIR/080319B.parameters_sbpl_like.toml" \
    "$RESULTS_ROOT/080319B_${RUN_TAG}"
fi

if contains_event "221009A"; then
  run_one \
    "221009A" \
    "$LOG_DIR/221009A.parameters_sbpl_like.toml" \
    "$RESULTS_ROOT/221009A_${RUN_TAG}"
fi

echo
echo "SBPL-like batch complete."
echo "Summary: $SUMMARY_CSV"
