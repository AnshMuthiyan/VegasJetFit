#!/usr/bin/env bash
set -euo pipefail

# Conservative overnight queue for light-curve oscillation suspects.
# Launches only when the machine is otherwise idle enough for another fit.

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
RESULTS_DIR="${RESULTS_DIR:-$VEGAS_DIR/jetfit/results}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_short.toml}"
INTERVAL_SEC="${INTERVAL_SEC:-900}"
LOAD1_LIMIT="${LOAD1_LIMIT:-8.0}"
ACTIVE_FIT_LIMIT="${ACTIVE_FIT_LIMIT:-0}"
WORKERS_TOPHAT="${WORKERS_TOPHAT:-3}"
WORKERS_SBPL="${WORKERS_SBPL:-3}"
TOPHAT_RUN_TAG="${TOPHAT_RUN_TAG:-theta1p0_thesis_short_kmin10_seeded_osc_v1}"
SBPL_RUN_TAG="${SBPL_RUN_TAG:-smoothbroken_thesis_short_kmin10_osc_v1}"
WATCH_LOG="${WATCH_LOG:-$VEGAS_DIR/logs/watch_oscillation_reruns_$(date -u +%Y%m%dT%H%M%SZ).log}"

TOPHAT_EVENTS=(111228A 220101A 090618)
SBPL_EVENTS=(080319B)
BLOCKING_SESSIONS=(sbpl_080413B_kmin10_fix)

mkdir -p "$(dirname "$WATCH_LOG")"

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

active_fit_count() {
  ps -Ao command= | awk '
    ($1 ~ /Python|python|caffeinate/) && index($0, "-m jetfit.run") > 0 {count += 1}
    ($1 ~ /Python|python|caffeinate/) && index($0, "/scripts/minimize.py") > 0 {count += 1}
    END {print count + 0}
  '
}

load1_value() {
  uptime | awk -F'load averages: ' 'NF > 1 {print $2}' | awk '{print $1}'
}

can_launch_now() {
  local load1 active blocking
  load1="$(load1_value)"
  active="$(active_fit_count)"
  blocking=""

  for blocking in "${BLOCKING_SESSIONS[@]}"; do
    if session_running "$blocking"; then
      printf 'blocked:tmux:%s load1=%s active_fits=%s' "$blocking" "$load1" "$active"
      return 1
    fi
  done

  if [ "$active" -gt "$ACTIVE_FIT_LIMIT" ]; then
    printf 'blocked:active_fits load1=%s active_fits=%s limit=%s' "$load1" "$active" "$ACTIVE_FIT_LIMIT"
    return 1
  fi

  if ! awk -v load="$load1" -v limit="$LOAD1_LIMIT" 'BEGIN { exit !(load <= limit) }'; then
    printf 'blocked:load load1=%s limit=%s active_fits=%s' "$load1" "$LOAD1_LIMIT" "$active"
    return 1
  fi

  printf 'ok load1=%s active_fits=%s' "$load1" "$active"
  return 0
}

launch_tophat() {
  local pending="$1"
  local session="tophat_oscillation_reruns"
  local log="$VEGAS_DIR/logs/${session}_$(date -u +%Y%m%dT%H%M%SZ).log"
  tmux new-session -d -s "$session" \
    "cd '$VEGAS_DIR' && ROOT='$ROOT' RUN_PROFILE_DIR='$RUN_PROFILE_DIR' MCMC_SETTINGS='$MCMC_SETTINGS' WORKERS='$WORKERS_TOPHAT' KEEP_AWAKE=1 RESUME=0 SKIP_COMPLETED=1 CONTINUE_ON_ERROR=1 THETA_C=1.0 THETA_V=0.0 K_LOWER=-10 K_UPPER=3 USE_DYLAN_SEEDS=1 RUN_TAG='$TOPHAT_RUN_TAG' GRBS='$pending' bash '$VEGAS_DIR/jwk_run_all_onaxis_powerlaw.sh' 2>&1 | tee '$log'"
  printf '%s launch tophat pending="%s" workers=%s log=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$pending" "$WORKERS_TOPHAT" "$log" >> "$WATCH_LOG"
}

launch_sbpl() {
  local pending="$1"
  local session="sbpl_oscillation_reruns"
  local log="$VEGAS_DIR/logs/${session}_$(date -u +%Y%m%dT%H%M%SZ).log"
  tmux new-session -d -s "$session" \
    "cd '$VEGAS_DIR' && ROOT='$ROOT' RUN_PROFILE_DIR='$RUN_PROFILE_DIR' MCMC_SETTINGS='$MCMC_SETTINGS' WORKERS='$WORKERS_SBPL' KEEP_AWAKE=1 K1_LOWER=-10 K1_UPPER=3 RUN_TAG='$SBPL_RUN_TAG' GRBS='$pending' bash '$VEGAS_DIR/jwk_run_sbpl_like_batch.sh' 2>&1 | tee '$log'"
  printf '%s launch sbpl pending="%s" workers=%s log=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$pending" "$WORKERS_SBPL" "$log" >> "$WATCH_LOG"
}

printf '%s watch_start interval=%ss load1_limit=%s active_fit_limit=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$INTERVAL_SEC" "$LOAD1_LIMIT" "$ACTIVE_FIT_LIMIT" >> "$WATCH_LOG"

while true; do
  pending_tophat="$(pending_tophat_events)"
  pending_sbpl="$(pending_sbpl_events)"
  launch_state="$(can_launch_now || true)"

  tophat_running=0
  sbpl_running=0
  if session_running "tophat_oscillation_reruns"; then
    tophat_running=1
  fi
  if session_running "sbpl_oscillation_reruns"; then
    sbpl_running=1
  fi

  printf '%s state launch="%s" tophat_running=%s pending_tophat="%s" sbpl_running=%s pending_sbpl="%s"\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$launch_state" \
    "$tophat_running" "$pending_tophat" \
    "$sbpl_running" "$pending_sbpl" >> "$WATCH_LOG"

  if [ -z "$pending_tophat" ] && [ -z "$pending_sbpl" ]; then
    printf '%s watch_end all_complete\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$WATCH_LOG"
    exit 0
  fi

  if [[ "$launch_state" == ok* ]]; then
    if [ -n "$pending_tophat" ] && [ "$tophat_running" -eq 0 ]; then
      launch_tophat "$pending_tophat"
    elif [ -n "$pending_sbpl" ] && [ "$sbpl_running" -eq 0 ]; then
      launch_sbpl "$pending_sbpl"
    fi
  fi

  sleep "$INTERVAL_SEC"
done
