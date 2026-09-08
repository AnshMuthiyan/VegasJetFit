#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
REPORT="$VJF/reports/core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_pending"
RUN_TAG="${RUN_TAG:-core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_v1}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_core_logangle_kminus10to3_10temp_5000x5000.toml}"
CAMPAIGN="${CAMPAIGN:-$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_07__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__final_seeded__10_temperature_5000x5000}"
SESSION="${SESSION:-dynamic_dispatch_core_logangle_powerlaw_kminus10to3_final_seeded_10temp_5000}"
POLL_SECONDS="${POLL_SECONDS:-300}"
LOG="${LOG:-$VJF/logs/${SESSION}.log}"

mkdir -p "$REPORT" "$CAMPAIGN" "$VJF/logs"
cmd="cd '$VJF' && while true; do date -u; '$PY' scripts/dynamic_dispatch_campaign.py --queue '$REPORT/dynamic_event_queue.csv' --manifest '$REPORT/dispatch_manifest.csv' --run-tag '$RUN_TAG' --event-script scripts/run_core_logangle_powerlaw_15grb_event.sh --campaign '$CAMPAIGN' --session-prefix core_logangle_powerlaw_kminus10to3_final_seeded_10temp_5000 --busy-pattern core_logangle_powerlawcsm --sync-path '$CONFIG_DIR' --sync-path '$MCMC_SETTINGS' --sync-path '$REPORT' --env CONFIG_DIR='$CONFIG_DIR' --env MCMC_SETTINGS='$MCMC_SETTINGS'; sleep '$POLL_SECONDS'; done >> '$LOG' 2>&1"

echo "launching dispatcher session=$SESSION"
echo "$cmd"
tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" "$cmd"
