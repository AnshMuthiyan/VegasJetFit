<!-- Purpose: Explain the exhaustive 8-16-rank benchmark and copying a whole VM folder to Windows. -->

# Benchmark 8 through 16 cores

Copy `benchmark_8_to_16.py` into `SkynetVMTesting` on the VM. It needs Python 3,
MPI, and the already compiled `amrvac`. Save checkpoints and stop/pause the other
production runs before measuring performance. The script refuses to benchmark
while your other active AMRVAC processes are competing for CPUs.

From the VM's csh/tcsh terminal:

```csh
cd /skynet/amrvac3.2/VanMarleTCRC/SkynetVMTesting
nohup python3 benchmark_8_to_16.py --case all < /dev/null >& benchmark_driver.log &
```

This tests **8, 9, 10, 11, 12, 13, 14, 15, and 16 MPI ranks for every physics
case**: 36 sequential runs, each advancing 50000 steps from a fixed checkpoint.
Rank count changes; physical inputs do not. Each case selects its newest valid
checkpoint by stellar age from its original folder or `production_*_CASE`
folders. Benchmark outputs are not selected as production checkpoints.

To test only conduction-on/cooling-on, replace `--case all` with
`--case tc_on_rc_on`. Add `--repeats 3` for three measurements of every rank
count. To select a specific checkpoint for one case, add
`--checkpoint /absolute/path/to/test0012.dat` with its matching `run.par` nearby.

Monitor from another terminal:

```csh
tail -f benchmark_driver.log
```

Each case starts from the same copied checkpoint for every rank count. There
is no short AMRVAC wall-time stop: all ranks stop at the same iteration. An
external 600-second per-run watchdog includes output/shutdown time and marks
timeouts as failures; change it with `--timeout 1200` if necessary. Interrupting
the driver stops its current test without signaling other jobs.

Results are grouped in **`benchmarks_8_16/TIMESTAMP/`**:

- `summary.csv`: rank counts, wall/compute times, throughput, errors, final ages.
- `fastest.txt`: fastest successful rank count per case, using median total time.
- `manifest.json`: checkpoint identities, hashes, and benchmark settings.
- Case subfolders: copied checkpoint/history and separate inputs, logs, native
  snapshots, VTU files, and guard diagnostics for each test.

Timings vary by rank count; they are not fixed two-minute tests. Only successful
completed tests with the requested step count are ranked. Single-case results
do not measure the effect of running four production cases simultaneously.

# Copy a whole VM folder back to Windows

Run **`fetch_vm_folder.ps1` on your Windows machine**, not in the VM. From Windows
PowerShell in your local `SkynetVMTesting` folder, download the entire VM project:

```powershell
.\fetch_vm_folder.ps1 -VmHost 'YOUR_VM_IP' -Destination 'C:\Users\anshm\Projects\GRB modelling\VMResults'
```

It defaults to username `muthiyan` and remote folder
`/skynet/amrvac3.2/VanMarleTCRC/SkynetVMTesting`. Enter the SSH password when
prompted, or use an already configured SSH key. Replace `YOUR_VM_IP` with the
same address used to SSH to this VM.

To download only the benchmark results, including every nested folder:

```powershell
.\fetch_vm_folder.ps1 -VmHost 'YOUR_VM_IP' -RemoteFolder '/skynet/amrvac3.2/VanMarleTCRC/SkynetVMTesting/benchmarks_8_16' -Destination 'C:\Users\anshm\Projects\GRB modelling\VMResults'
```

The script uses recursive SCP with a remote `username@host:/path` source. It
creates a fresh timestamped local destination, preserves timestamps, and leaves
the VM files in place. Add `-Preview` to print the paths without transferring.
Copy completed benchmark results so files are no longer being written.
