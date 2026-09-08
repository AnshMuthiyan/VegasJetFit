#!/usr/bin/env bash
set -euo pipefail

# Robust pull of the 221009A fixed-Gamma0 grid from Pauley hosts to Lyra.
# Features:
# - Resumable rsync transfers with append-verify
# - Retry loop with backoff on network failures
# - Per-run verification against remote chain.npz byte size
# - Idempotent: safe to re-run repeatedly

DEST_ROOT="${DEST_ROOT:-/Users/jkeohane/GRBs/VegasJetFit/jetfit/results}"
LOG_FILE="${LOG_FILE:-/Users/jkeohane/GRBs/VegasJetFit/scripts/pull_gamma0_grid_to_lyra_robust.log}"
RUN_TAG="${RUN_TAG:-gamma0grid_tophat_dylanspec_600x600_v1}"

MAX_RETRIES="${MAX_RETRIES:-120}"
SLEEP_SECS="${SLEEP_SECS:-15}"
RSYNC_TIMEOUT="${RSYNC_TIMEOUT:-180}"
RSYNC_CONTIMEOUT="${RSYNC_CONTIMEOUT:-20}"

mkdir -p "$DEST_ROOT"
touch "$LOG_FILE"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

remote_size() {
  local host="$1"
  local path="$2"
  ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" "stat -f%z '$path'" 2>/dev/null || true
}

local_size() {
  local path="$1"
  stat -f%z "$path" 2>/dev/null || true
}

pull_one() {
  local host="$1"
  local gamma="$2"
  local run_dir="221009A_g${gamma}_${RUN_TAG}"
  local src="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/${run_dir}/"
  local dst="${DEST_ROOT}/${run_dir}/"

  local try=1
  while [ "$try" -le "$MAX_RETRIES" ]; do
    log "START host=${host} gamma=${gamma} try=${try}"

    if rsync -az \
      --partial --append --inplace \
      --timeout="$RSYNC_TIMEOUT" --contimeout="$RSYNC_CONTIMEOUT" \
      "$host:$src" "$dst"; then
      # Basic required files for a successful run transfer.
      local ok=1
      for req in model.toml obs.csv mcmc_settings.toml chain.npz summary.csv; do
        if [ ! -s "${dst}${req}" ]; then
          log "MISSING host=${host} gamma=${gamma} file=${req}"
          ok=0
        fi
      done

      # Verify chain.npz size matches remote.
      local rsize lsize
      rsize="$(remote_size "$host" "${src}chain.npz")"
      lsize="$(local_size "${dst}chain.npz")"
      if [ -z "$rsize" ] || [ -z "$lsize" ] || [ "$rsize" != "$lsize" ]; then
        log "SIZE_MISMATCH host=${host} gamma=${gamma} remote=${rsize:-NA} local=${lsize:-NA}"
        ok=0
      fi

      if [ "$ok" -eq 1 ]; then
        log "DONE host=${host} gamma=${gamma}"
        return 0
      fi
    else
      log "RSYNC_FAIL host=${host} gamma=${gamma} try=${try}"
    fi

    try=$((try + 1))
    sleep "$SLEEP_SECS"
  done

  log "GIVE_UP host=${host} gamma=${gamma} retries=${MAX_RETRIES}"
  return 1
}

main() {
  log "=== robust pull begin ==="
  local fail=0

  for g in 50 100 150 200 250; do
    if ! pull_one "pauley404-01" "$g"; then
      fail=1
    fi
  done

  for g in 300 400 600 800 1000; do
    if ! pull_one "pauley404-02" "$g"; then
      fail=1
    fi
  done

  if [ "$fail" -eq 0 ]; then
    log "=== robust pull complete: SUCCESS ==="
  else
    log "=== robust pull complete: PARTIAL_FAILURE ==="
  fi
}

main "$@"
