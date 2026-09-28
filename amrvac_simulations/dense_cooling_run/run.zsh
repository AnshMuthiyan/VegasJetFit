#!/usr/bin/env zsh

set -euo pipefail

export HOMEBREW_PREFIX="${HOMEBREW_PREFIX:-/opt/homebrew}"
export PATH="${HOMEBREW_PREFIX}/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export FC="${FC:-${HOMEBREW_PREFIX}/bin/gfortran}"
export F77="${F77:-${FC}}"
export OMPI_FC="${OMPI_FC:-${FC}}"
export AMRVAC_DIR="${AMRVAC_DIR:-$HOME/codes/amrvac}"
export AMRVAC_NP="${AMRVAC_NP:-8}"

if [[ ! -d "${AMRVAC_DIR}" ]]; then
  echo "AMRVAC_DIR not found: ${AMRVAC_DIR}" >&2
  exit 1
fi

if ! command -v mpirun >/dev/null 2>&1; then
  echo "mpirun not found in PATH" >&2
  exit 1
fi

echo "Using gfortran: $(command -v gfortran)"
gfortran --version | head -n 1
echo "Using mpif90: $(command -v mpif90)"

mkdir -p output/Ostar_1D/test
"${AMRVAC_DIR}/setup.pl" -d=1
if [[ "${AMRVAC_FORCE_CLEAN:-0}" == "1" ]]; then
  make allclean
fi
make
mpirun -np "${AMRVAC_NP}" ./amrvac -i amrvac_evolving.par 2>&1 | tee amrvac.log
