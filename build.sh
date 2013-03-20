#!/bin/sh

# It is assumed that this script is executed from the root directory
# of the Python agent source directory checked out from GIT.

# Remove results of old builds.

rm -rf build dist
rm -rf *.egg-info


# Get the path to python2.7 version.
# license_reviewer.py

if test x"$BUILD_NUMBER" != x""
then
    PYTHON27="$HOME/python-tools/python-2.7-ucs4/bin/python2.7"
else
    PYTHON27="/usr/bin/python2.7"
fi

export LICENSE_REVIEWER_METAFILE_PATH=license_data

$PYTHON27 license_reviewer.py review

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
