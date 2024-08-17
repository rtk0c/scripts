# completely managed Don't Starve Together server scripts

`dst_setup_server.rb` is a fully featured dedicated server generator script, that can take a single configuration file in YAML and spit out all the necessary files to run a cluster. It also automatically manages (overwrites) `dedicated_sever_mods_setup.lua` to include the mods used by the configured cluster.

- `dst_2shard.yml` is a demo config file for a basic 2-shard cluster of Forest and Caves
- `dst_4shard.yml` is a demo config file for a [IslandAdventures](https://steamcommunity.com/sharedfiles/filedetails/?id=1467214795) enabled 4 shard cluster
