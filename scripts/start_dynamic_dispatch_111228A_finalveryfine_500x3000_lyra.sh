#!/usr/bin/env bash
# Dispatch the approved 111228A very-fine continuation to PCRC-1 only.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
REPORT="$VJF/reports/core_logangle_powerlaw_111228A_finalfinal_sthawed_veryfine_5temp_500x3000_campaign"
DECISION_RECORDS="$REPORT/event_decision_records.json"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_veryfine_5temp_500x3000_v1"
CONFIG_DIR="$VJF/structured_jet_core_logangle_powerlaw_111228A_finalfinal_sthawed_veryfine_5temp_configs"
MCMC_SETTINGS="$VJF/Ansh_Run/mcmc_settings_core_logangle_finalfinal_sthawed_fine_5temp_500x3000.toml"
INITIAL_POSITIONS="$VJF/initial_positions/finalfinal_sthawed_veryfine_5temp/111228A.npz"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_23__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__veryfine_resolution_111228A__5_temperature_500x3000"
SESSION="dynamic_dispatch_111228A_finalveryfine_500x3000_lyra"
LOG="$VJF/logs/dynamic_dispatch_111228A_finalveryfine_500x3000_lyra.log"
POLL_SECONDS="${POLL_SECONDS:-60}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "111228A very-fine dispatcher is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
COMMAND="cd '$VJF' && while true; do date -u +%Y-%m-%dT%H:%M:%SZ; '$PY' '$VJF/scripts/dynamic_dispatch_campaign.py' --queue '$REPORT/dynamic_event_queue.csv' --manifest '$REPORT/dispatch_manifest.csv' --run-tag '$RUN_TAG' --event-script '$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh' --results-root '$VJF/jetfit/results' --campaign '$CAMPAIGN' --machines 'pcrc-mac-studio-1:15' --pcrc-workers 15 --session-prefix 'grb_finalveryfine' --busy-pattern 'jetfit.run' --decision-records '$DECISION_RECORDS' --sync-path '$CONFIG_DIR' --sync-path '$MCMC_SETTINGS' --sync-path '$INITIAL_POSITIONS' --env 'CONFIG_DIR=$CONFIG_DIR' --env 'MCMC_SETTINGS=$MCMC_SETTINGS' --env 'INITIAL_POSITIONS=$INITIAL_POSITIONS'; sleep '$POLL_SECONDS'; done >> '$LOG' 2>&1"
tmux new-session -d -s "$SESSION" "$COMMAND"
echo "Started 111228A very-fine dispatcher: tmux attach -t $SESSION"
