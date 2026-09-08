#!/usr/bin/env bash
# Move the active 090618 final-final MCMC only at a verified checkpoint.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="090618"
SOURCE_HOST="pauley404-02"
PCRC_HOSTS=(pcrc-mac-studio-1 pcrc-mac-studio-2)
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_v2"
# PCRC has 16 logical CPUs; reserve one for macOS after migration.
WORKERS="${PCRC_WORKERS:-15}"
RESULT_NAME="${EVENT}_${RUN_TAG}"
RESULTS_ROOT="$VJF/jetfit/results"
SOURCE_RESULTS="$RESULTS_ROOT/$RESULT_NAME"
MANIFEST="$VJF/reports/core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_1000x5000_campaign/dispatch_manifest.csv"
RUNNER="$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh"
LOG="$VJF/logs/090618_checkpoint_migration_to_pcrc.log"
POLL_SECONDS="${POLL_SECONDS:-300}"

SSH=(ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12)

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { printf '[%s] %s\n' "$(ts)" "$*" | tee -a "$LOG"; }

remote() {
  local host="$1"
  shift
  "${SSH[@]}" "$host" "$@"
}

source_running() {
  remote "$SOURCE_HOST" "ps -axo command | grep '[j]etfit.run' | grep -F -- '--event $EVENT' | grep -F '$RUN_TAG' >/dev/null"
}

pcrc_idle_host() {
  local host
  for host in "${PCRC_HOSTS[@]}"; do
    if ! remote "$host" "true"; then
      continue
    fi
    # A PCRC host is available only when no fit is running.  Matching this
    # event's run tag alone allowed 090618 to share a host with another MCMC.
    if remote "$host" "ps -axo command | grep '[j]etfit.run' >/dev/null"; then
      continue
    fi
    printf '%s\n' "$host"
    return 0
  done
  return 1
}

checkpoint_info() {
  remote "$SOURCE_HOST" "/Users/jkeohane/GRBs/.venv/bin/python -c \"import os, numpy as np; p='$SOURCE_RESULTS/pt_resume_state.npz'; s=os.stat(p); d=np.load(p, allow_pickle=True); print(d['phase'].item(), d['completed_iterations'].item(), d['target_iterations'].item(), s.st_size, s.st_mtime_ns)\""
}

verify_destination_checkpoint() {
  local host="$1" expected_iteration="$2"
  remote "$host" "/Users/jkeohane/GRBs/.venv/bin/python -c \"import numpy as np; p=np.load('$SOURCE_RESULTS/pt_resume_state.npz', allow_pickle=True); assert p['completed_iterations'].item() >= $expected_iteration; print(p['phase'].item(), p['completed_iterations'].item(), p['target_iterations'].item())\""
}

copy_checkpoint_to() {
  local destination="$1" iteration="$2"
  local stage
  stage="$(mktemp -d "$VJF/tmp.090618_checkpoint.XXXXXX")"
  trap 'rm -rf "$stage"' RETURN
  log "copy_start destination=$destination checkpoint_iteration=$iteration"
  rsync -az --partial --append-verify -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" \
    "$SOURCE_HOST:$SOURCE_RESULTS/" "$stage/"
  rsync -az --partial --append-verify -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" \
    "$stage/" "$destination:$SOURCE_RESULTS/"
  verify_destination_checkpoint "$destination" "$iteration" >/dev/null
  rm -rf "$stage"
  trap - RETURN
  log "copy_verified destination=$destination checkpoint_iteration=$iteration"
}

stop_source() {
  local attempt
  log "stopping_source host=$SOURCE_HOST"
  remote "$SOURCE_HOST" "tmux kill-session -t grb_finalfinal_$EVENT 2>/dev/null || true"
  for attempt in {1..12}; do
    if ! source_running; then
      log "source_stopped host=$SOURCE_HOST"
      return 0
    fi
    sleep 5
  done
  log "ERROR source_job_did_not_stop host=$SOURCE_HOST"
  return 1
}

start_destination() {
  local destination="$1"
  local session="grb_finalfinal_${EVENT}_migrated"
  local command
  command="cd '$VJF' && EVENT='$EVENT' WORKERS='$WORKERS' RUN_TAG='$RUN_TAG' RESUME=1 CLEAN_INCOMPLETE=0 ENABLE_PREFLIGHT=0 SKIP_COMPLETED=1 bash '$RUNNER'"
  remote "$destination" "tmux new-session -d -s '$session' \"$command\""
  sleep 12
  remote "$destination" "ps -axo command | grep '[j]etfit.run' | grep -F -- '--event $EVENT' | grep -F '$RUN_TAG' >/dev/null"
  log "destination_running host=$destination session=$session"
}

restart_source() {
  local command
  command="cd '$VJF' && EVENT='$EVENT' WORKERS='$WORKERS' RUN_TAG='$RUN_TAG' RESUME=1 CLEAN_INCOMPLETE=0 ENABLE_PREFLIGHT=0 SKIP_COMPLETED=1 bash '$RUNNER'"
  remote "$SOURCE_HOST" "tmux new-session -d -s 'grb_finalfinal_$EVENT' \"$command\""
  sleep 12
  source_running
  log "source_resumed_after_destination_failure host=$SOURCE_HOST"
}

update_manifest() {
  local destination="$1"
  /Users/jkeohane/GRBs/.venv/bin/python -c "import csv; from datetime import datetime, timezone; from pathlib import Path; path=Path('$MANIFEST'); rows=list(csv.DictReader(path.open())); fields=list(rows[0]); row=next(r for r in rows if r['event']=='$EVENT'); row['host']='$destination'; row['workers']='$WORKERS'; row['launched_utc']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'); temp=path.with_suffix('.tmp'); handle=temp.open('w', newline=''); writer=csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows); handle.close(); temp.replace(path)"
  log "manifest_updated event=$EVENT host=$destination workers=$WORKERS"
}

last_signature=""
while true; do
  if ! source_running; then
    log "source_not_running; exiting without migration"
    exit 1
  fi

  if ! info="$(checkpoint_info 2>/dev/null)"; then
    log "checkpoint_unavailable; retry_in=${POLL_SECONDS}s"
    sleep "$POLL_SECONDS"
    continue
  fi
  read -r phase completed target size mtime_ns <<<"$info"
  signature="$phase:$completed:$size:$mtime_ns"
  if [[ "$phase" != "burn" && "$phase" != "production" ]] || (( completed < 100 )); then
    log "waiting_for_first_full_checkpoint phase=$phase completed=$completed/$target"
    sleep "$POLL_SECONDS"
    continue
  fi
  if [[ "$signature" == "$last_signature" ]]; then
    log "checkpoint_stable phase=$phase completed=$completed/$target"
  else
    last_signature="$signature"
    log "checkpoint_seen phase=$phase completed=$completed/$target; waiting_one_poll_for_stability"
    sleep "$POLL_SECONDS"
    continue
  fi

  if ! destination="$(pcrc_idle_host 2>/dev/null)"; then
    log "checkpoint_ready completed=$completed/$target; no_idle_pcrc; waiting_for_next_checkpoint"
    last_signature=""
    sleep "$POLL_SECONDS"
    continue
  fi

  copy_checkpoint_to "$destination" "$completed"
  stop_source
  if start_destination "$destination"; then
    update_manifest "$destination"
    log "migration_complete event=$EVENT source=$SOURCE_HOST destination=$destination checkpoint_iteration=$completed"
    exit 0
  fi

  log "ERROR destination_start_failed host=$destination; attempting_source_recovery"
  if restart_source; then
    exit 2
  fi
  log "ERROR source_recovery_failed host=$SOURCE_HOST; manual_intervention_required"
  exit 3
done
