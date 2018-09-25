#!/usr/bin/env bash

set -e

find . -user root -type f | xargs rm -f
find . -user root -type d | xargs rm -rf
