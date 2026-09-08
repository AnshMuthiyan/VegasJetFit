#!/usr/bin/env bash
set -euo pipefail
DEST="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results"
LOG="/Users/jkeohane/GRBs/VegasJetFit/scripts/pull_recent_gamma0_grids_robust.log"
RSYNC_BIN="${RSYNC_BIN:-rsync}"
mkdir -p "$DEST"
: > "$LOG"
log(){ echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
pull_one(){
  local host="$1" run="$2"
  local src="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/${run}/"
  local dst="$DEST/${run}/"
  local n=0
  while true; do
    n=$((n+1))
    log "START host=$host run=$run try=$n"
    if "$RSYNC_BIN" -az --partial --append --inplace --timeout=180 --contimeout=20 "$host:$src" "$dst"; then
      local req_ok=1
      for f in model.toml obs.csv mcmc_settings.toml chain.npz summary.csv minimized/minimized.json; do
        [ -s "$dst/$f" ] || { req_ok=0; log "MISSING run=$run file=$f"; }
      done
      if [ "$req_ok" -eq 1 ]; then
        log "DONE run=$run"
        return 0
      fi
    else
      log "RSYNC_FAIL host=$host run=$run"
    fi
    sleep 12
  done
}
for g in 50 100 200 400 800; do pull_one pauley404-01 "050922C_g${g}_gamma0grid_tophat_dylanspec_300x300_v1"; done
for g in 50 100 200 400 800; do pull_one pauley404-02 "130612A_g${g}_gamma0grid_tophat_dylanspec_300x300_v1"; done
log "ALL_DONE"
