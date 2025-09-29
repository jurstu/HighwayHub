#!/bin/bash
cd /home/jur/projects/HighwayHub/code

tmux kill-session -t 'HighwayHub'

sleep 1

tmux new-session -d -s 'HighwayHub' "bash -c 'source ~/HighwayHubEnv/bin/activate && python3 -m HighwayHub'"
