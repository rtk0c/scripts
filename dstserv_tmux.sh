#! /bin/bash

K_DST_INSTALL_DIR="${DST_DEDICATED_SERVER:-$HOME/.steam/steam/steamapps/common/Don\'t Starve Together Dedicated Server/}"

CLUSTER_NAME=$1
shift

# Options' default values
OPT_ARCH=64
OPT_UPDATE_MODS=true

while [[ $# -gt 0 ]]; do
	case $1 in
		-A|--arch)
			echo " -- [Opt] --arch=$2 "
			OPT_ARCH="$2"
			shift; shift
			;;
		-u|--update-mods)
			echo "-- [Opt] --update-mods=$2 "
			OPT_UPDATE_MODS="$2"
			shift; shift
			;;
		--lan)
			echo '-- [Opt] --lan'
			SERVER_OTHER_OPTIONS+=' -lan'
			OPT_LAN=true
			shift
			;;
		-*|--*)
			echo "Unknown option $i, qutting"
			exit 1
			;;
	esac
done

case $OPT_ARCH in
	32)
		SERVER_BIN_DIR="$K_DST_INSTALL_DIR/bin"
		SERVER_BIN_NAME=dontstarve_dedicated_server_nullrenderer
		echo "-- Using 32bit server at $SERVER_BIN_DIR/$SERVER_BIN_NAME"
		;;
	64)
		SERVER_BIN_DIR="$K_DST_INSTALL_DIR/bin64"
		SERVER_BIN_NAME=dontstarve_dedicated_server_nullrenderer_x64
		echo "-- Using 64bit server at $SERVER_BIN_DIR/$SERVER_BIN_NAME"
		;;
	*)
		echo '-- Unknown server architecture, qutting'
		exit 1
esac

DATA_DIR=$PWD
DATA_DIR_PREFIX=$(dirname "$DATA_DIR")
DATA_DIR_LAST=$(basename "$DATA_DIR")

if $OPT_UPDATE_MODS; then
	echo '-- Running the Master shard to update mods'
	cd "$SERVER_BIN_DIR"
	"./$SERVER_BIN_NAME" \
		-persistent_storage_root "$DATA_DIR_PREFIX" -conf_dir "$DATA_DIR_LAST" \
		-ugc_directory ../ugc_mods \
		-cluster "$CLUSTER_NAME" -shard Master \
		-only_update_server_mods \
		$SERVER_OTHER_OPTIONS > /dev/null 2>&1 &
	wait
	cd -
else
	echo '-- Skipping updating mods'
fi

echo "-- Data directory: $DATA_DIR"
echo "-- Starting cluster $CLUSTER_NAME"

try_run_instance() {
	SHARD_NAME="$1"
	if [[ $2 == *'+NoEcho'* ]]; then
		DO_ECHO=false
	else
		DO_ECHO=true
	fi

	if [[ -d "$CLUSTER_NAME/$SHARD_NAME" ]]; then
		$DO_ECHO && echo "-- * With shard $SHARD_NAME"

		# DST expects cwd to be its direct parent directory (so if we had used the 32 bit version, .../bin)
		# seems like because it tries to locate the data dir by relative paths
		tmux send-keys "cd '$SERVER_BIN_DIR'" Enter

		# Note that `-ugc_directory` is relative to the bin/ directory
		tmux send-keys "'./$SERVER_BIN_NAME' \\
-persistent_storage_root '$DATA_DIR_PREFIX' -conf_dir '$DATA_DIR_LAST' -ugc_directory ../ugc_mods \\
-skip_update_server_mods -console \\
-cluster '$CLUSTER_NAME' -shard '$SHARD_NAME' $SERVER_OTHER_OPTIONS" Enter
	else
		$DO_ECHO && echo "-- * Shard $SHARD_NAME not found, killing pane"
		tmux send-keys "C-c" "exit" Enter
	fi
}

SESSION="DST-$RANDOM"
# TODO is there a way to make this specific tmux session to use default-shell=/bin/sh
tmux new-session -d -s "$SESSION" 'exec /bin/sh'
tmux split-window -h -t "$SESSION:0" 'exec /bin/sh'
tmux split-window -v -t "$SESSION:0.1" 'exec /bin/sh'
tmux split-window -v -t "$SESSION:0.0" 'exec /bin/sh'

tmux select-pane -t "$SESSION:0.0"
# The Forest shard is always called Master by convention, even if it's not the actual master shard (e.g. in a IA shipwrecked master configuration)
try_run_instance Master
tmux select-pane -t "$SESSION:0.2"
try_run_instance Caves
tmux select-pane -t "$SESSION:0.1"
try_run_instance Island #for IA
tmux select-pane -t "$SESSION:0.3"
try_run_instance Volcano #for IA
