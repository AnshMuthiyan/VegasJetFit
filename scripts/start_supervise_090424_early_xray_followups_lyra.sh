#!/usr/bin/env bash
set -euo pipefail

VJF="${ROOT:-/Users/jkeohane/GRBs}/VegasJetFit"
SESSION="supervise_090424_early_xray_followups"

tmux has-session -t "$SESSION" 2>/dev/null || \
  tmux new-session -d -s "$SESSION" "cd '$VJF' && exec bash '$VJF/scripts/supervise_090424_early_xray_followups.sh' >> '$VJF/logs/supervise_090424_early_xray_followups.log' 2>&1"
echo "supervisor_session=$SESSION"
