# To target other architectures, change the --platform directive in the Dockerfile.
ARG IMAGE_TAG=latest
FROM ghcr.io/newrelic/newrelic-python-agent-ci:${IMAGE_TAG}

# Setup non-root user
USER root
ARG UID=1000
ARG GID=$UID
ENV HOME /home/vscode
RUN mkdir -p ${HOME} && \
    groupadd --gid ${GID} vscode && \
    useradd --uid ${UID} --gid ${GID} --home ${HOME} vscode && \
    chown -R ${UID}:${GID} /home/vscode

# Move pyenv installation
ENV PYENV_ROOT="${HOME}/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:${PATH}"
RUN mv /root/.pyenv /home/vscode/.pyenv && \
    chown -R vscode:vscode /home/vscode/.pyenv

# Set user
USER ${UID}:${GID}
