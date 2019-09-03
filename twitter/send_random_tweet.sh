#!/usr/bin/env bash

# simple script to run cronjob for tweets on local computer

# path to python env local || server
source /Users/hendorf/anaconda3/bin/activate PyConDE-www || source /home/hendorf/anaconda3/bin/activate pyconwww

cd ..
project_path=$(pwd)
cd - || exit

export PYTHONPATH="$project_path"
python random_tweets.py