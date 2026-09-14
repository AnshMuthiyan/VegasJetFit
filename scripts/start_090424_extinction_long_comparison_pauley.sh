#!/usr/bin/env bash
set -euo pipefail

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
REMOTE_VJF="${REMOTE_VJF:-/Users/jkeohane/GRBs/VegasJetFit}"
PY="${PY:-/Users/jkeohane/GRBs/.venv/bin/python}"

# The Pauley Tailscale node keys expired on 2026-09-13. These LAN names retain
# strict checking against the already-trusted Tailscale host keys.
P01_HOST="${P01_HOST:-jkeohane@pauley404-01.local}"
P01_KEY="${P01_KEY:-100.84.118.63}"
P02_HOST="${P02_HOST:-jkeohane@pauley404-02.local}"
P02_KEY="${P02_KEY:-100.118.36.86}"

ssh_cmd() {
  local key_alias="$1"
  shift
  ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 \
    -o HostKeyAlias="$key_alias" "$@"
}

ssh_stream() {
  local key_alias="$1"
  shift
  ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12 \
    -o HostKeyAlias="$key_alias" "$@"
}

check_free() {
  local host="$1" key_alias="$2"
  if ssh_cmd "$key_alias" "$host" "pgrep -f '[j]etfit.run|[m]inimize.py' >/dev/null"; then
    echo "Refusing to launch: $host already has an active fit or minimization." >&2
    exit 1
  fi
}

deploy() {
  local host="$1" key_alias="$2"
  git -C "$VJF" ls-files -z | tar -C "$VJF" --null -T - -cf - | \
    ssh_stream "$key_alias" "$host" "tar -xf - -C '$REMOTE_VJF'"
  ssh_cmd "$key_alias" "$host" "
    cd '$REMOTE_VJF' &&
    PYTHONPATH=. '$PY' -m compileall -q jetfit scripts &&
    PYTHONPATH=. '$PY' -m unittest discover -s test/core -p 'test_bandpass.py' &&
    PYTHONPATH=. '$PY' -m unittest discover -s test/mcmc -p 'test_trotter_extinction.py' &&
    PYTHONPATH=. '$PY' -m unittest discover -s test -p 'test_run_metadata.py'
  "
}

launch() {
  local host="$1" key_alias="$2" variant="$3"
  local session="extcmp_090424_${variant}_long"
  local tag="090424_${variant}_bandpass_verified_5temp_100x800_v1"
  ssh_cmd "$key_alias" "$host" "
    if tmux has-session -t '$session' 2>/dev/null; then
      echo 'Session already active: $session'
      exit 0
    fi
    tmux new-session -d -s '$session' \
      \"cd '$REMOTE_VJF' && exec caffeinate -is bash scripts/run_090424_extinction_long_variant.sh '$variant'\"
    tmux has-session -t '$session'
    echo 'Started $tag in tmux session $session.'
  "
}

cd "$VJF"
"$PY" scripts/prepare_090424_extinction_long_comparison.py
check_free "$P01_HOST" "$P01_KEY"
check_free "$P02_HOST" "$P02_KEY"
deploy "$P01_HOST" "$P01_KEY"
deploy "$P02_HOST" "$P02_KEY"
launch "$P01_HOST" "$P01_KEY" trotter
launch "$P02_HOST" "$P02_KEY" ccm

watch_session="watch_090424_extinction_comparison"
if ! tmux has-session -t "$watch_session" 2>/dev/null; then
  tmux new-session -d -s "$watch_session" \
    "cd '$VJF' && exec bash scripts/watch_090424_extinction_long_comparison_lyra.sh >> logs/090424_extinction_long_comparison.watch.log 2>&1"
fi
tmux has-session -t "$watch_session"
echo "Lyra watcher active in tmux session $watch_session."
