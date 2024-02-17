# Don't Starve Together related scripts

- `dstserv_simple.sh` is a basic dedicated server runner that simply launches each shard and redirects its output to /dev/null. Supports IA, and has a crude backup system based on 7z. This one used to live [here](https://gist.github.com/rtk0c/2adfe8c000fabdb30b7f40d7ddaf5795)
- `dstserv_tmux.sh` is a modified version of the `_simple` version. It runs each shard in a tmux pane for easier admin. This one used to live [here](https://gist.github.com/rtk0c/f6ac0913e0b555da149e0ea5bbc5e409)
- `dst_setup_server.rb` is a fully featured dedicated server generator script, that can take a single configuration file in YAML and spit out all the necessary files to run a cluster. It also automatically manages (overwrites) `dedicated_sever_mods_setup.lua` to include the mods used by the configured cluster.
  - `dst_2shard.yml` is a demo config file for a basic 2-shard cluster of Forest and Caves
  - `dst_4shard.yml` is a demo config file for a [IslandAdventures](https://steamcommunity.com/sharedfiles/filedetails/?id=1467214795) enabled 4 shard cluster
