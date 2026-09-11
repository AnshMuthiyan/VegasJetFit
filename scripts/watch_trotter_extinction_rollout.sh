#!/usr/bin/env bash
set -u

VJF="${VJF:-$(cd "$(dirname "$0")/.." && pwd)}"
REMOTE_VJF="/Users/jkeohane/GRBs/VegasJetFit"
STAGE="/Users/jkeohane/GRBs/VegasJetFit_trotter_test_20260910"
LOG_DIR="$VJF/logs/trotter_extinction_rollout"
POLL_SECONDS="${POLL_SECONDS:-300}"
mkdir -p "$LOG_DIR"

SSH=(ssh -n -x -o ForwardX11=no -o BatchMode=yes -o ConnectTimeout=8)
DEPLOY_FILES=(
  jetfit/mcmc/mcmc.py
  jetfit/mcmc/trotter_extinction.py
  jetfit/run.py
  scripts/plot/diagnose.py
  scripts/plot/visualize.py
  scripts/prepare_trotter_extinction_continuation.py
  test/mcmc/test_trotter_extinction.py
  test/test_run_metadata.py
  test/test_plot_extinction.py
  run_configs/trotter_extinction
  reports/2026_09_10_trotter_extinction_review
)

stamp() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log() { printf '%s %s\n' "$(stamp)" "$*" | tee -a "$LOG_DIR/watcher.log"; }

reachable() {
  "${SSH[@]}" "$1" true >/dev/null 2>&1
}

busy() {
  "${SSH[@]}" "$1" "pgrep -f 'python.*(jetfit.run|minimize.py)' >/dev/null" 2>/dev/null
}

deploy() {
  local host="$1"
  log "deploying reviewed Trotter code to $host"
  (cd "$VJF" && tar -cf - "${DEPLOY_FILES[@]}") |
    "${SSH[@]}" "$host" "tar -xf - -C '$REMOTE_VJF'" || return 1
  "${SSH[@]}" "$host" \
    "cd '$REMOTE_VJF' && PYTHONPATH=. /Users/jkeohane/GRBs/.venv/bin/python -m compileall -q jetfit scripts test && PYTHONPATH=. /Users/jkeohane/GRBs/.venv/bin/python -m unittest discover -s test/mcmc -p 'test_trotter_extinction.py' && PYTHONPATH=. /Users/jkeohane/GRBs/.venv/bin/python -m unittest discover -s test -p 'test_run_metadata.py'" \
    >>"$LOG_DIR/${host}_deploy_test.log" 2>&1 || return 1
  touch "$LOG_DIR/${host}.deployed"
  log "deployment verified on $host"
}

pull_090424_short() {
  local remote="$STAGE/jetfit/results/090424_trotter_extinction_short_5temp_25x100"
  local local_dir="$VJF/jetfit/results/090424_trotter_extinction_short_5temp_25x100"
  if [[ -f "$LOG_DIR/090424_short.pulled" ]]; then return 0; fi
  if "${SSH[@]}" pauley404-01 "test -s '$remote/chain.npz' -a -s '$remote/best_fit.json'" 2>/dev/null; then
    mkdir -p "$local_dir"
    rsync -a "pauley404-01:$remote/" "$local_dir/" >>"$LOG_DIR/090424_pull.log" 2>&1 || return 1
    touch "$LOG_DIR/090424_short.pulled"
    log "pulled completed 090424 short diagnostic from pauley404-01"
  fi
}

prepare_080319b() {
  local tag="080319B_core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_alluvoir_n17upper25_5temp_1000x5000_v1"
  local remote="$REMOTE_VJF/jetfit/results/$tag"
  local local_dir="$VJF/jetfit/results/$tag"
  local output="$VJF/run_configs/trotter_extinction/080319B"
  if [[ -f "$LOG_DIR/080319B.prepared" ]]; then return 0; fi
  if ! "${SSH[@]}" pauley404-02 "test -s '$remote/chain.npz' -a -s '$remote/best_fit.json' && ! pgrep -f '[j]etfit.run.*$tag' >/dev/null" 2>/dev/null; then
    return 0
  fi
  mkdir -p "$local_dir"
  for name in chain.npz best_fit.json model.toml obs.csv mcmc_settings.toml; do
    rsync -a "pauley404-02:$remote/$name" "$local_dir/$name" >>"$LOG_DIR/080319B_pull.log" 2>&1 || return 1
  done
  (cd "$VJF" && PYTHONPATH=. /Users/jkeohane/GRBs/.venv/bin/python \
    scripts/prepare_trotter_extinction_continuation.py \
    --source-results "$local_dir" --output-dir "$output" --ntemps 5 --seed 80319) \
    >>"$LOG_DIR/080319B_prepare.log" 2>&1 || return 1
  touch "$LOG_DIR/080319B.prepared"
  log "prepared 080319B Trotter continuation from completed upper-25 cloud"
}

launch_080319b() {
  if [[ ! -f "$LOG_DIR/080319B.prepared" || -f "$LOG_DIR/080319B.launched" ]]; then return 0; fi
  local host
  for host in pauley404-03 pauley404-01; do
    if reachable "$host" && ! busy "$host"; then
      [[ -f "$LOG_DIR/${host}.deployed" ]] || deploy "$host" || continue
      (cd "$VJF" && tar -cf - run_configs/trotter_extinction/080319B) |
        "${SSH[@]}" "$host" "tar -xf - -C '$REMOTE_VJF'" || continue
      local result="$REMOTE_VJF/jetfit/results/080319B_trotter_extinction_short_5temp_25x100"
      "${SSH[@]}" "$host" \
        "tmux new-session -d -s trotter_080319B_short 'cd $REMOTE_VJF && exec env PYTHONPATH=. MPLBACKEND=Agg /usr/bin/time -p /Users/jkeohane/GRBs/.venv/bin/python -u -m jetfit.run --event 080319B --obs $REMOTE_VJF/run_configs/trotter_extinction/080319B/obs.csv --model $REMOTE_VJF/run_configs/trotter_extinction/080319B/model.toml --mcmc $REMOTE_VJF/run_configs/trotter_extinction/mcmc_short_5temp_25x100.toml --results $result --initial-positions $REMOTE_VJF/run_configs/trotter_extinction/080319B/initial_positions.npz --workers 8 --start-method spawn --skip-plots >$REMOTE_VJF/logs/080319B.trotter_short.log 2>&1'" || continue
      printf '%s\n' "$host" >"$LOG_DIR/080319B.host"
      touch "$LOG_DIR/080319B.launched"
      log "launched 080319B Trotter short diagnostic on $host"
      return 0
    fi
  done
}

log "Trotter rollout watcher started; PCRC intentionally excluded"
while true; do
  pull_090424_short || log "warning: 090424 pull attempt failed"

  if [[ ! -f "$LOG_DIR/pauley404-03.deployed" ]] && reachable pauley404-03 && ! busy pauley404-03; then
    deploy pauley404-03 || log "warning: pauley404-03 deployment failed"
  fi

  prepare_080319b || log "warning: 080319B preparation failed"
  if [[ -f "$LOG_DIR/080319B.prepared" && ! -f "$LOG_DIR/pauley404-02.deployed" ]] && reachable pauley404-02 && ! busy pauley404-02; then
    deploy pauley404-02 || log "warning: pauley404-02 deployment failed"
  fi
  launch_080319b || log "warning: 080319B launch attempt failed"

  sleep "$POLL_SECONDS"
done
