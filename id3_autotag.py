import os
import glob
import re
import shutil
import argparse
import music_tag
from typing import Optional, Tuple

import my_util as MU

MUSIC_EXTS = ['mp3', 'm4a', 'flac', 'alac', 'wav', 'ogg', 'opus']
MUSIC_EXT_STRIPPER = MU.file_ext_stripper(set(MUSIC_EXTS))
# We want to match the following:
#   'no. 1' 'No. 1' 'no 1' '1.' '1-' '#1' '#1.' 'no. 1-'
# but not the following (bare numbers)
#   '1' '842'
#
# The regex divides into three capture groups.
# 1st: ([Nn]o\.? ?|#)? matches the prefix optionally
# 2nd: (\d+) matches the number itself
# 3rd has two parts:
#   ?(1)(?:\.|-|:)? optionally matches the trailing punctuation if there is a prefix (1st capture group is non-empty)
#   (?:\.|-|:) mandatorily matches the trailing punctuation otherwise
# Notice the \.|-|: common to both that describes the trailing punctuation
#
# Whole thing is wrapped in word boundary, beacuse matching 'ohno 1' makes no sense
# We match an optional extra space at the end to substitute out the extra space surrounding the index
TRACK_NUMBER_PATTERN = re.compile(r'\b([Nn]o\.? ?|#)?(\d+)(?(1)(?:\.|-|:)?|(?:\.|-|:)) ?\b')

def parse_track_number(s: str) -> Optional[int]:
  res = TRACK_NUMBER_PATTERN.search(s)
  if res:
    return int(res.group(2))
  return None

def parse_track_name(s: str) -> str:
  return MUSIC_EXT_STRIPPER(TRACK_NUMBER_PATTERN.sub('', s, count=1))

parser = argparse.ArgumentParser(prog='id3_autotag.py')
parser.add_argument('-D', '--dry-run', action='store_true')
parser.add_argument('-q', '--quiet', action='store_true')
parser.add_argument('-I', '--smart-index', action='store_true')
parser.add_argument('--artist')
parser.add_argument('--album')

args = parser.parse_args()

def my_print(msg):
  if not args.quiet:
    print(msg)

if args.dry_run:
  my_print('Performing a dry run')

music_files = []
for ext in ['*.' + s for s in MUSIC_EXTS]:
  music_files.extend(glob.glob(ext))

for filepath in music_files:
  if not args.dry_run:
    f = music_tag.load_file(filepath)
  else:
    # Dummy dict
    f = {}

  if args.smart_index:
    filename = os.path.basename(filepath)
    index = parse_track_number(filename)
    if index is not None:
      track_name = parse_track_name(filename)
      my_print(f"{filepath}: Assigning track number {index}, name '{track_name}'")
      f['tracknumber'] = index
      f['tracktitle'] = track_name
  if args.artist is not None:
    my_print(f"{filepath}: Assigning artist '{args.artist}'")
    f['artist'] = args.artist
  if args.album is not None:
    my_print(f"{filepath}: Assigning album '{args.album}'")
    f['album'] = args.album

  if not args.dry_run:
    f.save()
