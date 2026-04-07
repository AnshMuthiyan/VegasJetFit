#!/usr/bin/env bash
set -euo pipefail

# Lightweight status logger for the active oscillation review queue.

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RESULTS_DIR="${RESULTS_DIR:-$VEGAS_DIR/jetfit/results}"
INTERVAL_SEC="${INTERVAL_SEC:-900}"
DURATION_HOURS="${DURATION_HOURS:-36}"
OUT_LOG="${OUT_LOG:-$VEGAS_DIR/logs/watch_oscillation_status_$(date -u +%Y%m%dT%H%M%SZ).log}"

mkdir -p "$(dirname "$OUT_LOG")"
end_epoch=$(( $(date +%s) + DURATION_HOURS * 3600 ))

session_running() {
  local name="$1"
  tmux has-session -t "$name" 2>/dev/null
}

load1_value() {
  uptime | awk -F'load averages: ' 'NF > 1 {print $2}' | awk '{print $1}'
}

active_fit_count() {
  ps -Ao command= | awk '
    ($1 ~ /Python|python|caffeinate/) && index($0, "-m jetfit.run") > 0 {count += 1}
    ($1 ~ /Python|python|caffeinate/) && index($0, "/scripts/minimize.py") > 0 {count += 1}
    END {print count + 0}
  '
}

artifact_state() {
  local dir="$1"
  local best=0 chain=0 summary=0
  [ -f "$dir/best_fit.json" ] && best=1
  [ -f "$dir/chain.npz" ] && chain=1
  [ -f "$dir/summary.csv" ] && summary=1
  printf 'best_fit=%s chain=%s summary=%s' "$best" "$chain" "$summary"
}

printf 'watch_start_utc=%s interval_sec=%s duration_hours=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$INTERVAL_SEC" "$DURATION_HOURS" >> "$OUT_LOG"

while [ "$(date +%s)" -lt "$end_epoch" ]; do
  now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '========== %s ==========\n' "$now_utc" >> "$OUT_LOG"
  printf 'load1=%s active_fits=%s\n' "$(load1_value)" "$(active_fit_count)" >> "$OUT_LOG"

  for session in \
    sbpl_080413B_kmin10_fix \
    oscillation_rerun_watch \
    tophat_oscillation_reruns \
    sbpl_oscillation_reruns; do
    if session_running "$session"; then
      printf 'session %-28s RUNNING\n' "$session" >> "$OUT_LOG"
    else
      printf 'session %-28s STOPPED\n' "$session" >> "$OUT_LOG"
    fi
  done

  printf 'result 080413B_current %s dir=%s\n' \
    "$(artifact_state "$RESULTS_DIR/080413B_smoothbroken_thesis_short_kmin10_v1")" \
    "$RESULTS_DIR/080413B_smoothbroken_thesis_short_kmin10_v1" >> "$OUT_LOG"
  printf 'result 111228A_osc     %s dir=%s\n' \
    "$(artifact_state "$RESULTS_DIR/111228A_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_osc_v1")" \
    "$RESULTS_DIR/111228A_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_osc_v1" >> "$OUT_LOG"
  printf 'result 220101A_osc     %s dir=%s\n' \
    "$(artifact_state "$RESULTS_DIR/220101A_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_osc_v1")" \
    "$RESULTS_DIR/220101A_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_osc_v1" >> "$OUT_LOG"
  printf 'result 090618_osc      %s dir=%s\n' \
    "$(artifact_state "$RESULTS_DIR/090618_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_osc_v1")" \
    "$RESULTS_DIR/090618_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_osc_v1" >> "$OUT_LOG"
  printf 'result 080319B_osc     %s dir=%s\n' \
    "$(artifact_state "$RESULTS_DIR/080319B_smoothbroken_thesis_short_kmin10_osc_v1")" \
    "$RESULTS_DIR/080319B_smoothbroken_thesis_short_kmin10_osc_v1" >> "$OUT_LOG"

  printf '\n' >> "$OUT_LOG"
  sleep "$INTERVAL_SEC"
done

printf 'watch_end_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUT_LOG"
