#!/usr/bin/env bash
set -euo pipefail

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
HOST="${HOST:-pauley404-01}"
REMOTE_VJF="/Users/jkeohane/GRBs/VegasJetFit"
SESSION="trotter_090424_weekend"
RESULT_TAG="090424_trotter_extinction_production_5temp_1000x5000_v1"
PY="/Users/jkeohane/GRBs/.venv/bin/python"
SSH=(ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12)
SSH_STREAM=(ssh -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=12)

if "${SSH[@]}" "$HOST" "pgrep -f '[j]etfit.run|[m]inimize.py' >/dev/null"; then
  echo "Refusing to launch: $HOST already has an active fit or minimization." >&2
  exit 1
fi

deploy_files=(
  jetfit/mcmc/mcmc.py
  jetfit/mcmc/trotter_extinction.py
  jetfit/run.py
  test/mcmc/test_trotter_extinction.py
  test/test_run_metadata.py
  run_configs/trotter_extinction/090424
  run_configs/trotter_extinction/mcmc_weekend_5temp_1000x5000.toml
)
(cd "$VJF" && tar -cf - "${deploy_files[@]}") |
  "${SSH_STREAM[@]}" "$HOST" "tar -xf - -C '$REMOTE_VJF'"

"${SSH[@]}" "$HOST" "
  cd '$REMOTE_VJF' &&
  PYTHONPATH=. '$PY' -m compileall -q jetfit/run.py jetfit/mcmc &&
  PYTHONPATH=. '$PY' -m unittest discover -s test/mcmc -p 'test_trotter_extinction.py' &&
  PYTHONPATH=. '$PY' -m unittest discover -s test -p 'test_run_metadata.py'
"

"${SSH[@]}" "$HOST" "
  test ! -e '$REMOTE_VJF/jetfit/results/$RESULT_TAG/chain.npz' &&
  tmux new-session -d -s '$SESSION' \
    \"cd '$REMOTE_VJF' && exec caffeinate -is /usr/bin/time -p env PYTHONPATH=. MPLBACKEND=Agg '$PY' -u -m jetfit.run \
      --event 090424 \
      --obs '$REMOTE_VJF/run_configs/trotter_extinction/090424/obs.csv' \
      --model '$REMOTE_VJF/run_configs/trotter_extinction/090424/model.toml' \
      --mcmc '$REMOTE_VJF/run_configs/trotter_extinction/mcmc_weekend_5temp_1000x5000.toml' \
      --results '$REMOTE_VJF/jetfit/results/$RESULT_TAG' \
      --initial-positions '$REMOTE_VJF/run_configs/trotter_extinction/090424/initial_positions_from_short.npz' \
      --workers 8 --start-method spawn --skip-plots \
      > '$REMOTE_VJF/logs/090424.trotter_weekend.log' 2>&1\"
"

echo "Started $RESULT_TAG on $HOST in tmux session $SESSION."
