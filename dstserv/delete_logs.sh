#! /bin/bash

SERVER_DIR=$1

#remove_log() {
#	#rm -r $1
#	echo "$(readlink -f $1)"
#}

cd "$SERVER_DIR"
for d in */ ; do
	cd "$d"
	#remove_log server_log.txt
	#remove_log server_chat_log.txt
	#remove_log backup/
	rm server_log.txt
	rm server_chat_log.txt
	rm -r backup/
	cd ..
done
