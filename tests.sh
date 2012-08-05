#!/bin/sh

# We first need to work out what Python installations we can use on the
# system we are running this on. On the Hudson boxes we give preference
# to our own Python installations over the system ones. If running the
# MacOS X operating system we use what ever the system provides.

PYTHON25=
PYTHON26=
PYTHON27=

export PYTHON25
export PYTHON26
export PYTHON27

ENVIRONMENTS=

# First check if we are running on the Hudson boxes and if we are look for
# our own versions.

if test x"$BUILD_NUMBER" != x""
then
    if test -x $HOME/python-tools/python-2.5-ucs4/bin/python2.5
    then
        ENVIRONMENTS="$ENVIRONMENTS,py25"
        PYTHON25="$HOME/python-tools/python-2.5-ucs4/bin/python2.5"
    fi
    if test -x $HOME/python-tools/python-2.6-ucs4/bin/python2.6
    then
        ENVIRONMENTS="$ENVIRONMENTS,py26"
        PYTHON26="$HOME/python-tools/python-2.6-ucs4/bin/python2.6"
    fi
    if test -x $HOME/python-tools/python-2.7-ucs4/bin/python2.7
    then
        ENVIRONMENTS="$ENVIRONMENTS,py27"
        PYTHON27="$HOME/python-tools/python-2.7-ucs4/bin/python2.7"
    fi
fi

# Now fallback to system provided Python installations if we haven't
# already found one of our own.

if test x"$PYTHON25" = x""
then
    if test -x /usr/bin/python2.5
    then
        ENVIRONMENTS="$ENVIRONMENTS,py25"
        PYTHON25="/usr/bin/python2.5"
    fi
fi
if test x"$PYTHON26" = x""
then
    if test -x /usr/bin/python2.6
    then
        ENVIRONMENTS="$ENVIRONMENTS,py26"
        PYTHON26="/usr/bin/python2.6"
    fi
fi
if test x"$PYTHON27" = x""
then
    if test -x /usr/bin/python2.7
    then
        ENVIRONMENTS="$ENVIRONMENTS,py27"
        PYTHON27="/usr/bin/python2.7"
    fi
fi

ENVIRONMENTS=`echo $ENVIRONMENTS | sed -e 's/^,//'`

if test x"$ENVIRONMENTS" = x""
then
    echo "No Python installations found."
    exit 1
fi

tox --help > /dev/null 2>&1

if test "$?" = "0"
then
    exec tox --notest -e $ENVIRONMENTS
else
    exec python unit-tests/run-tox.py --notest -e $ENVIRONMENTS
fi
