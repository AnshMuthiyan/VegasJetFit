#!/usr/bin/env bash
set -euo pipefail

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
WORKERS="${WORKERS:-8}"
MCMC="$VJF/run_configs/bandpass_integration/mcmc_5temp_25x100.toml"

run_variant() {
  local variant="$1"
  local tag="090424_${variant}_bandpass_verified_5temp_25x100_v1"
  local config="$VJF/run_configs/bandpass_integration/090424_${variant}"
  local results="$VJF/jetfit/results/$tag"
  local log="$VJF/logs/${tag}.log"
  local -a resume_args=()

  if [[ -s "$results/chain.npz" && -s "$results/best_fit.json" ]]; then
    echo "Already complete: $tag"
    return
  fi
  if [[ -s "$results/pt_resume_state.npz" ]]; then
    echo "Resuming $tag from $results/pt_resume_state.npz"
    resume_args+=(--resume)
  elif [[ -e "$results/chain.npz" ]]; then
    echo "Refusing to overwrite incomplete result: $results" >&2
    return 1
  fi

  echo "Starting $tag at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  /usr/bin/time -p env PYTHONPATH="$VJF" MPLBACKEND=Agg \
    "$PY" -u -m jetfit.run \
      --event 090424 \
      --obs "$config/obs.csv" \
      --model "$config/model.toml" \
      --mcmc "$MCMC" \
      --results "$results" \
      --initial-positions "$config/initial_positions.npz" \
      --workers "$WORKERS" \
      --start-method fork \
      --bandpass-integration verified \
      --bandpass-nodes 16 \
      ${resume_args[@]+"${resume_args[@]}"} \
      --skip-plots \
      >"$log" 2>&1
  echo "Completed $tag at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

mkdir -p "$VJF/logs"
run_variant trotter
run_variant ccm
