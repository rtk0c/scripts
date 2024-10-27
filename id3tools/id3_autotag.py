#! /usr/bin/python

import os
import subprocess
import glob
import re
import shutil
import argparse
import music_tag
from typing import Optional, Tuple

import my_utils as MU
import my_vipe as MVipe

MUSIC_EXTS = ['mp3', 'm4a', 'flac', 'alac', 'wav', 'ogg', 'opus']
MUSIC_EXT_STRIPPER = MU.file_ext_stripper(set(MUSIC_EXTS))
# We want to match the following:
#   'no. 1' 'No. 1' 'no 1' '1.' '1-' '#1' '#1.' 'no. 1-'
# but not the following (bare numbers)
#   '1' '842'
#
# The regex divides into 3 parts:
#
# 1st: (?:\b[Nn]o\.? ?|#)?   Matches the prefix optionally; non-capturing, this part we're just throwing away.
#                            "no." at a word boundary, beacuse matching 'ohno 1' for the 'no 1' makes no sense.
#                            "#" not so, because apparently /\b#/ does not match "#" (pound at beginning of string, or line).
# 2nd: (\d+)       Matches the number itself.
# 3rd is a conditional on whether or not the 1st capture matched (?(1)TRUE|FALSE)
#   TRUE:  [.:-]?  Optionally matches the trailing punctuation if there is a prefix (1st group is non-empty).
#   FALSE: [.:-]   Mandatorily matches the trailing punctuation otherwise.
#
# We match an optional extra space at the end to substitute out the extra space surrounding the index
TRACK_NUMBER_PATTERN = re.compile(r'(?:\b[Nn]o\.? ?|#)?(\d+)(?(1)[.:-]?|[.:-]) ?')

YTDLP_ID_STRIPPER = re.compile(r'\[[a-zA-Z0-9-_]+\]$')

def parse_track_number(s: str) -> Optional[int]:
  res = TRACK_NUMBER_PATTERN.search(s)
  if res:
    return int(res.group(1))
  return None

def parse_track_name(s: str) -> str:
  return MUSIC_EXT_STRIPPER(TRACK_NUMBER_PATTERN.sub('', s, count=1))

parser = argparse.ArgumentParser(prog='id3_autotag.py')
parser.add_argument('-D', '--dry-run', action='store_true')
parser.add_argument('-q', '--quiet', action='store_true')
parser.add_argument('-r', '--recursive', action='store_true')
parser.add_argument('--index', default='none', choices=['none', 'smart', 'manual', 'manual+striptitle'])
parser.add_argument('--strip-ytdlp-id', action='store_true')

args = parser.parse_args()

def my_print(msg):
  if not args.quiet:
    print(msg)

if args.dry_run:
  my_print('Performing a dry run')

glob_pattern = '**/*' if args.recursive else '*'

music_files = []
for ext in [f"{glob_pattern}.{s}" for s in MUSIC_EXTS]:
  music_files.extend(glob.glob(ext, recursive=args.recursive))
music_files.sort()

if args.index.startswith('manual'):
  vipe_res = MVipe.vipe('\n'.join(music_files))
  if vipe_res:
    manual_index_map = {}
    for i, line in enumerate(vipe_res.split('\n')):
      # Skip empty lines or comments
      if line == '' or line.startswith('#'):
        continue
      manual_index_map[line.strip()] = i + 1

for filepath in music_files:
  if not args.dry_run:
    f = music_tag.load_file(filepath)
  else:
    # Dummy dict
    f = {}

  if args.index == 'smart':
    filename = os.path.basename(filepath)
    index = parse_track_number(filename)
    if index is not None:
      track_name = parse_track_name(filename)
      my_print(f"{filepath}: Assigning track number {index}, name '{track_name}'")
      f['tracknumber'] = index
      f['tracktitle'] = track_name
  elif args.index.startswith('manual'):
    if index := manual_index_map.get(filepath):
      filename = os.path.basename(filepath)
      track_name = parse_track_name(filename) if args.index.endswith('+striptitle') else MUSIC_EXT_STRIPPER(filename)
      my_print(f"{filepath}: User assigned track number {index}, name '{track_name}'")
      f['tracknumber'] = index
      f['tracktitle'] = track_name

  if args.strip_ytdlp_id:
    orig_title = str(f['tracktitle'])
    my_print(f"{filepath}: Stripped '{YTDLP_ID_STRIPPER.search(orig_title).group()}'")
    f['tracktitle'] = YTDLP_ID_STRIPPER.sub('', orig_title)

  if not args.dry_run:
    f.save()
