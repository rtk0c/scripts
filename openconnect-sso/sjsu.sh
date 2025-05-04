#!/bin/bash

HOST=https://vpn.sjsu.edu/
FINGERPRINT=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

if [[ $COOKIE = '' ]]; then
	read -p "Enter AnyConnect cookie: " COOKIE
fi

# https://stackoverflow.com/a/1885534
read -p "Replacing the default everything route with 10.0.0.0/8 only route? (y/N)" REPLY
echo #Move to next line
if [[ $REPLY =~ ^[Yy]$ ]]; then
	ROUTE_LAN_ONLY=true
fi

echo 'Running sudo once just to get password cached'
sudo echo '-- meaningless echo --'

# The gateway advertises 10.0.0.0/8 AND a default route, which we don't care about
echo $COOKIE | sudo openconnect $HOST --cookie-on-stdin --script 'vpn-slice 10.0.0.0/8' --servercert $FINGERPRINT &

# OpenConnect is running as background, it takes a bit to connect and setup its routes.
# Jank, I know. This is what "cloud" and all the docker clusters do apparently.
sleep 5s

# TODO replace this with a proper vpnc-script to setup the correct routes in the first go
if [[ $ROUTE_LAN_ONLY = true ]]; then
	sudo ip route del default dev tun0 && sudo ip route add 10.0.0.0/8 dev tun0
fi

onexit() {
	kill $(jobs -p)
	if [[ $ROUTE_LAN_ONLY = true ]]; then
		sudo ip route del 10.0.0.0/8 dev tun0
	fi
}

trap 'onexit' EXIT
wait
