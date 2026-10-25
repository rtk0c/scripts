# basic Don't Starve Together server scripts

- `dstserv_simple.sh` is a basic dedicated server runner that simply launches each shard and redirects its output to /dev/null. Supports IA, and has a crude backup system based on 7z. This one used to live [here](https://gist.github.com/rtk0c/2adfe8c000fabdb30b7f40d7ddaf5795)
- `dstserv_tmux.sh` is a modified version of the `_simple` version. It runs each shard in a tmux pane for easier admin. This one used to live [here](https://gist.github.com/rtk0c/f6ac0913e0b555da149e0ea5bbc5e409)

# proxy_for_ipv6.sh

Proxy or reverse proxy DST's listen ports on an IPv6 address, using socat.

On machine running the DST server, run this in reverse proxy, aka "host" mode.
On client machines, run this in proxy, aka "client" mode.

Listens for 4 consecutive ports starting from the given port. This works well if you have the shards bind to consecutive ports like 11001, 11002, \[11003, 11004 if playing Island Adventures\]. On normal vanilla servers, proxying extra ports shouldn't hurt.

Note that due to the reverse proxying, DST will see that all clients are connecting from 127.0.0.1.
As a consequence, you can set
```
[NETWORK]
lan_only_cluster = true
```
if you wish.


Example Usage:
```
proxy_for_ipv6.sh host '[2001:0DB8::114:514]' 11001
proxy_for_ipv6.sh client '[2001:0DB8::114:514]' 11001
```

Now you can `c_connect("127.0.0.1", 11001, "YOUR_PASSWORD")` to connect to the server, over a IPv6 link.


