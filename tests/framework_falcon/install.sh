#!/usr/bin/env bash

# Install cython only when the CYTHON env variable is set
if [ -n "$CYTHON" ]; then
    echo "CYTHON"
    pip install cython
    pip install --no-binary :all: $*
else
    echo "PYTHON"
    pip install $*
fi
