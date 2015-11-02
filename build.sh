#!/bin/sh

# It is assumed that this script is executed from the root directory
# of the Python agent source directory checked out from GIT.

# Remove results of old builds.

rm -rf build dist
rm -rf *.egg-info

# Get the path to python2.7 version.

PYTHON27="/usr/bin/python2.7"

# Python 2.7 on the PDX Jenkins build node 'build-ubuntu1004-32' is
# in a non-standard location, so we check the NODE_LABELS env var.

if test x"$NODE_LABELS" != x""
then
    if echo $NODE_LABELS | grep -q "build-ubuntu1004-32"
    then
        PYTHON27="$HOME/python-tools/python-2.7-ucs4/bin/python2.7"
    fi
fi

echo "Using Python: $PYTHON27"

export LICENSE_REVIEWER_METAFILE_PATH=license_data

$PYTHON27 license_reviewer.py review
$PYTHON27 license_reviewer.py geninstallerdoc newrelic/LICENSE

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi

# Record build number.

if test x"$BUILD_NUMBER" != x""
then
    echo "build_number = $BUILD_NUMBER" > newrelic/build.py
fi

# Trigger the build. Only do this if working locally and not on Hudson
# as there is no need to be doing it on Hudson.

if test x"$BUILD_NUMBER" = x""
then
    python setup.py build

    STATUS=$?
    if test "$STATUS" != "0"
    then
        echo "`basename $0`: *** Error $STATUS"
        exit 1
    fi
fi

# Trigger creation of source distribution tarball.

python setup.py sdist

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi

# Display the results of the build.

echo
ls -l dist

exit 0
