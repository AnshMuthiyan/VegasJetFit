#!/usr/bin/env bash
# Pull, validate, publish, and report authoritative n17-boundary follow-ups.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/26_09_04__authoritative_n17_upper15_followups"
RUN_TAG="core_logangle_powerlawcsm_finalfinal_sthawed_n17upper15_audit_5temp_1000x5000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_09_04__authoritative_n17_upper15__posterior_cloud__5_temperature_1000x5000"
SESSION="postprocess_authoritative_n17upper15_lyra"
LOG="$VJF/logs/postprocess_authoritative_n17upper15_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Authoritative n17 postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_1000burn_5000run_5temps_posterior_cloud_n17_upper15_audit' CAMPAIGN_SUMMARY_TITLE='Authoritative n17 Upper-Bound Follow-ups' CAMPAIGN_SUMMARY_PURPOSE='Controlled posterior-cloud sensitivity refits for authoritative GRBs whose retained n17 posteriors approach the former upper limit of 10. Each event preserves its authoritative data, model, special priors, and numerical grid while expanding only log10(n17) to an upper limit of 15.' bash '$WATCHER'"
echo "Started authoritative n17 postprocessor: tmux attach -t $SESSION"
