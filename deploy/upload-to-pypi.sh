#!/bin/sh

# Upload a source distribution package to a PyPI repository.
#
# This script will register and upload a package to either the
# Test PyPI repository, or the real production PyPI.
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
#
# Requires: git and twine.

set -e

# Run from the top of the repository directory.

cd $(git rev-parse --show-toplevel)

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

twine_command()
{
    TWINE_COMMAND=$1
    PKG_PATH=$2

    echo
    echo "Running twine $TWINE_COMMAND for $PKG_PATH"

    twine $TWINE_COMMAND \
        --repository $PYPI_REPOSITORY \
        --config-file $PYPIRC \
        --password $PYPI_PASSWORD \
        $PKG_PATH
}

# Set and validate environment variables

echo
echo "=== Start uploading ==="
echo
echo "Checking environment variables."

source ./deploy/common.sh

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

# If we get to this point, environment variables are OK.

echo "... PYPI_REPOSITORY = $PYPI_REPOSITORY"
echo "... AGENT_VERSION   = $AGENT_VERSION"
echo "... PACKAGE_PATH    = $PACKAGE_PATH"

# Run upload commands

twine_command register $PACKAGE_PATH
twine_command upload $PACKAGE_PATH
