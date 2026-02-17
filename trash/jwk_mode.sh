#!/bin/bash

# ==== RUN VEGASPY ====
NUM_CPUS=$(nproc)
export ROOT=/Users/jkeohane/GRBs
echo "Root directory is $ROOT"
export PYTHONPATH=$ROOT/VegasJetFit/
source $ROOT/.venv/bin/activate

JETFIT_PATH=$ROOT/VegasJetFit/jetfit/run.py
LOG_DIR=$ROOT/VegasJetFit/logs

event1=$(basename "221009A")
#event2=$(basename "171010A")
#event3=$(basename "140506A")
#event4=$(basename "130612A")
#event5=$(basename "080413B")

log_file1="$LOG_DIR/$event1.log"
#log_file2="$LOG_DIR/$event2.log"
#log_file3="$LOG_DIR/$event3.log"
#log_file4="$LOG_DIR/$event4.log"
#log_file5="$LOG_DIR/$event5.log"

taskset -c 0-4 nohup python $JETFIT_PATH --event "$event1" --obs "$ROOT/VegasJetFit/jetfit/resources/grbs/221009A/221009Aclean.csv" --results "$ROOT/VegasJetFit/jetfit/results/221009A" > "$log_file1" 2>&1 &
#taskset -c 0 nohup python $JETFIT_PATH --event "$event1" --results "$ROOT/VegasDev/VegasJetFit/jetfit/results/2210test" > "$log_file1" 2>&1 &
#taskset -c 16-23 nohup python $JETFIT_PATH --event "$event3" > "$log_file3" 2>&1 &
#taskset -c 24-31 nohup python $JETFIT_PATH --event "$event4" > "$log_file4" 2>&1 &
#taskset -c 3-32 nohup python $JETFIT_PATH --event "$event5" > "$log_file5" 2>&1 &

echo "Started modeling events $event1 on all CPUs"
