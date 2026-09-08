#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
WAITER="${WAITER:-$VEGAS_DIR/scripts/wait_and_start_structured_jet_all_2000.sh}"
LAUNCHER="${LAUNCHER:-$VEGAS_DIR/scripts/start_structured_jet_sbpl_2000.sh}"

exec env \
  WAIT_FAMILY=sbpl \
  SESSION_NAME="${SESSION_NAME:-lab_structured_jet_sbpl_wait}" \
  LAUNCHER="$LAUNCHER" \
  bash "$WAITER"
