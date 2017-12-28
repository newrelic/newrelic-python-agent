#!/bin/sh
#
# Run this before every docker test.
#
# Pull images. Start containers, which will leave existing
# containers running, so we don't interfere with already
# running tests.

./docker/packnsend pull
./docker/packnsend start
