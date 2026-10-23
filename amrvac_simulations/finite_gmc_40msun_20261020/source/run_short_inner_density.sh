#!/usr/bin/env bash
set -euo pipefail

cd /tmp/van_marle_density_inner0p01_20261014
test -x ./amrvac
test -d output

for case_file in ion_*_inner0p01_r*_0p1myr.par; do
  prefix=${case_file%.par}
  if [[ -e "$prefix.run.exit" ]]; then
    continue
  fi
  printf '%s\n' "$prefix"
done | xargs -r -P 4 -I '{}' bash -c '
  set -u
  prefix=$1
  if [[ -e "$prefix.run.log" || -e "$prefix.run.err" || -e "$prefix.run.exit" ]]; then
    printf "Existing run record for %s; refusing overwrite\n" "$prefix" >&2
    exit 2
  fi
  if [[ "$prefix" == *_r1024_* ]]; then
    base=evolving_base_inner0p01_1024.par
  else
    base=evolving_base_inner0p01_2048.par
  fi
  timeout 3600 stdbuf -oL ./amrvac -i "$base" "$prefix.par" > "$prefix.run.log" 2> "$prefix.run.err"
  rc=$?
  printf "%s\n" "$rc" > "$prefix.run.exit"
  printf "%s exit=%s\n" "$prefix" "$rc"
  exit "$rc"
' _ '{}'
