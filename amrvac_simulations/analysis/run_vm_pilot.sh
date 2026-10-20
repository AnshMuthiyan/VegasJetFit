#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$0")"
ranks="${1:-4}"
checkpoint="${2:-}"
if [[ ! "$ranks" =~ ^[1-9][0-9]*$ ]]; then
  printf 'MPI rank count must be a positive integer\n' >&2
  exit 2
fi
if [[ -e run.started || -e run.exit ]]; then
  printf 'This run directory has already been used; refusing to overwrite it\n' >&2
  exit 2
fi
for path in amrvac run.par mod_usr.t stellar_evolution.dat amrvac.h RUN.txt; do
  if [[ ! -e "$path" ]]; then
    printf 'Missing run input: %s\n' "$path" >&2
    exit 2
  fi
done
if [[ -n "$checkpoint" && ! -f "$checkpoint" ]]; then
  printf 'Missing restart checkpoint: %s\n' "$checkpoint" >&2
  exit 2
fi

mkdir -p output
sha256sum amrvac run.par mod_usr.t stellar_evolution.dat amrvac.h RUN.txt > input_sha256.txt
{
  printf 'host=%s\n' "$(hostname)"
  printf 'ranks=%s\n' "$ranks"
  printf 'started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'omp_num_threads=1\n'
} > run.started

export OMP_NUM_THREADS=1
set +e
if [[ -n "$checkpoint" ]]; then
  printf 'restart_checkpoint=%s\n' "$checkpoint" >> run.started
  /usr/bin/time -v mpirun -np "$ranks" ./amrvac -i run.par -if "$checkpoint" > run.stdout 2> run.stderr
else
  /usr/bin/time -v mpirun -np "$ranks" ./amrvac -i run.par > run.stdout 2> run.stderr
fi
mpi_status=$?
set -e

status="$mpi_status"
if [[ "$status" -eq 0 ]] && ! grep -Fq 'Finished AMRVAC in' run.stdout; then
  printf 'MPI exited 0 without the AMRVAC completion marker\n' > run.validation_error
  status=1
fi
printf '%s\n' "$mpi_status" > run.mpi_exit
printf '%s\n' "$status" > run.exit
printf 'finished_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> run.started
exit "$status"
