#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$HOME/GRBs}"
WATCHER="${WATCHER:-$ROOT/lab_watch_tophat_dylanspec_mcmc_queue.sh}"
VEGAS_DIR="${VEGAS_DIR:-$ROOT/VegasJetFit}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
BUILDER="${BUILDER:-$VEGAS_DIR/scripts/build_structured_jet_configs.py}"

CONFIG_SOURCE_DIR="${CONFIG_SOURCE_DIR:-$VEGAS_DIR/structured_jet_configs_v1}"
CONFIG_DIR="${CONFIG_DIR:-$VEGAS_DIR/structured_jet_configs_active}"

SESSION_NAME="${SESSION_NAME:-lab_structured_jet_2000_watch}"
LOG_DIR="${LOG_DIR:-$ROOT/tmp/lab_fit_sync/logs}"
WATCH_LOG="${WATCH_LOG:-$LOG_DIR/${SESSION_NAME}_$(date -u +%Y%m%dT%H%M%SZ).log}"
PL_AUDIT_CSV="${PL_AUDIT_CSV:-$LOG_DIR/${SESSION_NAME}_pl_audit_$(date -u +%Y%m%dT%H%M%SZ).csv}"
SBPL_AUDIT_CSV="${SBPL_AUDIT_CSV:-$LOG_DIR/${SESSION_NAME}_sbpl_audit_$(date -u +%Y%m%dT%H%M%SZ).csv}"

RUN_TAG="${RUN_TAG:-powerlawjet_thetacfree_seeded_2000x2000_v1}"
if [ "${RESULTS_NAME_TEMPLATE+x}" != "x" ] || [ -z "${RESULTS_NAME_TEMPLATE:-}" ]; then
  RESULTS_NAME_TEMPLATE='{event}_{run_tag}'
fi
MCMC_SETTINGS="${MCMC_SETTINGS:-$VEGAS_DIR/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml}"
RUN_FAMILY="${RUN_FAMILY:-all}"

PL_SOURCE_RUN_TAG="${PL_SOURCE_RUN_TAG:-thetacfree_dylanphyspriors_init5pct_2000x2000_v1}"
SBPL_SOURCE_RUN_TAG="${SBPL_SOURCE_RUN_TAG:-thetacfree_dylan_sbpl_init5pct_2000x2000_v1}"

PL_MODEL_NAME="${PL_MODEL_NAME:-PowerlawJetVegasDylanSpectrumModel}"
SBPL_MODEL_NAME="${SBPL_MODEL_NAME:-PowerlawJetVegasAfterglowModel}"
FIXED_K_E="${FIXED_K_E:-2.0}"
FIXED_K_G="${FIXED_K_G:-2.0}"
FIXED_S="${FIXED_S:-4.0}"

INTERVAL_MIN="${INTERVAL_MIN:-15}"
DURATION_HOURS="${DURATION_HOURS:-336}"
WORKERS="${WORKERS:-8}"
KEEP_AWAKE="${KEEP_AWAKE:-1}"
NOOP_STATUS="${NOOP_STATUS:-$ROOT/tmp/noop_status.py}"
SYNC_CODE_TO_HOSTS="${SYNC_CODE_TO_HOSTS:-1}"
HOSTS="${HOSTS:-pauley404-01 pauley404-02 pauley404-03}"

LYRA_EVENTS="${LYRA_EVENTS-221009A 140506A 090618 080413B}"
PAULEY404_01_EVENTS="${PAULEY404_01_EVENTS-220101A 131030A 090424 080319B}"
PAULEY404_02_EVENTS="${PAULEY404_02_EVENTS-210905A 130612A 050922C 050525A}"
PAULEY404_03_EVENTS="${PAULEY404_03_EVENTS-171010A 160131A 111228A}"
STATUS_EVENTS="${STATUS_EVENTS-221009A 220101A 210905A 171010A 160131A 140506A 131030A 130612A 111228A 090618 090424 050922C 050525A 080413B 080319B}"

PL_EVENTS=(
  221009A 220101A 210905A 171010A 160131A 140506A 131030A
  130612A 111228A 090618 090424 050922C 050525A
)
SBPL_EVENTS=(080413B 080319B)

mkdir -p "$LOG_DIR" "$CONFIG_SOURCE_DIR" "$CONFIG_DIR" "$(dirname "$NOOP_STATUS")"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: python executable not found: $PYTHON_BIN" >&2
  exit 2
fi
if [ ! -f "$BUILDER" ]; then
  echo "ERROR: builder not found: $BUILDER" >&2
  exit 2
fi
if [ ! -x "$WATCHER" ]; then
  echo "ERROR: watcher not executable: $WATCHER" >&2
  exit 2
fi
if [ ! -f "$MCMC_SETTINGS" ]; then
  echo "ERROR: MCMC settings file not found: $MCMC_SETTINGS" >&2
  exit 2
fi

cat >"$NOOP_STATUS" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
chmod +x "$NOOP_STATUS"

sync_hosts() {
  local host
  for host in $HOSTS; do
    rsync -az --delete --human-readable \
      -e "ssh -o BatchMode=yes -o ConnectTimeout=8" \
      --exclude '.git' \
      --exclude '.venv' \
      --exclude '__pycache__' \
      --exclude 'logs' \
      --exclude 'tmp' \
      --exclude 'jetfit/results' \
      "$VEGAS_DIR/" "$host:$VEGAS_DIR/"
    rsync -az --human-readable \
      -e "ssh -o BatchMode=yes -o ConnectTimeout=8" \
      "$ROOT/lab_watch_tophat_dylanspec_mcmc_queue.sh" \
      "$host:$ROOT/"
  done
}

verify_config_set() {
  "$PYTHON_BIN" - <<'PY' "$CONFIG_DIR" "$STATUS_EVENTS"
from pathlib import Path
import sys

config_dir = Path(sys.argv[1])
events = sys.argv[2].split()
missing = [event for event in events if not (config_dir / f"{event}.toml").exists()]
if missing:
    raise SystemExit(f"missing configs: {', '.join(missing)}")
PY
}

family_enabled() {
  case "$RUN_FAMILY" in
    all) return 0 ;;
    pl)
      [ "$1" = "pl" ]
      ;;
    sbpl)
      [ "$1" = "sbpl" ]
      ;;
    *)
      echo "ERROR: unsupported RUN_FAMILY=$RUN_FAMILY" >&2
      return 2
      ;;
  esac
}

echo "=================================================="
echo "Preparing structured-jet queue"
echo "Run family:       $RUN_FAMILY"
echo "Run tag:          $RUN_TAG"
echo "Config source:    $CONFIG_SOURCE_DIR"
echo "Config active:    $CONFIG_DIR"
echo "PL source tag:    $PL_SOURCE_RUN_TAG"
echo "SBPL source tag:  $SBPL_SOURCE_RUN_TAG"
echo "Fixed jet values: k_e=$FIXED_K_E k_g=$FIXED_K_G s=$FIXED_S"
echo "Events:           $STATUS_EVENTS"
echo "=================================================="

if family_enabled pl; then
  "$PYTHON_BIN" "$BUILDER" \
    --vegas-dir "$VEGAS_DIR" \
    --source-config-dir "$VEGAS_DIR/thesis_reproduction_configs_thetacfree_dylanphyspriors_init5pct_active" \
    --output-dir "$CONFIG_SOURCE_DIR" \
    --source-run-tag "$PL_SOURCE_RUN_TAG" \
    --results-name-template "{event}_thesis_reproduction_{run_tag}" \
    --results-root "$VEGAS_DIR/jetfit/results" \
    --events "${PL_EVENTS[@]}" \
    --audit-csv "$PL_AUDIT_CSV" \
    --model-name "$PL_MODEL_NAME" \
    --fixed-k-e "$FIXED_K_E" \
    --fixed-k-g "$FIXED_K_G" \
    --fixed-s "$FIXED_S"
fi

if family_enabled sbpl; then
  "$PYTHON_BIN" "$BUILDER" \
    --vegas-dir "$VEGAS_DIR" \
    --source-config-dir "$VEGAS_DIR/dylan_sbpl_configs_thetacfree_init5pct_active" \
    --output-dir "$CONFIG_SOURCE_DIR" \
    --source-run-tag "$SBPL_SOURCE_RUN_TAG" \
    --results-name-template "{event}_{run_tag}" \
    --results-root "$VEGAS_DIR/jetfit/results" \
    --events "${SBPL_EVENTS[@]}" \
    --audit-csv "$SBPL_AUDIT_CSV" \
    --model-name "$SBPL_MODEL_NAME" \
    --fixed-k-e "$FIXED_K_E" \
    --fixed-k-g "$FIXED_K_G" \
    --fixed-s "$FIXED_S"
fi

rsync -a --delete "$CONFIG_SOURCE_DIR"/ "$CONFIG_DIR"/
verify_config_set

if [ "$SYNC_CODE_TO_HOSTS" = "1" ]; then
  sync_hosts
fi

tmux has-session -t "$SESSION_NAME" >/dev/null 2>&1 && tmux kill-session -t "$SESSION_NAME"

tmux new-session -d -s "$SESSION_NAME" \
  "cd '$ROOT' && /usr/bin/caffeinate -is env ROOT='$ROOT' VEGAS_DIR='$VEGAS_DIR' STATUS_SCRIPT='$NOOP_STATUS' EVENT_RUNNER='$VEGAS_DIR/jwk_run_thesis_reproduction_event.sh' CONFIG_DIR='$CONFIG_DIR' RUN_TAG='$RUN_TAG' SOURCE_RESULTS_TAG='' RESULTS_NAME_TEMPLATE='$RESULTS_NAME_TEMPLATE' SOURCE_NAME_TEMPLATE='' MCMC_SETTINGS='$MCMC_SETTINGS' INTERVAL_MIN='$INTERVAL_MIN' DURATION_HOURS='$DURATION_HOURS' WORKERS='$WORKERS' KEEP_AWAKE='$KEEP_AWAKE' SYNC_SOURCE_INPUTS='0' LYRA_EVENTS='$LYRA_EVENTS' PAULEY404_01_EVENTS='$PAULEY404_01_EVENTS' PAULEY404_02_EVENTS='$PAULEY404_02_EVENTS' PAULEY404_03_EVENTS='$PAULEY404_03_EVENTS' STATUS_EVENTS='$STATUS_EVENTS' bash '$WATCHER' > '$WATCH_LOG' 2>&1"

echo "$SESSION_NAME"
echo "$WATCH_LOG"
