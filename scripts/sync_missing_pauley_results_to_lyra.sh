#!/usr/bin/env bash
set -euo pipefail

DEST_ROOT="${DEST_ROOT:-/Users/jkeohane/GRBs/VegasJetFit/jetfit/results}"
MANIFEST="${MANIFEST:-/Users/jkeohane/GRBs/VegasJetFit/scripts/missing_pauley_results_manifest.txt}"
LOG_FILE="${LOG_FILE:-/Users/jkeohane/GRBs/VegasJetFit/scripts/sync_missing_pauley_results_to_lyra.log}"

MAX_RETRIES="${MAX_RETRIES:-120}"
SLEEP_SECS="${SLEEP_SECS:-12}"
RSYNC_TIMEOUT="${RSYNC_TIMEOUT:-180}"
RSYNC_BIN="${RSYNC_BIN:-rsync}"
SSH_OPTS="${SSH_OPTS:--o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=20 -o ServerAliveCountMax=3}"
RSYNC_RSH="${RSYNC_RSH:-ssh ${SSH_OPTS}}"

mkdir -p "$DEST_ROOT"
touch "$LOG_FILE"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

run_exists_local() {
  local run="$1"
  [ -d "${DEST_ROOT}/${run}" ]
}

sync_one() {
  local host="$1"
  local run="$2"
  local src="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/${run}/"
  local dst="${DEST_ROOT}/${run}/"

  local try=1
  while [ "$try" -le "$MAX_RETRIES" ]; do
    log "START host=${host} run=${run} try=${try}"

    "$RSYNC_BIN" -az --partial --append --inplace \
      --timeout="$RSYNC_TIMEOUT" \
      -e "$RSYNC_RSH" \
      "$host:$src" "$dst" || true

    # Verify by dry-run: if rsync reports no file deltas, we're done.
    local delta
    delta="$("$RSYNC_BIN" -azn --out-format='%n' \
      --timeout="$RSYNC_TIMEOUT" \
      -e "$RSYNC_RSH" \
      "$host:$src" "$dst" 2>/dev/null | sed '/^$/d' || true)"

    if [ -z "$delta" ] && run_exists_local "$run"; then
      log "DONE host=${host} run=${run}"
      return 0
    fi

    log "RETRY host=${host} run=${run} try=${try}"
    try=$((try + 1))
    sleep "$SLEEP_SECS"
  done

  log "GIVE_UP host=${host} run=${run} retries=${MAX_RETRIES}"
  return 1
}

main() {
  log "=== sync begin ==="
  local fail=0

  if [ "$#" -eq 2 ]; then
    if ! sync_one "$1" "$2"; then
      fail=1
    fi
    if [ "$fail" -eq 0 ]; then
      log "=== sync complete: SUCCESS ==="
    else
      log "=== sync complete: PARTIAL_FAILURE ==="
    fi
    return "$fail"
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac
    local host="${line%%:*}"
    local run="${line#*:}"
    if [ -z "$host" ] || [ -z "$run" ] || [ "$host" = "$run" ]; then
      log "SKIP malformed line: $line"
      continue
    fi
    if ! sync_one "$host" "$run"; then
      fail=1
    fi
  done < "$MANIFEST"

  if [ "$fail" -eq 0 ]; then
    log "=== sync complete: SUCCESS ==="
  else
    log "=== sync complete: PARTIAL_FAILURE ==="
  fi
}

main "$@"
