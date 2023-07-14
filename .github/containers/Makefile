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

# Repository root for mounting into container.
MAKEFILE_DIR:=$(dir $(realpath $(firstword $(MAKEFILE_LIST))))
REPO_ROOT:=$(realpath $(MAKEFILE_DIR)../../)

.PHONY: default
default: test

.PHONY: build
build:
	@# Perform a shortened build for testing
	@docker build $(MAKEFILE_DIR) \
		-t ghcr.io/newrelic/newrelic-python-agent-ci:local \
		--build-arg='PYTHON_VERSIONS=3.10 2.7'

.PHONY: test
test: build
	@# Ensure python versions are usable
	@docker run --rm ghcr.io/newrelic/python-agent-ci:local /bin/bash -c '\
		python3.10 --version && \
		python2.7 --version && \
		touch tox.ini && tox --version && \
		echo "Success! Python versions installed."'

.PHONY: run
run: build
	@docker run --rm -it \
		--mount type=bind,source="$(REPO_ROOT)",target=/home/github/python-agent \
		--workdir=/home/github/python-agent \
		--add-host=host.docker.internal:host-gateway \
		-e NEW_RELIC_HOST="${NEW_RELIC_HOST}" \
		-e NEW_RELIC_LICENSE_KEY="${NEW_RELIC_LICENSE_KEY}" \
		-e NEW_RELIC_DEVELOPER_MODE="${NEW_RELIC_DEVELOPER_MODE}" \
		-e GITHUB_ACTIONS="true" \
		ghcr.io/newrelic/newrelic-python-agent-ci:local /bin/bash
