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

set -euo pipefail

# Create build dir
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
BUILD_DIR="${TOX_ENV_DIR:-${SCRIPT_DIR}}/build/azure-functions-worker"
rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}

# Clone repository
git clone https://github.com/Azure/azure-functions-python-worker.git ${BUILD_DIR}

# Setup virtual environment and install dependencies
python -m venv "${BUILD_DIR}/.venv"
PYTHON="${BUILD_DIR}/.venv/bin/python"
PIP="${BUILD_DIR}/.venv/bin/pip"
PIPCOMPILE="${BUILD_DIR}/.venv/bin/pip-compile"
INVOKE="${BUILD_DIR}/.venv/bin/invoke"
${PIP} install pip-tools build invoke

# Install proto build dependencies
$( cd ${BUILD_DIR}/workers/ && ${PIPCOMPILE} -o ${BUILD_DIR}/requirements.txt )
${PIP} install -r ${BUILD_DIR}/requirements.txt

# Patch proto generation script
cd ${BUILD_DIR}/workers/tests && patch -Rp1 <<EOF
*** test_setup.py	Mon Dec 29 13:33:06 2025
--- test_setup.cp	Mon Dec 29 13:32:57 2025
***************
*** 37,43 ****
  WEBHOST_GITHUB_API = "https://api.github.com/repos/Azure/azure-functions-host"
  WEBHOST_GIT_REPO = "https://github.com/Azure/azure-functions-host/archive"
  WEBHOST_TAG_PREFIX = "v4."
! WORKER_DIR = "azure_functions_worker"
  
  
  def get_webhost_version() -> str:
--- 37,43 ----
  WEBHOST_GITHUB_API = "https://api.github.com/repos/Azure/azure-functions-host"
  WEBHOST_GIT_REPO = "https://github.com/Azure/azure-functions-host/archive"
  WEBHOST_TAG_PREFIX = "v4."
! WORKER_DIR = "azure_functions_worker" if sys.version_info.minor < 13 else "proxy_worker"
  
  
  def get_webhost_version() -> str:
EOF

# Build proto files into pb2 files (invoke handles fixing include paths for the protos)
cd ${BUILD_DIR}/workers/tests && ${INVOKE} -c test_setup build-protos

# Build and install the package into the original environment (not the build venv)
# Do NOT use ${PIP} from the venv
pip install ${BUILD_DIR}/workers/

# Clean up and return to the original directory
rm -rf ${BUILD_DIR}
