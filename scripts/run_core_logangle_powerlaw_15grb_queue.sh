#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
WORKERS="${WORKERS:-8}"
EVENTS="${EVENTS:?set space-separated EVENTS}"
QUEUE_LOG="${QUEUE_LOG:-$VJF/logs/core_logangle_powerlaw_15grb_10temp_queue.log}"

mkdir -p "$(dirname "$QUEUE_LOG")"
exec > >(tee -a "$QUEUE_LOG") 2>&1

echo "queue_start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "host=$(hostname)"
echo "workers=$WORKERS"
echo "events=$EVENTS"

for event in $EVENTS; do
  echo "event_start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) event=$event"
  EVENT="$event" WORKERS="$WORKERS" \
    /bin/bash "$VJF/scripts/run_core_logangle_powerlaw_15grb_event.sh"
  echo "event_done_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) event=$event"
done

echo "queue_done_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
