#!/bin/sh

# Upload a source distribution package to a PyPI repository.
#
# First, this script will download the package from Artifactory. Then, it
# will register it and upload it to either the Test PyPI repository, or the
# real production PyPI.
#
# You must define several environment variables: one of the the PyPI
# password variables (either the password for testing PyPI, or the password
# for production PyPI), one for the PyPI repository, and one for the agent
# version.
#
# Required environment variables:
#
#   1. Either PYPI_TEST_PASSWORD or PYPI_PRODUCTION_PASSWORD
#   2. PYPI_REPOSITORY
#   3. AGENT_VERSION

set -e

# Define various file and URL locations.

GIT_REPO_ROOT=$(git rev-parse --show-toplevel)
PYPIRC=$GIT_REPO_ROOT/deploy/.pypirc

ARTIFACTORY=http://pdx-artifacts.pdx.vm.datanerd.us:8081/artifactory
ARTIFACTORY_PYPI_URL=$ARTIFACTORY/simple/pypi-newrelic

# Define functions

set_pypi_password()
{
    VAR_NAME=$1
    PASS=$2

    if test x"$PASS" = x""
    then
        echo "ERROR: $VAR_NAME environment variable is not set."
        exit 1
    else
        PYPI_PASSWORD=$PASS
    fi
}

download_from_artifactory()
{
    DOWNLOAD_PATH=$1
    DOWNLOAD_URL=$2

    echo
    echo "Downloading from Artifactory."
    echo "From: $DOWNLOAD_URL"
    echo "To:   $DOWNLOAD_PATH"

    curl -q \
        --silent \
        --show-error \
        --create-dirs \
        --output $DOWNLOAD_PATH \
        $DOWNLOAD_URL
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

twine_command()
{
    TWINE_COMMAND=$1

    echo
    echo "Running twine $TWINE_COMMAND."

    twine $TWINE_COMMAND \
        --repository $PYPI_REPOSITORY \
        --config-file $PYPIRC \
        --password $PYPI_PASSWORD \
        $PACKAGE_PATH
}

# Validate environment variables

echo
echo "Checking environment variables."

if test x"$PYPI_REPOSITORY" = x""
then
    echo "ERROR: PYPI_REPOSITORY environment variable is not set."
    exit 1
fi

case $PYPI_REPOSITORY in
    pypi-test)
        set_pypi_password PYPI_TEST_PASSWORD $PYPI_TEST_PASSWORD
        echo "... PYPI_TEST_PASSWORD is set."
        ;;

    pypi-production)
        set_pypi_password PYPI_PRODUCTION_PASSWORD $PYPI_PRODUCTION_PASSWORD
        echo "... PYPI_PRODUCTION_PASSWORD is set."
        ;;

    *)
        echo "... PYPI_REPOSITORY = $PYPI_REPOSITORY"
        echo "ERROR: PYPI_REPOSITORY must be 'pypi-test' or 'pypi-production'."
        exit 1
        ;;
esac

if test x"$AGENT_VERSION" = x""
then
    echo "ERROR: AGENT_VERSION environment variable is not set."
    exit 1
fi

# If we get to this point, environment variables are OK.

echo "... PYPI_REPOSITORY = $PYPI_REPOSITORY"
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
twine_command register
twine_command upload
