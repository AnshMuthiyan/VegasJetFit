#!/usr/bin/env bash
# Pull, validate, publish, and report the GRB 080319B all-UVOIR refit on Lyra.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/080319B_alluvoir_n17upper15_posteriorcloud_5temp_1000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_alluvoir_n17upper15_5temp_1000x5000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_09_04__080319B__all_early_uvoir__posterior_cloud__n17_upper15__5_temperature_1000x5000"
SESSION="postprocess_080319B_alluvoir_n17upper15_lyra"
LOG="$VJF/logs/postprocess_080319B_alluvoir_n17upper15_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "080319B all-UVOIR postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_1000burn_5000run_5temps_posterior_cloud_all_uvoir_n17_upper15' CAMPAIGN_SUMMARY_TITLE='GRB 080319B All-UVOIR Posterior-Cloud Refit' CAMPAIGN_SUMMARY_PURPOSE='Controlled refit of GRB 080319B with all 113 previously excluded UVOIR observations restored, using the completed expanded-n17 posterior cloud and otherwise unchanged model, priors, grid, and sampler.' bash '$WATCHER'"
echo "Started 080319B all-UVOIR postprocessor: tmux attach -t $SESSION"
