#!/usr/bin/env bash
# Move the controlled 090424 early-X-ray fit after its durable burn-in only.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="090424"
SOURCE_HOST="pauley404-01"
DESTINATION_HOST="pcrc-mac-studio-1"
SOURCE_WORKERS=8
DESTINATION_WORKERS=15
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_with_early_xray_v1"
RESULT_NAME="${EVENT}_${RUN_TAG}"
SOURCE_RESULTS="$VJF/jetfit/results/$RESULT_NAME"
MANIFEST="$VJF/reports/090424_core_logangle_powerlaw_kminus10to3_unseeded_10temp_5000x5000_with_early_xray_test_campaign/dispatch_manifest.csv"
RUNNER="$VJF/scripts/run_core_logangle_powerlaw_15grb_event.sh"
SESSION="grb_090424_early_xray_test_090424"
MIGRATED_SESSION="${SESSION}_migrated"
LOG="$VJF/logs/090424_early_xray_burnin_migration_to_pcrc1.log"
POLL_SECONDS="${POLL_SECONDS:-120}"

SSH=(ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12)
ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { printf '[%s] %s\n' "$(ts)" "$*" | tee -a "$LOG"; }
remote() { local host="$1"; shift; "${SSH[@]}" "$host" "$@"; }

source_running() {
  remote "$SOURCE_HOST" "ps -axo command | grep '[j]etfit.run' | grep -F -- '--event $EVENT' | grep -F '$RUN_TAG' >/dev/null"
}
destination_idle() {
  remote "$DESTINATION_HOST" "! ps -axo command | grep '[j]etfit.run' >/dev/null"
}
checkpoint_info() {
  remote "$SOURCE_HOST" "/Users/jkeohane/GRBs/.venv/bin/python -c \"import os, numpy as np; p='$SOURCE_RESULTS/pt_resume_state.npz'; s=os.stat(p); d=np.load(p, allow_pickle=True); phase=d['phase'].item(); burn_completed=d['burn_completed_iterations'].item() if 'burn_completed_iterations' in d else (5000 if phase == 'production' else -1); burn_target=d['burn_target_iterations'].item() if 'burn_target_iterations' in d else (5000 if phase == 'production' else -1); print(phase, d['completed_iterations'].item(), d['target_iterations'].item(), burn_completed, burn_target, s.st_size, s.st_mtime_ns)\""
}
update_manifest() {
  local host="$1" workers="$2"
  /Users/jkeohane/GRBs/.venv/bin/python -c "import csv; from datetime import datetime, timezone; from pathlib import Path; path=Path('$MANIFEST'); rows=list(csv.DictReader(path.open())); fields=list(rows[0]); row=next(r for r in rows if r['event']=='$EVENT'); row['host']='$host'; row['workers']='$workers'; row['launched_utc']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'); temp=path.with_suffix('.tmp'); h=temp.open('w', newline=''); w=csv.DictWriter(h, fieldnames=fields); w.writeheader(); w.writerows(rows); h.close(); temp.replace(path)"
  remote "$host" "mkdir -p '$(dirname "$MANIFEST")'"
  rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" "$MANIFEST" "$host:$MANIFEST"
  log "manifest_updated host=$host workers=$workers"
}
stop_source() {
  remote "$SOURCE_HOST" "tmux kill-session -t '$SESSION' 2>/dev/null || true"
  for _ in {1..12}; do
    if ! source_running; then
      log "source_stopped host=$SOURCE_HOST"
      return 0
    fi
    sleep 5
  done
  log "ERROR source_job_did_not_stop host=$SOURCE_HOST"
  return 1
}
copy_checkpoint() {
  local stage
  stage="$(mktemp -d "$VJF/tmp.090424_early_xray_checkpoint.XXXXXX")"
  trap 'rm -rf "$stage"' RETURN
  rsync -az --partial --append-verify -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" "$SOURCE_HOST:$SOURCE_RESULTS/" "$stage/"
  rsync -az --partial --append-verify -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" "$stage/" "$DESTINATION_HOST:$SOURCE_RESULTS/"
  remote "$DESTINATION_HOST" "/Users/jkeohane/GRBs/.venv/bin/python -c \"import numpy as np; d=np.load('$SOURCE_RESULTS/pt_resume_state.npz', allow_pickle=True); assert d['phase'].item() == 'production'; assert d['completed_iterations'].item() >= 0; assert ('burn_completed_iterations' not in d) or (d['burn_completed_iterations'].item() == d['burn_target_iterations'].item() == 5000); print('checkpoint_verified', d['completed_iterations'].item())\""
  rm -rf "$stage"
  trap - RETURN
  log "copy_verified destination=$DESTINATION_HOST"
}
start_host() {
  local host="$1" workers="$2" session="$3"
  local command
  command="cd '$VJF' && EVENT='$EVENT' WORKERS='$workers' RUN_TAG='$RUN_TAG' DISPATCH_MANIFEST='$MANIFEST' CONFIG_DIR='$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_configs_active' MCMC_SETTINGS='$VJF/Ansh_Run/mcmc_settings_core_logangle_kminus10to3_10temp_5000x5000.toml' OBS_CSV_OVERRIDE='$VJF/obs_overrides/090424_early_uvoir_included_with_early_xray.csv' ALLOW_090424_EARLY_XRAY_TEST=1 RESUME=1 CLEAN_INCOMPLETE=0 ENABLE_PREFLIGHT=0 SKIP_COMPLETED=1 bash '$RUNNER'"
  remote "$host" "tmux new-session -d -s '$session' \"$command\""
  sleep 15
  remote "$host" "ps -axo command | grep '[j]etfit.run' | grep -F -- '--event $EVENT' | grep -F '$RUN_TAG' >/dev/null"
  log "destination_running host=$host workers=$workers"
}

while true; do
  if ! source_running; then
    log "source_not_running; exiting_without_migration"
    exit 1
  fi
  if ! info="$(checkpoint_info 2>/dev/null)"; then
    log "checkpoint_unavailable retry_in=${POLL_SECONDS}s"
    sleep "$POLL_SECONDS"
    continue
  fi
  read -r phase completed target burn_completed burn_target size mtime_ns <<<"$info"
  if [ "$phase" != "production" ] || [ "$burn_completed" -lt "$burn_target" ]; then
    log "waiting_for_burnin phase=$phase burn=$burn_completed/$burn_target"
    sleep "$POLL_SECONDS"
    continue
  fi
  if ! destination_idle; then
    log "burnin_complete pcrc1_busy; leaving_source_running"
    sleep "$POLL_SECONDS"
    continue
  fi
  log "burnin_complete production=$completed/$target; migrating_to_pcrc1"
  stop_source
  if ! copy_checkpoint; then
    log "ERROR copy_failed; restoring_source"
    update_manifest "$SOURCE_HOST" "$SOURCE_WORKERS"
    start_host "$SOURCE_HOST" "$SOURCE_WORKERS" "$SESSION"
    exit 2
  fi
  update_manifest "$DESTINATION_HOST" "$DESTINATION_WORKERS"
  if start_host "$DESTINATION_HOST" "$DESTINATION_WORKERS" "$MIGRATED_SESSION"; then
    log "migration_complete source=$SOURCE_HOST destination=$DESTINATION_HOST production_iteration=$completed"
    exit 0
  fi
  log "ERROR destination_start_failed; restoring_source"
  update_manifest "$SOURCE_HOST" "$SOURCE_WORKERS"
  start_host "$SOURCE_HOST" "$SOURCE_WORKERS" "$SESSION"
  exit 3
done
