#!/usr/bin/env bash
# Restart one final-final MCMC at a verified durable checkpoint with more workers.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="${EVENT:?set EVENT}"
SOURCE_HOST="${SOURCE_HOST:?set SOURCE_HOST}"
TARGET_WORKERS="${TARGET_WORKERS:-15}"
FALLBACK_WORKERS="${FALLBACK_WORKERS:-8}"
RUN_TAG="${RUN_TAG:-core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_v2}"
POLL_SECONDS="${POLL_SECONDS:-300}"
RESULTS="$VJF/jetfit/results/${EVENT}_${RUN_TAG}"
RUNNER="$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh"
MANIFEST="$VJF/reports/core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_1000x5000_campaign/dispatch_manifest.csv"
SESSION="grb_finalfinal_${EVENT}"
LOG="${LOG:-$VJF/logs/${EVENT}_checkpoint_worker_resize.log}"
SSH=(ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12)

mkdir -p "$(dirname "$LOG")"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG"
}

remote() {
  "${SSH[@]}" "$SOURCE_HOST" "$1"
}

source_running() {
  remote "ps -axo command | grep '[j]etfit.run' | grep -F -- '--event $EVENT' | grep -F '$RUN_TAG' >/dev/null"
}

checkpoint_info() {
  remote "/Users/jkeohane/GRBs/.venv/bin/python -c \"import os, numpy as np; p='$RESULTS/pt_resume_state.npz'; s=os.stat(p); d=np.load(p, allow_pickle=True); print(d['phase'].item(), d['completed_iterations'].item(), d['target_iterations'].item(), s.st_size, s.st_mtime_ns)\""
}

verify_checkpoint() {
  local minimum_iteration="$1"
  remote "/Users/jkeohane/GRBs/.venv/bin/python -c \"import numpy as np; d=np.load('$RESULTS/pt_resume_state.npz', allow_pickle=True); assert d['completed_iterations'].item() >= $minimum_iteration; print(d['phase'].item(), d['completed_iterations'].item(), d['target_iterations'].item())\""
}

stop_source() {
  local attempt
  log "stopping source host=$SOURCE_HOST session=$SESSION"
  remote "tmux kill-session -t '$SESSION' 2>/dev/null || true"
  for attempt in {1..12}; do
    if ! source_running; then
      log "source stopped host=$SOURCE_HOST"
      return 0
    fi
    sleep 5
  done
  log "ERROR source process did not stop"
  return 1
}

start_source() {
  local workers="$1"
  local command
  command="cd '$VJF' && EVENT='$EVENT' WORKERS='$workers' RUN_TAG='$RUN_TAG' RESUME=1 CLEAN_INCOMPLETE=0 ENABLE_PREFLIGHT=0 SKIP_COMPLETED=1 bash '$RUNNER'"
  remote "tmux new-session -d -s '$SESSION' \"$command\""
  sleep 15
  source_running
  log "resumed host=$SOURCE_HOST workers=$workers session=$SESSION"
}

update_manifest_workers() {
  /Users/jkeohane/GRBs/.venv/bin/python -c "import csv; from pathlib import Path; p=Path('$MANIFEST'); rows=list(csv.DictReader(p.open())); fields=list(rows[0]); row=next(r for r in rows if r['event']=='$EVENT'); row['workers']='$TARGET_WORKERS'; tmp=p.with_suffix('.tmp'); f=tmp.open('w', newline=''); w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows); f.close(); tmp.replace(p)"
}

last_signature=""
while true; do
  if ! source_running; then
    log "source no longer running; exiting without resize"
    exit 1
  fi
  if ! info="$(checkpoint_info 2>/dev/null)"; then
    log "checkpoint unavailable; retry_in=${POLL_SECONDS}s"
    sleep "$POLL_SECONDS"
    continue
  fi
  read -r phase completed target size mtime_ns <<<"$info"
  signature="$phase:$completed:$size:$mtime_ns"
  if [[ "$phase" != "burn" && "$phase" != "production" ]] || (( completed < 100 )); then
    log "waiting for a full checkpoint phase=$phase completed=$completed/$target"
    sleep "$POLL_SECONDS"
    continue
  fi
  if [[ "$signature" != "$last_signature" ]]; then
    last_signature="$signature"
    log "checkpoint seen phase=$phase completed=$completed/$target; waiting one poll for stability"
    sleep "$POLL_SECONDS"
    continue
  fi

  log "checkpoint stable phase=$phase completed=$completed/$target; resizing to workers=$TARGET_WORKERS"
  if ! stop_source; then
    exit 2
  fi
  if start_source "$TARGET_WORKERS" && verify_checkpoint "$completed" >/dev/null; then
    update_manifest_workers
    log "resize complete event=$EVENT checkpoint_iteration=$completed workers=$TARGET_WORKERS"
    exit 0
  fi

  log "ERROR target-worker resume failed; attempting safe fallback workers=$FALLBACK_WORKERS"
  if start_source "$FALLBACK_WORKERS" && verify_checkpoint "$completed" >/dev/null; then
    log "fallback resume complete; manifest remains workers=$FALLBACK_WORKERS"
    exit 3
  fi
  log "ERROR fallback resume failed; manual intervention required"
  exit 4
done
