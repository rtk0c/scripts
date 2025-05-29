#!/bin/bash

: "${HOST:=https://vpn.sjsu.edu/}"
echo "server: $HOST"

: "${AUTHGROUP:=Student-SSO}"
echo "authgroup: $AUTHGROUP"

USER_ID=$1
if [[ -z $USER_ID ]]; then
	echo "Usage: sjsu_auth+connect.sh <student ID>"
	exit 1
fi

die() { echo "$*" 1>&2 ; exit 1; }

if [[ ! -e /tmp/openconnect_creds ]]; then
	openconnect-sso \
		--server "$HOST" \
		--authgroup "$AUTHGROUP" \
		--user "$USER_ID" \
		--authenticate \
		> /tmp/openconnect_creds || die 'openconnect-sso died'
fi

source /tmp/openconnect_creds
export FINGERPRINT=$FINGERPRINT
export COOKIE=$COOKIE

./sjsu_connect &
disown

rm /tmp/openconnect_creds
