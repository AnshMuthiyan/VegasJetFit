#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
REPORT="$VJF/reports/090424_core_logangle_powerlaw_kminus10to3_final_seeded_alluv_10temp_5000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_final_seeded_alluv_10temp_5000x5000_v2"
CONFIG_DIR="$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending"
MCMC_SETTINGS="$VJF/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml"
INITIAL_POSITIONS="$VJF/initial_positions/090424_alluv_unseeded_final_seeded_10temp.npz"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_07__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__final_seeded__10_temperature_5000x5000"
SESSION="dynamic_dispatch_090424_final_seeded_alluv_lyra"
LOG="$VJF/logs/dynamic_dispatch_090424_final_seeded_alluv_10temp_lyra.log"
POLL_SECONDS="${POLL_SECONDS:-300}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "090424 all-UV seeded dispatcher is already running: tmux attach -t $SESSION"
  exit 0
fi

COMMAND="cd '$VJF' && while true; do date -u +%Y-%m-%dT%H:%M:%SZ; '$PY' '$VJF/scripts/dynamic_dispatch_campaign.py' --queue '$REPORT/dynamic_event_queue.csv' --manifest '$REPORT/dispatch_manifest.csv' --run-tag '$RUN_TAG' --event-script '$VJF/scripts/run_core_logangle_powerlaw_15grb_event.sh' --results-root '$VJF/jetfit/results' --campaign '$CAMPAIGN' --machines 'pauley404-01:8' --session-prefix 'grb_090424_alluv_seeded' --busy-pattern 'jetfit.run' --decision-records '$REPORT/event_decision_records.json' --sync-path '$CONFIG_DIR' --sync-path '$MCMC_SETTINGS' --sync-path '$INITIAL_POSITIONS' --sync-path '$VJF/obs_overrides/090424_early_uvoir_included_no_early_xray.csv' --env 'CONFIG_DIR=$CONFIG_DIR' --env 'MCMC_SETTINGS=$MCMC_SETTINGS' --env 'INITIAL_POSITIONS=$INITIAL_POSITIONS'; sleep '$POLL_SECONDS'; done >> '$LOG' 2>&1"
tmux new-session -d -s "$SESSION" "$COMMAND"
echo "Started Pauley-01 090424 all-UV 10-temperature seeded dispatcher."
