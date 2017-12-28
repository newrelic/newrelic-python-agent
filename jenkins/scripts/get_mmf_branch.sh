#!/bin/bash

# The purpose of this script is to determine the name of the MMF branch to test
# and place that into `jenkins/environ`.
#
# The `jenkins/environ` file will be loaded into all test subjobs. Entries in
# this file are of the form `KEY=value`, one per line.

# fetch all refs from origin so we can get a complete list of branches in the
# next command
git fetch origin > /dev/null 2>&1

# search through all branches for most recently committed
mmf_branch=$(git for-each-ref --sort=-committerdate --format=%\(refname\) \
    --count=1 refs/remotes/origin/mmf-*)

echo Will run tests on MMF branch: $mmf_branch
echo GIT_REPOSITORY_BRANCH=$mmf_branch > jenkins/environ
