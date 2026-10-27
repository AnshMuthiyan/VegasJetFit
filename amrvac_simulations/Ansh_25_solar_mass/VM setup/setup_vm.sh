# Purpose: Install user-local Open MPI and stock AMRVAC 3.2, verify MPI Fortran, and compile this 25 Msun problem without sudo.
set -Eeuo pipefail

bundle_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
software_root="$HOME/.local/amrvac25"
mpi_prefix="$software_root/openmpi-4.1.8"
amrvac_source="$software_root/amrvac-v3.2"
logs="$bundle_dir/setup_logs"
expected_commit=c45d84650ed3379eb22dcfa6fb927a45734e5d8c
mpi_sha256=fb41086bbed9300baa2f3d7572491facfe5257412fa524ec5a396aa9101d5c62
printf '# Purpose: User-local 25 Msun MPI/AMRVAC setup transcript.\n'

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
case "$bundle_dir:$software_root" in
    *[[:space:]]*) die 'Use a Linux folder without spaces; AMRVAC setup does not support spaces in these paths.' ;;
esac
case "${1:-}" in ''|--check) ;; *) die 'Usage: bash setup_vm.sh [--check]' ;; esac

missing=()
for tool in gcc g++ gfortran git make perl rsync tar sha256sum awk grep; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    missing+=('curl or wget')
fi
((${#missing[@]}==0)) || die "Missing build tools: ${missing[*]}. Send this line before proceeding."
for file in mod_usr.t amrvac.h stellar_evolution_25Msun.dat; do
    [[ -f "$bundle_dir/$file" ]] || die "Missing input: $file"
done
for case_name in tc_off_rc_off tc_off_rc_on tc_on_rc_off tc_on_rc_on; do
    [[ -f "$bundle_dir/$case_name/run.par" ]] || die "Missing $case_name/run.par"
done
grep -q 'amr_pair_fallback, wind_init_radius_pc' "$bundle_dir/mod_usr.t" || die 'The supplied user module is not the current version.'
if [[ "${1:-}" == --check ]]; then
    printf 'PREFLIGHT PASSED\nMPI installation: %s\nStock AMRVAC: %s\nProblem: %s\n' "$mpi_prefix" "$amrvac_source" "$bundle_dir"
    exit 0
fi

mkdir -p "$logs" "$software_root/downloads" "$software_root/src" "$software_root/build"
trap 'printf "SETUP FAILED near line %s. Inspect setup_logs and the last error above.\n" "$LINENO" >&2' ERR
build_jobs=${AMRVAC25_BUILD_JOBS:-4}
[[ "$build_jobs" =~ ^[1-9][0-9]*$ ]] || die 'AMRVAC25_BUILD_JOBS must be a positive integer.'
cpu_count=$(getconf _NPROCESSORS_ONLN)
if ((build_jobs>cpu_count)); then build_jobs=$cpu_count; fi

run_step() {
    local name=$1
    shift
    local logfile="$logs/$name.log"
    printf 'START %s; detailed log: %s\n' "$name" "$logfile"
    printf '# Purpose: %s stage of user-local 25 Msun setup.\n' "$name" > "$logfile"
    if ! "$@" >> "$logfile" 2>&1; then
        tail -n 45 "$logfile" >&2
        return 1
    fi
    printf 'DONE %s\n' "$name"
}

if [[ ! -x "$mpi_prefix/bin/mpifort" || ! -x "$mpi_prefix/bin/mpirun" ]]; then
    archive="$software_root/downloads/openmpi-4.1.8.tar.gz"
    if [[ ! -f "$archive" ]]; then
        url=https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.8.tar.gz
        if command -v curl >/dev/null 2>&1; then
            run_step mpi_download curl --fail --location --retry 3 --output "$archive.part" "$url"
        else
            run_step mpi_download wget -O "$archive.part" "$url"
        fi
        mv -- "$archive.part" "$archive"
    fi
    printf '%s  %s\n' "$mpi_sha256" "$archive" | sha256sum -c -
    mpi_src="$software_root/src/openmpi-4.1.8"
    if [[ ! -f "$mpi_src/configure" ]]; then
        run_step mpi_extract tar -xzf "$archive" -C "$software_root/src"
    fi
    mpi_build="$software_root/build/openmpi-4.1.8"
    mkdir -p "$mpi_build"
    (
        cd "$mpi_build"
        run_step mpi_configure "$mpi_src/configure" --prefix="$mpi_prefix" --libdir="$mpi_prefix/lib" \
            --with-hwloc=internal --with-libevent=internal --with-pmix=internal \
            CC=gcc CXX=g++ FC=gfortran
        run_step mpi_build make -j"$build_jobs"
        run_step mpi_install make install
    )
else
    printf 'Reusing user-local MPI: %s\n' "$mpi_prefix"
fi

export PATH="$mpi_prefix/bin:$PATH"
export LD_LIBRARY_PATH="$mpi_prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export AMRVAC_DIR="$amrvac_source"
export OMP_NUM_THREADS=1
{
    printf '# Purpose: Activate the user-local MPI and stock AMRVAC used by the 25 Msun executable in bash.\n'
    printf 'export PATH=%q:"$PATH"\n' "$mpi_prefix/bin"
    printf 'export LD_LIBRARY_PATH=%q${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n' "$mpi_prefix/lib"
    printf 'export AMRVAC_DIR=%q\nexport OMP_NUM_THREADS=1\n' "$amrvac_source"
} > "$bundle_dir/env25.sh"
{
    printf '# Purpose: Activate the user-local MPI and stock AMRVAC used by the 25 Msun executable in tcsh.\n'
    printf 'set path = ("%s" $path)\n' "$mpi_prefix/bin"
    printf 'if ($?LD_LIBRARY_PATH) then\n    setenv LD_LIBRARY_PATH "%s:$LD_LIBRARY_PATH"\nelse\n    setenv LD_LIBRARY_PATH "%s"\nendif\n' "$mpi_prefix/lib" "$mpi_prefix/lib"
    printf 'setenv AMRVAC_DIR "%s"\nsetenv OMP_NUM_THREADS 1\n' "$amrvac_source"
} > "$bundle_dir/env25.csh"

cat > "$logs/mpi_probe.f90" <<'FORTRAN'
! Purpose: Verify MPI Fortran module compilation and a multi-rank collective before compiling AMRVAC.
program amrvac25_mpi_check
  use mpi
  implicit none
  integer :: ierr,rank,n,total
  call MPI_INIT(ierr)
  call MPI_COMM_RANK(MPI_COMM_WORLD,rank,ierr)
  call MPI_COMM_SIZE(MPI_COMM_WORLD,n,ierr)
  call MPI_ALLREDUCE(rank,total,1,MPI_INTEGER,MPI_SUM,MPI_COMM_WORLD,ierr)
  if(total/=n*(n-1)/2) call MPI_ABORT(MPI_COMM_WORLD,2,ierr)
  if(rank==0) print *, 'MPI FORTRAN PROBE PASSED; ranks=',n
  call MPI_FINALIZE(ierr)
end program amrvac25_mpi_check
FORTRAN
run_step mpi_fortran_compile mpifort "$logs/mpi_probe.f90" -o "$logs/mpi_probe"
probe_ranks=2
if ((cpu_count<2)); then probe_ranks=1; fi
run_step mpi_fortran_run mpirun --bind-to none -np "$probe_ranks" "$logs/mpi_probe"

if [[ ! -d "$amrvac_source" ]]; then
    run_step amrvac_download git -c core.autocrlf=false clone --branch v3.2 --depth 1 \
        --recurse-submodules --shallow-submodules https://github.com/amrvac/amrvac.git "$amrvac_source"
fi
[[ -f "$amrvac_source/setup.pl" && -d "$amrvac_source/.git" ]] || die 'The dedicated AMRVAC directory is incomplete; inspect setup_logs/amrvac_download.log.'
actual_commit=$(git -C "$amrvac_source" rev-parse HEAD)
[[ "$actual_commit" == "$expected_commit" ]] || die "Unexpected AMRVAC revision: $actual_commit"
git -C "$amrvac_source" diff --exit-code HEAD -- src arch setup.pl >/dev/null || die 'The dedicated AMRVAC core has local edits; use an unmodified source tree.'

cd "$bundle_dir"
flags='-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'
run_step amrvac_setup perl "$AMRVAC_DIR/setup.pl" -d=1
run_step amrvac_headers make hdr F90=mpifort
run_step amrvac_user_template make -B mod_usr.f F90=mpifort
run_step amrvac_build make -j"$build_jobs" F90=mpifort "F90FLAGS=$flags"
[[ -x "$bundle_dir/amrvac" ]] || die 'Build did not produce an executable.'
grep -aqF 'User-module conservative refinement:' "$bundle_dir/amrvac" || die 'Executable lacks the updated user module.'
git -C "$amrvac_source" diff --exit-code HEAD -- src arch setup.pl >/dev/null || die 'Core source changed unexpectedly during the build.'
printf 'SETUP COMPLETE: MPI Fortran verified; stock AMRVAC 3.2 user problem compiled.\n'
printf 'In tcsh: source env25.csh\nThen: bash launch_all.sh 8\n'
