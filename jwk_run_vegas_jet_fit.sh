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
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings.toml}"
MODEL_TOML="${MODEL_TOML:-}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
PREFLIGHT_ONLY="${PREFLIGHT_ONLY:-0}"
RUN_FOREGROUND="${RUN_FOREGROUND:-0}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RESUME="${RESUME:-0}"

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
echo "MCMC settings:  $MCMC_SETTINGS"
echo "Preflight:      $ENABLE_PREFLIGHT (burn=$PREFLIGHT_BURN_LENGTH run=$PREFLIGHT_RUN_LENGTH)"
echo "Preflight only: $PREFLIGHT_ONLY"
echo "Run foreground: $RUN_FOREGROUND"
echo "Keep awake:     $KEEP_AWAKE"
echo "Resume:         $RESUME"
if [ "${#CAFFEINATE_CMD[@]}" -gt 0 ]; then
  echo "Sleep guard:    ${CAFFEINATE_CMD[*]}"
else
  echo "Sleep guard:    disabled"
fi
echo "Python: $(which python)"
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
log_file1="$LOG_DIR/${event1}.${model_tag}.log"

if [ -n "${OBS_CSV:-}" ]; then
  obs1="$OBS_CSV"
else
  obs1="$ROOT/VegasJetFit/jetfit/resources/grbs/$event1/${event1}clean.csv"
fi

res1="${RESULTS_DIR:-$ROOT/VegasJetFit/jetfit/results/${event1}_${model_tag}_Ansh_Run}"
mkdir -p "$res1"

preflight_res1="${PREFLIGHT_RESULTS:-$ROOT/VegasJetFit/jetfit/results/${event1}_${model_tag}_preflight}"
preflight_log1="$LOG_DIR/${event1}.${model_tag}.preflight.log"
preflight_mcmc1="$LOG_DIR/${event1}.${model_tag}.preflight.mcmc.toml"

if [ ! -f "$obs1" ]; then
  echo "ERROR: observation file not found: $obs1" >&2
  return 2 2>/dev/null || exit 2
fi

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
    "${CAFFEINATE_CMD[@]}" /usr/bin/time -p python -u -m jetfit.run \
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
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$LOG_DIR/${event1}.${model_tag}.start_utc"
  if "${CAFFEINATE_CMD[@]}" /usr/bin/time -p python -u -m jetfit.run \
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
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$LOG_DIR/${event1}.${model_tag}.start_utc"
  nohup "${CAFFEINATE_CMD[@]}" /usr/bin/time -p python -u -m jetfit.run \
    --event "$event1" \
    --obs "$obs1" \
    --model "$MODEL_TOML" \
    --results "$res1" \
    --mcmc "$MCMC_SETTINGS" \
    --workers "$MCMC_WORKERS" \
    --start-method "$MP_START_METHOD" \
    ${RESUME_OPTION:+$RESUME_OPTION} \
    > "$log_file1" 2>&1 &
  echo $! > "$LOG_DIR/${event1}.${model_tag}.pid"
)

pid="$(cat "$LOG_DIR/${event1}.${model_tag}.pid" 2>/dev/null || true)"
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
