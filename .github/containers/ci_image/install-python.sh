#!/bin/bash
# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -eo pipefail

main() {
    # Coerce space separated string to array
    if [[ ${#PYTHON_VERSIONS[@]} -eq 1 ]]; then
        PYTHON_VERSIONS=($PYTHON_VERSIONS)
    fi

    if [[ -z "${PYTHON_VERSIONS[@]}" ]]; then
        echo "No python versions specified. Make sure PYTHON_VERSIONS is set." 1>&2
        exit 1
    fi

    # Find all latest pyenv supported versions for requested python versions
    PYENV_VERSIONS=()
    for v in "${PYTHON_VERSIONS[@]}"; do
        LATEST=$(pyenv latest -k "$v" || pyenv latest -k "$v-dev")
        if [[ -z "$LATEST" ]]; then
            echo "Latest version could not be found for ${v}." 1>&2
            exit 1
        fi
        PYENV_VERSIONS+=($LATEST)
    done

    # Install each specific version
    for v in "${PYENV_VERSIONS[@]}"; do
        pyenv install "$v" &
    done
    wait

    # Set all installed versions as globally accessible
    pyenv global ${PYENV_VERSIONS[@]}
    
    # Install dependencies for main python installation
    pyenv exec pip install --upgrade -r /requirements.txt
}

main
