#! /bin/bash

vipe > /tmp/process_music_input.txt
python process_music.py "$@" /tmp/process_music_input.txt 
rm /tmp/process_music_input.txt
