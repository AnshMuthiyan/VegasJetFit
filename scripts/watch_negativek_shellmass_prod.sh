#!/usr/bin/env bash
set -euo pipefail

# Production watchdog for the negative-k bubble triplet using the
# shell-mass-matched bubble profile.
#
# Responsibilities:
# - Keep the 3 target GRBs running (restart with RESUME=1 if needed)
# - Sync completed minimized outputs to shared Drive
# - Refresh status CSV/XLSX in Drive hourly

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RESULTS_ROOT="${RESULTS_ROOT:-$VEGAS_DIR/jetfit/results}"
RESOURCES_ROOT="${RESOURCES_ROOT:-$VEGAS_DIR/jetfit/resources/grbs}"
LOG_DIR="${LOG_DIR:-$VEGAS_DIR/logs}"
PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

DRIVE_ROOT="${DRIVE_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
OWNER_SUBDIR="${OWNER_SUBDIR:-jkeohane}"

EVENTS="${EVENTS:-080413B 140506A 210905A}"
RUN_TAG="${RUN_TAG:-theta1p0_thesis_full_shellmass_v1}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_thesis_full.toml}"
WORKERS="${WORKERS:-3}"
JETFIT_POOL_EXECUTOR="${JETFIT_POOL_EXECUTOR:-thread}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"

INTERVAL_MIN="${INTERVAL_MIN:-60}"
END_LOCAL="${END_LOCAL:-2026-03-13 17:00:00}"
END_TZ="${END_TZ:-America/New_York}"

SESSION_PREFIX="${SESSION_PREFIX:-negk_prod_shellmass}"
RUN_MINIMIZER="${RUN_MINIMIZER:-1}"
SYNC_TO_DRIVE="${SYNC_TO_DRIVE:-1}"
UPDATE_SHEETS="${UPDATE_SHEETS:-1}"

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
BATCH_SCRIPT="${BATCH_SCRIPT:-$VEGAS_DIR/jwk_run_negativek_bubble_batch.sh}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$VEGAS_DIR/scripts/sync_results_to_drive.sh}"
SUMMARY_SCRIPT="${SUMMARY_SCRIPT:-$VEGAS_DIR/scripts/update_negativek_bubble_status_sheet.py}"
TMUX_BIN="${TMUX_BIN:-$(command -v tmux || true)}"

mkdir -p "$LOG_DIR"
watch_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
WATCH_LOG="${WATCH_LOG:-$LOG_DIR/negativek_shellmass_prod_watch_${watch_stamp}.log}"

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  echo "[$(timestamp_utc)] $*" | tee -a "$WATCH_LOG"
}

run_dir_for() {
  local ev="$1"
  printf "%s/%s_bubble_tophat_%s" "$RESULTS_ROOT" "$ev" "$RUN_TAG"
}

session_for() {
  local ev="$1"
  printf "%s_%s" "$SESSION_PREFIX" "$ev"
}

obs_file_for() {
  local ev="$1"
  local p1="$RESOURCES_ROOT/$ev/$ev.csv"
  local p2="$RESOURCES_ROOT/$ev/${ev}clean.csv"
  if [ -f "$p1" ]; then
    printf "%s" "$p1"
  elif [ -f "$p2" ]; then
    printf "%s" "$p2"
  else
    find "$RESOURCES_ROOT/$ev" -maxdepth 1 -name "*.csv" | head -n 1 || true
  fi
}

to_epoch_local() {
  local local_time="$1"
  local tz_name="$2"
  if TZ="$tz_name" date -j -f "%Y-%m-%d %H:%M:%S" "$local_time" "+%s" >/dev/null 2>&1; then
    TZ="$tz_name" date -j -f "%Y-%m-%d %H:%M:%S" "$local_time" "+%s"
    return 0
  fi
  if TZ="$tz_name" date -d "$local_time" "+%s" >/dev/null 2>&1; then
    TZ="$tz_name" date -d "$local_time" "+%s"
    return 0
  fi
  return 1
}

is_done() {
  local ev="$1"
  local run_dir
  run_dir="$(run_dir_for "$ev")"
  [ -f "$run_dir/best_fit.json" ] && \
    [ -f "$run_dir/chain.npz" ] && \
    [ -f "$run_dir/minimized/minimized.json" ]
}

is_running() {
  local ev="$1"
  local run_dir
  run_dir="$(run_dir_for "$ev")"

  # During preflight, results path is "${event}_bubble_preflight" (no RUN_TAG),
  # so event-based matching is more robust than run-tag matching.
  if pgrep -f "jetfit.run --event $ev" >/dev/null 2>&1; then
    return 0
  fi

  # Keep the watchdog from relaunching while the post-fit minimizer is active.
  pgrep -f "minimize.py.*${run_dir}" >/dev/null 2>&1
}

resume_mode_for() {
  local ev="$1"
  local run_dir checkpoint
  run_dir="$(run_dir_for "$ev")"
  checkpoint="$run_dir/pt_resume_state.npz"
  if [ -f "$checkpoint" ]; then
    printf "1"
  else
    printf "0"
  fi
}

cleanup_dead_session() {
  local ev="$1"
  local sess dead
  sess="$(session_for "$ev")"
  if ! tmux has-session -t "$sess" >/dev/null 2>&1; then
    return 0
  fi
  dead="$(tmux list-panes -t "$sess" -F '#{pane_dead}' 2>/dev/null | head -n 1 || true)"
  if [ "$dead" = "1" ]; then
    "$TMUX_BIN" kill-session -t "$sess" || true
    log "killed_dead_session event=$ev session=$sess"
  fi
}

start_event() {
  local ev="$1"
  local sess run_log cmd resume_mode
  sess="$(session_for "$ev")"
  run_log="$LOG_DIR/${ev}.bubble.${RUN_TAG}.auto_$(date -u +%Y%m%dT%H%M%SZ).log"
  resume_mode="$(resume_mode_for "$ev")"

  if is_running "$ev"; then
    return 0
  fi

  cleanup_dead_session "$ev"
  if "$TMUX_BIN" has-session -t "$sess" >/dev/null 2>&1; then
    log "session_exists event=$ev session=$sess (leaving as-is)"
    return 0
  fi

  cmd="cd '$VEGAS_DIR' && JETFIT_POOL_EXECUTOR='$JETFIT_POOL_EXECUTOR' RUN_MINIMIZER='$RUN_MINIMIZER' DRIVE_SYNC_ENABLE='$SYNC_TO_DRIVE' MCMC_SETTINGS='$MCMC_SETTINGS' RUN_TAG='$RUN_TAG' GRBS='$ev' KEEP_AWAKE='$KEEP_AWAKE' ENABLE_PREFLIGHT=1 PREFLIGHT_BURN_LENGTH=10 PREFLIGHT_RUN_LENGTH=10 RESUME='$resume_mode' SKIP_COMPLETED=1 CONTINUE_ON_ERROR=1 WORKERS='$WORKERS' bash '$BATCH_SCRIPT' 2>&1 | tee '$run_log'"
  "$TMUX_BIN" new-session -d -s "$sess" "$cmd"
  log "started_event event=$ev session=$sess workers=$WORKERS resume=$resume_mode run_tag=$RUN_TAG log=$run_log"
}

maybe_sync_event() {
  local ev="$1"
  local run_dir dest_dir model_file obs_file log_file out
  [ "$SYNC_TO_DRIVE" = "1" ] || return 0
  run_dir="$(run_dir_for "$ev")"

  if [ ! -f "$run_dir/minimized/minimized.json" ]; then
    return 0
  fi

  dest_dir="$DRIVE_ROOT/$ev/$OWNER_SUBDIR/$(basename "$run_dir")"
  if [ -f "$dest_dir/minimized/minimized.json" ] && [ -f "$dest_dir/sync_manifest.txt" ]; then
    return 0
  fi

  model_file="$LOG_DIR/${ev}.parameters_bubble_theta1.0.synced.toml"
  obs_file="$(obs_file_for "$ev")"
  log_file="$LOG_DIR/${ev}.bubble.log"

  if out="$("$SYNC_SCRIPT" \
      --results-dir "$run_dir" \
      --event "$ev" \
      --drive-root "$DRIVE_ROOT" \
      --owner-subdir "$OWNER_SUBDIR" \
      --run-label "$(basename "$run_dir")" \
      --log-file "$log_file" \
      --mcmc-file "$MCMC_SETTINGS" \
      --model-file "$model_file" \
      --obs-file "$obs_file" 2>&1)"; then
    log "sync_ok event=$ev dest=$out"
  else
    log "sync_error event=$ev detail=$(printf '%q' "$out")"
  fi
}

update_sheet_files() {
  [ "$UPDATE_SHEETS" = "1" ] || return 0
  local output_csv="$DRIVE_ROOT/NegativeK_Bubble_Run_Status.csv"
  local output_xlsx="$DRIVE_ROOT/NegativeK_Bubble_Run_Status.xlsx"
  local out
  if out="$("$PYTHON_BIN" "$SUMMARY_SCRIPT" \
      --vegas-dir "$VEGAS_DIR" \
      --drive-root "$DRIVE_ROOT" \
      --owner-subdir "$OWNER_SUBDIR" \
      --events $EVENTS \
      --run-tags "$RUN_TAG" \
      --output-csv "$output_csv" \
      --output-xlsx "$output_xlsx" 2>&1)"; then
    log "sheet_update_ok csv=$output_csv xlsx=$output_xlsx"
  else
    log "sheet_update_error detail=$(printf '%q' "$out")"
  fi
}

cycle() {
  local ev
  log "cycle_begin"
  for ev in $EVENTS; do
    cleanup_dead_session "$ev"
    if is_done "$ev"; then
      log "event_done event=$ev run_tag=$RUN_TAG"
    elif is_running "$ev"; then
      log "event_running event=$ev run_tag=$RUN_TAG"
    else
      log "event_not_running event=$ev run_tag=$RUN_TAG restarting=1"
      start_event "$ev"
    fi
    maybe_sync_event "$ev"
  done
  update_sheet_files
  log "cycle_end"
}

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: Python not executable: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -x "$TMUX_BIN" ]; then
  echo "ERROR: tmux not executable: $TMUX_BIN" >&2
  exit 2
fi
if [ ! -f "$BATCH_SCRIPT" ]; then
  echo "ERROR: Batch script not found: $BATCH_SCRIPT" >&2
  exit 2
fi
if [ ! -x "$SYNC_SCRIPT" ]; then
  echo "ERROR: Sync script not executable: $SYNC_SCRIPT" >&2
  exit 2
fi
if [ ! -f "$SUMMARY_SCRIPT" ]; then
  echo "ERROR: Summary script not found: $SUMMARY_SCRIPT" >&2
  exit 2
fi
if ! end_epoch="$(to_epoch_local "$END_LOCAL" "$END_TZ")"; then
  echo "ERROR: could not parse END_LOCAL='$END_LOCAL' with TZ '$END_TZ'" >&2
  exit 2
fi

log "watchdog_start"
log "config events=\"$EVENTS\" run_tag=$RUN_TAG workers=$WORKERS interval_min=$INTERVAL_MIN end_local=\"$END_LOCAL\" end_tz=$END_TZ run_minimizer=$RUN_MINIMIZER sync_to_drive=$SYNC_TO_DRIVE update_sheets=$UPDATE_SHEETS"
log "watch_log=$WATCH_LOG"

cycle
while [ "$(date +%s)" -lt "$end_epoch" ]; do
  sleep "$((INTERVAL_MIN * 60))"
  cycle
done

log "watchdog_end"
