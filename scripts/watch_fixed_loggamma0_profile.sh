#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-pauley404-03}"
VJF="${VJF:-/Users/jkeohane/GRBs/VegasJetFit}"
RESULTS_ROOT="${RESULTS_ROOT:-$VJF/jetfit/results}"
RUN_TAG="${RUN_TAG:-core_logangle_powerlawcsm_080413B_fixed_loggamma0_profile_v1}"
OUT_DIR="${OUT_DIR:-/Users/jkeohane/GRBs/Share_Folder/Fits/shorter_diagnostic_runs/prior_tests/26_09_08__080413B__fixed_logGamma0_profile}"
POLL_SECONDS="${POLL_SECONDS:-300}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
LOGGAMMAS=(3 4 5 6 7 8)

mkdir -p "$OUT_DIR"
cp "$VJF/fixed_loggamma0_profile_configs/080413B_20260908/profile_provenance.json" "$OUT_DIR/"
cp "$VJF/obs_overrides/080413B_fixed_loggamma0_profile_20260908.csv" "$OUT_DIR/obs.csv"

while true; do
  terminal=0
  if ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15 "$REMOTE_HOST" \
    "tmux has-session -t grb_080413B_gamma_profile 2>/dev/null"; then
    remote_session_alive=1
  else
    remote_session_alive=0
  fi
  for loggamma in "${LOGGAMMAS[@]}"; do
    run_name="080413B_loggamma0_${loggamma}_${RUN_TAG}"
    local_dir="$RESULTS_ROOT/$run_name"
    remote_dir="$RESULTS_ROOT/$run_name"
    mkdir -p "$local_dir" "$OUT_DIR/loggamma0_${loggamma}"
    state="$(ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15 "$REMOTE_HOST" \
      "if test -f '$remote_dir/.profile_minimization_complete'; then echo complete; elif test -f '$remote_dir/.profile_minimization_failed'; then echo failed; fi" || true)"
    if [ -n "$state" ]; then
      if ssh -n -x -o ForwardX11=no -o BatchMode=yes "$REMOTE_HOST" "test -d '$remote_dir/minimized'"; then
        rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes" \
          "$REMOTE_HOST:$remote_dir/minimized/" "$local_dir/minimized/"
      fi
      touch "$local_dir/.profile_minimization_${state}"
      rsync -az "$local_dir/model.toml" "$local_dir/obs.csv" "$local_dir/best_fit.json" \
        "$local_dir"/.profile_minimization_* "$OUT_DIR/loggamma0_${loggamma}/"
      if [ -d "$local_dir/minimized" ]; then
        rsync -az "$local_dir/minimized" "$OUT_DIR/loggamma0_${loggamma}/"
      fi
      terminal=$((terminal + 1))
    elif [ "$remote_session_alive" -eq 0 ]; then
      touch "$local_dir/.profile_minimization_failed"
      rsync -az "$local_dir/model.toml" "$local_dir/obs.csv" "$local_dir/best_fit.json" \
        "$local_dir/.profile_minimization_failed" "$OUT_DIR/loggamma0_${loggamma}/"
      terminal=$((terminal + 1))
    fi
  done

  "$PY" "$VJF/scripts/summarize_fixed_loggamma0_profile.py" \
    --results-root "$RESULTS_ROOT" \
    --run-tag "$RUN_TAG" \
    --loggammas "${LOGGAMMAS[@]}" \
    --out-dir "$OUT_DIR"
  printf '[%s] terminal=%s/%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$terminal" "${#LOGGAMMAS[@]}"
  if [ "$terminal" -eq "${#LOGGAMMAS[@]}" ]; then
    touch "$OUT_DIR/profile_grid.complete"
    exit 0
  fi
  sleep "$POLL_SECONDS"
done
