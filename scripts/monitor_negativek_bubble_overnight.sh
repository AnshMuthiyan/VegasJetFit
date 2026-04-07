#!/usr/bin/env bash
set -u

ROOT="${ROOT:-/Users/jkeohane/GRBs/VegasJetFit}"
RUN_TAG="${RUN_TAG:-theta1p0_thesis_full}"
EVENTS="${EVENTS:-080413B 140506A 210905A}"
SLEEP_SECONDS="${SLEEP_SECONDS:-900}"
MAX_CHECKS="${MAX_CHECKS:-96}"

for _ in $(seq 1 "$MAX_CHECKS"); do
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[$ts] overnight_status"

  for ev in $EVENTS; do
    run_dir="$ROOT/jetfit/results/${ev}_bubble_tophat_${RUN_TAG}"
    log_file="$ROOT/logs/${ev}.bubble.log"

    if [ -f "$run_dir/best_fit.json" ]; then
      min_state="no"
      [ -f "$run_dir/minimized/minimized.json" ] && min_state="yes"
      echo "  $ev: DONE best_fit=yes minimized=$min_state"
    elif [ -d "$run_dir" ]; then
      chain_state="no"
      [ -f "$run_dir/chain.npz" ] && chain_state="yes"
      echo "  $ev: IN_PROGRESS run_dir=yes chain=$chain_state"
    else
      echo "  $ev: NOT_STARTED"
    fi

    if [ -f "$log_file" ]; then
      last_line="$(tail -n 1 "$log_file" 2>/dev/null | tr -d '\r')"
      if [ -z "$last_line" ]; then
        last_line="<empty>"
      fi
      echo "    log_tail: $last_line"
    fi
  done

  echo

  all_done=1
  for ev in $EVENTS; do
    run_dir="$ROOT/jetfit/results/${ev}_bubble_tophat_${RUN_TAG}"
    if [ ! -f "$run_dir/best_fit.json" ]; then
      all_done=0
      break
    fi
  done
  if [ "$all_done" -eq 1 ]; then
    echo "All requested bubble runs have best_fit.json; stopping monitor."
    break
  fi

  sleep "$SLEEP_SECONDS"
done
