#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
WATCHER="${WATCHER:-$ROOT/lab_watch_tophat_dylanspec_mcmc_queue.sh}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$ROOT/lab_sync_fit_stack.sh}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
BUILDER="${BUILDER:-$VEGAS_DIR/scripts/build_thetacfree_powerlaw_configs.py}"
CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/thesis_reproduction_configs_thetacfree_dylanphyspriors_init5pct_active}"

SESSION_NAME="${SESSION_NAME:-lab_thetacfree_powerlaw_2000_watch}"
LOG_DIR="${LOG_DIR:-$ROOT/tmp/lab_fit_sync/logs}"
WATCH_LOG="${WATCH_LOG:-$LOG_DIR/${SESSION_NAME}_$(date -u +%Y%m%dT%H%M%SZ).log}"
AUDIT_CSV="${AUDIT_CSV:-$LOG_DIR/${SESSION_NAME}_audit_$(date -u +%Y%m%dT%H%M%SZ).csv}"

RUN_TAG="${RUN_TAG:-thetacfree_dylanphyspriors_init5pct_2000x2000_v1}"
SOURCE_RUN_TAG="${SOURCE_RUN_TAG:-theta1p0_thesis_reproduction_dylanphyspriors_init5pct_2000x2000_v1}"
RESULTS_NAME_TEMPLATE="${RESULTS_NAME_TEMPLATE:-{event}_thesis_reproduction_{run_tag}}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml}"

INTERVAL_MIN="${INTERVAL_MIN:-15}"
DURATION_HOURS="${DURATION_HOURS:-336}"
HOSTS="${HOSTS:-pauley404-01 pauley404-02 pauley404-03}"
WORKERS="${WORKERS:-8}"
SYNC_FIRST="${SYNC_FIRST:-1}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"

THETA_C_INITIAL_SIGMA="${THETA_C_INITIAL_SIGMA:-0.05}"
THETA_C_LOWER_FLOOR="${THETA_C_LOWER_FLOOR:-0.001}"

LYRA_EVENTS="${LYRA_EVENTS:-130612A 140506A 050922C}"
PAULEY404_01_EVENTS="${PAULEY404_01_EVENTS:-221009A 171010A 160131A}"
PAULEY404_02_EVENTS="${PAULEY404_02_EVENTS:-220101A 111228A 090618}"
PAULEY404_03_EVENTS="${PAULEY404_03_EVENTS:-210905A 131030A 090424 050525A}"
STATUS_EVENTS="${STATUS_EVENTS:-221009A 220101A 210905A 171010A 160131A 140506A 131030A 130612A 111228A 090618 090424 050922C 050525A}"

mkdir -p "$LOG_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -x "$WATCHER" ]; then
  echo "ERROR: watcher not executable: $WATCHER" >&2
  exit 2
fi
if [ ! -x "$SYNC_SCRIPT" ]; then
  echo "ERROR: sync script not executable: $SYNC_SCRIPT" >&2
  exit 2
fi
if [ ! -f "$BUILDER" ]; then
  echo "ERROR: builder not found: $BUILDER" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings file not found: $MCMC_SETTINGS" >&2
  exit 2
fi

ALL_EVENTS=(
  050525A 050922C 090424 090618 111228A 130612A 131030A
  140506A 160131A 171010A 210905A 220101A 221009A
)

echo "=================================================="
echo "Preparing theta_c-free powerlaw queue"
echo "Run tag:          $RUN_TAG"
echo "Source run tag:   $SOURCE_RUN_TAG"
echo "Config dir:       $CONFIG_DIR"
echo "MCMC settings:    $MCMC_SETTINGS"
echo "theta_c sigma:    $THETA_C_INITIAL_SIGMA"
echo "theta_c floor:    $THETA_C_LOWER_FLOOR"
echo "Events:           ${ALL_EVENTS[*]}"
echo "=================================================="

"$PYTHON_BIN" "$BUILDER" \
  --vegas-dir "$VEGAS_DIR" \
  --source-config-dir "$VEGAS_DIR/thesis_reproduction_configs_dylanphyspriors_init5pct_active" \
  --output-dir "$CONFIG_DIR" \
  --source-run-tag "$SOURCE_RUN_TAG" \
  --results-name-template "{event}_thesis_reproduction_{run_tag}" \
  --results-root "$VEGAS_DIR/jetfit/results" \
  --events "${ALL_EVENTS[@]}" \
  --audit-csv "$AUDIT_CSV" \
  --theta-c-initial-sigma "$THETA_C_INITIAL_SIGMA" \
  --theta-c-lower-floor "$THETA_C_LOWER_FLOOR"

if [ "$SYNC_FIRST" = "1" ]; then
  HOSTS="$HOSTS" "$SYNC_SCRIPT"
fi

tmux has-session -t "$SESSION_NAME" >/dev/null 2>&1 && tmux kill-session -t "$SESSION_NAME"

tmux new-session -d -s "$SESSION_NAME" \
  "cd '$ROOT' && /usr/bin/caffeinate -is env ROOT='$ROOT' VEGAS_DIR='$VEGAS_DIR' EVENT_RUNNER='$VEGAS_DIR/jwk_run_thesis_reproduction_event.sh' CONFIG_DIR='$CONFIG_DIR' RUN_TAG='$RUN_TAG' SOURCE_RESULTS_TAG='$SOURCE_RUN_TAG' RESULTS_NAME_TEMPLATE='$RESULTS_NAME_TEMPLATE' SOURCE_NAME_TEMPLATE='' MCMC_SETTINGS='$MCMC_SETTINGS' INTERVAL_MIN='$INTERVAL_MIN' DURATION_HOURS='$DURATION_HOURS' WORKERS='$WORKERS' KEEP_AWAKE='$KEEP_AWAKE' SYNC_SOURCE_INPUTS='0' LYRA_EVENTS='$LYRA_EVENTS' PAULEY404_01_EVENTS='$PAULEY404_01_EVENTS' PAULEY404_02_EVENTS='$PAULEY404_02_EVENTS' PAULEY404_03_EVENTS='$PAULEY404_03_EVENTS' STATUS_EVENTS='$STATUS_EVENTS' bash '$WATCHER' > '$WATCH_LOG' 2>&1"

echo "$SESSION_NAME"
echo "$WATCH_LOG"
