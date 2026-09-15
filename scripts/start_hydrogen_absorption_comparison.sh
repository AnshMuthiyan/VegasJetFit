#!/usr/bin/env bash
set -euo pipefail

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
REMOTE_VJF="${REMOTE_VJF:-/Users/jkeohane/GRBs/VegasJetFit}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"
P03_HOST="${P03_HOST:-pauley404-03}"
CONFIG_ROOT="$VJF/run_configs/hydrogen_absorption"
variants=(none igm igm_host)

ssh_cmd() {
  ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 "$@"
}

ssh_stream() {
  ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 "$@"
}

if pgrep -f '[j]etfit.run|[m]inimize.py' >/dev/null; then
  echo "Refusing to launch: Lyra already has an active fit or minimization." >&2
  exit 1
fi
if ssh_cmd "$P03_HOST" "pgrep -f '[j]etfit.run|[m]inimize.py' >/dev/null"; then
  echo "Refusing to launch: $P03_HOST already has an active fit or minimization." >&2
  exit 1
fi

for event in 160131A 220101A; do
  for variant in "${variants[@]}"; do
    test -s "$CONFIG_ROOT/$event/$variant/model.toml"
    test -s "$CONFIG_ROOT/$event/$variant/obs.csv"
    test -s "$CONFIG_ROOT/$event/$variant/initial_positions.npz"
  done
done

git -C "$VJF" ls-files -z | tar -C "$VJF" --null -T - -cf - | \
  ssh_stream "$P03_HOST" "tar -xf - -C '$REMOTE_VJF'"
tar -C "$VJF" -cf - run_configs/hydrogen_absorption | \
  ssh_stream "$P03_HOST" "tar -xf - -C '$REMOTE_VJF'"

ssh_cmd "$P03_HOST" "
  cd '$REMOTE_VJF' &&
  PYTHONPATH=. '$PY' -m py_compile \
    jetfit/core/hydrogen_absorption.py \
    jetfit/mcmc/parameters.py jetfit/mcmc/mcmc.py jetfit/ampy.py jetfit/run.py &&
  PYTHONPATH=. '$PY' -m pytest -q \
    test/core/test_hydrogen_absorption.py test/core/test_bandpass.py \
    test/mcmc/test_extinction_model_selection.py
"

local_session="hydrogen_absorption_220101A"
remote_session="hydrogen_absorption_160131A"
if tmux has-session -t "$local_session" 2>/dev/null; then
  echo "Refusing to replace existing Lyra tmux session $local_session." >&2
  exit 1
fi
if ssh_cmd "$P03_HOST" "tmux has-session -t '$remote_session' 2>/dev/null"; then
  echo "Refusing to replace existing $P03_HOST tmux session $remote_session." >&2
  exit 1
fi

ssh_cmd "$P03_HOST" \
  "tmux new-session -d -s '$remote_session' \"cd '$REMOTE_VJF' && exec caffeinate -is env WORKERS=8 bash scripts/run_hydrogen_absorption_sequence.sh 160131A\" && tmux has-session -t '$remote_session'"

tmux new-session -d -s "$local_session" \
  "cd '$VJF' && exec caffeinate -is env WORKERS=8 bash scripts/run_hydrogen_absorption_sequence.sh 220101A"
tmux has-session -t "$local_session"

watch_session="watch_hydrogen_absorption_comparison"
if ! tmux has-session -t "$watch_session" 2>/dev/null; then
  tmux new-session -d -s "$watch_session" \
    "cd '$VJF' && exec bash scripts/watch_hydrogen_absorption_comparison.sh >> logs/hydrogen_absorption_comparison.watch.log 2>&1"
fi
tmux has-session -t "$watch_session"
echo "Started 160131A on $P03_HOST and 220101A on Lyra; watcher=$watch_session."
