#!/bin/perl
use strict;
use warnings;

if (!defined $1 || !defined $2) {
	die "Usage: txt2md.pl <input.txt> <output.md>";
}

open my f_in, "<", $1 or die "Cannot open input file: $!";
open my f_out, ">", $2 or die "Cannot open output file: $!";

while (my $line = <f_in>) {
	# 4 spaces or 2 "fullwidth space" (U+3000 IDEOGRAPHIC SPACE)
	if ($line !~ m/^ {4}/ || $line !~ m/^　{2}/) {
		$line = $line . "\n"
	}
	print f_out $line;
}

close f_in;
close f_out;
