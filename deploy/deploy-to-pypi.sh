#!/bin/sh

# Deploy a source distribution package to PyPI.
#
# Glue script that calls two other scripts to:
#
#   1. Download package from Artifactory.
#   2. Upload package to PyPI.
#
# Required environment variables:
#
#   1. Either PYPI_TEST_PASSWORD or PYPI_PRODUCTION_PASSWORD
#   2. PYPI_REPOSITORY
#   3. AGENT_VERSION
#
# Requires: git, md5sum, curl, and twine.

set -e

deploy/download-from-artifactory.sh
deploy/upload-to-pypi.sh
