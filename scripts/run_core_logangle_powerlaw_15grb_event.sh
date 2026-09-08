#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="${EVENT:?set EVENT}"
WORKERS="${WORKERS:-8}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_core_logangle_10temp_2000x2000.toml}"
RUN_TAG="${RUN_TAG:-core_logangle_powerlawcsm_unseeded_10temp_2000x2000_v1}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/structured_jet_core_logangle_powerlaw_15grb_10temp_configs_active}"
INITIAL_POSITIONS="${INITIAL_POSITIONS:-}"
DISPATCH_MANIFEST="${DISPATCH_MANIFEST:-$VJF/reports/core_logangle_powerlaw_15grb_10temp_2000_campaign/dispatch_manifest.csv}"
ENFORCE_DISPATCH_HOST="${ENFORCE_DISPATCH_HOST:-1}"

# The approved 090424 analysis includes all UVOT/UVOIR observations while
# retaining the separately documented early-X-ray exclusions. The one explicit
# exception is the controlled early-X-ray comparison, which must opt in by
# setting ALLOW_090424_EARLY_XRAY_TEST=1 and records its own run tag.
if [ "$EVENT" = "090424" ]; then
  if [ "${ALLOW_090424_EARLY_XRAY_TEST:-0}" = "1" ]; then
    OBS_CSV_OVERRIDE="${OBS_CSV_OVERRIDE:-$VJF/obs_overrides/090424_early_uvoir_included_with_early_xray.csv}"
  else
    OBS_CSV_OVERRIDE="${OBS_CSV_OVERRIDE:-$VJF/obs_overrides/090424_early_uvoir_included_no_early_xray.csv}"
  fi
  REQUIRE_090424_ALL_UV=1
fi

normalize_host() {
  printf '%s\n' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/\.local$//'
}

if [ "$ENFORCE_DISPATCH_HOST" = "1" ] && [ -f "$DISPATCH_MANIFEST" ]; then
  expected_host="$(awk -F, -v ev="$EVENT" 'NR>1 && $1==ev {print $2; exit}' "$DISPATCH_MANIFEST")"
  expected_workers="$(awk -F, -v ev="$EVENT" 'NR>1 && $1==ev {print $5; exit}' "$DISPATCH_MANIFEST")"
  if [ -n "$expected_host" ]; then
    this_host="$(normalize_host "$(hostname)")"
    expected_norm="$(normalize_host "$expected_host")"
    if [ "$expected_norm" != "lyra" ] && [ "$expected_norm" != "$this_host" ]; then
      echo "skip_unassigned_event_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) event=$EVENT host=$this_host expected_host=$expected_norm manifest=$DISPATCH_MANIFEST"
      exit 0
    fi
  fi
  if [ -n "$expected_workers" ] && [ "$WORKERS" != "$expected_workers" ]; then
    echo "ERROR: WORKERS=$WORKERS does not match manifest workers=$expected_workers for event=$EVENT manifest=$DISPATCH_MANIFEST" >&2
    echo "Set WORKERS from the dispatch manifest or update the manifest intentionally before launch." >&2
    exit 2
  fi
fi

cd "$VJF"
EVENT="$EVENT" \
CONFIG_DIR="$CONFIG_DIR" \
RUN_TAG="$RUN_TAG" \
RESULTS_NAME_TEMPLATE='{event}_{run_tag}' \
MCMC_SETTINGS="$MCMC_SETTINGS" \
INITIAL_POSITIONS="$INITIAL_POSITIONS" \
OBS_CSV_OVERRIDE="${OBS_CSV_OVERRIDE:-}" \
REQUIRE_090424_ALL_UV="${REQUIRE_090424_ALL_UV:-0}" \
ALLOW_090424_EARLY_XRAY_TEST="${ALLOW_090424_EARLY_XRAY_TEST:-0}" \
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}" \
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-1}" \
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-1}" \
PREFLIGHT_ONLY="${PREFLIGHT_ONLY:-0}" \
RUN_FOREGROUND=1 \
RUN_MINIMIZER=0 \
RUN_POSTFIT_PRODUCTS=0 \
SKIP_MCMC_PLOTS=1 \
DRIVE_SYNC_ENABLE=0 \
WORKERS="$WORKERS" \
CLEAN_INCOMPLETE="${CLEAN_INCOMPLETE:-1}" \
SKIP_COMPLETED="${SKIP_COMPLETED:-1}" \
REQUIRE_AUDIT_OBS_ROWS=0 \
REQUIRE_STANDARD_EJET_GAMMA_PRIORS=0 \
/bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
