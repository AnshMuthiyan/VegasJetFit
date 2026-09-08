#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
BUILDER="${BUILDER:-$VEGAS_DIR/scripts/build_thetacfree_dylan_sbpl_configs.py}"
CAMPAIGN_LAUNCHER="${CAMPAIGN_LAUNCHER:-$ROOT/lab_start_dylan_sbpl_campaign.sh}"
CONFIG_SOURCE_DIR="${CONFIG_SOURCE_DIR:-$VEGAS_DIR/dylan_sbpl_configs_thetacfree_init5pct_v1}"
CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/dylan_sbpl_configs_thetacfree_init5pct_active}"

SESSION_NAME="${SESSION_NAME:-lab_thetacfree_dylan_sbpl_init5pct_watch}"
LOG_DIR="${LOG_DIR:-$ROOT/tmp/lab_fit_sync/logs}"
AUDIT_CSV="${AUDIT_CSV:-$LOG_DIR/${SESSION_NAME}_audit_$(date -u +%Y%m%dT%H%M%SZ).csv}"

RUN_TAG="${RUN_TAG:-thetacfree_dylan_sbpl_init5pct_2000x2000_v1}"
SOURCE_RUN_TAG="${SOURCE_RUN_TAG:-dylan_sbpl_init5pct_2000x2000_v1}"

THETA_C_INITIAL_SIGMA="${THETA_C_INITIAL_SIGMA:-0.05}"
THETA_C_LOWER_FLOOR="${THETA_C_LOWER_FLOOR:-0.001}"

LYRA_EVENTS="${LYRA_EVENTS:-080413B}"
PAULEY404_01_EVENTS="${PAULEY404_01_EVENTS:-080319B}"
PAULEY404_02_EVENTS="${PAULEY404_02_EVENTS:-}"
PAULEY404_03_EVENTS="${PAULEY404_03_EVENTS:-}"
STATUS_EVENTS="${STATUS_EVENTS:-080413B 080319B}"

mkdir -p "$LOG_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -f "$BUILDER" ]; then
  echo "ERROR: builder not found: $BUILDER" >&2
  exit 2
fi
if [ ! -x "$CAMPAIGN_LAUNCHER" ]; then
  echo "ERROR: campaign launcher not executable: $CAMPAIGN_LAUNCHER" >&2
  exit 2
fi

ALL_EVENTS=(080413B 080319B)

echo "=================================================="
echo "Preparing theta_c-free Dylan SBPL queue"
echo "Run tag:          $RUN_TAG"
echo "Source run tag:   $SOURCE_RUN_TAG"
echo "Config source:    $CONFIG_SOURCE_DIR"
echo "Config active:    $CONFIG_DIR"
echo "theta_c sigma:    $THETA_C_INITIAL_SIGMA"
echo "theta_c floor:    $THETA_C_LOWER_FLOOR"
echo "Events:           ${ALL_EVENTS[*]}"
echo "=================================================="

"$PYTHON_BIN" "$BUILDER" \
  --vegas-dir "$VEGAS_DIR" \
  --source-config-dir "$VEGAS_DIR/dylan_sbpl_configs_init5pct_active" \
  --output-dir "$CONFIG_SOURCE_DIR" \
  --source-run-tag "$SOURCE_RUN_TAG" \
  --results-name-template "{event}_{run_tag}" \
  --results-root "$VEGAS_DIR/jetfit/results" \
  --events "${ALL_EVENTS[@]}" \
  --audit-csv "$AUDIT_CSV" \
  --theta-c-initial-sigma "$THETA_C_INITIAL_SIGMA" \
  --theta-c-lower-floor "$THETA_C_LOWER_FLOOR"

CONFIG_SOURCE_DIR="$CONFIG_SOURCE_DIR" \
CONFIG_DIR="$CONFIG_DIR" \
RUN_TAG="$RUN_TAG" \
SESSION_NAME="$SESSION_NAME" \
LYRA_EVENTS="$LYRA_EVENTS" \
PAULEY404_01_EVENTS="$PAULEY404_01_EVENTS" \
PAULEY404_02_EVENTS="$PAULEY404_02_EVENTS" \
PAULEY404_03_EVENTS="$PAULEY404_03_EVENTS" \
STATUS_EVENTS="$STATUS_EVENTS" \
bash "$CAMPAIGN_LAUNCHER"
