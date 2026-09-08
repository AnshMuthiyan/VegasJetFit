#!/usr/bin/env bash
set -euo pipefail

# Run one smoothly-broken CSM power-law campaign queue.
#
# This is the unseeded analogue of the recent single-power-law CSM tests:
#   - Dylan-smoothed synchrotron spectrum enabled in the model TOML.
#   - Smoothly broken CSM power-law medium.
#   - No initial_guess / initial_sigma entries in the campaign TOMLs.
#   - Parallel-tempered sampler with the Dylan-smoothed 2000x2000 profile.
#   - Final minimization over all MCMC walkers.

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="${VJF:-$ROOT/VegasJetFit}"
EVENTS="${EVENTS:-080319B 080413B}"
CONFIG_DIR="${CONFIG_DIR:?Set CONFIG_DIR to the campaign TOML directory}"
RUN_TAG="${RUN_TAG:?Set RUN_TAG to the descriptive campaign tag}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml}"
WORKERS="${WORKERS:-8}"

cd "$VJF"

for event in $EVENTS; do
  echo "===== SBPL UNSEEDED CAMPAIGN: $RUN_TAG $event ====="
  EVENT="$event" \
  CONFIG_DIR="$CONFIG_DIR" \
  RUN_TAG="$RUN_TAG" \
  RESULTS_NAME_TEMPLATE="{event}_{run_tag}" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  ENABLE_PREFLIGHT=1 \
  PREFLIGHT_BURN_LENGTH=1 \
  PREFLIGHT_RUN_LENGTH=1 \
  RUN_FOREGROUND=1 \
  RUN_MINIMIZER=1 \
  MINIMIZE_MODE=walkers \
  MINIMIZE_MAX_WALKERS=0 \
  DRIVE_SYNC_ENABLE=0 \
  WORKERS="$WORKERS" \
  CLEAN_INCOMPLETE=1 \
  SKIP_COMPLETED=1 \
  /bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
done
