#!/usr/bin/env bash

set -e

git reset HEAD

cd .asv

git_remote="$(git config --get remote.origin.url)"
expected_remote="git@source.datanerd.us:python-agent/benchmark-results.git"

[[ $git_remote == $expected_remote ]] || exit 1

git add .
git commit -m "Benchmarks run by $(hostname)"
git push

cd html
git add .
git commit -m "HTML pages."
git push -f
