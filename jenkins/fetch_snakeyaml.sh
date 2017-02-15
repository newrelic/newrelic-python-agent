#!/bin/bash -ex

LIBDIR='dsl-lib'
mkdir -p $LIBDIR

if [ ! -e $LIBDIR/snakeyaml-1.17.jar ]; then
    wget -nv -O $LIBDIR/snakeyaml-1.17.jar https://repo1.maven.org/maven2/org/yaml/snakeyaml/1.17/snakeyaml-1.17.jar
fi
