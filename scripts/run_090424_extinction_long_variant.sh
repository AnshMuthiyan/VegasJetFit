#!/usr/bin/env bash
set -euo pipefail

variant="${1:?usage: run_090424_extinction_long_variant.sh ccm|trotter}"
case "$variant" in
  ccm) source_extinction_model="ccm89" ;;
  trotter) source_extinction_model="trotter2011" ;;
  *) echo "Unknown extinction variant: $variant" >&2; exit 2 ;;
esac

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
WORKERS="${WORKERS:-8}"
tag="090424_${variant}_bandpass_verified_5temp_100x800_v1"
config="$VJF/run_configs/bandpass_integration/090424_${variant}"
results="$VJF/jetfit/results/$tag"
log="$VJF/logs/${tag}.log"
resume_args=()

mkdir -p "$VJF/logs"
if [[ -s "$results/chain.npz" && -s "$results/best_fit.json" ]]; then
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

echo "Starting $tag at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
/usr/bin/time -p env PYTHONPATH="$VJF" MPLBACKEND=Agg \
  "$PY" -u -m jetfit.run \
    --event 090424 \
    --obs "$config/obs.csv" \
    --model "$config/model.toml" \
    --mcmc "$VJF/run_configs/bandpass_integration/mcmc_5temp_100x800.toml" \
    --results "$results" \
    --initial-positions "$config/initial_positions_long.npz" \
    --workers "$WORKERS" \
    --start-method spawn \
    --bandpass-integration verified \
    --bandpass-nodes 16 \
    --source-extinction-model "$source_extinction_model" \
    ${resume_args[@]+"${resume_args[@]}"} \
    --skip-plots \
    >>"$log" 2>&1
echo "Completed $tag at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$log"
