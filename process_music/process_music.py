#! /usr/bin/python

import sys
import glob
import os
import shutil
import itertools
import hashlib
import argparse
import json
from typing import Optional
from dataclasses import dataclass, field

import ffmpeg
import music_tag
from yt_dlp import YoutubeDL

# Local script files
import my_utils as MU

@dataclass
class TagOp():
  name: str = ''
  value: str = ''

@dataclass
class Chunk():
  begin_time: float = 0.0
  end_time: float | str = ''
  chunk_name: str = ''
  tag_ops: list[TagOp] = field(default_factory=list)
  out_basename: Optional[str] = None
  out_filepath: Optional[str] = None

@dataclass
class Job():
  url: str = ''
  mainfile: str = ''
  mainfile_ext: str = ''
  chunk_by_chapter: bool = False
  prefix: Optional[str] = None
  suffix: Optional[str] = None
  wksp_id: str = ''
  video_info: dict = field(default_factory=dict)
  tag_ops: list[TagOp] = field(default_factory=list)
  chunks: list[Chunk] = field(default_factory=list)

@dataclass
class InputStruct():
  job_list: list[Job] = field(default_factory=list)

def use_pattern(pattern, txt, idx):
  return pattern.format(
    index = idx + 1,
    index_roman = MU.int_to_roman_unicode(idx + 1))

def calc_workspace_id(url: str) -> str:
  return hashlib.md5(url.encode('utf-8')).hexdigest()

# Pass 1
def pass_postprocess_info(input_struct: InputStruct):
  print(input_struct)
  for job in input_struct.job_list:
    chunks = job.chunks
    for i in range(len(chunks)):
      curr_chunk = chunks[i]
      next_chunk = chunks[i + 1] if i + 1 < len(chunks) else None

      if curr_chunk.end_time == 'NEXTCHUNK':
        if next_chunk is not None:
          curr_chunk.end_time = next_chunk.begin_time
        else:
          curr_chunk.end_time = 'VIDEOLENGTH'

# Pass 2
def pass_prepare_yt_dlp(input_struct: InputStruct):
  # TODO maybe add a cache timeout for video info?
  for job in input_struct.job_list:
    wksp_id = calc_workspace_id(job.url)
    os.makedirs(wksp_id, exist_ok=True)

    info_file_path = os.path.join(wksp_id, '$info.json')
    try:
      with open(info_file_path, 'r') as info_file:
        print('-- $info.json found, loading video info')
        info = json.load(info_file)
    except:
      print('-- $info.json not found, downloading')
      info = ydl.extract_info(job.url, download=False)
      with open(info_file_path, 'w') as info_file:
        print('-- Saving $info.json')
        info_file.write(json.dumps(info))

    # Add an empty file for easy identification inside a file browser
    marker_file_path = os.path.join(wksp_id, '$$ ' + MU.format_filename(info['title']))
    try:
      open(marker_file_path, 'x').close()
    except:
      pass

    job.wksp_id = wksp_id
    job.video_info = info

# Pass 3
def pass_video_dependent_info(input_struct: InputStruct):
  for job in input_struct.job_list:
    chunks = job.chunks

    # Section: generating new chunks
    # (there should be no such thing happening later as we'll proceed to post process chunk info)
    video_chapters = job.video_info.get('chapters')
    if job.chunk_by_chapter and video_chapters:
      for chap in video_chapters:
        chunks.append(Chunk(
          begin_time=chap['start_time'],
          end_time=chap['end_time'],
          chunk_name=chap['title'],
          out_basename=MU.format_filename(chap['title'])))

    for i, chunk in enumerate(chunks):
      # NOTE: we leave 'end_time' special value VIDEOLENGTH as is because it's easy to compute, and knowing it is required in pass_split_chunks()
      # output FileName
      fn = ""
      if job.prefix:
        fn = use_pattern(job.prefix, fn, i)
      fn += chunk.chunk_name
      if job.suffix:
        fn += use_pattern(job.suffix, fn, i)
      chunk.out_basename = fn

def obtain_video_with_yt_dlp(video_url: str) -> tuple[str, str]:
  existing_files = set(os.listdir())
  ydl.download_with_info_file('$info.json')
  for file in os.listdir():
    if file not in existing_files:
      _, ext = os.path.splitext(file)
      # This is our downloaded video file
      # We don't try to get the filename from yt-dlp because AFIAK that's unstable across versions
      # and trying to duplicate their title legalize logic is a pain in he ass
      mainfile = f"$mainfile{ext}"
      os.rename(file, mainfile)
      return (mainfile, ext)

MUSIC_EXTS = ['.mp3', '.m4a', '.flac', '.alac', '.wav', '.opus']

def obtain_video_reuse(video_id: str, reuse_dir: os.path) -> Optional[tuple[str, str]]:
  # Try to find a existing file
  for filepath in os.listdir(reuse_dir):
    filename = os.path.basename(filepath)
    base, ext = os.path.splitext(filename)
    if (ext in MUSIC_EXTS
      and base.find(video_id) != -1
      and MU.query_yes_no(f"-- Reuse '{filepath}' for the video {video_id}?")
    ):
      mainfile = f"./$mainfile{ext}"
      shutil.copyfile(filepath, mainfile)
      return (mainfile, ext)
  return None

def obtain_video(video_id: str, video_url: str, reuse_dir: Optional[os.path]) -> tuple[str, str]:
  # Use iglob to avoid overhead of collecting into a list, we just want the first item
  # TODO maybe print a warning if there is more than one $mainfile.*
  for mainfile in glob.iglob('$mainfile.*'):
    print(f"-- {mainfile} already exists, skipping dowload")
    _, ext = os.path.splitext(mainfile)
    return (mainfile, ext)

  if reuse_dir is not None:
    result = obtain_video_reuse(video_id, reuse_dir)
    if result is not None:
      print('-- Reused existing file.')
      return result

  return obtain_video_with_yt_dlp(video_url)

# Pass 4
def pass_download_yt_dlp(input_struct: InputStruct, reuse_dir: Optional[os.path]):
  for job in input_struct.job_list:
    os.chdir(job.wksp_id)
    mainfile, ext = obtain_video(job.video_info['id'], job.url, reuse_dir)
    job.mainfile = mainfile
    job.mainfile_ext = ext
    if ext == '.webm':
      # TODO actually make sure it's an opus/vorbis stream...
      basename, _ = os.path.splitext(mainfile)
      new_name = f"{basename}.ogg"
      stream = ffmpeg.input(mainfile)
      stream = ffmpeg.output(stream, new_name, acodec="copy")
      stream = ffmpeg.overwrite_output(stream)
      ffmpeg.run(stream)
      job.mainfile = new_name
      job.mainfile_ext = '.ogg'
      os.remove(mainfile)
    os.chdir('..')

# Pass 6
def pass_split_chunks(input_struct: InputStruct, output_dir: Optional[os.path]):
  for job in input_struct.job_list:
    # Assume cwd is already in work_dir, so just wksp_id is enough
    output_prefix = output_dir if output_dir is not None else job.wksp_id
    audio_filepath = os.path.join(job.wksp_id, job.mainfile)

    for chunk in job.chunks:
      chunk_filepath = os.path.join(output_prefix, chunk.out_basename + job.mainfile_ext)
      # Save absolute file path for later passes
      chunk.out_filepath = os.path.abspath(chunk_filepath)

      begin_time = chunk.begin_time
      end_time = chunk.end_time
      if end_time == 'VIDEOLENGTH' and begin_time == 0:
        # This is a whole video chunk
        shutil.copyfile(audio_filepath, chunk_filepath)
        continue
      elif end_time == 'VIDEOLENGTH':
        end_time = job.video_info['duration']

      # open a file, from `ss`, for duration `t`
      stream = ffmpeg.input(audio_filepath, ss=begin_time, t=(end_time - begin_time))
      # output to named file
      stream = ffmpeg.output(stream, chunk_filepath, vcodec="copy", acodec="copy")
      # this was to make trial and error easier
      stream = ffmpeg.overwrite_output(stream)

      # and actually run
      ffmpeg.run(stream)

# Pass 7
def pass_apply_tag_ops(input_struct: InputStruct):
  for job in input_struct.job_list:
    for idx, chunk in enumerate(job.chunks):
      f = music_tag.load_file(chunk.out_filepath)

      for op in itertools.chain(job.tag_ops, chunk.tag_ops):
        name = op.name
        value = op.value
        if value == '$INDEX':
          value = idx + 1
        elif value == '$FILENAME':
          value = chunk.out_basename + job.mainfile_ext
        elif value == '$FILENAME_ORIG':
          print('-- [WARN] $FILENAME_ORIG is deprecated, use $CHUNK_NAME instead')
          value = chunk.chunk_name
        elif value == '$CHUNK_NAME':
          value = chunk.chunk_name
        f[name] = value

      f.save()

def parse_line_with_prefix(line, prefix):
  if line.startswith(prefix):
    return line.removeprefix(prefix)
  else:
    return None

def parse_unresolved_time(s: str) -> str | int:
  if s == 'NEXTCHUNK' or s == 'VIDEOLENGTH':
    return s
  return MU.strparse_hms_to_seconds(s)

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

def parse_input_file(f) -> InputStruct:
  input_struct = InputStruct()
  job_list = input_struct.job_list

  curr_job = Job()
  curr_section_beg = 0

  for line in f:
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
      curr_job.url = url_str.strip()
    elif chunk_str := parse_line_with_prefix(line, 'chunk: '):
      tp = chunk_str.strip().split(" ", 2)
      if len(tp) != 3:
        raise RuntimeError('chunk string need exactly 3 components: BEGIN_TIME, END_TIME, CHUNK_NAME separated by spaces')
      chunks = curr_job.chunks
      chunks.append(Chunk(
        begin_time=MU.strparse_hms_to_seconds(tp[0]),
        end_time=parse_unresolved_time(tp[1]),
        chunk_name=parse_value(tp[2])))
    elif line.startswith('chunk_by_chapter: true'):
      curr_job.chunk_by_chapter = True
    elif ext_str := parse_line_with_prefix(line, 'use_file_extension: '):
      print('-- [WARN] Directive use_file_extension is now deprecated. Chunks file extension will be automatically extracted from the video info.')
      #curr_job.use_file_extension = parse_value(ext_str)
    elif ext_str := parse_line_with_prefix(line, 'prefix: '):
      curr_job.prefix = parse_value(ext_str)
    elif ext_str := parse_line_with_prefix(line, 'suffix: '):
      curr_job.suffix = parse_value(ext_str)
    elif line.startswith('$$--SECTION BREAK--$$'):
      curr_section_beg = len(curr_job.chunks)
    elif ext_str := parse_line_with_prefix(line, 'tag('):
      (tag_names, _, ext_str) = ext_str.partition(')')
      tag_value = parse_value(ext_str.removeprefix(': '))

      tag_lists = []
      if tag_scope == 1:
        tag_lists.append(curr_job.tag_ops)
      elif tag_scope == 2:
        tag_lists.append(curr_job.chunks[-1].tag_ops)
      elif tag_scope == 3:
        for i in range(curr_section_beg, len(curr_job.chunks)):
          tag_lists.append(curr_job.chunks[i].tag_ops)
      else:
        print('Error: tag scope not specified')
        sys.exit(-1)

      for tag_name in tag_names.split(','):
        for tag_list in tag_lists:
          tag_list.append(TagOp(
            name=tag_name,
            value=tag_value))
    elif line.startswith('---') and curr_job.url:
      # Separator, commit curr_job
      job_list.append(curr_job)
      curr_section_beg = 0
      curr_job = Job()

  # Commit last job if there is one (we assume a job to be well-formed only if at least an url is present)
  if curr_job.url:
    job_list.append(curr_job)

  return input_struct

# Example YAML input format
"""
# Sibelius: Lemminkäinen ∙ hr-Sinfonieorchester ∙ Jukka-Pekka Saraste
url: "https://www.youtube.com/watch?v=x_vVc62BMfs"
prefix: "{index_roman}. "
suffix: ".m4a"
chunks:
- filename: "Lemminkäinen und die Mädchen auf der Insel"
  segment: "00:03 NEXTCHUNK"
- filename: "Lemminkäinen in Tuonela"
  segment: "16:02 NEXTCHUNK"
- filename: "Der Schwan von Tuonela"
  segment: "30:50 NEXTCHUNK"
- filename: "Lemminkäinen zieht heimwärts"
  segment: "39:05 NEXTCHUNK"
tags:
- type: author
  scope: all
  value: "Jean Sibelius"
- type: album
  scope: all
  value: "Lemminkäinen Suite"
- type: tracknumber
  scope: all
  value:
    macro: $INDEX
---
url: "another vidoe"
prefix: "..."
"""
def parse_input_file_yaml(file):
  pass # TODO

def dump_input_struct(input_struct: InputStruct):
  # TODO other fields
  for job in input_struct.job_list:
    print(f"url: \"{job.url}\"")
    print(f"chunk_by_chapter: {bool(job.chunk_by_chapter)}")
    print(f"prefix: {job.prefix}")
    print(f"suffix: {job.suffix}")
    print('chunks:')
    for chunk in job.chunks:
      begin_time = chunk.begin_time
      end_time = chunk.end_time
      def time_fmt(time: str | float | int) -> str:
        if isinstance(time, int) or isinstance(time, float):
          return MU.strformat_seconds(time)
        else:
          return time
      print(f"- begin_time: {time_fmt(begin_time)}")
      print(f"  end_time: {time_fmt(end_time)}")
      print(f"  chunk_name: \"{chunk.chunk_name}\"")
      print(f"  out_basename: \"{chunk.out_basename}\"")
      print(f"  tag_ops:")
      for tag_op in chunk.tag_ops:
        print(f"  - name: {tag_op.name}")
        print(f"    value: \"{tag_op.value}\"")
    print('tag_ops:')
    for tag_op in job.tag_ops:
      print(f"- name: {tag_op.name}")
      print(f"  value: \"{tag_op.value}\"")

def clean_outputs(work_dir):
  for dirpath, dnames, fnames in os.walk(work_dir):
    for f in fnames:
      if not f.startswith('$'):
        fpath = os.path.join(dirpath, f)
        print(f'-- Removing {fpath}')
        os.remove(fpath)

def prompt_continuation(input_struct: InputStruct, question):
  dump_input_struct(input_struct)
  if args.always_yes:
    return
  if not MU.query_yes_no(question):
    print('-- Aborting')
    sys.exit()
  else:
    print('-- Continuing...')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(prog='process_music.py', description='Music downloader and splicer')
  parser.add_argument('command_file', nargs='?')
  parser.add_argument('--reuse', help='Directory to search for existing video files. File names must contain the video ID.')
  parser.add_argument('--work-dir', default='/tmp/00-myscript-process_music/')
  parser.add_argument('--output-dir', help='Directory to place output (sliced) audio files. If relative, it is relative to --work-dir. Omit to use the same directory as work dir.')
  parser.add_argument('-y', '--always-yes', action='store_true', help='Skip all yes/no prompts.')
  # It's much cleaner, logical, and intuitive if we had `-c outputs` and `-c everything`, but that's not as ergonomic for an experience user
  parser.add_argument('-c', '--clean-outputs', action='store_true')
  parser.add_argument('-C', '--clean-everything', action='store_true')
  parser.add_argument('--format', default='bestaudio')

  args = parser.parse_args()

  if args.clean_everything:
    print(f'-- Cleaning everything in output directory {args.work_dir}')
    shutil.rmtree(args.work_dir)
  elif args.clean_outputs:
    print(f'-- Cleaning output files in output directory {args.work_dir}')
    clean_outputs(args.work_dir)

  if args.command_file:
    input_file_path = os.path.abspath(args.command_file)
  else:
    print('-- No commands file provided, quitting')
    sys.exit()

  print(f"-- Reuse dir: {args.reuse}")

  print(f"-- Using work dir: {args.work_dir}")
  os.makedirs(args.work_dir, exist_ok=True)
  os.chdir(args.work_dir)

  if args.output_dir is not None:
    print(f"-- Using output dir {os.path.abspath(args.output_dir)}")
    os.makedirs(args.output_dir, exist_ok=True)
  else:
    print("-- Using output dir same as each video's work dir")

  dirty_file = 'dirty'
  if os.path.isfile(dirty_file):
    print('-- Found working dir in dirty state, likely last run was canceled in the middle.')
    if args.always_yes or MU.query_yes_no('-- Try to recover?'):
      print('-- Recovering...')
      # TODO I wrote this dirty system before everything else, turns out this "recover" logic isn't really needed and it's just a no-op right now
      #      beacuse we ended up using video ID as the folder name, implicitly having a map inside the filesystem. should we get rid of it?
    else:
      print('-- Clearing working dir...')
      shutil.rmtree(args.work_dir)
      os.mkdir(args.work_dir)
      open(dirty_file, 'x').close()
  else:
    # Create the file
    open(dirty_file, 'x').close()

  print('\n' * 2)

  ydl_opts = {
    'format': args.format,
    # yt-dlp automatically downloads all playlist items, no need to specify anything
    # The heuristic for handling playlists is basically a detection for how many files were produced during the download process
    # For B站的分P视频，yt-dlp会自动把它当作playlist处理；合集同理，因此不需要额外的逻辑
    #'playlist-items': (Something)
  }

  with open(input_file_path, 'r') as file, YoutubeDL(ydl_opts) as ydl:
    input_struct = parse_input_file(file)

    pass_postprocess_info(input_struct)
    prompt_continuation(input_struct, '-- About to process these, continue to resolve patterns and video info?')

    pass_prepare_yt_dlp(input_struct)
    pass_video_dependent_info(input_struct)
    prompt_continuation(input_struct, '-- About to process these, continue to download and processing?')

    print('\n' * 2)

    pass_download_yt_dlp(input_struct, args.reuse)
    pass_split_chunks(input_struct, args.output_dir)
    pass_apply_tag_ops(input_struct)

  os.remove(dirty_file)
  os.chdir('..')
