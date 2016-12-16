#!/bin/sh

# Build wheels for each package for all python version

set -e

DEVPI_SERVER=http://localhost:3141

echo
echo "Creating devpi user and index."
echo

# Connect to the devpi server

devpi use $DEVPI_SERVER

# Create a user

devpi user -c packnsend password=python_agent

# Login as user

devpi login packnsend --password python_agent

# Create the index

devpi index -c packnsend/testing

# Use the index

devpi use packnsend/testing

echo
echo "Building wheels"
echo

# Create directory for wheels

mkdir -p /wheels

# Use devpi cache when building wheels

export PIP_INDEX_URL=$DEVPI_SERVER/root/pypi/+simple/

# Treat mysql-connector-python special, since it's externally hosted

MYQL_CONNECTOR_URL='http://cdn.mysql.com/Downloads/Connector-Python/mysql-connector-python-2.0.4.zip#md5=3df394d89300db95163f17c843ef49df'

# Variable containing packages that need wheels
NEEDS_WHEEL="$(cat /root/needs-wheel.txt)"
PY2_ALREADY_BUILT=""
PY3_ALREADY_BUILT=""

## Install wheel in all virtualenvs
#
for venv in $(find /venvs -maxdepth 1 -type d | grep -v "/venvs$"); do
    py_name=$(echo "$venv" | cut -f3 -d"/")
    IS_PY2="$(echo "$py_name" | grep "^py2" || true)"
    IS_PY3="$(echo "$py_name" | grep "^py3" || true)"

    $venv/bin/pip install wheel
    $venv/bin/pip wheel --wheel-dir=/wheels $MYQL_CONNECTOR_URL
    while read PACKAGE
    do
        test -n "$IS_PY2" && echo "$PY2_ALREADY_BUILT" | grep -q "^$PACKAGE$" && continue
        test -n "$IS_PY3" && echo "$PY3_ALREADY_BUILT" | grep -q "^$PACKAGE$" && continue

        LAST_BUILT_WHEEL=""
        # if the wheel build fails it should be safe to ignore the failure
        echo "$NEEDS_WHEEL" | grep -q "^$PACKAGE$" &&
            $venv/bin/pip wheel --wheel-dir=/wheels $PACKAGE &&
            LAST_BUILT_WHEEL=$(ls -lt /wheels | tail -n+2 | head -n1) || true

        test -n "$LAST_BUILT_WHEEL" &&
        echo "$LAST_BUILT_WHEEL" | grep -q "py2.py3-none-any.whl" &&
        NEEDS_WHEEL=$(echo "$NEEDS_WHEEL" | grep -v "^$PACKAGE$")

        test -n "$LAST_BUILT_WHEEL" &&
        echo "$LAST_BUILT_WHEEL" | grep -q "py2-none-any.whl" &&
        PY2_ALREADY_BUILT="$PACKAGE
$PY2_ALREADY_BUILT"

        test -n "$LAST_BUILT_WHEEL" &&
        echo "$LAST_BUILT_WHEEL" | grep -q "py3-none-any.whl" &&
        PY3_ALREADY_BUILT="$PACKAGE
$PY3_ALREADY_BUILT"

    done < /root/package-lists/wheels-$py_name.txt
done

# Upload wheels to devpi

devpi upload --from-dir /wheels

# Remove the pytest wheel, since it doesn't install the py.test script in a
# bin directory. Tests can't run, if tox can't find py.test!

[ -e /wheels/pytest* ] && devpi remove -y pytest

# Remove the WebTest wheel, since it uses orderereddict, which is a separate
# package in Python 2.6, and installing the WebTest wheel in 2.6 doesn't
# install ordereddict.

[ -e /wheels/WebTest* ] && devpi remove -y WebTest

# Make docker image somewhat slimmer

rm -rf /wheels
