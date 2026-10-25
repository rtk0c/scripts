#!/bin/bash

PROXY_MODE=$1
PUBLIC_IP=$2
START_PORT=$3

# https://stackoverflow.com/a/2173421
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# $current_port dynamic scoped, inherit from callsite

# job control '&' has to be inside functions, because otherwise calling `do_socat &` creates a subshell for that function.
# subshells bad for here

if [[ $PROXY_MODE = 'host' ]]; then
	do_socat() {
		socat "UDP4:127.0.0.1:$current_port" \
		      "UDP6-LISTEN:$current_port,fork,reuseaddr,bind=$PUBLIC_IP" &
	}
elif [[ $PROXY_MODE = 'client' ]]; then
	do_socat() {
		socat "UDP4-LISTEN:$current_port,fork,reuseaddr,bind=127.0.0.1" \
		      "UDP6:$PUBLIC_IP:$current_port" &
	}
else
	echo "Invalid mode '$PROXY_MODE'"
	exit 1
fi

current_port=$START_PORT
echo "socat for $current_port"
do_socat
((current_port++))
echo "socat for $current_port"
do_socat
((current_port++))
echo "socat for $current_port"
do_socat
((current_port++))
echo "socat for $current_port"
do_socat

wait
