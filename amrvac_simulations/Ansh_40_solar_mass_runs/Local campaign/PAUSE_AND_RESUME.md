<!-- Purpose: Explain how to resume each paused production case or recover its saved checkpoint after WSL shuts down. -->

# Paused stellar-wind campaign

All four original simulation ranks have been suspended with SIGSTOP, after
AMRVAC finished writing a fresh native checkpoint requested using `savenow`.
The MPI launchers and campaign supervisor remain alive and waiting. A paused
rank does not advance its solution. Its in-memory state is preserved while
WSL remains running; the disk checkpoint survives WSL or computer shutdown.

| Case | Checkpoint age (years) | Native checkpoint |
|---|---:|---|
| `tc_off_rc_off` | 1214065.410945 | `tc_off_rc_off/output/test0013.dat` |
| `tc_on_rc_off` | 1073816.474477 | `tc_on_rc_off/output/test0011.dat` |
| `tc_off_rc_on` | 1067801.003334 | `tc_off_rc_on/output/test0011.dat` |
| `tc_on_rc_on` | 1022650.888509 | `tc_on_rc_on/output/test0011.dat` |

`pause_state.json` records the checkpoint paths, ages, process IDs, process
start times, and WSL boot identity. Do not edit its recorded process IDs.
Checkpoints contain the native AMR mesh, conserved variables, and simulation age.
The wind therefore continues according to its original stellar age on restart.

## Resume one case while its original process still exists

Run these commands in WSL/Ubuntu from this campaign folder:

```sh
python3 pause_runs.py status
python3 pause_runs.py resume --case tc_on_rc_on
```

Replace `tc_on_rc_on` with any case in the table. Only that case resumes.
To resume all four, use:

```sh
python3 pause_runs.py resume --case all
```

This continues the exact suspended in-memory state without loading a snapshot
or resetting the wind history. Other cases remain suspended. The original
supervisor continues checking each case's logs.

## Restart a case after WSL or the computer has shut down

If the original process no longer exists, use its disk checkpoint:

```sh
python3 restart_checkpoint.py start --case tc_on_rc_on
```

The helper refuses to start a duplicate of a live original case. It copies
the checkpoint and inputs into a new folder under `restarted_runs/`, launches
one MPI rank in a detached session, and continues to the original 4.77 Myr end
age. It preserves the original production outputs and logs. Inspect the new
folder's `run.log`, `output/test.log`, and `supervisor.log` for progress.
`restart_result.json` is written only after successful completion and auditing.

The disk checkpoint is the last completed time step saved immediately before
suspension. The in-memory process may have advanced a few additional steps
between completing the save and receiving SIGSTOP. Thus resuming the original
process is exact; restarting from disk returns to the listed checkpoint age.

Numerical energy-safeguard counters reset when a new executable starts; their
original logs remain preserved. All four guards had recorded zero corrections
before this pause. A restarted segment has its own guard log and supervisor.
This does not alter the gas state, stellar age, physical parameters, or target
duration. The native checkpoint is essential; converted VTU files are not used
as restart inputs.

## Verification performed

Each saved checkpoint passed native-cell auditing and a separate 0.25-year
restart test with the production executable and its original physics switches.
All four tests reached the expected later age with finite states and positive
pressure. Test files are under `restart_checks/`. These tests did not resume
the original production jobs or change their checkpoints.

The `pause_runs.py` controller manages the four original production processes.
Its `pause` action currently requires all four to be running, so do not use it
to pause a mixture of resumed and still-suspended cases. Independently restarted
segments have separate supervisors and are not controlled by that original-job
controller. Ask for a fresh checkpoint pause before shutting down a subsequently
resumed run if you want to preserve its later progress.
