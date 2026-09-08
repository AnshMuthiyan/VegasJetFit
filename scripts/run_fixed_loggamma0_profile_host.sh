#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 5 ]; then
  echo "Usage: $0 RESULTS_ROOT CONFIG_DIR OBS_CSV RUN_TAG LOGGAMMA [...]" >&2
  exit 2
fi

RESULTS_ROOT="$1"; shift
CONFIG_DIR="$1"; shift
OBS_CSV="$1"; shift
RUN_TAG="$1"; shift
VJF="${VJF:-/Users/jkeohane/GRBs/VegasJetFit}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
WORKERS="${WORKERS:-8}"
MAX_WALKERS="${MAX_WALKERS:-16}"

for loggamma in "$@"; do
  label="${loggamma//./p}"
  run_name="080413B_loggamma0_${label}_${RUN_TAG}"
  run_dir="$RESULTS_ROOT/$run_name"
  config="$CONFIG_DIR/080413B_loggamma0_${label}.toml"
  if [ -f "$run_dir/.profile_minimization_complete" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] already_complete loggamma=$loggamma"
    continue
  fi
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] minimize_start loggamma=$loggamma gamma0=1e${loggamma}"
  if "$PY" "$VJF/scripts/minimize.py" \
    --results "$run_dir" \
    --obs "$OBS_CSV" \
    --params "$config" \
    --mode walkers \
    --max-walkers "$MAX_WALKERS" \
    --parallel-workers "$WORKERS" \
    --minimizer minimize \
    --scipy-method Powell \
    --fallback-scipy-method Nelder-Mead; then
    if "$PY" - "$run_dir/minimized/minimized.json" <<'PY'
import json
import math
import sys

value = float(json.load(open(sys.argv[1]))["nmap"])
raise SystemExit(0 if math.isfinite(value) else 1)
PY
    then
      touch "$run_dir/.profile_minimization_complete"
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] minimize_complete loggamma=$loggamma"
      continue
    fi
  fi
  touch "$run_dir/.profile_minimization_failed"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] minimize_failed loggamma=$loggamma" >&2
done
