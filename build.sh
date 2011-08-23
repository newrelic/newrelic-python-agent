#!/bin/sh

# It is assumed that this script is executed from the root directory
# of the Python agent source directory checked out from GIT. This should
# be the parent directory of where this script is held in the source
# tree.

# If the BUILD_NUMBER environment variable is set, assume we are running
# under Hudson build server.

if test x"$BUILD_NUMBER" = x""
then
    TOOLSDIR=python-tools/parts
else
    TOOLSDIR=$HOME/python-tools
fi

# Work out what platform we are and what Python versions/variants we use
# to do the build of the package. These should be one of the Python
# versions/variants that have been installed using install scripts in
# 'python-tools' directory. Specifically those listed in the 'parts'
# variable in the 'buildout' section of the platform specific build
# configuration files in the 'python-tools' directory.

PLATFORM=`./config.guess | sed -e "s/[0-9.]*$//"`

case $PLATFORM in
    i386-apple-darwin)
        PYTHON_VERSION='2.6'
        UNICODE_VARIANT='ucs2'
        ;;
    i686-pc-linux-gnu)
        PYTHON_VERSION='2.6'
        UNICODE_VARIANT='ucs4'
        ;;
    x86_64-unknown-linux-gnu)
        PYTHON_VERSION='2.6'
        UNICODE_VARIANT='ucs4'
        ;;
esac

# Clean up checkout directory if there was the results of a prior build
# still there.

test -f Makefile && make distclean

# Everything is keyed off version number from 'newrelic/__init__.py'
# file. The final release file though gets a build number stuck on the
# end from the Hudson server though. If we aren't running under the
# Hudson server then use a build number of '0'.

VERSION=`cat newrelic/__init__.py | \
            grep '^version' | sed -e "s/.*'\(.*\)'.*/\1/"`

if test -z "$BUILD_NUMBER"
then
    BUILD_NUMBER=0
fi

HUDSON_BUILD_NUMBER=$BUILD_NUMBER
export HUDSON_BUILD_NUMBER

# Define the destination for builds and where the agent specific parts
# are to be installed. Remove any existing directory which corresponds
# to the same build. Then create the new directory structure.

RELEASE=newrelic-python-$VERSION.$BUILD_NUMBER

BUILDDIR=package
ROOTDIR=$BUILDDIR/$RELEASE

test -d $ROOTDIR && rm -rf $ROOTDIR

mkdir -p $ROOTDIR

# Now build the Python agent.

echo ./configure --with-python=$TOOLSDIR/python-${PYTHON_VERSION}-${UNICODE_VARIANT}/bin/python${PYTHON_VERSION} "$@"
./configure --with-python=$TOOLSDIR/python-${PYTHON_VERSION}-${UNICODE_VARIANT}/bin/python${PYTHON_VERSION} "$@"

echo make hudson-install DESTDIR=$ROOTDIR
make hudson-install DESTDIR=$ROOTDIR

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi

echo make distclean
make distclean

STATUS=$?
if test "$STATUS" != "0"
then
    echo "`basename $0`: *** Error $STATUS"
    exit 1
fi

# Leave a cookie file for the package version.

echo $VERSION.$BUILD_NUMBER > $ROOTDIR/VERSION

# Copy in licence file and installation instructions, plus the sample
# configuration file to be used with the Python agent.

#cp php_agent/LICENSE.txt $ROOTDIR/LICENSE
cp INSTALL $ROOTDIR/INSTALL
cp newrelic.ini $ROOTDIR/newrelic.ini

# Copy in the installation script used to install the Python agent into
# the desired Python installation.

cp setup.py $ROOTDIR/setup.py

# Remove any tar balls which correspond to the same build and then build
# fresh tar balls.

rm -f $ROOTDIR.tar
rm -f $ROOTDIR.tar.gz

(cd $BUILDDIR; tar cvf $RELEASE.tar $RELEASE)
gzip --best $BUILDDIR/$RELEASE.tar

# Display the results of the build.

echo
ls -l $ROOTDIR

exit 0
