#!/bin/sh

# Download package from Artifactory and verify MD5 checksum.
#
# If running locally, you'll need to set one environment variable:
#
#   1. AGENT_VERSION
#
# Requires: git, md5sum, and curl.

set -e

# Define various file and URL locations.

GIT_REPO_ROOT=$(git rev-parse --show-toplevel)

PYPIRC=$GIT_REPO_ROOT/deploy/.pypirc
ARTIFACTORY=http://pdx-artifacts.pdx.vm.datanerd.us:8081/artifactory
ARTIFACTORY_PYPI_URL=$ARTIFACTORY/simple/pypi-newrelic

# Define functions

download_from_artifactory()
{
    DOWNLOAD_PATH=$1
    DOWNLOAD_URL=$2

    echo
    echo "Downloading from Artifactory"
    echo "From: $DOWNLOAD_URL"
    echo "To:   $DOWNLOAD_PATH"

    CURL_RESPONSE=$(curl -q \
        --silent \
        --show-error \
        --write-out "\n%{http_code}" \
        --create-dirs \
        --output $DOWNLOAD_PATH \
        $DOWNLOAD_URL)

    HTTP_RESPONSE_CODE=$(echo "$CURL_RESPONSE" | tail -1)

    if test x"$HTTP_RESPONSE_CODE" != x"200"
    then
        ERROR_MESSAGE=$(cat $DOWNLOAD_PATH)
        echo
        echo "ERROR: Curl command failed"
        echo "$ERROR_MESSAGE"
        exit 1
    fi
}

verify_md5_checksum()
{
    ARTIFACTORY_MD5=$(cat $MD5_PATH)
    PACKAGE_MD5_OUTPUT=$(md5sum $PACKAGE_PATH)
    PACKAGE_MD5=$(echo $PACKAGE_MD5_OUTPUT | awk '{print $1}')

    echo
    echo "Checking MD5 checksums"
    echo "... ARTIFACTORY_MD5 = $ARTIFACTORY_MD5"
    echo "... PACKAGE_MD5     = $PACKAGE_MD5"

    if test x"$ARTIFACTORY_MD5" != x"$PACKAGE_MD5"
    then
        echo
        echo "ERROR: MD5 checksums do not match."
        exit 1
    fi
}

# Validate environment variables

echo
echo "=== Start downloading ==="
echo
echo "Checking environment variables"

if test x"$AGENT_VERSION" = x""
then
    echo "ERROR: AGENT_VERSION environment variable is not set."
    exit 1
fi

# If we get to this point, environment variables are OK.

echo "... AGENT_VERSION = $AGENT_VERSION"

# Use environment variables to construct package path and download URL.

PACKAGE_NAME=newrelic-$AGENT_VERSION.tar.gz

PACKAGE_PATH=$GIT_REPO_ROOT/dist/$PACKAGE_NAME
PACKAGE_URL=$ARTIFACTORY_PYPI_URL/newrelic/$AGENT_VERSION/$PACKAGE_NAME

MD5_PATH=$PACKAGE_PATH.md5
MD5_URL=$PACKAGE_URL.md5

# Run commands

cd $GIT_REPO_ROOT

download_from_artifactory $PACKAGE_PATH $PACKAGE_URL
download_from_artifactory $MD5_PATH $MD5_URL
verify_md5_checksum
