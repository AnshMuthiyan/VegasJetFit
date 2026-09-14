#!/usr/bin/env bash
set -euo pipefail

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
REMOTE_VJF="${REMOTE_VJF:-/Users/jkeohane/GRBs/VegasJetFit}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
POLL_SECONDS="${POLL_SECONDS:-300}"
WATCH_ONCE="${WATCH_ONCE:-0}"
OUTPUT_DIR="$VJF/reports/2026_09_14_090424_extinction_long_comparison"

variants=(trotter ccm)
hosts=(jkeohane@pauley404-01.local jkeohane@pauley404-02.local)
key_aliases=(100.84.118.63 100.118.36.86)
trotter_restarts=0
ccm_restarts=0

ssh_cmd() {
  local key_alias="$1"
  shift
  ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 \
    -o HostKeyAlias="$key_alias" "$@"
}

ssh_stream() {
  local key_alias="$1"
  shift
  ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 \
    -o HostKeyAlias="$key_alias" "$@"
}

restart_count() {
  case "$1" in
    trotter) echo "$trotter_restarts" ;;
    ccm) echo "$ccm_restarts" ;;
  esac
}

increment_restart_count() {
  case "$1" in
    trotter) trotter_restarts=$((trotter_restarts + 1)) ;;
    ccm) ccm_restarts=$((ccm_restarts + 1)) ;;
  esac
}

resume_if_needed() {
  local host="$1" key_alias="$2" variant="$3" tag="$4"
  local session="extcmp_090424_${variant}_long"
  local checkpoint="$REMOTE_VJF/jetfit/results/$tag/pt_resume_state.npz"
  local count
  count="$(restart_count "$variant")"
  if ssh_cmd "$key_alias" "$host" \
    "tmux has-session -t '$session' 2>/dev/null || pgrep -f '[j]etfit.run.*$tag' >/dev/null"; then
    return 0
  fi
  if ! ssh_cmd "$key_alias" "$host" "test -s '$checkpoint'"; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $variant stopped before its first checkpoint; manual review required"
    return 0
  fi
  if (( count >= 3 )); then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $variant reached the three-restart limit; manual review required"
    return 0
  fi
  ssh_cmd "$key_alias" "$host" "
    tmux new-session -d -s '$session' \
      \"cd '$REMOTE_VJF' && exec caffeinate -is bash scripts/run_090424_extinction_long_variant.sh '$variant'\"
    tmux has-session -t '$session'
  "
  increment_restart_count "$variant"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) resumed $variant from checkpoint (attempt $((count + 1))/3)"
}

pull_complete_result() {
  local host="$1" key_alias="$2" tag="$3"
  local destination="$VJF/jetfit/results/$tag"
  local incoming="$VJF/jetfit/results/.incoming_${tag}_$$"
  if [[ -s "$destination/chain.npz" && -s "$destination/best_fit.json" ]]; then
    return 0
  fi
  mkdir -p "$incoming"
  ssh_stream "$key_alias" "$host" \
    "tar -cf - -C '$REMOTE_VJF/jetfit/results/$tag' ." | tar -xf - -C "$incoming"
  "$PY" - "$incoming" <<'PY'
import json
import sys
from pathlib import Path
import numpy as np

path = Path(sys.argv[1])
with np.load(path / "chain.npz", allow_pickle=False) as archive:
    chain = np.asarray(archive["chain"])
if chain.shape[:2] != (800, 100):
    raise SystemExit(f"Unexpected completed chain shape: {chain.shape}")
json.loads((path / "best_fit.json").read_text())
PY
  if [[ -e "$destination" ]]; then
    mv "$destination" "${destination}.superseded.$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  mv "$incoming" "$destination"
  echo "Pulled and validated $tag from $host at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

mkdir -p "$OUTPUT_DIR" "$VJF/logs"
while :; do
  all_complete=1
  for index in 0 1; do
    variant="${variants[$index]}"
    host="${hosts[$index]}"
    key_alias="${key_aliases[$index]}"
    tag="090424_${variant}_bandpass_verified_5temp_100x800_v1"
    if ssh_cmd "$key_alias" "$host" \
      "test -s '$REMOTE_VJF/jetfit/results/$tag/chain.npz' -a -s '$REMOTE_VJF/jetfit/results/$tag/best_fit.json'"; then
      pull_complete_result "$host" "$key_alias" "$tag"
    else
      all_complete=0
      resume_if_needed "$host" "$key_alias" "$variant" "$tag"
      status="$(ssh_cmd "$key_alias" "$host" \
        "p='$REMOTE_VJF/jetfit/results/$tag/pt_resume_state.npz'; if test -s \"\$p\"; then '$PY' -c 'import sys; import numpy as np; z=np.load(sys.argv[1]); burn=int(z[\"burn_completed_iterations\"]) if \"burn_completed_iterations\" in z.files else 0; print(str(z[\"phase\"].item()), burn, int(z[\"completed_iterations\"]))' \"\$p\"; else echo starting; fi" \
        2>/dev/null || echo unreachable)"
      echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $variant $host $status"
    fi
  done

  if (( all_complete )); then
    "$PY" "$VJF/scripts/compare_090424_bandpass_models.py" \
      --ccm-results "$VJF/jetfit/results/090424_ccm_bandpass_verified_5temp_100x800_v1" \
      --trotter-results "$VJF/jetfit/results/090424_trotter_bandpass_verified_5temp_100x800_v1" \
      --output-dir "$OUTPUT_DIR"
    touch "$OUTPUT_DIR/comparison.complete"
    echo "Comparison complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    exit 0
  fi
  if [[ "$WATCH_ONCE" == "1" ]]; then
    exit 0
  fi
  sleep "$POLL_SECONDS"
done
