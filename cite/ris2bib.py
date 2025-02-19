#!/usr/bin/python
# https://github.com/ksaaskil/ris-to-bib/blob/master/ris_to_bibtex.py
'''
Tool to change the .ris citation file format (used e.g. by Nature) to the bibtex format. Give the .ris file as input and optionally the .bib file to be used as output.

Requires also: switch.py (elegant switch-case that essentially works as if-elif-else.)

author: K. Saaskilahti, 26.3.2015; rtk0c, since 202-02-16
'''

# rtk0c: replaced with just if-elif chain
#from switch import switch
import argparse

parser=argparse.ArgumentParser()
parser.add_argument("risfile",help="The .ris file to be turned into bibtex format")
parser.add_argument("bibfile",nargs='?',help="The file to be written (optional, otherwise output written to standard output).")
args=parser.parse_args()

author_list=[]
title=None
journal=None
volume=None
year=None
month=None
startingpage=None
finalpage=None
publisher=None
doi=None
url=None

with open(args.risfile,'r') as f:
	for data in f:
		data=data.split('-',1)
		if len(data)==1:
			pass
		else:
			field=data[0].strip(' ')
			value=data[1].strip(' ').strip('\n').strip('\r')
			if field == 'AU':
				author_list.append(value)
			elif field == 'TI':
				title=value
			elif field == 'JA' or field == 'JO':
				journal=value
			elif field == 'VL':
				volume=value
			elif field == 'PY':
				year=value.rsplit('/')[0]
#				month=value.rsplit('/')[1]
			elif field == 'SP':
				startingpage=value
			elif field == 'EP':
				finalpage=value
			elif field == 'L3' or field == 'DO':
				doi=value
			elif field == 'UR':
				url = value
			elif field == 'PB':
				publisher=value


lines=[]
firstauthor=author_list[0].rsplit(',')[0].strip(' ')

lines.append('@article{'+firstauthor.lower()+year+',')

authorline=' '*4 + 'author={' + ' and '.join(author_list)+'},'
lines.append(authorline)
if title is not None:
	lines.append(' '*4 + 'title={' + title + '},')
if journal is not None:
	lines.append(' '*4 + 'journal={' + journal + '},')
if volume is not None:
	lines.append(' '*4 + 'volume={' + volume + '},')
if startingpage is not None and finalpage is not None:
	lines.append(' '*4 + 'pages={' + startingpage + '--'+finalpage+'},')
if year is not None:
	lines.append(' '*4 + 'year={' + year + '},')
if doi is not None:
	lines.append(' '*4 + 'doi={' + doi + '},')
if url is not None:
	lines.append(' '*4 + 'url={' + url + '},')
if publisher is not None:
	lines.append(' '*4 + 'publisher={' + publisher + '},')
lines.append('}\n')

if args.bibfile is not None:
	print(f"Writing output to file {args.bibfile}")
	with open(args.bibfile,'w') as f:
		f.write('\n'.join(lines))
else:
	import sys
	sys.stdout.write('\n'.join(lines))
