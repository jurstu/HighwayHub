#!/bin/bash

set -ex

raw_path=$(<venvPath)
eval "path=$raw_path"
source $path/TenaciousTrackerEnv/bin/activate
echo "$VIRTUAL_ENV"

sudo apt install -y libcairo2-dev libxt-dev libgirepository1.0-dev

python3 -m pip install -r requirements.txt



