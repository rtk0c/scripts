#!/bin/bash

# https://stackoverflow.com/a/28085062
: "${HOST:=https://vpn.sjsu.edu/}"
echo "server: $HOST"

: "${VPN_ROUTE:=10.0.0.0/8}"

interactive_prompt() {
	echo ''
	echo "set \$$1 to avoid this interactive prompt"
	echo "note: prefix '$1=' will be automatically stripped from input here"
	echo "note: this means you may paste the whole line from 'openconnect-sso --authenticate'"
	read -p "enter $1: " $1
}

if [[ $FINGERPRINT = '' ]]; then
	interactive_prompt FINGERPRINT
	FINGERPRINT=${FINGERPRINT#'FINGERPRINT='}
fi
echo "fingerprint: $FINGERPRINT"

if [[ $COOKIE = '' ]]; then
	interactive_prompt COOKIE
	COOKIE=${COOKIE#'COOKIE='}
fi
echo "cookie: $COOKIE"

if [[ $(type -P vpn-slice) ]]; then
	# vpn-slice exists, use that

	echo $COOKIE | sudo openconnect "$HOST" \
		--cookie-on-stdin --servercert $FINGERPRINT \
		-s "vpn-slice $VPN_ROUTE"
else
	# use manual hack

	echo $COOKIE | sudo openconnect "$HOST" \
		--cookie-on-stdin --servercert $FINGERPRINT \
		&

	# OpenConnect is running as background, it takes a bit to connect and setup its routes.
	# Jank, I know. This is what "cloud" and all the docker clusters do apparently.
	sleep 5s

	echo 'removing default route'
	sudo ip route del default dev tun0
	sudo ip route add 10.0.0.0/8 dev tun0
	# disable using VPN's DNS globally
	sudo resolvectl default-route tun0 false

	wait
fi
