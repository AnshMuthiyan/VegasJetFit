#!/usr/bin/env bash
# Low-priority historical corner refresh, followed by campaign-book rebuilds.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
LOG="$VJF/logs/backfill_prior_bound_corners_and_meeting_books.log"

cd "$VJF"
export PYTHONPATH="$VJF${PYTHONPATH:+:$PYTHONPATH}"

nice -n 15 "$PY" scripts/replot_corners_with_gamma.py \
  --root "$ROOT/Share_Folder/Fits/production_runs" >> "$LOG" 2>&1

while IFS= read -r campaign; do
  nice -n 15 "$PY" scripts/write_campaign_latex_summary.py \
    --campaign "$campaign" >> "$LOG" 2>&1
done < <(find "$ROOT/Share_Folder/Fits/production_runs" \
  -path '*/trash/*' -prune -o -name campaign_meeting_summary.pdf -print | sort | xargs -n1 dirname)

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] prior_bound_corner_backfill_done" >> "$LOG"
