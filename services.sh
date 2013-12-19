#!/bin/sh

case $1 in
    start)
        devpi-server --start
        ;;
    stop)
        devpi-server --stop
        ;;
esac
