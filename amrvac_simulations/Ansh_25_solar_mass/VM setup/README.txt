# Purpose: Install and run four fresh 25 Msun wind simulations on modeling-prod01-02 without sudo or AMRVAC engine edits.

Physics: spherical 1D ideal-gas HD in every case. tc_on activates saturated
Spitzer conduction; rc_on activates SPEX_DM exact cooling and Tfix at 100 K.
Folder names select all four conduction/cooling on/off combinations.
The supplied user module handles invalid refinement child pairs conservatively.
Duplicate coordinate entries are accepted only when their finite positive
cell volumes agree to roundoff; inconsistent geometry still stops the run.
All four physics inputs passed 1000-year local tests; full 7-Myr stability
is untested. This is a fresh 25 Msun model, with no 40 Msun checkpoint.

VM steps (tcsh on modeling-prod01-02):

1. Transfer this entire VanMarle25Msun folder into your VM home directory.
   Keep its four case subfolders. Enter it:
     cd ~/VanMarle25Msun

2. Check that the required ordinary compiler/build tools are available:
     bash setup_vm.sh --check
   If it prints missing tools, stop and send that line. No sudo is used.

3. Install MPI and build the problem in the background:
     nohup bash setup_vm.sh < /dev/null >& setup_vm.log &
     tail -f setup_vm.log
   Wait for SETUP COMPLETE. Ctrl+C exits tail, leaving setup running.
   The script downloads checksum-verified Open MPI 4.1.8, tests MPI Fortran,
   and compiles official AMRVAC v3.2. Installation is private to this account:
     ~/.local/amrvac25/openmpi-4.1.8
     ~/.local/amrvac25/amrvac-v3.2
   The AMRVAC engine remains unmodified; only this problem is configured.
   Detailed build logs are in setup_logs/. Do not launch while setup runs.

4. After SETUP COMPLETE, activate its matching MPI and start all four cases:
     source env25.csh
     nproc
     bash launch_all.sh 8
   Eight MPI ranks per case require 32 available CPUs in total. The launcher
   refuses CPU oversubscription and existing run logs/native outputs.
   Choose fewer ranks per case if needed. Keep CPU capacity for other jobs.
   STARTED means launched; check the logs to confirm healthy integration.

5. Watch all runs, or just conduction and cooling together:
     tail -f tc_*/run25.log
     tail -f tc_on_rc_on/run25.log
   Status prints every 30 seconds. Ctrl+C exits tail; background runs continue.
   Startup must show two wind phases ending at 7000000 yr, initial wind radius
   0.03 pc, conservative refinement T, and initial code time/iteration zero.
   Console logs: each case/run25.log. Native data: each case/output_25Msun/.

6. Later resume a case by setting its restart_from_file to a completed native
   output_25Msun/testNNNN.dat. Keep reset_time and reset_it false. From that
   case folder, after sourcing the matching env25.csh, launch manually:
     nohup mpirun --bind-to none -np 8 ../amrvac -i run.par < /dev/null >& resume25.log &
   Start only one job per case. The fresh launcher deliberately refuses reruns.

Official build references:
  https://www.open-mpi.org/faq/?category=building
  https://amrvac.org/md_doc_2getting__started.html

Simulation parameters:
  Fresh initial state, stellar age 0; stop age 7 Myr (code time 715.4033120524).
  MS: 0-6.5 Myr; mass loss 2e-7 Msun/yr; speed 1500 km/s; assumed T=10000 K.
  RSG: 6.5-7 Myr; mass loss 1e-5 Msun/yr; speed 15 km/s; assumed T=1000 K.
  No WR phase. History: stellar_evolution_25Msun.dat; values constant per phase.
  Ambient: 1e4 total particles/cm3, 100 K, inherited fixed H/He EOS, gamma=5/3.
  Initial free wind: 0.01-0.03 pc; ambient unchanged outside 0.03 pc.
  Domain 0.01-20 pc; 192 base cells; 8 cells/block; maximum AMR level 3; q=1.03.
  TVDLF/minmod/SSPRK3; CFL=0.1; STS dtpar=0.1; ghost_copy=true.
  Native output interval 10000 yr; output_25Msun/test; console log run25.log.
