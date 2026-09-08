#!/usr/bin/env bash
# Generate expensive event products on a worker host; Lyra remains publisher.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
EVENT="${1:?usage: run_postfit_compute_only.sh EVENT RESULTS_DIR}"
RESULTS="${2:?usage: run_postfit_compute_only.sh EVENT RESULTS_DIR}"
PRODUCT_WORKERS="${PRODUCT_WORKERS:-8}"
MINIMIZER_MAX_WALKERS="${MINIMIZER_MAX_WALKERS:-8}"
MINIMIZER_WORKERS="${MINIMIZER_WORKERS:-8}"
RESOLUTION_CONVERGENCE="${RESOLUTION_CONVERGENCE:-1}"

[[ -d "$RESULTS" ]] || { echo "results directory not found: $RESULTS" >&2; exit 2; }
[[ -s "$RESULTS/chain.npz" && -s "$RESULTS/obs.csv" && -s "$RESULTS/model.toml" ]] || {
  echo "incomplete results inputs: $RESULTS" >&2
  exit 2
}

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
RUNNING="$RESULTS/.postfit_compute.running"
if ! mkdir "$RUNNING" 2>/dev/null; then
  echo "post-fit compute already active: $RESULTS" >&2
  exit 3
fi
trap 'rm -rf "$RUNNING"' EXIT INT TERM
{
  printf 'pid=%s\nstarted_utc=%s\nevent=%s\nhost=%s\n' "$$" "$(ts)" "$EVENT" "$(hostname)"
} > "$RUNNING/owner"
echo "[$(ts)] compute_only_start event=$EVENT host=$(hostname) results=$RESULTS"

if [[ ! -s "$RESULTS/minimized/minimized.json" ]]; then
  "$PY" "$VJF/scripts/minimize.py" \
    --results "$RESULTS" \
    --obs "$RESULTS/obs.csv" \
    --params "$RESULTS/model.toml" \
    --mode walkers \
    --max-walkers "$MINIMIZER_MAX_WALKERS" \
    --parallel-workers "$MINIMIZER_WORKERS" \
    --scipy-method Powell \
    --fallback-scipy-method Nelder-Mead
fi

"$PY" "$VJF/scripts/generate_postfit_products.py" \
  --results "$RESULTS" \
  --event "$EVENT" \
  --parallel-products \
  --product-workers "$PRODUCT_WORKERS"

validation_args=(--results "$RESULTS")
if [[ "$RESOLUTION_CONVERGENCE" = "1" ]]; then
  "$PY" "$VJF/scripts/run_vegas_resolution_ladder.py" \
    --event "$EVENT" \
    --results "$RESULTS" \
    --out "$RESULTS/resolution_ladder"
  "$PY" "$VJF/scripts/plot_vegas_resolution_ladder.py" \
    --event-dir "$RESULTS/resolution_ladder"
  validation_args+=(--require-resolution-ladder)
fi
"$PY" "$VJF/scripts/validate_core_postfit_products.py" "${validation_args[@]}"
{
  printf 'completed_utc=%s\nevent=%s\nexecutor_host=%s\n' "$(ts)" "$EVENT" "$(hostname)"
} > "$RESULTS/postfit_compute.done"
echo "[$(ts)] compute_only_done event=$EVENT results=$RESULTS"
