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
    while read PACKAGE || test -n "$PACKAGE"
    do
        test -n "$IS_PY2" && echo "$PY2_ALREADY_BUILT" | grep -q "^$PACKAGE$" && echo "$PACKAGE PY2 ALREADY BUILT: SKIPPING" && continue
        test -n "$IS_PY3" && echo "$PY3_ALREADY_BUILT" | grep -q "^$PACKAGE$" && echo "$PACKAGE PY3 ALREADY BUILT: SKIPPING" && continue
        echo "$NEEDS_WHEEL" | grep -q "^$PACKAGE$" || continue

        BUILT_WHEEL=""
        # if the wheel build fails it should be safe to ignore the failure but don't pick up wheels
        echo "$PACKAGE BUILDING WHEEL" &&
        $venv/bin/pip wheel --wheel-dir=/wheels $PACKAGE || continue

        TRUE_PACKAGE_NAME=$(echo $PACKAGE | tr -s "<=>" " " | cut -f1 -d" " | tr -s "-" "_")
        echo "$PACKAGE TRUE_PACKAGE_NAME: $TRUE_PACKAGE_NAME"

        BUILT_WHEEL=$(find /wheels -maxdepth 1 -iname "$TRUE_PACKAGE_NAME"'*' | xargs ls -1t | head -n1 || true)
        test -n "$BUILT_WHEEL" && echo "$PACKAGE BUILT WHEEL: $BUILT_WHEEL" || echo "$PACKAGE NO BUILT WHEEL DETECTED"

        test -n "$BUILT_WHEEL" &&
        echo "$BUILT_WHEEL" | grep -q "py2.py3-none-any.whl" &&
        echo "$PACKAGE DETECTED UNIVERSAL WHEEL $BUILT_WHEEL" &&
        NEEDS_WHEEL=$(echo "$NEEDS_WHEEL" | grep -v "^$PACKAGE$") && continue

        test -n "$BUILT_WHEEL" &&
        echo "$BUILT_WHEEL" | grep -q "py2-none-any.whl" &&
        echo "$PACKAGE DETECTED PY2 WHEEL $BUILT_WHEEL" &&
        PY2_ALREADY_BUILT="$PACKAGE
$PY2_ALREADY_BUILT" && continue

        test -n "$BUILT_WHEEL" &&
        echo "$BUILT_WHEEL" | grep -q "py3-none-any.whl" &&
        echo "$PACKAGE DETECTED PY3 WHEEL $BUILT_WHEEL" &&
        PY3_ALREADY_BUILT="$PACKAGE
$PY3_ALREADY_BUILT" && continue

    done < /root/package-lists/wheels-$py_name.txt
done

# Upload wheels to devpi

devpi upload --from-dir /wheels

# Make docker image somewhat slimmer

rm -rf /wheels
