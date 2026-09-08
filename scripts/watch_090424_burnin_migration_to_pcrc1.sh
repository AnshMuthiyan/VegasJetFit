#!/usr/bin/env bash
# Migrate the 090424 all-UV intermediate fit only after burn-in is durable.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="090424"
SOURCE_HOST="pauley404-01"
DESTINATION_HOST="pcrc-mac-studio-1"
SOURCE_WORKERS=8
DESTINATION_WORKERS=15
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_final_seeded_alluv_10temp_5000x5000_v2"
RESULT_NAME="${EVENT}_${RUN_TAG}"
RESULTS_ROOT="$VJF/jetfit/results"
SOURCE_RESULTS="$RESULTS_ROOT/$RESULT_NAME"
MANIFEST="$VJF/reports/090424_core_logangle_powerlaw_kminus10to3_final_seeded_alluv_10temp_5000x5000_campaign/dispatch_manifest.csv"
RUNNER="$VJF/scripts/run_core_logangle_powerlaw_15grb_event.sh"
SESSION="grb_090424_alluv_seeded_090424"
MIGRATED_SESSION="${SESSION}_migrated"
LOG="$VJF/logs/090424_burnin_migration_to_pcrc1.log"
POLL_SECONDS="${POLL_SECONDS:-300}"

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
  remote "$SOURCE_HOST" "/Users/jkeohane/GRBs/.venv/bin/python -c \"import os, numpy as np; p='$SOURCE_RESULTS/pt_resume_state.npz'; s=os.stat(p); d=np.load(p, allow_pickle=True); print(d['phase'].item(), d['completed_iterations'].item(), d['target_iterations'].item(), d['burn_completed_iterations'].item() if 'burn_completed_iterations' in d else -1, d['burn_target_iterations'].item() if 'burn_target_iterations' in d else -1, s.st_size, s.st_mtime_ns)\""
}

copy_checkpoint_to_destination() {
  local production_iteration="$1"
  local stage
  stage="$(mktemp -d "$VJF/tmp.090424_checkpoint.XXXXXX")"
  trap 'rm -rf "$stage"' RETURN
  log "copy_start destination=$DESTINATION_HOST production_iteration=$production_iteration"
  rsync -az --partial --append-verify -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" \
    "$SOURCE_HOST:$SOURCE_RESULTS/" "$stage/"
  rsync -az --partial --append-verify -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" \
    "$stage/" "$DESTINATION_HOST:$SOURCE_RESULTS/"
  remote "$DESTINATION_HOST" "/Users/jkeohane/GRBs/.venv/bin/python -c \"import numpy as np; d=np.load('$SOURCE_RESULTS/pt_resume_state.npz', allow_pickle=True); assert d['phase'].item() == 'production'; assert d['completed_iterations'].item() >= $production_iteration; print('checkpoint_verified', d['completed_iterations'].item())\"" >/dev/null
  rm -rf "$stage"
  trap - RETURN
  log "copy_verified destination=$DESTINATION_HOST production_iteration=$production_iteration"
}

update_manifest() {
  local host="$1" workers="$2"
  /Users/jkeohane/GRBs/.venv/bin/python -c "import csv; from datetime import datetime, timezone; from pathlib import Path; path=Path('$MANIFEST'); rows=list(csv.DictReader(path.open())); fields=list(rows[0]); row=next(r for r in rows if r['event']=='$EVENT'); row['host']='$host'; row['workers']='$workers'; row['launched_utc']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'); temp=path.with_suffix('.tmp'); h=temp.open('w', newline=''); w=csv.DictWriter(h, fieldnames=fields); w.writeheader(); w.writerows(rows); h.close(); temp.replace(path)"
  rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12" "$MANIFEST" "$DESTINATION_HOST:$MANIFEST"
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

start_destination() {
  local command
  command="cd '$VJF' && EVENT='$EVENT' WORKERS='$DESTINATION_WORKERS' RUN_TAG='$RUN_TAG' DISPATCH_MANIFEST='$MANIFEST' CONFIG_DIR='$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending' MCMC_SETTINGS='$VJF/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml' INITIAL_POSITIONS='$VJF/initial_positions/090424_alluv_unseeded_final_seeded_10temp.npz' OBS_CSV_OVERRIDE='$VJF/obs_overrides/090424_early_uvoir_included_no_early_xray.csv' RESUME=1 CLEAN_INCOMPLETE=0 ENABLE_PREFLIGHT=0 SKIP_COMPLETED=1 bash '$RUNNER'"
  remote "$DESTINATION_HOST" "tmux new-session -d -s '$MIGRATED_SESSION' \"$command\""
  sleep 15
  remote "$DESTINATION_HOST" "ps -axo command | grep '[j]etfit.run' | grep -F -- '--event $EVENT' | grep -F '$RUN_TAG' >/dev/null"
  log "destination_running host=$DESTINATION_HOST workers=$DESTINATION_WORKERS"
}

restart_source() {
  update_manifest "$SOURCE_HOST" "$SOURCE_WORKERS"
  local command
  command="cd '$VJF' && EVENT='$EVENT' WORKERS='$SOURCE_WORKERS' RUN_TAG='$RUN_TAG' DISPATCH_MANIFEST='$MANIFEST' CONFIG_DIR='$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending' MCMC_SETTINGS='$VJF/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml' INITIAL_POSITIONS='$VJF/initial_positions/090424_alluv_unseeded_final_seeded_10temp.npz' OBS_CSV_OVERRIDE='$VJF/obs_overrides/090424_early_uvoir_included_no_early_xray.csv' RESUME=1 CLEAN_INCOMPLETE=0 ENABLE_PREFLIGHT=0 SKIP_COMPLETED=1 bash '$RUNNER'"
  remote "$SOURCE_HOST" "tmux new-session -d -s '$SESSION' \"$command\""
  sleep 15
  source_running
  log "source_resumed_after_destination_failure host=$SOURCE_HOST"
}

last_signature=""
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
  # Phase changes to production only after the 5,000-step burn-in is saved.
  if [[ "$phase" != "production" ]]; then
    log "waiting_for_burnin phase=$phase burn=$burn_completed/$burn_target"
    sleep "$POLL_SECONDS"
    continue
  fi
  signature="$phase:$completed:$size:$mtime_ns"
  if [[ "$signature" != "$last_signature" ]]; then
    last_signature="$signature"
    log "production_checkpoint_seen completed=$completed/$target; waiting_one_poll_for_stability"
    sleep "$POLL_SECONDS"
    continue
  fi
  if ! destination_idle; then
    log "production_checkpoint_ready completed=$completed/$target; pcrc1_busy"
    last_signature=""
    sleep "$POLL_SECONDS"
    continue
  fi
  copy_checkpoint_to_destination "$completed"
  stop_source
  update_manifest "$DESTINATION_HOST" "$DESTINATION_WORKERS"
  if start_destination; then
    log "migration_complete source=$SOURCE_HOST destination=$DESTINATION_HOST production_iteration=$completed"
    exit 0
  fi
  log "ERROR destination_start_failed; attempting_source_recovery"
  restart_source
  exit 2
done
