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

function create_venvs {
    virtualenv /venvs/py27 -p /usr/bin/python2.7
    virtualenv /venvs/py35 -p /usr/bin/python3.5
    virtualenv /venvs/py36 -p /usr/bin/python3.6
    virtualenv /venvs/py37 -p /usr/bin/python3.7
    virtualenv /venvs/py38 -p /usr/bin/python3.8
    virtualenv /venvs/py39 -p /usr/bin/python3.9
    virtualenv /venvs/pypy -p /usr/local/bin/pypy
    virtualenv /venvs/pypy3 -p /usr/local/bin/pypy3
}

create_venvs

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
rm -rf /venvs/*

create_venvs
