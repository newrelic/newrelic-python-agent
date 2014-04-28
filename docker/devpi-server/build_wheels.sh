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

# Install wheel in all virtualenvs

/venvs/py26/bin/pip install wheel
/venvs/py27/bin/pip install wheel
/venvs/py33/bin/pip install wheel
/venvs/pypy/bin/pip install wheel

# Create directory for wheels

mkdir -p /wheels

# Use devpi cache when building wheels

export PIP_INDEX_URL=$DEVPI_SERVER/root/pypi/+simple/

echo
echo "Building Python 2.6 wheels"
echo

while read PACKAGE
do
    /venvs/py26/bin/pip wheel --wheel-dir=/wheels $PACKAGE
done < /root/package-lists/wheels-py26.txt

echo
echo "Building Python 2.7 wheels"
echo

while read PACKAGE
do
    /venvs/py27/bin/pip wheel --wheel-dir=/wheels $PACKAGE
done < /root/package-lists/wheels-py27.txt

echo
echo "Building Python 3.3 wheels"
echo

while read PACKAGE
do
    /venvs/py33/bin/pip wheel --wheel-dir=/wheels $PACKAGE
done < /root/package-lists/wheels-py33.txt

echo
echo "Building PyPy wheels"
echo

while read PACKAGE
do
    /venvs/pypy/bin/pip wheel --wheel-dir=/wheels $PACKAGE
done < /root/package-lists/wheels-pypy.txt

# Upload wheels to devpi

devpi upload --from-dir /wheels

# Remove the pytest wheel, since it doesn't install the py.test script in a
# bin directory. Tests can't run, if tox can't find py.test!

devpi remove -y pytest

# Remove the WebTest wheel, since it uses orderereddict, which is a separate package
# in Python 2.6, and installing the WebTest wheel in 2.6 doesn't install ordereddict.

devpi remove -y WebTest

# Make docker image somewhat slimmer

rm -rf /wheels
