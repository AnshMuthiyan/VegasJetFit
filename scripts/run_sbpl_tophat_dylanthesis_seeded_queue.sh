#!/usr/bin/env bash
set -euo pipefail

# Superseded queue for wide top-hat smoothly-broken CSM fits seeded at Dylan
# thesis medians.
#
# This is intentionally guarded because Dylan's two-pass thesis workflow seeds
# the second pass at the first-pass best-fit/minimized position, not at the
# posterior table medians. Use run_sbpl_tophat_minseed10pct_queue.sh instead.
#
# Campaign intent:
#   - wide top-hat jet: theta_c = 1 rad, theta_v = 0
#   - smoothly broken power-law CSM
#   - broad prior boxes copied from the unseeded SBPL top-hat campaign
#   - initial_guess values set to Dylan thesis medians
#   - initial_sigma values set to 5% of each fitted prior range
#   - parallel-tempered 5x100 walkers, 2000 burn-in + 2000 production

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="${VJF:-$ROOT/VegasJetFit}"
EVENTS="${EVENTS:-080319B 080413B}"
CONFIG_DIR="${CONFIG_DIR:-$VJF/sbpl_tophat_theta1p0_dylanthesis_seeded_configs_active}"
RUN_TAG="${RUN_TAG:-sbpl_tophat_theta1p0_dylanthesis_seeded_2000x2000_v1}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VJF/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml}"
WORKERS="${WORKERS:-8}"
RUN_MINIMIZER="${RUN_MINIMIZER:-1}"

if [[ "${ALLOW_SUPERSEDED_MEDIAN_SEEDED:-0}" != "1" ]]; then
  cat >&2 <<'EOF'
ERROR: This thesis-median-seeded queue is superseded.

Dylan's two-pass workflow is broad physical priors first, then a second
independent pass initialized in a 10% region centered on the first-pass
best-fit/minimized position.

Use scripts/run_sbpl_tophat_minseed10pct_queue.sh instead, or set
ALLOW_SUPERSEDED_MEDIAN_SEEDED=1 if you intentionally want the older
median-seeded diagnostic.
EOF
  exit 2
fi

cd "$VJF"

for event in $EVENTS; do
  echo "===== SBPL TOPHAT DYLAN-THESIS SEEDED: $RUN_TAG $event ====="
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
