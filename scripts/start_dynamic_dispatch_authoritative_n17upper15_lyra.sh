#!/usr/bin/env bash
# Keep authoritative n17-boundary follow-ups assigned one per idle workstation.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
REPORT="$VJF/reports/26_09_04__authoritative_n17_upper15_followups"
RUN_TAG="core_logangle_powerlawcsm_finalfinal_sthawed_n17upper15_audit_5temp_1000x5000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_09_04__authoritative_n17_upper15__posterior_cloud__5_temperature_1000x5000"
SESSION="dynamic_dispatch_authoritative_n17upper15_lyra"
LOG="$VJF/logs/dynamic_dispatch_authoritative_n17upper15_lyra.log"
POLL_SECONDS="${POLL_SECONDS:-300}"
EVENT_RUNNER="$VJF/scripts/run_authoritative_n17upper15_event.sh"
GENERIC_RUNNER="$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh"
CONFIG_DIR="$VJF/structured_jet_core_logangle_authoritative_n17upper15_5temp_configs"
MCMC_SETTINGS="$VJF/Ansh_Run/mcmc_settings_core_logangle_finalfinal_sthawed_5temp_1000x5000.toml"
INITIAL_POSITIONS="$VJF/initial_positions/authoritative_n17upper15_5temp"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Authoritative n17 dispatcher is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
COMMAND="cd '$VJF' && while true; do date -u +%Y-%m-%dT%H:%M:%SZ; '$PY' '$VJF/scripts/dynamic_dispatch_campaign.py' --queue '$REPORT/dynamic_event_queue.csv' --manifest '$REPORT/dispatch_manifest.csv' --run-tag '$RUN_TAG' --event-script '$EVENT_RUNNER' --results-root '$VJF/jetfit/results' --campaign '$CAMPAIGN' --machines 'pauley404-01:8,pauley404-03:8,pauley404-02:8,pcrc-mac-studio-1:14,pcrc-mac-studio-2:14' --pcrc-workers 14 --session-prefix 'grb_n17upper15' --busy-pattern 'jetfit.run' --decision-records '$REPORT/event_decision_records.json' --sync-path '$GENERIC_RUNNER' --sync-path '$CONFIG_DIR' --sync-path '$MCMC_SETTINGS' --sync-path '$INITIAL_POSITIONS' --sync-path '$VJF/obs_overrides/050525A_authoritative_n17upper15_20260904.csv' --sync-path '$VJF/obs_overrides/050922C_authoritative_n17upper15_20260904.csv' --sync-path '$VJF/obs_overrides/130612A_authoritative_n17upper15_20260904.csv' --sync-path '$VJF/jwk_run_thesis_reproduction_event.sh' --sync-path '$VJF/jetfit/run.py' --sync-path '$VJF/jetfit/ampy.py' --sync-path '$VJF/jetfit/core/utils.py' --sync-path '$VJF/jetfit/mcmc/mcmc.py' --sync-path '$VJF/jetfit/mcmc/parameters.py' --sync-path '$VJF/jetfit/models/powerlawVegas.py' --sync-path '$VJF/jetfit/models/powerlawJetVegasDylanSpectrum.py' --sync-path '$VJF/jetfit/models/vegas_resolution.py' --sync-path '$VJF/jetfit/models/vegasafterglow.py' --sync-path '$VJF/jetfit/models/jet_energy.py'; sleep '$POLL_SECONDS'; done >> '$LOG' 2>&1"
tmux new-session -d -s "$SESSION" "$COMMAND"
echo "Started authoritative n17 dispatcher: tmux attach -t $SESSION"
