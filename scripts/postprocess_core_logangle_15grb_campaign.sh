#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
MANIFEST="$VJF/reports/core_logangle_15grb_campaign/dispatch_manifest.csv"
RUN_TAG="core_logangle_unseeded_5temp_2000x2000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/unseeded_runs/26_06_25__core_ejet_gamma_logangles__mixed_powerlaw_and_sbpl_csm__unseeded__5_temperature_2000x2000"
TODO_FILE="$ROOT/Share_Folder/Things_to_do/Unseeded GRB Run with new parameters and Ranges #.md"
COMPLETED_DIR="$ROOT/Share_Folder/Things_to_do/completed"
LOG="$VJF/logs/postprocess_core_logangle_15grb_campaign.log"
POLL_SECONDS="${POLL_SECONDS:-300}"
# Zero requests every terminal cold-chain walker; see density_profile_sampling.json.
DENSITY_PROFILE_SAMPLES="${DENSITY_PROFILE_SAMPLES:-0}"

export JETFIT_DENSITY_PROFILE_SAMPLES="$DENSITY_PROFILE_SAMPLES"

mkdir -p "$CAMPAIGN" "$VJF/logs"
exec > >(tee -a "$LOG") 2>&1

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
lyra_mcmc_busy() {
  pgrep -f "core_logangle_15grb_queue|core_logangle_unseeded_5temp_2000x2000" >/dev/null 2>&1
}
lyra_postfit_busy() {
  pgrep -f "scripts/minimize.py|scripts/generate_postfit_products.py" >/dev/null 2>&1
}
remote_complete() {
  local host="$1" remote="$2"
  ssh -n -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "test -s '$remote/chain.npz' -a -s '$remote/best_fit.json' && ! ps -axo command | grep '[j]etfit.run' | grep -F '$remote' >/dev/null"
}
local_complete() {
  local local_dir="$1"
  test -s "$local_dir/chain.npz" -a -s "$local_dir/best_fit.json" &&
    ! ps -axo command | grep '[j]etfit.run' | grep -F "$local_dir" >/dev/null
}
all_published() {
  local count
  count="$(find "$CAMPAIGN" -mindepth 2 -maxdepth 2 -name core_postfit_products.validated -not -path '*/trash/*' | wc -l | tr -d ' ')"
  test "$count" -eq 15
}

echo "[$(ts)] watcher_start campaign=$CAMPAIGN"
while ! all_published; do
  progress=0
  while IFS=, read -r event host family order workers; do
    [ "$event" = "event" ] && continue
    run="${event}_${RUN_TAG}"
    local_dir="$VJF/jetfit/results/$run"
    dest="$CAMPAIGN/$event"
    [ -e "$dest/core_postfit_products.validated" ] && continue

    ready=0
    if [ "$host" = "lyra" ]; then
      local_complete "$local_dir" && ready=1
    else
      remote="$VJF/jetfit/results/$run"
      if remote_complete "$host" "$remote"; then
        mkdir -p "$local_dir"
        echo "[$(ts)] pull_start event=$event host=$host"
        rsync -a --partial "$host:$remote/" "$local_dir/"
        echo "[$(ts)] pull_done event=$event host=$host"
        ready=1
      fi
    fi
    [ "$ready" -eq 1 ] || continue

    while lyra_mcmc_busy || lyra_postfit_busy; do
      echo "[$(ts)] lyra_busy event=$event sleep=$POLL_SECONDS"
      sleep "$POLL_SECONDS"
    done

    if [ ! -s "$local_dir/minimized/minimized.json" ]; then
      echo "[$(ts)] minimize_start event=$event max_walkers=8 workers=8"
      "$PY" "$VJF/scripts/minimize.py" \
        --results "$local_dir" \
        --obs "$local_dir/obs.csv" \
        --params "$local_dir/model.toml" \
        --mode walkers \
        --max-walkers 8 \
        --parallel-workers 8 \
        --scipy-method Powell \
        --fallback-scipy-method Nelder-Mead
      echo "[$(ts)] minimize_done event=$event"
    fi

    echo "[$(ts)] postfit_start event=$event"
    "$PY" "$VJF/scripts/generate_postfit_products.py" \
      --results "$local_dir" \
      --event "$event" \
      --parallel-products \
      --product-workers 4
    "$PY" "$VJF/scripts/validate_core_postfit_products.py" --results "$local_dir"
    printf 'validated_utc=%s\nevent=%s\n' "$(ts)" "$event" > "$local_dir/core_postfit_products.validated"
    printf 'done_utc=%s\nevent=%s\n' "$(ts)" "$event" > "$local_dir/postfit_products.done"
    mkdir -p "$dest"
    rsync -a --delete --exclude='trash/' "$local_dir/" "$dest/"
    "$PY" "$VJF/scripts/validate_core_postfit_products.py" --results "$dest"
    printf 'validated_utc=%s\nevent=%s\n' "$(ts)" "$event" > "$dest/core_postfit_products.validated"
    {
      echo "synced_utc=$(ts)"
      echo "event=$event"
      echo "run_label=$run"
      echo "source_host=$host"
      echo "source_results=$local_dir"
      echo "campaign_core_parameterization=E_j_core_52,Gamma_0_core_avg,log_theta_c,log_theta_v"
    } > "$dest/sync_manifest.txt"
    echo "[$(ts)] publish_done event=$event dest=$dest"
    progress=1
  done < "$MANIFEST"

  if [ "$progress" -eq 0 ]; then
    echo "[$(ts)] no_new_completed_runs sleep=$POLL_SECONDS"
    sleep "$POLL_SECONDS"
  fi
done

echo "[$(ts)] all_15_published campaign_products_start"
cd "$VJF"
"$PY" scripts/plot_campaign_physical_parameter_histograms.py --campaign "$CAMPAIGN"
"$PY" scripts/plot_minimized_core_mass_vs_solid_angle.py --campaign "$CAMPAIGN"
{
  echo "validated_utc=$(ts)"
  echo "events=15"
  echo "histograms=physical_shared_and_family_specific"
  echo "scatterplots=minimized_core_mass_vs_solid_angle,minimized_core_mass_per_solid_angle_vs_solid_angle"
} > "$CAMPAIGN/campaign_products.validated"
echo "[$(ts)] campaign_products_done"

cat > "$CAMPAIGN/campaign_summary.md" <<EOF
# Core-Energy / Core-Gamma Log-Angle Campaign

- Completed UTC: $(ts)
- Events: 15
- MCMC: 5 temperatures, 100 walkers, 2000 burn-in + 2000 production
- Power-law CSM events: 13
- Smoothly broken power-law CSM events: 080319B, 080413B
- Each event passed core-derived posterior and standard-product validation.
- Campaign-level physical-parameter histograms and minimized core-mass scatter
  products were regenerated from all 15 published event folders.
EOF

if [ -f "$TODO_FILE" ]; then
  if ! grep -q '^## Completion Report' "$TODO_FILE"; then
    cat >> "$TODO_FILE" <<EOF

## Completion Report

- Completed UTC: $(ts)
- [Published 15-GRB campaign](../../Fits/production_runs/unseeded_runs/26_06_25__core_ejet_gamma_logangles__mixed_powerlaw_and_sbpl_csm__unseeded__5_temperature_2000x2000/)
- [Campaign summary](../../Fits/production_runs/unseeded_runs/26_06_25__core_ejet_gamma_logangles__mixed_powerlaw_and_sbpl_csm__unseeded__5_temperature_2000x2000/campaign_summary.md)
- All event products passed the core-aware publication validator.
- Campaign histograms and scatter plots were rebuilt after all 15 events were
  published.
EOF
  fi
  mkdir -p "$COMPLETED_DIR"
  mv "$TODO_FILE" "$COMPLETED_DIR/"
  echo "[$(ts)] todo_report_moved_to_completed"
fi

/bin/bash "$VJF/scripts/resume_paused_sbpl_watchers_after_core_logangle_campaign.sh"
echo "[$(ts)] paused_sbpl_watchers_resumed"
