#!/usr/bin/env bash
# Guarded workstation launcher for the 2026-09-01 GRB 080319B n17-boundary refit.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="${EVENT:?set EVENT}"
WORKERS="${WORKERS:?set WORKERS}"
CONFIG_DIR="$VJF/structured_jet_core_logangle_080319B_n17upper15_finalfinal_sthawed_5temp_configs"
MCMC_SETTINGS="$VJF/Ansh_Run/mcmc_settings_core_logangle_finalfinal_sthawed_5temp_1000x5000.toml"
INITIAL_POSITIONS="$VJF/initial_positions/080319B_n17upper15_finalfinal_sthawed_5temp.npz"
OBS_CSV_OVERRIDE="$VJF/obs_overrides/080319B_authoritative_all_early_uvoir_20260901.csv"
GENERIC_RUNNER="$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh"
HOST_SHORT="$(hostname -s | tr '[:upper:]' '[:lower:]')"

[ "$EVENT" = "080319B" ] || { echo "ERROR: this runner is only for 080319B" >&2; exit 2; }
case "$HOST_SHORT" in
  pcrc-*) EXPECTED_WORKERS=14 ;;
  pauley*) EXPECTED_WORKERS=8 ;;
  *) echo "ERROR: unsupported MCMC host $HOST_SHORT" >&2; exit 2 ;;
esac
[ "$WORKERS" = "$EXPECTED_WORKERS" ] || {
  echo "ERROR: expected $EXPECTED_WORKERS workers on $HOST_SHORT, got $WORKERS" >&2
  exit 2
}

verify_sha256() {
  local expected="$1" path="$2" actual
  [ -s "$path" ] || { echo "ERROR: missing required file: $path" >&2; exit 2; }
  actual="$(shasum -a 256 "$path" | awk '{print $1}')"
  [ "$actual" = "$expected" ] || {
    echo "ERROR: checksum mismatch for $path: expected=$expected actual=$actual" >&2
    exit 2
  }
}

verify_sha256 656cc4d5d71e1a9d2ed4d452e93673524d3731c8ed0296e934c240d1bd653f43 "$CONFIG_DIR/080319B.toml"
verify_sha256 6b313ca393b176dbacb1afae7ea99621d1df0cb5032cb75a98c819a23a83ff34 "$OBS_CSV_OVERRIDE"
verify_sha256 06d0c8bdd7a811eee9d0d44069d708c73e007d303ca7040e2f99a0e30bbbb4c4 "$INITIAL_POSITIONS"
verify_sha256 79e62535c95b054d806c40426c45bdab96c012b38195d5b4d610c05138dbe5c9 "$MCMC_SETTINGS"
verify_sha256 f7a3501cae8e2e5dd07644ca7d259b0a7d44658cba7deb4b50e36cc2853bb0d7 "$GENERIC_RUNNER"
verify_sha256 f45f944c1e0f649593e5a82610e47e5b13719ca15ae37b38fdbd71f70e33738c "$VJF/jwk_run_thesis_reproduction_event.sh"
verify_sha256 d9ca3b3b739a16403b5c3b9935c8e50295e769fc659831425e9300b52636db4f "$VJF/jetfit/run.py"
verify_sha256 c04581ecba43581e7fc75e1e27c1daa75168a9eb5938255bc6b6b916e23f323e "$VJF/jetfit/ampy.py"
verify_sha256 3e81e08b24009fe3f3168e26ea276f0c6fa808c89b2358f004478a55e5c11f56 "$VJF/jetfit/core/utils.py"
verify_sha256 ecf778c88c913c41bbb5abf2799fe5220194a585b87491061f4e23710264de43 "$VJF/jetfit/mcmc/mcmc.py"
verify_sha256 70f99ffeba6a76e32eb061ba099e8890af0133a7c614fec9fe0b13b5dcb3b64b "$VJF/jetfit/mcmc/parameters.py"
verify_sha256 af0c36adc83415bac98db3ae08811785c218690098425cc6f0908b7624b70256 "$VJF/jetfit/models/powerlawVegas.py"
verify_sha256 4ad67f8a6531f490a18952520bedb51a9a377ee578f3ae7ed50c598fc48a57b4 "$VJF/jetfit/models/powerlawJetVegasDylanSpectrum.py"
verify_sha256 1ccd68a198f31e6f0e07bfce2840e2b1ea40da8e59031769e11750c6d087849b "$VJF/jetfit/models/vegas_resolution.py"
verify_sha256 11e509f70b31020525fc60bc67d810bda43b95e47e4b4463dce6787b23bd6b91 "$VJF/jetfit/models/vegasafterglow.py"
verify_sha256 6a85c370f4fab2eacd3d4b48bbe77c7fa000e5841e11614168de4a063f4dd6cd "$VJF/jetfit/models/jet_energy.py"

"$ROOT/.venv/bin/python" - "$CONFIG_DIR/080319B.toml" "$INITIAL_POSITIONS" <<'PY'
import sys
import tomllib

import numpy as np

model_path, seed_path = sys.argv[1:]
with open(model_path, "rb") as handle:
    config = tomllib.load(handle)
n017 = next(entry for entry in config["model"] if entry.get("name") == "n017")
prior = n017["prior"]
if prior.get("type") != "uniform" or float(prior["lower"]) != -6.0 or float(prior["upper"]) != 15.0:
    raise SystemExit(f"invalid n017 prior: {prior}")

with np.load(seed_path, allow_pickle=False) as seed:
    positions = np.asarray(seed["positions"], dtype=float)
    names = np.asarray(seed["parameter_names"]).astype(str).tolist()
    if positions.shape != (5, 100, 37) or not np.isfinite(positions).all():
        raise SystemExit(f"invalid posterior cloud: shape={positions.shape}")
    if str(seed["ridge_parameter"]) != "n017" or str(seed["ridge_coupled_parameter"]) != "k":
        raise SystemExit("initializer does not carry the approved n017-k ridge metadata")
    n_index = names.index("n017")
    if positions[0, :, n_index].max() > 10.0 or positions[-1, :, n_index].max() < 13.0:
        raise SystemExit("initializer does not preserve the cold cloud and broaden the hot cloud as approved")
PY

echo "080319B n17-upper15 workstation preflight guard passed on $HOST_SHORT with $WORKERS workers"
exec env \
  CONFIG_DIR="$CONFIG_DIR" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  INITIAL_POSITIONS="$INITIAL_POSITIONS" \
  OBS_CSV_OVERRIDE="$OBS_CSV_OVERRIDE" \
  bash "$GENERIC_RUNNER"
