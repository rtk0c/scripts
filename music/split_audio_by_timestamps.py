#! /usr/bin/python

import ffmpeg
from sys import argv

""" split_audio_by_timestamps `audio file` `time listing`

	`audio file` is any file known by local FFmpeg
	`time listing` is a file containing multiple lines of format:
		`start time` `end time` output name 

	times can be either HH:MM:SS, MM::SS, or S*
"""

_in_file = argv[1]

def make_time(elem):
	# allow user to enter times on CLI
	t = elem.split(':')
	if len(t) == 3:
		return int(t[0]) * 60 * 60 + int(t[1]) * 60 + float(t[2])
	elif len(t) == 2:
		return int(t[0]) * 60 + int(t[1])
	elif len(t) == 1:
		return float(t[0])
	else:
		raise RuntimeError("Unknown time format")

def collect_from_file():
	"""user can save times in a file, with start and end time on a line"""

	time_pairs = []
	with open(argv[2]) as in_times:
		for l, line in enumerate(in_times):
			# NOTE: 2 indicates consume at most 2 delimiters, i.e. create 2 + 1 = 3 segments
			tp = line.strip().split(" ", 2)
			begin_time = make_time(tp[0])
			end_time = make_time(tp[1])
			# if no name given, append line count
			if len(tp) < 3:
				out_filename = str(l) + '.wav'
			else:
				out_filename = tp[2]
			time_pairs.append({
				'begin_time': begin_time,
				'duration': end_time - begin_time,
				'out_filename': out_filename
			})
	return time_pairs

for i, config in enumerate(collect_from_file()):
	# open a file, from `ss`, for duration `t`
	stream = ffmpeg.input(_in_file, ss=config['begin_time'], t=config['duration'])
	# output to named file
	stream = ffmpeg.output(stream, config['out_filename'], vcodec="copy", acodec="copy")
	# this was to make trial and error easier
	stream = ffmpeg.overwrite_output(stream)

	# and actually run
	ffmpeg.run(stream)
