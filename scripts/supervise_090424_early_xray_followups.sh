#!/usr/bin/env bash
# Automatically advance the approved GRB 090424 early-X-ray experiment.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
REPORT="$VJF/reports/090424_with_early_xray_followup_seeded_pipeline"
WATCHER="$VJF/scripts/postprocess_core_logangle_powerlaw_15grb_10temp.sh"
POLL_SECONDS="${POLL_SECONDS:-300}"
EVENT="090424"
OBS="$VJF/obs_overrides/090424_early_uvoir_included_with_early_xray.csv"
DECISIONS="$REPORT/event_decision_records.json"

UNSEEDED_TAG="core_logangle_powerlawcsm_kminus10to3_unseeded_10temp_5000x5000_with_early_xray_v1"
SEEDED_TAG="core_logangle_powerlawcsm_kminus10to3_final_seeded_10temp_5000x5000_with_early_xray_v1"
FINAL_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_with_early_xray_v1"

UNSEEDED="$VJF/jetfit/results/${EVENT}_${UNSEEDED_TAG}"
SEEDED="$VJF/jetfit/results/${EVENT}_${SEEDED_TAG}"
SEEDED_CLOUD="$VJF/initial_positions/090424_early_xray_unseeded_final_seeded_10temp.npz"
FINAL_CLOUD="$VJF/initial_positions/090424_early_xray_final_seeded_finalfinal_sthawed_5temp.npz"

SEEDED_REPORT="$REPORT/final_seeded_10temp"
FINAL_REPORT="$REPORT/finalfinal_sthawed_5temp"
SEEDED_CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_07__core_ejet_gamma_logangles__single_powerlaw_csm__kminus10to3__final_seeded__10_temperature_5000x5000"
FINAL_CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_07_16__core_ejet_gamma_logangles__single_powerlaw_csm__finalfinal__s_thawed__expanded_priors__moderate_resolution__5_temperature_1000x5000"

SEEDED_CONFIG="$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_10temp_final_seeded_configs_pending"
SEEDED_MCMC="$VJF/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml"
FINAL_CONFIG="$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_configs_pending"
FINAL_MCMC="$VJF/Ansh_Run/mcmc_settings_core_logangle_finalfinal_sthawed_5temp_1000x5000.toml"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
validated() { [ -s "$1/core_postfit_products.validated" ]; }
launched() {
  [ -s "$1/dispatch_manifest.csv" ] &&
    awk -F, 'NR > 1 && $2 != "" && $2 != "pending" && $2 != "blocked" && $2 != "queued" {found=1} END {exit !found}' \
      "$1/dispatch_manifest.csv"
}

write_stage_files() {
  local dir="$1" tag="$2" workers="$3" note="$4"
  mkdir -p "$dir"
  if [ ! -f "$dir/dynamic_event_queue.csv" ]; then
    printf 'event,csm_family,queue_order,note\n%s,power_law,1,%s\n' "$EVENT" "$note" > "$dir/dynamic_event_queue.csv"
  fi
  if [ ! -f "$dir/dispatch_manifest.csv" ]; then
    printf 'event,host,csm_family,queue_order,workers,run_tag,launched_utc\n%s,pending,power_law,1,%s,%s,\n' "$EVENT" "$workers" "$tag" > "$dir/dispatch_manifest.csv"
  fi
}

ensure_pending_stage_workers() {
  local manifest="$1" workers="$2"
  "$PY" - "$manifest" "$workers" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
workers = sys.argv[2]
rows = list(csv.DictReader(path.open()))
if rows and rows[0]["host"] in {"", "pending", "queued"}:
    rows[0]["workers"] = workers
    with path.with_suffix(".tmp").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    path.with_suffix(".tmp").replace(path)
PY
}

start_postprocess() {
  local session="$1" report="$2" tag="$3" campaign="$4" sampler="$5"
  local log="$VJF/logs/postprocess_${tag}.log"
  local command
  command="cd '$VJF' && exec env MANIFEST='$report/dispatch_manifest.csv' RUN_TAG='$tag' CAMPAIGN='$campaign' LOG='$log' POLL_SECONDS=300 DENSITY_PROFILE_SAMPLES=0 PRODUCT_WORKERS=8 MINIMIZER_MAX_WALKERS=8 MINIMIZER_WORKERS=8 RESOLUTION_CONVERGENCE=1 PUBLISH_EVENT_SOURCE=090424 PUBLISH_EVENT_NAME=090424_with_early_xray SAMPLER_LABEL='$sampler' CAMPAIGN_SUMMARY_TITLE='GRB 090424 Early-X-Ray Comparison' CAMPAIGN_SUMMARY_PURPOSE='Controlled early-X-ray inclusion branch, published separately from canonical GRB 090424.' bash '$WATCHER'"
  tmux has-session -t "$session" 2>/dev/null || tmux new-session -d -s "$session" "$command"
}

dispatch_seeded() {
  "$PY" "$VJF/scripts/dynamic_dispatch_campaign.py" \
    --queue "$SEEDED_REPORT/dynamic_event_queue.csv" \
    --manifest "$SEEDED_REPORT/dispatch_manifest.csv" \
    --run-tag "$SEEDED_TAG" \
    --event-script "$VJF/scripts/run_core_logangle_powerlaw_15grb_event.sh" \
    --results-root "$VJF/jetfit/results" \
    --machines 'pcrc-mac-studio-1:15' --pcrc-workers 15 \
    --session-prefix grb_090424_early_xray_final_seeded \
    --busy-pattern jetfit.run \
    --decision-records "$DECISIONS" \
    --sync-path "$VJF/scripts/run_core_logangle_powerlaw_15grb_event.sh" \
    --sync-path "$VJF/jwk_run_thesis_reproduction_event.sh" \
    --sync-path "$SEEDED_CONFIG" --sync-path "$SEEDED_MCMC" \
    --sync-path "$SEEDED_CLOUD" --sync-path "$OBS" \
    --env "CONFIG_DIR=$SEEDED_CONFIG" --env "MCMC_SETTINGS=$SEEDED_MCMC" \
    --env "INITIAL_POSITIONS=$SEEDED_CLOUD" --env "OBS_CSV_OVERRIDE=$OBS" \
    --env ALLOW_090424_EARLY_XRAY_TEST=1
}

dispatch_final() {
  "$PY" "$VJF/scripts/dynamic_dispatch_campaign.py" \
    --queue "$FINAL_REPORT/dynamic_event_queue.csv" \
    --manifest "$FINAL_REPORT/dispatch_manifest.csv" \
    --run-tag "$FINAL_TAG" \
    --event-script "$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh" \
    --results-root "$VJF/jetfit/results" \
    --machines 'pcrc-mac-studio-1:15' --pcrc-workers 15 \
    --session-prefix grb_090424_early_xray_finalfinal \
    --busy-pattern jetfit.run --decision-records "$DECISIONS" \
    --sync-path "$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh" \
    --sync-path "$VJF/jwk_run_thesis_reproduction_event.sh" \
    --sync-path "$FINAL_CONFIG" --sync-path "$FINAL_MCMC" \
    --sync-path "$FINAL_CLOUD" --sync-path "$OBS" \
    --env "CONFIG_DIR=$FINAL_CONFIG" --env "MCMC_SETTINGS=$FINAL_MCMC" \
    --env "INITIAL_POSITIONS=$FINAL_CLOUD" --env "OBS_CSV_OVERRIDE=$OBS" \
    --env ALLOW_090424_EARLY_XRAY_TEST=1
}

write_stage_files "$SEEDED_REPORT" "$SEEDED_TAG" 15 "automatic_after_validated_unseeded_early_xray_pcrc1"
write_stage_files "$FINAL_REPORT" "$FINAL_TAG" 15 "automatic_after_validated_seeded_early_xray"
ensure_pending_stage_workers "$SEEDED_REPORT/dispatch_manifest.csv" 15
ensure_pending_stage_workers "$FINAL_REPORT/dispatch_manifest.csv" 15

while true; do
  if validated "$UNSEEDED"; then
    if [ ! -s "$SEEDED_CLOUD" ]; then
      "$PY" "$VJF/scripts/build_posterior_informed_initial_positions.py" \
        --source-results "$UNSEEDED" --target-model "$SEEDED_CONFIG/090424.toml" \
        --out "$SEEDED_CLOUD" --ntemps 10 --nwalkers 100 --new-parameter '' --seed 90424
      echo "[$(ts)] seeded_cloud_built=$SEEDED_CLOUD"
    fi
    start_postprocess postprocess_090424_early_xray_final_seeded "$SEEDED_REPORT" "$SEEDED_TAG" "$SEEDED_CAMPAIGN" "100walkers_5000burn_5000run_10temps_seeded_allUV_plus_earlyXray"
    launched "$SEEDED_REPORT" || dispatch_seeded
  fi

  if validated "$SEEDED"; then
    if [ ! -s "$FINAL_CLOUD" ]; then
      "$PY" "$VJF/scripts/build_posterior_informed_initial_positions.py" \
        --source-results "$SEEDED" --target-model "$FINAL_CONFIG/090424.toml" \
        --out "$FINAL_CLOUD" --ntemps 5 --nwalkers 100 --new-parameter s \
        --new-center 4.0 --new-sigma 0.4 --new-lower 0.1 --new-upper 10.0 --seed 90424
      echo "[$(ts)] final_cloud_built=$FINAL_CLOUD"
    fi
    start_postprocess postprocess_090424_early_xray_finalfinal "$FINAL_REPORT" "$FINAL_TAG" "$FINAL_CAMPAIGN" "100walkers_1000burn_5000run_5temps_seeded_allUV_plus_earlyXray_s_thawed"
    launched "$FINAL_REPORT" || dispatch_final
  fi
  sleep "$POLL_SECONDS"
done
