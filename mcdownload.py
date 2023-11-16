import argparse
import requests
import os
import shutil
import json
import hashlib
from typing import Dict, TypeAlias, NamedTuple
from dataclasses import dataclass

# Terminology:
# - For the metadata describing list of all Minecraft versions, we call it the "version index". This is Mojang's version_manifest.json
# - For the metadata describing a single Minecraft version, we call it the "version manifest".

# TODO we expect a newer version_manifest_v2.json never replaces old jars, fix that

MinecraftVersionIndex: TypeAlias = Dict[str, Dict]
MinecraftVersionManifest: TypeAlias = Dict[str, Dict]

def get_default_data_dir() -> os.path:
	return os.path.join(os.path.expanduser('~'), '.local', 'share', '.mcman', 'downloads')

def download_version_index(output_path: os.path) -> MinecraftVersionIndex:
	resp = requests.get('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json')
	if resp.status_code != 200:
		raise RuntimeError(f"Failed to download version index from Mojang: status code {resp.status_code}")

	mojang = json.loads(resp.text)
	ours = {}

	ours['latest'] = mojang['latest']
	ours['versions'] = {}
	for entry in mojang['versions']:
		id = entry['id']
		del entry['id']
		ours['versions'][id] = entry

	with open(output_path, 'w') as f:
		f.write(json.dumps(ours))
	return ours

def load_version_index(path: os.path) -> MinecraftVersionIndex:
	with open(path, 'r') as f:
		return json.load(f)

@dataclass
class Context:
	data_dir: os.path
	version_index: MinecraftVersionIndex

	def load_from_disk(self):
		the_file = os.path.join(self.data_dir, 'index.json')
		try:
			self.version_index = load_version_index(the_file)
		except IOError:
			print('-- index.json does not exist, downloading')
			self.version_index = download_version_index(the_file)

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
	subparser_grab.add_argument('-d', '--no-download', help='Error if the specified Minecraft version has not been downloaded, instead of automatically downloading it.', action='store_false')

	return parser

def do_work(args):
	ctx = Context(
		data_dir=get_default_data_dir() if args.data_dir == '' else os.path.expanduser(args.data_dir),
		version_index={},
	)

	print(f"-- Using data dir: {ctx.data_dir}")

	match args.subparser_name:
		case 'update':
			out_path = os.path.join(ctx.data_dir, 'index.json')
			ctx.version_index = download_version_index(out_path)
		case 'list':
			ctx.load_from_disk()
			# TODO
		case 'download':
			ctx.load_from_disk()
			download_minecraft_instance(ctx, args.version)
		case 'grab':
			ctx.load_from_disk()
			repo_path = download_minecraft_instance(ctx, args.version)
			out_path = os.path.join(args.output, 'server.jar')
			if args.type == 'symlink':
				os.symlink(repo_path, out_path)
			elif args.type == 'copy':
				shutil.copyfile(repo_path, out_path)

if __name__ == "__main__":
	args = make_arg_parser().parse_args()
	do_work(args)
