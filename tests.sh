#!/bin/sh

# This script searches for python executables for each version of python that
# we test. If an appropriate python executable is detected, we automatically
# add it to the list of python versions to run unit tests against.
#
# Because of what appears to be a bug in tox and its understanding of
# what the current working directory is when using a non default test
# environment, we use the default test environments and run tests twice.
# The first time as pure Python and the second with extensions enabled.

py26=$(which python2.6)
py27=$(which python2.7)
py33=$(which python3.3)
py34=$(which python3.4)
py35=$(which python3.5)
py36=$(which python3.6)
pypy=$(which pypy)
pypy3=$(which pypy3)

ENVIRONMENTS=

if test x"$1" = x""
then
    for e in py26 py27 py33 py34 py35 py36 pypy pypy3
    do
        eval py_exe="\$$e"
        if test x"$py_exe" != x""
        then
            ENVIRONMENTS="$ENVIRONMENTS,$e"
        fi
    done
    ENVIRONMENTS=`echo $ENVIRONMENTS | sed -e 's/^,//'`
    if test x"$ENVIRONMENTS" = x""
    then
        echo "No Python installations found."
        exit 1
    fi
else
    # Don't validate target environments. Trust the user.
    ENVIRONMENTS=$1
    shift
fi

tox --help > /dev/null 2>&1
if test "$?" != "0"
then
    echo "Please install tox using 'pip install tox'"
    exit 1
fi

if test x"$*" = x""
then
    TOX_TESTS=""

    TOX_TESTS="$TOX_TESTS newrelic/common/tests"
    TOX_TESTS="$TOX_TESTS newrelic/core/tests"
    TOX_TESTS="$TOX_TESTS newrelic/api/tests"
    TOX_TESTS="$TOX_TESTS newrelic/tests"

    NEW_RELIC_ADMIN_TESTS=true
else
    TOX_TESTS="$*"

    NEW_RELIC_ADMIN_TESTS=false
fi

echo "Running tests with Pure Python version of agent!"

if test x"$NEW_RELIC_ADMIN_TESTS" = x"true"
then
    NEW_RELIC_EXTENSIONS=false tox -v -e $ENVIRONMENTS -c tox-admin.ini
fi

NEW_RELIC_EXTENSIONS=false tox -v -e $ENVIRONMENTS -c tox.ini $TOX_TESTS

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi

echo "Running tests with mixed binary version of agent!"

if test x"$NEW_RELIC_ADMIN_TESTS" = x"true"
then
    NEW_RELIC_EXTENSIONS=true tox -v -e $ENVIRONMENTS -c tox-admin.ini
fi

NEW_RELIC_EXTENSIONS=true tox -v -e $ENVIRONMENTS -c tox.ini $TOX_TESTS

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi
