#!/bin/bash

set -ex

raw_path=$(<venvPath)
eval "path=$raw_path"
source $path/TenaciousTrackerEnv/bin/activate
echo "$VIRTUAL_ENV"

python3 -m pip install -r requirements.txt