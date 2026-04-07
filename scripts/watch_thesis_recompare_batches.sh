#!/usr/bin/env bash
set -euo pipefail

# Watchdog for thesis-comparison reruns.
# - Keeps top-hat recompare and SBPL thesis reruns moving while unattended.
# - Relaunches only pending events when sessions are not running.
# - Exits once all target results are complete.

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
RESULTS_DIR="${RESULTS_DIR:-$VEGAS_DIR/jetfit/results}"
INTERVAL_SEC="${INTERVAL_SEC:-600}"
WORKERS_TOPHAT="${WORKERS_TOPHAT:-4}"
WORKERS_SBPL="${WORKERS_SBPL:-4}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_short.toml}"
TOPHAT_RUN_TAG="${TOPHAT_RUN_TAG:-theta1p0_thesis_short_kmin10_seeded_v1}"
SBPL_RUN_TAG="${SBPL_RUN_TAG:-smoothbroken_thesis_short_kmin10_v1}"
WATCH_LOG="${WATCH_LOG:-$VEGAS_DIR/logs/watch_thesis_recompare_$(date -u +%Y%m%dT%H%M%SZ).log}"

TOPHAT_EVENTS=(
  130612A 171010A 050525A 050922C 210905A
  090424 090618 111228A 131030A 140506A
  161031A 220101A
)
SBPL_EVENTS=(080413B 080319B)

mkdir -p "$(dirname "$WATCH_LOG")"

tophat_done() {
  local ev="$1"
  local d="$RESULTS_DIR/${ev}_powerlaw_tophat_${TOPHAT_RUN_TAG}"
  [ -f "$d/best_fit.json" ] && [ -f "$d/chain.npz" ]
}

sbpl_done() {
  local ev="$1"
  local d="$RESULTS_DIR/${ev}_${SBPL_RUN_TAG}"
  [ -f "$d/best_fit.json" ] && [ -f "$d/chain.npz" ]
}

session_running() {
  local name="$1"
  tmux has-session -t "$name" 2>/dev/null
}

join_by_space() {
  local out=""
  local item
  for item in "$@"; do
    if [ -z "$out" ]; then
      out="$item"
    else
      out="$out $item"
    fi
  done
  printf '%s' "$out"
}

pending_tophat_events() {
  local ev
  local pending=()
  for ev in "${TOPHAT_EVENTS[@]}"; do
    if ! tophat_done "$ev"; then
      pending+=("$ev")
    fi
  done
  join_by_space "${pending[@]}"
}

pending_sbpl_events() {
  local ev
  local pending=()
  for ev in "${SBPL_EVENTS[@]}"; do
    if ! sbpl_done "$ev"; then
      pending+=("$ev")
    fi
  done
  join_by_space "${pending[@]}"
}

launch_tophat() {
  local pending="$1"
  local session="tophat_kmin10_recompare"
  local log="$VEGAS_DIR/logs/${session}_watch_restart_$(date -u +%Y%m%dT%H%M%SZ).log"
  tmux new-session -d -s "$session" \
    "cd '$VEGAS_DIR' && ROOT='$ROOT' RUN_PROFILE_DIR='$RUN_PROFILE_DIR' MCMC_SETTINGS='$MCMC_SETTINGS' WORKERS='$WORKERS_TOPHAT' KEEP_AWAKE=1 RESUME=0 SKIP_COMPLETED=1 CONTINUE_ON_ERROR=1 THETA_C=1.0 THETA_V=0.0 K_LOWER=-10 K_UPPER=3 USE_DYLAN_SEEDS=1 RUN_TAG='$TOPHAT_RUN_TAG' GRBS='$pending' bash '$VEGAS_DIR/jwk_run_all_onaxis_powerlaw.sh' 2>&1 | tee '$log'"
  printf '%s launch tophat pending="%s" log=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$pending" "$log" >> "$WATCH_LOG"
}

launch_sbpl() {
  local pending="$1"
  local session="sbpl_kmin10_recompare"
  local log="$VEGAS_DIR/logs/${session}_watch_restart_$(date -u +%Y%m%dT%H%M%SZ).log"
  tmux new-session -d -s "$session" \
    "cd '$VEGAS_DIR' && ROOT='$ROOT' RUN_PROFILE_DIR='$RUN_PROFILE_DIR' MCMC_SETTINGS='$MCMC_SETTINGS' WORKERS='$WORKERS_SBPL' KEEP_AWAKE=1 K1_LOWER=-10 K1_UPPER=3 RUN_TAG='$SBPL_RUN_TAG' GRBS='$pending' bash '$VEGAS_DIR/jwk_run_sbpl_like_batch.sh' 2>&1 | tee '$log'"
  printf '%s launch sbpl pending="%s" log=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$pending" "$log" >> "$WATCH_LOG"
}

printf '%s watch_start interval=%ss\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$INTERVAL_SEC" >> "$WATCH_LOG"

while true; do
  pending_tophat="$(pending_tophat_events)"
  pending_sbpl="$(pending_sbpl_events)"

  tophat_running=0
  sbpl_running=0
  if session_running "tophat_kmin10_recompare"; then
    tophat_running=1
  fi
  if session_running "sbpl_kmin10_recompare"; then
    sbpl_running=1
  fi

  printf '%s state tophat_running=%s pending_tophat="%s" sbpl_running=%s pending_sbpl="%s"\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$tophat_running" "$pending_tophat" \
    "$sbpl_running" "$pending_sbpl" >> "$WATCH_LOG"

  if [ -z "$pending_tophat" ] && [ -z "$pending_sbpl" ]; then
    printf '%s watch_end all_complete\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$WATCH_LOG"
    exit 0
  fi

  if [ -n "$pending_tophat" ] && [ "$tophat_running" -eq 0 ]; then
    launch_tophat "$pending_tophat"
  fi

  if [ -n "$pending_sbpl" ] && [ "$sbpl_running" -eq 0 ]; then
    launch_sbpl "$pending_sbpl"
  fi

  sleep "$INTERVAL_SEC"
done
