#!/usr/bin/env bash
set -euo pipefail

VJF="/Users/jkeohane/GRBs/VegasJetFit"
REPORT="$VJF/reports/090424_with_early_xray_ssc_kn_final_seeded_10temp_5000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_with_early_xray_ssc_kn_v1"
CAMPAIGN="$VJF/../Share_Folder/Fits/production_runs/final_seeded_runs/26_08_03__core_ejet_gamma_logangles__single_powerlaw_csm__090424_early_xray__ssc_kn__final_seeded__10_temperature_5000x5000"
LOG="$VJF/logs/postprocess_090424_early_xray_ssc_kn_final_seeded.log"
SESSION="postprocess_090424_early_xray_ssc_kn_final_seeded"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

command="cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 PUBLISH_EVENT_SOURCE=090424 PUBLISH_EVENT_NAME=090424_with_early_xray_ssc_kn SAMPLER_LABEL='100walkers_5000burn_5000run_10temps_seeded_allUV_plus_earlyXray_SSC_KN' CAMPAIGN_SUMMARY_TITLE='GRB 090424 Early-X-Ray SSC+KN Seeded Comparison' CAMPAIGN_SUMMARY_PURPOSE='Controlled posterior refit with the same early-X-ray data and seed cloud as the synchrotron-only branch, changing only SSC and Klein-Nishina physics.' bash '$WATCHER'"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux kill-session -t "$SESSION"
fi
tmux new-session -d -s "$SESSION" "$command"
printf 'started_session=%s\nlog=%s\n' "$SESSION" "$LOG"
