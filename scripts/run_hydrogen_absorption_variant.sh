#!/usr/bin/env bash
set -euo pipefail

event="${1:?usage: run_hydrogen_absorption_variant.sh EVENT none|igm|igm_host smoke|diagnostic}"
variant="${2:?missing absorption variant}"
stage="${3:?missing run stage}"
case "$variant" in
  none|igm|igm_host) ;;
  *) echo "Unknown absorption variant: $variant" >&2; exit 2 ;;
esac
case "$stage" in
  smoke) dimensions="2x3"; expected_steps=3 ;;
  diagnostic) dimensions="12x40"; expected_steps=40 ;;
  *) echo "Unknown run stage: $stage" >&2; exit 2 ;;
esac

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
WORKERS="${WORKERS:-8}"
config="$VJF/run_configs/hydrogen_absorption/$event/$variant"
mcmc="$VJF/run_configs/hydrogen_absorption/mcmc_${stage}_5temp_${dimensions}.toml"
tag="${event}_hydrogen_${variant}_bandpass_verified_5temp_${dimensions}_v1"
results="$VJF/jetfit/results/$tag"
log="$VJF/logs/${tag}.log"
resume_args=()

valid_completed_result() {
  [[ -s "$results/chain.npz" && -s "$results/best_fit.json" ]] || return 1
  grep -q '^real ' "$log" 2>/dev/null || return 1
  "$PY" - "$results" "$expected_steps" <<'PY'
import json
import sys
from pathlib import Path

import numpy as np

path = Path(sys.argv[1])
expected_steps = int(sys.argv[2])
with np.load(path / "chain.npz", allow_pickle=False) as archive:
    chain = np.asarray(archive["chain"])
if chain.shape[0:2] != (expected_steps, 100):
    raise SystemExit(1)
json.loads((path / "best_fit.json").read_text())
PY
}

mkdir -p "$VJF/logs"
if valid_completed_result; then
  if ! grep -q '^Completed ' "$log" 2>/dev/null; then
    echo "Completed $tag at $(date -u +%Y-%m-%dT%H:%M:%SZ) (validated marker recovery)" \
      | tee -a "$log"
  fi
  echo "Already complete: $tag"
  exit 0
fi
if [[ -s "$results/pt_resume_state.npz" ]]; then
  echo "Resuming $tag from $results/pt_resume_state.npz"
  resume_args+=(--resume)
elif [[ -d "$results" && -n "$(find "$results" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Refusing to overwrite incomplete uncheckpointed result: $results" >&2
  exit 1
fi

echo "Starting $tag at $(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) workers=$WORKERS" | tee -a "$log"
/usr/bin/time -p env PYTHONPATH="$VJF" MPLBACKEND=Agg \
  "$PY" -u -m jetfit.run \
    --event "$event" \
    --obs "$config/obs.csv" \
    --model "$config/model.toml" \
    --mcmc "$mcmc" \
    --results "$results" \
    --initial-positions "$config/initial_positions.npz" \
    --workers "$WORKERS" \
    --start-method spawn \
    --bandpass-integration verified \
    --bandpass-nodes 16 \
    ${resume_args[@]+"${resume_args[@]}"} \
    --skip-plots \
    >>"$log" 2>&1
echo "Completed $tag at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$log"
