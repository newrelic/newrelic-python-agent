#!/bin/sh

# Deploy a source distribution package to PyPI.
#
# Glue script that calls two other scripts to:
#
#   1. Download package from Artifactory.
#   2. Upload package to New Relic Download site.
#
# Required environment variables:
#
#   3. AGENT_VERSION
#
# Requires: git, md5sum, and curl.

set -e

GIT_REPO_ROOT=$(git rev-parse --show-toplevel)

cd $GIT_REPO_ROOT

deploy/download-from-artifactory.sh
deploy/upload-to-download-site.sh
