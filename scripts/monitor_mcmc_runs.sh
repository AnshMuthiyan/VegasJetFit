#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs/VegasJetFit}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
RESULTS_DIR="${RESULTS_DIR:-$ROOT/jetfit/results}"
DRIVE_ROOT="${DRIVE_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
EVENT_FILTER="${EVENT_FILTER:-}"

if [ "${1:-}" = "--event" ]; then
  EVENT_FILTER="${2:-}"
  shift 2 || true
fi

now_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
now_epoch="$(date +%s)"

printf 'MCMC Monitor Snapshot: %s\n' "$now_utc"
printf 'Root: %s\n' "$ROOT"
printf 'Logs: %s\n' "$LOG_DIR"
printf 'Results: %s\n' "$RESULTS_DIR"
printf 'Drive: %s\n' "$DRIVE_ROOT"
printf '\n'

if [ ! -d "$LOG_DIR" ]; then
  echo "ERROR: log directory not found: $LOG_DIR"
  exit 2
fi

have_issues=0
running_count=0
done_count=0
failed_count=0

tmp_active="$(mktemp)"
tmp_seen="$(mktemp)"
trap 'rm -f "$tmp_active" "$tmp_seen"' EXIT

ps -Ao pid=,pcpu=,command= | awk '
index($0, "-m jetfit.run") > 0 {
  pid=$1
  cpu=$2
  event=""
  model=""
  results=""
  for (i = 3; i <= NF; i++) {
    if ($i == "--event" && i + 1 <= NF) event=$(i + 1)
    if ($i == "--model" && i + 1 <= NF) model=$(i + 1)
    if ($i == "--results" && i + 1 <= NF) results=$(i + 1)
  }
  if (event == "") next
  key = event "|" model "|" results
  if (first_pid[key] == "") first_pid[key] = pid
  sum_cpu[key] += cpu
  nproc[key] += 1
}
END {
  for (k in sum_cpu) {
    split(k, parts, "|")
    printf "%s\t%s\t%s\t%s\t%.1f\t%d\n", parts[1], parts[2], parts[3], first_pid[k], sum_cpu[k], nproc[k]
  }
}
' > "$tmp_active"

printf '%-24s %-9s %-8s %-8s %-8s %s\n' "RUN" "STATUS" "PID" "CPU%" "LOG_AGE" "NOTE"
printf '%s\n' "----------------------------------------------------------------------------------------"

while IFS=$'\t' read -r event model results pid cpu_sum nproc; do
  [ -n "$event" ] || continue
  if [ -n "$EVENT_FILTER" ] && [ "$event" != "$EVENT_FILTER" ]; then
    continue
  fi

  model_base="$(basename "$model")"
  model_tag="run"
  case "$model_base" in
    *bubble*) model_tag="bubble" ;;
    *powerlaw*|*tophat*) model_tag="powerlaw" ;;
  esac

  run_id="$event.$model_tag"
  log_file="$LOG_DIR/$run_id.log"
  log_age="na"
  note="workers=$nproc"

  if [ -f "$log_file" ]; then
    log_mtime="$(stat -f %m "$log_file")"
    age_min=$(( (now_epoch - log_mtime) / 60 ))
    log_age="${age_min}m"
    if [ "$age_min" -gt 180 ] && awk 'BEGIN{exit !('"$cpu_sum"' < 1.0)}'; then
      note="$note; possible stall (no log update + low CPU)"
      have_issues=1
    fi
  fi

  printf '%-24s %-9s %-8s %-8s %-8s %s\n' "$run_id" "RUNNING" "$pid" "$cpu_sum" "$log_age" "$note"
  echo "$run_id" >> "$tmp_seen"
  running_count=$((running_count + 1))
done < "$tmp_active"

for pid_file in "$LOG_DIR"/*.pid; do
  [ -f "$pid_file" ] || continue

  run_id="$(basename "$pid_file" .pid)"
  case "$run_id" in
    manual_subshell_runner) continue ;;
  esac

  event="${run_id%%.*}"
  if [ -n "$EVENT_FILTER" ] && [ "$event" != "$EVENT_FILTER" ]; then
    continue
  fi

  if [ -s "$tmp_seen" ] && rg -q "^${run_id}$" "$tmp_seen"; then
    continue
  fi

  pid="$(tr -d '[:space:]' < "$pid_file")"
  log_file="$LOG_DIR/$run_id.log"
  status="UNKNOWN"
  cpu="0.0"
  log_age="na"
  note=""

  if ps -p "$pid" >/dev/null 2>&1; then
    status="RUNNING"
    running_count=$((running_count + 1))

    cpu="$(ps -Ao pcpu,command | \
      awk -v ev="$event" 'index($0, "jetfit.run --event " ev " ") > 0 {sum += $1} END {printf "%.1f", sum+0}')"

    if [ -f "$log_file" ]; then
      log_mtime="$(stat -f %m "$log_file")"
      age_min=$(( (now_epoch - log_mtime) / 60 ))
      log_age="${age_min}m"
      if [ "$age_min" -gt 180 ] && awk 'BEGIN{exit !('"$cpu"' < 1.0)}'; then
        note="possible stall (no log update + low CPU)"
        have_issues=1
      fi
    fi
  else
    pid_mtime="$(stat -f %m "$pid_file")"
    pid_age_min=$(( (now_epoch - pid_mtime) / 60 ))
    if [ -f "$log_file" ] && rg -q "Foreground run completed successfully|MCMC run completed successfully|Done running emcee" "$log_file"; then
      status="DONE"
      done_count=$((done_count + 1))
      if [ -d "$DRIVE_ROOT/$event/jkeohane" ]; then
        latest_sync="$(find "$DRIVE_ROOT/$event/jkeohane" -maxdepth 1 -mindepth 1 -type d -print | tail -n 1 || true)"
        if [ -n "$latest_sync" ]; then
          note="synced: $(basename "$latest_sync")"
        fi
      fi
    elif [ -f "$log_file" ] && rg -q "Traceback|ERROR|fit failed|unbound variable|unexpected EOF|Abort trap|Segmentation fault|Killed" "$log_file"; then
      status="FAILED"
      failed_count=$((failed_count + 1))
      have_issues=1
      note="error in log"
    elif [ "$pid_age_min" -gt 30 ]; then
      status="STALE"
      note="old pid metadata (${pid_age_min}m)"
    else
      status="STOPPED"
      have_issues=1
      note="not running and no clear completion marker"
    fi
  fi

  printf '%-24s %-9s %-8s %-8s %-8s %s\n' "$run_id" "$status" "$pid" "$cpu" "$log_age" "$note"
done

printf '\nSummary: running=%d done=%d failed=%d\n' "$running_count" "$done_count" "$failed_count"

if [ "$have_issues" -ne 0 ]; then
  exit 1
fi
