# A set of python scripts to automatically download youtube music videos

Example input file `process_music_input.txt`:
```
# Sibelius: Lemminkäinen ∙ hr-Sinfonieorchester ∙ Jukka-Pekka Saraste
url: https://www.youtube.com/watch?v=x_vVc62BMfs
use_file_extension: .m4a
prefix: "{index_roman}. "
Xtag(artist,composer): "Jean Sibelius"
Xtag(album): "Lemminkäinen Suite"
Xtag(tracknumber): $INDEX
Xtag(tracktitle): $FILENAME_ORIG
chunk: 00:03 NEXTCHUNK Lemminkäinen und die Mädchen auf der Insel
chunk: 16:02 NEXTCHUNK Lemminkäinen in Tuonela
chunk: 30:50 NEXTCHUNK Der Schwan von Tuonela
chunk: 39:05 NEXTCHUNK Lemminkäinen zieht heimwärts
---
# Another video
url: <youtube video URL>
chunk: <start time> <end time> <chunk name, spaces permitted>
# For rest of the options, see `parse_input_file()` in `process_music.py`
```

Example usage:
```sh
$ ls
process_music.py  process_music_input.txt  my_util.py
$ python process_music.py process_music_input.txt
```
