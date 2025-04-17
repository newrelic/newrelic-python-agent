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

# To target other architectures, change the --platform directive in the Dockerfile.
ARG IMAGE_TAG=latest
FROM ghcr.io/newrelic/newrelic-python-agent-ci:${IMAGE_TAG}

# Setup non-root user
USER root
ARG UID=1001
ARG GID=${UID}
ENV HOME=/home/vscode
RUN mkdir -p ${HOME} && \
    groupadd --gid ${GID} vscode && \
    useradd --uid ${UID} --gid ${GID} --home ${HOME} vscode && \
    chown -R ${UID}:${GID} /home/vscode

# Fix pyenv installation
RUN echo 'eval "$(pyenv init -)"' >>${HOME}/.bashrc && \
    chown -R vscode:vscode "${PYENV_ROOT}" && \
    chown -R vscode:vscode "${PIPX_HOME}"

# Set user
USER ${UID}:${GID}
