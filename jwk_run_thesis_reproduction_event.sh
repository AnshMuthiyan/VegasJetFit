#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
RUNNER="${RUNNER:-$VEGAS_DIR/jwk_run_vegas_jet_fit.sh}"

EVENT="${EVENT:-${EVENT_NAME:-}}"
RUN_TAG="${RUN_TAG:-theta1p0_thesis_reproduction_median5sig_2000x2000_v1}"
if [ "${RESULTS_NAME_TEMPLATE+x}" != "x" ] || [ -z "${RESULTS_NAME_TEMPLATE:-}" ]; then
  RESULTS_NAME_TEMPLATE="{event}_thesis_reproduction_{run_tag}"
fi
CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/thesis_reproduction_configs}"
MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_dylanspec_2000x2000.toml}"

WORKERS="${WORKERS:-8}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-0}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
RUN_FOREGROUND="${RUN_FOREGROUND:-1}"
RUN_MINIMIZER="${RUN_MINIMIZER:-0}"
MINIMIZE_SCIPY_METHOD="${MINIMIZE_SCIPY_METHOD:-Powell}"
MINIMIZE_FALLBACK_SCIPY_METHOD="${MINIMIZE_FALLBACK_SCIPY_METHOD:-Nelder-Mead}"
REQUIRE_AUDIT_OBS_ROWS="${REQUIRE_AUDIT_OBS_ROWS:-0}"
REQUIRE_220101A_HST_FILTERS="${REQUIRE_220101A_HST_FILTERS:-1}"
REQUIRE_221009A_MILKY_WAY_RV_PRIOR="${REQUIRE_221009A_MILKY_WAY_RV_PRIOR:-1}"
DRIVE_SYNC_ENABLE="${DRIVE_SYNC_ENABLE:-0}"
SKIP_COMPLETED="${SKIP_COMPLETED:-1}"
CLEAN_INCOMPLETE="${CLEAN_INCOMPLETE:-1}"
REQUIRE_STANDARD_EJET_GAMMA_PRIORS="${REQUIRE_STANDARD_EJET_GAMMA_PRIORS:-1}"

if [ -z "$EVENT" ]; then
  echo "ERROR: EVENT or EVENT_NAME is required." >&2
  exit 2
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -x "$RUNNER" ]; then
  echo "ERROR: runner not found: $RUNNER" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings file not found: $MCMC_SETTINGS" >&2
  exit 2
fi

render_name() {
  local template="$1"
  local event="$2"
  local out
  out="${template//\{event\}/$event}"
  out="${out//\{run_tag\}/$RUN_TAG}"
  printf '%s\n' "$out"
}

detect_obs() {
  local obs_dir="$VEGAS_DIR/jetfit/resources/grbs/$EVENT"
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

copy_sidecars() {
  local obs_path="$1"
  local target_dir="${2:-$results_dir}"
  mkdir -p "$target_dir"
  if [ -f "$model_toml" ]; then
    cp -f "$model_toml" "$target_dir/model.toml"
  fi
  if [ -f "$MCMC_SETTINGS" ]; then
    cp -f "$MCMC_SETTINGS" "$target_dir/mcmc_settings.toml"
  fi
  if [ -f "$obs_path" ]; then
    cp -f "$obs_path" "$target_dir/obs.csv"
  fi
  if [ -f "$run_log" ]; then
    cp -f "$run_log" "$target_dir/run.log"
  fi
}

is_mcmc_complete() {
  [ -f "$results_dir/best_fit.json" ] && \
  [ -f "$results_dir/chain.npz" ] && \
  [ -f "$results_dir/summary.csv" ]
}

results_name="$(render_name "$RESULTS_NAME_TEMPLATE" "$EVENT")"
results_dir="$VEGAS_DIR/jetfit/results/$results_name"
preflight_results_dir="$VEGAS_DIR/jetfit/results/${results_name}_preflight"
log_stem="${EVENT}.${RUN_TAG}"
model_toml="$CONFIG_DIR/${EVENT}.toml"
run_log="$VEGAS_DIR/logs/${log_stem}.log"
preflight_log="$VEGAS_DIR/logs/${log_stem}.preflight.log"
preflight_mcmc="$VEGAS_DIR/logs/${log_stem}.preflight.mcmc.toml"
start_utc_file="$VEGAS_DIR/logs/${log_stem}.start_utc"
pid_file="$VEGAS_DIR/logs/${log_stem}.pid"

mkdir -p "$VEGAS_DIR/logs"

if [ ! -f "$model_toml" ]; then
  echo "ERROR: thesis reproduction model TOML not found: $model_toml" >&2
  exit 2
fi

"$PYTHON_BIN" - "$model_toml" "$REQUIRE_STANDARD_EJET_GAMMA_PRIORS" <<'PY'
import math
from pathlib import Path
import sys
import tomllib

path = Path(sys.argv[1])
require_standard = sys.argv[2] == "1"
data = tomllib.loads(path.read_text())
found_ejet = False
found_lf0 = False
energy_name = None
gamma_name = None
ejet_bounds = None
lf0_bounds = None
for param in data.get("model", []):
    name = param.get("name")
    if name in {"E_j_52", "E_j_core_52"} and param.get("prior") is not None:
        found_ejet = True
        energy_name = name
        scale = str(param.get("scale", "")).lower()
        if scale != "log":
            raise SystemExit(
                f"ERROR: fitted {name} must use scale='log'; "
                f"found scale={scale!r} in {path}"
            )
        prior = param["prior"]
        ejet_bounds = (
            float(prior.get("lower", math.nan)),
            float(prior.get("upper", math.nan)),
        )
    if name in {"lf0", "Gamma_0_core_avg"} and param.get("prior") is not None:
        found_lf0 = True
        gamma_name = name
        scale = str(param.get("scale", "")).lower()
        if scale != "log":
            raise SystemExit(
                f"ERROR: fitted {name} must use scale='log'; "
                f"found scale={scale!r} in {path}"
            )
        prior = param["prior"]
        lf0_bounds = (
            float(prior.get("lower", math.nan)),
            float(prior.get("upper", math.nan)),
        )
if require_standard and found_ejet:
    lower, upper = ejet_bounds
    if not (math.isclose(lower, -4.0) and math.isclose(upper, 2.0)):
        raise SystemExit(
            f"ERROR: standard fitted {energy_name} prior must use log10 bounds [-4,2] "
            f"(10^48..10^54 erg); found [{lower},{upper}] in {path}. "
            "Set REQUIRE_STANDARD_EJET_GAMMA_PRIORS=0 only for an explicitly "
            "approved special-prior experiment."
        )
if require_standard and found_ejet and not found_lf0:
    raise SystemExit(
        f"ERROR: standard {energy_name} fit has no fitted Lorentz-factor prior in {path}"
    )
if require_standard and found_ejet:
    lower, upper = lf0_bounds
    expected_lower = math.log10(50.0)
    expected_upper = 5.0
    if not (math.isclose(lower, expected_lower) and math.isclose(upper, expected_upper)):
        raise SystemExit(
            f"ERROR: standard {gamma_name} prior must represent [50,100000], "
            f"log10 bounds [{expected_lower},{expected_upper}]; found "
            f"[{lower},{upper}] in {path}. Set "
            "REQUIRE_STANDARD_EJET_GAMMA_PRIORS=0 only for an explicitly "
            "approved special-prior experiment."
        )
if energy_name == "E_j_core_52" and gamma_name != "Gamma_0_core_avg":
    raise SystemExit(
        "ERROR: core-energy parameterization requires Gamma_0_core_avg, "
        f"not {gamma_name!r}, in {path}"
    )
if gamma_name == "Gamma_0_core_avg" and energy_name != "E_j_core_52":
    raise SystemExit(
        "ERROR: core-average Gamma parameterization requires E_j_core_52, "
        f"not {energy_name!r}, in {path}"
    )
if energy_name == "E_j_52":
    print(
        f"WARNING: legacy total-E_j/on-axis-Gamma parameterization in {path}; "
        "new future configs should use E_j_core_52 and Gamma_0_core_avg."
    )
PY

if [ "$EVENT" = "221009A" ] && [ "$REQUIRE_221009A_MILKY_WAY_RV_PRIOR" = "1" ]; then
  "$PYTHON_BIN" - "$model_toml" <<'PY'
from pathlib import Path
import sys
import tomllib

path = Path(sys.argv[1])
data = tomllib.loads(path.read_text())
for entry in data.get("extinction", []):
    if isinstance(entry, dict) and entry.get("name") == "rv_milky_way":
        prior = entry.get("prior")
        if isinstance(prior, dict) and prior.get("type") == "milkywayrv":
            raise SystemExit(0)
        raise SystemExit(
            "ERROR: 221009A rv_milky_way must use prior type 'milkywayrv'; "
            f"found {prior!r} in {path}"
        )
raise SystemExit(f"ERROR: 221009A config is missing rv_milky_way in {path}")
PY
fi

obs_csv="${OBS_CSV_OVERRIDE:-}"
if [ -z "$obs_csv" ]; then
  obs_csv="$(detect_obs || true)"
fi
if [ -z "$obs_csv" ] || [ ! -f "$obs_csv" ]; then
  echo "ERROR: observation CSV not found for $EVENT" >&2
  exit 2
fi

# The approved GRB 090424 analysis includes all Swift UVOT/UVOIR points.
# Earlier campaign files accidentally retained the legacy exclusions, so make
# that scientifically consequential choice an explicit launch-time invariant.
# The early X-ray sequence remains independently excluded by the approved CSV.
if [ "$EVENT" = "090424" ] && [ "${REQUIRE_090424_ALL_UV:-1}" = "1" ]; then
  "$PYTHON_BIN" - "$obs_csv" <<'PY'
import csv
import sys

path = sys.argv[1]
required = {"uvw2", "uvm2", "uvw1", "uvot-u", "uvot-b", "uvot-v"}
included = 0
excluded = []
with open(path, newline="") as handle:
    for row in csv.DictReader(handle):
        band = (row.get("Filter") or row.get("Band") or "").strip().lower()
        if band not in required:
            continue
        raw = (row.get("Include") or "").strip()
        is_included = raw == "" or raw.lower() not in {"0", "false", "no", "n", "exclude"}
        if is_included:
            included += 1
        else:
            excluded.append((band, row.get("Time", "")))
if included != 79 or excluded:
    raise SystemExit(
        "ERROR: GRB 090424 requires all 79 UVOT/UVOIR measurements to be included; "
        f"found included={included}, excluded={len(excluded)} in {path}. "
        "Use the approved early-UVOIR override or explicitly set "
        "REQUIRE_090424_ALL_UV=0 only for a documented historical reproduction."
    )
PY
fi

if [ "$EVENT" = "220101A" ] && [ "$REQUIRE_220101A_HST_FILTERS" = "1" ]; then
  "$PYTHON_BIN" - "$obs_csv" <<'PY'
import csv
import math
import sys

path = sys.argv[1]
required = {"F775W", "F125W"}
generic_duplicates = {("i", 36.97), ("J", 37.04)}
included_hst = set()
included_generic_duplicates = []
included_early_xray_times = []


def is_included(row):
    raw = (row.get("Include") or "").strip()
    if raw == "":
        return True
    try:
        return float(raw) != 0.0
    except ValueError:
        return raw.lower() not in {"false", "no", "n", "exclude"}


with open(path, newline="") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        if not is_included(row):
            continue
        band = (row.get("Filter") or row.get("Band") or "").strip()
        if band in required:
            included_hst.add(band)
        try:
            time_value = float(row.get("Time", "nan"))
        except ValueError:
            time_value = math.nan
        for duplicate_band, duplicate_time in generic_duplicates:
            if band == duplicate_band and math.isclose(time_value, duplicate_time, rel_tol=0.0, abs_tol=1.0e-6):
                included_generic_duplicates.append((band, time_value))
        value_type = (row.get("ValueType") or "").strip().lower()
        time_units = (row.get("TimeUnits") or "").strip().lower()
        if band.lower() == "xray" and value_type == "integrated flux" and time_units.startswith("s"):
            if 150.0 <= time_value <= 250.0:
                included_early_xray_times.append(time_value)

missing = sorted(required - included_hst)
if missing:
    raise SystemExit(
        "ERROR: 220101A obs CSV must include HST filters "
        f"F775W and F125W; missing {missing} in {path}"
    )
if included_generic_duplicates:
    raise SystemExit(
        "ERROR: 220101A obs CSV includes generic i/J duplicates for the "
        f"late HST points: {included_generic_duplicates} in {path}"
    )
if len(included_early_xray_times) < 100:
    raise SystemExit(
        "ERROR: 220101A obs CSV must include Dylan's early X-ray clump "
        f"around t~10^-2.7 d; found only {len(included_early_xray_times)} "
        f"included xray rows between 150 and 250 s in {path}"
    )
if min(included_early_xray_times) > 160.0 or max(included_early_xray_times) < 235.0:
    raise SystemExit(
        "ERROR: 220101A included early X-ray clump has the wrong time span: "
        f"{min(included_early_xray_times)}..{max(included_early_xray_times)} s "
        f"in {path}"
    )
PY
fi

if [ "$REQUIRE_AUDIT_OBS_ROWS" = "1" ]; then
  "$PYTHON_BIN" "$VEGAS_DIR/scripts/check_obs_rows_against_audit.py" \
    --event "$EVENT" \
    --obs "$obs_csv" \
    --mode fail
fi

if [ "$SKIP_COMPLETED" = "1" ] && is_mcmc_complete; then
  copy_sidecars "$obs_csv"
  echo "Skipping completed MCMC run: $results_dir"
  exit 0
fi

if [ -d "$results_dir" ] && ! is_mcmc_complete && [ "$CLEAN_INCOMPLETE" = "1" ]; then
  rm -rf "$results_dir"
fi
if [ -d "$preflight_results_dir" ] && [ "$CLEAN_INCOMPLETE" = "1" ]; then
  rm -rf "$preflight_results_dir"
fi

mkdir -p "$results_dir"
copy_sidecars "$obs_csv"

# Stage the approved per-event rationale only after incomplete-result cleanup.
# This makes the record durable for both fresh launches and safe restarts.
if [ -n "${EVENT_DECISION_RECORDS:-}" ]; then
  if [ ! -f "$EVENT_DECISION_RECORDS" ]; then
    echo "ERROR: decision-record file is missing: $EVENT_DECISION_RECORDS" >&2
    exit 2
  fi
  "$PYTHON_BIN" "$VEGAS_DIR/scripts/stage_event_decision_record.py" \
    --records "$EVENT_DECISION_RECORDS" \
    --event "$EVENT" \
    --out "$results_dir/decision_record.json"
fi

echo "=================================================="
echo "Thesis reproduction MCMC event launch"
echo "Event:            $EVENT"
echo "Model TOML:       $model_toml"
echo "Obs CSV:          $obs_csv"
echo "Results:          $results_dir"
echo "MCMC settings:    $MCMC_SETTINGS"
echo "Workers:          $WORKERS"
echo "Initial positions: ${INITIAL_POSITIONS:-prior draws}"
echo "Preflight:        $ENABLE_PREFLIGHT"
echo "Run minimizer:    $RUN_MINIMIZER"
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
INITIAL_POSITIONS="${INITIAL_POSITIONS:-}" \
ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
KEEP_AWAKE="$KEEP_AWAKE" \
RESUME="${RESUME:-0}" \
RUN_FOREGROUND="$RUN_FOREGROUND" \
RUN_MINIMIZER="$RUN_MINIMIZER" \
MINIMIZE_SCIPY_METHOD="$MINIMIZE_SCIPY_METHOD" \
MINIMIZE_FALLBACK_SCIPY_METHOD="$MINIMIZE_FALLBACK_SCIPY_METHOD" \
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
if [ -d "$preflight_results_dir" ]; then
  copy_sidecars "$obs_csv" "$preflight_results_dir"
fi
