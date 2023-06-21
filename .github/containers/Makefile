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

.PHONY: default 
default: build test

.PHONY: build
build:
	@# Perform a shortened build for testing
	@docker build --build-arg='PYTHON_VERSIONS=3.10 2.7' . -t ghcr.io/newrelic/python-agent-ci:local

.PHONY: test
test:
	@# Ensure python versions are usable
	@docker run --rm ghcr.io/newrelic/python-agent-ci:local /bin/bash -c '\
		python3.10 --version && \
		python2.7 --version && \
		touch tox.ini && tox --version && \
		echo "Success! Python versions installed."'
