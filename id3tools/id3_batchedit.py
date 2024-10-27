#! /usr/bin/python

import os
import sys
import re
import itertools
import argparse
import music_tag

import my_vipe as MVipe

# get list of files from stdin
# write them into a table as a text file, with columns filled with current tag values (specified with --tags=xxx,yyy,zzz)
# when user closes file, read text back and parse them
# apply the new values

parser = argparse.ArgumentParser(prog='id3_batchedit.py')
parser.add_argument('tags')
args = parser.parse_args()

VALID_ID3_TAG_LIST = ['tracktitle', 'tracknumber', 'artist', 'albumartist', 'composer', 'album', 'comment']
VALID_ID3_TAGS = set(VALID_ID3_TAG_LIST)

def validate_tags(tags):
  has_invalid_tags = False
  for tag in tags:
    if tag not in VALID_ID3_TAGS:
      print(f"Error: invalid tag '{tag}'")
      has_invalid_tags = True
  if has_invalid_tags:
    print('Use one of the following tags: ' + ', '.join(VALID_ID3_TAGS))
    return False
  else:
    return True

tags_name = args.tags.split(',')
if not validate_tags(tags_name):
  sys.exit(-1)

files_path = [f.strip() for f in sys.stdin]
files_tags = [music_tag.load_file(path) for path in files_path]

original_rows = itertools.chain.from_iterable([
  (f"# File: {file_path}",
   [str(idx)] + [str(file_tags[tag_name]) for tag_name in tags_name])
  for idx, (file_tags, file_path) in enumerate(zip(files_tags, files_path))])

if vipe_res := MVipe.vipe(MVipe.format_table_data(['ID'] + tags_name, original_rows), syntax_hint='csv'):
  directives, edited_rows = MVipe.parse_table_data(vipe_res, advanced=True)

  constants = {}
  for d in directives:
    var_name, value = d.split('=', maxcount=1)
    constants[var_name.strip()] = value.strip()

  for idx, row in enumerate(edited_rows):
    f = files_tags[int(row[0])]

    for tag, value in zip(tags_name, row[1:]):
      if tag == 'tracknumber':
        if value == 'i':
          value = idx
        else:
          value = int(value) + 1

      if value == '*':
        value = constants[tag]

      f[tag] = value

    f.save()
else:
  print("Nothing changed. Exiting.")
