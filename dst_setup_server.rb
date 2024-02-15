#! /bin/ruby

require 'slop'
require 'yaml'
require 'optout'

opts = Slop.parse do |o|
  o.string '-c', '--config-file', 'input config file'
  o.string '-o', '--output', 'output directory', default: '.'
  o.string '--dst-server-dir', 'Don\'t Starve Together Dedicated Server install directory. Leave empty to read from the environment variable DST_SERVER_DIR.', default: ''
  o.bool '-v', '--verbose', 'enable verbose mode'
  o.bool '-q', '--quiet', 'suppress output (quiet mode)'
end

conf = YAML.load_file(opts[:config_file], aliases: true)
conf_cluster = conf["cluster"]
conf_shards = conf["shards"]
if conf_shards.length <= 0
  raise RuntimeError, "The cluster must have at least 1 shard."
end

dst_dir = if opts.dst_server_dir?
  ENV['DST_SERVER_DIR']
else
  opts[:dst_server_dir]
end
if dst_dir.nil? || dst_dir.empty?
  raise RuntimeError, "No DST server install provided. Set option --dst-server-dir or environment variable DST_SERVER_DIR."
end

def dup_val(file, dict, name, def_value=nil)
  if dict.key? name
    file.puts "#{name} = #{dict[name]}"
  else
    unless def_value.nil?
      file.puts "#{name} = #{def_value}"
    end
  end
end

def require_val(file, dict, name) 
  if !dict.key? name
    raise RuntimeError, "Required key: #{name}"
  end

  file.puts "#{name} = #{dict[name]}"
end

File.open(File.join(opts[:output], "cluster.ini"), "w") do |f|
  # Optional config value
  def o(name, def_value=nil) dup_val(f, conf_cluster, name, def_value) end
  # Required config value
  def r(name) require_val(f, conf_cluster, name) end

  f.puts "[GAMEPLAY]"
  o("max_players")
  o("pvp")
  o("game_mode")
  o("pause_when_empty", true)
  o("vote_enabled")
  
  f.puts "[MISC]"
  o("max_snapshots")
  o("console_enabled")

  f.puts "[NETWORK]"
  r("cluster_name")
  o("cluster_password")
  o("cluster_description")
  o("cluster_intention")
  o("lan_only_cluster")
  o("offlien_cluster")
  o("tick_rate")
  # TODO whitelist_slots; read this from the whitelists list property
  o("autosaver_enabled")
  
  f.puts "[STEAM]"
  o("steam_group_only")
  o("steam_group_id")
  o("steam_group_admins")
  
  # These configs are only needed for multi-shard clusters
  if conf["shards"].length > 1
    f.puts "[SHARD]"
    f.puts "shard_enabled = true"
    f.puts "bind_ip = 127.0.0.1"
    f.puts "master_ip = 127.0.0.1"
    f.puts "master_port = 10887"
    f.puts "cluster_key = defaultPass1"
  end
end

# TODO modoverrides.lua and aggregate mods

base_port = 10998
base_port_steam_master = 28900
base_port_steam_auth = 28700

conf_shards.each_with_index do |shard, i|
  Dir.mkdir(File.join(opts[:output], shard["name"]))

  File.symlink(File.join(opts[:output], shard["name"], "modoverrides.lua"), "../modoverrides.lua")

  File.open(File.join(opts[:output], shard["name"], "worldgenoverride.lua"), "w") do |f|
    # TODO
  end
  
  File.open(File.join(opts[:output], shard["name"], "server.ini"), "w") do |f|
    # Optional config value
    def o(name, def_value=nil) dup_val(f, shard, name, def_value) end
    # Required config value
    def r(name) require_val(f, shard, name) end

    f.puts "[SHARD]"
    f.puts "is_master = true" if i == 0
    f.puts "name = #{shard["name"]}"
    if shard.key? "id"
      f.puts "id = #{shard["id"]}"
    else
      f.puts "id = #{i + 1}"
    end

    f.puts "[NETWORK]"
    f.puts "server_port = #{base_port + i}"

    f.puts "[STEAM]"
    f.puts "master_server_port = #{base_port_steam_master + i}"
    f.puts "authentification_port = #{base_port_steam_auth + i}"

    f.puts "[ACCOUNT]"
    o("encode_user_path", true)
  end
end
