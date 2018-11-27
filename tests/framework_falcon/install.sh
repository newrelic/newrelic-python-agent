#!/usr/bin/env bash

# Install cython only when the CYTHON env variable is set
[[ $CYTHON ]] && pip install cython

pip install --no-binary :all: $*
