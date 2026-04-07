#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VEGAS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$VEGAS_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
SPECTRUM_TIMESERIES_SCRIPT="$SCRIPT_DIR/generate_spectrum_timeseries.py"

usage() {
  cat <<'EOF'
Usage:
  sync_results_to_drive.sh \
    --results-dir <path> \
    --event <GRB_EVENT> \
    [--drive-root <path>] \
    [--owner-subdir <name>] \
    [--run-label <name>] \
    [--log-file <path>] \
    [--mcmc-file <path>] \
    [--model-file <path>] \
    [--obs-file <path>]

Behavior:
  Copies a finished VegasJetFit results directory into:
    <drive-root>/<event>/<owner-subdir>/<run-label>/
EOF
}

RESULTS_DIR=""
EVENT_NAME=""
DRIVE_ROOT="${DRIVE_ROOT:-/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns}"
OWNER_SUBDIR="${OWNER_SUBDIR:-jkeohane}"
RUN_LABEL=""
LOG_FILE=""
MCMC_FILE=""
MODEL_FILE=""
OBS_FILE=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --results-dir)
      RESULTS_DIR="${2:-}"
      shift 2
      ;;
    --event)
      EVENT_NAME="${2:-}"
      shift 2
      ;;
    --drive-root)
      DRIVE_ROOT="${2:-}"
      shift 2
      ;;
    --owner-subdir)
      OWNER_SUBDIR="${2:-}"
      shift 2
      ;;
    --run-label)
      RUN_LABEL="${2:-}"
      shift 2
      ;;
    --log-file)
      LOG_FILE="${2:-}"
      shift 2
      ;;
    --mcmc-file)
      MCMC_FILE="${2:-}"
      shift 2
      ;;
    --model-file)
      MODEL_FILE="${2:-}"
      shift 2
      ;;
    --obs-file)
      OBS_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$RESULTS_DIR" ] || [ -z "$EVENT_NAME" ]; then
  echo "ERROR: --results-dir and --event are required." >&2
  usage >&2
  exit 2
fi
if [ ! -d "$RESULTS_DIR" ]; then
  echo "ERROR: results directory not found: $RESULTS_DIR" >&2
  exit 2
fi
if [ ! -d "$DRIVE_ROOT" ]; then
  echo "ERROR: drive root not found: $DRIVE_ROOT" >&2
  exit 2
fi
if [ -z "$RUN_LABEL" ]; then
  RUN_LABEL="$(basename "$RESULTS_DIR")"
fi

if [ ! -f "$RESULTS_DIR/spectrum_timeseries.pdf" ] \
  && [ -x "$PYTHON_BIN" ] \
  && [ -f "$SPECTRUM_TIMESERIES_SCRIPT" ] \
  && [ -f "$RESULTS_DIR/model.toml" ] \
  && [ -f "$RESULTS_DIR/obs.csv" ]; then
  PYTHONPATH="$VEGAS_DIR:${PYTHONPATH:-}" \
    "$PYTHON_BIN" "$SPECTRUM_TIMESERIES_SCRIPT" --results "$RESULTS_DIR" >/dev/null || true
fi

DEST_DIR="$DRIVE_ROOT/$EVENT_NAME/$OWNER_SUBDIR/$RUN_LABEL"
mkdir -p "$DEST_DIR"

if command -v rsync >/dev/null 2>&1; then
  rsync -a "$RESULTS_DIR"/ "$DEST_DIR"/
else
  cp -R "$RESULTS_DIR"/. "$DEST_DIR"/
fi

if [ ! -f "$DEST_DIR/spectral_plot.pdf" ] && [ -f "$DEST_DIR/frequencies.pdf" ]; then
  cp -f "$DEST_DIR/frequencies.pdf" "$DEST_DIR/spectral_plot.pdf"
fi

copy_if_file() {
  local src="$1"
  local dst="$2"
  if [ -n "$src" ] && [ -f "$src" ]; then
    cp -f "$src" "$dst"
  fi
}

copy_if_file "$LOG_FILE" "$DEST_DIR/run.log"
copy_if_file "$MCMC_FILE" "$DEST_DIR/mcmc_settings.toml"
copy_if_file "$MODEL_FILE" "$DEST_DIR/model.toml"
copy_if_file "$OBS_FILE" "$DEST_DIR/obs.csv"

{
  echo "synced_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "event=$EVENT_NAME"
  echo "owner_subdir=$OWNER_SUBDIR"
  echo "run_label=$RUN_LABEL"
  echo "source_results=$RESULTS_DIR"
} > "$DEST_DIR/sync_manifest.txt"

echo "$DEST_DIR"
