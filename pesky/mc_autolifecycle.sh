#! /bin/bash

tmux has-session -t Minecraft 2>/dev/null
if [[ $? != 0 ]]; then
	echo 'tmux session does not exist, bailing'
	echo 'create one named "Minecraft" and navigate the focused window to the directory containing a ./run.sh to use this script'
	exit 1
fi

mark_dir="$(dirname "$0")"
pause_mark_file="$mark_dir/autolifecycle-mark_paused"
stopped_mark_file="$mark_dir/autolifecycle-mark_server_stopped"

case $1 in
	pause)
		touch "$pause_mark_file"
		is_script_paused=true
		echo 'autolifecycle.sh will now drop all management commands.'
		if [[ ! -f "$stopped_mark_file" ]]; then
			tmux send-keys -t Minecraft 'say Server lifecycle script paused.' Enter
		fi
		;;
	resume)
		rm "$pause_mark_file"
		is_script_paused=false
		echo 'autolifecycle.sh will now accept management commands.'
		if [[ ! -f "$stopped_mark_file" ]]; then
			tmux send-keys -t Minecraft 'say Server lifecycle script resumed.' Enter
		fi
		;;
	shutdown)
		if [[ ! -f "$pause_mark_file" ]] && [[ ! -f "$stopped_mark_file" ]]; then
			tmux send-keys -t Minecraft 'stop' Enter
			sleep 10s
			# Press CTRL-C to make forge actually kill itself, rather than leaving a readline open
			tmux send-keys -t Minecraft C-c
			sleep 2s
			tmux send-keys -t Minecraft C-c

			# Mark server finally stopped
			# Only at this point is it fine to immediately do `./autolifecycle.sh reboot`
			touch "$stopped_mark_file"
		fi
		;;
	reboot)
		# In case the script is paused before scheduled shutdown, and resumed before the scheduled reboot, the reboot issued
		# by cron will be stopped by a check for [[ -f $stopped_mark_file ]]
		if [[ ! -f "$pause_mark_file" ]] && [[ -f "$stopped_mark_file" ]]; then
			# Press CTRL-C one more time, just in case forge decided to not kill itself, or somebody left stuff in the shell input buffer
			tmux send-keys -t Minecraft C-c './run.sh' Enter

			# TODO if somebody shutdowns immediately, the script will break
			rm "$stopped_mark_file"
		fi
		;;

	# For other non-lifecycle related notifications 
	sendcmd)
		if [[ ! -f "$pause_mark_file" ]] && [[ ! -f "$stopped_mark_file" ]]; then
			tmux send-keys -t Minecraft "${@:2}" Enter
		fi
		;;
esac
