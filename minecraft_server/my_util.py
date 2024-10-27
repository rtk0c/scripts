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
