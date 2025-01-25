#!/bin/perl
use strict;
use warnings;

if (!defined $ARGV[0] || !defined $ARGV[1]) {
	die "Usage: txt2md.pl <input.txt> <output.md>";
}

open my $f_in, "<", $ARGV[0] or die "Cannot open input file: $!";
open my $f_out, ">", $ARGV[1] or die "Cannot open output file: $!";

my $NUMERAL = qr/[0-9一二三四五六七八九十零百千万〇]/;

# 第一卷 卷一 etc.
my $DELIM_1 = qr/[第卷部]/;
# 第一章 章一 etc.
my $DELIM_2 = qr/[第章集节]/;

my $HEADING_1 = qr/^(${DELIM_1}${NUMERAL}*${DELIM_1}?)/;
my $HEADING_2 = qr/^(${DELIM_2}${NUMERAL}*${DELIM_2}?)/;

my $prev_line = "";
while (my $line = <$f_in>) {
	# Insert a blank line after every paragraph lines
	# = 4 spaces or 2 "fullwidth space" (U+3000 IDEOGRAPHIC SPACE)
	if ($line ne "\n" && ($prev_line =~ /^(?: {4}|　{2})/)) {
		print $f_out "\n";
	}

	if ($line =~ $HEADING_1) {
		print $f_out ("# " . $line);
	} elsif ($line =~ $HEADING_2) {
		print $f_out ("## " . $line);
	} else {
		print $f_out $line;
	}

	$prev_line = $line;
}

close $f_in;
close $f_out;
