#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/core_logangle_powerlaw_15grb_kminus10to3_10temp_5000_campaign"
RUN_TAG="${RUN_TAG:-core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_v1}"
CAMPAIGN="${CAMPAIGN:-$ROOT/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000}"
SESSION="${SESSION:-postprocess_core_logangle_powerlaw_kminus10to3_10temp_5000}"
LOG="${LOG:-$VJF/logs/postprocess_core_logangle_powerlaw_kminus10to3_10temp_5000.log}"
SAMPLER_LABEL="${SAMPLER_LABEL:-100walkers_5000burn_5000run_10temps}"

mkdir -p "$CAMPAIGN" "$VJF/logs"
cmd="cd '$VJF' && env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='$SAMPLER_LABEL' bash scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

echo "launching postprocess session=$SESSION"
echo "$cmd"
tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" "$cmd"
