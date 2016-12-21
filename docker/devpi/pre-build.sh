#!/usr/bin/env bash

OUT_DIR=docker/devpi/package-lists/
mkdir -p $OUT_DIR

EXCLUDE_ALL="mysql-connector-python"
SOURCE_ONLY="importlib==1.0.4 psycopg2cffi"
EXTRA_PACKAGES="importlib==1.0.4 ordereddict==1.1 cffi==1.9.1 httpretty==0.8.10 docutils==0.13.1 simplejson==3.3.0 pyramid==1.5b1 nose==1.3.7"

test -n "$EXCLUDE_ALL" && EXCLUDE_ALL="-e $EXCLUDE_ALL"
test -n "$SOURCE_ONLY" && SOURCE_ONLY="-s $SOURCE_ONLY"
test -n "$EXTRA_PACKAGES" && EXTRA_PACKAGES="-x $EXTRA_PACKAGES"

TOX_FILES=$(git ls-files '*tox*.ini')
$(python docker/devpi/parseconfig.py $TOX_FILES -o $OUT_DIR $EXCLUDE_ALL $SOURCE_ONLY $EXTRA_PACKAGES)
