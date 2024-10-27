#! /usr/bin/python

import argparse
from datetime import datetime
import requests
import os
import stat
import shutil
import json
import hashlib
from enum import Enum
from string import Template
from typing import Dict, Optional, TypeAlias, NamedTuple
from dataclasses import dataclass

# Local script files
import my_util as MU

def do_symlink(src: os.path, dst: os.path, on_exist: int):
  print(f"-- Creating symlink {dst} that points to {src} in {MU.on_exist_tostr(on_exist)} mode")
  MU.symlink(src, dst, on_exist)

def do_write_file(filepath: os.path, content: str, on_exist: int = MU.OVERWRITE, permissions: int = -1):
  print(f"-- Writing file {filepath} in {MU.on_exist_tostr(on_exist)} mode")
  MU.write_file(filepath, content, on_exist, permissions)

# Terminology:
# - For the metadata describing list of all Minecraft versions, we call it the "version index". This is Mojang's version_manifest.json
# - For the metadata describing a single Minecraft version, we call it the "version manifest".

# TODO we expect a newer version_manifest_v2.json never replaces old jars, fix that

MinecraftVersionIndex: TypeAlias = Dict[str, Dict]
MinecraftVersionManifest: TypeAlias = Dict[str, Dict]

def get_default_data_dir() -> os.path:
  # TODO OS-specific data directories
  return os.path.join(os.path.expanduser('~'), '.local', 'share', '.mcman', 'downloads')

def download_version_index(output_path: os.path) -> MinecraftVersionIndex:
  resp = requests.get('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json')
  if resp.status_code != 200:
    raise RuntimeError(f"Failed to download version index from Mojang: status code {resp.status_code}")

  mojang = json.loads(resp.text)
  ours = {}

  version_list = mojang['versions']
  version_list.sort(key=lambda x: datetime.fromisoformat(x['releaseTime']))

  ours['latest'] = mojang['latest']
  ours['versions'] = {}
  for i, entry in enumerate(version_list):
    id = entry['id']
    del entry['id']
    # Precompute the sorting index of each version, for easier comparision later on
    entry['ordinal'] = i
    ours['versions'][id] = entry

  with open(output_path, 'w') as f:
    f.write(json.dumps(ours))
  return ours

def load_version_index(path: os.path) -> MinecraftVersionIndex:
  with open(path, 'r') as f:
    return json.load(f)

LOG4J2_17_111_FILENAME = 'log4j2_17-111.xml'
LOG4J2_17_111_CONTENT = r"""
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN" packages="com.mojang.util">
  <Appenders>
    <Console name="SysOut" target="SYSTEM_OUT">
      <PatternLayout pattern="[%d{HH:mm:ss}] [%t/%level]: %msg%n"/>
    </Console>
    <Queue name="ServerGuiConsole">
      <PatternLayout pattern="[%d{HH:mm:ss} %level]: %msg%n"/>
    </Queue>
    <RollingRandomAccessFile name="File" fileName="logs/latest.log" filePattern="logs/%d{yyyy-MM-dd}-%i.log.gz">
      <PatternLayout pattern="[%d{HH:mm:ss}] [%t/%level]: %msg%n"/>
      <Policies>
        <TimeBasedTriggeringPolicy/>
        <OnStartupTriggeringPolicy/>
      </Policies>
    </RollingRandomAccessFile>
  </Appenders>
  <Loggers>
    <Root level="info">
      <filters>
        <MarkerFilter marker="NETWORK_PACKETS" onMatch="DENY" onMismatch="NEUTRAL"/>
        <RegexFilter regex="(?s).*\$\{[^}]*\}.*" onMatch="DENY" onMismatch="NEUTRAL"/>
      </filters>
      <AppenderRef ref="SysOut"/>
      <AppenderRef ref="File"/>
      <AppenderRef ref="ServerGuiConsole"/>
    </Root>
  </Loggers>
</Configuration>
"""

LOG4J2_112_116_FILENAME = 'log4j2_112-116.xml'
LOG4J2_112_116_CONTENT = r"""
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
  <Appenders>
    <Console name="SysOut" target="SYSTEM_OUT">
      <PatternLayout pattern="[%d{HH:mm:ss}] [%t/%level]: %msg{nolookups}%n"/>
    </Console>
    <Queue name="ServerGuiConsole">
      <PatternLayout pattern="[%d{HH:mm:ss} %level]: %msg{nolookups}%n"/>
    </Queue>
    <RollingRandomAccessFile name="File" fileName="logs/latest.log" filePattern="logs/%d{yyyy-MM-dd}-%i.log.gz">
      <PatternLayout pattern="[%d{HH:mm:ss}] [%t/%level]: %msg{nolookups}%n"/>
      <Policies>
        <TimeBasedTriggeringPolicy/>
        <OnStartupTriggeringPolicy/>
      </Policies>
    </RollingRandomAccessFile>
  </Appenders>
  <Loggers>
    <Root level="info">
      <filters>
        <MarkerFilter marker="NETWORK_PACKETS" onMatch="DENY" onMismatch="NEUTRAL"/>
      </filters>
      <AppenderRef ref="SysOut"/>
      <AppenderRef ref="File"/>
      <AppenderRef ref="ServerGuiConsole"/>
    </Root>
  </Loggers>
</Configuration>
"""

class Context:
  def __init__(self, data_dir: os.path, version_index):
    self.data_dir = data_dir
    self.log4j2_17_111_path = os.path.join(data_dir, LOG4J2_17_111_FILENAME)
    self.log4j2_112_116_path = os.path.join(data_dir, LOG4J2_112_116_FILENAME)

    self.version_index = version_index
    do_write_file(self.log4j2_17_111_path, LOG4J2_17_111_CONTENT, on_exist=MU.IGNORE)
    do_write_file(self.log4j2_112_116_path, LOG4J2_112_116_CONTENT, on_exist=MU.IGNORE)
    self.mc_1_7_ordinal = self.get_version_basicinfo('1.7')['ordinal']
    self.mc_1_12_ordinal = self.get_version_basicinfo('1.12')['ordinal']
    self.mc_1_16_5_ordinal = self.get_version_basicinfo('1.16.5')['ordinal']
    self.mc_1_17_ordinal = self.get_version_basicinfo('1.17')['ordinal']
    self.mc_1_17_1_ordinal = self.get_version_basicinfo('1.17.1')['ordinal']
    self.mc_1_18_1_ordinal = self.get_version_basicinfo('1.18.1')['ordinal']
    self.mc_1_21_oridinal = self.get_version_basicinfo('1.21')['ordinal']

  def download_version_manifest(self, version: str) -> MinecraftVersionManifest:
    manifest_url = self.version_index['versions'][version]['url']
    resp = requests.get(manifest_url)
    if resp.status_code != 200:
      raise RuntimeError(f"Failed to download version manifest for version f{version}: status code {resp.status_code}")

    mojang = json.loads(resp.text)
    ours = mojang

    output_path = os.path.join(self.data_dir, f"server_{version}.json")
    with open(output_path, 'w') as f:
      f.write(json.dumps(ours))

    return ours

  def load_version_manifest(self, version: str) -> MinecraftVersionManifest:
    path = os.path.join(self.data_dir, f"server_{version}.json")
    with open(path, 'r') as f:
      return json.load(f)

  def get_version_manifest(self, version: str) -> MinecraftVersionManifest:
    try:
      return self.load_version_manifest(version)
    except IOError:
      return self.download_version_manifest(version)

  def get_version_basicinfo(self, version: str) -> dict:
    return self.version_index['versions'][version]

def download_minecraft_instance(ctx: Context, version: str) -> os.path:
  manifest = ctx.get_version_manifest(version)
  jar_path = os.path.join(ctx.data_dir, f"server_{version}.jar")

  # We've already downloaded it
  if os.path.isfile(jar_path):
    return jar_path

  jar_url = manifest['downloads']['server']['url']
  MU.download_file_and_save(jar_url, jar_path)

  # Check file hash
  # https://stackoverflow.com/a/44873382
  with open(jar_path, 'rb', buffering=0) as f:
    actual_sha1 = hashlib.file_digest(f, 'sha1').hexdigest()
    expected_sha1 = jar_url = manifest['downloads']['server']['sha1']
    if actual_sha1 != expected_sha1:
      raise RuntimeError(f"Mismatching file hash for {jar_path}: expected {expected_sha1}, file has {actual_sha1}")

  return jar_path

def do_grab(ctx: Context, args):
  repo_path = download_minecraft_instance(ctx, args.version)
  inst_path = os.path.join(args.output, 'server.jar')

  if args.on_existing_file == 'bail':
    if os.path.isfile(inst_path):
      raise RuntimeError(f"File {inst_path} already exists, bailing.")
  mode = MU.OVERWRITE if args.on_existing_file == 'overwrite' else MU.IGNORE

  if args.type == 'symlink':
    do_symlink(repo_path, inst_path, on_exist=mode)
  elif args.type == 'copy':
    shutil.copyfile(repo_path, inst_path)

SERVER_SCRIPT_TEMPLATE = Template("""
#!/bin/sh

${java_exe} -XX:+UnlockExperimentalVMOptions \\
  -Xms${min_ram_usage} -Xmx${max_ram_usage} \\
  -XX:+UseG1GC \\
  -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 \\
  -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 \\
  -XX:MaxGCPauseMillis=200 -XX:MaxTenuringThreshold=1 \\
  -XX:+ParallelRefProcEnabled -XX:+DisableExplicitGC \\
  -XX:+AlwaysPreTouch \\
  -XX:InitiatingHeapOccupancyPercent=15 \\
  -XX:SurvivorRatio=32 \\
  -XX:+PerfDisableSharedMem \\
  -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true \\
  ${extra_jvm_flags} -jar ${jar_name} ${extra_mc_flags}
""")

DEFAULT_TEMPLATE_ARGS = {
  'jar_name': 'server.jar',
  'min_ram_usage': '512M',
  'max_ram_usage': '6G',
}

class JavaVersion(Enum):
  JAVA_8 = '/usr/lib/jvm/java-8-openjdk/bin/java'
  JAVA_16 = '/usr/lib/jvm/java-16-openjdk/bin/java'
  JAVA_17 = '/usr/lib/jvm/java-17-openjdk/bin/java'
  JAVA_21 = '/usr/lib/jvm/java-21-openjdk/bin/java'

class Log4jPatch(Enum):
  NONE = ''
  LOG4J2_17_111 = '-Dlog4j.configurationFile=log4j2_17-111.xml'
  LOG4J2_112_116 = '-Dlog4j.configurationFile=log4j2_112-116.xml'
  MSG_NO_LOOKUPS = '-Dlog4j2.formatMsgNoLookups=true'

class MinecraftVersionTraits(NamedTuple):
  java_version: JavaVersion
  log4j_patch: Optional[Log4jPatch]

def compute_mc_version_traits(ctx: Context, version: str) -> MinecraftVersionTraits:
  idx = ctx.get_version_basicinfo(version)['ordinal']

  if idx >= ctx.mc_1_21_oridinal:
    java_ver = JavaVersion.JAVA_21
  elif idx >= ctx.mc_1_17_1_ordinal:
    java_ver = JavaVersion.JAVA_17
  elif idx >= ctx.mc_1_16_5_ordinal:
    java_ver = JavaVersion.JAVA_16
  else:
    # For 1.8-1.11, we could use java 11, but since forge doesn't like that we just go with 8 for everything
    java_ver = JavaVersion.JAVA_8

  # https://www.minecraft.net/en-us/article/important-message--security-vulnerability-java-edition
  if idx >= ctx.mc_1_18_1_ordinal:
    log4j = Log4jPatch.NONE
  elif idx >= ctx.mc_1_17_ordinal:
    log4j = Log4jPatch.MSG_NO_LOOKUPS
  elif idx >= ctx.mc_1_12_ordinal:
    log4j = Log4jPatch.LOG4J2_112_116
  elif idx >= ctx.mc_1_7_ordinal:
    log4j = Log4jPatch.LOG4J2_17_111
  else:
    log4j = Log4jPatch.NONE

  return MinecraftVersionTraits(java_version=java_ver, log4j_patch=log4j)

def do_setup(ctx: Context, args):
  path_eula_txt = os.path.join(args.output, 'eula.txt')
  path_startserver_sh = os.path.join(args.output, 'startserver.sh')
  traits = compute_mc_version_traits(ctx, args.version)

  if args.on_existing_file == 'bail':
    for p in [path_eula_txt, path_startserver_sh]:
      if os.path.isfile(p):
        raise RuntimeError(f"File {path_p} already exists, bailing.")
  mode = MU.OVERWRITE if args.on_existing_file == 'overwrite' else MU.IGNORE

  startserver_script = SERVER_SCRIPT_TEMPLATE.substitute(
    DEFAULT_TEMPLATE_ARGS,
    java_exe=traits.java_version.value,
    extra_jvm_flags=traits.log4j_patch.value,
    extra_mc_flags='nogui',
  )
  # 0o744 = rwxr--r--
  #       = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IROTH
  do_write_file(path_startserver_sh, startserver_script, on_exist=mode, permissions=0o744)
  do_write_file(path_eula_txt, 'eula=true\n', on_exist=mode)

  match traits.log4j_patch:
    case Log4jPatch.NONE | Log4jPatch.MSG_NO_LOOKUPS:
      pass
    case Log4jPatch.LOG4J2_17_111:
      do_symlink(ctx.log4j2_17_111_path, os.path.join(args.output, LOG4J2_17_111_FILENAME), on_exist=mode)
    case Log4jPatch.LOG4J2_112_116:
      do_symlink(ctx.log4j2_112_116_path, os.path.join(args.output, LOG4J2_112_116_FILENAME), on_exist=mode)

  # Turns out (at least I _believe_ so) minecraft's libraries always include the version in their file names,
  # so we can save some storage even further by just making every version share the same libraries folder.
  # This is not true for Forge and Fabric.
  # Forge in post-1.18 introduced some instance specific files like user_jvm_args.txt that needs to live in libraries/
  # Fabric does not, but seems to really not like traversing through the symlink (crashes on startup during my testing)
  libs_repo = os.path.join(ctx.data_dir, f"libraries")
  libs_inst = os.path.join(args.output, 'libraries')
  os.makedirs(libs_repo, exist_ok=True)
  do_symlink(libs_repo, libs_inst, on_exist=mode)

def make_grablike_parser(parser: argparse.ArgumentParser):
  parser.add_argument('version', help='Minecraft version string, like 1.7.10 or 23w16a')
  parser.add_argument('-o', '--output', default='.', help='Output directory.')
  parser.add_argument('-t', '--type', choices=['symlink', 'copy'], default='symlink', help='Method of getting the instance.')
  parser.add_argument('-e', '--on-existing-file', choices=['bail', 'overwrite', 'ignore'], default='ignore', help='Action to perform when a file to be written already exists.')

def make_arg_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='Minecraft Instance Downloader')
  parser.add_argument('-D', '--data-dir', default='', help='Data directory for storing downloaded files. Leave empty to use the platform default.')
  subparsers = parser.add_subparsers(dest='subparser_name', help='subcommands')

  subparser_update = subparsers.add_parser('update', help='Update the version index.')

  subparser_list = subparsers.add_parser('list', help='List Minecraft versions')
  subparser_list.add_argument('-a', '--all', action='store_true', help='List all available versions rather than just the locally installed ones')

  subparser_download = subparsers.add_parser('download', help='Download a Minecraft instance into the data directory.')
  subparser_download.add_argument('version', help='Minecraft version string, like 1.7.10 or 23w16a')

  subparser_grab = subparsers.add_parser('grab', help='Get a Minecraft instance into some output directory; download it if it has not been downloaded already.')
  make_grablike_parser(subparser_grab)

  subparser_setup = subparsers.add_parser('setup', help='Setup a Minecraft instance with all the necessary files in addition to the server jar.')
  make_grablike_parser(subparser_setup)

  return parser

def run_user_facing_program(args):
  if d := args.data_dir:
    # Support things like ~/path/to/mcman
    data_dir = os.path.expanduser(d)
  elif d := os.environ.get('MCMAN_DATA_DIR'):
    data_dir = d
  else:
    data_dir = get_default_data_dir()

  print(f"-- Using data dir: {ctx.data_dir}")

  index_file = os.path.join(self.data_dir, 'index.json')
  match args.subparser_name:
    case 'update':
      download_version_index(index_file)
      print('-- Finished downloading version index')
      return

  ctx = Context(load_version_index(index_file))
  match args.subparser_name:
    case 'update':
      pass
    case 'list':
      pass
      # TODO
    case 'download':
      download_minecraft_instance(ctx, args.version)
    case 'grab':
      do_grab(ctx, args)
    case 'setup':
      do_grab(ctx, args)
      do_setup(ctx, args)

if __name__ == "__main__":
  args = make_arg_parser().parse_args()
  run_user_facing_program(args)
