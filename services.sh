#!/bin/sh

test ! -d $HOME/.distlib && mkdir $HOME/.distlib

case $1 in
    start)
        devpi-server --start
        ;;
    stop)
        devpi-server --stop
        ;;
esac
