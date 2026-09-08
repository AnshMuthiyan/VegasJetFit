#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  cleanup_completed_remote_mcmc.sh --event EVENT --results REMOTE_RESULTS_DIR [--session TMUX_SESSION]

Run on the remote MCMC machine after Lyra has pulled a completed MCMC result.
It only cleans up wrappers/tmux sessions when both chain.npz and best_fit.json
exist in the remote results directory.
USAGE
}

EVENT=""
RESULTS=""
SESSION=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --event) EVENT="${2:-}"; shift 2 ;;
    --results) RESULTS="${2:-}"; shift 2 ;;
    --session) SESSION="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$EVENT" ] || [ -z "$RESULTS" ]; then
  echo "ERROR: --event and --results are required" >&2
  usage >&2
  exit 2
fi

if [ ! -f "$RESULTS/chain.npz" ] || [ ! -f "$RESULTS/best_fit.json" ]; then
  echo "not_complete event=$EVENT results=$RESULTS"
  exit 0
fi

# Kill the known tmux session first when supplied.  Otherwise, conservatively
# clean only logejet sessions that contain the event name.
if [ -n "$SESSION" ]; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
else
  if command -v tmux >/dev/null 2>&1; then
    tmux list-sessions -F '#S' 2>/dev/null \
      | grep -E "(^|[^A-Za-z0-9])${EVENT}([^A-Za-z0-9]|$)" \
      | grep -E 'logejet|structjet|penultimate|mcmc' \
      | while IFS= read -r s; do tmux kill-session -t "$s" 2>/dev/null || true; done
  fi
fi

# If the process tree survived the tmux kill, terminate only commands that point
# at this exact event/result directory.  Use TERM first, then a short KILL pass.
patterns=(
  "jetfit.run --event $EVENT .*--results $RESULTS"
  "caffeinate -is .*jetfit.run --event $EVENT .*--results $RESULTS"
  "jwk_run_thesis_reproduction_event.sh"
)
for pat in "${patterns[@]}"; do
  if [ "$pat" = "jwk_run_thesis_reproduction_event.sh" ]; then
    # Only kill generic launch wrappers when their descendant/result path is no
    # longer needed; keep this conservative by matching the event in commandline too.
    pkill -TERM -f "$EVENT.*$pat|$pat.*$EVENT" 2>/dev/null || true
  else
    pkill -TERM -f "$pat" 2>/dev/null || true
  fi
done
sleep 2
for pat in "${patterns[@]}"; do
  if [ "$pat" = "jwk_run_thesis_reproduction_event.sh" ]; then
    pkill -KILL -f "$EVENT.*$pat|$pat.*$EVENT" 2>/dev/null || true
  else
    pkill -KILL -f "$pat" 2>/dev/null || true
  fi
done

echo "remote_mcmc_cleanup_done event=$EVENT results=$RESULTS session=${SESSION:-auto}"
