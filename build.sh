#!/bin/sh

# It is assumed that this script is executed from the root directory
# of the Python agent source directory checked out from GIT.

# Remove results of old builds.

rm -rf build dist
rm -rf *.egg-info

# Trigger the build.

python setup.py build

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi

# Trigger creation of source distribution tarball.

python setup.py sdist

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi

# Rename the generated tar ball to match naming convention.

mv dist/newrelic-`cat VERSION`.tar.gz dist/newrelic-python-`cat VERSION`.tar.gz

# Display the results of the build.

echo
ls -l dist

exit 0
