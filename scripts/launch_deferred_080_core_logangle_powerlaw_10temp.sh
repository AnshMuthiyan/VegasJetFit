#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/core_logangle_powerlaw_15grb_10temp_2000_campaign"
MANIFEST="$REPORT/dispatch_manifest.csv"
RUN_TAG="core_logangle_powerlawcsm_unseeded_10temp_2000x2000_v1"
now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if ! grep -q '^080319B,' "$MANIFEST"; then
  echo "080319B,pcrc-mac-studio-1,power_law,14,14,$RUN_TAG,$now" >> "$MANIFEST"
fi
if ! grep -q '^080413B,' "$MANIFEST"; then
  echo "080413B,pcrc-mac-studio-2,power_law,15,14,$RUN_TAG,$now" >> "$MANIFEST"
fi
for h in pcrc-mac-studio-1 pcrc-mac-studio-2; do
  rsync -a "$MANIFEST" "$h:$MANIFEST"
done
ssh -n pcrc-mac-studio-1 "tmux has-session -t core_logangle_powerlaw_10temp_080319B 2>/dev/null || tmux new-session -d -s core_logangle_powerlaw_10temp_080319B 'cd $VJF && env EVENT=080319B WORKERS=14 bash scripts/run_core_logangle_powerlaw_15grb_event.sh'"
ssh -n pcrc-mac-studio-2 "tmux has-session -t core_logangle_powerlaw_10temp_080413B 2>/dev/null || tmux new-session -d -s core_logangle_powerlaw_10temp_080413B 'cd $VJF && env EVENT=080413B WORKERS=14 bash scripts/run_core_logangle_powerlaw_15grb_event.sh'"
echo "deferred_080_launched_utc=$now"
