#!/bin/sh

# Upload a source distribution package to S3.
#
# Glue script that calls two other scripts to:
#
#   1. Download package from Artifactory.
#   2. Upload package to S3.
#
# Required environment variables:
#
#   1. AGENT_VERSION
#   2. AWS_ACCESS_KEY_ID
#   3. AWS_SECRET_ACCESS_KEY
#   4. AWS_BUCKET_PREFIX (either "testing", "release", or "archive")
#
# Requires: git, md5sum, curl, and awscli.

set -e

GIT_REPO_ROOT=$(git rev-parse --show-toplevel)

cd $GIT_REPO_ROOT

deploy/download-from-artifactory.sh
deploy/upload-to-s3.sh
