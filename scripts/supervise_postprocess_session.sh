#!/usr/bin/env bash
# Restart a Lyra post-processing session after a recoverable script failure.
set -euo pipefail

SESSION="${SESSION:?set SESSION}"
STARTER="${STARTER:?set STARTER}"
MANIFEST="${MANIFEST:?set MANIFEST}"
CAMPAIGN="${CAMPAIGN:?set CAMPAIGN}"
MARKER="${PUBLISHED_MARKER:-core_postfit_products.validated}"
POLL_SECONDS="${POLL_SECONDS:-60}"

all_published() {
  local event
  while IFS=, read -r event _; do
    [[ "$event" == "event" || -z "$event" ]] && continue
    [[ -f "$CAMPAIGN/$event/$MARKER" ]] || return 1
  done < "$MANIFEST"
  return 0
}

while true; do
  if all_published; then
    printf '[%s] all_manifest_events_published session=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$SESSION"
    exit 0
  fi
  if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    printf '[%s] restarting_postprocessor session=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$SESSION"
    bash "$STARTER"
  fi
  sleep "$POLL_SECONDS"
done
