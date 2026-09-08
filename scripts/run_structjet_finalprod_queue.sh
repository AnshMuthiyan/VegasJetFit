#!/usr/bin/env bash
set -euo pipefail

# Queue final-production single-CSM-power-law structured-jet fits.
#
# Model intent:
#   - structured power-law jet
#   - Dylan-smoothed spectrum
#   - single power-law CSM
#   - theta_c, theta_v, and electron p thawed
#   - no initial_guess / initial_sigma seed entries
#   - parallel-tempered 10x100 walkers, 5000 burn-in + 5000 production
#   - run one GRB at a time on the host

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="${VJF:-$ROOT/VegasJetFit}"
EVENTS="${EVENTS:-}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/structured_jet_finalprod_unseeded_configs_active}"
RUN_TAG="${RUN_TAG:-structjet_thetav_thetac_electronp_unseeded_finalprod_10temp_5000x5000_v1}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_finalprod_10temp_5000x5000.toml}"
WORKERS="${WORKERS:-8}"

if [ -z "$EVENTS" ]; then
  echo "ERROR: set EVENTS to one or more GRBs, e.g. EVENTS='050922C 090424'." >&2
  exit 2
fi

cd "$VJF"

for event in $EVENTS; do
  echo "===== STRUCTJET FINALPROD: $RUN_TAG $event ====="
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
  MINIMIZE_SCIPY_METHOD=Powell \
  MINIMIZE_FALLBACK_SCIPY_METHOD=Nelder-Mead \
  DRIVE_SYNC_ENABLE=0 \
  WORKERS="$WORKERS" \
  CLEAN_INCOMPLETE=1 \
  SKIP_COMPLETED=1 \
  /bin/bash "$VJF/jwk_run_thesis_reproduction_event.sh"
done
