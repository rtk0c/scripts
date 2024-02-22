import sys
import os
import string
import requests
import shutil
from typing import Final, List, Set

OVERWRITE: Final[int] = 0
IGNORE: Final[int] = 1
RAISE_ERROR: Final[int] = 2

ON_EXIST_STR = ['overwrite', 'ignore', 'error']
def on_exist_tostr(n: int) -> str:
  return ON_EXIST_STR[n]

def symlink(src: os.path, dst: os.path, on_exist: int):
  for _ in range(2):
    try:
      os.symlink(src, dst)
      break
    except FileExistsError as e:
      if on_exist == OVERWRITE:
        os.remove(dst)
      elif on_exist == IGNORE:
        break
      elif on_exist == RAISE_ERROR:
        raise e

def write_file(filepath: os.path, content: str, on_exist: int = OVERWRITE, permissions: int = -1):
  """
  if permissions == -1:
    if on_exist == IGNORE and os.path.isfile(filepath):
      return

    with open(filepath, 'x' if on_exist == RAISE_ERROR else 'w') as f:
      f.write(content)
  else:
    # https://stackoverflow.com/a/45368120
    fd = os.open(
      path=filepath,
      flags=os.O_WRONLY if on_exist != OVERWRITE else os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
      mode=permissions,
    )
    if fd == -1:
      if on_exist == RAISE_ERROR:
        raise FileExistsError(f"{filepath} already exists.")
      elif on_exist == IGNORE:
        return
      else:
        raise RuntimeError('Unexpected codepath taken, report bug.')
    # We don't need 'x' exclusive write mode here, since os.open and the branch above takes care of that
    with open(fd, 'w') as f:
      f.write(content)
  """
  # I give up, I'll just live with the TOCTOU
  # Surely this won't matter for some utility scripts, right?

  if on_exist == IGNORE and os.path.isfile(filepath):
    return

  with open(filepath, 'x' if on_exist == RAISE_ERROR else 'w') as f:
    f.write(content)

  if permissions != -1:
    os.chmod(filepath, permissions)

def download_file_and_save(url: str, out: os.path):
  # https://stackoverflow.com/a/39217788
  with requests.get(url, stream=True) as r:
    r.raise_for_status()
    with open(out, 'wb') as f:
      shutil.copyfileobj(r.raw, f)

# https://stackoverflow.com/a/3041990
def query_yes_no(question, default="yes"):
  """Ask a yes/no question via raw_input() and return their answer.

  "question" is a string that is presented to the user.
  "default" is the presumed answer if the user just hits <Enter>.
      It must be "yes" (the default), "no" or None (meaning
      an answer is required of the user).

  The "answer" return value is True for "yes" or False for "no".
  """
  valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
  if default is None:
    prompt = " [y/n] "
  elif default == "yes":
    prompt = " [Y/n] "
  elif default == "no":
    prompt = " [y/N] "
  else:
    raise ValueError("invalid default answer: '%s'" % default)

  while True:
    sys.stdout.write(question + prompt)
    choice = input().lower()
    if default is not None and choice == "":
      return valid[default]
    elif choice in valid:
      return valid[choice]
    else:
      sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

# https://gist.github.com/seanh/93666
def format_filename(s: str, keep_spaces: bool=True) -> str:
  """Take a string and return a valid filename constructed from the string.
Uses a whitelist approach: any characters not present in valid_chars are
removed. Also spaces are replaced with underscores.

Note: this method may produce invalid filenames such as ``, `.` or `..`
When I use this method I prepend a date string like '2009_01_15_19_46_32_'
and append a file extension like '.txt', so I avoid the potential of using
an invalid filename.

"""
  valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
  filename = ''.join(c for c in s if c in valid_chars)
  if not keep_spaces:
    filename = filename.replace(' ','_')
  return filename

def format_filename_lean(s: str) -> str:
  # Replace ASCII slashes (which Linux rejects as filename) with U+2044 FRACTION SLASH
  # TODO handle windows and macos
  return s.replace('/', '⁄')

# This is not 100% exhausive to the URL, but it's good enough for this script, probably
def get_id_from_ytb_url(ytb_url: str) -> str:
  prefix = 'v='
  prefix_idx = ytb_url.find(prefix)
  if prefix_idx == -1:
    raise RuntimeError(f'Unable to find ID from Youtube URL {ytb_url}')

  # First '&' after the video argument
  suffix_idx = ytb_url.find('&', prefix_idx)
  # If another argument is not found, go all the way until the end
  if suffix_idx == -1:
    suffix_idx = None

  return ytb_url[(prefix_idx + len(prefix)):suffix_idx]

def strparse_hms_to_seconds(elem: str) -> int:
  t = elem.split(':')
  if len(t) == 3:
    return int(t[0]) * 60 * 60 + int(t[1]) * 60 + float(t[2])
  elif len(t) == 2:
    return int(t[0]) * 60 + float(t[1])
  elif len(t) == 1:
    return float(t[0])
  else:
    raise RuntimeError("Unknown time format")

def strformat_seconds(time: int | float) -> str:
  hrs = int(time // 3600)
  mins = int(time // 60)
  sec = time % 60
  # Convert to int if possible, so that we don't get the annoying 00:00:05.0
  sec = int(sec) if (isinstance(sec, float) and sec.is_integer()) else sec
  return f'{hrs:02}:{mins:02}:{sec:02}'

# https://stackoverflow.com/a/47713392
ROMAN_ASCII = [
  (1000, "M"),
  ( 900, "CM"),
  ( 500, "D"),
  ( 400, "CD"),
  ( 100, "C"),
  (  90, "XC"),
  (  50, "L"),
  (  40, "XL"),
  (  10, "X"),
  (   9, "IX"),
  (   5, "V"),
  (   4, "IV"),
  (   1, "I"),
]
def int_to_roman_ascii(number: int) -> str:
  result = ""
  for (arabic, roman) in ROMAN_ASCII:
    (factor, number) = divmod(number, arabic)
    result += roman * factor
  return result

# TODO support large numbers
ROMAN_UNICODE_UPPER = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ", "Ⅺ", "Ⅻ"]
def int_to_roman_unicode(number: int) -> str:
  if number >= len(ROMAN_UNICODE_UPPER):
    return "<UNKNOWN>"
  return ROMAN_UNICODE_UPPER[number - 1]

def file_ext_stripper(exts: Set[str]):
  def stripper(s: str) -> str:
    dot_idx = s.rfind('.')
    if dot_idx == -1:
      return s
    suffix = s[(dot_idx+1):]
    if suffix in exts:
      return s[:dot_idx]
    else:
      return s
  return stripper
