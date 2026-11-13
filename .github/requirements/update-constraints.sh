#!/usr/bin/env bash
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

# =====================================================================================
# Re-pin every hash-locked requirements file in .github/requirements from its .in file,
# upgrading all pins to the latest versions the .in constraints allow.
# =====================================================================================

set -euo pipefail

PYTHON_VERSION="3.10"

if ! command -v uv > /dev/null 2>&1; then
    echo "Error: uv is a required dependency." >&2
    exit 1
fi

# Run from the repository root so the paths recorded in each lock file's header are stable.
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
REQUIREMENTS_DIR=".github/requirements"

for input in "$REQUIREMENTS_DIR"/*.in; do
    echo "Pinning $input"
    uv pip compile --universal --python-version "$PYTHON_VERSION" --generate-hashes --upgrade \
        "$input" -o "${input%.in}.txt"
done
