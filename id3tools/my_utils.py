from typing import Set

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
