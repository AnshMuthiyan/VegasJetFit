#!/usr/bin/env bash
# Start only the Lyra-owned watcher; MCMC dispatch remains a separate action.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
SESSION="postprocess_core_logangle_finalfinal_sthawed_5temp_1000x5000_lyra"
MANIFEST="$VJF/reports/core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_1000x5000_campaign/dispatch_manifest.csv"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_16__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__moderate_resolution__5_temperature_1000x5000"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_v2"
LOG="$VJF/logs/postprocess_core_logangle_finalfinal_sthawed_5temp_1000x5000_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Lyra final-final postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$CAMPAIGN" "$VJF/logs"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$MANIFEST' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_1000burn_5000run_5temps_posterior_cloud_thawed_s_moderate_resolution' CAMPAIGN_SUMMARY_TITLE='Final-Final Thawed-s Expanded-Prior Campaign' CAMPAIGN_SUMMARY_PURPOSE='Posterior-cloud-seeded final robustness sampling with s thawed, expanded priors, and moderate VegasAfterglow resolution.' bash '$WATCHER'"

echo "Started Lyra-owned final-final postprocessor: tmux attach -t $SESSION"
echo "Campaign destination: $CAMPAIGN"
