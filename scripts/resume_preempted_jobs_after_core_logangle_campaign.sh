#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
host="$(hostname | tr '[:upper:]' '[:lower:]')"

case "$host" in
  pcrc-mac-studio-1.local|pcrc-mac-studio-1)
    if [ ! -s "$VJF/jetfit/results/220101A_core_logangle_unseeded_5temp_2000x2000_v1/chain.npz" ]; then
      echo "reassigned_core_logangle_start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) event=220101A host=$host"
      EVENT=220101A WORKERS=14 /bin/bash "$VJF/scripts/run_core_logangle_15grb_event.sh"
      echo "reassigned_core_logangle_done_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) event=220101A host=$host"
    fi
    EVENT=080413B FAMILY=sbpl WORKERS=14 RESUME=1 CLEAN_INCOMPLETE=0 SKIP_COMPLETED=0 \
      /bin/bash "$VJF/scripts/run_sbpl_pair_logejet52_penultimate_event.sh"
    ;;
  pauley404-01|pauley404-01.local)
    EVENT=080413B FAMILY=powerlaw WORKERS=8 RESUME=1 CLEAN_INCOMPLETE=0 SKIP_COMPLETED=0 \
      /bin/bash "$VJF/scripts/run_sbpl_pair_powerlaw_csm_logejet52_penultimate_event.sh"
    ;;
  pauley404-03|pauley404-03.local)
    EVENT=080319B FAMILY=powerlaw WORKERS=8 RESUME=1 CLEAN_INCOMPLETE=0 SKIP_COMPLETED=0 \
      /bin/bash "$VJF/scripts/run_sbpl_pair_powerlaw_csm_logejet52_penultimate_event.sh"
    ;;
  *)
    echo "No preempted job registered for host=$host"
    ;;
esac
