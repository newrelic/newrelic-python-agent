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

# Install most packages in python 2.7 virtualenv

while read PACKAGE
do
    /venvs/py27/bin/pip install \
        -i http://localhost:3141/root/pypi/ \
        --download /downloads \
        -U $PACKAGE

    ls /downloads/*-py2.py3-none-any.whl > /dev/null 2>&1 || echo $PACKAGE >> /root/needs-wheel.txt

    # Clean out /downloads, so it's possible to install multiple versions
    # of the same package

    rm -rf /downloads
    mkdir -p /downloads

done < /root/package-lists/packages-py2.txt

# Some packages must be installed in python 3 virtualenv

while read PACKAGE
do
    /venvs/py33/bin/pip install \
        -i http://localhost:3141/root/pypi/ \
        --download /downloads \
        -U $PACKAGE

    ls /downloads/*-py2.py3-none-any.whl > /dev/null 2>&1 || echo $PACKAGE >> /root/needs-wheel.txt

    # Make it possible to install multiple versions of the same package

    rm -rf /downloads
    mkdir -p /downloads

done < /root/package-lists/packages-py3.txt

rm -rf /downloads
