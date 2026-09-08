#!/usr/bin/env bash
# Publish the approved 140506A ultra-fine continuation from Lyra only.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_ultrafine_5temp_500x3000_v2"
REPORT="$VJF/reports/core_logangle_powerlaw_140506A_finalfinal_sthawed_ultrafine_5temp_500x3000_campaign"
MANIFEST="$REPORT/dispatch_manifest.csv"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_22__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__ultrafine_resolution_140506A__5_temperature_500x3000"
SESSION="postprocess_140506A_finalultrafine_500x3000_lyra"
LOG="$VJF/logs/postprocess_140506A_finalultrafine_500x3000_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Ultra-fine postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$MANIFEST' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_500burn_3000run_5temps_full_current_posterior_cloud_ultrafine_resolution_memory_safe_8worker_pcrc' CAMPAIGN_SUMMARY_TITLE='GRB 140506A Ultra-Fine Final-Final Continuation (Memory-Safe Restart)' CAMPAIGN_SUMMARY_PURPOSE='Full current-posterior-cloud seeded ultra-fine numerical continuation selected from the moderate resolution ladder; v2 uses a documented PCRC memory-safe worker cap after a v1 host fault.' bash '$WATCHER'"
echo "Started 140506A ultra-fine postprocessor: tmux attach -t $SESSION"
