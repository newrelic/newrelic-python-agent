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
