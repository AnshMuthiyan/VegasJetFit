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
TRACKING_SHEET="${TRACKING_SHEET:-$ROOT/tmp/spreadsheets/grb_tracking.csv}"
TRACKING_SHEET_NAME="${TRACKING_SHEET_NAME:-}"
TRACKING_EVENT_COLUMN="${TRACKING_EVENT_COLUMN:-GRB (Priority Order)}"
TRACKING_STATUS_COLUMN="${TRACKING_STATUS_COLUMN:-Restart2000 Status}"
TRACKING_RESOURCES_DIR="${TRACKING_RESOURCES_DIR:-$VEGAS_DIR/jetfit/resources/grbs}"

LYRA_EVENTS="${LYRA_EVENTS:-171010A 130612A 080413B}"
PAULEY404_01_EVENTS="${PAULEY404_01_EVENTS:-221009A 160131A 111228A 080319B}"
PAULEY404_02_EVENTS="${PAULEY404_02_EVENTS:-220101A 140506A 090618 050922C}"
PAULEY404_03_EVENTS="${PAULEY404_03_EVENTS:-210905A 131030A 090424 050525A}"
STATUS_EVENTS="${STATUS_EVENTS:-221009A 220101A 210905A 171010A 160131A 140506A 131030A 130612A 111228A 090618 090424 080413B 080319B 050922C 050525A}"

OLD_RUN_TAG="${OLD_RUN_TAG:-theta1p0_thesis_short_kmin10_seeded_vegasv201_dylanspec_v3}"

mkdir -p "$LOG_DIR"

build_queues_from_tracking_sheet() {
  [ -f "$TRACKING_SHEET" ] || return 1
  local queue_exports
  queue_exports="$("$ROOT/.venv/bin/python" - <<'PY' \
    "$TRACKING_SHEET" "$TRACKING_EVENT_COLUMN" "$TRACKING_RESOURCES_DIR"
from pathlib import Path
import csv
import pandas as pd
import re
import shlex
import sys

tracking_path = Path(sys.argv[1])
event_column = sys.argv[2]
resources_dir = Path(sys.argv[3])
aliases = {"161031A": "160131A"}
host_envs = [
    ("pauley404-01", "PAULEY404_01_EVENTS"),
    ("pauley404-02", "PAULEY404_02_EVENTS"),
    ("pauley404-03", "PAULEY404_03_EVENTS"),
    ("lyra", "LYRA_EVENTS"),
]

def normalize(value: str) -> str | None:
    text = str(value).strip()
    if not text:
        return None
    text = aliases.get(text, text)
    if re.fullmatch(r"\d{6}[A-Z]?", text):
        return text
    return None

if tracking_path.suffix.lower() == ".csv":
    frame = pd.read_csv(tracking_path)
else:
    frame = pd.read_excel(tracking_path, sheet_name=0, engine="openpyxl")

source_column = event_column if event_column in frame.columns else frame.columns[0]
events = []
seen = set()
for raw_value in frame[source_column].tolist():
    event = normalize(raw_value)
    if not event or event in seen:
        continue
    if not (resources_dir / event).is_dir():
        continue
    seen.add(event)
    events.append(event)

extra_events = []
for path in sorted(resources_dir.iterdir()):
    if not path.is_dir():
        continue
    event = normalize(path.name)
    if not event or event in seen:
        continue
    seen.add(event)
    extra_events.append(event)

events.extend(extra_events)

assignments = {env_name: [] for _, env_name in host_envs}
for idx, event in enumerate(events):
    _, env_name = host_envs[idx % len(host_envs)]
    assignments[env_name].append(event)

for _, env_name in host_envs:
    print(f"{env_name}={shlex.quote(' '.join(assignments[env_name]))}")
print(f"STATUS_EVENTS={shlex.quote(' '.join(events))}")
PY
  )" || return 1
  eval "$queue_exports"
}

if ! build_queues_from_tracking_sheet; then
  echo "WARN: using fallback hard-coded GRB queues; tracking sheet unavailable: $TRACKING_SHEET" >&2
fi

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
  "cd '$ROOT' && /usr/bin/caffeinate -is env ROOT='$ROOT' VEGAS_DIR='$VEGAS_DIR' RUN_TAG='$RUN_TAG' SOURCE_RESULTS_TAG='$SOURCE_RESULTS_TAG' MCMC_SETTINGS='$MCMC_SETTINGS' INTERVAL_MIN='$INTERVAL_MIN' DURATION_HOURS='$DURATION_HOURS' WORKERS='$WORKERS' KEEP_AWAKE='$KEEP_AWAKE' SEED_BEST_FIT_ROOT='$SEED_BEST_FIT_ROOT' SEED_OWNER_SUBDIR='$SEED_OWNER_SUBDIR' TRACKING_SHEET='$TRACKING_SHEET' TRACKING_SHEET_NAME='$TRACKING_SHEET_NAME' TRACKING_EVENT_COLUMN='$TRACKING_EVENT_COLUMN' TRACKING_STATUS_COLUMN='$TRACKING_STATUS_COLUMN' LYRA_EVENTS='$LYRA_EVENTS' PAULEY404_01_EVENTS='$PAULEY404_01_EVENTS' PAULEY404_02_EVENTS='$PAULEY404_02_EVENTS' PAULEY404_03_EVENTS='$PAULEY404_03_EVENTS' STATUS_EVENTS='$STATUS_EVENTS' bash '$WATCHER' > '$WATCH_LOG' 2>&1"

echo "$SESSION_NAME"
echo "$WATCH_LOG"
