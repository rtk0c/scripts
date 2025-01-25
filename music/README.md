# Music Tools

Set of scripts for managing a local music library.

# id3_autotag.py

Automatically parse author, title, and tracknumber from file names, and apply them as id3 tags.

# id3_batchedit.py

Batch edit any id3 tags in a text editor.

# process_music.py

Script designed for archiving classic music concerts, where multiple pieces are recorded into a single video, often surrounded by certain noises (such as programme announcers and claps). If you want to see it in action, go straight to the [demos](#demonstration).

## Functionality
- Download & extract the audio track of some hosted media, e.g. a Youtube video, or something on Bilibili
- Split the audio track into pieces, according to a timestamp list.
  - I tend to go to the comment section to see if anybody has posted movements times. If not, I will use some well-known recording to estimate where each of the movements end and just compile one myself.
- ID3 tag each track
  - Supports any ID3 tag. I tend to provide album as the piece, artist as the performers, composer as the actual composer.
- Organize into folders by the artist and the album tag (if provided)

## Demonstration
Suppose you want to archive https://www.youtube.com/watch?v=JGBZIfaxfrM, right now. It is 2024 and who uses audio file tags anymore? The Youtube video helpfully has builtin chapters (the segments on the video player timeline). When can write this in a file, let's call it `input.txt`:
```
url: https://www.youtube.com/watch?v=JGBZIfaxfrM
chunk_by_chapter: true
```
and then run `python process_music.py input.txt`. It will parse the metadata, and prompt you to confirm that it is in fact the right video and the right chunks. A *chunk* is a subsection of the whole audio track the script will cut out, and store as a separate audio file.

This:
- Puts all output files in `/tmp/00-myscript-process_music/`, you can change it with the `--work-dir` flag. 
- Pick the audio format with yt-dlp's `bestaudio` option. On Youtube, for the majority of videos, is encoded in Opus, you can change it with the `--format` flag. (NOTE: Youtube stores opus audio as a .webm file, this script handles it specially to remux it as a .ogg file to make foobar2000 happy).

Copy the files you want out of here, to iTunes or whatever. Then, you can either delete the folder manually at any time, or run `python process_music.py -C` to clear everything inside. Run `python process_music.py` to clear only the chunks.

Manually spelling out each chunk, the above is equivalent to:
```
url: https://www.youtube.com/watch?v=JGBZIfaxfrM
chunk: 00:00 NEXTCHUNK "Moderato"
chunk: 10:38 NEXTCHUNK "Adagio"
chunk: 18:42 NEXTCHUNK "Finale, Allegro molto"
```

Breaking it down:
- The `url` specifies the thing to download.
- Each `chunk` specifies a thing that gets cut out from the whole track. After the colon, it takes 3 "arguments" separated by a space
  - First 2 are the begin time and end time
  - First 2 written as either (1) a timestamp as in `[hh]:mm:ss` with leading-zero ommitable, or (2) a few special macro values: `VIDEOLENGTH` for the total runtime of the video, so 28:08 here; `NEXTCHUNK` for the begin time of the chunk after it, or `VIDEOLENGTH` if this is the last chunk. They **CANNOT** be quoted.
  - Last 1 is the filename the chunk will be stored as. It is *optionally quoted* (and if unquoted, *internal spaces are allowed*, but any trailing spaces will be trimmed).
  - File extension is automatically assigned based on the downloaded audio format.

Now for a more complicated situation. Suppose you want to archive this performance: https://www.youtube.com/watch?v=Q4NC4E5RXik. It is a piece of Herlioz, *Harold en Italie* (or Harold in Italy, the english name).
```
# Berlioz: Harold en Italie ∙ hr-Sinfonieorchester ∙ Antoine Tamestit ∙ Eliahu Inbal
url: https://www.youtube.com/watch?v=Q4NC4E5RXik
prefix: "{index}. "
Xtag(artist,composer): "Hector Berlioz"
Xtag(album): "Harold en Italie (hr-Sinfonieorchester ∙ Antoine Tamestit ∙ Eliahu Inbal)"
Xtag(tracknumber): $INDEX
Xtag(tracktitle): $CHUNK_NAME
# Put the programatic title in comments just to stop the filename/tracktitle getting out of hand
chunk: 00:35 NEXTCHUNK Adagio – Allegro – Tempo I
^tag(comment): "Harold aux montagnes. Scènes de mélancolie, de bonheur, et de joie."
chunk: 16:00 NEXTCHUNK Allegretto
^tag(comment): "Marche de pèlerins chantant la prière du soir."
chunk: 24:12 NEXTCHUNK Allegro assai – Allegretto
^tag(comment): "Sérénade d'un montagnard des Abruzzes à sa maîtresse."
chunk: 30:53 NEXTCHUNK Allegro frenetico – Adagio – Allegro. Tempo I
^tag(comment): "Orgie des brigands. Souvenirs des scènes précédentes."
```
Breaking it down:
- `prefix` specifies the filename prefix to each chunk. It supports a few macros based on python format-strings. `{index}` is a 1-based index of the chunk. `{index_roman}` is the same index, but spelled as a Roman numeral.
- `tag` specifies the ID3 tags to apply to the chunks
  - 3 possible prefixes, `X` for all chunks, `^` for the chunk right before this tag directive, `S` for all chunks before this tag directive until the previous tag directive
  - In the parenthesis is a comma-separated list of ID3 tag names. All tags listed inside will be assigned the same value. TODO add list of all supported tag names.
  - The value specified after the colon is *optionally quoted*.
- Lines starting with `#` are comments
- The chunk names are not quoted here to show it is accepted
