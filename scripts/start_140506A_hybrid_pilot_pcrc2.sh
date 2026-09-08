#!/usr/bin/env bash
# Launch the guarded 25+100 hybrid-grid MCMC pilot on PCRC-2.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="140506A"
HOST="pcrc-mac-studio-2"
WORKERS=5
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_hybrid_5temp_25x100_pilot_v1"
REPORT="$VJF/reports/core_logangle_powerlaw_140506A_finalfinal_sthawed_hybrid_5temp_25x100_pilot_campaign"
CONFIG_DIR="$VJF/structured_jet_core_logangle_powerlaw_140506A_finalfinal_sthawed_hybrid_5temp_configs"
MCMC_SETTINGS="$VJF/Ansh_Run/mcmc_settings_140506A_hybrid_pilot_5temp_25x100.toml"
INITIAL_POSITIONS="$VJF/initial_positions/finalfinal_sthawed_ultrafine_5temp/140506A.npz"
RUNNER="$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh"
SESSION="grb_140506A_hybrid_pilot"
SSH=(ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15)

"${SSH[@]}" "$HOST" "mkdir -p '$REPORT'"
rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15" "$REPORT/" "$HOST:$REPORT/"
rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15" "$RUNNER" "$VJF/jwk_run_thesis_reproduction_event.sh" "$HOST:$VJF/scripts/"
rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15" "$CONFIG_DIR/" "$HOST:$CONFIG_DIR/"
rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15" "$MCMC_SETTINGS" "$HOST:$VJF/Ansh_Run/"
rsync -az -e "ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=15" "$INITIAL_POSITIONS" "$HOST:$INITIAL_POSITIONS"

command="cd '$VJF' && EVENT='$EVENT' WORKERS='$WORKERS' RUN_TAG='$RUN_TAG' DISPATCH_MANIFEST='$REPORT/dispatch_manifest.csv' CONFIG_DIR='$CONFIG_DIR' MCMC_SETTINGS='$MCMC_SETTINGS' INITIAL_POSITIONS='$INITIAL_POSITIONS' FORCE_FRESH=1 ENABLE_PREFLIGHT=1 PREFLIGHT_BURN_LENGTH=1 PREFLIGHT_RUN_LENGTH=1 CLEAN_INCOMPLETE=1 SKIP_COMPLETED=0 bash '$RUNNER'"
"${SSH[@]}" "$HOST" "tmux has-session -t '$SESSION' 2>/dev/null && exit 0; tmux new-session -d -s '$SESSION' \"$command\""
echo "started host=$HOST session=$SESSION workers=$WORKERS run_tag=$RUN_TAG"
