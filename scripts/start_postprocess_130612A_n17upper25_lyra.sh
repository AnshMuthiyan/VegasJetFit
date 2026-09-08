#!/usr/bin/env bash
# Pull, validate, publish, and report the GRB 130612A n17-upper25 continuation.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/130612A_n17upper25_posteriorcloud_5temp_1000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_finalfinal_sthawed_n17upper25_5temp_1000x5000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_09_07__130612A__posterior_cloud__n17_upper25__5_temperature_1000x5000"
SESSION="postprocess_130612A_n17upper25_lyra"
LOG="$VJF/logs/postprocess_130612A_n17upper25_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "130612A n17-upper25 postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_1000burn_5000run_5temps_full_cloud_n17_upper25' CAMPAIGN_SUMMARY_TITLE='GRB 130612A n17-Upper25 Continuation' CAMPAIGN_SUMMARY_PURPOSE='Controlled continuation of GRB 130612A, expanding only the log10(n17) upper bound from 15 to 25 because n17 is an extrapolated normalization outside the observed radial range.' bash '$WATCHER'"
echo "Started 130612A n17-upper25 postprocessor: tmux attach -t $SESSION"
