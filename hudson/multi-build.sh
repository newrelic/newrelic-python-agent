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
    TOOLSDIR=/usr/local/python
fi

# Work out what platform we are and what Python versions/variants we
# need to build for. These should be the same as or a subset of what
# Python versions/variants have been installed using install scripts in
# 'python-tools' directory. Specifically those listed in the 'parts'
# variable in the 'buildout' section of the platform specific build
# configuration files in the 'python-tools' directory.

PLATFORM=`./config.guess | sed -e "s/[0-9.]*$//"`

case $PLATFORM in
    i386-apple-darwin)
        PYTHON_VERSIONS='2.6 2.7'
        UNICODE_VARIANTS='ucs2 ucs4'
        ;;
    i686-pc-linux-gnu)
        PYTHON_VERSIONS='2.4 2.5 2.6 2.7'
        UNICODE_VARIANTS='ucs2 ucs4'
        ;;
    x86_64-unknown-linux-gnu)
        PYTHON_VERSIONS='2.4 2.5 2.6 2.7'
        UNICODE_VARIANTS='ucs2 ucs4'
        ;;
esac

# Everything is keyed off the version number in the 'VERSION' file.
# This is even what is builtin to the compiled agent. The final
# release file though gets a build number stuck on the end from the
# Hudson server though. If we aren't running under the Hudson server
# then use a build number of '0'.

VERSION=`cat VERSION`

if test -z "$BUILD_NUMBER"
then
    BUILD_NUMBER=0
fi

# Clean up checkout directory if there was the results of a prior build
# still there.

test -f Makefile && make distclean

# Define the destination for builds and where the agent specific parts
# are to be installed. Remove any existing directory which corresponds
# to the same build. Then create the new directory structure.

ROOTDIR=hudson-results/newrelic-python-$VERSION.$BUILD_NUMBER-$PLATFORM

AGENTDIR=$ROOTDIR/agent
SCRIPTSDIR=$ROOTDIR/scripts
DAEMONDIR=$ROOTDIR/daemon

test -d $ROOTDIR && rm -rf $ROOTDIR

mkdir -p $ROOTDIR
mkdir -p $AGENTDIR
mkdir -p $SCRIPTSDIR
mkdir -p $DAEMONDIR

# Now build the Python agent for all the Python version/variants which
# are required for this platform.

for i in $PYTHON_VERSIONS
do
    for j in $UNICODE_VARIANTS
    do
        echo ./configure --with-python=$TOOLSDIR/python-$i-$j/bin/python$i
        ./configure --with-python=$TOOLSDIR/python-$i-$j/bin/python$i
        echo make hudson-install DESTDIR=$AGENTDIR/python-$i-$j
        make hudson-install DESTDIR=$AGENTDIR/python-$i-$j
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
    done
done

# Leave a cookie file indicating name of platform this package has been
# built for as well as one which flags what version of the agent this is.

echo $PLATFORM > $ROOTDIR/PLATFORM
echo $VERSION.$BUILD_NUMBER > $AGENTDIR/VERSION

# Copy in licence file and installation instructions, plus the sample
# configuration file to be used with the Python agent.

cp php_agent/LICENSE.txt $ROOTDIR/LICENSE
cp package/INSTALL $ROOTDIR/INSTALL
cp package/newrelic.ini $AGENTDIR/newrelic.ini

# Copy in 'config.guess' which is used to validate at time of install
# that the package is for the correct platform.

cp config.guess $ROOTDIR/scripts/config.guess

# Copy in the installation script used to install the Python agent into
# the desired Python installation.

cp package/setup.py $ROOTDIR/setup.py

# Copy in the local daemon script files required for installation as
# well as the installer itself.

#cp php_agent/newrelic-install.sh $ROOTDIR/install.sh

cp php_agent/scripts/init.* $SCRIPTSDIR/
cp php_agent/scripts/newrelic.xml $SCRIPTSDIR/
cp php_agent/scripts/newrelic.sysconfig $SCRIPTSDIR/

# Copy the local daemon into place. If not building under hudson, grab
# if from the parallel source checkout directory. If running under Hudson
# then we need to grab it from the Hudson rsync server.

if test x"$BUILD_NUMBER" = x"0"
then
    cp ../local_daemon/src/newrelic-daemon $DAEMONDIR/newrelic-daemon
    STATUS=$?
    if test "$STATUS" != "0"
    then
        echo "`basename $0`: *** Error $STATUS"
        exit 1
    fi

    grep '#define NR_LOCAL_DAEMON_VERSION' ../local_daemon/src/version.c | \
        sed -e 's/^.* "//' -e 's/".*$/.0/' > $DAEMONDIR/VERSION
else
    # XXX Grab from Hudson rsync server.
    true
fi

# Remove any tar balls which correspond to the same build and then build
# fresh tar balls.

rm -f $ROOTDIR.tar
rm -f $ROOTDIR.tar.gz

tar cvf $ROOTDIR.tar $ROOTDIR
gzip --best $ROOTDIR.tar

# Display the results of the build.

echo
ls -l $ROOTDIR

echo
ls -l $AGENTDIR

echo
ls -l $DAEMONDIR

echo
ls -l $SCRIPTSDIR

exit 0
