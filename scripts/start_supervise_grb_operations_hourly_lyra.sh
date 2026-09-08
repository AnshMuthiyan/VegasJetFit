#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
SESSION="supervise_grb_operations_hourly_lyra"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Hourly operations supervisor already running: tmux attach -t $SESSION"
  exit 0
fi
tmux new-session -d -s "$SESSION" "cd '$VJF' && exec bash '$VJF/scripts/supervise_grb_operations_hourly.sh'"
echo "Started hourly operations supervisor: tmux attach -t $SESSION"
