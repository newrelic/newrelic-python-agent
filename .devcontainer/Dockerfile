# To target other architectures, change the --platform directive in the Dockerfile.
ARG IMAGE_TAG=latest
FROM ghcr.io/newrelic/newrelic-python-agent-ci:${IMAGE_TAG}

# Setup non-root user
USER root
ARG UID=1000
ARG GID=${UID}
ENV HOME /home/vscode
RUN mkdir -p ${HOME} && \
    groupadd --gid ${GID} vscode && \
    useradd --uid ${UID} --gid ${GID} --home ${HOME} vscode && \
    chown -R ${UID}:${GID} /home/vscode

# Fix pyenv installation
RUN echo 'eval "$(pyenv init -)"' >>${HOME}/.bashrc && \
    find ${PYENV_ROOT}/ -perm 644 -exec chmod 666 {} \; && \
    find ${PYENV_ROOT}/ -perm 755 -exec chmod 777 {} \; && \
    pyenv update

# Set user
USER ${UID}:${GID}
