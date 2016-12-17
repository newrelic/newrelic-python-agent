#!/usr/bin/env bash

OUT_DIR=docker/devpi/package-lists/
mkdir -p $OUT_DIR

EXCLUDE_ALL="mysql-connector-python"
SOURCE_ONLY=""

test -n "$EXCLUDE_ALL" && EXCLUDE_ALL="-e $EXCLUDE_ALL"
test -n "$SOURCE_ONLY" && SOURCE_ONLY="-s $SOURCE_ONLY"

TOX_FILES=$(git ls-files '*tox*.ini')
$(python docker/devpi/parseconfig.py $TOX_FILES -o $OUT_DIR $EXCLUDE_ALL $SOURCE_ONLY)
