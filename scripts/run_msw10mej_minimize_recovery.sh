#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="/Users/jkeohane/GRBs/VegasJetFit${PYTHONPATH:+:$PYTHONPATH}"
PY="/Users/jkeohane/GRBs/.venv/bin/python"

run_one() {
  local event="$1"
  local results_dir="$2"
  local obs_csv="$3"
  echo "[start] $(date -u +%Y-%m-%dT%H:%M:%SZ) ${event}"
  "$PY" /Users/jkeohane/GRBs/VegasJetFit/scripts/minimize.py \
    --results "$results_dir" \
    --obs "$obs_csv" \
    --params "$results_dir/model.toml" \
    --mode walkers \
    --parallel-workers 4 \
    --minimizer minimize \
    --scipy-method Powell \
    --fallback-scipy-method Nelder-Mead
  echo "[done]  $(date -u +%Y-%m-%dT%H:%M:%SZ) ${event}"
}

run_one "221009A_msw10mejcut_clean" \
  "/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/221009A_powerlaw_tophat_theta1p0_msw10mejcut_clean_offsetspatched_dylanspec_2000x2000_v1" \
  "/Users/jkeohane/GRBs/VegasJetFit/jetfit/resources/grbs/221009A/221009Aclean_msw10mej_cut.csv"

run_one "131030A_msw10mejcut" \
  "/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/131030A_powerlaw_tophat_theta1p0_msw10mejcut_offsetspatched_dylanspec_2000x2000_v1" \
  "/Users/jkeohane/GRBs/VegasJetFit/jetfit/resources/grbs/131030A/131030A_msw10mej_cut.csv"

run_one "140506A_msw10mejcut" \
  "/Users/jkeohane/GRBs/VegasJetFit/jetfit/results/140506A_powerlaw_tophat_theta1p0_msw10mejcut_offsetspatched_dylanspec_2000x2000_v1" \
  "/Users/jkeohane/GRBs/VegasJetFit/jetfit/resources/grbs/140506A/140506A_msw10mej_cut.csv"
