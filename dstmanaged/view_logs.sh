#! /bin/bash

# Open the log files of the DST cluster in cwd, in tmux with `less`
# Intended to work with dstserv_simple.sh, where there is no direct PTY access to the server itself

# NOTE: these must have no spaces in them
SESSION='DST-servers'
DST_SERVER_NAME='testworld'

tmux new-session -d -s $SESSION

tmux new-window -t $SESSION:1 -n 'DST'
tmux send-keys -t $SESSION:1 'cd ~/Games/DontStarveTogether/' Enter "./start.sh $DST_SERVER_NAME"

tmux new-window -t $SESSION:2 -n 'DST logs'
tmux split-window -h -t $SESSION:2
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

tmux select-pane -t 0
tmux send-keys -t $SESSION:2 "cd ~/Games/DontStarveTogether/$DST_SERVER_NAME" Enter "tail -f Master/server_log.txt" Enter
tmux select-pane -t 2
tmux send-keys -t $SESSION:2 "cd ~/Games/DontStarveTogether/$DST_SERVER_NAME" Enter "tail -f Caves/server_log.txt" Enter
tmux select-pane -t 1
tmux send-keys -t $SESSION:2 "cd ~/Games/DontStarveTogether/$DST_SERVER_NAME" Enter "tail -f Island/server_log.txt" Enter
tmux select-pane -t 3
tmux send-keys -t $SESSION:2 "cd ~/Games/DontStarveTogether/$DST_SERVER_NAME" Enter "tail -f Volcano/server_log.txt" Enter
