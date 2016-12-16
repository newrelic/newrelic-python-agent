#!/usr/bin/env bash

OUT_DIR=docker/devpi/package-lists/
mkdir -p $OUT_DIR

EXCLUDE_ALL="mysql-connector-python"

TOX_FILES=$(git ls-files '*tox*.ini')
$(python docker/devpi/parseconfig.py $TOX_FILES -o $OUT_DIR -e $EXCLUDE_ALL)
