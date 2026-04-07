#!/usr/bin/env bash
set -euo pipefail

# Hourly watchdog for the negative-k bubble triplet.
# - Monitors active MCMC/minimizer processes
# - Restarts primary batch on pending events if needed
# - Runs minimizer on completed runs (one job at a time)
# - Syncs minimized runs to shared Drive
# - Refreshes shared status spreadsheet

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RESULTS_ROOT="${RESULTS_ROOT:-$VEGAS_DIR/jetfit/results}"
RESOURCES_ROOT="${RESOURCES_ROOT:-$VEGAS_DIR/jetfit/resources/grbs}"
LOG_DIR="${LOG_DIR:-$VEGAS_DIR/logs}"

DRIVE_ROOT="${DRIVE_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
OWNER_SUBDIR="${OWNER_SUBDIR:-jkeohane}"

EVENTS="${EVENTS:-080413B 140506A 210905A}"
PRIMARY_RUN_TAG="${PRIMARY_RUN_TAG:-theta1p0_4h_target}"
EXTRA_RUN_TAGS="${EXTRA_RUN_TAGS:-theta1p0_moderate24h}"

MCMC_SETTINGS_PRIMARY="${MCMC_SETTINGS_PRIMARY:-$VEGAS_DIR/Ansh_Run/mcmc_settings_negativek_4h_target.toml}"
MCMC_SETTINGS_MODERATE="${MCMC_SETTINGS_MODERATE:-$VEGAS_DIR/Ansh_Run/mcmc_settings_negativek_moderate_24h.toml}"
WORKERS="${WORKERS:-8}"
JETFIT_POOL_EXECUTOR="${JETFIT_POOL_EXECUTOR:-thread}"

INTERVAL_MIN="${INTERVAL_MIN:-60}"
END_LOCAL="${END_LOCAL:-2026-03-13 17:00:00}"
END_TZ="${END_TZ:-America/New_York}"

TMUX_SESSION="${TMUX_SESSION:-negk_4h_target}"
AUTO_RESTART="${AUTO_RESTART:-1}"
RUN_MINIMIZER="${RUN_MINIMIZER:-1}"
UPDATE_SHEETS="${UPDATE_SHEETS:-1}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
BATCH_SCRIPT="${BATCH_SCRIPT:-$VEGAS_DIR/jwk_run_negativek_bubble_batch.sh}"
MINIMIZE_SCRIPT="${MINIMIZE_SCRIPT:-$VEGAS_DIR/scripts/minimize.py}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$VEGAS_DIR/scripts/sync_results_to_drive.sh}"
SUMMARY_SCRIPT="${SUMMARY_SCRIPT:-$VEGAS_DIR/scripts/update_negativek_bubble_status_sheet.py}"

mkdir -p "$LOG_DIR"
watch_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
WATCH_LOG="${WATCH_LOG:-$LOG_DIR/negativek_watchdog_${watch_stamp}.log}"

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  echo "[$(timestamp_utc)] $*" | tee -a "$WATCH_LOG"
}

run_dir_for() {
  local ev="$1"
  local tag="$2"
  printf "%s/%s_bubble_tophat_%s" "$RESULTS_ROOT" "$ev" "$tag"
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
    local first_csv
    first_csv="$(find "$RESOURCES_ROOT/$ev" -maxdepth 1 -name "*.csv" | head -n 1 || true)"
    printf "%s" "$first_csv"
  fi
}

mcmc_file_for_tag() {
  local tag="$1"
  case "$tag" in
    theta1p0_moderate24h) printf "%s" "$MCMC_SETTINGS_MODERATE" ;;
    *) printf "%s" "$MCMC_SETTINGS_PRIMARY" ;;
  esac
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

print_process_snapshot() {
  log "process_snapshot_begin"
  ps -Ao pid,ppid,pcpu,pmem,etime,command | \
    rg -i "jetfit.run|minimize.py|jwk_run_negativek_bubble_batch|$TMUX_SESSION" | \
    tee -a "$WATCH_LOG" || true
  log "process_snapshot_end"
}

pending_primary_events() {
  local pending=()
  local ev run_dir
  for ev in $EVENTS; do
    run_dir="$(run_dir_for "$ev" "$PRIMARY_RUN_TAG")"
    if [ ! -f "$run_dir/best_fit.json" ]; then
      pending+=("$ev")
    fi
  done
  printf "%s" "${pending[*]-}"
}

start_primary_batch() {
  local pending_events="$1"
  local batch_log="$LOG_DIR/negativek_bubble_${PRIMARY_RUN_TAG}_autoresume_$(date -u +%Y%m%dT%H%M%SZ).log"
  local cmd
  cmd="cd \"$VEGAS_DIR\" && JETFIT_POOL_EXECUTOR=\"$JETFIT_POOL_EXECUTOR\" RUN_MINIMIZER=0 MCMC_SETTINGS=\"$MCMC_SETTINGS_PRIMARY\" RUN_TAG=\"$PRIMARY_RUN_TAG\" GRBS=\"$pending_events\" KEEP_AWAKE=\"$KEEP_AWAKE\" ENABLE_PREFLIGHT=1 PREFLIGHT_BURN_LENGTH=10 PREFLIGHT_RUN_LENGTH=10 RESUME=1 SKIP_COMPLETED=1 CONTINUE_ON_ERROR=1 WORKERS=\"$WORKERS\" bash \"$BATCH_SCRIPT\" 2>&1 | tee \"$batch_log\""
  tmux new-session -d -s "$TMUX_SESSION" "$cmd"
  log "autoresume_started session=$TMUX_SESSION pending=\"$pending_events\" batch_log=$batch_log"
}

maybe_restart_primary() {
  [ "$AUTO_RESTART" = "1" ] || return 0

  local pending
  pending="$(pending_primary_events)"
  if [ -z "$pending" ]; then
    log "primary_status all_events_completed"
    return 0
  fi

  if pgrep -f "jetfit.run .*_bubble_tophat_${PRIMARY_RUN_TAG}" >/dev/null 2>&1; then
    log "primary_status running pending=\"$pending\""
    return 0
  fi

  if tmux has-session -t "$TMUX_SESSION" >/dev/null 2>&1; then
    log "primary_status session_exists_no_active_jetfit pending=\"$pending\""
    return 0
  fi

  start_primary_batch "$pending"
}

maybe_launch_minimizer() {
  [ "$RUN_MINIMIZER" = "1" ] || return 0

  if pgrep -f "$MINIMIZE_SCRIPT" >/dev/null 2>&1; then
    log "minimizer_status already_running"
    return 0
  fi

  local tags="$PRIMARY_RUN_TAG $EXTRA_RUN_TAGS"
  local ev tag run_dir min_json min_log
  for tag in $tags; do
    for ev in $EVENTS; do
      run_dir="$(run_dir_for "$ev" "$tag")"
      min_json="$run_dir/minimized/minimized.json"
      if [ ! -f "$run_dir/best_fit.json" ] || [ ! -f "$run_dir/chain.npz" ]; then
        continue
      fi
      if [ -f "$min_json" ]; then
        continue
      fi
      mkdir -p "$run_dir/minimized"
      min_log="$LOG_DIR/${ev}.bubble.${tag}.watch.minimize.log"
      log "minimizer_launch event=$ev run_tag=$tag run_dir=$run_dir log=$min_log"
      if [ "$KEEP_AWAKE" = "1" ] && command -v caffeinate >/dev/null 2>&1; then
        PYTHONPATH="$VEGAS_DIR" caffeinate -is "$PYTHON_BIN" "$MINIMIZE_SCRIPT" \
          --results "$run_dir" \
          --mode walkers \
          --minimizer minimize \
          > "$min_log" 2>&1 &
      else
        PYTHONPATH="$VEGAS_DIR" "$PYTHON_BIN" "$MINIMIZE_SCRIPT" \
          --results "$run_dir" \
          --mode walkers \
          --minimizer minimize \
          > "$min_log" 2>&1 &
      fi
      log "minimizer_pid=$! event=$ev run_tag=$tag"
      return 0
    done
  done

  log "minimizer_status no_candidates"
}

maybe_sync_completed() {
  local tags="$PRIMARY_RUN_TAG $EXTRA_RUN_TAGS"
  local ev tag run_dir dest_dir mcmc_file model_file obs_file log_file

  for tag in $tags; do
    for ev in $EVENTS; do
      run_dir="$(run_dir_for "$ev" "$tag")"
      if [ ! -f "$run_dir/minimized/minimized.json" ]; then
        continue
      fi

      dest_dir="$DRIVE_ROOT/$ev/$OWNER_SUBDIR/$(basename "$run_dir")"
      if [ -f "$dest_dir/minimized/minimized.json" ] && [ -f "$dest_dir/sync_manifest.txt" ]; then
        continue
      fi

      mcmc_file="$(mcmc_file_for_tag "$tag")"
      model_file="$LOG_DIR/${ev}.parameters_bubble_theta1.0.synced.toml"
      obs_file="$(obs_file_for "$ev")"
      log_file="$LOG_DIR/${ev}.bubble.log"

      if [ ! -d "$run_dir" ]; then
        continue
      fi

      if out="$("$SYNC_SCRIPT" \
        --results-dir "$run_dir" \
        --event "$ev" \
        --drive-root "$DRIVE_ROOT" \
        --owner-subdir "$OWNER_SUBDIR" \
        --run-label "$(basename "$run_dir")" \
        --log-file "$log_file" \
        --mcmc-file "$mcmc_file" \
        --model-file "$model_file" \
        --obs-file "$obs_file" 2>&1)"; then
        log "sync_ok event=$ev run_tag=$tag dest=$out"
      else
        log "sync_error event=$ev run_tag=$tag detail=$(printf '%q' "$out")"
      fi
    done
  done
}

update_sheet_files() {
  [ "$UPDATE_SHEETS" = "1" ] || return 0
  local output_csv="$DRIVE_ROOT/NegativeK_Bubble_Run_Status.csv"
  local output_xlsx="$DRIVE_ROOT/NegativeK_Bubble_Run_Status.xlsx"
  local tags="$PRIMARY_RUN_TAG $EXTRA_RUN_TAGS"

  if out="$("$PYTHON_BIN" "$SUMMARY_SCRIPT" \
    --vegas-dir "$VEGAS_DIR" \
    --drive-root "$DRIVE_ROOT" \
    --owner-subdir "$OWNER_SUBDIR" \
    --events $EVENTS \
    --run-tags $tags \
    --output-csv "$output_csv" \
    --output-xlsx "$output_xlsx" 2>&1)"; then
    log "sheet_update_ok csv=$output_csv xlsx=$output_xlsx"
  else
    log "sheet_update_error detail=$(printf '%q' "$out")"
  fi
}

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: Python not executable: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -x "$SYNC_SCRIPT" ]; then
  echo "ERROR: Sync script not executable: $SYNC_SCRIPT" >&2
  exit 2
fi
if [ ! -f "$MINIMIZE_SCRIPT" ]; then
  echo "ERROR: Minimize script not found: $MINIMIZE_SCRIPT" >&2
  exit 2
fi
if [ ! -f "$SUMMARY_SCRIPT" ]; then
  echo "ERROR: Summary script not found: $SUMMARY_SCRIPT" >&2
  exit 2
fi
if [ ! -f "$BATCH_SCRIPT" ]; then
  echo "ERROR: Batch script not found: $BATCH_SCRIPT" >&2
  exit 2
fi

if ! end_epoch="$(to_epoch_local "$END_LOCAL" "$END_TZ")"; then
  echo "ERROR: could not parse END_LOCAL='$END_LOCAL' with TZ '$END_TZ'" >&2
  exit 2
fi

log "watchdog_start"
log "config events=\"$EVENTS\" primary_run_tag=$PRIMARY_RUN_TAG extra_run_tags=\"$EXTRA_RUN_TAGS\" interval_min=$INTERVAL_MIN end_local=\"$END_LOCAL\" end_tz=$END_TZ end_epoch=$end_epoch"
log "log_file=$WATCH_LOG"

run_cycle() {
  log "cycle_begin"
  print_process_snapshot
  maybe_restart_primary
  maybe_launch_minimizer
  maybe_sync_completed
  update_sheet_files
  log "cycle_end"
}

run_cycle
while [ "$(date +%s)" -lt "$end_epoch" ]; do
  sleep "$((INTERVAL_MIN * 60))"
  run_cycle
done

log "watchdog_end"
