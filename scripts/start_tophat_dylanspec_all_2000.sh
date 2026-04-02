#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
WATCHER="${WATCHER:-$ROOT/lab_watch_tophat_dylanspec_mcmc_queue.sh}"
SYNC_SCRIPT="${SYNC_SCRIPT:-$ROOT/lab_sync_fit_stack.sh}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
SESSION_NAME="${SESSION_NAME:-lab_tophat_dylanspec_all_2000_watch}"
LOG_DIR="${LOG_DIR:-$ROOT/tmp/lab_fit_sync/logs}"
WATCH_LOG="${WATCH_LOG:-$LOG_DIR/${SESSION_NAME}_$(date -u +%Y%m%dT%H%M%SZ).log}"

RUN_TAG="${RUN_TAG:-theta1p0_thesis_short_kmin10_seeded_vegasv201_dylanspec_restart2000}"
SOURCE_RESULTS_TAG="${SOURCE_RESULTS_TAG:-theta1p0_resume5k}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml}"
INTERVAL_MIN="${INTERVAL_MIN:-30}"
DURATION_HOURS="${DURATION_HOURS:-336}"
HOSTS="${HOSTS:-pauley404-01 pauley404-02 pauley404-03}"
WORKERS="${WORKERS:-8}"
SYNC_FIRST="${SYNC_FIRST:-1}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
SEED_BEST_FIT_ROOT="${SEED_BEST_FIT_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
SEED_OWNER_SUBDIR="${SEED_OWNER_SUBDIR:-jkeohane}"

LYRA_EVENTS="${LYRA_EVENTS:-171010A 130612A 080413B}"
PAULEY404_01_EVENTS="${PAULEY404_01_EVENTS:-221009A 160131A 111228A 080319B}"
PAULEY404_02_EVENTS="${PAULEY404_02_EVENTS:-220101A 140506A 090618 050922C}"
PAULEY404_03_EVENTS="${PAULEY404_03_EVENTS:-210905A 131030A 090424 050525A}"
STATUS_EVENTS="${STATUS_EVENTS:-221009A 220101A 210905A 171010A 160131A 140506A 131030A 130612A 111228A 090618 090424 080413B 080319B 050922C 050525A}"

OLD_RUN_TAG="${OLD_RUN_TAG:-theta1p0_thesis_short_kmin10_seeded_vegasv201_dylanspec_v3}"

mkdir -p "$LOG_DIR"

if [ ! -x "$WATCHER" ]; then
  echo "ERROR: watcher not executable: $WATCHER" >&2
  exit 2
fi
if [ ! -x "$SYNC_SCRIPT" ]; then
  echo "ERROR: sync script not executable: $SYNC_SCRIPT" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings file not found: $MCMC_SETTINGS" >&2
  exit 2
fi

if [ "$SYNC_FIRST" = "1" ]; then
  HOSTS="$HOSTS" "$SYNC_SCRIPT"
fi

tmux has-session -t lab_tophat_dylanspec_v3_5day_watch >/dev/null 2>&1 && tmux kill-session -t lab_tophat_dylanspec_v3_5day_watch
tmux has-session -t "$SESSION_NAME" >/dev/null 2>&1 && tmux kill-session -t "$SESSION_NAME"
for session in $(tmux list-sessions -F '#S' 2>/dev/null | egrep '^(lyra|lab)_tophat_dylanspec_(mcmc|min)_' || true); do
  tmux kill-session -t "$session" >/dev/null 2>&1 || true
done

pkill -f "$RUN_TAG" >/dev/null 2>&1 || true
pkill -f "$OLD_RUN_TAG" >/dev/null 2>&1 || true
pkill -f 'lab_watch_tophat_dylanspec_mcmc_queue.sh' >/dev/null 2>&1 || true
pkill -f 'jwk_run_tophat_dylanspec_mcmc_event.sh' >/dev/null 2>&1 || true
pkill -f 'scripts/minimize.py --results .*dylanspec_' >/dev/null 2>&1 || true

for host in pauley404-01 pauley404-02 pauley404-03; do
  ssh -o BatchMode=yes "$host" \
    "pkill -f '$RUN_TAG' >/dev/null 2>&1 || true; \
     pkill -f '$OLD_RUN_TAG' >/dev/null 2>&1 || true; \
     pkill -f 'jwk_run_tophat_dylanspec_mcmc_event.sh' >/dev/null 2>&1 || true; \
     pkill -f 'scripts/minimize.py --results .*dylanspec_' >/dev/null 2>&1 || true"
done

tmux new-session -d -s "$SESSION_NAME" \
  "cd '$ROOT' && /usr/bin/caffeinate -is env ROOT='$ROOT' VEGAS_DIR='$VEGAS_DIR' RUN_TAG='$RUN_TAG' SOURCE_RESULTS_TAG='$SOURCE_RESULTS_TAG' MCMC_SETTINGS='$MCMC_SETTINGS' INTERVAL_MIN='$INTERVAL_MIN' DURATION_HOURS='$DURATION_HOURS' WORKERS='$WORKERS' KEEP_AWAKE='$KEEP_AWAKE' SEED_BEST_FIT_ROOT='$SEED_BEST_FIT_ROOT' SEED_OWNER_SUBDIR='$SEED_OWNER_SUBDIR' LYRA_EVENTS='$LYRA_EVENTS' PAULEY404_01_EVENTS='$PAULEY404_01_EVENTS' PAULEY404_02_EVENTS='$PAULEY404_02_EVENTS' PAULEY404_03_EVENTS='$PAULEY404_03_EVENTS' STATUS_EVENTS='$STATUS_EVENTS' bash '$WATCHER' > '$WATCH_LOG' 2>&1"

echo "$SESSION_NAME"
echo "$WATCH_LOG"
