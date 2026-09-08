#!/usr/bin/env bash
# Hourly fleet-level audit: records the same facts used for process updates.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
LOG="${LOG:-$VJF/logs/grb_operations_hourly.log}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-3600}"

mkdir -p "$VJF/logs"
while true; do
  {
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) fleet_audit ==="
    "$HOME/bin/grb-cores" lyra pcrc-mac-studio-1 pcrc-mac-studio-2 pauley404-01 pauley404-02 pauley404-03
    echo "--- capacity ---"
    "$HOME/bin/grb-capacity" --class high --workers 8
    echo "--- postprocess_activity ---"
    find "$VJF/logs/postprocess_activity" -maxdepth 1 -type f -name '*.active' -exec sh -c 'echo "--- $1"; cat "$1"' _ {} \; 2>/dev/null || true
    echo "--- critical_sessions ---"
    sessions="$(tmux list-sessions -F '#S' 2>/dev/null | grep -E '^(dynamic_dispatch_|postprocess_)' || true)"
    if [ -n "$sessions" ]; then
      while IFS= read -r session; do
        [ -n "$session" ] && echo "session=running name=$session"
      done <<< "$sessions"
    else
      echo "session=none name=dynamic_dispatch_or_postprocess"
    fi
  } >> "$LOG" 2>&1
  sleep "$INTERVAL_SECONDS"
done
