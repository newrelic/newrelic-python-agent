#!/bin/sh

# Download package from Artifactory and verify MD5 checksum.
#
# If running locally, you'll need to set one environment variable:
#
#   1. AGENT_VERSION
#
# Requires: git, md5sum, and curl.

set -e

# Run from the top of the repository directory.

cd $(git rev-parse --show-toplevel)

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

# Set and validate environment variables

echo
echo "=== Start downloading ==="
echo
echo "Checking environment variables"

source ./deploy/common.sh

# If we get to this point, environment variables are OK.

echo "... AGENT_VERSION = $AGENT_VERSION"
echo "... PACKAGE_PATH  = $PACKAGE_PATH"
echo "... PACKAGE_URL   = $PACKAGE_URL"
echo "... MD5_PATH      = $MD5_PATH"
echo "... MD5_URL       = $MD5_URL"

# Run commands

download_from_artifactory $PACKAGE_PATH $PACKAGE_URL
download_from_artifactory $MD5_PATH $MD5_URL
verify_md5_checksum
