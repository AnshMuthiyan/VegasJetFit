#!/usr/bin/env bash
# Watch and publish the controlled GRB 090424 early-X-ray inclusion test.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/090424_core_logangle_powerlaw_kminus10to3_unseeded_10temp_5000x5000_with_early_xray_test_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_with_early_xray_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/unseeded_runs/26_06_29__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__unseeded__10_temperature_5000x5000"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"
LOG="$VJF/logs/postprocess_090424_early_xray_unseeded_test.log"
SESSION="postprocess_090424_early_xray_test"

command="cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 PUBLISH_EVENT_SOURCE=090424 PUBLISH_EVENT_NAME=090424_with_early_xray SAMPLER_LABEL='100walkers_5000burn_5000run_10temps_unseeded_allUV_plus_earlyXray_test' CAMPAIGN_SUMMARY_TITLE='June 29 Unseeded Campaign with GRB 090424 Early-X-Ray Test' CAMPAIGN_SUMMARY_PURPOSE='Controlled GRB 090424 comparison retaining all UVOT/UVOIR data and adding the early X-ray sequence labelled as flare.' bash '$WATCHER'"

tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" "$command"
echo "watcher_session=$SESSION"
