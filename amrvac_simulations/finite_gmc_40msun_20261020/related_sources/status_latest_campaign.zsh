#!/usr/bin/env zsh

set -euo pipefail

base_dir="${0:A:h}"
current_link="${base_dir}/CURRENT_ACTIVE_LATEST_xmin0p2"
campaign_dir="${1:-${current_link}}"

if [[ -L "${campaign_dir}" ]]; then
  campaign_dir="$(cd "$(dirname "${campaign_dir}")" && pwd -P)/$(readlink "${campaign_dir}")"
fi
campaign_dir="$(cd "${campaign_dir}" && pwd -P)"

echo "Latest AMRVAC campaign: ${campaign_dir}"
echo

echo "Local run directories:"
find "${campaign_dir}" -maxdepth 1 -type d -name 'pressure_*' -print | sort | while read -r run_dir; do
  name="${run_dir:t}"
  log="${run_dir}/amrvac.log"
  vtus=$(find "${run_dir}/output" -name '*.vtu' 2>/dev/null | wc -l | tr -d ' ')
  if [[ -f "${run_dir}/FAILED" ]]; then
    state="FAILED"
  elif [[ -f "${log}" ]] && grep -q 'Finished AMRVAC' "${log}"; then
    state="FINISHED"
  elif [[ -f "${log}" ]] && (( $(date +%s) - $(stat -f %m "${log}") < 300 )); then
    state="RUNNING_RECENT"
  elif pgrep -f "${run_dir}.*amrvac" >/dev/null 2>&1; then
    state="RUNNING_LOCAL"
  elif [[ -f "${log}" ]]; then
    state="LOG_PRESENT"
  else
    state="NOT_LOCAL"
  fi
  last_time=""
  if [[ -f "${log}" ]]; then
    last_time="$(grep -E '^   #|^ *#' "${log}" | tail -1 | sed 's/^ *//')"
  fi
  printf "%-22s %-14s vtu=%-4s %s\n" "${name}" "${state}" "${vtus}" "${last_time}"
done

echo
echo "Local tmux sessions:"
tmux ls 2>/dev/null | grep -E 'amrvac|lab_|jet' || true

echo
echo "Remote AMRVAC/JetFit processes:"
for host in pauley404-01 pauley404-02 pauley404-03; do
  echo "== ${host} =="
  ssh -o BatchMode=yes -o ConnectTimeout=5 "${host}" \
    "tmux ls 2>/dev/null | grep -E 'amrvac|lab_|jet' || true; ps -eo pid,ppid,etime,pcpu,pmem,command | egrep 'amrvac|mpirun|mpiexec|prterun|jetfit|python.*jetfit|host_pressure_queue' | grep -v egrep || true" \
    2>/dev/null || echo "unreachable"
done
