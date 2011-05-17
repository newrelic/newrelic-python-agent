#!/bin/sh

TOOLSDIR=$1

if test x"$TOOLSDIR" = x""
then
    TOOLSDIR=python-tools/parts
fi

PLATFORM=`./config.guess | sed -e "s/[0-9.]*$//"`

case $PLATFORM in
    i386-apple-darwin)
        PYTHON_VERSIONS='2.6 2.7'
        UNICODE_VARIANTS='ucs2'
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

VERSION=`cat VERSION`

ROOTDIR=newrelic-python-$VERSION-$PLATFORM

test -f Makefile && make distclean
test -d $ROOTDIR && rm -rf $ROOTDIR

for i in $PYTHON_VERSIONS
do
    for j in $UNICODE_VARIANTS
    do
        echo ./configure --with-python=$TOOLSDIR/python-$i-$j/bin/python$i
        ./configure --with-python=$TOOLSDIR/python-$i-$j/bin/python$i
        echo make install-destdir DESTDIR=$ROOTDIR/python-$i-$j
        make install-destdir DESTDIR=$ROOTDIR/python-$i-$j
    done
done

rm -f $ROOTDIR.tar
rm -f $ROOTDIR.tar.gz

tar cvf $ROOTDIR.tar $ROOTDIR
gzip --best $ROOTDIR.tar
