#!/bin/bash

TARGET_DIR=data/tally/
NR_RUNS=1
NR_VOTERS="100,215,464,1000,2154,4641,10000,21544,46416,100000,215443"
DELEGATION_PERCENTS="0.8"

python -m voteagain tally -o $TARGET_DIR -r $NR_RUNS -n $NR_VOTERS

python -m voteagain tally-delegation -o $TARGET_DIR -r $NR_RUNS -n $NR_VOTERS -d $DELEGATION_PERCENTS