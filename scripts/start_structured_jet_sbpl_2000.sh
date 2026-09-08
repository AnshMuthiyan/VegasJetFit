#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
LAUNCHER="${LAUNCHER:-$VEGAS_DIR/scripts/start_structured_jet_all_2000.sh}"

exec env \
  RUN_FAMILY=sbpl \
  CONFIG_SOURCE_DIR="${CONFIG_SOURCE_DIR:-$VEGAS_DIR/structured_jet_sbpl_configs_v1}" \
  CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/structured_jet_sbpl_configs_active}" \
  SESSION_NAME="${SESSION_NAME:-lab_structured_jet_sbpl_2000_watch}" \
  HOSTS="${HOSTS:-pauley404-01}" \
  LYRA_EVENTS="${LYRA_EVENTS:-080319B}" \
  PAULEY404_01_EVENTS="${PAULEY404_01_EVENTS:-080413B}" \
  PAULEY404_02_EVENTS="${PAULEY404_02_EVENTS:-}" \
  PAULEY404_03_EVENTS="${PAULEY404_03_EVENTS:-}" \
  STATUS_EVENTS="${STATUS_EVENTS:-080413B 080319B}" \
  bash "$LAUNCHER"
