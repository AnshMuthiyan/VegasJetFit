#!/usr/bin/env bash
# Launch one final-final run only after its posterior-informed cloud exists.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="${EVENT:?set EVENT}"
HOST_SHORT="$(hostname -s | tr '[:upper:]' '[:lower:]')"
if [ -z "${WORKERS+x}" ]; then
  case "$HOST_SHORT" in
    pcrc-*) WORKERS=15 ;;
    *) WORKERS=8 ;;
  esac
else
  WORKERS="$WORKERS"
fi
RUN_TAG="${RUN_TAG:-core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_v2}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/structured_jet_core_logangle_powerlaw_15grb_kminus10to3_finalfinal_sthawed_5temp_configs_pending}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_core_logangle_finalfinal_sthawed_5temp_1000x5000.toml}"
INITIAL_POSITIONS="${INITIAL_POSITIONS:-$VJF/initial_positions/finalfinal_sthawed_5temp/${EVENT}.npz}"
EVENT_DECISION_RECORDS="${EVENT_DECISION_RECORDS:-}"

# GRB 090424's approved final analysis retains every UVOT/UVOIR point while
# leaving the separately rejected early X-ray sequence out. The controlled
# early-X-ray branch must opt in explicitly, so generic final-final launches
# cannot silently change the canonical likelihood.
if [ "$EVENT" = "090424" ]; then
  if [ "${ALLOW_090424_EARLY_XRAY_TEST:-0}" = "1" ]; then
    OBS_CSV_OVERRIDE="${OBS_CSV_OVERRIDE:-$VJF/obs_overrides/090424_early_uvoir_included_with_early_xray.csv}"
  else
    OBS_CSV_OVERRIDE="${OBS_CSV_OVERRIDE:-$VJF/obs_overrides/090424_early_uvoir_included_no_early_xray.csv}"
  fi
  REQUIRE_090424_ALL_UV=1
fi

# Multi-event dispatchers pass the directory containing one cloud per GRB;
# retain the existing single-file interface for dedicated one-event launchers.
if [ -d "$INITIAL_POSITIONS" ]; then
  INITIAL_POSITIONS="$INITIAL_POSITIONS/${EVENT}.npz"
fi

RESULTS_DIR="$VJF/jetfit/results/${EVENT}_${RUN_TAG}"
CHECKPOINT="$RESULTS_DIR/pt_resume_state.npz"

# A power loss must never turn a recoverable parallel-tempered chain into a
# fresh launch.  Validate the checkpoint before enabling its paired resume
# mode; a deliberately fresh replacement can still set FORCE_FRESH=1.
if [ "${FORCE_FRESH:-0}" != "1" ] && [ -f "$CHECKPOINT" ]; then
  "$ROOT/.venv/bin/python" - "$CHECKPOINT" <<'PY'
from pathlib import Path
import sys

import numpy as np

path = Path(sys.argv[1])
with np.load(path, allow_pickle=False) as state:
    required = {"chain", "lnprob", "last_pos", "completed_iterations", "phase"}
    missing = sorted(required.difference(state.files))
    if missing:
        raise SystemExit(f"invalid resume checkpoint {path}: missing {missing}")
    if state["chain"].ndim != 3 or state["lnprob"].ndim != 2 or state["last_pos"].ndim != 3:
        raise SystemExit(f"invalid resume checkpoint {path}: unexpected array dimensions")
PY
  RESUME=1
  CLEAN_INCOMPLETE=0
  echo "Validated interrupted checkpoint; resuming without cleanup: $CHECKPOINT"
fi

if [ ! -f "$INITIAL_POSITIONS" ]; then
  echo "ERROR: final-final posterior cloud is required but missing: $INITIAL_POSITIONS" >&2
  exit 2
fi

if [ -n "$EVENT_DECISION_RECORDS" ]; then
  if [ ! -f "$EVENT_DECISION_RECORDS" ]; then
    echo "ERROR: decision-record file is missing: $EVENT_DECISION_RECORDS" >&2
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
EVENT_DECISION_RECORDS="$EVENT_DECISION_RECORDS" \
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
REQUIRE_STANDARD_EJET_GAMMA_PRIORS=1 \
REQUIRE_220101A_HST_FILTERS=1 \
REQUIRE_221009A_MILKY_WAY_RV_PRIOR=1 \
/bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
