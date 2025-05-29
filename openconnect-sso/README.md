# OpenConnect scripts

These scripts are configured to work with SJSU's Cisco AnyConnect server by default. This means server URLs, authgroups, routed IP prefixes, etc. You may need to tweak them if you want to use them for your own organization.

## Why not just `openconnect`?

SJSU's VPN requires authenticating through their SSO on Okta, which requires 2FA through Duo. Regular `openconnec` doens't support this, and the best solution I found is [`openconnect-sso`](https://github.com/vlaci/openconnect-sso).

## `sjsu_connect.sh`

Install `openconnect`. It's almost certainly in your favorite package manager.

This script takes a AnyConnect server, server fingerprint, and cookie (a one-time token for logging in) and spawns `openconnect` to connect. It removes the default route, instead only routing `10.0.0.0/8` which is SJSU's internal subnet.

This is designed for if you need to run the VPN on a headless or inconvenient-to-operate machine. For example, if you need to authenticate on your laptop, and transport the cookie to a server to run the VPN.

To obtain the cookie etc., I personally use
```sh
$ openconnect-sso --server vpn.sjsu.edu --authgroup Student-SSO --user ${YOUR_STUDENT_ID} --authenticate
```
which will spit out something like
```
HOST=https://vpn.sjsu.edu/
COOKIE=YESTHETHINGBELOWISSUPPOSEDTOBESCREAMMING00@@-002THANKSFORLISTENINGTOMYJOKE
FINGERPRINT=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
```
Note `YOUR_STUDENT_ID` is the 7 digit number on your Tower ID card. (Otherwise known as the Tower ID, I just thought writing the above in this verbose manner will reduce ambiguity for the fast skimmers. Tell me if it's actually helpful.)

## `sjsu_auth+connect.sh`

Install `openconnect`, _and_ [`openconnect-sso`](https://github.com/vlaci/openconnect-sso). Aside from AUR or Nix, I believe your best bet is the Pip installation method as described in their README.

This is combines the authentication step and the connection step in one script.
```sh
$ ./sjsu_auth+connect.sh ${YOUR_STUDENT_ID}
```
