#!/bin/bash

# https://stackoverflow.com/a/28085062
: "${HOST:=https://vpn.sjsu.edu/}"
echo "server: $HOST"

: "${VPN_ROUTE:=10.0.0.0/8}"

if [[ $FINGERPRINT = '' ]]; then
	echo 'set $FINGERPRINT to avoid this interactive prompt'
	echo 'note: you may past the whole line from `openconnect-sso --authenticate`, like FINGER=xxxxyyyyzzzz'
	read -p 'enter server fingerprint: ' FINGERPRINT
	FINGERPRINT=${FINGERPRINT#'FINGERPRINT='}
else
	echo "fingerprint: $FINGERPRINT"
fi

if [[ $COOKIE = '' ]]; then
	echo 'set $COOKIE to avoid this interactive prompt'
	read -p 'enter cookie: ' COOKIE
	COOKIE=${COOKIE#'COOKIE='}
else
	echo "cookie: $COOKIE"
fi

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
