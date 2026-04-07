#!/usr/bin/env bash
set -euo pipefail

# Watchdog for all-event on-axis powerlaw batch.
# - checks completion status every INTERVAL_SEC
# - if batch is not running and work remains, relaunches in a new tmux session
# - exits when all target events have best_fit.json + chain.npz

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
RESULTS_DIR="${RESULTS_DIR:-$VEGAS_DIR/jetfit/results}"
WATCH_LOG="${WATCH_LOG:-$VEGAS_DIR/logs/watch_onaxis_batch_$(date -u +%Y%m%dT%H%M%SZ).log}"
INTERVAL_SEC="${INTERVAL_SEC:-300}"
WORKERS="${WORKERS:-8}"
RUN_TAG="${RUN_TAG:-theta1p0_thesis_short}"

events=(
  050525A 050922C 080319B 080413B
  090424 090618 111228A 130612A
  131030A 140506A 160131A 171010A
  210905A 220101A 221009A 250129A
)

mkdir -p "$(dirname "$WATCH_LOG")"

is_batch_running() {
  if tmux ls 2>/dev/null | rg -q '^vegas_onaxis_restart_|^vegas_onaxis_all_'; then
    return 0
  fi
  if pgrep -f 'jwk_run_all_onaxis_powerlaw.sh' >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

count_done() {
  local done=0
  local ev d
  for ev in "${events[@]}"; do
    d="$RESULTS_DIR/${ev}_powerlaw_tophat_${RUN_TAG}"
    if [ -f "$d/best_fit.json" ] && [ -f "$d/chain.npz" ]; then
      done=$((done + 1))
    fi
  done
  echo "$done"
}

launch_batch() {
  local session stamp run_log
  session="vegas_onaxis_restart_$(date +%Y%m%d_%H%M%S)"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  run_log="$VEGAS_DIR/logs/run_all_onaxis_powerlaw_restart_${stamp}.log"

  tmux new-session -d -s "$session" \
    "cd $ROOT && env ROOT=$ROOT VEGAS_DIR=$VEGAS_DIR RUN_PROFILE_DIR=$RUN_PROFILE_DIR MCMC_SETTINGS=$RUN_PROFILE_DIR/mcmc_settings_thesis_short.toml WORKERS=$WORKERS ENABLE_PREFLIGHT=1 PREFLIGHT_BURN_LENGTH=10 PREFLIGHT_RUN_LENGTH=10 KEEP_AWAKE=1 RESUME=0 SKIP_COMPLETED=1 CONTINUE_ON_ERROR=1 DRY_RUN=0 bash $VEGAS_DIR/jwk_run_all_onaxis_powerlaw.sh > '$run_log' 2>&1"

  printf '%s launch session=%s log=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$session" "$run_log" >> "$WATCH_LOG"
}

printf '%s watch_start interval_sec=%s run_tag=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$INTERVAL_SEC" "$RUN_TAG" >> "$WATCH_LOG"

while true; do
  done_count="$(count_done)"
  total_count="${#events[@]}"
  running=0
  if is_batch_running; then
    running=1
  fi

  printf '%s done=%s/%s running=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$done_count" "$total_count" "$running" >> "$WATCH_LOG"

  if [ "$done_count" -ge "$total_count" ]; then
    printf '%s watch_end all_complete\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$WATCH_LOG"
    exit 0
  fi

  if [ "$running" -eq 0 ]; then
    launch_batch
  fi

  sleep "$INTERVAL_SEC"
done

