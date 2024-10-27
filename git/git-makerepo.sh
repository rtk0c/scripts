#! /bin/bash

# Personal configuration:
# - $GIT_HOME = /srv/git
# - `git` user $HOME = /srv/git, with permissions set with g+s sticky bit
# - `git-daemon` setup to to serve /srv/git for public readonly access
# - This script is placed as /srv/git.makerepo

# Directory that git repositories are placed under
# This is intended to be set as `git` user's $HOME, so that any <repo> created by this script can be clone with `git@<host>:<repo>`
GIT_HOME=/srv/git

# Clean any .. and . from the user argument
# IMPORTANT: this is just a fool-proofing protection, to prevent accidentally litering files anywhere
# THIS IS NOT A SECURITY MEASURE
#
# Logic: since there is nothing parent of /, all .. trying to escape will be mapped back to .
# e.g. "test" -> realpath("/test") -> "test"
#      "/test" -> realpath("//test") -> "test"
#      "../test" -> realpath("/../test") -> "test"
REPO_LOCATION=$(realpath --relative-to=/ -m "/$1")
# All dir components except the actual repository
# e.g. if the user tries to run `git.makerepo Group/Subgroup/Repo`, this will be `Group/Subgroup` so we can create it
REPO_PREFIX=$(dirname "$REPO_PATH")

REPO=$GIT_HOME/$REPO_LOCATION

if [[ -d $REPO ]]; then
	echo "Something already exists at $REPO, refuse to create git repo there"
	exit -1
fi

echo "Creating git repository at $REPO"

sudo -u git mkdir -p "$GIT_HOME/$REPO_PREFIX"
sudo -u git git init --bare "$REPO"
