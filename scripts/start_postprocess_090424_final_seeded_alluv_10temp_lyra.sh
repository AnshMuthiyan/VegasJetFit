#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/090424_core_logangle_powerlaw_kminus10to3_final_seeded_alluv_10temp_5000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_final_seeded_alluv_10temp_5000x5000_v2"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_07__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__final_seeded__10_temperature_5000x5000"
SESSION="postprocess_090424_final_seeded_alluv_lyra"
LOG="$VJF/logs/postprocess_090424_final_seeded_alluv_10temp_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "090424 all-UV seeded postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 PRODUCT_WORKERS=8 MINIMIZER_WORKERS=8 MINIMIZER_MAX_WALKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_5000burn_5000run_10temps_alluv_unseeded_cloud_seed' CAMPAIGN_SUMMARY_TITLE='GRB 090424 All-UV Seeded Replacement' CAMPAIGN_SUMMARY_PURPOSE='Corrected 10-temperature seeded replacement, initialized from the validated all-UV unseeded posterior and retaining all approved UVOT/UVOIR observations.' bash '$WATCHER'"
echo "Started 090424 all-UV seeded postprocessor."
