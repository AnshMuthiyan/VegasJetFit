#!/usr/bin/env bash
# Guarded launcher for the all-UVOIR GRB 080319B n17-upper25 continuation.
set -euo pipefail

ROOT="${ROOT:-/Users/jkeohane/GRBs}"
VJF="$ROOT/VegasJetFit"
EVENT="${EVENT:?set EVENT}"
WORKERS="${WORKERS:?set WORKERS}"
CONFIG_DIR="$VJF/structured_jet_core_logangle_080319B_alluvoir_n17upper25_finalfinal_sthawed_5temp_configs"
MCMC_SETTINGS="$VJF/Ansh_Run/mcmc_settings_core_logangle_finalfinal_sthawed_5temp_1000x5000.toml"
INITIAL_POSITIONS="$VJF/initial_positions/080319B_alluvoir_n17upper25_finalfinal_sthawed_5temp.npz"
OBS_CSV_OVERRIDE="$VJF/obs_overrides/080319B_all_early_uvoir_included_n17upper15_20260904.csv"
GENERIC_RUNNER="$VJF/scripts/run_core_logangle_finalfinal_sthawed_5temp_event.sh"
RUN_TAG="core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_alluvoir_n17upper25_5temp_1000x5000_v1"
HOST_SHORT="$(hostname -s | tr '[:upper:]' '[:lower:]')"

[ "$EVENT" = "080319B" ] || { echo "ERROR: this runner is only for 080319B" >&2; exit 2; }
case "$HOST_SHORT" in
  pcrc-*) EXPECTED_WORKERS=14 ;;
  pauley*) EXPECTED_WORKERS=8 ;;
  lyra)
    [ "${PREFLIGHT_ONLY:-0}" = "1" ] || {
      echo "ERROR: Lyra is permitted only for a local preflight of this MCMC" >&2
      exit 2
    }
    EXPECTED_WORKERS=8
    ;;
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

verify_sha256 32c34200fddc9166c17a714972b489652d5903df2960c2efaa79bc4ad1cd3213 "$CONFIG_DIR/080319B.toml"
verify_sha256 136fc55f192117c6bb5be3b4389e72b5641ca58c94bd47f748fb143adb62fa3e "$OBS_CSV_OVERRIDE"
verify_sha256 c626825a381a6e074183f850df04681611b2ab6436acd23ad2f4c15d153a4d88 "$INITIAL_POSITIONS"
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

"$ROOT/.venv/bin/python" - "$CONFIG_DIR/080319B.toml" "$INITIAL_POSITIONS" "$OBS_CSV_OVERRIDE" <<'PY'
import sys
import tomllib

import numpy as np
import pandas as pd

model_path, seed_path, obs_path = sys.argv[1:]
with open(model_path, "rb") as handle:
    config = tomllib.load(handle)
n017 = next(entry for entry in config["model"] if entry.get("name") == "n017")
prior = n017["prior"]
if prior.get("type") != "uniform" or float(prior["lower"]) != -6.0 or float(prior["upper"]) != 25.0:
    raise SystemExit(f"invalid n017 prior: {prior}")

with np.load(seed_path, allow_pickle=False) as seed:
    positions = np.asarray(seed["positions"], dtype=float)
    names = np.asarray(seed["parameter_names"]).astype(str).tolist()
    if positions.shape != (5, 100, 37) or not np.isfinite(positions).all():
        raise SystemExit(f"invalid posterior cloud: shape={positions.shape}")
    source = str(seed["source_results"])
    if not source.endswith("080319B_core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_alluvoir_n17upper15_5temp_1000x5000_v1"):
        raise SystemExit(f"initializer has the wrong source posterior: {source}")
    if str(seed["ridge_parameter"]) != "n017" or str(seed["ridge_coupled_parameter"]) != "k":
        raise SystemExit("initializer lacks the documented n17-k hot-temperature ridge expansion")
    if float(seed["ridge_coupled_factor"]) != -1.0 or float(seed["ridge_max_shift"]) != 10.0:
        raise SystemExit("initializer has the wrong n17-k ridge controls")
    deltas = np.asarray(seed["ridge_deltas"], dtype=float)
    if deltas.shape != (5, 100) or not np.allclose(deltas[0], 0.0):
        raise SystemExit("cold ensemble must remain an exact source-posterior draw")
    n_index = names.index("n017")
    if positions[:, :, n_index].min() <= -6.0 or positions[:, :, n_index].max() >= 25.0:
        raise SystemExit("initializer contains n017 values outside the approved prior")

obs = pd.read_csv(obs_path)
if len(obs) != 2372 or "Include" not in obs or not (obs["Include"] == 1).all():
    raise SystemExit("observation override does not include all 2372 reviewed rows")
PY

echo "080319B all-UVOIR n17-upper25 workstation guard passed on $HOST_SHORT with $WORKERS workers"
exec env \
  RUN_TAG="$RUN_TAG" \
  CONFIG_DIR="$CONFIG_DIR" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  INITIAL_POSITIONS="$INITIAL_POSITIONS" \
  OBS_CSV_OVERRIDE="$OBS_CSV_OVERRIDE" \
  bash "$GENERIC_RUNNER"
