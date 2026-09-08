#!/usr/bin/env bash
set -euo pipefail

VEGAS="/Users/jkeohane/GRBs/VegasJetFit"
PY="/Users/jkeohane/GRBs/.venv/bin/python"
EVENT="140506A"
RUN_TAG="anshstyle_structjet_thetavthawed_v1"
RESULTS="$VEGAS/jetfit/results/${EVENT}_${RUN_TAG}"
LOG="$VEGAS/logs/${EVENT}.${RUN_TAG}.log"
OBS="$VEGAS/jetfit/resources/grbs/$EVENT/$EVENT.csv"
MODEL="$VEGAS/structured_jet_anshstyle_thetavthawed_configs_active/$EVENT.toml"
MCMC="$VEGAS/Ansh_Run/mcmc_settings_dylanspec_2000x2000.toml"

export PYTHONPATH="$VEGAS${PYTHONPATH:+:$PYTHONPATH}"
export MPLBACKEND="Agg"

cd "$VEGAS"
mkdir -p "$RESULTS" "$VEGAS/logs"
cp -f "$MODEL" "$RESULTS/model.toml"
cp -f "$OBS" "$RESULTS/obs.csv"
cp -f "$MCMC" "$RESULTS/mcmc_settings.toml"

date -u +"[lyra-140506A] start_utc=%Y-%m-%dT%H:%M:%SZ" >> "$LOG"
/usr/bin/time -p "$PY" -u -m jetfit.run \
  --event "$EVENT" \
  --obs "$OBS" \
  --model "$MODEL" \
  --results "$RESULTS" \
  --mcmc "$MCMC" \
  --workers 8 \
  --start-method spawn >> "$LOG" 2>&1

date -u +"[lyra-140506A] mcmc_done_utc=%Y-%m-%dT%H:%M:%SZ" >> "$LOG"
"$PY" "$VEGAS/scripts/minimize.py" \
  --results "$RESULTS" \
  --obs "$OBS" \
  --params "$RESULTS/model.toml" \
  --mode walkers \
  --minimizer minimize \
  --scipy-method Powell \
  --fallback-scipy-method Nelder-Mead >> "$LOG" 2>&1

date -u +"[lyra-140506A] minimize_done_utc=%Y-%m-%dT%H:%M:%SZ" >> "$LOG"
if [ -x "$VEGAS/scripts/sync_results_to_drive.sh" ] && [ -d "/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns" ]; then
  "$VEGAS/scripts/sync_results_to_drive.sh" \
    --results-dir "$RESULTS" \
    --event "$EVENT" \
    --drive-root "/Users/jkeohane/My Drive (jwkeohane@gmail.com)/VegasGRBruns" \
    --owner-subdir jkeohane \
    --run-label "${EVENT}_${RUN_TAG}" \
    --log-file "$LOG" \
    --mcmc-file "$MCMC" \
    --model-file "$MODEL" \
    --obs-file "$OBS" >> "$LOG" 2>&1 || true
fi

date -u +"[lyra-140506A] done_utc=%Y-%m-%dT%H:%M:%SZ" >> "$LOG"
