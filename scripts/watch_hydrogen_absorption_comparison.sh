#!/usr/bin/env bash
set -euo pipefail

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
REMOTE_VJF="${REMOTE_VJF:-/Users/jkeohane/GRBs/VegasJetFit}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
P03_HOST="${P03_HOST:-pauley404-03}"
POLL_SECONDS="${POLL_SECONDS:-300}"
WATCH_ONCE="${WATCH_ONCE:-0}"
LOCAL_REPORT="$VJF/reports/2026_09_15_hydrogen_absorption_comparison"
SHARE_REPORT="${SHARE_REPORT:-/Users/jkeohane/GRBs/Share_Folder/Reports/Meeting_Books/26_09_15__hydrogen_absorption_comparison}"
variants=(none igm igm_host)
local_restarts=0
remote_restarts=0

ssh_cmd() {
  ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 "$@"
}

ssh_stream() {
  ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 "$@"
}

complete_local() {
  local event="$1" variant="$2" stage="$3" dimensions
  [[ "$stage" == smoke ]] && dimensions=2x3 || dimensions=25x100
  local tag="${event}_hydrogen_${variant}_bandpass_verified_5temp_${dimensions}_v1"
  [[ -s "$VJF/jetfit/results/$tag/chain.npz" && \
     -s "$VJF/jetfit/results/$tag/best_fit.json" ]] && \
    grep -q '^Completed ' "$VJF/logs/$tag.log" 2>/dev/null
}

complete_remote() {
  local event="$1" variant="$2" stage="$3" dimensions
  [[ "$stage" == smoke ]] && dimensions=2x3 || dimensions=25x100
  local tag="${event}_hydrogen_${variant}_bandpass_verified_5temp_${dimensions}_v1"
  ssh_cmd "$P03_HOST" \
    "test -s '$REMOTE_VJF/jetfit/results/$tag/chain.npz' -a -s '$REMOTE_VJF/jetfit/results/$tag/best_fit.json' && grep -q '^Completed ' '$REMOTE_VJF/logs/$tag.log'"
}

event_complete_local() {
  local event="$1"
  for stage in smoke diagnostic; do
    for variant in "${variants[@]}"; do
      complete_local "$event" "$variant" "$stage" || return 1
    done
  done
}

event_complete_remote() {
  local event="$1"
  for stage in smoke diagnostic; do
    for variant in "${variants[@]}"; do
      complete_remote "$event" "$variant" "$stage" || return 1
    done
  done
}

start_local_sequence() {
  tmux new-session -d -s hydrogen_absorption_220101A \
    "cd '$VJF' && exec caffeinate -is env WORKERS=8 bash scripts/run_hydrogen_absorption_sequence.sh 220101A"
}

start_remote_sequence() {
  ssh_cmd "$P03_HOST" \
    "tmux new-session -d -s hydrogen_absorption_160131A \"cd '$REMOTE_VJF' && exec caffeinate -is env WORKERS=8 bash scripts/run_hydrogen_absorption_sequence.sh 160131A\""
}

pull_remote_result() {
  local variant="$1" stage="$2" dimensions tag destination incoming
  [[ "$stage" == smoke ]] && dimensions=2x3 || dimensions=25x100
  tag="160131A_hydrogen_${variant}_bandpass_verified_5temp_${dimensions}_v1"
  destination="$VJF/jetfit/results/$tag"
  incoming="$VJF/jetfit/results/.incoming_${tag}_$$"
  if [[ -s "$destination/chain.npz" && -s "$destination/best_fit.json" ]]; then
    return 0
  fi
  mkdir -p "$incoming"
  ssh_stream "$P03_HOST" \
    "tar -cf - -C '$REMOTE_VJF/jetfit/results/$tag' ." | tar -xf - -C "$incoming"
  ssh_stream "$P03_HOST" "cat '$REMOTE_VJF/logs/$tag.log'" >"$incoming/run.log"
  "$PY" - "$incoming" "$stage" <<'PY'
import json
import sys
from pathlib import Path
import numpy as np

path = Path(sys.argv[1])
expected_steps = 3 if sys.argv[2] == "smoke" else 100
with np.load(path / "chain.npz", allow_pickle=False) as archive:
    chain = np.asarray(archive["chain"])
if chain.shape[0:2] != (expected_steps, 100):
    raise SystemExit(f"Unexpected completed chain shape: {chain.shape}")
json.loads((path / "best_fit.json").read_text())
if not any(line.startswith("real ") for line in (path / "run.log").read_text().splitlines()):
    raise SystemExit("Timing log is incomplete.")
PY
  if [[ -e "$destination" ]]; then
    mv "$destination" "${destination}.superseded.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  mv "$incoming" "$destination"
  cp "$destination/run.log" "$VJF/logs/$tag.log"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) pulled $tag"
}

status_line_local() {
  local state="$VJF/jetfit/results/220101A_hydrogen_${1}_bandpass_verified_5temp_${2}_v1/pt_resume_state.npz"
  if [[ -s "$state" ]]; then
    "$PY" - "$state" <<'PY'
import sys
import numpy as np
with np.load(sys.argv[1], allow_pickle=False) as z:
    print(str(z["phase"].item()), int(z.get("burn_completed_iterations", 0)), int(z["completed_iterations"]))
PY
  else
    echo pending
  fi
}

mkdir -p "$VJF/logs"
while :; do
  if ! event_complete_local 220101A; then
    if ! tmux has-session -t hydrogen_absorption_220101A 2>/dev/null && \
       ! pgrep -f '[j]etfit.run.*220101A_hydrogen_' >/dev/null; then
      if (( local_restarts < 3 )); then
        start_local_sequence
        local_restarts=$((local_restarts + 1))
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) restarted Lyra sequence attempt=$local_restarts"
      else
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Lyra sequence needs manual review"
      fi
    fi
  fi

  if ! event_complete_remote 160131A; then
    if ! ssh_cmd "$P03_HOST" \
      "tmux has-session -t hydrogen_absorption_160131A 2>/dev/null || pgrep -f '[j]etfit.run.*160131A_hydrogen_' >/dev/null"; then
      if (( remote_restarts < 3 )); then
        start_remote_sequence
        remote_restarts=$((remote_restarts + 1))
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) restarted Pauley-03 sequence attempt=$remote_restarts"
      else
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Pauley-03 sequence needs manual review"
      fi
    fi
  fi

  for stage in smoke diagnostic; do
    for variant in "${variants[@]}"; do
      if complete_remote 160131A "$variant" "$stage"; then
        pull_remote_result "$variant" "$stage"
      fi
    done
  done

  if event_complete_local 220101A && event_complete_remote 160131A; then
    mkdir -p "$LOCAL_REPORT"
    "$PY" "$VJF/scripts/write_hydrogen_absorption_comparison_report.py" \
      --output-dir "$LOCAL_REPORT" --compile
    incoming="${SHARE_REPORT}.incoming.$$"
    if [[ -e "$incoming" ]]; then
      echo "Refusing to replace unexpected staging directory: $incoming" >&2
      exit 1
    fi
    mkdir -p "$(dirname "$SHARE_REPORT")"
    cp -R "$LOCAL_REPORT" "$incoming"
    if [[ -e "$SHARE_REPORT" ]]; then
      mv "$SHARE_REPORT" "${SHARE_REPORT}.superseded.$(date -u +%Y%m%dT%H%M%SZ)"
    fi
    mv "$incoming" "$SHARE_REPORT"
    touch "$SHARE_REPORT/comparison.complete"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) comparison report complete at $SHARE_REPORT"
    exit 0
  fi

  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) active local=$(tmux has-session -t hydrogen_absorption_220101A 2>/dev/null && echo yes || echo no) remote=$(ssh_cmd "$P03_HOST" 'tmux has-session -t hydrogen_absorption_160131A 2>/dev/null && echo yes || echo no' 2>/dev/null || echo unreachable)"
  if [[ "$WATCH_ONCE" == 1 ]]; then
    exit 0
  fi
  sleep "$POLL_SECONDS"
done
