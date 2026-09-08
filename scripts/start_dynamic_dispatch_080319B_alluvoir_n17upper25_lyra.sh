#!/usr/bin/env bash
# Keep the approved all-UVOIR GRB 080319B n17-upper25 continuation queued.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
PY="$ROOT/.venv/bin/python"
REPORT="$VJF/reports/080319B_alluvoir_n17upper25_posteriorcloud_5temp_1000x5000_campaign"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_alluvoir_n17upper25_5temp_1000x5000_v1"
CAMPAIGN="$ROOT/Share_Folder/Fits/production_runs/final_seeded_runs/26_09_07__080319B__all_uvoir__posterior_cloud__n17_upper25__5_temperature_1000x5000"
SESSION="dynamic_dispatch_080319B_alluvoir_n17upper25_lyra"
LOG="$VJF/logs/dynamic_dispatch_080319B_alluvoir_n17upper25_lyra.log"
POLL_SECONDS="${POLL_SECONDS:-300}"
EVENT_RUNNER="$VJF/scripts/run_080319B_alluvoir_n17upper25_event.sh"
GENERIC_RUNNER="$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh"
CONFIG_DIR="$VJF/structured_jet_core_logangle_080319B_alluvoir_n17upper25_finalfinal_sthawed_5temp_configs"
MCMC_SETTINGS="$VJF/Ansh_Run/mcmc_settings_core_logangle_finalfinal_sthawed_5temp_1000x5000.toml"
INITIAL_POSITIONS="$VJF/initial_positions/080319B_alluvoir_n17upper25_finalfinal_sthawed_5temp.npz"
OBS_CSV_OVERRIDE="$VJF/obs_overrides/080319B_all_early_uvoir_included_n17upper15_20260904.csv"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "080319B all-UVOIR n17-upper25 dispatcher is already running: tmux attach -t $SESSION"
  exit 0
fi

mkdir -p "$VJF/logs"
COMMAND="cd '$VJF' && while true; do date -u +%Y-%m-%dT%H:%M:%SZ; '$PY' '$VJF/scripts/dynamic_dispatch_campaign.py' --queue '$REPORT/dynamic_event_queue.csv' --manifest '$REPORT/dispatch_manifest.csv' --run-tag '$RUN_TAG' --event-script '$EVENT_RUNNER' --results-root '$VJF/jetfit/results' --campaign '$CAMPAIGN' --machines 'pauley404-02:8,pauley404-01:8,pauley404-03:8' --pcrc-workers 14 --session-prefix 'grb080319B_alluvoir_n17upper25' --busy-pattern 'jetfit.run' --decision-records '$REPORT/event_decision_records.json' --sync-path '$GENERIC_RUNNER' --sync-path '$CONFIG_DIR' --sync-path '$MCMC_SETTINGS' --sync-path '$INITIAL_POSITIONS' --sync-path '$OBS_CSV_OVERRIDE' --sync-path '$VJF/jwk_run_thesis_reproduction_event.sh' --sync-path '$VJF/jetfit/run.py' --sync-path '$VJF/jetfit/ampy.py' --sync-path '$VJF/jetfit/core/utils.py' --sync-path '$VJF/jetfit/mcmc/mcmc.py' --sync-path '$VJF/jetfit/mcmc/parameters.py' --sync-path '$VJF/jetfit/models/powerlawVegas.py' --sync-path '$VJF/jetfit/models/powerlawJetVegasDylanSpectrum.py' --sync-path '$VJF/jetfit/models/vegas_resolution.py' --sync-path '$VJF/jetfit/models/vegasafterglow.py' --sync-path '$VJF/jetfit/models/jet_energy.py'; sleep '$POLL_SECONDS'; done >> '$LOG' 2>&1"
tmux new-session -d -s "$SESSION" "$COMMAND"
echo "Started 080319B all-UVOIR n17-upper25 dispatcher: tmux attach -t $SESSION"
