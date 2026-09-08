#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
if [ -d /opt/homebrew/bin ]; then
  PATH="/opt/homebrew/bin:$PATH"
fi
export PATH
MANIFEST="${MANIFEST:-$VJF/reports/core_logangle_powerlaw_15grb_10temp_2000_campaign/dispatch_manifest.csv}"
RUN_TAG="${RUN_TAG:-core_logangle_powerlawcsm_unseeded_10temp_2000x2000_v1}"
CAMPAIGN="${CAMPAIGN:-$ROOT/Share_Folder/Fits/production_runs/unseeded_runs/26_06_27__core_ejet_gamma_logangles__single_powerlaw_csm__unseeded__10_temperature_2000x2000}"
LOG="${LOG:-$VJF/logs/postprocess_core_logangle_powerlaw_15grb_10temp.log}"
POLL_SECONDS="${POLL_SECONDS:-300}"
# Zero requests every terminal cold-chain walker; see density_profile_sampling.json.
DENSITY_PROFILE_SAMPLES="${DENSITY_PROFILE_SAMPLES:-0}"
PRODUCT_WORKERS="${PRODUCT_WORKERS:-4}"
MINIMIZER_MAX_WALKERS="${MINIMIZER_MAX_WALKERS:-8}"
MINIMIZER_WORKERS="${MINIMIZER_WORKERS:-8}"
RESOLUTION_CONVERGENCE="${RESOLUTION_CONVERGENCE:-1}"
SAMPLER_LABEL="${SAMPLER_LABEL:-100walkers_2000burn_2000run_10temps}"
CAMPAIGN_SUMMARY_TITLE="${CAMPAIGN_SUMMARY_TITLE:-GRB Campaign Meeting Summary}"
CAMPAIGN_SUMMARY_PURPOSE="${CAMPAIGN_SUMMARY_PURPOSE:-Campaign meeting summary generated from published results.}"
# A controlled one-event comparison can preserve its normal event identity in
# the fit while publishing to a distinct campaign subdirectory. Both variables
# are required, so ordinary campaign watchers retain their existing layout.
PUBLISH_EVENT_SOURCE="${PUBLISH_EVENT_SOURCE:-}"
PUBLISH_EVENT_NAME="${PUBLISH_EVENT_NAME:-}"
export JETFIT_DENSITY_PROFILE_SAMPLES="$DENSITY_PROFILE_SAMPLES"

mkdir -p "$CAMPAIGN" "$VJF/logs"
exec > >(tee -a "$LOG") 2>&1

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
ACTIVITY_DIR="$VJF/logs/postprocess_activity"
ACTIVITY_FILE="$ACTIVITY_DIR/$(basename "$LOG").active"
LYRA_POSTFIT_LOCK="$ACTIVITY_DIR/lyra_postfit.lock"
LYRA_POSTFIT_LOCK_HELD=0
mkdir -p "$ACTIVITY_DIR"
activity_start() {
  {
    echo "pid=$$"
    echo "event=$1"
    echo "started_utc=$(ts)"
    echo "watcher_log=$LOG"
  } > "$ACTIVITY_FILE"
}
activity_clear() { rm -f "$ACTIVITY_FILE"; }
postfit_lock_owner() { { sed -n 's/^pid=//p' "$LYRA_POSTFIT_LOCK/owner" 2>/dev/null | head -n 1; } || true; }
postfit_lock_is_stale() {
  local owner="$1" command modified now
  if [ -n "$owner" ]; then
    command="$(ps -p "$owner" -o command= 2>/dev/null || true)"
    [[ "$command" != *"postprocess_core_logangle_powerlaw_15grb_10temp.sh"* ]]
    return
  fi
  # This only covers a crash between mkdir and writing the owner file.
  modified="$(stat -f %m "$LYRA_POSTFIT_LOCK" 2>/dev/null || true)"
  now="$(date +%s)"
  [ -n "$modified" ] && [ $((now - modified)) -ge 300 ]
}
postfit_lock_release() {
  [ "$LYRA_POSTFIT_LOCK_HELD" = "1" ] || return 0
  [ "$(postfit_lock_owner)" = "$$" ] && rm -rf "$LYRA_POSTFIT_LOCK"
  LYRA_POSTFIT_LOCK_HELD=0
}
postfit_lock_acquire() {
  if mkdir "$LYRA_POSTFIT_LOCK" 2>/dev/null; then
    {
      echo "pid=$$"
      echo "event=$1"
      echo "watcher_log=$LOG"
      echo "started_utc=$(ts)"
    } > "$LYRA_POSTFIT_LOCK/owner"
    LYRA_POSTFIT_LOCK_HELD=1
    return 0
  fi
  local owner
  owner="$(postfit_lock_owner)"
  # A killed/rebooted watcher cannot leave a permanent scheduling barrier.
  if postfit_lock_is_stale "$owner"; then
    rm -rf "$LYRA_POSTFIT_LOCK"
    postfit_lock_acquire "$1"
    return
  fi
  return 1
}
trap 'activity_clear; postfit_lock_release' EXIT INT TERM
normalize_host() { printf '%s\n' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/\.local$//'; }
metadata_value() {
  local key="$1"
  shift
  local file
  for file in "$@"; do
    [ -f "$file" ] || continue
    awk -F= -v key="$key" '$1 == key {print substr($0, length(key) + 2); exit}' "$file"
  done | head -n 1
}
WATCHER_HOST="$(normalize_host "$(hostname)")"
manifest_events() { awk -F, 'NR>1 && $1 != "" {print $1}' "$MANIFEST"; }
campaign_event_name() {
  local event="$1"
  if [ -n "$PUBLISH_EVENT_SOURCE" ] && [ -n "$PUBLISH_EVENT_NAME" ] && [ "$event" = "$PUBLISH_EVENT_SOURCE" ]; then
    printf '%s\n' "$PUBLISH_EVENT_NAME"
  else
    printf '%s\n' "$event"
  fi
}
manifest_count() { manifest_events | wc -l | tr -d ' '; }
campaign_expected_events() {
  local records="$CAMPAIGN/event_decision_records.json"
  local recorded=""
  if [ -s "$records" ]; then
    recorded="$("$PY" - "$records" 2>/dev/null <<'PY' || true
import json
import sys

with open(sys.argv[1]) as handle:
    events = json.load(handle).get("events", {})
if isinstance(events, dict):
    names = events.keys()
elif isinstance(events, list):
    names = (item.get("event") for item in events if isinstance(item, dict))
else:
    names = ()
for name in names:
    if name:
        print(name)
PY
)"
  fi
  if [ -n "$recorded" ]; then
    printf '%s\n' "$recorded"
  else
    while read -r event; do
      campaign_event_name "$event"
    done < <(manifest_events)
  fi
}
campaign_expected_count() { campaign_expected_events | wc -l | tr -d ' '; }
campaign_validated_count() {
  local event count=0
  while read -r event; do
    [ -s "$CAMPAIGN/$event/core_postfit_products.validated" ] && count=$((count + 1))
  done < <(campaign_expected_events)
  printf '%s\n' "$count"
}
lyra_busy_processes() {
  # Require a Python executable as well as a known compute entry point.  A
  # shell status command can contain a script pathname, but must not serialize
  # the post-fit queue merely by mentioning one.
  ps -axo command= | awk '
    /\/[Pp]ython([[:space:]]|$)/ &&
    (/-m[[:space:]]+jetfit[.]run([[:space:]]|$)/ ||
     /scripts\/minimize[.]py([[:space:]]|$)/ ||
     /scripts\/generate_postfit_products[.]py([[:space:]]|$)/ ||
     /scripts\/run_vegas_resolution_ladder[.]py([[:space:]]|$)/ ||
     /scripts\/plot_spread_light_curves[.]py([[:space:]]|$)/ ||
     /scripts\/plot_structjet_swept_mass_diagnostics[.]py([[:space:]]|$)/) { print }
  ' || true
}
lyra_busy() { [ -n "$(lyra_busy_processes)" ]; }
remote_complete() {
  local host="$1" remote="$2"
  ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "test -s '$remote/chain.npz' -a -s '$remote/best_fit.json' && ! ps -axo command | grep '[j]etfit.run' | grep -F '$remote' >/dev/null"
}
local_complete() {
  local local_dir="$1"
  test -s "$local_dir/chain.npz" -a -s "$local_dir/best_fit.json" && \
    ! ps -axo command | grep '[j]etfit.run' | grep -F "$local_dir" >/dev/null
}
all_manifest_published() {
  local ev
  local total
  total="$(manifest_count)"
  [ "$total" -gt 0 ] || return 1
  while read -r ev; do
    [ -e "$CAMPAIGN/$(campaign_event_name "$ev")/core_postfit_products.validated" ] || return 1
  done < <(manifest_events)
  return 0
}
manifest_published_count() {
  local ev count=0
  while read -r ev; do
    [ -e "$CAMPAIGN/$(campaign_event_name "$ev")/core_postfit_products.validated" ] && count=$((count + 1))
  done < <(manifest_events)
  printf '%s\n' "$count"
}
SUMMARY_PENDING="$CAMPAIGN/.campaign_meeting_summary.pending"
SUMMARY_UPDATED="$CAMPAIGN/.campaign_meeting_summary.updated"
refresh_campaign_summary() {
  local trigger="${1:-watcher}"
  : > "$SUMMARY_PENDING"
  echo "[$(ts)] campaign_summary_start trigger=$trigger manifest_published=$(manifest_published_count)/$(manifest_count) campaign_validated=$(campaign_validated_count)/$(campaign_expected_count)"
  if ! (
    cd "$VJF"
    "$PY" scripts/write_campaign_latex_summary.py \
      --campaign "$CAMPAIGN" \
      --title "$CAMPAIGN_SUMMARY_TITLE" \
      --purpose "$CAMPAIGN_SUMMARY_PURPOSE"
  ); then
    echo "[$(ts)] campaign_summary_failed trigger=$trigger"
    return 1
  fi
  {
    echo "updated_utc=$(ts)"
    echo "trigger=$trigger"
    echo "published_events=$(campaign_validated_count)"
    echo "expected_campaign_events=$(campaign_expected_count)"
    echo "manifest_published_events=$(manifest_published_count)"
    echo "manifest_events=$(manifest_count)"
  } > "$SUMMARY_UPDATED"
  rm -f "$SUMMARY_PENDING"
  echo "[$(ts)] campaign_summary_done trigger=$trigger"
}

echo "[$(ts)] watcher_start campaign=$CAMPAIGN manifest=$MANIFEST"
while ! all_manifest_published; do
  progress=0
  if [ -e "$SUMMARY_PENDING" ]; then
    refresh_campaign_summary "retry" || true
  fi
  while IFS=, read -r event host family order workers run_tag launched_utc; do
    [ "$event" = "event" ] && continue
    [ -n "$event" ] || continue
    # A dispatch manifest may retain queued, pending, or scientifically blocked
    # rows.  Those labels are scheduling state, not SSH destinations.
    case "$(normalize_host "$host")" in
      ""|n/a|pending*|queued*|blocked*) continue ;;
    esac
    tag="${run_tag:-$RUN_TAG}"
    run="${event}_${tag}"
    local_dir="$VJF/jetfit/results/$run"
    dest="$CAMPAIGN/$(campaign_event_name "$event")"
    [ -e "$dest/core_postfit_products.validated" ] && continue

    ready=0
    if [ "$(normalize_host "$host")" = "$WATCHER_HOST" ]; then
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
    # A worker host may be producing the expensive diagnostics locally.  The
    # pull is intentionally non-deleting so it never removes a local recovery
    # file; consequently an old local running marker can survive the remote
    # cleanup. A validated completion marker always takes precedence.
    if [ ! -s "$local_dir/postfit_compute.done" ] && \
       [ -e "$local_dir/.postfit_compute.running" ]; then
      echo "[$(ts)] remote_postfit_compute_active event=$event host=$host sleep=$POLL_SECONDS"
      continue
    fi

    while true; do
      if lyra_busy; then
        busy_process="$(lyra_busy_processes | head -n 1 | sed 's/[[:space:]]\+/ /g')"
        echo "[$(ts)] lyra_busy event=$event process=$busy_process sleep=$POLL_SECONDS"
      elif postfit_lock_acquire "$event"; then
        break
      else
        lock_owner="$(postfit_lock_owner)"
        echo "[$(ts)] postfit_lock_busy event=$event owner_pid=${lock_owner:-unknown} sleep=$POLL_SECONDS"
      fi
      sleep "$POLL_SECONDS"
    done
    activity_start "$event"

    # Preserve a scientific-review decision when regenerating/publishing an
    # event.  These flags are metadata, not a product-generation result.
    review_status="$(metadata_value review_status "$local_dir/core_postfit_products.validated" "$local_dir/sync_manifest.txt")"
    review_reason="$(metadata_value review_reason "$local_dir/sync_manifest.txt")"

    if [ ! -s "$local_dir/minimized/minimized.json" ]; then
      echo "[$(ts)] minimize_start event=$event max_walkers=$MINIMIZER_MAX_WALKERS workers=$MINIMIZER_WORKERS"
      "$PY" "$VJF/scripts/minimize.py" \
        --results "$local_dir" \
        --obs "$local_dir/obs.csv" \
        --params "$local_dir/model.toml" \
        --mode walkers \
        --max-walkers "$MINIMIZER_MAX_WALKERS" \
        --parallel-workers "$MINIMIZER_WORKERS" \
        --scipy-method Powell \
        --fallback-scipy-method Nelder-Mead
      echo "[$(ts)] minimize_done event=$event"
    fi

    validation_args=(--results "$local_dir")
    [ "$RESOLUTION_CONVERGENCE" = "1" ] && validation_args+=(--require-resolution-ladder)
    compute_reused=0
    if [ -s "$local_dir/postfit_compute.done" ] && \
       "$PY" "$VJF/scripts/validate_core_postfit_products.py" "${validation_args[@]}"; then
      compute_reused=1
      echo "[$(ts)] postfit_compute_reused event=$event"
    fi
    if [ "$compute_reused" -eq 0 ]; then
      rm -f "$local_dir/postfit_compute.done"
      echo "[$(ts)] postfit_start event=$event"
      "$PY" "$VJF/scripts/generate_postfit_products.py" \
        --results "$local_dir" \
        --event "$event" \
        --parallel-products \
        --product-workers "$PRODUCT_WORKERS"
      if [ "$RESOLUTION_CONVERGENCE" = "1" ]; then
        echo "[$(ts)] resolution_convergence_start event=$event"
        "$PY" "$VJF/scripts/run_vegas_resolution_ladder.py" \
          --event "$event" \
          --results "$local_dir" \
          --out "$local_dir/resolution_ladder"
        "$PY" "$VJF/scripts/plot_vegas_resolution_ladder.py" \
          --event-dir "$local_dir/resolution_ladder"
        echo "[$(ts)] resolution_convergence_done event=$event"
      fi
      "$PY" "$VJF/scripts/validate_core_postfit_products.py" "${validation_args[@]}"
      {
        printf 'completed_utc=%s\nevent=%s\n' "$(ts)" "$event"
        echo "executor_host=$WATCHER_HOST"
      } > "$local_dir/postfit_compute.done"
    fi
    "$PY" "$VJF/scripts/validate_core_postfit_products.py" "${validation_args[@]}"
    {
      printf 'validated_utc=%s\nevent=%s\n' "$(ts)" "$event"
      [ -z "$review_status" ] || printf 'review_status=%s\n' "$review_status"
    } > "$local_dir/core_postfit_products.validated"
    printf 'done_utc=%s\nevent=%s\n' "$(ts)" "$event" > "$local_dir/postfit_products.done"
    mkdir -p "$dest"
    rsync -a --delete --exclude='trash/' "$local_dir/" "$dest/"
    validation_args=(--results "$dest")
    [ "$RESOLUTION_CONVERGENCE" = "1" ] && validation_args+=(--require-resolution-ladder)
    "$PY" "$VJF/scripts/validate_core_postfit_products.py" "${validation_args[@]}"
    {
      printf 'validated_utc=%s\nevent=%s\n' "$(ts)" "$event"
      [ -z "$review_status" ] || printf 'review_status=%s\n' "$review_status"
    } > "$dest/core_postfit_products.validated"
    {
      echo "synced_utc=$(ts)"
      echo "event=$event"
      echo "run_label=$run"
      echo "source_host=$host"
      echo "source_results=$local_dir"
      echo "campaign_core_parameterization=E_j_core_52,Gamma_0_core_avg,log_theta_c,log_theta_v"
      echo "csm_family=power_law"
      echo "sampler=$SAMPLER_LABEL"
      [ -z "$review_status" ] || echo "review_status=$review_status"
      [ -z "$review_reason" ] || echo "review_reason=$review_reason"
    } > "$dest/sync_manifest.txt"
    echo "[$(ts)] publish_done event=$event dest=$dest"
    refresh_campaign_summary "$event" || true
    activity_clear
    postfit_lock_release
    progress=1
    if all_manifest_published; then
      echo "[$(ts)] all_manifest_published_after_event event=$event"
      break
    fi
  done < "$MANIFEST"

  all_manifest_published && break
  if [ "$progress" -eq 0 ]; then
    echo "[$(ts)] no_new_completed_runs sleep=$POLL_SECONDS"
    sleep "$POLL_SECONDS"
  fi
done

echo "[$(ts)] manifest_events_published campaign_products_start"
until refresh_campaign_summary "all_manifest_published"; do
  echo "[$(ts)] campaign_summary_retry_after_all_events sleep=$POLL_SECONDS"
  sleep "$POLL_SECONDS"
done
expected_campaign_events="$(campaign_expected_count)"
validated_campaign_events="$(campaign_validated_count)"
if [ "$validated_campaign_events" -ge "$expected_campaign_events" ]; then
  rm -f "$CAMPAIGN/.campaign_products.partial"
  {
    echo "validated_utc=$(ts)"
    echo "events=$expected_campaign_events"
    echo "validated_events=$validated_campaign_events"
    echo "manifest_events=$(manifest_count)"
    echo "histograms=physical_shared_and_family_specific"
    echo "scatterplots=minimized_core_mass_vs_solid_angle,minimized_core_mass_per_solid_angle_vs_solid_angle"
  } > "$CAMPAIGN/campaign_products.validated"
  echo "[$(ts)] campaign_products_done events=$expected_campaign_events manifest_events=$(manifest_count)"
else
  rm -f "$CAMPAIGN/campaign_products.validated"
  {
    echo "updated_utc=$(ts)"
    echo "validated_events=$validated_campaign_events"
    echo "expected_events=$expected_campaign_events"
    echo "manifest_events=$(manifest_count)"
  } > "$CAMPAIGN/.campaign_products.partial"
  echo "[$(ts)] campaign_products_partial validated=$validated_campaign_events expected=$expected_campaign_events"
fi
