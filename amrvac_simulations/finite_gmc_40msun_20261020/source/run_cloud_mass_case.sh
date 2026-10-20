#!/usr/bin/env bash
set -euo pipefail

case_name=${1:?case name required}
guard_seconds=${2:?guard seconds required}
base_file=${BASE_FILE:-cloud_mass_base_1024.par}
[[ $case_name =~ ^cloudmass_[a-z0-9_]+_(atmosphere|wind|full)$ ]]
[[ -x ./amrvac && -f ./$base_file && -f ./$case_name.par ]]
[[ -d ./output ]]
for suffix in run.log run.err run.exit; do
  if [[ -e "$case_name.$suffix" ]]; then
    printf 'Existing run record for %s; refusing overwrite\n' "$case_name" >&2
    exit 2
  fi
done
if compgen -G "output/$case_name*.vtu" > /dev/null; then
  printf 'Existing output for %s; refusing overwrite\n' "$case_name" >&2
  exit 2
fi
sha256sum ./amrvac "./$base_file" "./$case_name.par" > "$case_name.sha256"
set +e
timeout "$guard_seconds" stdbuf -oL ./amrvac -i "$base_file" "$case_name.par" \
  > "$case_name.run.log" 2> "$case_name.run.err"
rc=$?
set -e
printf '%s\n' "$rc" > "$case_name.run.exit"
exit "$rc"
