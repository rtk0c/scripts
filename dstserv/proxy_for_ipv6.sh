#!/bin/bash

# proxy_for_ipv6.sh: Reverse proxy DST's listen ports on an IPv6 address, using socat.
#
# Listens for 4 consecutive ports starting from the given port. This works well if you have the shards bind to
# consecutive ports like 11001, 11002, [11003, 11004 if playing Island Adventures]. On normal vanilla servers,
# proxying extra ports shouldn't hurt.
#
# Example Usage:
#     proxy_for_ipv6.sh '[2001:0DB8::114:514]' 11001


IPv6=$1
START_PORT=$2

#cleanup() {
#	kill $(jobs -p) &>/dev/null
#}
#trap cleanup EXIT INT TERM

# https://stackoverflow.com/a/2173421
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

echo "socat for $START_PORT"
socat UDP:127.0.0.1:$START_PORT UDP6-LISTEN:$START_PORT,fork,reuseaddr,bind=$IPV6 &
((START_PORT++))
echo "socat for $START_PORT"
socat UDP:127.0.0.1:$START_PORT UDP6-LISTEN:$START_PORT,fork,reuseaddr,bind=$IPV6 &
((START_PORT++))
echo "socat for $START_PORT"
socat UDP:127.0.0.1:$START_PORT UDP6-LISTEN:$START_PORT,fork,reuseaddr,bind=$IPV6 &
((START_PORT++))
echo "socat for $START_PORT"
socat UDP:127.0.0.1:$START_PORT UDP6-LISTEN:$START_PORT,fork,reuseaddr,bind=$IPV6 &

wait
