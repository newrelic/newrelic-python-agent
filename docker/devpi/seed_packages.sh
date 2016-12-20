#!/bin/sh

# Seed the devpi-server cache with all of the packages that the tox tests
# need. This should eliminate the need to download any packages from PyPI,
# greatly speeding up our tests.

# Seeding the cache is done by downloading all packages in a virtualenv.
# Downloading to a throwaway directory is preferable to installing and
# uninstalling, since it is faster. To make it possible to download multiple
# versions of the same package, it's necessary to delete and recreate the
# throwaway directory between installs.

set -e

# Create directory to hold package tarballs temporarily

mkdir -p /downloads
touch /root/needs-wheel.txt

for venv in $(find /venvs -maxdepth 1 -type d | grep -v "/venvs$"); do
    $venv/bin/pip install -U "pip<=9.0.1"
done

# Some packages must be installed in source format only
while read PACKAGE || test -n "$PACKAGE"
do
    echo "DOWNLOADING SOURCE: $PACKAGE"
    /venvs/py27/bin/pip download \
        -i http://localhost:3141/root/pypi/ \
        -d /downloads \
        --no-binary :all: \
        $PACKAGE

    # Clean out /downloads, so it's possible to install multiple versions
    # of the same package

    rm -rf /downloads
    mkdir -p /downloads
done < /root/package-lists/packages-source.txt

# Install most packages in python 2.7 virtualenv

while read PACKAGE || test -n "$PACKAGE"
do
    echo "DOWNLOADING PY2: $PACKAGE"
    /venvs/py27/bin/pip download \
        -i http://localhost:3141/root/pypi/ \
        -d /downloads \
        $PACKAGE

    ls /downloads/*-py2.py3-none-any.whl > /dev/null 2>&1 || echo $PACKAGE >> /root/needs-wheel.txt

    # Clean out /downloads, so it's possible to install multiple versions
    # of the same package

    rm -rf /downloads
    mkdir -p /downloads

done < /root/package-lists/packages-py2.txt

# Some packages must be installed in python 3 virtualenv

while read PACKAGE || test -n "$PACKAGE"
do
    echo "DOWNLOADING PY3: $PACKAGE"
    /venvs/py33/bin/pip download \
        -i http://localhost:3141/root/pypi/ \
        -d /downloads \
        $PACKAGE

    ls /downloads/*-py2.py3-none-any.whl > /dev/null 2>&1 || echo $PACKAGE >> /root/needs-wheel.txt

    # Make it possible to install multiple versions of the same package

    rm -rf /downloads
    mkdir -p /downloads

done < /root/package-lists/packages-py3.txt

rm -rf /downloads
