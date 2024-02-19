#! /bin/ruby

require 'set'
require 'yaml'
require 'fileutils'
require 'slop'

class String
  def for_prefix(prefix)
    yield self[(prefix.length)..] if self.start_with? prefix
  end
end

def dump_as_lua(o)
  case o
  when Hash
    middle = o.map { |k,v| "\"#{k.to_s}\"=#{dump_as_lua(v)}" }.join(",")
    return "{#{middle}}"
  when Array
    middle = o.map { |x| dump_as_lua(x) }.join(",")
    return "[#{middle}]"
  when String
    return o.dump
  when nil
    # nil.to_s gives an empty string, not what we want
    return "nil"
  else
    # Integers, floats, booleans are fine as-is
    return o.to_s
  end
end

opts = Slop.parse do |o|
  o.string '-c', '--config-file', 'input config file'
  o.string '-o', '--output', 'Output directory. Leave empty to use ./<config file name without extension>'
  o.string '--dst-server-dir', 'Don\'t Starve Together Dedicated Server install directory. Leave empty to read from the environment variable DST_SERVER_DIR.'
  o.bool '--write-installer-lua', 'Whether or not to overwrite dedicated_server_mods_setup.lua to be all the mods used by this cluster.', default: true
  o.bool '--script', 'Whether or not to generate a script.sh for running the server.', default: true
  o.symbol '--script-type', 'Which style of start.sh to generate. Available options: simple, tmux', default: :simple
  o.string '--multilib', 'Which multilib to use in start.sh. Available options: x86, x86_64', default: :x86_64

  o.bool '-h', '--help'
end
if opts[:help]
  puts opts
  exit
end

if !opts.output?
  opts[:output] = "./" + opts[:config_file].delete_suffix(".yml")
end
puts "-- Using output dir: #{opts[:output]}"
FileUtils.mkdir_p(opts[:output])

dst_dir = if opts.dst_server_dir?
  opts[:dst_server_dir]
else
  ENV['DST_SERVER_DIR']
end
if dst_dir.nil? || dst_dir.empty?
  raise RuntimeError, "No DST server install provided. Set option --dst-server-dir or environment variable DST_SERVER_DIR."
end
if !Dir.exist? dst_dir
  raise RuntimeError, "Specified DST server dir does not exist."
end

conf = YAML.load_file(opts[:config_file], aliases: true)
conf_cluster = conf["cluster"]
conf_shards = conf["shards"]
if conf_shards.length <= 0
  raise RuntimeError, "The cluster must have at least 1 shard."
end

# Gather a list of all mods that needs to be installed through Steam Workshop
mod_list = Set.new
conf_shards.each do |shard|
  mods = shard["mods"]
  next if mods.nil?

  # Validate individual mods
  raise RuntimeError unless mods.is_a? Hash
  mods.each do |mod_name, options|
    # Validate mod name
    raise RuntimeError unless mod_name.is_a?(String) && !mod_name.empty?

    # Validate options
    if options.nil?
      options = mods[mod_name] = {}
    end
    raise RuntimeError unless options.is_a? Hash

    mod_name.for_prefix("workshop-") { |id| mod_list.add(id) }
  end
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
  # Values: survival, endless, wilderness
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
  opt.call "offline_cluster"
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

# Write dedicated_server_mods_setup.lua
File.open(File.join(dst_dir, "mods", "dedicated_server_mods_setup.lua"), "w") do |f|
  mod_list.each do |mod_name|
    f.puts "ServerModSetup(\"#{mod_name}\")"
  end
end if opts[:write_installer_lua]

def get_worldgenoverride_lua(world)
  # TODO support overrides
  return %{
return {
  override_enabled = true,
  worldgen_preset = "#{world["worldgen_preset"]}",
  settings_preset = "#{world["settings_preset"]}",
  overrides = {
  },
}
}
end

base_port = 10998
base_port_steam_master = 28900
base_port_steam_auth = 28700

conf_shards.each_with_index do |shard, i|
  shard_name = shard["name"]
  world = shard["world"]
  mods = shard["mods"]

  FileUtils.mkdir_p(File.join(opts[:output], shard_name))

  case world["setup"]
  when "worldgenoverride.lua"
    wgo_path = File.join(opts[:output], shard_name, "worldgenoverride.lua")
    f = File.open(wgo_path, "w")
    f.write get_worldgenoverride_lua(world)
    f.close
  when "leveldataoverride.lua"
    ldo_path = File.join(opts[:output], shard_name, "levedataoverride.lua")
    if world["file"].is_a? String
      FileUtils.cp(world["file"], ldo_path)
    elsif world["content"].is_a? String
      f = File.open(ldo_path, "w")
      f.write world["content"]
      f.close
    else
      raise RuntimeError, "Selected leveldataoverride.lua but no data is specified"
    end
  end

  File.open(File.join(opts[:output], shard_name, "modoverrides.lua"), "w") do |f|
    f.puts "return {"
    mods.each do |mod_name, options|
      f.puts "[\"#{mod_name}\"] = {"
      f.puts "enabled = true,"
      f.puts "configuration_options = #{dump_as_lua(options)}"
      f.puts "},"
    end
    f.puts "}"
  end unless mods.nil?
  # We could omit the file too if mods.empty?, but that can be confusing as to "why is that file not generating!?"
  # emitting an empty file tells the user more clearly that "you did something wrong, the mods block had nothing in it"

  File.open(File.join(opts[:output], shard_name, "server.ini"), "w") do |f|
    # Optional config value
    opt = ->(name, def_value=nil) { write_defaulted_val(f, shard, name, def_value) }
    # Required config value
    req = ->(name) { write_required_val(f, shard, name) }

    f.puts "[SHARD]"
    f.puts "is_master = true" if i == 0
    f.puts "name = #{shard_name}"
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

ARGS_BASIC = '-persistent_storage_root "$DATA_DIR_PREFIX" -conf_dir "$DATA_DIR_LAST" -ugc_directory ../ugc_mods'
ARGS_EXTRA = '-console -skip_update_server_mods'

# Generate server start script
File.open(File.join(opts[:output], "start.sh"), "w") do |f|
  cluster_dir_name = File.basename File.expand_path opts[:output]

  f.puts "#! /bin/sh"

  case opts[:multilib]
  when :x86
    dstds_cwd = File.join(dst_dir, "bin")
    dstds_bin = "dontstarve_dedicated_server_nullrenderer"
  when :x86_64
    dstds_cwd = File.join(dst_dir, "bin64")
    dstds_bin = "dontstarve_dedicated_server_nullrenderer_x64"
  end

  # https://stackoverflow.com/a/246128
  f.puts %{
CLUSTER_DIR_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
CLUSTER_DIR_NAME=$(basename "$CLUSTER_DIR_PATH")
DATA_DIR=$(readlink -f "$CLUSTER_DIR_PATH/..")
DATA_DIR_PREFIX=$(dirname "$DATA_DIR")
DATA_DIR_LAST=$(basename "$DATA_DIR")
echo "-- Running cluster at '$DATA_DIR_PREFIX/$DATA_DIR_LAST/$CLUSTER_DIR_NAME'"
echo "-- Multilib: #{opts[:multilib]}"
echo "-- Updating server mods..."
cd '#{dstds_cwd}'
./#{dstds_bin} #{ARGS_BASIC} -only_update_server_mods > /dev/null 2>&1 &
wait
cd -
}

  case opts[:script_type]
  when :simple
    # See dstserv_simple.sh for the reference implementation

    f.puts "cd '#{dstds_cwd}'"
    conf_shards.each do |shard|
      shard_dir_name = shard["name"]

      f.puts "echo '-- Running shard #{shard_dir_name}'"
      f.puts "./#{dstds_bin} #{ARGS_BASIC} -cluster \"$CLUSTER_DIR_NAME\" -shard '#{shard_dir_name}' #{ARGS_EXTRA} > /dev/null 2>&1 &"
    end

    f.puts "trap 'kill $(jobs -p)' EXIT"
    f.puts "wait"
  when :tmux
    # See dstserv_tmux.sh for the reference implementation

    f.puts "SESSION='DST #{conf_cluster["cluster_name"]}'"
    conf_shards.each_with_index do |shard, i|
      shard_dir_name = shard["name"]

      if i == 0
        f.puts "tmux new-session -d -s \"$SESSION\" -n '#{shard_dir_name}' 'exec /bin/sh'"
      else
        f.puts "tmux new-window -t \"$SESSION\" -n '#{shard_dir_name}' 'exec /bin/sh'"
      end

      f.puts "tmux send-keys -t \"$SESSION\" \"cd '#{dstds_cwd}'\" Enter"
      f.puts "tmux send-keys -t \"$SESSION\" \"./#{dstds_bin} #{ARGS_BASIC.gsub(/"/, "'")} -cluster '$CLUSTER_DIR_NAME' -shard '#{shard_dir_name}' #{ARGS_EXTRA}\" Enter"
    end
  end
end if opts[:script]
