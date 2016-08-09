#!/bin/bash -x

arg=$1

case $arg in
    --restart)
        restart=true
        ;;
    *)
        restart=false
        ;;
esac

./docker/packnsend pull

if $restart
then
    # stop all containers prior to starting them
    ./docker/packnsend restart
else
    # if container is not running, start it, else do nothing
    ./docker/packnsend start
fi
