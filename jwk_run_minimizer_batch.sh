#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
PROJECT_ROOT="${PROJECT_ROOT:-$ROOT/VegasJetFit}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
MIN_SCRIPT="${MIN_SCRIPT:-$PROJECT_ROOT/scripts/minimize.py}"
RESULTS_ROOT="${RESULTS_ROOT:-$PROJECT_ROOT/jetfit/results}"
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/logs}"

MODE="${MODE:-walkers}"
MINIMIZER="${MINIMIZER:-minimize}"
SCIPY_METHOD="${SCIPY_METHOD:-Powell}"
FALLBACK_SCIPY_METHOD="${FALLBACK_SCIPY_METHOD:-Nelder-Mead}"
PATTERN="${PATTERN:-*_powerlaw_tophat_theta1p0_*}"
MAX_WALKERS="${MAX_WALKERS:-0}"

mkdir -p "$LOG_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="$LOG_DIR/minimize_batch_${STAMP}.log"
SUMMARY_CSV="$LOG_DIR/minimize_batch_${STAMP}.csv"

{
  echo "ROOT=$ROOT"
  echo "PROJECT_ROOT=$PROJECT_ROOT"
  echo "RESULTS_ROOT=$RESULTS_ROOT"
  echo "PATTERN=$PATTERN"
  echo "MODE=$MODE"
  echo "MINIMIZER=$MINIMIZER"
  echo "SCIPY_METHOD=$SCIPY_METHOD"
  echo "FALLBACK_SCIPY_METHOD=$FALLBACK_SCIPY_METHOD"
  echo "MAX_WALKERS=$MAX_WALKERS"
  echo "START_UTC=$STAMP"
} | tee -a "$BATCH_LOG"

printf "event,results_dir,status,nmap,minimized_json\n" > "$SUMMARY_CSV"

shopt -s nullglob
dirs=( "$RESULTS_ROOT"/$PATTERN )
shopt -u nullglob

if [ "${#dirs[@]}" -eq 0 ]; then
  echo "No result directories matched pattern: $RESULTS_ROOT/$PATTERN" | tee -a "$BATCH_LOG"
  exit 0
fi

for results_dir in "${dirs[@]}"; do
  if [ ! -d "$results_dir" ]; then
    continue
  fi
  if [ ! -f "$results_dir/chain.npz" ] || [ ! -f "$results_dir/best_fit.json" ]; then
    echo "Skipping (missing chain.npz or best_fit.json): $results_dir" | tee -a "$BATCH_LOG"
    continue
  fi

  event="$(basename "$results_dir" | cut -d'_' -f1)"
  minimized_json="$results_dir/minimized/minimized.json"

  echo "==================================================" | tee -a "$BATCH_LOG"
  echo "Minimizing: $results_dir" | tee -a "$BATCH_LOG"
  echo "Event: $event" | tee -a "$BATCH_LOG"

  cmd=(
    "$PYTHON_BIN" "$MIN_SCRIPT"
    --results "$results_dir"
    --mode "$MODE"
    --minimizer "$MINIMIZER"
    --scipy-method "$SCIPY_METHOD"
    --fallback-scipy-method "$FALLBACK_SCIPY_METHOD"
  )
  if [ -f "$results_dir/model.toml" ]; then
    cmd+=( --params "$results_dir/model.toml" )
  fi
  if [ "$MAX_WALKERS" != "0" ]; then
    cmd+=( --max-walkers "$MAX_WALKERS" )
  fi

  if PYTHONPATH="$PROJECT_ROOT" "${cmd[@]}" >> "$BATCH_LOG" 2>&1; then
    nmap="$("$PYTHON_BIN" - <<'PY' "$minimized_json"
import json
import sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.exists():
    print("")
    raise SystemExit(0)
with p.open() as f:
    d = json.load(f)
print(d.get("nmap", ""))
PY
)"
    printf "%s,%s,%s,%s,%s\n" "$event" "$results_dir" "ok" "$nmap" "$minimized_json" >> "$SUMMARY_CSV"
    echo "Done: $results_dir (nmap=$nmap)" | tee -a "$BATCH_LOG"
  else
    printf "%s,%s,%s,%s,%s\n" "$event" "$results_dir" "error" "" "$minimized_json" >> "$SUMMARY_CSV"
    echo "ERROR: $results_dir" | tee -a "$BATCH_LOG"
  fi
done

echo "Summary CSV: $SUMMARY_CSV" | tee -a "$BATCH_LOG"
echo "Batch log:   $BATCH_LOG" | tee -a "$BATCH_LOG"
