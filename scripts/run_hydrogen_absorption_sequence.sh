#!/usr/bin/env bash
set -euo pipefail

event="${1:?usage: run_hydrogen_absorption_sequence.sh EVENT}"
VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
for stage in smoke diagnostic; do
  for variant in none igm igm_host; do
    WORKERS="${WORKERS:-8}" VJF="$VJF" \
      bash "$VJF/scripts/run_hydrogen_absorption_variant.sh" \
        "$event" "$variant" "$stage"
  done
done
