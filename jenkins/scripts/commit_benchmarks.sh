#!/usr/bin/env bash

cd .asv

git add .
git commit -m "Benchmarks run by $(hostname)"
git push
