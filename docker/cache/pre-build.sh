#!/usr/bin/env bash

set -e

BASE_DIR=$(dirname $0)
OUT_DIR=$BASE_DIR/package-lists/
echo "OUT_DIR: $OUT_DIR"
mkdir -p $OUT_DIR
rm -rf $OUT_DIR/*

EXCLUDE_ALL="
    mysql-connector-python"
SOURCE_ONLY="
    psycopg2cffi"
EXTRA_PACKAGES=""

if [[ -f tests/base_requirements.txt ]]
then
    EXTRA_PACKAGES="$EXTRA_PACKAGES $(cat tests/base_requirements.txt)"
fi

test -n "$EXCLUDE_ALL" && EXCLUDE_ALL="-e $EXCLUDE_ALL"
test -n "$SOURCE_ONLY" && SOURCE_ONLY="-s $SOURCE_ONLY"
test -n "$EXTRA_PACKAGES" && EXTRA_PACKAGES="-x $EXTRA_PACKAGES"

TOX_FILES="$(git ls-files '*tox*.ini')"
python $BASE_DIR/parseconfig.py \
    $TOX_FILES \
    -o $OUT_DIR \
    $EXCLUDE_ALL \
    $SOURCE_ONLY \
    $EXTRA_PACKAGES
