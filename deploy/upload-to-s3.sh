#!/bin/sh

# Upload source distribution package in `dist` directory to
# S3 bucket defined at $AWS_BUCKET/$AWS_BUCKET_PREFIX/.
#
# Required environment variables
#
#   1. AGENT_VERSION
#   2. AWS_ACCESS_KEY_ID
#   3. AWS_SECRET_ACCESS_KEY
#   4. AWS_BUCKET_PREFIX (either "testing", "release", or "archive")
#
# Requires: git and awscli

set -e

# Run from the top of the repository directory.

cd $(git rev-parse --show-toplevel)

# Define upload function

upload_to_s3()
{
    if test $# -ne 2
    then
        echo
        echo "ERROR: Wrong number of arguments to upload_to_s3."
        exit 1
    fi

    SRC=$1
    DST=$2

    CMD="aws s3 cp $SRC $DST"

    echo
    echo "Running awscli command:"
    echo $CMD

    $CMD
}

abort_if_key_exists_or_error()
{
    if test $# -ne 1
    then
        echo
        echo "ERROR: Wrong number of arguments to abort_if_key_exists_or_error."
        exit 1
    fi

    S3_KEY=$1
    CMD="aws s3 ls $S3_KEY"

    echo
    echo "Running awscli command:"
    echo $CMD

    set +e
    $CMD
    RETURN_STATUS=$?
    set -e

    # Return codes from `aws s3 ls` command:
    #   0          : Key prefix exists
    #   1          : Key prefix does not exist
    #   All others : Error
    #
    # http://docs.aws.amazon.com/cli/latest/topic/return-codes.html

    if test $RETURN_STATUS -eq 0
    then
        echo
        echo "ERROR: Key $S3_KEY already exists."
        exit 1

    elif test $RETURN_STATUS -gt 1
    then
        echo
        echo "ERROR: Running command \`$CMD\` failed."
        echo "       Confirm networking, permissions, aws keys, and S3_DIR then try again."
        exit 1
    fi
}

# Set and validate environment variables

echo
echo "=== Start uploading ==="
echo
echo "Checking environment variables"

# Source common variables

. ./deploy/common.sh

if test x"$AWS_ACCESS_KEY_ID" = x""
then
    echo
    echo "ERROR: AWS_ACCESS_KEY_ID environment variable is not set."
    exit 1
fi
if test x"$AWS_SECRET_ACCESS_KEY" = x""
then
    echo
    echo "ERROR: AWS_SECRET_ACCESS_KEY environment variable is not set."
    exit 1
fi
if test x"$S3_RELEASE_TYPE" != x"testing" && \
        test x"$S3_RELEASE_TYPE" != x"release" && \
        test x"$S3_RELEASE_TYPE" != x"archive"
then
    echo
    echo "ERROR: S3_RELEASE_TYPE environment variable is incorrectly set."
    echo "       Shoule be one of \"testing\", \"release\", or \"archive\""
    echo "       but is set to \"$S3_RELEASE_TYPE\" instead."
    exit 1
fi

S3_DIR=s3://$S3_BUCKET/$S3_AGENT_NAME/$S3_RELEASE_TYPE/

# If we get to this point, environment variables are OK.

echo "... AGENT_VERSION  = $AGENT_VERSION"
echo "... PACKAGE_NAME   = $PACKAGE_NAME"
echo "... PACKAGE_PATH   = $PACKAGE_PATH"
echo "... MD5_NAME       = $MD5_NAME"
echo "... MD5_PATH       = $MD5_PATH"
echo "... S3_DIR         = $S3_DIR"

# Make sure permissions are right before uploading

chmod 644 $PACKAGE_PATH
chmod 644 $MD5_PATH

# Bail, if package version already exists in S3.

echo
echo "Checking for existing files in S3"

S3_PACKAGE_URI=${S3_DIR}${PACKAGE_NAME}

abort_if_key_exists_or_error $S3_PACKAGE_URI

# Upload to S3

echo
echo "Uploading to S3"

upload_to_s3 $PACKAGE_PATH $S3_DIR
upload_to_s3 $MD5_PATH $S3_DIR
