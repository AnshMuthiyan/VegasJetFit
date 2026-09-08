#!/usr/bin/env bash
# Run all currently eligible fixed-parameter resolution ladders on Lyra.
set -euo pipefail

ROOT=/Users/jkeohane/GRBs
VJF=$ROOT/VegasJetFit
SOURCE_ROOT=$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_16__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__moderate_resolution__5_temperature_1000x5000
CAMPAIGN=$VJF/reports/vegasafterglow_resolution_ladder_15grb_finalfinal
QUEUE=$CAMPAIGN/resolution_queue.csv
OUT_ROOT=${OUT_ROOT:-$CAMPAIGN/results}
MPL_CACHE=${MPL_CACHE:-/tmp/matplotlib-vegas-resolution-ladder}
RUN_LOG=${RUN_LOG:-$OUT_ROOT/run_log.txt}
PYTHON=$ROOT/.venv/bin/python

mkdir -p "$OUT_ROOT" "$MPL_CACHE"
exec > >(tee -a "$RUN_LOG") 2>&1

while IFS=, read -r order event status _; do
    [[ "$order" == "queue_order" ]] && continue
    [[ "$status" == "ready-when-finalfinal-published" ]] || continue
    results=$SOURCE_ROOT/$event
    for required in "$results/minimized/minimized.json" "$results/model.toml" "$results/obs.csv"; do
        [[ -f "$required" ]] || { echo "BLOCKED $event missing $required"; continue 2; }
    done
    echo "START $event $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    MPLCONFIGDIR=$MPL_CACHE "$PYTHON" "$VJF/scripts/run_vegas_resolution_ladder.py" \
        --event "$event" --results "$results" --out "$OUT_ROOT/$event"
    echo "DONE $event $(date -u +%Y-%m-%dT%H:%M:%SZ)"
done < "$QUEUE"

echo "ALL_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
