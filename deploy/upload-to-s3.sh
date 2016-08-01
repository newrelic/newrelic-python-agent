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

# Define function to test if file exists in S3

s3_file_exists()
{
    if test $# -ne 2
    then
        echo
        echo "ERROR: Wrong number of arguments to s3_file_exists."
        exit 1
    fi

    NAME=$1
    URI=$2

    # $URI already ends in a / so it is not necessary to include one here
    # between $URI and $NAME
    CMD="aws s3 ls ${URI}${NAME}"

    echo
    echo "Running awscli command:"
    echo $CMD

    # Since `aws s3 ls` does not do an exact match (it matches by prefix), a
    # further check must be preformed
    for result in `$CMD | awk '{print $4}'`
    do
        if [[ $result = $NAME ]]
        then
            return 0
        fi
    done

    return 1
}

# Define function to test s3 connection and settings (such as networking,
# correct keys, existence of s3 directories, etc.)

test_s3_env_settings()
{
    # Since it is only stdout that is redirected to /dev/null, any errors will
    # still appear in the terminal output.
    CMD="aws s3 ls $S3_URI"

    echo
    echo "Running awscli command:"
    echo $CMD

    set +e
    $CMD > /dev/null

    if [[ $? > 0 ]]
    then
        echo
        echo "ERROR: Running command \`$CMD\` failed."
        echo "       Confirm networking, permissions, aws keys, and S3_URI then try again."
        exit 1
    fi

    set -e
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

S3_URI=s3://$S3_BUCKET/$S3_AGENT_NAME/$S3_RELEASE_TYPE/

# If we get to this point, environment variables are OK.

echo "... AGENT_VERSION  = $AGENT_VERSION"
echo "... PACKAGE_NAME   = $PACKAGE_NAME"
echo "... PACKAGE_PATH   = $PACKAGE_PATH"
echo "... MD5_NAME       = $MD5_NAME"
echo "... MD5_PATH       = $MD5_PATH"
echo "... S3_URI         = $S3_URI"

# Make sure permissions are right before uploading

chmod 644 $PACKAGE_PATH
chmod 644 $MD5_PATH

# Check connection to s3. Confirms error cases like networking and proper keys.

echo
echo "Testing S3 connection"
echo

test_s3_env_settings  # exits 1 on failure

# Bail, if package version already exists in S3.

echo
echo "Checking for existing files in S3"
echo

if s3_file_exists $PACKAGE_NAME $S3_URI
then
    echo
    echo "ERROR: $PACKAGE_NAME already exists at $S3_URI"
    exit 1
fi

if s3_file_exists $MD5_NAME $S3_URI
then
    echo
    echo "ERROR: $MD5_NAME already exists at $S3_URI"
    exit 1
fi

# Upload to S3

echo
echo "Uploading to S3"
echo

upload_to_s3 $PACKAGE_PATH $S3_URI
upload_to_s3 $MD5_PATH $S3_URI
