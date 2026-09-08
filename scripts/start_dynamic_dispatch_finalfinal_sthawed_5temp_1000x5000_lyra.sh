#!/usr/bin/env bash
# Keep the approved final-final queue moving; Lyra is intentionally excluded
# from MCMC here because it is reserved for the campaign postprocessor.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
REPORT="$VJF/reports/core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_1000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_v2"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_16__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__moderate_resolution__5_temperature_1000x5000"
SESSION="dynamic_dispatch_finalfinal_sthawed_5temp_1000x5000_lyra"
LOG="$VJF/logs/dynamic_dispatch_finalfinal_sthawed_5temp_1000x5000_lyra.log"
POLL_SECONDS="${POLL_SECONDS:-300}"
PCRC_WORKERS="${PCRC_WORKERS:-15}"
PAULEY_WORKERS="${PAULEY_WORKERS:-8}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Final-final dispatcher is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
COMMAND="cd '$VJF' && while true; do date -u +%Y-%m-%dT%H:%M:%SZ; '$PY' '$VJF/scripts/dynamic_dispatch_campaign.py' --queue '$REPORT/dynamic_event_queue.csv' --manifest '$REPORT/dispatch_manifest.csv' --run-tag '$RUN_TAG' --event-script '$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh' --results-root '$VJF/jetfit/results' --campaign '$CAMPAIGN' --machines 'pcrc-mac-studio-1:$PCRC_WORKERS,pcrc-mac-studio-2:$PCRC_WORKERS,pauley404-01:$PAULEY_WORKERS,pauley404-02:$PAULEY_WORKERS,pauley404-03:$PAULEY_WORKERS' --pcrc-workers '$PCRC_WORKERS' --session-prefix 'grb_finalfinal' --busy-pattern '$RUN_TAG'; sleep '$POLL_SECONDS'; done >> '$LOG' 2>&1"
tmux new-session -d -s "$SESSION" "$COMMAND"
echo "Started final-final dispatcher: tmux attach -t $SESSION"
