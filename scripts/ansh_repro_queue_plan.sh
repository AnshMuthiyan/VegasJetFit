#!/usr/bin/env bash
set -euo pipefail

# Queue plan only.
# This file intentionally does not launch anything.
#
# Purpose:
# - Preserve the exact campaign breakdown agreed in meeting notes.
# - Make later launches explicit and repeatable.
# - Prevent accidental start before the compiled-vs-Python smoothing decision.

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"

TRACKING_SHEET_URL="https://docs.google.com/spreadsheets/d/1pbgOMIJx_C9crSOtti6BJvAbXvTsWJv0fZXESgRCPf8"

THESIS_ORDER=(
  221009A
  171010A
  130612A
  050922C
  050525A
  210905A
  090424
  090618
  111228A
  131030A
  140506A
  160131A
  220101A
  080413B
  080319B
)

BOWTIE_PRIORITY=(
  050525A
  090424
  160131A
)

CAMPAIGN_A_TAG="${CAMPAIGN_A_TAG:-powerlawjet_openview_ourpriors_seeded_v1}"
CAMPAIGN_B_TAG="${CAMPAIGN_B_TAG:-ansh_exact_reproduction_v1}"
CAMPAIGN_C_TAG="${CAMPAIGN_C_TAG:-ourmodel_anshsetup_v1}"

cat <<EOF
Queue plan only. No jobs launched.

Live meeting sheet:
  $TRACKING_SHEET_URL

Priority bow-tie / pinching events:
  ${BOWTIE_PRIORITY[*]}

Full thesis order:
  ${THESIS_ORDER[*]}

Campaign A:
  tag=$CAMPAIGN_A_TAG
  meaning=our recent setup, thaw theta_v only

Campaign B:
  tag=$CAMPAIGN_B_TAG
  meaning=exact Ansh reproduction from shared metadata

Campaign C:
  tag=$CAMPAIGN_C_TAG
  meaning=our model family under Ansh's inference setup

Current block:
  Do not launch until the Dylan smoothing path decision is made.
  Current PowerlawJetVegasDylanSpectrumModel still uses Python-side smoothing.

Relevant references:
  $VEGAS_DIR/reports/ansh_repro_campaign_20260428.md
  $VEGAS_DIR/reports/ansh_repro_campaign_20260428.json
EOF
