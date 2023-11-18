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
<script/></Configuration>
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
<script/></Configuration>
"""

def write_file_if_not_exists(filepath: os.path, content: str):
	if not os.path.isfile(filepath):
		with open(filepath, 'w') as f:
			f.write(content)

class Context:
	data_dir: os.path
	version_index: MinecraftVersionIndex
	log4j2_17_111_path: os.path
	log4j2_112_116_path: os.path
	mc_1_7_ordinal: int
	mc_1_12_ordinal: int
	mc_1_16_5_ordinal: int
	mc_1_17_ordinal: int
	mc_1_17_1_ordinal: int
	mc_1_18_1_ordinal: int

	def __init__(self, data_dir: os.path):
		self.data_dir = data_dir
		self.log4j2_17_111_path = os.path.join(data_dir, LOG4J2_17_111_FILENAME)
		self.log4j2_112_116_path = os.path.join(data_dir, LOG4J2_112_116_FILENAME)

	# Perform filesystem level initialization
	def setup(self):
		index_file = os.path.join(self.data_dir, 'index.json')
		try:
			self.version_index = load_version_index(index_file)
		except IOError:
			print('-- index.json does not exist, downloading')
			self.version_index = download_version_index(index_file)
		write_file_if_not_exists(self.log4j2_17_111_path, LOG4J2_17_111_CONTENT)
		write_file_if_not_exists(self.log4j2_112_116_path, LOG4J2_112_116_CONTENT)
		self.mc_1_7_ordinal = self.get_version_basicinfo('1.7')['ordinal']
		self.mc_1_12_ordinal = self.get_version_basicinfo('1.12')['ordinal']
		self.mc_1_16_5_ordinal = self.get_version_basicinfo('1.16.5')['ordinal']
		self.mc_1_17_ordinal = self.get_version_basicinfo('1.17')['ordinal']
		self.mc_1_17_1_ordinal = self.get_version_basicinfo('1.17.1')['ordinal']
		self.mc_1_18_1_ordinal = self.get_version_basicinfo('1.18.1')['ordinal']

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

def download_file(url: str, out: os.path):
	# https://stackoverflow.com/a/39217788
	with requests.get(url, stream=True) as r:
		r.raise_for_status()
		with open(out, 'wb') as f:
			shutil.copyfileobj(r.raw, f)

def download_minecraft_instance(ctx: Context, version: str) -> os.path:
	manifest = ctx.get_version_manifest(version)
	jar_path = os.path.join(ctx.data_dir, f"server_{version}.jar")

	# We've already downloaded it
	if os.path.isfile(jar_path):
		return jar_path

	jar_url = manifest['downloads']['server']['url']
	download_file(jar_url, jar_path)

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
	if args.type == 'symlink':
		os.symlink(repo_path, inst_path)
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

	if idx >= ctx.mc_1_17_1_ordinal:
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
	elif idx >= mc_1_12_ordinal:
		log4j = Log4jPatch.LOG4J2_112_116
	elif idx >= mc_1_7_ordinal:
		log4j = Log4jPatch.LOG4J2_17_111
	else:
		log4j = Log4jPatch.NONE

	return MinecraftVersionTraits(java_version=java_ver, log4j_patch=log4j)

def do_setup(ctx: Context, out_dir: os.path, version: str):
	traits = compute_mc_version_traits(ctx, version)

	match traits.log4j_patch:
		case Log4jPatch.NONE | Log4jPatch.MSG_NO_LOOKUPS:
			pass
		case Log4jPatch.LOG4J2_17_111:
			os.symlink(ctx.log4j2_17_111_path, os.path.join(out_dir, LOG4J2_17_111_FILENAME))
		case Log4jPatch.LOG4J2_112_116:
			os.symlink(ctx.log4j2_112_116_path, os.path.join(out_dir, LOG4J2_112_116_FILENAME))

	# https://stackoverflow.com/a/45368120
	startserver_sh = os.path.join(out_dir, 'startserver.sh')
	startserver_sh_fd = os.open(
		path=startserver_sh,
		flags=os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
		# stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IROTH
		mode=0o744,
	)
	with open(startserver_sh_fd, 'w') as f:
		f.write(SERVER_SCRIPT_TEMPLATE.substitute(
			DEFAULT_TEMPLATE_ARGS,
			java_exe=traits.java_version.value,
			extra_jvm_flags=traits.log4j_patch.value,
			extra_mc_flags='nogui',
		))

	with open(os.path.join(out_dir, 'eula.txt'), 'w') as f:
		f.write('eula=true\n')

	libs_repo = os.path.join(ctx.data_dir, f"server_{version}_libs")
	libs_inst = os.path.join(out_dir, 'libraries')
	os.makedirs(libs_repo, exist_ok=True)
	os.symlink(libs_repo, libs_inst)

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
	subparser_grab.add_argument('version', help='Minecraft version string, like 1.7.10 or 23w16a')
	subparser_grab.add_argument('-o', '--output', default='.', help='Output directory.')
	subparser_grab.add_argument('-t', '--type', choices=['symlink', 'copy'], default='symlink', help='Method of getting the instance.')

	subparser_setup = subparsers.add_parser('setup', help='Setup a Minecraft instance with all the necessary files in addition to the server jar.')
	subparser_setup.add_argument('version', help='Minecraft version string, like 1.7.10 or 23w16a')
	subparser_setup.add_argument('-o', '--output', default='.', help='Output directory.')
	subparser_setup.add_argument('-t', '--type', choices=['symlink', 'copy'], default='symlink', help='Method of getting the instance.')

	return parser

def run_user_facing_program(args):
	ctx = Context(get_default_data_dir() if args.data_dir == '' else os.path.expanduser(args.data_dir))

	print(f"-- Using data dir: {ctx.data_dir}")

	match args.subparser_name:
		case 'update':
			out_path = os.path.join(ctx.data_dir, 'index.json')
			ctx.version_index = download_version_index(out_path)
		case 'list':
			ctx.setup()
			# TODO
		case 'download':
			ctx.setup()
			download_minecraft_instance(ctx, args.version)
		case 'grab':
			ctx.setup()
			do_grab(ctx, args)
		case 'setup':
			ctx.setup()
			do_grab(ctx, args)
			do_setup(ctx, args.output, args.version)

if __name__ == "__main__":
	args = make_arg_parser().parse_args()
	run_user_facing_program(args)
