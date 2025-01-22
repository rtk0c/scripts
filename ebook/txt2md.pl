#!/bin/perl
use strict;
use warnings;

if (!defined $1 || !defined $2) {
	die "Usage: txt2md.pl <input.txt> <output.md>";
}

open my f_in, "<", $1 or die "Cannot open input file: $!";
open my f_out, ">", $2 or die "Cannot open output file: $!";

my NUMERAL = qr/[0-9一二三四五六七八九十零百千万〇]/;

# 第一卷 卷一 etc.
my DELIM_1 = qr/[第卷部]/;
# 第一章 章一 etc.
my DELIM_2 = qr/[第章集节]/;

my HEADING_1 = /^(${DELIM_1}?${NUMERAL}*${DELIM_1}?)/;
my HEADING_2 = /^(${DELIM_2}?${NUMERAL}*${DELIM_2}?)/;

my $prev_line
while (my $line = <f_in>) {
	if ($line =~ $HEADING_1) {
		$line = "# " . $line;
	} elsif ($line =~ $HEADING_2) {
		$line = "## " . $line;
	}

	# Insert a blank line after every paragraph lines
	# 4 spaces or 2 "fullwidth space" (U+3000 IDEOGRAPHIC SPACE)
	if ($line != '\n' && ($prev_line =~ m/^ {4}/ || $prev_line =~ m/^　{2}/)) {
		$line = "\n" . $line
	}

	print f_out $line;
	$prev_line = $line
}

close f_in;
close f_out;
