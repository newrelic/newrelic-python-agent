#!/bin/sh

# Upload source distribution package in `dist` directory to Artifactory.
#
# If running locally, you'll need to set two environment variables:
#
#   1. ARTIFACTORY_PASSWORD
#   2. AGENT_VERSION
#
# Requires: git, md5sum, and curl.

set -e

# Run from the top of the repository directory.

cd $(git rev-parse --show-toplevel)

# Set and validate environment variables

echo
echo "=== Start uploading ==="
echo
echo "Checking environment variables."

. ./deploy/common.sh

if test x"$ARTIFACTORY_PASSWORD" = x""
then
    echo
    echo "ERROR: ARTIFACTORY_PASSWORD environment variable is not set."
    exit 1
fi

# If we get to this point, environment variables are OK.

echo "... AGENT_VERSION = $AGENT_VERSION"
echo "... PACKAGE_PATH  = $PACKAGE_PATH"
echo "... PACKAGE_URL   = $PACKAGE_URL"

# Get MD5 checksum of file to upload, so Artifactory can verify it.

MD5_OUTPUT=$(md5sum $PACKAGE_PATH)
MD5_CHECKSUM=$(echo $MD5_OUTPUT | awk '{print $1}')

echo
echo "Computing MD5 checksum"
echo "$MD5_CHECKSUM"

if test x"$MD5_CHECKSUM" = x""
then
    echo
    echo "ERROR: MD5_CHECKSUM cannot be empty."
    exit 1
fi

# Upload the agent source distribution package with curl.
#
# Use `--write-out` to store the HTTP status response code in the last
# line of RESPONSE, so we can check to see if the upload succeeded.

echo
echo "Uploading to: $PACKAGE_URL"

RESPONSE=$(curl -q \
    --silent \
    --show-error \
    --write-out "\n%{http_code}" \
    --header "X-Checksum-Md5: $MD5_CHECKSUM" \
    --user "$ARTIFACTORY_USER:$ARTIFACTORY_PASSWORD" \
    --upload-file "$PACKAGE_PATH" \
    "$PACKAGE_URL")

echo
echo "Response:"
echo "$RESPONSE"

# Verify upload was successful.

HTTP_RESPONSE_STATUS=$(echo "$RESPONSE" | tail -1)

if test x"$HTTP_RESPONSE_STATUS" = x"201"
then
    echo
    echo "SUCCESS: Agent uploaded."
else
    echo
    echo "ERROR: Agent NOT uploaded."
    exit 1
fi
