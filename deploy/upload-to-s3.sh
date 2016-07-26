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
    DST=$2/

    CMD="aws s3 cp $SRC $DST"

    echo
    echo "Running awscli command:"
    echo $CMD

    $CMD
}

# Define function to test if file exists in S3

s3_file_exists()
{
    if test $# -ne 2
    then
        echo
        echo "ERROR: Wrong number of agruments to s3_file_exists."
        exit 1
    fi

    NAME=$1
    BUCKET=$2

    CMD="aws s3 ls $BUCKET/$NAME"

    echo
    echo "Running awscli command:"
    echo $CMD

    $CMD
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
    echo "ERROR: AWS_ACCESS_KEY_ID environment variable is not set."
    exit 1
fi
if test x"$AWS_SECRET_ACCESS_KEY" = x""
then
    echo "ERROR: AWS_SECRET_ACCESS_KEY environment variable is not set."
    exit 1
fi
if test x"$AWS_BUCKET_PREFIX" != x"testing" && \
        test x"$AWS_BUCKET_PREFIX" != x"release" && \
        test x"$AWS_BUCKET_PREFIX" != x"archive"
then
    echo "ERROR: AWS_BUCKET_PREFIX environment variable is incorrectly set."
    echo "       Shoule be one of \"testing\", \"release\", or \"archive\""
    echo "       but is set to \"$AWS_BUCKET_PREFIX\" instead."
    exit 1
fi

AWS_BUCKET=$AWS_BUCKET/$AWS_BUCKET_PREFIX

# If we get to this point, environment variables are OK.

echo "... AGENT_VERSION  = $AGENT_VERSION"
echo "... PACKAGE_NAME   = $PACKAGE_NAME"
echo "... PACKAGE_PATH   = $PACKAGE_PATH"
echo "... MD5_NAME       = $MD5_NAME"
echo "... MD5_PATH       = $MD5_PATH"
echo "... AWS_BUCKET     = $AWS_BUCKET"

# Make sure permissions are right before uploading

chmod 644 $PACKAGE_PATH
chmod 644 $MD5_PATH

# Bail, if package version already exists in S3.

echo
echo "Checking for existing files in S3"
echo

if s3_file_exists $PACKAGE_NAME $AWS_BUCKET
then
    echo "ERROR: $PACKAGE_NAME already exists at $AWS_BUCKET"
    exit 1
fi

if s3_file_exists $MD5_NAME $AWS_BUCKET
then
    echo "ERROR: $MD5_NAME already exists at $AWS_BUCKET"
    exit 1
fi

# Upload to S3

echo
echo "Uploading to S3"
echo

upload_to_s3 $PACKAGE_PATH $AWS_BUCKET
upload_to_s3 $MD5_PATH $AWS_BUCKET
