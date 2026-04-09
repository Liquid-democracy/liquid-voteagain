#!/bin/bash

TARGET_DIR=data/distr/
NR_RUNS=1

# Using 50.000 ballots after padding
NR_VOTERS="4,20,50,100"
PERCENTS="300850.0,29155.0,9246.0,3839.0"
DELEGATION_PERCENTS="0.8,0.8,0.8,0.8"

python -m voteagain filter -o $TARGET_DIR -r $NR_RUNS -n $NR_VOTERS -p $PERCENTS -d $DELEGATION_PERCENTS
