#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
PROJECT_ROOT="${PROJECT_ROOT:-$ROOT/VegasJetFit}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
RESULTS_ROOT="${RESULTS_ROOT:-$PROJECT_ROOT/jetfit/results}"
RESOURCES_DIR="${RESOURCES_DIR:-$PROJECT_ROOT/jetfit/resources/grbs}"
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/logs}"

BUILDER="${BUILDER:-$PROJECT_ROOT/scripts/build_tophat_model_toml.py}"
MIN_SCRIPT="${MIN_SCRIPT:-$PROJECT_ROOT/scripts/minimize.py}"
PATTERN="${PATTERN:-*_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_v1}"
MODEL_NAME="${MODEL_NAME:-powerlawVegasDylanSpectrumModel}"
OUTPUT_SUBDIR="${OUTPUT_SUBDIR:-minimized_vegasv201_dylanspec_v1}"
MODE="${MODE:-walkers}"
MINIMIZER="${MINIMIZER:-minimize}"
SCIPY_METHOD="${SCIPY_METHOD:-Powell}"
FALLBACK_SCIPY_METHOD="${FALLBACK_SCIPY_METHOD:-Nelder-Mead}"
MAX_WALKERS="${MAX_WALKERS:-0}"
THETA_C="${THETA_C:-1.0}"
THETA_V="${THETA_V:-0.0}"
K_LOWER="${K_LOWER:--10.0}"
K_UPPER="${K_UPPER:-3.0}"
SKIP_COMPLETED="${SKIP_COMPLETED:-1}"

mkdir -p "$LOG_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="$LOG_DIR/tophat_dylan_minimizer_batch_${STAMP}.log"
SUMMARY_CSV="$LOG_DIR/tophat_dylan_minimizer_batch_${STAMP}.csv"

{
  echo "ROOT=$ROOT"
  echo "PROJECT_ROOT=$PROJECT_ROOT"
  echo "RESULTS_ROOT=$RESULTS_ROOT"
  echo "RESOURCES_DIR=$RESOURCES_DIR"
  echo "PATTERN=$PATTERN"
  echo "MODEL_NAME=$MODEL_NAME"
  echo "OUTPUT_SUBDIR=$OUTPUT_SUBDIR"
  echo "MODE=$MODE"
  echo "MINIMIZER=$MINIMIZER"
  echo "SCIPY_METHOD=$SCIPY_METHOD"
  echo "FALLBACK_SCIPY_METHOD=$FALLBACK_SCIPY_METHOD"
  echo "MAX_WALKERS=$MAX_WALKERS"
  echo "THETA_C=$THETA_C"
  echo "THETA_V=$THETA_V"
  echo "K_LOWER=$K_LOWER"
  echo "K_UPPER=$K_UPPER"
  echo "SKIP_COMPLETED=$SKIP_COMPLETED"
  echo "START_UTC=$STAMP"
} | tee -a "$BATCH_LOG"

printf "event,results_dir,output_dir,status,nmap,minimized_json,params_toml\n" > "$SUMMARY_CSV"

shopt -s nullglob
dirs=( "$RESULTS_ROOT"/$PATTERN )
shopt -u nullglob

if [ "${#dirs[@]}" -eq 0 ]; then
  echo "No result directories matched pattern: $RESULTS_ROOT/$PATTERN" | tee -a "$BATCH_LOG"
  exit 0
fi

for results_dir in "${dirs[@]}"; do
  [ -d "$results_dir" ] || continue
  if [ ! -f "$results_dir/chain.npz" ] || [ ! -f "$results_dir/best_fit.json" ]; then
    echo "Skipping (missing chain.npz or best_fit.json): $results_dir" | tee -a "$BATCH_LOG"
    continue
  fi

  event="$(basename "$results_dir" | cut -d'_' -f1)"
  source_model="$RESOURCES_DIR/$event/parameters.toml"
  params_toml="$LOG_DIR/${event}.parameters_tophat_theta${THETA_C}.dylanspec.toml"
  output_dir="$results_dir/$OUTPUT_SUBDIR"
  minimized_json="$output_dir/minimized.json"

  if [ "$SKIP_COMPLETED" = "1" ] && [ -f "$minimized_json" ]; then
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
    printf "%s,%s,%s,%s,%s,%s,%s\n" \
      "$event" "$results_dir" "$output_dir" "skipped_completed" "$nmap" "$minimized_json" "$params_toml" \
      >> "$SUMMARY_CSV"
    echo "Skipping completed output: $minimized_json" | tee -a "$BATCH_LOG"
    continue
  fi

  echo "==================================================" | tee -a "$BATCH_LOG"
  echo "Event:       $event" | tee -a "$BATCH_LOG"
  echo "Results dir: $results_dir" | tee -a "$BATCH_LOG"
  echo "Params TOML: $params_toml" | tee -a "$BATCH_LOG"
  echo "Output dir:  $output_dir" | tee -a "$BATCH_LOG"

  "$PYTHON_BIN" "$BUILDER" \
    --input "$source_model" \
    --output "$params_toml" \
    --theta-c "$THETA_C" \
    --theta-v "$THETA_V" \
    --k-lower "$K_LOWER" \
    --k-upper "$K_UPPER" \
    --model-name "$MODEL_NAME" >> "$BATCH_LOG" 2>&1

  cmd=( "$PYTHON_BIN" "$MIN_SCRIPT"
    --results "$results_dir"
    --params "$params_toml"
    --mode "$MODE"
    --minimizer "$MINIMIZER"
    --scipy-method "$SCIPY_METHOD"
    --fallback-scipy-method "$FALLBACK_SCIPY_METHOD"
    --output "$output_dir"
  )
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
    printf "%s,%s,%s,%s,%s,%s,%s\n" \
      "$event" "$results_dir" "$output_dir" "ok" "$nmap" "$minimized_json" "$params_toml" \
      >> "$SUMMARY_CSV"
    echo "Done: $event (nmap=$nmap)" | tee -a "$BATCH_LOG"
  else
    printf "%s,%s,%s,%s,%s,%s,%s\n" \
      "$event" "$results_dir" "$output_dir" "error" "" "$minimized_json" "$params_toml" \
      >> "$SUMMARY_CSV"
    echo "ERROR: $event" | tee -a "$BATCH_LOG"
  fi
done

echo "Summary CSV: $SUMMARY_CSV" | tee -a "$BATCH_LOG"
echo "Batch log:   $BATCH_LOG" | tee -a "$BATCH_LOG"
