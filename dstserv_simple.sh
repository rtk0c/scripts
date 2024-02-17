#! /bin/bash

K_DST_INSTALL_DIR="${DST_DEDICATED_SERVER:-$HOME/.steam/steam/steamapps/common/Don\'t Starve Together Dedicated Server/}"

CLUSTER_NAME=$1
shift

# Options' default values
OPT_ARCH=64
OPT_UPDATE_MODS=true
OPT_BACKUP=true
OPT_BACKUP_MAX_COUNT=-1

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
		-B|--backup)
			echo "-- [Opt] --backup=$2"
			OPT_BACKUP="$2"
			shift; shift
			;;
		--backup-max-count)
			echo "-- [Opt] --backup-max-count=$2"
			OPT_BACKUP_MAX_COUNT=$2
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

try_run_instance() {
	SHARD_NAME="$1"
	if [[ $2 == *'+UpdateMods'* ]]; then
		SERVER_OTHER_OPTIONS+=' -only_update_server_mods'
	else
		SERVER_OTHER_OPTIONS+=' -skip_update_server_mods'
	fi
	if [[ $2 == *'+NoEcho'* ]]; then
		DO_ECHO=false
	else
		DO_ECHO=true
	fi

	if [[ -d "$CLUSTER_NAME/$SHARD_NAME" ]]; then
		$DO_ECHO && echo "-- * With shard $SHARD_NAME"

		# DST expects cwd to be its direct parent directory (so if we had used the 32 bit version, .../bin)
		# seems like because it tries to locate the data dir by relative paths
		cd "$SERVER_BIN_DIR"

		# Note that `-ugc_directory` is relative to the bin/ directory
		"./$SERVER_BIN_NAME" \
			-persistent_storage_root "$DATA_DIR_PREFIX" -conf_dir "$DATA_DIR_LAST" \
			-ugc_directory ../ugc_mods \
			-cluster "$CLUSTER_NAME" -shard "$SHARD_NAME" \
			$SERVER_OTHER_OPTIONS \
			> /dev/null 2>&1 &

		cd "$OLDPWD"
	else
		$DO_ECHO && echo "-- * Shard $SHARD_NAME not found, skipping"
	fi
}

backup() {
	if [[ -f "$CLUSTER_NAME/nobackup" ]]; then
		echo "-- [Backup] 'nobackup' present, skipping"
		return
	fi

	BACKUP_START_TIME=$(date -d 'today' +'%Y%m%d%H%M')
	BACKUP_SUFFIX=$BACKUP_START_TIME
	echo "-- [Backup] Using '$BACKUP_SUFFIX' as archive suffices"

	rm -rf /tmp/backup-tmp
	mkdir /tmp/backup-tmp

	DIRNAME=$(basename "$CLUSTER_NAME")
	echo "-- [Backup] Backing up $CLUSTER_NAME"

	# Make a temporary copy to /tmp, in case the files get modified by DST server during backup
	# tbh I don't know if 7z handles this gracefully (it probably does, by scanning all files at the beginning and keeping a fd to them) but we should do it just in case

	# https://unix.stackexchange.com/a/412262
	# Use the -R flag and /. to copy dir and rename at the same time
	cp -R "$CLUSTER_NAME/." "/tmp/backup-tmp/$DIRNAME"
	# Use tar if we want a faster backup
	# tar cf ".snapshots/$DIRNAME $BACKUP_SUFFIX.tar" --directory="$d" .
	7z a -t7z ".snapshots/$DIRNAME $BACKUP_SUFFIX.7z" "$CLUSTER_NAME" > /dev/null 2>&1
	rm -r "/tmp/backup-tmp/$DIRNAME"

	rm -r /tmp/backup-tmp
}

backup_service() {
	while true; do
		sleep 8m
	
		# This might cause the archive files to have a slightly different timestamp than the log (e.g. if the script ran just before the minute sticks)
		# but honestly it's not that big of a deal
		echo "-- [Backup][$(date -d today +'%Y-%m-%d %H:%M')] Starting backup..."
		backup
		echo "-- [Backup][$(date -d today +'%Y-%m-%d %H:%M')] Finished"
	done
}

if $OPT_UPDATE_MODS; then
	echo '-- Running the Master shard to update mods'
	try_run_instance Master +UpdateMods,+NoEcho
	wait
else
	echo '-- Skipping updating mods'
fi

if $OPT_BACKUP; then
	echo "-- Starting backup service: every 5 minutes"
	# We trigger a backup the moment we start the server, as a convenience feature in case something gets screwed up, e.g. world starts regenerating or something
	echo "-- [Backup][$(date -d today +'%Y-%m-%d %H:%M')] Starting initial backup..."
	backup
	echo "-- [Backup][$(date -d today +'%Y-%m-%d %H:%M')] Finished"
	backup_service &
fi

echo "-- Data directory: $DATA_DIR"
echo "-- Starting cluster $CLUSTER_NAME"

# IA stands for Island Adventures
# The Forest shard is always called Master by convention, even if it's not the actual master shard (e.g. in a IA shipwrecked master configuration)
try_run_instance Master
try_run_instance Caves
try_run_instance Island #for IA
try_run_instance Volcano #for IA

trap 'kill $(jobs -p)' EXIT
wait
