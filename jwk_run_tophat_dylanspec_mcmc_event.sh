#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
TOPHAT_BUILDER="${TOPHAT_BUILDER:-$VEGAS_DIR/scripts/build_tophat_model_toml.py}"
RUNNER="${RUNNER:-$VEGAS_DIR/jwk_run_vegas_jet_fit.sh}"

EVENT="${EVENT:-${EVENT_NAME:-}}"
SOURCE_RESULTS_TAG="${SOURCE_RESULTS_TAG:-theta1p0_thesis_short_kmin10_seeded_v1}"
RUN_TAG="${RUN_TAG:-theta1p0_thesis_short_kmin10_seeded_vegasv201_dylanspec_v1}"
MODEL_NAME="${MODEL_NAME:-powerlawVegasDylanSpectrumModel}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_short.toml}"
SEED_BEST_FIT_ROOT="${SEED_BEST_FIT_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
SEED_OWNER_SUBDIR="${SEED_OWNER_SUBDIR:-jkeohane}"

THETA_C="${THETA_C:-1.0}"
THETA_V="${THETA_V:-0.0}"
K_LOWER="${K_LOWER:--10.0}"
K_UPPER="${K_UPPER:-3.0}"

WORKERS="${WORKERS:-8}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RUN_FOREGROUND="${RUN_FOREGROUND:-1}"
RUN_MINIMIZER="${RUN_MINIMIZER:-1}"
MINIMIZE_MODE="${MINIMIZE_MODE:-walkers}"
MINIMIZE_MAX_WALKERS="${MINIMIZE_MAX_WALKERS:-0}"
MINIMIZE_MINIMIZER="${MINIMIZE_MINIMIZER:-minimize}"
MINIMIZE_SCIPY_METHOD="${MINIMIZE_SCIPY_METHOD:-Powell}"
MINIMIZE_FALLBACK_SCIPY_METHOD="${MINIMIZE_FALLBACK_SCIPY_METHOD:-Nelder-Mead}"
MINIMIZE_OUTPUT_DIR="${MINIMIZE_OUTPUT_DIR:-}"
MINIMIZE_STRICT="${MINIMIZE_STRICT:-0}"
DRIVE_SYNC_ENABLE="${DRIVE_SYNC_ENABLE:-0}"
AUTO_DISABLE_PREFLIGHT_ON_RESUME="${AUTO_DISABLE_PREFLIGHT_ON_RESUME:-1}"
SKIP_COMPLETED="${SKIP_COMPLETED:-1}"

if [ -z "$EVENT" ]; then
  echo "ERROR: EVENT or EVENT_NAME is required." >&2
  exit 2
fi

source_results_dir="$VEGAS_DIR/jetfit/results/${EVENT}_powerlaw_tophat_${SOURCE_RESULTS_TAG}"
results_dir="$VEGAS_DIR/jetfit/results/${EVENT}_powerlaw_tophat_${RUN_TAG}"
preflight_results_dir="$VEGAS_DIR/jetfit/results/${EVENT}_powerlaw_tophat_${RUN_TAG}_preflight"
source_model="$VEGAS_DIR/jetfit/resources/grbs/$EVENT/parameters.toml"
log_stem="${EVENT}.${RUN_TAG}"
model_toml="$VEGAS_DIR/logs/${log_stem}.parameters.toml"
run_log="$VEGAS_DIR/logs/${log_stem}.log"
preflight_log="$VEGAS_DIR/logs/${log_stem}.preflight.log"
preflight_mcmc="$VEGAS_DIR/logs/${log_stem}.preflight.mcmc.toml"
start_utc_file="$VEGAS_DIR/logs/${log_stem}.start_utc"
pid_file="$VEGAS_DIR/logs/${log_stem}.pid"
obs_dir="$VEGAS_DIR/jetfit/resources/grbs/$EVENT"
seed_json=""

mkdir -p "$VEGAS_DIR/logs" "$results_dir"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -f "$TOPHAT_BUILDER" ]; then
  echo "ERROR: top-hat builder not found: $TOPHAT_BUILDER" >&2
  exit 2
fi
if [ ! -f "$RUNNER" ]; then
  echo "ERROR: runner not found: $RUNNER" >&2
  exit 2
fi
if [ ! -f "$source_model" ]; then
  echo "ERROR: event parameters missing: $source_model" >&2
  exit 2
fi
detect_obs() {
  local clean="$obs_dir/${EVENT}clean.csv"
  local plain="$obs_dir/${EVENT}.csv"
  if [ -f "$clean" ]; then
    printf '%s\n' "$clean"
    return 0
  fi
  if [ -f "$plain" ]; then
    printf '%s\n' "$plain"
    return 0
  fi
  find "$obs_dir" -maxdepth 1 -type f -name '*.csv' | sort | head -n 1
}

choose_seed_json() {
  "$PYTHON_BIN" - <<'PY' "$EVENT" "$source_results_dir" "$SEED_BEST_FIT_ROOT" "$SEED_OWNER_SUBDIR"
import json
import math
import sys
from pathlib import Path

event = sys.argv[1]
root = Path(sys.argv[2])
drive_root = Path(sys.argv[3])
owner = sys.argv[4]


def valid_json(candidate: Path) -> bool:
    if not candidate.exists():
        return False
    if candidate.name != "minimized.json":
        return True
    try:
        payload = json.loads(candidate.read_text())
    except Exception:
        return False
    success = payload.get("success")
    nmap = payload.get("nmap")
    return success is True and isinstance(nmap, (int, float)) and math.isfinite(float(nmap))


drive_event = drive_root / event
candidates = [
    drive_event / "PL Open On-Axis" / "best_fit.json",
    drive_event / "PL Open OnAxis" / "best_fit.json",
    drive_event / "PL Open On-Axis (1)" / "best_fit.json",
    drive_event / "PL Open OnAxis (1)" / "best_fit.json",
    drive_event / "2000 2000Run" / "best_fit.json",
    drive_event / "2000 2000Run (1)" / "best_fit.json",
    drive_event / owner / f"{event}_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_vegasv201_dylanspec_v3" / "minimized" / "minimized.json",
    drive_event / owner / f"{event}_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_vegasv201_dylanspec_v2" / "minimized" / "minimized.json",
    drive_event / owner / f"{event}_powerlaw_tophat_theta1p0_thesis_short_kmin10_seeded_vegasv201_dylanspec_v1" / "minimized" / "minimized.json",
    drive_event / owner / f"{event}_powerlaw_tophat_theta1p0_resume5k" / "best_fit.json",
    drive_event / owner / f"{event}_powerlaw_tophat_theta1p0_thesis_full" / "best_fit.json",
    drive_event / owner / f"{event}_powerlaw_tophat_theta1p0_thesis_short" / "best_fit.json",
    root / "minimized_vegasv201_dylanspec_v1" / "minimized.json",
    root / "minimized" / "minimized.json",
    root / "best_fit.json",
]

for candidate in candidates:
    if valid_json(candidate):
        print(candidate)
        raise SystemExit(0)

print("")
PY
}

copy_sidecars() {
  local obs_path="$1"
  [ -f "$model_toml" ] && cp -f "$model_toml" "$results_dir/model.toml"
  [ -f "$MCMC_SETTINGS" ] && cp -f "$MCMC_SETTINGS" "$results_dir/mcmc_settings.toml"
  [ -f "$obs_path" ] && cp -f "$obs_path" "$results_dir/obs.csv"
  if [ -f "$run_log" ]; then
    cp -f "$run_log" "$results_dir/run.log"
  fi
}

is_complete() {
  [ -f "$results_dir/best_fit.json" ] && \
  [ -f "$results_dir/chain.npz" ] && \
  [ -f "$results_dir/summary.csv" ] && \
  [ -f "$results_dir/minimized/minimized.json" ]
}

obs_csv="$(detect_obs || true)"
if [ -z "$obs_csv" ] || [ ! -f "$obs_csv" ]; then
  echo "ERROR: observation CSV not found for $EVENT" >&2
  exit 2
fi

if [ "$SKIP_COMPLETED" = "1" ] && is_complete; then
  copy_sidecars "$obs_csv"
  echo "Skipping completed run: $results_dir"
  exit 0
fi

seed_json="$(choose_seed_json)"
if [ -z "$seed_json" ]; then
  echo "ERROR: could not determine a seed JSON for $EVENT" >&2
  exit 2
fi

"$PYTHON_BIN" "$TOPHAT_BUILDER" \
  --input "$source_model" \
  --output "$model_toml" \
  --theta-c "$THETA_C" \
  --theta-v "$THETA_V" \
  --k-lower "$K_LOWER" \
  --k-upper "$K_UPPER" \
  --seed-best-fit "$seed_json" \
  --model-name "$MODEL_NAME"

copy_sidecars "$obs_csv"

resume_flag=0
if [ -f "$results_dir/pt_resume_state.npz" ]; then
  resume_flag=1
  if [ "$AUTO_DISABLE_PREFLIGHT_ON_RESUME" = "1" ]; then
    ENABLE_PREFLIGHT=0
  fi
fi

echo "=================================================="
echo "Dylan-spectrum top-hat MCMC event launch"
echo "Event:            $EVENT"
echo "Source results:   $source_results_dir"
echo "New results:      $results_dir"
echo "Seed JSON:        $seed_json"
echo "Model TOML:       $model_toml"
echo "Obs CSV:          $obs_csv"
echo "MCMC settings:    $MCMC_SETTINGS"
echo "Workers:          $WORKERS"
echo "Resume:           $resume_flag"
echo "Preflight:        $ENABLE_PREFLIGHT"
echo "Drive sync:       $DRIVE_SYNC_ENABLE"
echo "=================================================="

ROOT="$ROOT" \
RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
EVENT_NAME="$EVENT" \
MODEL_CHOICE="powerlaw" \
MODEL_TOML="$model_toml" \
OBS_CSV="$obs_csv" \
MCMC_SETTINGS="$MCMC_SETTINGS" \
WORKERS="$WORKERS" \
ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
KEEP_AWAKE="$KEEP_AWAKE" \
RESUME="$resume_flag" \
RUN_FOREGROUND="$RUN_FOREGROUND" \
RUN_MINIMIZER="$RUN_MINIMIZER" \
MINIMIZE_MODE="$MINIMIZE_MODE" \
MINIMIZE_MAX_WALKERS="$MINIMIZE_MAX_WALKERS" \
MINIMIZE_MINIMIZER="$MINIMIZE_MINIMIZER" \
MINIMIZE_SCIPY_METHOD="$MINIMIZE_SCIPY_METHOD" \
MINIMIZE_FALLBACK_SCIPY_METHOD="$MINIMIZE_FALLBACK_SCIPY_METHOD" \
MINIMIZE_OUTPUT_DIR="$MINIMIZE_OUTPUT_DIR" \
MINIMIZE_STRICT="$MINIMIZE_STRICT" \
DRIVE_SYNC_ENABLE="$DRIVE_SYNC_ENABLE" \
DRIVE_RUN_LABEL="$(basename "$results_dir")" \
RESULTS_DIR="$results_dir" \
LOG_BASENAME="$log_stem" \
LOG_FILE_OVERRIDE="$run_log" \
PREFLIGHT_RESULTS="$preflight_results_dir" \
PREFLIGHT_LOG_FILE_OVERRIDE="$preflight_log" \
PREFLIGHT_MCMC_FILE_OVERRIDE="$preflight_mcmc" \
START_UTC_FILE_OVERRIDE="$start_utc_file" \
PID_FILE_OVERRIDE="$pid_file" \
bash "$RUNNER"

copy_sidecars "$obs_csv"
