#!/usr/bin/env bash
set -euo pipefail
DEST="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results"
RSYNC_BIN="${RSYNC_BIN:-rsync}"
mkdir -p "$DEST"
pull_one() {
  local host="$1"; local g="$2"
  local src="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/221009A_g${g}_gamma0grid_tophat_dylanspec_600x600_v1"
  local tries=0
  while true; do
    tries=$((tries+1))
    echo "[$(date)] pull host=${host} g=${g} try=${tries}"
    if "$RSYNC_BIN" -az --partial --append-verify --timeout=120 --progress "${host}:${src}" "$DEST/"; then
      echo "[$(date)] done host=${host} g=${g}"
      break
    fi
    echo "[$(date)] retry host=${host} g=${g}"
    sleep 10
  done
}
for g in 50 100 150 200 250; do pull_one pauley404-01 "$g"; done
for g in 300 400 600 800 1000; do pull_one pauley404-02 "$g"; done
