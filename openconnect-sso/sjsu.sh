#!/bin/bash

# https://stackoverflow.com/a/28085062
: "${HOST:=https://vpn.sjsu.edu/}"
echo "server: $HOST"

if [[ $FINGERPRINT = '' ]]; then
	read -p "enter server fingerprint: " FINGERPRINT
else
	echo "fingerprint: $FINGERPRINT"
fi

if [[ $COOKIE = '' ]]; then
	read -p "enter cookie: " COOKIE
else
	echo "cookie: $COOKIE"
fi

EXTRA_ARGS=()

# https://stackoverflow.com/a/1885534
read -p "Route 10.0.0.0/8 only, instead of accepting the AnyConnect gateway's advertised routes? (y/N)" REPLY
echo #Move to next line
if [[ $REPLY =~ ^[Yy]$ ]]; then
	EXTRA_ARGS+=('--script')
	EXTRA_ARGS+=('vpn-slice 10.0.0.0/8')
fi

# The gateway advertises 10.0.0.0/8 AND a default route, which we don't care about
echo $COOKIE | sudo openconnect "$HOST" --cookie-on-stdin --servercert "$FINGERPRINT" "${EXTRA_ARGS[@]}"
