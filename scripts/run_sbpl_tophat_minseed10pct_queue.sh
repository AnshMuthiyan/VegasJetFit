#!/usr/bin/env bash
set -euo pipefail

# Queue wide top-hat smoothly-broken CSM fits using Dylan's two-pass recipe.
# Pass 1 was the broad-prior unseeded SBPL top-hat campaign.
# Pass 2 starts walkers at the pass-1 minimized values with initial_sigma set
# to 10% of each bounded prior range in fit-space.

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="${VJF:-$ROOT/VegasJetFit}"
EVENTS="${EVENTS:-080319B 080413B}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/sbpl_tophat_theta1p0_minseed10pct_configs_active}"
RUN_TAG="${RUN_TAG:-sbpl_tophat_theta1p0_minseed10pct_2000x2000_v1}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml}"
WORKERS="${WORKERS:-8}"
RUN_MINIMIZER="${RUN_MINIMIZER:-1}"

cd "$VJF"

for event in $EVENTS; do
  echo "===== SBPL TOPHAT MIN-SEED-10PCT: $RUN_TAG $event ====="
  EVENT="$event" \
  CONFIG_DIR="$CONFIG_DIR" \
  RUN_TAG="$RUN_TAG" \
  RESULTS_NAME_TEMPLATE="{event}_{run_tag}" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  ENABLE_PREFLIGHT=1 \
  PREFLIGHT_BURN_LENGTH=1 \
  PREFLIGHT_RUN_LENGTH=1 \
  RUN_FOREGROUND=1 \
  RUN_MINIMIZER="$RUN_MINIMIZER" \
  MINIMIZE_MODE=walkers \
  MINIMIZE_MAX_WALKERS=0 \
  MINIMIZE_SCIPY_METHOD=Powell \
  MINIMIZE_FALLBACK_SCIPY_METHOD=Nelder-Mead \
  DRIVE_SYNC_ENABLE=0 \
  WORKERS="$WORKERS" \
  CLEAN_INCOMPLETE=1 \
  SKIP_COMPLETED=1 \
  /bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
done
