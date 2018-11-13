#!/usr/bin/env bash

set -e

find . -user root -type f | xargs chown -f jenkins:jenkins
find . -user root -type d | xargs chown -f -R jenkins:jenkins
