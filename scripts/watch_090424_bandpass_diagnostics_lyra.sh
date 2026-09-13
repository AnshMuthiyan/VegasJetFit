#!/usr/bin/env bash
set -euo pipefail

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
SESSION="${SESSION:-bandpass_090424_diagnostics}"
POLL_SECONDS="${POLL_SECONDS:-300}"
MAX_RESTARTS="${MAX_RESTARTS:-3}"
WATCH_LOG="$VJF/logs/090424.bandpass_diagnostics.watch.log"
restart_count=0

complete() {
  local variant tag results
  for variant in trotter ccm; do
    tag="090424_${variant}_bandpass_verified_5temp_25x100_v1"
    results="$VJF/jetfit/results/$tag"
    [[ -s "$results/chain.npz" && -s "$results/best_fit.json" ]] || return 1
  done
}

mkdir -p "$VJF/logs"
while ! complete; do
  if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    if (( restart_count >= MAX_RESTARTS )); then
      printf '%s restart limit reached; manual review required\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$WATCH_LOG"
      exit 1
    fi
    restart_count=$((restart_count + 1))
    printf '%s restarting diagnostics, attempt %d/%d\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$restart_count" "$MAX_RESTARTS" >>"$WATCH_LOG"
    tmux new-session -d -s "$SESSION" \
      "cd '$VJF' && exec caffeinate -is bash scripts/run_090424_bandpass_diagnostics_lyra.sh >> logs/090424.bandpass_diagnostics.supervisor.log 2>&1"
  fi
  sleep "$POLL_SECONDS"
done

printf '%s both diagnostics complete\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$WATCH_LOG"
