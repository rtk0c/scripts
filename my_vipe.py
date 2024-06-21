# A set of utilities for emulating moreutils `vipe` in your Python script.

import os
import subprocess
import re

def get_preferred_editor():
  # TODO non-unix platforms
  # Logic from moreutils vipe source code
  if ed := os.getenv('EDITOR'):
    return ed
  elif ed := os.getenv('VISUAL'):
    return ed
  elif os.path.isfile('/usr/bin/editor'):
    return '/usr/bin/editor'
  else:
    return 'vi'

def get_temp_file_path():
  # TODO non-unix platforms
  return '/tmp/myvipe-temp-file'

def vipe(initial_content):
  filepath = get_temp_file_path()

  with open(filepath, 'w') as f:
    f.write(initial_content)

  ret = subprocess.run([get_preferred_editor(), filepath]).returncode
  if ret != 0:
    return None
    #raise RuntimeError(f"Editor exited with abnormal exit-code {ret}.")

  with open(filepath, 'r') as f:
    updated_content = f.read()

  if updated_content == initial_content:
    return None
  else:
    return updated_content


def format_table_data(headers: list[str], dat: list[list[str]], tab_width=8) -> str:
  # TODO we can't really measure text width accurately here, only a best guess possible
  # leave it as assume everything is 1-cell wide (monospace ASCII), or just don't guess at all, and insert 1 tab and be done iwth it?

  # TODO allow \t characters (our delimiter) in input or user generated data

  out = []
  out.append('# ' + '\t'.join(headers))
  for row in dat:
    out.append('\t'.join(row))

  return '\n'.join(out)

def parse_table_data(content: str) -> list[list[str]]:
  TAB_DELIMIT = re.compile(r'\t+')
  return [TAB_DELIMIT.split(line) for line in content.splitlines() if not line.startswith("#") and line != '']
