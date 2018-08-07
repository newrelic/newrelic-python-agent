#!/usr/bin/env bash

rm -rf .asv

git clone git@source.datanerd.us:python-agent/benchmark-results.git .asv
git add -f .asv/results

cd .asv
git fetch origin gh-pages
git worktree add -B gh-pages html origin/gh-pages

cd html
git reset --hard empty
