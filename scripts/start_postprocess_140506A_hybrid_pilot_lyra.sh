#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/core_logangle_powerlaw_140506A_finalfinal_sthawed_hybrid_5temp_25x100_pilot_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_hybrid_5temp_25x100_pilot_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_08_01__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__hybrid_resolution_140506A__5_temperature_25x100_pilot"
SESSION="postprocess_140506A_hybrid_pilot_lyra"
LOG="$VJF/logs/postprocess_140506A_hybrid_pilot_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 PRODUCT_WORKERS=8 MINIMIZER_WORKERS=8 MINIMIZER_MAX_WALKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_25burn_100run_5temps_hybrid_resolution_pilot' CAMPAIGN_SUMMARY_TITLE='GRB 140506A Hybrid Resolution Pilot' CAMPAIGN_SUMMARY_PURPOSE='Short posterior-cloud-seeded pilot at phi=0.20, theta=1.00, time=30; intended to evaluate numerical behavior, not final uncertainty bars.' bash '$WATCHER'"
echo "watcher_session=$SESSION"
