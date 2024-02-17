#! /bin/ruby

require 'slop'
require 'yaml'
require 'optout'
require 'fileutils'

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
  opts[:dst_server_dir]
else
  ENV['DST_SERVER_DIR']
end
if dst_dir.nil? || dst_dir.empty?
  raise RuntimeError, "No DST server install provided. Set option --dst-server-dir or environment variable DST_SERVER_DIR."
end

# Collect whitelist, blocklist, and adminlist
def collect_user_list(list)
  return [] if list.nil?

  # Validate
  raise RuntimeError if !list.is_a? Array
  for elm in list
    raise RuntimeError if !elm.is_a? String
  end

  # If everything is fine, we can just return it
  return list
end
adminlist = collect_user_list(conf_cluster["adminlist"])
whitelist = collect_user_list(conf_cluster["whitelist"])
blocklist = collect_user_list(conf_cluster["blocklist"])

def write_defaulted_val(file, dict, name, def_value=nil)
  if dict.key? name
    file.puts "#{name} = #{dict[name]}"
  else
    file.puts "#{name} = #{def_value}" unless def_value.nil?
  end
end

def write_required_val(file, dict, name)
  if !dict.key? name
    raise RuntimeError, "Required key: #{name}"
  end

  file.puts "#{name} = #{dict[name]}"
end

File.open(File.join(opts[:output], "cluster.ini"), "w") do |f|
  # Optional config value
  opt = ->(name, def_value=nil) { write_defaulted_val(f, conf_cluster, name, def_value) }
  # Required config value
  req = ->(name) { write_required_val(f, conf_cluster, name) }

  f.puts "[GAMEPLAY]"
  opt.call "max_players"
  opt.call "pvp"
  opt.call "game_mode"
  opt.call "pause_when_empty", true
  opt.call "vote_enabled"
  
  f.puts "[MISC]"
  opt.call "max_snapshots"
  opt.call "console_enabled"

  f.puts "[NETWORK]"
  req.call "cluster_name"
  opt.call "cluster_password"
  opt.call "cluster_description"
  opt.call "cluster_intention"
  opt.call "lan_only_cluster"
  opt.call "offlien_cluster"
  opt.call "tick_rate"
  f.puts "whitelist_slots = #{whitelist.length}" unless whitelist.empty?
  opt.call "autosaver_enabled"
  
  f.puts "[STEAM]"
  opt.call "steam_group_only"
  opt.call "steam_group_id"
  opt.call "steam_group_admins"
  
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

[["whitelist.txt", whitelist],
 ["blocklist.txt", blocklist],
 ["adminlist.txt", adminlist]].each do |(filename, content)|
  next if content.empty?
  File.open(File.join(opts[:output], filename), "w") do |f|
    content.each { |user| f.puts user }
  end
end

# TODO modoverrides.lua and aggregate mods

base_port = 10998
base_port_steam_master = 28900
base_port_steam_auth = 28700

conf_shards.each_with_index do |shard, i|
  FileUtils.mkdir_p(File.join(opts[:output], shard["name"]))

  FileUtils.ln_s(
    File.join(opts[:output], shard["name"], "modoverrides.lua"),
    "../modoverrides.lua",
    force: true)

  File.open(File.join(opts[:output], shard["name"], "worldgenoverride.lua"), "w") do |f|
    f.puts %{
return {
  override_enabled = true,
  worldgen_preset = "#{shard["worldgen_preset"]}",
  settings_preset = "#{shard["settings_preset"]}",
  overrides = {
  },
}}
  end
  
  File.open(File.join(opts[:output], shard["name"], "server.ini"), "w") do |f|
    # Optional config value
    opt = ->(name, def_value=nil) { write_defaulted_val(f, shard, name, def_value) }
    # Required config value
    req = ->(name) { write_required_val(f, shard, name) }

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
    opt.call "encode_user_path", true
  end
end
