#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_SCRIPT="$VEGAS_DIR/scripts/run_221009A_fixed_gamma0_grid.sh"
CONFIG_DIR="$VEGAS_DIR/thesis_reproduction_configs/221009A_gamma0_grid_top_hat_widephys_v1"
RUN_TAG="gamma0grid_tophat_onaxiswidephys_dylanspec_600x600_v1"
MCMC_SETTINGS="$VEGAS_DIR/Ansh_Run/mcmc_settings_gamma0grid_600x600.toml"
OBS_CLEAN="$VEGAS_DIR/jetfit/resources/grbs/221009A/221009Aclean.csv"
OBS_FULL="$VEGAS_DIR/jetfit/resources/grbs/221009A/221009A.csv"
INTERVAL_SEC="${INTERVAL_SEC:-300}"
LOG_FILE="$VEGAS_DIR/logs/watch_case221009A_grid.log"

mkdir -p "$VEGAS_DIR/logs"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

log() {
  echo "[$(timestamp)] $*" | tee -a "$LOG_FILE"
}

is_done_local() {
  local g="$1"
  local r="$VEGAS_DIR/jetfit/results/221009A_g${g}_${RUN_TAG}"
  [[ -f "$r/minimized/minimized.json" || -f "$r/best_fit.json" ]]
}

is_done_remote() {
  local host="$1" g="$2"
  ssh -o ConnectTimeout=10 "$host" "test -f '$VEGAS_DIR/jetfit/results/221009A_g${g}_${RUN_TAG}/minimized/minimized.json' -o -f '$VEGAS_DIR/jetfit/results/221009A_g${g}_${RUN_TAG}/best_fit.json'" >/dev/null 2>&1
}

session_exists_local() {
  local sess="$1"
  tmux has-session -t "$sess" >/dev/null 2>&1
}

session_exists_remote() {
  local host="$1" sess="$2"
  ssh -o ConnectTimeout=10 "$host" "tmux has-session -t '$sess'" >/dev/null 2>&1
}

start_local_queue() {
  local sess="$1" gammas="$2" queue_label="$3"
  local cmd
  cmd="cd '$VEGAS_DIR' && RESUME=1 CONFIG_DIR='$CONFIG_DIR' RUN_TAG='$RUN_TAG' MCMC_SETTINGS='$MCMC_SETTINGS' WORKERS=8 MCMC_OBS_CSV='$OBS_CLEAN' MINIMIZE_OBS_CSV='$OBS_FULL' bash '$RUN_SCRIPT' $gammas 2>&1 | tee '$VEGAS_DIR/logs/${queue_label}.log'"
  tmux new-session -d -s "$sess" "$cmd"
}

start_remote_queue() {
  local host="$1" sess="$2" gammas="$3" queue_label="$4"
  local remote_cmd
  remote_cmd="cd '$VEGAS_DIR' && RESUME=1 CONFIG_DIR='$CONFIG_DIR' RUN_TAG='$RUN_TAG' MCMC_SETTINGS='$MCMC_SETTINGS' WORKERS=8 MCMC_OBS_CSV='$OBS_CLEAN' MINIMIZE_OBS_CSV='$OBS_FULL' bash '$RUN_SCRIPT' $gammas 2>&1 | tee '$VEGAS_DIR/logs/${queue_label}.log'"
  ssh -o ConnectTimeout=10 "$host" "tmux new-session -d -s '$sess' \"$remote_cmd\""
}

host_cycle_local() {
  local sess="case221009A_ggrid_lyra"
  local queue_label="221009A_casewidegrid_lyra_watch"
  local all=(50)
  local remain=()
  local g
  for g in "${all[@]}"; do
    if ! is_done_local "$g"; then
      remain+=("$g")
    fi
  done

  if [[ "${#remain[@]}" -eq 0 ]]; then
    log "lyra: done"
    return
  fi

  if session_exists_local "$sess"; then
    log "lyra: running session=$sess remaining=${remain[*]}"
  else
    log "lyra: restarting session=$sess remaining=${remain[*]}"
    start_local_queue "$sess" "${remain[*]}" "$queue_label"
  fi
}

host_cycle_remote() {
  local host="$1" sess="$2" queue_label="$3"
  shift 3
  local all=("$@")
  local remain=()
  local g
  for g in "${all[@]}"; do
    if ! is_done_remote "$host" "$g"; then
      remain+=("$g")
    fi
  done

  if [[ "${#remain[@]}" -eq 0 ]]; then
    log "$host: done"
    return
  fi

  if session_exists_remote "$host" "$sess"; then
    log "$host: running session=$sess remaining=${remain[*]}"
  else
    log "$host: restarting session=$sess remaining=${remain[*]}"
    start_remote_queue "$host" "$sess" "${remain[*]}" "$queue_label"
  fi
}

all_done() {
  local g
  local local_all=(50)
  for g in "${local_all[@]}"; do
    is_done_local "$g" || return 1
  done

  local p01=(100 150 200)
  for g in "${p01[@]}"; do
    is_done_remote "pauley404-01" "$g" || return 1
  done

  local p02=(250 300 400)
  for g in "${p02[@]}"; do
    is_done_remote "pauley404-02" "$g" || return 1
  done

  local p03=(600 800 1000)
  for g in "${p03[@]}"; do
    is_done_remote "pauley404-03" "$g" || return 1
  done

  return 0
}

log "watchdog start interval=${INTERVAL_SEC}s"
while true; do
  host_cycle_local
  host_cycle_remote "pauley404-01" "case221009A_ggrid_p01" "221009A_casewidegrid_p01_watch" 100 150 200
  host_cycle_remote "pauley404-02" "case221009A_ggrid_p02" "221009A_casewidegrid_p02_watch" 250 300 400
  host_cycle_remote "pauley404-03" "case221009A_ggrid_p03" "221009A_casewidegrid_p03_watch" 600 800 1000

  if all_done; then
    log "all done; watchdog exit"
    exit 0
  fi

  sleep "$INTERVAL_SEC"
done
