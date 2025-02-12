#!/bin/perl
use strict;
use warnings;

use constant {
	HEADING_DELIMITED => 'delimited',
	HEADING_CAPS => 'caps',
	HEADING_NUMERAL => 'num',
};

use Getopt::Long;

GetOptions(
	'help|?' => \(my $print_help = 0),
	'parse-heading=s' => \(my $heading_mode = HEADING_DELIMITED),
);

if ($print_help || !defined $ARGV[0] || !defined $ARGV[1]) {
	die <<'END_TXT';
Usage: txt2md.pl <input.txt> <output.md> [flags]

-h, -?                  Display this message
--parse-headings, -p    Heading formatting, available 'delimited', 'caps', 'num'
END_TXT
}

open my $f_in, "<", $ARGV[0] or die "Cannot open input file: $!";
open my $f_out, ">", $ARGV[1] or die "Cannot open output file: $!";

my $H1 = 0;
my $H2 = 0;
if ($heading_mode eq HEADING_DELIMITED) {
	my $DELIM_1 = qr/[第卷部]/;
	my $DELIM_2 = qr/[第章集节]/;

	# 第一卷 卷一 etc.
	$H1 = qr/^(${DELIM_1}[0-9一二三四五六七八九十零百千万〇]*${DELIM_1}?)/;
	# 第一章 章一 etc.
	$H2 = qr/^(${DELIM_2}[0-9一二三四五六七八九十零百千万〇]*${DELIM_2}?)/;
} elsif ($heading_mode eq HEADING_CAPS) {
	$H1 = qr/^[一二三四五六七八九十零百千万〇]+/;
} elsif ($heading_mode eq HEADING_NUMERAL) {
	$H1 = qr/^(\d+)/;
} else {
	die "Unkown heading mode '$heading_mode'";
}

my $prev_line = "";
while (my $line = <$f_in>) {
	# Insert a blank line after every paragraph lines
	# = 4 spaces or 2 "fullwidth space" (U+3000 IDEOGRAPHIC SPACE)
	if ($line ne "\n" && ($prev_line =~ /^(?: {4}|　{2})/)) {
		print $f_out "\n";
	}

	if ($H1 != 0 && $line =~ $H1) {
		print $f_out ("# " . $line);
	} elsif ($H2 != 0 && $line =~ $H2) {
		print $f_out ("## " . $line);
	} else {
		print $f_out $line;
	}

	$prev_line = $line;
}

close $f_in;
close $f_out;
