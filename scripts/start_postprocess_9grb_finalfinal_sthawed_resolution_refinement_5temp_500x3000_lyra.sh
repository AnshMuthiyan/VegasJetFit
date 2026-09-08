#!/usr/bin/env bash
# Lyra-only publication for the resource-aware refinement queue.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_resolution_refinement_5temp_500x3000_v1"
REPORT="$VJF/reports/core_logangle_powerlaw_9grb_finalfinal_sthawed_resolution_refinement_5temp_500x3000_campaign"
MANIFEST="$REPORT/dispatch_manifest.csv"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_23__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__resolution_refinement__5_temperature_500x3000"
SESSION="postprocess_9grb_resolution_refinement_lyra"
LOG="$VJF/logs/postprocess_9grb_resolution_refinement_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Resolution-refinement postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs" "$CAMPAIGN"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$MANIFEST' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_500burn_3000run_5temps_full_current_posterior_cloud_resource_aware_resolution_refinement' CAMPAIGN_SUMMARY_TITLE='Final-Final Resolution-Refinement Campaign' CAMPAIGN_SUMMARY_PURPOSE='Posterior-cloud seeded final refinements selected from per-GRB numerical ladders; PCRC serves long CPU-bound work, Pauleys serve routine work, and Lyra is reserved for post-processing or memory placement supported by measurement.' bash '$WATCHER'"
echo "Started resolution-refinement postprocessor: tmux attach -t $SESSION"
