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

CONFIGS="PY2_py27_/root/package-lists/packages-py2.txt PY3_py33_/root/package-lists/packages-py3.txt"

for config in $CONFIGS
do
    PY_NAME=$(echo $config | cut -f1 -d"_")
    PY_FULL=$(echo $config | cut -f2 -d"_")
    PKG_FILE=$(echo $config | cut -f3 -d"_")
    echo "PY_NAME: $PY_NAME"
    echo "PY_FULL: $PY_FULL"
    echo "PKG_FILE: $PKG_FILE"
    while read PACKAGE || test -n "$PACKAGE"
    do
        echo "DOWNLOADING $PY_NAME: $PACKAGE"
        /venvs/$PY_FULL/bin/pip download \
            -i http://localhost:3141/root/pypi/ \
            -d /downloads \
            $PACKAGE

        TRUE_PACKAGE_NAME=$(echo $PACKAGE | tr -s "<=>" " " | cut -f1 -d" " | tr -s "-" "_")
        echo "$PACKAGE TRUE_PACKAGE_NAME: $TRUE_PACKAGE_NAME"

        UNIVERSAL_WHEEL=$(find /downloads -maxdepth 1 -iname "$TRUE_PACKAGE_NAME"'*' | grep "py2.py3-none-any.whl" || true)

        test -n "$UNIVERSAL_WHEEL" && echo "$PACKAGE UNIVERSAL_WHEEL: $UNIVERSAL_WHEEL"
        test -n "$UNIVERSAL_WHEEL" || echo "NEEDS WHEEL: $PACKAGE"
        test -n "$UNIVERSAL_WHEEL" || echo $PACKAGE >> /root/needs-wheel.txt

        # Clean out /downloads, so it's possible to install multiple versions
        # of the same package

        rm -rf /downloads
        mkdir -p /downloads

    done < $PKG_FILE
done

rm -rf /downloads
