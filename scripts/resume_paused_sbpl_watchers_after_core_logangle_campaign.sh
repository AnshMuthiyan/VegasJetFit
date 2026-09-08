#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
WATCHER="$ROOT/tmp/watch_sbpl_pair_family_20260622.sh"

if [ ! -x "$WATCHER" ]; then
  echo "Paused SBPL watcher not found or not executable: $WATCHER" >&2
  exit 2
fi

for family in sbpl powerlaw; do
  session="watch_sbpl_pair_${family}_20260622"
  if tmux has-session -t "$session" 2>/dev/null; then
    echo "Watcher already running: $session"
    continue
  fi
  tmux new-session -d -s "$session" \
    "env FAMILY=$family /bin/bash '$WATCHER'"
  echo "Resumed watcher: $session"
done
