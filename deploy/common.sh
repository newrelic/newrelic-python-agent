#!/bin/sh

# Validates common environment variables, and sets common
# global variables for deploy scripts.

set -e

# Validate environment variable

if test x"$AGENT_VERSION" = x""
then
    echo "ERROR: AGENT_VERSION environment variable is not set."
    exit 1
fi

# Set "Constant" Global Variables

GIT_REPO_ROOT=$(git rev-parse --show-toplevel)
PYPIRC=$GIT_REPO_ROOT/deploy/.pypirc

ARTIFACTORY=http://pdx-artifacts.pdx.vm.datanerd.us:8081/artifactory
ARTIFACTORY_PYPI_URL=$ARTIFACTORY/simple/pypi-newrelic
ARTIFACTORY_USER=python-agent

# Set "Constructed" Global Variables that require AGENT_VERSION.

PACKAGE_NAME=newrelic-$AGENT_VERSION.tar.gz
PACKAGE_PATH=$GIT_REPO_ROOT/dist/$PACKAGE_NAME
PACKAGE_URL=$ARTIFACTORY_PYPI_URL/newrelic/$AGENT_VERSION/$PACKAGE_NAME

MD5_PATH=$PACKAGE_PATH.md5
MD5_URL=$PACKAGE_URL.md5
