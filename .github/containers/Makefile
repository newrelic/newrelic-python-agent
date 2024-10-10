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

# Override constants
PLATFORM_OVERRIDE:=
PYTHON_VERSIONS_OVERRIDE:=

# Computed variables
IMAGE_NAME:=ghcr.io/newrelic/newrelic-python-agent-ci
MAKEFILE_DIR:=$(dir $(realpath $(firstword ${MAKEFILE_LIST})))
REPO_ROOT:=$(realpath ${MAKEFILE_DIR}../../)
UNAME_P:=$(shell uname -p)
PLATFORM_AUTOMATIC:=$(if $(findstring arm,${UNAME_P}),linux/arm64,linux/amd64)
PLATFORM:=$(if ${PLATFORM_OVERRIDE},${PLATFORM_OVERRIDE},${PLATFORM_AUTOMATIC})
PYTHON_VERSIONS_AUTOMATIC:=3.10
PYTHON_VERSIONS:=$(if ${PYTHON_VERSIONS_OVERRIDE},${PYTHON_VERSIONS_OVERRIDE},${PYTHON_VERSIONS_AUTOMATIC})

.PHONY: default
default: test

.PHONY: build
build:
	@docker build ${MAKEFILE_DIR} \
		--platform=${PLATFORM} \
		-t ${IMAGE_NAME}:local \
		--build-arg='PYTHON_VERSIONS=${PYTHON_VERSIONS}'

# Run the local tag as a container.
.PHONY: run
run: run.local

# Run a specific tag as a container.
# Usage: make run.<tag>
# Defaults to run.local, but can instead be run.latest or any other tag.
.PHONY: run.%
run.%:
# Build image if local was specified, else pull latest
	@if [[ "$*" = "local" ]]; then \
		cd ${MAKEFILE_DIR} && $(MAKE) build; \
	else \
		docker pull --platform=${PLATFORM} ${IMAGE_NAME}:$*; \
	fi
	@docker run --rm -it \
		--platform=${PLATFORM} \
		--mount type=bind,source="${REPO_ROOT}",target=/home/github/python-agent \
		--workdir=/home/github/python-agent \
		--add-host=host.docker.internal:host-gateway \
		-e NEW_RELIC_HOST="${NEW_RELIC_HOST}" \
		-e NEW_RELIC_LICENSE_KEY="${NEW_RELIC_LICENSE_KEY}" \
		-e NEW_RELIC_DEVELOPER_MODE="${NEW_RELIC_DEVELOPER_MODE}" \
		-e GITHUB_ACTIONS="true" \
		${IMAGE_NAME}:$* /bin/bash

# Ensure python versions are usable. Cannot be automatically used with PYTHON_VERSIONS_OVERRIDE.
.PHONY: test
test: build
	@docker run --rm \
		--platform=${PLATFORM} \
		ghcr.io/newrelic/python-agent-ci:local \
		/bin/bash -c '\
			python3.10 --version && \
			touch tox.ini && tox --version && \
			echo "Success! Python versions installed."'
