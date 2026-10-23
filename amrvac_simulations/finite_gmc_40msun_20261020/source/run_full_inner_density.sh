#!/usr/bin/env bash
set -euo pipefail

cd /tmp/van_marle_density_inner0p01_20261014
test -x ./amrvac
test -d output

for n0 in 20000 40000; do
  for branch in gravity nogravity; do
    for grid in 1024 2048; do
      short="ion_${branch}_n${n0}_inner0p01_r${grid}_0p1myr"
      test "$(cat "$short.run.exit")" = 0
      test ! -s "$short.run.err"
      grep -q 'Finished AMRVAC' "$short.run.log"
      test -f "output/${short}0005.vtu"
    done
  done
done

for n0 in 20000 40000; do
  for branch in gravity nogravity; do
    prefix="ion_${branch}_n${n0}_inner0p01_r1024_4p77myr"
    if [[ -e "$prefix.run.log" || -e "$prefix.run.err" || -e "$prefix.run.exit" ]]; then
      printf 'Existing run record for %s; refusing overwrite\n' "$prefix" >&2
      exit 2
    fi
    if compgen -G "output/${prefix}*" > /dev/null; then
      printf 'Existing output for %s; refusing overwrite\n' "$prefix" >&2
      exit 2
    fi
    printf '%s\n' "$prefix"
  done
done | xargs -P 4 -I '{}' bash -c '
  prefix=$1
  timeout 36000 stdbuf -oL ./amrvac -i evolving_base_inner0p01_1024.par "$prefix.par" > "$prefix.run.log" 2> "$prefix.run.err"
  rc=$?
  printf "%s\n" "$rc" > "$prefix.run.exit"
  printf "%s exit=%s\n" "$prefix" "$rc"
  exit "$rc"
' _ '{}'
