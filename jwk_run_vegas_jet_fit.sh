#!/usr/bin/env bash

# If executed: behave strictly.
# If sourced: do NOT change the caller's shell options.
_is_sourced=0
if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "${0}" ]; then
  _is_sourced=1
fi
if [ "$_is_sourced" -eq 0 ]; then
  set -euo pipefail
fi

# Enable bash tracing if requested (safe even when sourced)
if [ "${DEBUG:-0}" = "1" ]; then
  set -x
fi

# ==== RUN VEGASJETFIT ====
export ROOT="${ROOT:-$HOME/GRBs}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$ROOT/VegasJetFit/Ansh_Run}"
EVENT_NAME="${EVENT_NAME:-221009A}"
MODEL_CHOICE="${MODEL_CHOICE:-powerlaw}"   # powerlaw | bubble | fireball

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
MP_START_METHOD="${JETFIT_MP_START_METHOD:-auto}"
POOL_EXECUTOR="${JETFIT_POOL_EXECUTOR:-auto}"
if [ "$POOL_EXECUTOR" = "auto" ]; then
  if [ "$(uname -s)" = "Darwin" ]; then
    POOL_EXECUTOR="thread"
  else
    POOL_EXECUTOR="process"
  fi
fi
export JETFIT_POOL_EXECUTOR="$POOL_EXECUTOR"
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings.toml}"
MODEL_TOML="${MODEL_TOML:-}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
PREFLIGHT_ONLY="${PREFLIGHT_ONLY:-0}"
RUN_FOREGROUND="${RUN_FOREGROUND:-0}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RESUME="${RESUME:-0}"
RUN_MINIMIZER="${RUN_MINIMIZER:-1}"
MINIMIZE_MODE="${MINIMIZE_MODE:-walkers}"
MINIMIZE_MAX_WALKERS="${MINIMIZE_MAX_WALKERS:-0}"
MINIMIZE_MINIMIZER="${MINIMIZE_MINIMIZER:-minimize}"
MINIMIZE_OUTPUT_DIR="${MINIMIZE_OUTPUT_DIR:-}"
MINIMIZE_STRICT="${MINIMIZE_STRICT:-0}"
DRIVE_SYNC_ENABLE="${DRIVE_SYNC_ENABLE:-1}"
DRIVE_RESULTS_ROOT="${DRIVE_RESULTS_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
DRIVE_OWNER_SUBDIR="${DRIVE_OWNER_SUBDIR:-jkeohane}"
DRIVE_RUN_LABEL="${DRIVE_RUN_LABEL:-}"

# Ensure we are in the repo so "python -m jetfit.run" can import "jetfit"
export PYTHONPATH="$ROOT/VegasJetFit:${PYTHONPATH:-}"

# ---- sanity checks ----
if [ ! -d "$ROOT" ]; then
  echo "ERROR: ROOT does not exist: $ROOT" >&2
  return 2 2>/dev/null || exit 2
fi
if [ ! -d "$ROOT/VegasJetFit" ]; then
  echo "ERROR: VegasJetFit repo not found at: $ROOT/VegasJetFit" >&2
  return 2 2>/dev/null || exit 2
fi
if [ ! -d "$RUN_PROFILE_DIR" ]; then
  echo "ERROR: profile directory not found: $RUN_PROFILE_DIR" >&2
  return 2 2>/dev/null || exit 2
fi
if [ ! -f "$ROOT/.venv/bin/activate" ]; then
  echo "ERROR: venv activate script not found: $ROOT/.venv/bin/activate" >&2
  return 2 2>/dev/null || exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings file not found: $MCMC_SETTINGS" >&2
  return 2 2>/dev/null || exit 2
fi

# Activate the venv that you rebuilt
source "$ROOT/.venv/bin/activate"
PYTHON_BIN="$(command -v python || true)"
if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: could not resolve executable python in active environment." >&2
  return 2 2>/dev/null || exit 2
fi

# Keep matplotlib/arviz caches in repo-writable paths.
export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT/VegasJetFit/.cache/matplotlib}"
export ARVIZ_DATA="${ARVIZ_DATA:-$ROOT/VegasJetFit/.cache/arviz}"
JETFIT_HOME_DIR="${JETFIT_HOME_DIR:-$ROOT/VegasJetFit/.cache/home}"
export MPLBACKEND="${MPLBACKEND:-Agg}"
mkdir -p "$MPLCONFIGDIR" "$ARVIZ_DATA" "$JETFIT_HOME_DIR"

# ArviZ (current version) writes daily-warning stamps under Path.home()/arviz_data.
# Point HOME to a writable cache root for robust batch/background runs.
export HOME="$JETFIT_HOME_DIR"

# macOS sleep prevention guard for long runs.
CAFFEINATE_CMD=()
if [ "$KEEP_AWAKE" = "1" ]; then
  if command -v caffeinate >/dev/null 2>&1; then
    # Keep system awake for compute while allowing display sleep.
    CAFFEINATE_CMD=(caffeinate -is)
  else
    echo "WARNING: KEEP_AWAKE=1 but 'caffeinate' was not found; continuing without sleep guard."
  fi
fi

run_with_sleep_guard() {
  if [ "${#CAFFEINATE_CMD[@]}" -gt 0 ]; then
    "${CAFFEINATE_CMD[@]}" "$@"
  else
    "$@"
  fi
}

echo "ROOT: $ROOT"
echo "Profile dir:    $RUN_PROFILE_DIR"
echo "PWD:  $(pwd)"
echo "PYTHONPATH: $PYTHONPATH"
echo "MPLCONFIGDIR:   $MPLCONFIGDIR"
echo "ARVIZ_DATA:     $ARVIZ_DATA"
echo "MPLBACKEND:     $MPLBACKEND"
echo "HOME:           $HOME"
echo "CPUs available: $NUM_CPUS"
echo "Default workers:$DEFAULT_WORKERS"
echo "MCMC workers:   $MCMC_WORKERS"
echo "Model choice:   $MODEL_CHOICE"
echo "MP start method:$MP_START_METHOD"
echo "Pool executor:  $JETFIT_POOL_EXECUTOR"
echo "MCMC settings:  $MCMC_SETTINGS"
echo "Preflight:      $ENABLE_PREFLIGHT (burn=$PREFLIGHT_BURN_LENGTH run=$PREFLIGHT_RUN_LENGTH)"
echo "Preflight only: $PREFLIGHT_ONLY"
echo "Run foreground: $RUN_FOREGROUND"
echo "Keep awake:     $KEEP_AWAKE"
echo "Resume:         $RESUME"
echo "Run minimizer:  $RUN_MINIMIZER"
echo "Min mode:       $MINIMIZE_MODE"
echo "Min max walkers:$MINIMIZE_MAX_WALKERS"
echo "Min optimizer:  $MINIMIZE_MINIMIZER"
echo "Min strict:     $MINIMIZE_STRICT"
echo "Drive sync:     $DRIVE_SYNC_ENABLE"
echo "Drive root:     $DRIVE_RESULTS_ROOT"
echo "Drive owner:    $DRIVE_OWNER_SUBDIR"
if [ "${#CAFFEINATE_CMD[@]}" -gt 0 ]; then
  echo "Sleep guard:    ${CAFFEINATE_CMD[*]}"
else
  echo "Sleep guard:    disabled"
fi
echo "Python: $PYTHON_BIN"
python -V
python -m pip -V

# Print key versions (do not fail script if one import is missing)
python - <<'PY'
import importlib, importlib.metadata as m
def show(mod):
    try:
        x = importlib.import_module(mod)
        v = getattr(x, "__version__", None)
        if v is None:
            try:
                v = m.version(mod.replace("_","-"))
            except Exception:
                v = "unknown"
        print(f"{mod}: {v}")
    except Exception as e:
        print(f"{mod}: NOT IMPORTABLE ({e})")
for mod in ["numpy","numba","llvmlite","astropy","VegasAfterglow"]:
    show(mod)
PY

JETFIT_PATH="$ROOT/VegasJetFit/jetfit/run.py"   # kept for familiarity
LOG_DIR="$ROOT/VegasJetFit/logs"
mkdir -p "$LOG_DIR"

event1="$(basename "$EVENT_NAME")"

if [ -z "$MODEL_TOML" ]; then
  case "$MODEL_CHOICE" in
    powerlaw)
      MODEL_TOML="$ROOT/VegasJetFit/jetfit/resources/grbs/$event1/parameters.toml"
      ;;
    bubble)
      MODEL_TOML="$RUN_PROFILE_DIR/parameters_bubble.toml"
      ;;
    fireball)
      MODEL_TOML="$RUN_PROFILE_DIR/parameters.toml"
      ;;
    *)
      echo "ERROR: MODEL_CHOICE must be one of: powerlaw, bubble, fireball. Got: $MODEL_CHOICE" >&2
      return 2 2>/dev/null || exit 2
      ;;
  esac
fi

if [ ! -f "$MODEL_TOML" ]; then
  echo "ERROR: model TOML file not found: $MODEL_TOML" >&2
  return 2 2>/dev/null || exit 2
fi

model_tag="$MODEL_CHOICE"
if [ -n "${OBS_CSV:-}" ]; then
  obs1="$OBS_CSV"
else
  obs_dir="$ROOT/VegasJetFit/jetfit/resources/grbs/$event1"
  obs_clean="$obs_dir/${event1}clean.csv"
  obs_plain="$obs_dir/${event1}.csv"
  if [ -f "$obs_clean" ]; then
    obs1="$obs_clean"
  elif [ -f "$obs_plain" ]; then
    obs1="$obs_plain"
  else
    obs1="$(find "$obs_dir" -maxdepth 1 -type f -name '*.csv' 2>/dev/null | sort | head -n 1 || true)"
  fi
fi

res1="${RESULTS_DIR:-$ROOT/VegasJetFit/jetfit/results/${event1}_${model_tag}_Ansh_Run}"
mkdir -p "$res1"

log_stem_default="$(basename "$res1")"
log_stem="${LOG_BASENAME:-$log_stem_default}"
log_file1="${LOG_FILE_OVERRIDE:-$LOG_DIR/${log_stem}.log}"
start_utc_file="${START_UTC_FILE_OVERRIDE:-$LOG_DIR/${log_stem}.start_utc}"
pid_file="${PID_FILE_OVERRIDE:-$LOG_DIR/${log_stem}.pid}"

preflight_res1="${PREFLIGHT_RESULTS:-$ROOT/VegasJetFit/jetfit/results/${log_stem}_preflight}"
preflight_log1="${PREFLIGHT_LOG_FILE_OVERRIDE:-$LOG_DIR/${log_stem}.preflight.log}"
preflight_mcmc1="${PREFLIGHT_MCMC_FILE_OVERRIDE:-$LOG_DIR/${log_stem}.preflight.mcmc.toml}"
SYNC_SCRIPT="$ROOT/VegasJetFit/scripts/sync_results_to_drive.sh"
RUNNER_SCRIPT="$ROOT/VegasJetFit/scripts/run_fit_and_sync.sh"
MINIMIZE_SCRIPT="$ROOT/VegasJetFit/scripts/minimize.py"

if [ ! -f "$obs1" ]; then
  echo "ERROR: observation file not found: $obs1" >&2
  return 2 2>/dev/null || exit 2
fi
if [ "$RUN_MINIMIZER" = "1" ] && [ ! -f "$MINIMIZE_SCRIPT" ]; then
  echo "ERROR: minimizer script not found: $MINIMIZE_SCRIPT" >&2
  return 2 2>/dev/null || exit 2
fi

run_minimizer() {
  local run_status="${1:-0}"
  local min_status
  local min_cmd

  if [ "$RUN_MINIMIZER" != "1" ]; then
    return 0
  fi
  if [ "$run_status" -ne 0 ]; then
    echo "Minimizer skipped because run failed (status=$run_status)."
    return 0
  fi
  if [ ! -f "$MINIMIZE_SCRIPT" ]; then
    echo "WARNING: minimizer script not found: $MINIMIZE_SCRIPT"
    if [ "$MINIMIZE_STRICT" = "1" ]; then
      return 2
    fi
    return 0
  fi

  min_cmd=( "$PYTHON_BIN" "$MINIMIZE_SCRIPT"
    --results "$res1"
    --mode "$MINIMIZE_MODE"
    --minimizer "$MINIMIZE_MINIMIZER"
  )
  if [ "$MINIMIZE_MAX_WALKERS" != "0" ]; then
    min_cmd+=( --max-walkers "$MINIMIZE_MAX_WALKERS" )
  fi
  if [ -n "$MINIMIZE_OUTPUT_DIR" ]; then
    min_cmd+=( --output "$MINIMIZE_OUTPUT_DIR" )
  fi

  echo "Running minimizer..."
  echo "  Mode:      $MINIMIZE_MODE"
  echo "  MaxWalker: $MINIMIZE_MAX_WALKERS"
  echo "  Optimizer: $MINIMIZE_MINIMIZER"
  if [ -n "$MINIMIZE_OUTPUT_DIR" ]; then
    echo "  Output:    $MINIMIZE_OUTPUT_DIR"
  fi
  {
    echo "[minimizer] start_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "[minimizer] cmd=${min_cmd[*]}"
  } >> "$log_file1"

  if (
    cd "$ROOT/VegasJetFit"
    run_with_sleep_guard "${min_cmd[@]}" >> "$log_file1" 2>&1
  ); then
    min_status=0
    echo "Minimizer completed."
  else
    min_status=$?
    echo "WARNING: minimizer failed (exit $min_status)."
    echo "---- last 60 lines of log ----"
    tail -n 60 "$log_file1" || true
    echo "------------------------------"
  fi

  if [ "$min_status" -ne 0 ] && [ "$MINIMIZE_STRICT" = "1" ]; then
    return "$min_status"
  fi
  return 0
}

sync_results_to_drive() {
  local run_status="${1:-0}"
  local sync_label
  local sync_output

  if [ "$DRIVE_SYNC_ENABLE" != "1" ]; then
    return 0
  fi
  if [ "$run_status" -ne 0 ]; then
    echo "Drive sync skipped because run failed (status=$run_status)."
    return 0
  fi
  if [ ! -x "$SYNC_SCRIPT" ]; then
    echo "WARNING: sync helper missing or not executable: $SYNC_SCRIPT"
    return 0
  fi
  if [ ! -d "$DRIVE_RESULTS_ROOT" ]; then
    echo "WARNING: drive root not found: $DRIVE_RESULTS_ROOT"
    return 0
  fi

  sync_label="$DRIVE_RUN_LABEL"
  if [ -z "$sync_label" ]; then
    sync_label="$(basename "$res1")"
  fi

  if sync_output="$("$SYNC_SCRIPT" \
      --results-dir "$res1" \
      --event "$event1" \
      --drive-root "$DRIVE_RESULTS_ROOT" \
      --owner-subdir "$DRIVE_OWNER_SUBDIR" \
      --run-label "$sync_label" \
      --log-file "$log_file1" \
      --mcmc-file "$MCMC_SETTINGS" \
      --model-file "$MODEL_TOML" \
      --obs-file "$obs1" 2>&1)"; then
    echo "Drive sync completed: $sync_output"
  else
    echo "WARNING: Drive sync failed."
    echo "$sync_output"
  fi
}

echo
echo "Event:   $event1"
echo "Obs:     $obs1"
echo "Model:   $MODEL_TOML"
echo "Results: $res1"
echo "Log:     $log_file1"
echo
echo "MCMC profile:"
sed -n '1,80p' "$MCMC_SETTINGS"
echo

RESUME_OPTION=""
if [ "$RESUME" = "1" ]; then
  RESUME_OPTION="--resume"
fi

# ---- Preflight ----
if [ "$ENABLE_PREFLIGHT" = "1" ]; then
  case "$PREFLIGHT_BURN_LENGTH" in
    ''|*[!0-9]*)
      echo "ERROR: PREFLIGHT_BURN_LENGTH must be a non-negative integer, got '$PREFLIGHT_BURN_LENGTH'" >&2
      return 2 2>/dev/null || exit 2
      ;;
  esac
  case "$PREFLIGHT_RUN_LENGTH" in
    ''|*[!0-9]*)
      echo "ERROR: PREFLIGHT_RUN_LENGTH must be a non-negative integer, got '$PREFLIGHT_RUN_LENGTH'" >&2
      return 2 2>/dev/null || exit 2
      ;;
  esac

  mkdir -p "$preflight_res1"

  awk -v burn="$PREFLIGHT_BURN_LENGTH" -v run="$PREFLIGHT_RUN_LENGTH" '
    BEGIN {seen_burn=0; seen_run=0}
    /^[[:space:]]*burn_length[[:space:]]*=/ {print "burn_length = " burn; seen_burn=1; next}
    /^[[:space:]]*run_length[[:space:]]*=/  {print "run_length = " run; seen_run=1; next}
    {print}
    END {
      if (!seen_burn) print "burn_length = " burn
      if (!seen_run)  print "run_length = " run
    }
  ' "$MCMC_SETTINGS" > "$preflight_mcmc1"

  echo "Running preflight..."
  echo "  Results: $preflight_res1"
  echo "  Log:     $preflight_log1"
  echo "  MCMC:    $preflight_mcmc1"

  if (
    cd "$ROOT/VegasJetFit"
    run_with_sleep_guard /usr/bin/time -p "$PYTHON_BIN" -u -m jetfit.run \
      --event "$event1" \
      --obs "$obs1" \
      --model "$MODEL_TOML" \
      --results "$preflight_res1" \
      --mcmc "$preflight_mcmc1" \
      --workers "$MCMC_WORKERS" \
      --start-method "$MP_START_METHOD" \
      --skip-plots \
      > "$preflight_log1" 2>&1
  ); then
    preflight_status=0
  else
    preflight_status=$?
  fi

  if [ "$preflight_status" -ne 0 ]; then
    echo "ERROR: preflight failed (exit $preflight_status). Production run not started." >&2
    echo "---- last 80 lines of preflight log ----" >&2
    tail -n 80 "$preflight_log1" >&2 || true
    echo "----------------------------------------" >&2
    return "$preflight_status" 2>/dev/null || exit "$preflight_status"
  fi

  echo "Preflight passed. Starting full production run."
  echo

  if [ "$PREFLIGHT_ONLY" = "1" ]; then
    echo "PREFLIGHT_ONLY=1 set, not launching production run."
    return 0 2>/dev/null || exit 0
  fi
fi

# ---- Launch ----
if [ "$RUN_FOREGROUND" = "1" ]; then
  cd "$ROOT/VegasJetFit"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$start_utc_file"
  if run_with_sleep_guard /usr/bin/time -p "$PYTHON_BIN" -u -m jetfit.run \
    --event "$event1" \
    --obs "$obs1" \
    --model "$MODEL_TOML" \
    --results "$res1" \
    --mcmc "$MCMC_SETTINGS" \
    --workers "$MCMC_WORKERS" \
    --start-method "$MP_START_METHOD" \
    ${RESUME_OPTION:+$RESUME_OPTION} \
    > "$log_file1" 2>&1; then
    echo "Foreground run completed successfully."
    if run_minimizer 0; then
      :
    else
      status=$?
      echo "ERROR: minimizer step failed (exit $status)." >&2
      return "$status" 2>/dev/null || exit "$status"
    fi
    sync_results_to_drive 0
  else
    status=$?
    echo "ERROR: foreground run failed (exit $status)." >&2
    echo "---- last 80 lines of log ----" >&2
    tail -n 80 "$log_file1" >&2 || true
    echo "------------------------------" >&2
    return "$status" 2>/dev/null || exit "$status"
  fi

  echo
  echo "---- last 80 lines of log ----"
  tail -n 80 "$log_file1" || true
  echo "------------------------------"
  echo
  echo "Results directory listing:"
  ls -la "$res1" || true
  return 0 2>/dev/null || exit 0
fi

(
  cd "$ROOT/VegasJetFit"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$start_utc_file"
  if [ ! -x "$RUNNER_SCRIPT" ]; then
    echo "ERROR: background runner missing or not executable: $RUNNER_SCRIPT" >> "$log_file1"
    return 2 2>/dev/null || exit 2
  fi
  nohup /bin/bash "$RUNNER_SCRIPT" \
    --root "$ROOT" \
    --event "$event1" \
    --obs "$obs1" \
    --model "$MODEL_TOML" \
    --results "$res1" \
    --mcmc "$MCMC_SETTINGS" \
    --workers "$MCMC_WORKERS" \
    --start-method "$MP_START_METHOD" \
    --python-bin "$PYTHON_BIN" \
    --log-file "$log_file1" \
    --resume "$RESUME" \
    --keep-awake "$KEEP_AWAKE" \
    --run-minimizer "$RUN_MINIMIZER" \
    --minimize-mode "$MINIMIZE_MODE" \
    --minimize-max-walkers "$MINIMIZE_MAX_WALKERS" \
    --minimize-minimizer "$MINIMIZE_MINIMIZER" \
    --minimize-output "$MINIMIZE_OUTPUT_DIR" \
    --minimize-strict "$MINIMIZE_STRICT" \
    --minimize-script "$MINIMIZE_SCRIPT" \
    --drive-sync-enable "$DRIVE_SYNC_ENABLE" \
    --drive-root "$DRIVE_RESULTS_ROOT" \
    --drive-owner "$DRIVE_OWNER_SUBDIR" \
    --drive-run-label "$DRIVE_RUN_LABEL" \
    --sync-script "$SYNC_SCRIPT" \
    >> "$log_file1" 2>&1 &
  echo $! > "$pid_file"
)

pid="$(cat "$pid_file" 2>/dev/null || true)"
echo "Started background job. PID: ${pid:-UNKNOWN}"
echo

# Give it a moment to write something
sleep "${SLEEP_SECS:-1}"

echo "---- last 80 lines of log ----"
if [ -f "$log_file1" ]; then
  tail -n 80 "$log_file1" || true
else
  echo "(log file not created yet)"
fi
echo "------------------------------"
echo

if [ -n "${pid:-}" ]; then
  if kill -0 "$pid" 2>/dev/null; then
    echo "Process check: PID $pid is running."
  else
    echo "Process check: PID $pid is NOT running (exited quickly)."
    echo "If it exited, the log above should say why."
  fi
fi

echo
echo "Results directory listing:"
ls -la "$res1" || true
