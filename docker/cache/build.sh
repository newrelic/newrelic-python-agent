#!/usr/bin/env bash

# Seed the pip cache with all of the packages that the tox tests
# need. This should eliminate the need to download any packages from PyPI,
# greatly speeding up our tests.

# Seeding the cache is done by downloading all packages in a virtualenv.
# Downloading to a throwaway directory is preferable to installing and
# uninstalling, since it is faster. To make it possible to download multiple
# versions of the same package, it's necessary to delete and recreate the
# throwaway directory between installs.

set -e

for venv in $(find /venvs -maxdepth 1 -type d | grep -v "/venvs$"); do
    $venv/bin/pip install -U "pip<=9.0.1"
    $venv/bin/pip install -U "wheel<0.30.0"
done

for PY_FULL in $(ls -1 /venvs | grep -v "^pypy")
do
    echo "PY_FULL: $PY_FULL"
    while read PACKAGE || test -n "$PACKAGE"
    do
        # Some packages must be installed in source format only
        echo "$PY_FULL: $PACKAGE downloading"
        /venvs/$PY_FULL/bin/pip download \
            -d /downloads \
            --cache-dir=/cache \
            --no-binary :all: \
            $PACKAGE ||
        echo "$PY_FULL: $PACKAGE download failed -- ignoring"

        # Clean out /downloads, so it's possible to install multiple versions
        # of the same package

        rm -rf /downloads/*
    done < /home/guest/package-lists/packages-source.txt

    while read PACKAGE || test -n "$PACKAGE"
    do
        echo "$PY_FULL: $PACKAGE building"
        /venvs/$PY_FULL/bin/pip install -U \
            --cache-dir=/cache \
            $PACKAGE ||
        echo "$PY_FULL: $PACKAGE failed to build -- ignoring"

    done < /home/guest/package-lists/packages-compiled.txt
done

rm -rf /downloads/*
