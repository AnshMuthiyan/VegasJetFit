#!/usr/bin/env bash
# Pull, validate, publish, and report the GRB 080319B expanded-n17 refit on Lyra.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
REPORT="$VJF/reports/080319B_n17upper15_posteriorcloud_5temp_1000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_n17upper15_5temp_1000x5000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_09_01__080319B__posterior_cloud__n17_upper15__5_temperature_1000x5000"
SESSION="postprocess_080319B_n17upper15_lyra"
LOG="$VJF/logs/postprocess_080319B_n17upper15_lyra.log"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "080319B n17-upper15 postprocessor is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
tmux new-session -d -s "$SESSION" \
  "cd '$VJF' && exec env MANIFEST='$REPORT/dispatch_manifest.csv' RUN_TAG='$RUN_TAG' CAMPAIGN='$CAMPAIGN' LOG='$LOG' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 SAMPLER_LABEL='100walkers_1000burn_5000run_5temps_posterior_cloud_n17_upper15' CAMPAIGN_SUMMARY_TITLE='GRB 080319B Expanded-n17 Posterior-Cloud Refit' CAMPAIGN_SUMMARY_PURPOSE='Controlled refit of the authoritative 080319B solution with the event-specific log10 n17 upper prior expanded from 10 to 15 because the 10^17 cm normalization is extrapolated beyond the observed radial profile.' bash '$WATCHER'"
echo "Started 080319B n17-upper15 postprocessor: tmux attach -t $SESSION"
