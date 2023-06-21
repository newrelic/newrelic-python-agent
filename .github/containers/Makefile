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
