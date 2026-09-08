#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
LAUNCHER="${LAUNCHER:-$VEGAS_DIR/scripts/start_structured_jet_all_2000.sh}"
SESSION_NAME="${SESSION_NAME:-lab_structured_jet_wait}"
POLL_MINUTES="${POLL_MINUTES:-15}"
WAIT_FAMILY="${WAIT_FAMILY:-all}"

PL_SOURCE_RUN_TAG="${PL_SOURCE_RUN_TAG:-thetacfree_dylanphyspriors_init5pct_2000x2000_v1}"
SBPL_SOURCE_RUN_TAG="${SBPL_SOURCE_RUN_TAG:-thetacfree_dylan_sbpl_init5pct_2000x2000_v1}"
RESULTS_ROOT="${RESULTS_ROOT:-$VEGAS_DIR/jetfit/results}"

PL_EVENTS=(
  221009A 220101A 210905A 171010A 160131A 140506A 131030A
  130612A 111228A 090618 090424 050922C 050525A
)
SBPL_EVENTS=(080413B 080319B)

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -x "$LAUNCHER" ]; then
  echo "ERROR: launcher not executable: $LAUNCHER" >&2
  exit 2
fi

ready_check() {
  "$PYTHON_BIN" - <<'PY' "$RESULTS_ROOT" "$PL_SOURCE_RUN_TAG" "$SBPL_SOURCE_RUN_TAG" "$WAIT_FAMILY" "${PL_EVENTS[*]}" "${SBPL_EVENTS[*]}"
from pathlib import Path
import json
import math
import sys

results_root = Path(sys.argv[1])
pl_tag = sys.argv[2]
sbpl_tag = sys.argv[3]
wait_family = sys.argv[4]
pl_events = sys.argv[5].split()
sbpl_events = sys.argv[6].split()

missing: list[str] = []

def valid(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return False
    return payload.get("success") is True and math.isfinite(float(payload.get("nmap", float("nan"))))

if wait_family in {"all", "pl"}:
    for event in pl_events:
        path = results_root / f"{event}_thesis_reproduction_{pl_tag}" / "minimized" / "minimized.json"
        if not valid(path):
            missing.append(event)

if wait_family in {"all", "sbpl"}:
    for event in sbpl_events:
        path = results_root / f"{event}_{sbpl_tag}" / "minimized" / "minimized.json"
        if not valid(path):
            missing.append(event)

if missing:
    print("WAIT", " ".join(missing))
    raise SystemExit(1)

print("READY")
PY
}

while true; do
  stamp="$(date)"
  if ready_check; then
    echo "[$stamp] source runs complete; launching structured-jet queue"
    exec bash "$LAUNCHER"
  fi

  echo "[$stamp] waiting ${POLL_MINUTES}m for theta_c-free source minimizations"
  sleep "$((POLL_MINUTES * 60))"
done
