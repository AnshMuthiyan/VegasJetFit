#!/usr/bin/env bash
# Publish the isolated 221009A fine-resolution continuation from Lyra only.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_fine_5temp_500x3000_v1"
REPORT="$VJF/reports/core_logangle_powerlaw_221009A_finalfinal_sthawed_fine_5temp_500x3000_campaign"
MANIFEST="$REPORT/dispatch_manifest.csv"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_20__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__fine_resolution__5_temperature_500x3000"
SESSION="postprocess_221009A_finalfine_500x3000_lyra"
LOG="$VJF/logs/postprocess_221009A_finalfine_500x3000_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Fine-resolution postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$MANIFEST' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_500burn_3000run_5temps_posterior_cloud_fine_resolution' CAMPAIGN_SUMMARY_TITLE='GRB 221009A Fine-Resolution Final-Final Continuation' CAMPAIGN_SUMMARY_PURPOSE='Full posterior-cloud seeded resolution refinement at the measured next coupled VegasAfterglow grid.' bash '$WATCHER'"
echo "Started 221009A fine-resolution postprocessor: tmux attach -t $SESSION"
