#!/usr/bin/env bash
set -euo pipefail

# Seed new full-run result directories from completed short-run outputs,
# then resume each parallel-tempered chain to the longer target run length.

ROOT="${ROOT:-$HOME/GRBs}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
RUN_PROFILE_DIR="${RUN_PROFILE_DIR:-$VEGAS_DIR/Ansh_Run}"
RESULTS_ROOT="${RESULTS_ROOT:-$VEGAS_DIR/jetfit/results}"

SOURCE_RUN_TAG="${SOURCE_RUN_TAG:-theta1p0_thesis_short}"
TARGET_RUN_TAG="${TARGET_RUN_TAG:-theta1p0_thesis_full}"

MCMC_SETTINGS="${MCMC_SETTINGS:-$RUN_PROFILE_DIR/mcmc_settings_thesis_full.toml}"
WORKERS="${WORKERS:-8}"
ENABLE_PREFLIGHT="${ENABLE_PREFLIGHT:-1}"
PREFLIGHT_BURN_LENGTH="${PREFLIGHT_BURN_LENGTH:-10}"
PREFLIGHT_RUN_LENGTH="${PREFLIGHT_RUN_LENGTH:-10}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
CONTINUE_ON_ERROR="${CONTINUE_ON_ERROR:-1}"
DRY_RUN="${DRY_RUN:-0}"

# Optional explicit event list (space- or comma-separated).
GRBS="${GRBS:-}"

if [ ! -d "$RESULTS_ROOT" ]; then
  echo "ERROR: results root not found: $RESULTS_ROOT" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings not found: $MCMC_SETTINGS" >&2
  exit 2
fi

events=()
if [ -n "$GRBS" ]; then
  read -r -a events <<< "$(echo "$GRBS" | tr ',' ' ')"
else
  while IFS= read -r src_dir; do
    [ -n "$src_dir" ] || continue
    base="$(basename "$src_dir")"
    event="${base%_powerlaw_tophat_${SOURCE_RUN_TAG}}"
    [ -n "$event" ] && events+=("$event")
  done < <(find "$RESULTS_ROOT" -maxdepth 1 -type d -name "*_powerlaw_tophat_${SOURCE_RUN_TAG}" | sort)
fi

if [ "${#events[@]}" -eq 0 ]; then
  echo "ERROR: no source short-run directories found for run tag: $SOURCE_RUN_TAG" >&2
  exit 2
fi

seeded=0
skipped=0
missing=0

echo "=================================================="
echo "Seed Full On-Axis Powerlaw Runs"
echo "Source tag:       $SOURCE_RUN_TAG"
echo "Target tag:       $TARGET_RUN_TAG"
echo "MCMC settings:    $MCMC_SETTINGS"
echo "Workers:          $WORKERS"
echo "Preflight:        $ENABLE_PREFLIGHT (burn=$PREFLIGHT_BURN_LENGTH run=$PREFLIGHT_RUN_LENGTH)"
echo "Keep awake:       $KEEP_AWAKE"
echo "Dry run:          $DRY_RUN"
echo "Events:           ${events[*]}"
echo "=================================================="
echo

for event in "${events[@]}"; do
  src_dir="$RESULTS_ROOT/${event}_powerlaw_tophat_${SOURCE_RUN_TAG}"
  dst_dir="$RESULTS_ROOT/${event}_powerlaw_tophat_${TARGET_RUN_TAG}"

  if [ ! -f "$src_dir/pt_resume_state.npz" ]; then
    echo "[seed] missing checkpoint, skipping: $src_dir"
    missing=$((missing + 1))
    continue
  fi

  if [ -d "$dst_dir" ] && [ -f "$dst_dir/pt_resume_state.npz" ]; then
    echo "[seed] already present, keeping: $dst_dir"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[seed] $src_dir -> $dst_dir"
  if [ "$DRY_RUN" != "1" ]; then
    rm -rf "$dst_dir"
    cp -a "$src_dir" "$dst_dir"
  fi
  seeded=$((seeded + 1))
done

echo
echo "Seed summary: seeded=$seeded skipped=$skipped missing=$missing"
echo

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN=1 set, not launching resumed full runs."
  exit 0
fi

grbs_csv="$(printf '%s\n' "${events[@]}" | paste -sd, -)"

exec env \
  ROOT="$ROOT" \
  VEGAS_DIR="$VEGAS_DIR" \
  RUN_PROFILE_DIR="$RUN_PROFILE_DIR" \
  MCMC_SETTINGS="$MCMC_SETTINGS" \
  WORKERS="$WORKERS" \
  ENABLE_PREFLIGHT="$ENABLE_PREFLIGHT" \
  PREFLIGHT_BURN_LENGTH="$PREFLIGHT_BURN_LENGTH" \
  PREFLIGHT_RUN_LENGTH="$PREFLIGHT_RUN_LENGTH" \
  KEEP_AWAKE="$KEEP_AWAKE" \
  RESUME=1 \
  SKIP_COMPLETED=0 \
  CONTINUE_ON_ERROR="$CONTINUE_ON_ERROR" \
  DRY_RUN=0 \
  THETA_C=1.0 \
  THETA_V=0.0 \
  RUN_TAG="$TARGET_RUN_TAG" \
  GRBS="$grbs_csv" \
  bash "$VEGAS_DIR/jwk_run_all_onaxis_powerlaw.sh"
