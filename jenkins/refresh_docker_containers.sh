#!/bin/sh
#
# Run this after updating docker images.
#
# Pull images. Stop and start docker containers, so that
# all running containers will be using the latest images.

./docker/packnsend pull
./docker/packnsend restart
