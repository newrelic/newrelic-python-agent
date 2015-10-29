#!/bin/sh

# Upload source distribution package in `dist` directory to Artifactory.
#
# Our `pypi-newrelic` Artifactory repository can be accessed with the
# PyPI API, so we can use `twine` to upload the package. Unlike the real
# PyPI, we don't register the package first. We simply upload it.

set -e

# If running locally, you'll need to set this environment variable. It should
# already be set when running in a Jenkins job.

if test x"$PYPI_NEWRELIC_PASSWORD" = x""
then
    echo
    echo "ERROR: PYPI_NEWRELIC_PASSWORD environment variable is not set."
    echo "       Use password for pypi-newrelic repository in Artifactory."
    exit 1
fi

GIT_REPO_ROOT=$(git rev-parse --show-toplevel)

PYPIRC=$GIT_REPO_ROOT/deploy/.pypirc

DIST_DIR=$GIT_REPO_ROOT/dist

twine upload \
    --repository pypi-newrelic \
    --config-file $PYPIRC \
    --password $PYPI_NEWRELIC_PASSWORD \
    $DIST_DIR/newrelic*.tar.gz
