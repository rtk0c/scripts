import sys
import glob
import os
import shutil
import json
import yaml
import argparse
import music_tag
import ffmpeg

from yt_dlp import YoutubeDL

# Local script files
import my_util as MU

def make_unresolved_time(s: str) -> str | int:
	if s == 'NEXTCHUNK' or s == 'VIDEOLENGTH':
		return s
	return MU.strparse_hms_to_seconds(s)

def use_pattern(pattern, txt, idx):
	return pattern.format(
		index = idx + 1,
		index_roman = MU.int_to_roman_unicode(idx + 1))

# Pass 1
def pass_postprocess_info(input_struct):
	for entry in input_struct:
		url = entry['url']
		chunks = entry['chunks']
		for i in range(len(chunks)):
			curr_chunk = chunks[i]
			next_chunk = chunks[i + 1] if i + 1 < len(chunks) else None

			if curr_chunk['end_time'] == 'NEXTCHUNK':
				if next_chunk:
					curr_chunk['end_time'] = next_chunk['begin_time']
				else:
					curr_chunk['end_time'] = 'VIDEOLENGTH'

# Pass 2
def pass_prepare_yt_dlp(input_struct):
	# TODO maybe add a cache timeout for video info?
	for entry in input_struct:
		ytb_id = MU.get_id_from_ytb_url(entry['url'])
		os.makedirs(ytb_id, exist_ok=True)

		info_file_path = os.path.join(args.output_dir, ytb_id, '$info.json')
		try:
			with open(info_file_path, 'r') as info_file:
				print('-- $info.json found, loading video info')
				info = json.load(info_file)
		except:
			print('-- $info.json not found, downloading')
			info = ydl.extract_info(entry['url'], download=False)
			with open(info_file_path, 'w+') as info_file:
				print('-- Saving $info.json')
				info_file.write(json.dumps(info))

		# Add an empty file for easy identification inside a file browser
		marker_file_path = os.path.join(args.output_dir, ytb_id, '$$ ' + MU.format_filename_lean(info['title']))
		try:
			open(marker_file_path, 'x').close()
		except:
			pass

		entry['video_id'] = ytb_id
		entry['video_info'] = info

# Pass 3
def pass_video_dependent_info(input_struct):
	for entry in input_struct:
		url = entry['url']
		video_info = entry['video_info']
		chunks = entry['chunks']
		append_filename = entry.get('use_file_extension')
		use_suffix = entry.get('suffix')
		use_prefix = entry.get('prefix')

		# Section: generating new chunks
		# (there should be no such thing happening later as we'll proceed to post process chunk info)
		video_chapters = video_info.get('chapters')
		if entry.get('chunk_by_chapter') and video_chapters:
			for chap in video_chapters:
				# TODO this should use logic in commit_entry()
				chunks.append({
					'begin_time': chap['start_time'],
					'end_time': chap['end_time'],
					'out_filename': MU.format_filename(chap['title'])
				})

		for i, chunk in enumerate(chunks):
			if chunk['end_time'] == 'VIDEOLENGTH':
				chunk['end_time'] = video_info['duration']

			# output FileName
			fn = ""
			if use_prefix:
				fn = use_pattern(use_prefix, fn, i)
			fn += chunk['chunk_name']
			if append_filename:
				fn += append_filename
			if use_suffix:
				fn += use_pattern(use_suffix, fn, i)
			chunk['out_filename'] = fn

# Pass 4
def pass_download_yt_dlp(input_struct):
	for entry in input_struct:
		# TODO is there a way to skip redownloading the info json?
		# TODO maybe there is a way to make yt-dlp download to a folder directly instead of this jank mess of changing cwd

		# At this point, we have the proper ID obtained from yt-dlp
		# But keep consistent with previous code here just in case our ID extraction logic is buggy and got a different one than theirs
		os.chdir(entry['video_id'])

		if not os.path.isfile('$mainfile.m4a'):
			existing_files = set(glob.glob('*.m4a'))
			ydl.download(entry['url'])
			for file in glob.iglob('*.m4a'):
				if file not in existing_files:
					# This is our downloaded video file
					# We don't try to get the filename from yt-dlp because AFIAK that's unstable across versions
					# and trying to duplicate their title legalize logic is a pain in he ass
					os.rename(file, '$mainfile.m4a')
		else:
			print('-- $mainfile.m4a already exists, skipping dowload')

		os.chdir('..')

# Pass 6
def pass_split_chunks(input_struct):
	for entry in input_struct:
		for chunk in entry['chunks']:
			# open a file, from `ss`, for duration `t`
			begin_time = chunk['begin_time']
			end_time = chunk['end_time']
			audio_file_path = os.path.join(entry['video_id'], '$mainfile.m4a')
			chunk_file_path = os.path.join(entry['video_id'], chunk['out_filename'])
			stream = ffmpeg.input(audio_file_path, ss=begin_time, t=(end_time - begin_time))
			# output to named file
			stream = ffmpeg.output(stream, chunk_file_path, vcodec="copy", acodec="copy")
			# this was to make trial and error easier
			stream = ffmpeg.overwrite_output(stream)

			# and actually run
			ffmpeg.run(stream)

# Pass 7
def pass_apply_tag_ops(input_struct):
	for entry in input_struct:
		for idx, chunk in enumerate(entry['chunks']):
			chunk_file_path = os.path.join(entry['video_id'], chunk['out_filename'])
			f = music_tag.load_file(chunk_file_path)

			def do_tag_op(tag_op):
				name = tag_op['name']
				value = tag_op['value']
				if value == '$INDEX':
					value = idx + 1
				elif value == '$FILENAME':
					value = chunk['out_filename']
				elif value == '$FILENAME_ORIG':
					value = chunk['chunk_name']
				f[name] = value

			for op in entry['tag_ops']:
				do_tag_op(op)
			for op in chunk['tag_ops']:
				do_tag_op(op)

			f.save()

def parse_line_with_prefix(line, prefix):
	if line.startswith(prefix):
		return line.removeprefix(prefix)
	else:
		return None

def parse_value(s):
	if not s:
		return ''
	s = s.strip()
	if s[0] == '"' and s[-1] == '"':
		return s[1:-1]
	if s[0] == "'" and s[-1] == "'":
		return s[1:-1]
	return s

TAG_OP_PREFIX = {
	'X': 1, #All
	'^': 2, #Previous line
	'S': 3, #Section
}

def parse_input_file(file):
	input_struct = []

	def make_default_entry():
		return {'url': '', 'chunks': [], 'tag_ops': []}
	curr_entry = make_default_entry()
	curr_section_beg = 0

	for line in file:
		# Skip empty lines
		if not line:
			continue
		# Skip comments
		if line.startswith('#'):
			continue

		indicator = line[0]
		tag_scope = 0
		if indicator in TAG_OP_PREFIX:
			tag_scope = TAG_OP_PREFIX[indicator]
			line = line[1:]

		if url_str := parse_line_with_prefix(line, "url: "):
			curr_entry['url'] = url_str.strip()
		elif chunk_str := parse_line_with_prefix(line, 'chunk: '):
			tp = chunk_str.strip().split(" ", 2)
			chunks = curr_entry['chunks']
			chunks.append({
				'begin_time': MU.strparse_hms_to_seconds(tp[0]),
				'end_time': make_unresolved_time(tp[1]),
				# if no name given, append chunk index
				'chunk_name': str(len(chunks) + 1) + '.m4a' if len(tp) < 3 else tp[2],
				# To be filled in postprocess pass
				'out_filename': '',
				'tag_ops': []
			})
		elif line.startswith('chunk_by_chapter: true'):
			# TODO implement this from yt-dlp's video info section
			curr_entry['chunk_by_chapter'] = True
		elif ext_str := parse_line_with_prefix(line, 'use_file_extension: '):
			curr_entry['use_file_extension'] = parse_value(ext_str)
		elif ext_str := parse_line_with_prefix(line, 'prefix: '):
			curr_entry['prefix'] = parse_value(ext_str)
		elif ext_str := parse_line_with_prefix(line, 'suffix: '):
			curr_entry['suffix'] = parse_value(ext_str)
		elif line == "$$--SECTION BREAK--$$":
			curr_section_beg = len(curr_entry['chunks'])
		elif ext_str := parse_line_with_prefix(line, 'tag('):
			(tag_names, _, ext_str) = ext_str.partition(')')
			tag_value = parse_value(ext_str.removeprefix(': '))

			tag_lists = []
			if tag_scope == 1:
				tag_lists.append(curr_entry['tag_ops'])
			elif tag_scope == 2:
				tag_lists.append(curr_entry['chunks'][-1]['tag_ops'])
			elif tag_scope == 3:
				for i in range(curr_section_beg, curr_section_end - 1):
					tag_lists.append(curr_entry['chunks'][i]['tag_ops'])
				tag_lists.append(curr_chunk['tag_ops'])
			else:
				print('Error: tag scope not specified')
				sys.exit(-1)

			for tag_name in tag_names.split(','):
				for tag_list in tag_lists:
					tag_list.append({
						'name': tag_name,
						'value': tag_value
					})
		elif line.startswith('---') and curr_entry['url']:
			# Separator, commit curr_entry
			input_struct.append(curr_entry)
			curr_section_beg = 0
			curr_entry = make_default_entry()

	# Commit last entry if there is one (we assume an entry to exist only if at least a link is present)
	if curr_entry['url']:
		input_struct.append(curr_entry)

	return input_struct

def parse_input_file_yaml(file):
	pass # TODO

def dump_input_struct(input_struct):
	# Just realized I don't actually need this, I can just print the dict using python's default formatting
	#print(json.dumps(input_struct, sort_keys=True, indent=4))
	for entry in input_struct:
		print(f"url: \"{entry['url']}\"")
		print(f"use_file_extension: {entry.get('use_file_extension')}")
		print(f"chunk_by_chapter: {bool(entry.get('chunk_by_chapter'))}")
		print(f"prefix: {entry.get('prefix')}")
		print(f"suffix: {entry.get('suffix')}")
		print('chunks:')
		for chunk in entry['chunks']:
			begin_time = chunk['begin_time']
			end_time = chunk['end_time']
			def time_fmt(time: str | int) -> str:
				if isinstance(time, int) or isinstance(time, float):
					return MU.strformat_seconds(time)
				else:
					return time
			print(f"- begin_time: {time_fmt(begin_time)}")
			print(f"  end_time: {time_fmt(end_time)}")
			print(f"  chunk_name: \"{chunk['chunk_name']}\"")
			print(f"  out_filename: \"{chunk['out_filename']}\"")
			print(f"  tag_ops:")
			for tag_op in chunk['tag_ops']:
				print(f"  - name: {tag_op['name']}")
				print(f"    value: \"{tag_op['value']}\"")
		print('tag_ops:')
		for tag_op in entry['tag_ops']:
			print(f"- name: {tag_op['name']}")
			print(f"  value: \"{tag_op['value']}\"")

def clean_outputs(output_dir):
	for dirpath, dnames, fnames in os.walk(output_dir):
		for f in fnames:
			if not f.startswith('$'):
				fpath = os.path.join(dirpath, f)
				print(f'-- Removing {fpath}')
				os.remove(fpath)

def prompt_continuation(input_struct, question):
	dump_input_struct(input_struct)
	if not MU.query_yes_no(question):
		print('-- Aborting')
		sys.exit()
	else:
		print('-- Continuing...')

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog='process_music.py', description='Music downloader and splicer')
	parser.add_argument('command_file', nargs='?')
	parser.add_argument('-o', '--output-dir', default='/tmp/hnosm--process_music/')
	# It's much cleaner, logical, and intuitive if we had `-c outputs` and `-c everything`, but that's not as ergonomic for an experience user
	parser.add_argument('-c', '--clean-outputs', action='store_true')
	parser.add_argument('-C', '--clean-everything', action='store_true')

	args = parser.parse_args()

	if args.clean_everything:
		print(f'-- Cleaning everything in output directory {args.output_dir}')
		# TODO
	elif args.clean_outputs:
		print(f'-- Cleaning output files in output directory {args.output_dir}')
		clean_outputs(args.output_dir)

	if args.command_file:
		input_file_path = os.path.abspath(args.command_file)
	else:
		print('-- No commands file provided, quitting')
		sys.exit()

	os.makedirs(args.output_dir, exist_ok=True)
	os.chdir(args.output_dir)

	dirty_file = os.path.join(args.output_dir, 'dirty')
	if os.path.isfile(dirty_file):
		print('-- Found working dir in dirty state, likely last run was canceled in the middle.')
		if MU.query_yes_no('-- Try to recover?'):
			print('-- Recovering...')
			# TODO I wrote this dirty system before everything else, turns out this "recover" logic isn't really needed and it's just a no-op right now
			#      beacuse we ended up using video ID as the folder name, implicitly having a map inside the filesystem. should we get rid of it?
		else:
			print('-- Clearing working dir...')
			shutil.rmtree(args.output_dir)
			os.mkdir(args.output_dir)
			open(dirty_file, 'x').close()
	else:
		# Create the file
		open(dirty_file, 'x').close()

	print('\n' * 2)

	ydl_opts = {
		# 140 is Youtube's AAC/.m4a format ID
		# TODO replace this with a selector so we can always get the proper one
		'format': '140'
	}

	with open(input_file_path, 'r') as file, YoutubeDL(ydl_opts) as ydl:
		input_struct = parse_input_file(file)

		pass_postprocess_info(input_struct)
		prompt_continuation(input_struct, '-- About to process these, continue to resolve patterns and video info?')

		pass_prepare_yt_dlp(input_struct)
		pass_video_dependent_info(input_struct)
		prompt_continuation(input_struct, '-- About to process these, continue to download and processing?')

		print('\n' * 2)

		pass_download_yt_dlp(input_struct)
		pass_split_chunks(input_struct)
		pass_apply_tag_ops(input_struct)

	os.remove(dirty_file)
