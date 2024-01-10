import os
import glob
import re
import shutil
import argparse
import music_tag
from typing import Optional, Tuple

import my_util as MU

def parse_leading_digits(s: str) -> Tuple[Optional[int], str]:
    i = 0
    while i < len(s) and s[i].isdigit():
        i += 1
    if i > 0:
        return (int(s[:i]), s[i:])
    else:
        return (None, s)

MUSIC_EXTS = ['mp3', 'm4a', 'flac', 'alac', 'wav', 'opus']
MUSIC_EXT_STRIPPER = MU.file_ext_stripper(set(MUSIC_EXTS))
LEADING_DOT_STRIPPER = re.compile(r'^[\. ]*')
def parse_track_name(s: str) -> str:
    return MUSIC_EXT_STRIPPER(LEADING_DOT_STRIPPER.sub('', s))

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
        index, rest = parse_leading_digits(filename)
        if index is not None:
            track_name = parse_track_name(rest)
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
