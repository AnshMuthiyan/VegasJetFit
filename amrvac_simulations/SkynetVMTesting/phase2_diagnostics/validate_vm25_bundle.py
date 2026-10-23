# Purpose: Validate the 25 Msun scripts, compile/run their actual MPI check, and mock the launcher without installing software or running simulations.
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import time

source = Path(__file__).resolve().parents[1] / "VanMarle25Msun"
scratch = Path(tempfile.mkdtemp(prefix="vm25-validation-"))
bundle = scratch / "VanMarle25Msun"
shutil.copytree(source, bundle)
print(f"Validation folder: {bundle}", flush=True)
cases = ("tc_off_rc_off", "tc_off_rc_on", "tc_on_rc_off", "tc_on_rc_on")
inputs = ["mod_usr.t", "amrvac.h", "stellar_evolution_25Msun.dat"]
inputs.extend(f"{case}/run.par" for case in cases)
for name in inputs:
    assert hashlib.sha256((source / name).read_bytes()).digest() == hashlib.sha256(
        (source.parent / name).read_bytes()
    ).digest(), f"Transfer input differs from tested root: {name}"
for name in ("setup_vm.sh", "launch_all.sh"):
    subprocess.run(["bash", "-n", str(bundle / name)], check=True)
subprocess.run(["bash", str(bundle / "setup_vm.sh"), "--check"], check=True)

# Compile the exact embedded Fortran, so namespace errors cannot hide behind mocks.
setup_text = (bundle / "setup_vm.sh").read_text()
probe_text = setup_text.split("<<'FORTRAN'\n", 1)[1].split("\nFORTRAN\n", 1)[0]
probe_source = scratch / "mpi_probe.f90"
probe_source.write_text(probe_text + "\n")
probe_binary = scratch / "mpi_probe"
subprocess.run(["mpifort", str(probe_source), "-o", str(probe_binary)], check=True)
subprocess.run(["mpirun", "--bind-to", "none", "-np", "2", str(probe_binary)], check=True)

mock_bin = scratch / "bin"
mock_bin.mkdir()
(mock_bin / "mpirun").write_text(
    "#!/bin/bash\n# Purpose: Mock MPI launcher to verify rank arguments and case working directories.\n"
    '[[ "$1 $2 $3 $4" == "--bind-to none -np 1" ]] || exit 92\n'
    'shift 4\nexec "$@"\n'
)
(mock_bin / "mpirun").chmod(0o755)
(bundle / "env25.sh").write_text(
    '# Purpose: Activate mock MPI for isolated launcher validation.\n'
    f'export PATH="{mock_bin}:$PATH"\n'
)
(bundle / "amrvac").write_text(
    '#!/bin/bash\n# Purpose: Mock AMRVAC verifying case inputs and producing an isolated completion marker.\n'
    '[[ "$1 $2" == "-i run.par" ]] || exit 93\n'
    '[[ -f run.par && -f ../stellar_evolution_25Msun.dat && -d output_25Msun ]] || exit 94\n'
    'printf "MOCK COMPLETED %s\\n" "$PWD"\n'
)
(bundle / "amrvac").chmod(0o755)
result = subprocess.run(["bash", "launch_all.sh", "1"], cwd=bundle, text=True,
                        capture_output=True, check=True)
assert result.stdout.count("STARTED tc_") == 4, result.stdout
deadline = time.monotonic() + 5
for case in cases:
    log = bundle / case / "run25.log"
    while "MOCK COMPLETED" not in log.read_text() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert f"MOCK COMPLETED {bundle / case}" in log.read_text(), log.read_text()
    assert int((bundle / case / "launcher.pid").read_text().splitlines()[-1]) > 0
duplicate = subprocess.run(["bash", "launch_all.sh", "1"], cwd=bundle,
                           text=True, capture_output=True)
assert duplicate.returncode != 0 and "existing log/output" in duplicate.stderr
assert "STARTED" not in duplicate.stdout
oversubscribed = subprocess.run(["bash", "launch_all.sh", str(os.cpu_count() + 1)],
                                cwd=bundle, text=True, capture_output=True)
assert oversubscribed.returncode != 0 and "Choose fewer ranks" in oversubscribed.stderr
print("PASSED: unchanged science inputs, Bash syntax, dependency preflight, actual two-rank MPI Fortran check, four mock launches, duplicate prevention, CPU limit.")
