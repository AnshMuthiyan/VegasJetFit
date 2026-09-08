#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/core_logangle_powerlaw_090424_finalfinal_sthawed_alluv_v2_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_alluv_v2"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_16__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__moderate_resolution__5_temperature_1000x5000"
SESSION="postprocess_090424_finalfinal_alluv_v2"
LOG="$VJF/logs/postprocess_090424_finalfinal_alluv_v2.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "090424 all-UV final-final v2 postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 PRODUCT_WORKERS=8 MINIMIZER_WORKERS=8 MINIMIZER_MAX_WALKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_1000burn_5000run_5temps_alluv_final_seeded_cloud_s_thawed' CAMPAIGN_SUMMARY_TITLE='Final-Final Thawed-s Expanded-Prior Moderate-Resolution Campaign' CAMPAIGN_SUMMARY_PURPOSE='Five-temperature final-final campaign with s thawed. GRB 090424 is the provenance-correct all-UV replacement, initialized from its validated all-UV seeded posterior cloud; early X-ray points remain excluded.' bash '$WATCHER'"
echo "Started 090424 all-UV final-final v2 postprocessor."
