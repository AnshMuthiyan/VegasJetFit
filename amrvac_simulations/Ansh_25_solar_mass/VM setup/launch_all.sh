# Purpose: Launch the four fresh 25 Msun physics combinations with matching user-local MPI, resource checks, separate logs, and duplicate-run protection.
set -Eeuo pipefail
bundle_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$bundle_dir"
[[ -f env25.sh ]] || { printf 'Run bash setup_vm.sh first.\n' >&2; exit 1; }
source ./env25.sh
[[ -x ./amrvac ]] || { printf 'Missing compiled amrvac executable.\n' >&2; exit 1; }
ranks=${1:-8}
[[ "$ranks" =~ ^[1-9][0-9]*$ ]] || { printf 'Ranks must be a positive integer.\n' >&2; exit 1; }
cpu_count=$(getconf _NPROCESSORS_ONLN)
if ((4*ranks>cpu_count)); then
    printf 'Requested %s ranks total, but this VM reports %s CPUs. Choose fewer ranks per case.\n' "$((4*ranks))" "$cpu_count" >&2
    exit 1
fi
cases=(tc_off_rc_off tc_off_rc_on tc_on_rc_off tc_on_rc_on)
for case_name in "${cases[@]}"; do
    [[ -f "$case_name/run.par" ]] || { printf 'Missing %s/run.par\n' "$case_name" >&2; exit 1; }
    grep -Eq "^[[:space:]]*restart_from_file[[:space:]]*=[[:space:]]*'undefined'" "$case_name/run.par" || {
        printf '%s is configured for a restart; use its manual restart command.\n' "$case_name" >&2; exit 1;
    }
    if [[ -e "$case_name/run25.log" ]] || compgen -G "$case_name/output_25Msun/test*.dat" >/dev/null; then
        printf '%s has an existing log/output. Use a fresh case copy or an explicit checkpoint restart.\n' "$case_name" >&2
        exit 1
    fi
done
for case_name in "${cases[@]}"; do
    mkdir -p "$case_name/output_25Msun"
    (
        cd "$case_name"
        printf '# Purpose: Console output of the fresh 25 Msun %s simulation.\n' "$case_name" > run25.log
        nohup mpirun --bind-to none -np "$ranks" ../amrvac -i run.par < /dev/null >> run25.log 2>&1 &
        pid=$!
        printf '# Purpose: MPI launcher PID for this specific 25 Msun case.\n%s\n' "$pid" > launcher.pid
        printf 'STARTED %s; MPI PID=%s; ranks=%s; log=%s/run25.log\n' "$case_name" "$pid" "$ranks" "$case_name"
    )
done
printf 'Watch from this folder: tail -f tc_*/run25.log\n'
printf 'STARTED records confirm launch only; inspect each log for startup or runtime errors.\n'
