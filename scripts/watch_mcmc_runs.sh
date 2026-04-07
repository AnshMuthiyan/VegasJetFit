#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs/VegasJetFit}"
MONITOR_SCRIPT="${MONITOR_SCRIPT:-$ROOT/scripts/monitor_mcmc_runs.sh}"
INTERVAL_MIN="${INTERVAL_MIN:-15}"
DURATION_HOURS="${DURATION_HOURS:-48}"
EVENT_FILTER="${EVENT_FILTER:-}"
OUT_LOG="${OUT_LOG:-$ROOT/logs/mcmc_monitor_$(date -u +%Y%m%dT%H%M%SZ).log}"

mkdir -p "$(dirname "$OUT_LOG")"

end_epoch=$(( $(date +%s) + DURATION_HOURS * 3600 ))

echo "watch_start_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$OUT_LOG"
echo "interval_min=$INTERVAL_MIN duration_hours=$DURATION_HOURS event_filter=${EVENT_FILTER:-all}" >> "$OUT_LOG"
echo "monitor_script=$MONITOR_SCRIPT" >> "$OUT_LOG"
echo >> "$OUT_LOG"

while [ "$(date +%s)" -lt "$end_epoch" ]; do
  echo "========== $(date -u +"%Y-%m-%dT%H:%M:%SZ") ==========" >> "$OUT_LOG"
  if [ -n "$EVENT_FILTER" ]; then
    if "$MONITOR_SCRIPT" --event "$EVENT_FILTER" >> "$OUT_LOG" 2>&1; then
      :
    else
      echo "ALERT: monitor reported an issue." >> "$OUT_LOG"
      /usr/bin/osascript -e 'display notification "MCMC monitor found an issue. Check the monitor log." with title "VegasJetFit Monitor"' >/dev/null 2>&1 || true
    fi
  else
    if "$MONITOR_SCRIPT" >> "$OUT_LOG" 2>&1; then
      :
    else
      echo "ALERT: monitor reported an issue." >> "$OUT_LOG"
      /usr/bin/osascript -e 'display notification "MCMC monitor found an issue. Check the monitor log." with title "VegasJetFit Monitor"' >/dev/null 2>&1 || true
    fi
  fi
  echo >> "$OUT_LOG"
  sleep "$((INTERVAL_MIN * 60))"
done

echo "watch_end_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$OUT_LOG"

