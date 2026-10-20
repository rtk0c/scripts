#! /bin/bash

# Create a backup .7z file in cwd, of a DST cluster given by the 1st argument, omitting any logs
#   ./create_backup.sh ../some/path/MyCluster/
#   # creates ./MyCluster.7z

SERVER_NAME=$(basename "$1")
SERVER_DIR=$(realpath "$1")
BACKUP_TARGET=$(realpath "./$SERVER_NAME.7z")

TMPDIR=$(realpath "./tmp$RANDOM")
mkdir "$TMPDIR" || { echo "tmpdir $TMPDIR already exists, bailing"; exit 1; }

# make a copy of the cluster, delete logs, and then make backup
trap "rm -r '$TMPDIR'" EXIT
cp -r --reflink=auto "$SERVER_DIR" "$TMPDIR/$SERVER_NAME"

for d in "$TMPDIR/$SERVER_NAME"/*/ ; do
	rm -r "$d/backup" "$d/server_log.txt" "$d/server_chat_log.txt"
done

# cd to a tmpdir and then archive, so inside the archive the folder path looks correct, like:
#   ./MyCluster/<files>
# instead of
#   ./tmp12345/MyCluster/<files>
cd "$TMPDIR"
# -snl: preserve symlinks
# to accomodate my style of `ln ../adminlist.txt .` config files
7z a -snl "$BACKUP_TARGET" "./$SERVER_NAME"

echo "You'll want to extract the archive with '7z x -snld' to allow 'dangerous' symlinks like ../adminlist.txt"
