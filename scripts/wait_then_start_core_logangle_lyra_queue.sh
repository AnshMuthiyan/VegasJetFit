#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
POLL_SECONDS="${POLL_SECONDS:-60}"

while pgrep -f "scripts/minimize.py|scripts/generate_postfit_products.py" >/dev/null 2>&1; do
  echo "waiting_for_lyra_postfit_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sleep "$POLL_SECONDS"
done

cd "$VJF"
EVENTS="171010A 210905A" \
WORKERS=8 \
QUEUE_LOG="$VJF/logs/core_logangle_15grb_lyra.log" \
exec /bin/bash "$VJF/scripts/run_core_logangle_15grb_queue.sh"
