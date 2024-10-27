#! /bin/fish

argparse 'f/file=' 'o/out=' 'page-range=?' 'D/dpi=?' -- $argv

# In case the later operation failed
rm -r /tmp/rasterize-pdf-tmp 2> /dev/null
mkdir /tmp/rasterize-pdf-tmp

if not set -q $_flag_dpi
	set _flag_dpi '200'
end

if set -q $_flag_page_range
	set input_file $_flag_file
else
	set input_file "/tmp/rasterize-pdf-tmp/$_flag_file cut.pdf"
	qpdf $_flag_file --pages . $_flag_page_range -- $input_file
end

# Convert each page to a png image, with the specified DPI
pdftoppm -png -r $_flag_dpi $input_file /tmp/rasterize-pdf-tmp/pg

# Convert each image page to a pdf
magick mogrify -format pdf /tmp/rasterize-pdf-tmp/*.png
# Concat the page together
qpdf --empty --pages /tmp/rasterize-pdf-tmp/pg-*.pdf -- $_flag_out

rm -r /tmp/rasterize-pdf-tmp
