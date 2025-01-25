#! /bin/bash

if [[ "$#" -ne 2 ]]; then
	echo "Usage: txt_normalize.sh <input file> <output file>"
	exit 1
fi

inF=$1
outF=$2

encoding=$(uchardet "$inF")
echo "-- File $inF: $encoding"
if [[ "$encoding" = "UTF-8" || "$encoding" = "ASCII" ]]; then
	echo "--      skiping encoding conversion"
	cp "$inF" "$outF"
else
	echo "--      converting to UTF-8"
	iconv -f "$encoding" -t utf-8 "$inF" > "$outF"
fi
echo "--      converting line endings"
dos2unix "$outF"
