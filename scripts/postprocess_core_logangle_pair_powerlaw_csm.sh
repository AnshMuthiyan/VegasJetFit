#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
MANIFEST="$VJF/reports/core_logangle_15grb_campaign/pair_powerlaw_csm_dispatch_manifest.csv"
RUN_TAG="core_logangle_powerlawcsm_unseeded_5temp_2000x2000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/unseeded_runs/26_06_25__core_ejet_gamma_logangles__mixed_powerlaw_and_sbpl_csm__unseeded__5_temperature_2000x2000"
LOG="$VJF/logs/postprocess_core_logangle_pair_powerlaw_csm.log"
POLL_SECONDS="${POLL_SECONDS:-300}"
# Zero requests every terminal cold-chain walker; see density_profile_sampling.json.
DENSITY_PROFILE_SAMPLES="${DENSITY_PROFILE_SAMPLES:-0}"
export JETFIT_DENSITY_PROFILE_SAMPLES="$DENSITY_PROFILE_SAMPLES"

mkdir -p "$CAMPAIGN" "$VJF/logs"
exec > >(tee -a "$LOG") 2>&1

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
lyra_busy() {
  pgrep -f "scripts/minimize.py|scripts/generate_postfit_products.py|plot_spread_light_curves.py|plot_structjet_swept_mass_diagnostics.py" >/dev/null 2>&1
}
remote_complete() {
  local host="$1" remote="$2"
  ssh -n -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "test -s '$remote/chain.npz' -a -s '$remote/best_fit.json' && ! ps -axo command | grep '[j]etfit.run' | grep -F '$remote' >/dev/null"
}
all_published() {
  test -e "$CAMPAIGN/080319B/core_postfit_products.validated" -a \
       -e "$CAMPAIGN/080413B/core_postfit_products.validated"
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
    remote="$VJF/jetfit/results/$run"
    if remote_complete "$host" "$remote"; then
      mkdir -p "$local_dir"
      echo "[$(ts)] pull_start event=$event host=$host"
      rsync -a --partial "$host:$remote/" "$local_dir/"
      echo "[$(ts)] pull_done event=$event host=$host"
    else
      continue
    fi
    while lyra_busy; do
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
      echo "csm_family=power_law"
      echo "replacement_for=SBPL_RUNS/${event}_SBPL"
    } > "$dest/sync_manifest.txt"
    echo "[$(ts)] publish_done event=$event dest=$dest"
    progress=1
  done < "$MANIFEST"
  if [ "$progress" -eq 0 ]; then
    echo "[$(ts)] no_new_completed_runs sleep=$POLL_SECONDS"
    sleep "$POLL_SECONDS"
  fi
done

echo "[$(ts)] both_pair_powerlaw_published campaign_products_start"
cd "$VJF"
"$PY" scripts/plot_campaign_physical_parameter_histograms.py --campaign "$CAMPAIGN"
"$PY" scripts/plot_minimized_core_mass_vs_solid_angle.py --campaign "$CAMPAIGN"
{
  echo "validated_utc=$(ts)"
  echo "events=15"
  echo "pair_powerlaw_replacements=080319B,080413B"
  echo "sbpl_archived_under=SBPL_RUNS"
  echo "histograms=physical_shared_and_family_specific"
  echo "scatterplots=minimized_core_mass_vs_solid_angle,minimized_core_mass_per_solid_angle_vs_solid_angle"
} > "$CAMPAIGN/campaign_products.validated"
echo "[$(ts)] campaign_products_done"
